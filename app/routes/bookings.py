# app/routes/bookings.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user, login_required
from app import db
from app.models.user import User
from app.models.coach import Coach
from app.models.court import Court, CoachCourt
from app.models.court_fee import CourtFee
from app.models.pricing import PricingPlan
from app.models.booking import Availability, Booking, AvailabilityReservation
from app.models.package import BookingPackage
from app.forms.booking import BookingForm
from datetime import datetime, timedelta
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from app.models.notification import Notification
from app.utils.email import send_coach_booking_notification
from werkzeug.utils import secure_filename
from app.models.payment import PaymentProof
import os
import uuid 
import json

bp = Blueprint('bookings', __name__)


#@login_required
@bp.route('/api/availability/<int:coach_id>/<int:court_id>/<string:date>')
def get_availability(coach_id, court_id, date):
    """API endpoint to get availability for a coach at a court on a specific date"""
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Get all availability slots
        availabilities = Availability.query.filter(
            and_(
                Availability.coach_id == coach_id,
                Availability.court_id == court_id,
                Availability.date == date_obj,
                Availability.is_booked == False
            )
        ).all()
        
        # Get booked slots (for display purposes)
        bookings = Booking.query.filter(
            and_(
                Booking.coach_id == coach_id,
                Booking.court_id == court_id,
                Booking.date == date_obj
            )
        ).all()
        
        # Get court fees for this court
        court_fees = CourtFee.query.filter_by(court_id=court_id).all()
        
        # Get coach pricing plans
        pricing_plans = PricingPlan.query.filter(
            PricingPlan.coach_id == coach_id,
            PricingPlan.is_active == True
        ).all()
        
        # Organize pricing plans for easier client-side processing
        formatted_plans = []
        for plan in pricing_plans:
            if plan.discount_type != 'package':
                plan_data = {
                    'id': plan.id,
                    'name': plan.name,
                    'description': plan.description,
                    'discount_type': plan.discount_type,
                    'sessions_required': plan.sessions_required,
                    'first_time_only': plan.first_time_only,
                }
                
                if plan.percentage_discount:
                    plan_data['discount_amount'] = plan.percentage_discount
                    plan_data['discount_type_amount'] = 'percentage'
                elif plan.fixed_discount:
                    plan_data['discount_amount'] = plan.fixed_discount
                    plan_data['discount_type_amount'] = 'fixed'
                    
                if plan.valid_from and plan.valid_to:
                    plan_data['valid_from'] = plan.valid_from.isoformat() if plan.valid_from else None
                    plan_data['valid_to'] = plan.valid_to.isoformat() if plan.valid_to else None
                    
                formatted_plans.append(plan_data)
        
        # Format court fees for client-side use
        formatted_fees = []
        for fee in court_fees:
            formatted_fees.append({
                'start_time': fee.start_time.strftime('%H:%M'),
                'end_time': fee.end_time.strftime('%H:%M'),
                'fee': fee.fee
            })
        
        available_slots = []
        booked_slots = []
        
        for a in availabilities:
            # Determine court fee for this time slot
            court_fee = get_court_fee_for_time(court_fees, a.start_time)
            
            available_slots.append({
                'id': a.id,
                'time': a.start_time.strftime('%I:%M %p'),
                'court_fee': court_fee,
                'student_books_court': a.student_books_court  # Include booking responsibility
            })
            
        for b in bookings:
            court_fee = get_court_fee_for_time(court_fees, b.start_time)
            
            booked_slots.append({
                'time': b.start_time.strftime('%I:%M %p'),
                'court_fee': court_fee
            })
            
        return jsonify({
            'available': available_slots,
            'booked': booked_slots,
            'court_fees': formatted_fees,
            'pricing_plans': formatted_plans
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


def get_court_fee_for_time(court_fees, slot_time):
    """Helper function to determine the court fee for a specific time slot"""
    for fee in court_fees:
        if fee.start_time <= slot_time <= fee.end_time:
            return fee.fee
    
    # Default fee if no matching time range is found
    return 0.0

@bp.route('/api/bookings/create-with-proofs', methods=['POST'])
def create_booking_with_proofs():
    """API endpoint to create bookings with payment and booking proofs"""
    # Get form data and files
    try:
        reservation_token = request.form.get('reservation_token')
        if not reservation_token:
            return jsonify({'error': 'Missing reservation token'}), 400

        bookings_data = json.loads(request.form.get('bookings', '[]'))
        user_data_json = request.form.get('user_data')
        user_data = json.loads(user_data_json) if user_data_json else None
        
        # Get uploaded files
        coach_payment_proof = request.files.get('coach_payment_proof')
        court_booking_proof = request.files.get('court_booking_proof')
        
        # Validate required data
        if not bookings_data:
            return jsonify({'error': 'No booking data provided'}), 400
        
        # Ensure all bookings are for a single court
        unique_court_ids = set()
        for booking_item in bookings_data:
            court_id = booking_item.get('court_id')
            if court_id:
                unique_court_ids.add(court_id)
        
        if len(unique_court_ids) > 1:
            return jsonify({'error': 'All bookings must be for the same court. Please book one court at a time.'}), 400

        # Analyze all availability slots to determine requirements
        all_availability_ids = []
        total_availability_slots = 0
        for booking_item in bookings_data:
            all_availability_ids.extend(booking_item.get('availability_ids', []))
            total_availability_slots += len(booking_item.get('availability_ids', []))

        # Start a transaction
        db.session.begin()

        # Verify all slots are reserved by this user with valid reservations
        for avail_id in all_availability_ids:
            reservation = AvailabilityReservation.query.filter(
                AvailabilityReservation.availability_id == avail_id,
                AvailabilityReservation.student_id == user_id,
                AvailabilityReservation.reservation_token == reservation_token,
                AvailabilityReservation.expires_at > datetime.utcnow()
            ).first()
            
            if not reservation:
                db.session.rollback()
                return jsonify({
                    'error': 'Your reservation for one or more slots has expired. Please try again.',
                    'code': 'RESERVATION_EXPIRED'
                }), 400

        # Lock and verify all slots are still available
        unavailable = []
        for avail_id in all_availability_ids:
            avail = db.session.query(Availability).filter(
                Availability.id == avail_id,
                Availability.is_booked == False
            ).with_for_update().first()
            
            if not avail:
                unavailable.append(avail_id)

        if unavailable:
            db.session.rollback()
            return jsonify({
                'error': 'One or more selected slots are no longer available',
                'code': 'SLOT_UNAVAILABLE',
                'availability_ids': unavailable
            }), 409
        
        # Check if a package is being used and has enough sessions
        package = None
        package_id = None
        for booking_item in bookings_data:
            if booking_item.get('package_id'):
                package_id = booking_item.get('package_id')
                break

        if package_id:
            package = BookingPackage.query.get(package_id)
            if package:
                # Verify package belongs to this user and has sessions remaining
                if package.student_id != user_id:
                    return jsonify({'error': 'This package does not belong to you'}), 400
                    
                # Verify package is active
                if package.status != 'active':
                    return jsonify({'error': 'This package is not active yet. Please wait for approval.'}), 400

                # Check if package has enough remaining sessions
                sessions_remaining = package.total_sessions - package.sessions_booked
                if sessions_remaining < total_availability_slots:
                    return jsonify({'error': f'Not enough sessions remaining in package. You have {sessions_remaining} sessions left, but are trying to book {total_availability_slots} sessions.'}), 400
                    
        # Get all availabilities to check booking responsibilities
        availabilities = Availability.query.filter(Availability.id.in_(all_availability_ids)).all()
        
        # Check if any slots require student booking and any require coach booking
        has_student_booked_courts = any(a.student_books_court for a in availabilities)
        has_coach_booked_courts = any(not a.student_books_court for a in availabilities)
        
        # Check if coach payment is required
        coach_payment_required = True
        package_id = None
        for booking_item in bookings_data:
            package_id = booking_item.get('package_id')
            if package_id:
                # If using a package, coach payment might not be needed
                break
                
        if package_id:
            # Get package to check if it's valid and covers coaching fee
            package = BookingPackage.query.get(package_id)
            if package and package.sessions_booked < package.total_sessions:
                # Package is valid and has remaining sessions - no coach payment needed
                coach_payment_required = False
        
        # Validate required proofs based on scenario
        if coach_payment_required and not coach_payment_proof:
            return jsonify({'error': 'Coach payment proof is required for coaching fees'}), 400
            
        # Validate court-related proofs
        if has_student_booked_courts and not court_booking_proof:
            return jsonify({'error': 'Court booking proof is required for courts you need to book'}), 400
            
        # For coach-booked courts, we need to check if a payment proof is required
        # (could be the same as coach_payment_proof in some systems, separate in others)
        court_payment_required = has_coach_booked_courts
        if court_payment_required and not court_booking_proof:
            return jsonify({'error': 'Court payment proof is required for court fees paid to coach'}), 400
            
        # Check if user is authenticated or we need to create a guest user
        if current_user.is_authenticated:
            user_id = current_user.id
        else:
            # Create or get temporary user
            email = user_data.get('email')
            if not email:
                return jsonify({'error': 'Email is required for guest bookings'}), 400
                
            # Check if user with this email already exists
            existing_user = User.query.filter_by(email=email).first()
            
            if existing_user:
                user_id = existing_user.id
            else:
                # Create temporary user
                temp_user = User(
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    email=email,
                    phone=user_data.get('phone', ''),
                    is_temporary=True,
                    dupr_rating=user_data.get('dupr_rating'),
                    location=user_data.get('location', ''),
                    bio=user_data.get('bio', '')
                )
                
                # Set password if creating account
                if user_data.get('create_account'):
                    temp_user.is_temporary = False
                    temp_user.set_password(user_data.get('password'))
                
                try:
                    db.session.add(temp_user)
                    db.session.flush()  # Get ID without committing
                    user_id = temp_user.id
                except IntegrityError:
                    db.session.rollback()
                    return jsonify({'error': 'Failed to create temporary user'}), 400
        
        # Save uploaded files
        unique_id = uuid.uuid4().hex
        proofs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payment_proofs')
        os.makedirs(proofs_dir, exist_ok=True)
        
        # Save coach payment proof if provided
        coach_proof_path = None
        if coach_payment_proof:
            coach_proof_filename = f"coach_payment_{unique_id}_{secure_filename(coach_payment_proof.filename)}"
            coach_proof_path = os.path.join(proofs_dir, coach_proof_filename)
            coach_payment_proof.save(coach_proof_path)
        
        # Save court booking/payment proof if provided
        court_proof_path = None
        if court_booking_proof:
            court_proof_filename = f"court_booking_{unique_id}_{secure_filename(court_booking_proof.filename)}"
            court_proof_path = os.path.join(proofs_dir, court_proof_filename)
            court_booking_proof.save(court_proof_path)
        
        # Process each booking
        bookings_created = []
        
        # Initialize package session counter
        package_sessions_used = 0

        for booking_item in bookings_data:
            coach_id = booking_item.get('coach_id')
            court_id = booking_item.get('court_id')
            availability_ids = booking_item.get('availability_ids', [])
            package_id = booking_item.get('package_id')
            
            # Get coach hourly rate
            coach = Coach.query.get(coach_id)
            if not coach:
                return jsonify({'error': f'Coach with ID {coach_id} not found'}), 404
                
            hourly_rate = coach.hourly_rate
            
            # Check for package
            package = None
            if package_id:
                package = BookingPackage.query.get(package_id)
                
                # Verify package belongs to this user and has sessions remaining
                if not package or package.student_id != user_id or package.sessions_booked >= package.total_sessions:
                    return jsonify({'error': 'Invalid package or insufficient sessions remaining'}), 400
                
                # Verify package can be used with this coach
                if not package.can_use_for_coach(coach_id):
                    return jsonify({'error': 'This package cannot be used with this coach'}), 400
            
            # Process each availability slot
            for avail_id in availability_ids:
                availability = Availability.query.get(avail_id)
                
                if not availability or availability.is_booked:
                    return jsonify({'error': 'One or more selected slots are no longer available'}), 400
                    
                # Get court fee for this time
                court_fees = CourtFee.query.filter_by(court_id=court_id).all()
                court_fee = get_court_fee_for_time(court_fees, availability.start_time)
                
                # Calculate total price (coach fee + court fee)
                base_price = hourly_rate + court_fee
                
                # Apply discount if any
                discount_percentage = None
                discount_amount = None
                price = base_price
                
                # Check for applied pricing plan
                pricing_plan_id = booking_item.get('pricing_plan_id')
                if pricing_plan_id:
                    pricing_plan = PricingPlan.query.get(pricing_plan_id)
                    
                    if pricing_plan and pricing_plan.is_active:
                        # Set discount values
                        if pricing_plan.percentage_discount:
                            discount_percentage = pricing_plan.percentage_discount
                            discount_value = base_price * (discount_percentage / 100)
                            price = base_price - discount_value
                        elif pricing_plan.fixed_discount:
                            # Distribute fixed discount proportionally across all booked sessions
                            per_session_discount = pricing_plan.fixed_discount / len(availability_ids)
                            discount_amount = per_session_discount
                            price = base_price - per_session_discount
                
                # If using package, set coach fee to 0
                if package and package_sessions_used < (package.total_sessions - package.sessions_booked):
                    price = court_fee  # Only pay for court
                    package_sessions_used += 1  # Increment package session counter
                
                    package.bookings.append(booking)

                # Mark availability as booked
                availability.is_booked = True
                
                # Determine payment statuses based on this specific slot
                student_books_court = availability.student_books_court
                
                # Coaching payment status
                coaching_payment_required = not package  # No coaching payment needed if using package
                coaching_payment_status = 'not_required'
                if coaching_payment_required:
                    coaching_payment_status = 'uploaded' if coach_payment_proof else 'pending'
                
                # Court payment/booking status
                court_payment_required = True  # Court fee is always required
                
                if student_books_court:
                    # Student books court directly with venue
                    court_payment_status = 'uploaded' if court_booking_proof else 'pending'
                else:
                    # Coach books court, student pays coach for court fee
                    court_payment_status = 'uploaded' if court_booking_proof else 'pending'

                # Create booking
                booking = Booking(
                    student_id=user_id,
                    coach_id=coach_id,
                    court_id=court_id,
                    availability_id=availability.id,
                    date=availability.date,
                    start_time=availability.start_time,
                    end_time=availability.end_time,
                    base_price=base_price,
                    price=price,
                    court_fee=court_fee,
                    coach_fee=hourly_rate,
                    status='upcoming',
                    pricing_plan_id=pricing_plan_id,
                    discount_percentage=discount_percentage,
                    discount_amount=discount_amount,
                    court_payment_required=court_payment_required,
                    court_payment_status=court_payment_status,
                    coaching_payment_required=coaching_payment_required,
                    coaching_payment_status=coaching_payment_status,
                    court_booking_responsibility = 'student' if availability.student_books_court else 'student',
                )
                
                db.session.add(booking)
                db.session.flush()  # Get booking ID
                
                # Associate booking with package if applicable
                if package:
                    package.bookings.append(booking)
            
                # Add coach payment proof if provided
                if coach_payment_proof and coach_proof_path and coaching_payment_required:
                    coach_proof = PaymentProof(
                        booking_id=booking.id,
                        image_path=coach_proof_path.replace(current_app.config['UPLOAD_FOLDER'] + '/', ''),
                        proof_type='coaching',
                        status='pending'
                    )
                    db.session.add(coach_proof)
                
                # Add court proof - this covers both direct booking proof and court fee payment to coach
                if court_booking_proof and court_proof_path:
                    proof_type = 'court_booking' if student_books_court else 'court_payment'
                    court_proof = PaymentProof(
                        booking_id=booking.id,
                        image_path=court_proof_path.replace(current_app.config['UPLOAD_FOLDER'] + '/', ''),
                        proof_type=proof_type,
                        status='pending'
                    )
                    db.session.add(court_proof)
                
                bookings_created.append({
                    'id': booking.id,
                    'date': availability.date.isoformat(),
                    'start_time': availability.start_time.strftime('%I:%M %p'),
                    'end_time': availability.end_time.strftime('%I:%M %p'),
                    'coach_fee': hourly_rate,
                    'court_fee': court_fee,
                    'base_price': base_price,
                    'price': price,
                    'student_books_court': availability.student_books_court
                })
        
        # After all bookings are processed, update the package sessions count ONCE
        if package and package_sessions_used > 0:
            package.sessions_booked += package_sessions_used

        # Generate confirmation number
        confirmation_number = f"PBC-{uuid.uuid4().hex[:8].upper()}"
        
        # Create notification for coach
        notification = Notification(
            user_id=coach.user_id,
            title="New booking with payment proof",
            message=f"New booking on {booking.date.strftime('%Y-%m-%d')} with payment proof uploaded",
            notification_type="booking",
            related_id=booking.id
        )
        db.session.add(notification)
        
        try:
            for avail_id in all_availability_ids:
                AvailabilityReservation.query.filter_by(
                    availability_id=avail_id,
                    student_id=user_id
                ).delete()
        except Exception as e:
            # Just log this error, don't affect the booking success
            current_app.logger.warning(f"Failed to clean up reservations for user {user_id}: {str(e)}")

        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Bookings created successfully with payment proofs',
            'confirmation_number': confirmation_number,
            'bookings': bookings_created
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/reserve-slots', methods=['POST'])
def reserve_availability_slots():
    """Create temporary reservations for selected availability slots"""
    data = request.get_json()
    availability_ids = data.get('availability_ids', [])
    
    current_user_id = -1

    try:
        current_user_id = current_user.id
    except:
        print("Current user is an anonymous user")

    if not availability_ids:
        return jsonify({'error': 'No availability slots selected'}), 400
    
    # Check if any slots are already booked or reserved
    availabilities = Availability.query.filter(
        Availability.id.in_(availability_ids)
    ).all()
    
    # Check availability
    for avail in availabilities:
        if avail.is_booked:
            return jsonify({
                'error': 'One or more selected slots are no longer available',
                'availability_id': avail.id,
                'start_time': avail.start_time.strftime("%H:%M"),
                'availability_date': avail.date.strftime("%m/%d/%Y")
            }), 409  # 409 Conflict
        
        # Check for existing non-expired reservations
        existing_reservation = AvailabilityReservation.query.filter(
            AvailabilityReservation.availability_id == avail.id,
            AvailabilityReservation.expires_at > datetime.utcnow()
        ).first()
        
        if existing_reservation and existing_reservation.student_id != current_user_id:
            return jsonify({
                'error': 'One or more selected slots are currently being booked by another student',
                'availability_id': avail.id,
                'start_time': avail.start_time.strftime("%H:%M"),
                'availability_date': avail.date.strftime("%m/%d/%Y")
            }), 409  # 409 Conflict
    
    # Create reservations
    reservations = []
    reservation_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=15)  # 15-minute timeout
    
    try:
        for avail_id in availability_ids:
            # Delete any existing expired reservations
            AvailabilityReservation.query.filter(
                AvailabilityReservation.availability_id == avail_id,
                AvailabilityReservation.expires_at <= datetime.utcnow()
            ).delete()
            
            # Delete existing reservation by this user if any
            AvailabilityReservation.query.filter(
                AvailabilityReservation.availability_id == avail_id,
                AvailabilityReservation.student_id == current_user_id
            ).delete()
            
            # Create new reservation
            reservation = AvailabilityReservation(
                availability_id=avail_id,
                student_id=current_user_id,
                reservation_token=reservation_token,
                expires_at=expires_at
            )
            db.session.add(reservation)
            reservations.append(reservation)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'reservation_token': reservation_token,
            'expires_at': expires_at.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/book/<int:coach_id>', methods=['GET', 'POST'])
@login_required
def book_session(coach_id):
    if current_user.is_coach:
        flash('Coaches cannot book sessions with other coaches')
        return redirect(url_for('main.index'))
    
    coach = Coach.query.get_or_404(coach_id)

    # Get coach courts
    coach_courts = CoachCourt.query.filter_by(coach_id=coach_id).all()
    courts = Court.query.filter(Court.id.in_([cc.court_id for cc in coach_courts])).all()
    
    # Get active pricing plans
    pricing_plans = PricingPlan.query.filter_by(
        coach_id=coach_id, 
        is_active=True
    ).all()
    
    # Check if this student is a first-time student with this coach
    is_first_time = not Booking.query.filter_by(
        student_id=current_user.id,
        coach_id=coach_id
    ).first()
    
    # Get active packages this student has purchased
    coach_packages = BookingPackage.query.filter(
        BookingPackage.student_id == current_user.id,
        BookingPackage.coach_id == coach_id,
        BookingPackage.sessions_booked < BookingPackage.total_sessions,
        (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.utcnow()))
    ).all()
    
    # Get academy packages that can be used with this coach
    academy_packages = []
    
    # Get academies this coach belongs to
    coach_academies = AcademyCoach.query.filter_by(
        coach_id=coach_id,
        is_active=True
    ).all()
    
    academy_ids = [ca.academy_id for ca in coach_academies]
    
    if academy_ids:
        # Find packages for these academies
        academy_packages = BookingPackage.query.filter(
            BookingPackage.student_id == current_user.id,
            BookingPackage.academy_id.in_(academy_ids),
            BookingPackage.package_type == 'academy',
            BookingPackage.sessions_booked < BookingPackage.total_sessions,
            (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.utcnow()))
        ).all()
    
    # Combine all available packages
    available_packages = coach_packages + academy_packages
    
    if request.method == 'POST':
        # Get form data
        availability_ids = request.form.getlist('availability_ids')
        court_id = request.form.get('court_id')
        pricing_plan_id = request.form.get('pricing_plan_id')
        package_id = request.form.get('package_id')
        
        if not availability_ids or not court_id:
            flash('Please select at least one time slot and a court.', 'error')
            return redirect(url_for('bookings.book_session', coach_id=coach_id))
        
        # Determine which pricing to apply
        applied_pricing_plan = None
        applied_package = None
        total_sessions = len(availability_ids)
        base_price = coach.hourly_rate
        discount_percentage = None
        discount_amount = None
        
        # If using a package
        if package_id:
            package = BookingPackage.query.get(package_id)
            if package and package.student_id == current_user.id and package.sessions_booked < package.total_sessions:
                applied_package = package
                # Package price is already accounted for, so set price to 0
                base_price = 0
                applied_pricing_plan = package.pricing_plan
        
        # If using a pricing plan (and not a package)
        elif pricing_plan_id:
            plan = PricingPlan.query.get(pricing_plan_id)
            
            # Verify plan eligibility
            if plan and plan.is_active:
                # First-time discount
                if plan.first_time_only and not is_first_time:
                    flash('First-time discount can only be applied to new students.')
                # Package deal
                elif plan.discount_type == 'package' and total_sessions < plan.sessions_required:
                    flash(f'You need to book at least {plan.sessions_required} sessions to use this package deal.')
                # Seasonal discount
                elif plan.discount_type == 'seasonal' and (
                    (plan.valid_from and plan.valid_from > datetime.utcnow().date()) or
                    (plan.valid_to and plan.valid_to < datetime.utcnow().date())
                ):
                    flash('This promotional discount is not currently active.')
                else:
                    applied_pricing_plan = plan
                    
                    # Calculate discount
                    if plan.percentage_discount:
                        discount_percentage = plan.percentage_discount
                        discount_amount = (base_price * total_sessions) * (discount_percentage / 100)
                    elif plan.fixed_discount:
                        discount_amount = plan.fixed_discount
                    
                    # If it's a package deal and sufficient sessions are selected, create a package
                    if plan.discount_type == 'package' and plan.sessions_required <= total_sessions:
                        # Calculate total price with discount
                        original_price = base_price * plan.sessions_required
                        if discount_percentage:
                            total_price = original_price * (1 - discount_percentage / 100)
                        elif discount_amount:
                            total_price = original_price - discount_amount
                        else:
                            total_price = original_price
                        
                        # Create the package
                        package = BookingPackage(
                            student_id=current_user.id,
                            coach_id=coach_id,
                            pricing_plan_id=plan.id,
                            total_sessions=plan.sessions_required,
                            sessions_booked=0,  # Will be updated during booking
                            total_price=total_price,
                            original_price=original_price,
                            discount_amount=discount_amount,
                            # Set expiration if needed (e.g., 90 days from now)
                            expires_at=datetime.utcnow() + timedelta(days=90) if plan.sessions_required > 1 else None
                        )
                        
                        applied_package = package
        
        total_cost = 0
        bookings_created = []
        
        # Start a transaction to ensure atomicity
        try:
            # If creating a new package, add it to the database
            if applied_package and applied_package.id is None:
                db.session.add(applied_package)
                db.session.flush()  # Get the package ID
            
            for avail_id in availability_ids:
                availability = Availability.query.get(avail_id)
                
                # Double-check that the availability is still free (prevent race conditions)
                if availability and not availability.is_booked:
                    # Determine price for this booking
                    booking_price = base_price
                    booking_discount = 0
                    booking_discount_percentage = None
                    
                    # If using a package
                    if applied_package:
                        # Check if this package can be used with this coach
                        if not applied_package.can_use_for_coach(coach_id):
                            flash('This package cannot be used with this coach.', 'error')
                            return redirect(url_for('bookings.book_session', coach_id=coach_id))

                        # If we still have sessions in the package
                        if applied_package.sessions_booked < applied_package.total_sessions:
                            booking_price = 0  # Package already paid for
                            applied_package.sessions_booked += 1
                        else:
                            # Regular price if package is used up
                            booking_price = base_price
                    
                    # Apply discount if not using a package
                    elif applied_pricing_plan and not applied_package:
                        if applied_pricing_plan.percentage_discount:
                            booking_discount_percentage = applied_pricing_plan.percentage_discount
                            booking_discount = booking_price * (booking_discount_percentage / 100)
                            booking_price -= booking_discount
                        elif applied_pricing_plan.fixed_discount:
                            # Distribute fixed discount evenly across all bookings
                            booking_discount = applied_pricing_plan.fixed_discount / total_sessions
                            booking_price -= booking_discount
                    
                    # Mark as booked
                    availability.is_booked = True
                    
                    # Create booking
                    booking = Booking(
                        student_id=current_user.id,
                        coach_id=coach_id,
                        court_id=court_id,
                        availability_id=availability.id,
                        date=availability.date,
                        start_time=availability.start_time,
                        end_time=availability.end_time,
                        base_price=base_price,
                        price=booking_price,
                        status='upcoming',
                        pricing_plan_id=applied_pricing_plan.id if applied_pricing_plan else None,
                        discount_amount=booking_discount if booking_discount > 0 else None,
                        discount_percentage=booking_discount_percentage
                    )
                    
                    db.session.add(booking)
                    
                    # If using a package, associate this booking with the package
                    if applied_package:
                        applied_package.bookings.append(booking)
                    
                    bookings_created.append(booking)
                    total_cost += booking_price
                else:
                    # If any slot is already booked, rollback the entire transaction
                    db.session.rollback()
                    flash('One or more of your selected time slots is no longer available. Please try again.', 'error')
                    return redirect(url_for('bookings.book_session', coach_id=coach_id))
            
            # Commit all changes if everything is successful
            db.session.commit()
            
            # Generate success message
            if applied_package:
                flash(f'Successfully booked {len(bookings_created)} sessions using your package! {applied_package.total_sessions - applied_package.sessions_booked} sessions remaining in this package.')
            elif applied_pricing_plan:
                flash(f'Successfully booked {len(bookings_created)} sessions with a discount for a total of ${total_cost:.2f}!')
            else:
                flash(f'Successfully booked {len(bookings_created)} sessions for a total of ${total_cost:.2f}!')
                
            return redirect(url_for('students.bookings'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}')
            return redirect(url_for('bookings.book_session', coach_id=coach_id))
    
    return render_template(
        'bookings/book.html', 
        coach=coach, 
        courts=courts, 
        pricing_plans=pricing_plans,
        is_first_time=is_first_time,
        active_packages=available_packages
    )

@bp.route('/purchase-package/<int:coach_id>/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def purchase_package(coach_id, plan_id):
    if current_user.is_coach:
        flash('Coaches cannot purchase packages')
        return redirect(url_for('main.index'))
    
    coach = Coach.query.get_or_404(coach_id)
    pricing_plan = PricingPlan.query.get_or_404(plan_id)
    
    # Verify this is a package plan
    if pricing_plan.discount_type != 'package':
        flash('Invalid package selected')
        return redirect(url_for('bookings.book_session', coach_id=coach_id))
    
    # Calculate package price
    base_price = coach.hourly_rate
    total_sessions = pricing_plan.sessions_required
    original_price = base_price * total_sessions
    
    discount_amount = None
    if pricing_plan.percentage_discount:
        discount_amount = original_price * (pricing_plan.percentage_discount / 100)
    elif pricing_plan.fixed_discount:
        discount_amount = pricing_plan.fixed_discount
    
    total_price = original_price - (discount_amount or 0)
    
    if request.method == 'POST':
        # Create the package
        package = BookingPackage(
            student_id=current_user.id,
            coach_id=coach_id,
            pricing_plan_id=plan_id,
            total_sessions=total_sessions,
            sessions_booked=0,
            sessions_completed=0,
            total_price=total_price,
            original_price=original_price,
            discount_amount=discount_amount,
            # Set expiration (e.g., 90 days from now)
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
        
        try:
            db.session.add(package)
            db.session.commit()
            flash(f'Successfully purchased a package of {total_sessions} sessions for ${total_price:.2f}!')
            return redirect(url_for('students.bookings'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}')
            return redirect(url_for('bookings.purchase_package', coach_id=coach_id, plan_id=plan_id))
    
    return render_template(
        'bookings/purchase_package.html',
        coach=coach,
        plan=pricing_plan,
        original_price=original_price,
        discount_amount=discount_amount,
        total_price=total_price,
        total_sessions=total_sessions
    )

@bp.route('/purchase-package/<int:coach_id>/<int:plan_id>/checkout', methods=['POST'])
@login_required
def package_checkout(coach_id, plan_id):
    if current_user.is_coach:
        flash('Coaches cannot purchase packages')
        return redirect(url_for('main.index'))
    
    coach = Coach.query.get_or_404(coach_id)
    pricing_plan = PricingPlan.query.get_or_404(plan_id)
    
    # Calculate package price
    base_price = coach.hourly_rate
    total_sessions = pricing_plan.sessions_required
    original_price = base_price * total_sessions
    
    discount_amount = None
    if pricing_plan.percentage_discount:
        discount_amount = original_price * (pricing_plan.percentage_discount / 100)
    elif pricing_plan.fixed_discount:
        discount_amount = pricing_plan.fixed_discount
    
    total_price = original_price - (discount_amount or 0)
    total_price_cents = int(total_price * 100)  # Stripe uses cents
    
    try:
        # Create Stripe checkout session
        import stripe
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"{pricing_plan.name} - {total_sessions} Sessions with {coach.user.full_name()}",
                        'description': pricing_plan.description,
                    },
                    'unit_amount': total_price_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('bookings.package_success', coach_id=coach_id, plan_id=plan_id, _external=True) + 
                         '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('bookings.book_session', coach_id=coach_id, _external=True),
            client_reference_id=f"package_{current_user.id}_{coach_id}_{plan_id}",
            metadata={
                'coach_id': coach_id,
                'student_id': current_user.id,
                'plan_id': plan_id,
                'total_sessions': total_sessions,
                'total_price': total_price,
                'original_price': original_price,
                'discount_amount': discount_amount or 0
            }
        )
        
        return redirect(checkout_session.url)
    
    except Exception as e:
        flash(f'An error occurred with the payment process: {str(e)}')
        return redirect(url_for('bookings.purchase_package', coach_id=coach_id, plan_id=plan_id))

@bp.route('/purchase-package/success')
@login_required
def package_success():
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Invalid checkout session')
        return redirect(url_for('main.index'))
    
    try:
        # Verify the payment with Stripe
        import stripe
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status != 'paid':
            flash('Your payment was not successful')
            return redirect(url_for('main.index'))
        
        # Extract metadata
        metadata = checkout_session.metadata
        coach_id = int(metadata.get('coach_id'))
        plan_id = int(metadata.get('plan_id'))
        total_sessions = int(metadata.get('total_sessions'))
        total_price = float(metadata.get('total_price'))
        original_price = float(metadata.get('original_price'))
        discount_amount = float(metadata.get('discount_amount'))
        
        # Create the package
        package = BookingPackage(
            student_id=current_user.id,
            coach_id=coach_id,
            pricing_plan_id=plan_id,
            total_sessions=total_sessions,
            sessions_booked=0,
            sessions_completed=0,
            total_price=total_price,
            original_price=original_price,
            discount_amount=discount_amount,
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
        
        db.session.add(package)
        db.session.commit()
        
        flash(f'Successfully purchased a package of {total_sessions} sessions!')
        return redirect(url_for('students.bookings'))
        
    except Exception as e:
        flash(f'An error occurred while processing your package purchase: {str(e)}')
        return redirect(url_for('main.index'))
        
# # Add this to the booking route
# from sqlalchemy.exc import IntegrityError

# # When creating a booking...
# try:
#     # [existing booking creation code]
#     db.session.commit()
# except IntegrityError:
#     db.session.rollback()
#     flash('This time slot has just been booked by someone else. Please choose another time.', 'error')
#     return redirect(url_for('coaches.view_coach', coach_id=coach_id))