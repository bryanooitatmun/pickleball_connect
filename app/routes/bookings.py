# app/routes/bookings.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.models.user import User
from app.models.coach import Coach
from app.models.court import Court, CoachCourt
from app.models.court_fee import CourtFee
from app.models.pricing import PricingPlan
from app.models.booking import Availability, Booking
from app.forms.booking import BookingForm
from datetime import datetime, timedelta
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
import uuid 

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
                'court_fee': court_fee
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


@bp.route('/api/bookings/create', methods=['POST'])
def create_booking():
    """API endpoint to create bookings"""
    data = request.json
    
    # Extract booking data
    bookings_data = data.get('bookings', [])
    user_data = data.get('user_data', {})
    
    # Check if we have booking data
    if not bookings_data:
        return jsonify({'error': 'No booking data provided'}), 400
    
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
                is_temporary=True,  # Mark as temporary user
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
    
    # Process each booking
    bookings_created = []
    
    try:
        for booking_item in bookings_data:
            coach_id = booking_item.get('coach_id')
            court_id = booking_item.get('court_id')
            availability_ids = booking_item.get('availability_ids', [])
            
            # Get coach hourly rate
            coach = Coach.query.get(coach_id)
            if not coach:
                return jsonify({'error': f'Coach with ID {coach_id} not found'}), 404
                
            hourly_rate = coach.hourly_rate
            
            # Check if student is eligible for first-time discount
            is_first_time = not Booking.query.filter_by(
                student_id=user_id,
                coach_id=coach_id
            ).first()
            
            # Check for applied pricing plan
            pricing_plan_id = booking_item.get('pricing_plan_id')
            pricing_plan = None
            discount_percentage = None
            discount_amount = None
            
            if pricing_plan_id:
                pricing_plan = PricingPlan.query.get(pricing_plan_id)
                
                # Verify eligibility
                if pricing_plan and pricing_plan.is_active:
                    # First-time discount eligibility
                    if pricing_plan.first_time_only and not is_first_time:
                        return jsonify({'error': 'First-time discount can only be applied to new students.'}), 400
                        
                    # Seasonal discount eligibility
                    if pricing_plan.discount_type == 'seasonal' and (
                        (pricing_plan.valid_from and pricing_plan.valid_from > datetime.now().date()) or
                        (pricing_plan.valid_to and pricing_plan.valid_to < datetime.now().date())
                    ):
                        return jsonify({'error': 'This promotional discount is not currently active.'}), 400
                        
                    # Package discount eligibility
                    if pricing_plan.discount_type == 'package' and len(availability_ids) < pricing_plan.sessions_required:
                        return jsonify({
                            'error': f'You need to book at least {pricing_plan.sessions_required} sessions to use this package deal.'
                        }), 400
                    
                    # Set discount values
                    if pricing_plan.percentage_discount:
                        discount_percentage = pricing_plan.percentage_discount
                    elif pricing_plan.fixed_discount:
                        discount_amount = pricing_plan.fixed_discount
            
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
                if discount_percentage:
                    discount_value = base_price * (discount_percentage / 100)
                    price = base_price - discount_value
                elif discount_amount:
                    # Distribute fixed discount proportionally across all booked sessions
                    per_session_discount = discount_amount / len(availability_ids)
                    price = base_price - per_session_discount
                else:
                    price = base_price
                
                # Mark availability as booked
                availability.is_booked = True
                
                # Create booking
                booking = Booking(
                    student_id=user_id,
                    coach_id=coach_id,
                    court_id=court_id,
                    availability_id=availability.id,
                    date=availability.date,
                    start_time=availability.start_time,
                    end_time=availability.end_time,
                    base_price=base_price,  # Store the original price before discount
                    price=price,            # Actual price after discount
                    court_fee=court_fee,    # Store the court fee separately
                    coach_fee=hourly_rate,  # Store the coach fee separately
                    status='upcoming',
                    pricing_plan_id=pricing_plan_id if pricing_plan else None,
                    discount_percentage=discount_percentage,
                    discount_amount=discount_amount
                )
                
                db.session.add(booking)
                
                bookings_created.append({
                    'date': availability.date.isoformat(),
                    'start_time': availability.start_time.strftime('%I:%M %p'),
                    'end_time': availability.end_time.strftime('%I:%M %p'),
                    'coach_fee': hourly_rate,
                    'court_fee': court_fee,
                    'base_price': base_price,
                    'price': price
                })
        
        # Generate confirmation number
        confirmation_number = f"PBC-{uuid.uuid4().hex[:8].upper()}"
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Bookings created successfully',
            'confirmation_number': confirmation_number,
            'bookings': bookings_created
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


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
    active_packages = BookingPackage.query.filter(
        BookingPackage.student_id == current_user.id,
        BookingPackage.coach_id == coach_id,
        BookingPackage.sessions_booked < BookingPackage.total_sessions,
        (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.now()))
    ).all()
    
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
                    (plan.valid_from and plan.valid_from > datetime.now().date()) or
                    (plan.valid_to and plan.valid_to < datetime.now().date())
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
                            expires_at=datetime.now() + timedelta(days=90) if plan.sessions_required > 1 else None
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
        active_packages=active_packages
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
            expires_at=datetime.now() + timedelta(days=90)
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
            expires_at=datetime.now() + timedelta(days=90)
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