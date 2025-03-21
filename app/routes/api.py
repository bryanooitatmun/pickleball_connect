# app/routes/api.py
from flask import Blueprint, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.coach import Coach, CoachImage
from app.models.user import User
from app.models.court import Court, CoachCourt
from app.models.booking import Availability, Booking, AvailabilityTemplate
from app.models.package import BookingPackage, booking_package_association
from app.models.session_log import SessionLog
from app.models.rating import CoachRating
from app.models.pricing import PricingPlan  # Add missing import for PricingPlan
from app.forms.coach import CoachProfileForm, AvailabilityForm, SessionLogForm  # Also add the missing form import
from app.models.academy import Academy, AcademyCoach, AcademyManager
from app.models.academy_pricing import AcademyPricingPlan
from app.models.user import User
from app.utils.file_utils import save_uploaded_file, delete_file
from datetime import datetime, timedelta, time
from app.models.payment import PaymentProof
from app.models.notification import Notification
from app.models.tag import Tag, CoachTag
from functools import wraps
import os
import json
import uuid 
from sqlalchemy import func, or_, extract 

bp = Blueprint('api', __name__, url_prefix='/api')

# Academy manager access decorator
def coach_or_academy_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_academy_manager and not current_user.is_coach:
            flash('Access denied.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/coach/contact/<int:coach_id>')
@login_required
def get_coach_contact(coach_id):
    """API endpoint to get coach contact information"""
    coach = Coach.query.get_or_404(coach_id)
    user = User.query.get_or_404(coach.user_id)
    
    # First check for direct packages with this coach
    has_direct_packages = BookingPackage.query.filter(
        BookingPackage.student_id == current_user.id,
        BookingPackage.coach_id == coach_id,
        BookingPackage.status == 'active'
    ).first() is not None
    
    # If no direct packages, check for academy packages
    has_academy_packages = False
    if not has_direct_packages:
        # Get all academies this coach belongs to
        coach_academies = AcademyCoach.query.filter_by(
            coach_id=coach_id,
            is_active=True
        ).all()
        
        academy_ids = [ac.academy_id for ac in coach_academies]
        
        # If coach belongs to any academies, check if student has active packages with those academies
        if academy_ids:
            has_academy_packages = BookingPackage.query.filter(
                BookingPackage.student_id == current_user.id,
                BookingPackage.academy_id.in_(academy_ids),
                BookingPackage.package_type == 'academy',
                BookingPackage.status == 'active'
            ).first() is not None
    
    # Only allow access if student has either direct or academy packages
    if not (has_direct_packages or has_academy_packages):
        return jsonify({'error': 'You must have active credits to access coach contact info'}), 403
    
    return jsonify({
        'phone_number': user.phone,
        'email': user.email
    })

@bp.route('/coach/profile')
@login_required
def get_coach_profile():
    """API endpoint to get the current coach's profile data"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get coach rating
    avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(CoachRating.coach_id == coach.id).scalar() or 0
    rating_count = CoachRating.query.filter_by(coach_id=coach.id).count()
    
    # Get coach courts
    courts = Court.query.join(CoachCourt).filter(CoachCourt.coach_id == coach.id).all()
    court_data = [{'id': court.id, 'name': court.name} for court in courts]

    # Format response data
    response = {
        'id': coach.id,
        'user': {
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'email': current_user.email,
            'gender': current_user.gender,
            'location': current_user.location,
            'dupr_rating': current_user.dupr_rating,
            'profile_picture': current_user.profile_picture
        },
        'hourly_rate': coach.hourly_rate,
        'sessions_completed': coach.sessions_completed,
        'avg_rating': round(float(avg_rating), 1),
        'rating_count': rating_count,
        'courts': court_data,
        'biography': coach.biography,
        'years_experience': coach.years_experience,
        'specialties': coach.specialties,
        'payment_details': coach.payment_info
    }
    
    return jsonify(response)

@bp.route('/coach/stats')
@login_required
def get_coach_stats():
    """API endpoint to get coach statistics for dashboard"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Count upcoming bookings
    upcoming_sessions = Booking.query.filter(
        Booking.coach_id == coach.id,
        Booking.status == 'upcoming',
        Booking.date >= datetime.utcnow().date()
    ).count()
    
    # Get total earnings from completed sessions
    total_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed'
    ).scalar() or 0
    
    # Get average rating
    avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(
        CoachRating.coach_id == coach.id
    ).scalar() or 0
    
    # Get rating count
    rating_count = CoachRating.query.filter_by(coach_id=coach.id).count()
    
    # Get monthly earnings for dashboard chart
    # This will get earnings for the last 6 months
    monthly_earnings = {}
    for i in range(5, -1, -1):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
        month_name = month_start.strftime('%B %Y')
        
        month_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach.id,
            Booking.status == 'completed',
            extract('year', Booking.date) == month_start.year,
            extract('month', Booking.date) == month_start.month
        ).scalar() or 0
        
        monthly_earnings[month_name] = float(month_earnings)
    
    # Get upcoming bookings (limited to 3 for dashboard)
    upcoming_bookings_query = Booking.query.filter(
        Booking.coach_id == coach.id,
        Booking.status == 'upcoming',
        Booking.date >= datetime.utcnow().date()
    ).order_by(Booking.date, Booking.start_time).limit(3)
    
    upcoming_bookings = []
    for booking in upcoming_bookings_query:
        upcoming_bookings.append({
            'id': booking.id,
            'student': {
                'first_name': booking.student.first_name,
                'last_name': booking.student.last_name,
                'email': booking.student.email
            },
            'date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M:%S'),
            'end_time': booking.end_time.strftime('%H:%M:%S'),
            'price': float(booking.price),
            'status': booking.status,
            'court': {
                'id': booking.court_id,
                'name': booking.court.name
            },
            'venue_confirmed': booking.venue_confirmed,
            'court_booking_responsibility': booking.court_booking_responsibility
        })
    
    # Get recent session logs (limited to 3 for dashboard)
    recent_logs_query = SessionLog.query.filter_by(coach_id=coach.id).order_by(
        SessionLog.created_at.desc()
    ).limit(3)
    
    recent_logs = []
    for log in recent_logs_query:
        recent_logs.append({
            'id': log.id,
            'title': log.title,
            'notes': log.notes,
            'coach_notes': log.coach_notes,
            'created_at': log.created_at.isoformat(),
            'booking': {
                'id': log.booking_id,
                'date': log.booking.date.isoformat(),
                'start_time': log.booking.start_time.strftime('%H:%M:%S'),
                'end_time': log.booking.end_time.strftime('%H:%M:%S'),
                'court': {
                    'id': log.booking.court_id,
                    'name': log.booking.court.name
                }
            }
        })
    
    result = {
        'completed_sessions': coach.sessions_completed,
        'upcoming_sessions': upcoming_sessions,
        'total_earnings': float(total_earnings),
        'average_rating': float(avg_rating),
        'rating_count': rating_count,
        'monthly_earnings': monthly_earnings,
        'upcoming_bookings': upcoming_bookings,
        'recent_logs': recent_logs
    }
    
    # Add academy-specific data if user is an academy manager
    if current_user.is_academy_manager:
        # Get academy ID from academy manager record
        academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first()
        
        if academy_manager:
            academy_id = academy_manager.academy_id
            
            # Get academy coaches
            academy_coaches_query = AcademyCoach.query.filter_by(
                academy_id=academy_id,
                is_active=True
            ).limit(4)  # Limit to 4 for dashboard display
            
            academy_coaches = []
            for ac in academy_coaches_query:
                coach_obj = Coach.query.get(ac.coach_id)
                if not coach_obj or not coach_obj.user:
                    continue
                
                # Get profile picture
                profile_picture = coach_obj.user.profile_picture
                
                academy_coaches.append({
                    'id': coach_obj.id,
                    'first_name': coach_obj.user.first_name,
                    'last_name': coach_obj.user.last_name,
                    'role': ac.role,
                    'dupr_rating': coach_obj.user.dupr_rating,
                    'profile_picture': profile_picture,
                    'sessions_completed': coach_obj.sessions_completed
                })
            
            # Get recent package requests
            recent_packages_query = BookingPackage.query.filter_by(
                academy_id=academy_id
            ).order_by(BookingPackage.purchase_date.desc()).limit(3)
            
            recent_packages = []
            for package in recent_packages_query:
                student = User.query.get(package.student_id)
                if not student:
                    continue
                
                package_data = {
                    'id': package.id,
                    'student': {
                        'first_name': student.first_name,
                        'last_name': student.last_name
                    },
                    'package_name': '',
                    'sessions_count': package.total_sessions,
                    'status': package.status,
                    'purchase_date': package.purchase_date.isoformat()
                }
                
                # Get package name from pricing plan
                if package.package_type == 'coach' and package.pricing_plan_id:
                    pricing_plan = PricingPlan.query.get(package.pricing_plan_id)
                    if pricing_plan:
                        package_data['package_name'] = pricing_plan.name
                
                elif package.package_type == 'academy' and package.academy_pricing_plan_id:
                    academy_plan = AcademyPricingPlan.query.get(package.academy_pricing_plan_id)
                    if academy_plan:
                        package_data['package_name'] = academy_plan.name
                
                # Add coach info if available
                if package.coach_id:
                    coach_obj = Coach.query.get(package.coach_id)
                    if coach_obj and coach_obj.user:
                        package_data['coach'] = {
                            'first_name': coach_obj.user.first_name,
                            'last_name': coach_obj.user.last_name
                        }
                
                recent_packages.append(package_data)
            
            # Add data to result
            result['academy_coaches'] = academy_coaches
            result['recent_packages'] = recent_packages
    
    return jsonify(result)

@bp.route('/coach/pricing-plans')
@login_required
def get_pricing_plans():
    """API endpoint to get coach pricing plans"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    plans = PricingPlan.query.filter_by(coach_id=coach.id).all()
    
    result = []
    for plan in plans:
        plan_data = {
            'id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'discount_type': plan.discount_type,
            'is_active': plan.is_active,
            'sessions_required': plan.sessions_required,
            'percentage_discount': plan.percentage_discount,
            'fixed_discount': plan.fixed_discount,
            'first_time_only': plan.first_time_only,
            'valid_from': plan.valid_from.isoformat() if plan.valid_from else None,
            'valid_to': plan.valid_to.isoformat() if plan.valid_to else None
        }
        result.append(plan_data)
    
    return jsonify(result)

@bp.route('/coach/pricing-plans/<int:coach_id>')
def get_pricing_plans_by_coachid(coach_id):
    """API endpoint to get coach pricing plans"""
    
    coach = Coach.query.filter_by(id=coach_id).first_or_404()
    
    plans = PricingPlan.query.filter_by(coach_id=coach.id).all()
    
    result = []
    for plan in plans:
        plan_data = {
            'id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'discount_type': plan.discount_type,
            'is_active': plan.is_active,
            'sessions_required': plan.sessions_required,
            'percentage_discount': plan.percentage_discount,
            'fixed_discount': plan.fixed_discount,
            'first_time_only': plan.first_time_only,
            'valid_from': plan.valid_from.isoformat() if plan.valid_from else None,
            'valid_to': plan.valid_to.isoformat() if plan.valid_to else None
        }
        result.append(plan_data)
    
    return jsonify(result)

@bp.route('/coach/pricing-plans/add', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def add_pricing_plan():
    """API endpoint to add a pricing plan"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Create new pricing plan
    plan = PricingPlan(
        coach_id=coach.id,
        name=data.get('name'),
        description=data.get('description'),
        discount_type=data.get('discount_type'),
        is_active=data.get('is_active', True)
    )
    
    # Set specific fields based on discount type
    if data.get('discount_type') == 'first_time':
        plan.first_time_only = True
    
    if data.get('discount_type') == 'package':
        plan.sessions_required = data.get('sessions_required')
    
    if data.get('valid_from') and data.get('valid_to'):
        plan.valid_from = datetime.fromisoformat(data.get('valid_from'))
        plan.valid_to = datetime.fromisoformat(data.get('valid_to'))
    
    # Set discount values
    if data.get('percentage_discount'):
        plan.percentage_discount = float(data.get('percentage_discount'))
    elif data.get('fixed_discount'):
        plan.fixed_discount = float(data.get('fixed_discount'))
    
    try:
        db.session.add(plan)
        db.session.commit()
        return jsonify({
            'success': True,
            'id': plan.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/pricing-plans/delete', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def delete_pricing_plan():
    """API endpoint to delete a pricing plan"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    plan_id = data.get('plan_id')
    
    plan = PricingPlan.query.filter_by(id=plan_id, coach_id=Coach.query.filter_by(user_id=current_user.id).first().id).first_or_404()
    
    try:
        db.session.delete(plan)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/availability')
@login_required
def get_availability():
    """API endpoint to get coach availability"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get availability for future dates
    availabilities = Availability.query.filter(
        Availability.coach_id == coach.id,
        Availability.date >= datetime.utcnow().date()
    ).order_by(Availability.date, Availability.start_time).all()
    
    result = []
    for availability in availabilities:
        result.append({
            'id': availability.id,
            'court_id': availability.court_id,
            'court': {
                'id': availability.court.id,
                'name': availability.court.name
            },
            'date': availability.date.isoformat(),
            'start_time': availability.start_time.strftime('%H:%M:%S'),
            'end_time': availability.end_time.strftime('%H:%M:%S'),
            'is_booked': availability.is_booked
        })
    
    return jsonify(result)

@bp.route('/coach/availability/add', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def add_availability():
    """API endpoint to add availability"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Validate the data
    if not all(key in data for key in ['court_id', 'date', 'start_time', 'end_time']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Parse date and times
        date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        # Check if date is in the future
        if date_obj < datetime.utcnow().date():
            return jsonify({'error': 'Cannot add availability for past dates'}), 400
        
        # Check if end time is after start time
        if start_time >= end_time:
            return jsonify({'error': 'End time must be after start time'}), 400
        
        # Create availability record
        availability = Availability(
            coach_id=coach.id,
            court_id=data['court_id'],
            date=date_obj,
            start_time=start_time,
            end_time=end_time,
            is_booked=False,
            student_books_court=data.get('student_books_court', True)  # New field
        )
        
        db.session.add(availability)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'id': availability.id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/availability/delete', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def delete_availability():
    """API endpoint to delete availability"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    availability_id = data.get('availability_id')
    
    print( Availability.query.filter_by(
        id=availability_id
    ).first())
    availability = Availability.query.filter_by(
        id=availability_id, 
        coach_id=Coach.query.filter_by(user_id=current_user.id).first().id
    ).first_or_404()
    
    # Check if it's booked
    if availability.is_booked:
        return jsonify({'error': 'Cannot delete a booked availability'}), 400
    
    try:
        db.session.delete(availability)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/availability/add-bulk', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def add_bulk_availability():
    """API endpoint to add multiple availability slots at once"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    slots = data.get('slots', [])
    
    if not slots:
        return jsonify({'error': 'No slots provided'}), 400
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    created_slots = []
    errors = []
    
    # Start a transaction
    try:
        for slot_data in slots:
            try:
                # Parse date and times
                date_obj = datetime.strptime(slot_data['date'], '%Y-%m-%d').date()
                start_time = datetime.strptime(slot_data['start_time'], '%H:%M').time()
                end_time = datetime.strptime(slot_data['end_time'], '%H:%M').time()
                
                # Create availability record
                availability = Availability(
                    coach_id=coach.id,
                    court_id=slot_data['court_id'],
                    date=date_obj,
                    start_time=start_time,
                    end_time=end_time,
                    is_booked=False,
                    student_books_court=slot_data.get('student_books_court', True)  # New field
                )
                
                db.session.add(availability)
                created_slots.append(availability)
            except Exception as e:
                errors.append(f"Error creating slot {slot_data['date']} {slot_data['start_time']}-{slot_data['end_time']}: {str(e)}")
        
        # Only commit if there were no errors
        if not errors:
            db.session.commit()
            return jsonify({
                'success': True,
                'created_count': len(created_slots)
            })
        else:
            # Rollback if there were any errors
            db.session.rollback()
            return jsonify({
                'error': 'Some slots could not be created',
                'errors': errors
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add these routes to app/routes/api.py

@bp.route('/coach/availability/templates', methods=['GET'])
@login_required
def get_availability_templates():
    """API endpoint to get a coach's saved availability templates"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    templates = AvailabilityTemplate.query.filter_by(coach_id=coach.id).order_by(AvailabilityTemplate.created_at.desc()).all()
    
    result = []
    for template in templates:
        result.append({
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'settings': template.settings,
            'created_at': template.created_at.isoformat()
        })
    
    return jsonify(result)

@bp.route('/coach/availability/templates/save', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def save_availability_template():
    """API endpoint to save an availability template"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Validate required fields
    if not all(k in data for k in ['name', 'settings']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate settings
    settings = data.get('settings')
    required_settings = ['days', 'courts', 'start_time', 'end_time', 'duration']
    
    if not all(k in settings for k in required_settings):
        return jsonify({'error': 'Missing required settings'}), 400
    
    # Create template
    template = AvailabilityTemplate(
        coach_id=coach.id,
        name=data.get('name'),
        description=data.get('description'),
        settings=settings
    )
    
    try:
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'id': template.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/availability/templates/apply', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def apply_availability_template():
    """API endpoint to apply a template to create availability slots"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Validate required fields
    if not all(k in data for k in ['template_id', 'start_date', 'end_date']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get template
    template = AvailabilityTemplate.query.filter_by(
        id=data.get('template_id'),
        coach_id=coach.id
    ).first_or_404()
    
    # Parse dates
    try:
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    if start_date > end_date:
        return jsonify({'error': 'Start date must be before or equal to end date'}), 400
    
    if start_date < datetime.utcnow().date():
        return jsonify({'error': 'Start date cannot be in the past'}), 400
    
    # Extract template settings
    settings = template.settings
    selected_days = settings.get('days', [])
    courts = settings.get('courts', [])
    start_time = settings.get('start_time')
    end_time = settings.get('end_time')
    duration_minutes = settings.get('duration')
    
    # Get increment (if stored in settings, otherwise default to duration)
    increment = settings.get('increment')
    if increment == 'duration':
        increment = duration_minutes
    else:
        increment = int(increment)
    
    created_slots = []
    errors = []
    
    # Start transaction
    try:
        # For each day in the date range
        current_date = start_date
        while current_date <= end_date:
            day_of_week = current_date.weekday()  # 0 = Monday, 6 = Sunday
            
            # Convert to the same format as stored in template
            if day_of_week == 6:  # Sunday in Python is 6, but in JS it's 0
                template_day = 0
            else:
                template_day = day_of_week + 1  # Adjust to match JS day numbering
            
            # Check if this day of week is selected in the template
            if template_day in selected_days:
                # For each court
                for court in courts:
                    court_id = court.get('id')
                    
                    # Parse start and end times
                    start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                    end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                    
                    # Calculate start and end times in minutes for easier processing
                    start_minutes = start_time_obj.hour * 60 + start_time_obj.minute
                    end_minutes = end_time_obj.hour * 60 + end_time_obj.minute
                    
                    # Create slots based on duration and increment
                    for time_minutes in range(start_minutes, end_minutes - duration_minutes + 1, increment):
                        slot_start_time = time(hour=time_minutes // 60, minute=time_minutes % 60)
                        slot_end_time = time(hour=(time_minutes + duration_minutes) // 60, minute=(time_minutes + duration_minutes) % 60)
                        
                        # Check for overlapping slots
                        overlapping = Availability.query.filter(
                            Availability.coach_id == coach.id,
                            Availability.court_id == court_id,
                            Availability.date == current_date,
                            Availability.start_time < slot_end_time,
                            Availability.end_time > slot_start_time
                        ).first()
                        
                        if overlapping:
                            errors.append(f"Overlapping slot: {current_date.isoformat()} {slot_start_time}-{slot_end_time}")
                            continue
                        
                        # Create availability record
                        availability = Availability(
                            coach_id=coach.id,
                            court_id=court_id,
                            date=current_date,
                            start_time=slot_start_time,
                            end_time=slot_end_time,
                            is_booked=False
                        )
                        
                        db.session.add(availability)
                        created_slots.append(availability)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Commit if any slots were created
        if created_slots:
            db.session.commit()
            
            return jsonify({
                'success': True,
                'created_count': len(created_slots),
                'errors': errors if errors else None
            })
        elif errors:
            return jsonify({
                'error': 'Could not create any slots',
                'errors': errors
            }), 400
        else:
            return jsonify({
                'error': 'No slots created. Check that template contains valid days within the selected date range.'
            }), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/availability/templates/delete', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def delete_availability_template():
    """API endpoint to delete an availability template"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    template_id = data.get('template_id')
    if not template_id:
        return jsonify({'error': 'Template ID is required'}), 400
    
    template = AvailabilityTemplate.query.filter_by(
        id=template_id,
        coach_id=coach.id
    ).first_or_404()
    
    try:
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/earnings/<period>')
@login_required
@coach_or_academy_manager_required
def get_earnings(period):
    """API endpoint to get coach earnings for specified period"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get total earnings
    total_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed'
    ).scalar() or 0
    
    # Current month earnings
    now = datetime.utcnow()
    this_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed',
        extract('year', Booking.date) == now.year,
        extract('month', Booking.date) == now.month
    ).scalar() or 0
    
    # Last month earnings
    last_month = now.replace(day=1) - timedelta(days=1)
    last_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed',
        extract('year', Booking.date) == last_month.year,
        extract('month', Booking.date) == last_month.month
    ).scalar() or 0
    
    # Get monthly earnings for chart
    monthly_data = {}
    months_to_fetch = 12
    if period.isdigit():
        months_to_fetch = int(period)
    
    for i in range(months_to_fetch-1, -1, -1):
        month_date = now.replace(day=1) - timedelta(days=i*30)
        month_key = month_date.strftime('%Y-%m')
        month_name = month_date.strftime('%B %Y')
        
        month_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach.id,
            Booking.status == 'completed',
            extract('year', Booking.date) == month_date.year,
            extract('month', Booking.date) == month_date.month
        ).scalar() or 0
        
        monthly_data[month_name] = float(month_earnings)
    
    # Get earnings by court
    court_earnings = {}
    courts = Court.query.join(CoachCourt).filter(CoachCourt.coach_id == coach.id).all()
    for court in courts:
        court_total = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach.id,
            Booking.court_id == court.id,
            Booking.status == 'completed'
        ).scalar() or 0
        
        if court_total > 0:
            court_earnings[court.name] = float(court_total)
    
    # Get earnings breakdown by discount type
    earnings_breakdown = {}
    # Regular sessions (no discount)
    regular_count = Booking.query.filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed',
        Booking.pricing_plan_id.is_(None)
    ).count()
    
    regular_amount = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed',
        Booking.pricing_plan_id.is_(None)
    ).scalar() or 0
    
    earnings_breakdown['regular'] = {
        'sessions': regular_count,
        'amount': float(regular_amount)
    }
    
    # Discounted sessions by type
    for discount_type in ['first_time', 'package', 'seasonal', 'custom']:
        discount_count = Booking.query.join(PricingPlan).filter(
            Booking.coach_id == coach.id,
            Booking.status == 'completed',
            PricingPlan.discount_type == discount_type
        ).count()
        
        discount_amount = db.session.query(func.sum(Booking.price)).join(PricingPlan).filter(
            Booking.coach_id == coach.id,
            Booking.status == 'completed',
            PricingPlan.discount_type == discount_type
        ).scalar() or 0
        
        if discount_count > 0:
            earnings_breakdown[discount_type] = {
                'sessions': discount_count,
                'amount': float(discount_amount)
            }
    
    response = {
        'total': float(total_earnings),
        'this_month': float(this_month_earnings),
        'last_month': float(last_month_earnings),
        'monthly': monthly_data,
        'by_court': court_earnings,
        'breakdown': earnings_breakdown
    }
    
    return jsonify(response)

@bp.route('/coach/bookings/<int:booking_id>')
@login_required
def get_coach_bookings_by_id(booking_id):
    """API endpoint to get coach bookings by id"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    
    # Define query based on status
    booking = Booking.query.filter(Booking.id == booking_id).first_or_404()
    

    # Get all payment proofs for these bookings in one query
    payment_proofs = {}
    if booking:
        proofs = PaymentProof.query.filter(
            PaymentProof.booking_id == booking_id
        ).all()

        # Organize proofs by booking_id and proof_type
        for proof in proofs:
            if proof.booking_id not in payment_proofs:
                payment_proofs[proof.booking_id] = {}
            payment_proofs[proof.booking_id][proof.proof_type] = proof.image_path
    
    
    # Format bookings data

    booking_payment_proofs = payment_proofs.get(booking.id, {})

    booking_data = {
        'id': booking.id,
        'student': {
            'id': booking.student_id,
            'first_name': booking.student.first_name,
            'last_name': booking.student.last_name,
            'email': booking.student.email
        },
        'date': booking.date.isoformat(),
        'start_time': booking.start_time.strftime('%H:%M:%S'),
        'end_time': booking.end_time.strftime('%H:%M:%S'),
        'price': float(booking.price),
        'status': booking.status,
        'court': {
            'id': booking.court_id,
            'name': booking.court.name
        },
        'venue_confirmed': booking.venue_confirmed,
        'court_booking_responsibility': booking.court_booking_responsibility,
        # Use the payment proofs from our lookup
        'payment_proof': booking_payment_proofs.get('coaching'),
        'court_booking_proof': booking_payment_proofs.get('court')
    }
        

    return jsonify(booking_data)


@bp.route('/coach/bookings/<status>')
@login_required
def get_coach_bookings(status):
    """API endpoint to get coach bookings by status"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Define query based on status
    query = Booking.query.filter(Booking.coach_id == coach.id)
    
    if status == 'upcoming':
        query = query.filter(
            Booking.status == 'upcoming',
            Booking.date >= datetime.utcnow().date()
        ).order_by(Booking.date, Booking.start_time)
    elif status == 'pending-venue':
        query = query.filter(
            Booking.status == 'upcoming',
            Booking.date >= datetime.utcnow().date(),
            Booking.venue_confirmed == False,
        ).order_by(Booking.date.asc())
    elif status == 'completed':
        query = query.filter(
            Booking.status == 'completed'
        ).order_by(Booking.date.desc())
    elif status == 'cancelled':
        query = query.filter(
            Booking.status == 'cancelled'
        ).order_by(Booking.date.desc())
    else:
        return jsonify({'error': 'Invalid status provided'}), 400
    
    bookings = query.all()

    # Get all booking IDs for efficient payment proof lookup
    booking_ids = [booking.id for booking in bookings]

    # Get all payment proofs for these bookings in one query
    payment_proofs = {}
    if booking_ids:
        proofs = PaymentProof.query.filter(
            PaymentProof.booking_id.in_(booking_ids)
        ).all()

        # Organize proofs by booking_id and proof_type
        for proof in proofs:
            if proof.booking_id not in payment_proofs:
                payment_proofs[proof.booking_id] = {}
            payment_proofs[proof.booking_id][proof.proof_type] = proof.image_path
    
    
    # Format bookings data
    result = []
    for booking in bookings:
        booking_payment_proofs = payment_proofs.get(booking.id, {})

        booking_data = {
            'id': booking.id,
            'student': {
                'id': booking.student_id,
                'first_name': booking.student.first_name,
                'last_name': booking.student.last_name,
                'email': booking.student.email
            },
            'date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M:%S'),
            'end_time': booking.end_time.strftime('%H:%M:%S'),
            'price': float(booking.price),
            'status': booking.status,
            'court': {
                'id': booking.court_id,
                'name': booking.court.name
            },
            'venue_confirmed': booking.venue_confirmed,
            'court_booking_responsibility': booking.court_booking_responsibility,
            # Use the payment proofs from our lookup
            'payment_proof': booking_payment_proofs.get('coaching'),
            'court_booking_proof': booking_payment_proofs.get('court')
        }
        
        # Add session log if it exists
        if booking.session_log:
            booking_data['session_log'] = {
                'id': booking.session_log.id,
                'title': booking.session_log.title,
                'notes': booking.session_log.notes,
                'coach_notes': booking.session_log.coach_notes,
                'created_at': booking.session_log.created_at.isoformat()
            }
        
        result.append(booking_data)
    
    return jsonify(result)

@bp.route('/coach/bookings/period')
@login_required
def get_bookings_by_period():
    """API endpoint to get coach bookings for a specific date range"""
    # Get date range from query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Validate date parameters
    if not start_date_str or not end_date_str:
        return jsonify({'error': 'Start date and end date are required'}), 400
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # For academy managers, allow filtering by coach_id
    coach_id = None
    if current_user.is_academy_manager:
        coach_id = request.args.get('coach_id', type=int)
        
        # If coach_id provided, verify it belongs to this academy manager
        if coach_id:
            # Get academies managed by this user
            academy_ids = [am.academy_id for am in AcademyManager.query.filter_by(user_id=current_user.id).all()]
            
            # Check if the coach belongs to any of these academies
            coach_in_academy = AcademyCoach.query.filter(
                AcademyCoach.coach_id == coach_id,
                AcademyCoach.academy_id.in_(academy_ids)
            ).first()
            
            if not coach_in_academy:
                return jsonify({'error': 'You do not have access to this coach'}), 403
    # Regular coach can only see their own bookings
    elif current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
        coach_id = coach.id
    else:
        return jsonify({'error': 'Access denied'}), 403
    
    # Define query based on parameters
    query = Booking.query
    
    # Filter by date range
    query = query.filter(
        Booking.date >= start_date,
        Booking.date <= end_date
    )
    
    # Filter by coach
    if coach_id:
        query = query.filter(Booking.coach_id == coach_id)
    elif current_user.is_academy_manager:
        # If no specific coach_id but user is academy manager, get all coaches from their academies
        academy_ids = [am.academy_id for am in AcademyManager.query.filter_by(user_id=current_user.id).all()]
        academy_coach_ids = [ac.coach_id for ac in AcademyCoach.query.filter(AcademyCoach.academy_id.in_(academy_ids)).all()]
        
        if academy_coach_ids:
            query = query.filter(Booking.coach_id.in_(academy_coach_ids))
        else:
            # No coaches found in this academy, return empty result
            return jsonify([])
    
    # Order by date and time
    query = query.order_by(Booking.date, Booking.start_time)
    
    # Execute query
    bookings = query.all()
    
    # Get all booking IDs for efficient payment proof lookup
    booking_ids = [booking.id for booking in bookings]
    
    # Get all payment proofs for these bookings in one query
    payment_proofs = {}
    if booking_ids:
        proofs = PaymentProof.query.filter(
            PaymentProof.booking_id.in_(booking_ids)
        ).all()
        
        # Organize proofs by booking_id and proof_type
        for proof in proofs:
            if proof.booking_id not in payment_proofs:
                payment_proofs[proof.booking_id] = {}
            payment_proofs[proof.booking_id][proof.proof_type] = proof.image_path
    
    # Format bookings data
    result = []
    for booking in bookings:
        # Get payment proofs for this booking
        booking_payment_proofs = payment_proofs.get(booking.id, {})
        
        booking_data = {
            'id': booking.id,
            'student': {
                'id': booking.student_id,
                'first_name': booking.student.first_name,
                'last_name': booking.student.last_name,
                'email': booking.student.email
            },
            'coach': {
                'id': booking.coach_id,
                'user': {
                    'first_name': booking.coach.user.first_name,
                    'last_name': booking.coach.user.last_name
                }
            },
            'date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M:%S'),
            'end_time': booking.end_time.strftime('%H:%M:%S'),
            'price': float(booking.price),
            'status': booking.status,
            'court': {
                'id': booking.court_id,
                'name': booking.court.name
            },
            'venue_confirmed': booking.venue_confirmed,
            'court_booking_responsibility': booking.court_booking_responsibility,
            # Use the payment proofs from our lookup
            'payment_proof': booking_payment_proofs.get('coaching'),
            'court_booking_proof': booking_payment_proofs.get('court')
        }
        
        # Add session log if it exists
        if hasattr(booking, 'session_log') and booking.session_log:
            booking_data['session_log'] = {
                'id': booking.session_log.id,
                'title': booking.session_log.title,
                'notes': booking.session_log.notes,
                'coach_notes': booking.session_log.coach_notes,
                'created_at': booking.session_log.created_at.isoformat()
            }
        
        result.append(booking_data)
    
    return jsonify(result)

@bp.route('/coach/sessions')
@login_required
def sessions():
    if not current_user.is_coach:
        flash('Access denied. You are not registered as a coach.')
        return redirect(url_for('main.index'))
    
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    # Get all completed bookings
    completed_bookings = Booking.query.filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed'
    ).order_by(Booking.date.desc()).all()
    
    # Get all upcoming bookings
    upcoming_bookings = Booking.query.filter(
        Booking.coach_id == coach.id,
        Booking.status == 'upcoming',
        Booking.date >= datetime.utcnow().date()
    ).order_by(Booking.date, Booking.start_time).all()
    
    return render_template(
        'coaches/sessions.html', 
        coach=coach, 
        completed_bookings=completed_bookings,
        upcoming_bookings=upcoming_bookings
    )

@bp.route('/coach/session/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def session_detail(booking_id):
    if not current_user.is_coach:
        flash('Access denied. You are not registered as a coach.')
        return redirect(url_for('main.index'))
    
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    # Get booking and verify it belongs to this coach
    booking = Booking.query.filter_by(id=booking_id, coach_id=coach.id).first_or_404()
    
    # Get or create session log
    session_log = SessionLog.query.filter_by(booking_id=booking.id).first()
    if not session_log and booking.status == 'completed':
        session_log = SessionLog(
            booking_id=booking.id,
            coach_id=coach.id,
            student_id=booking.student_id,
            title='Pickleball Session'
        )
        db.session.add(session_log)
        db.session.commit()
    
    form = SessionLogForm(obj=session_log) if session_log else None
    
    if form and form.validate_on_submit():
        session_log.title = form.title.data
        session_log.coach_notes = form.coach_notes.data
        session_log.notes = form.notes.data
        db.session.commit()
        
        flash('Session log updated successfully')
        return redirect(url_for('coaches.session_detail', booking_id=booking_id))
    
    return render_template(
        'coaches/session_detail.html', 
        coach=coach, 
        booking=booking, 
        session_log=session_log,
        form=form
    )


@bp.route('/coach/session-logs')
@login_required
def get_coach_session_logs():
    """API endpoint to get coach session logs"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    session_logs = SessionLog.query.filter_by(coach_id=coach.id).order_by(SessionLog.created_at.desc()).all()
    
    # Format session logs data
    result = []
    for log in session_logs:
        log_data = {
            'id': log.id,
            'title': log.title,
            'notes': log.notes,
            'coach_notes': log.coach_notes,
            'created_at': log.created_at.isoformat(),
            'updated_at': log.updated_at.isoformat(),
            'student': {
                'id': log.student_id,
                'first_name': log.student.first_name,
                'last_name': log.student.last_name
            },
            'booking': {
                'id': log.booking_id,
                'date': log.booking.date.isoformat(),
                'start_time': log.booking.start_time.strftime('%H:%M:%S'),
                'end_time': log.booking.end_time.strftime('%H:%M:%S'),
                'court': {
                    'id': log.booking.court_id,
                    'name': log.booking.court.name
                }
            }
        }
        
        result.append(log_data)
    
    return jsonify(result)

@bp.route('/coach/complete-session', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def api_complete_session():
    """API endpoint to mark a session as completed"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    booking = Booking.query.filter_by(
        id=booking_id,
        coach_id=coach.id,
        status='upcoming'
    ).first_or_404()
    
    # Mark as completed
    booking.status = 'completed'
    coach.sessions_completed += 1
    
    # Create session log if it doesn't exist
    if not SessionLog.query.filter_by(booking_id=booking.id).first():
        session_log = SessionLog(
            booking_id=booking.id,
            coach_id=coach.id,
            student_id=booking.student_id,
            title='Pickleball Session'
        )
        db.session.add(session_log)
    
    try:
        # Award Connect Points after the booking is successfully completed
        from app.models.connect_points import ConnectPoints
        points_transaction = ConnectPoints.award_booking_points(booking_id)
        
        # Get the number of points awarded
        points_awarded = points_transaction.points if points_transaction else 0
        
        return jsonify({
            'success': True,
            'connect_points_awarded': points_awarded
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# @bp.route('/coach/cancel-session', methods=['POST'])
# @login_required
# def api_cancel_session():
#     """API endpoint to cancel a session"""
#     if not current_user.is_coach:
#         return jsonify({'error': 'Not a coach account'}), 403
    
#     data = request.get_json()
#     booking_id = data.get('booking_id')
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
#     booking = Booking.query.filter_by(
#         id=booking_id,
#         coach_id=coach.id,
#         status='upcoming'
#     ).first_or_404()
    
#     # Mark as cancelled
#     booking.status = 'cancelled'
    
#     # Make availability available again
#     if booking.availability:
#         booking.availability.is_booked = False
    
#     try:
#         db.session.commit()
#         return jsonify({'success': True})
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500

@bp.route('/coach/cancel-session', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def cancel_session_with_reason():
    """Cancel a booking with reason"""
    data = request.get_json()
    
    if not data or 'booking_id' not in data:
        return jsonify({'error': 'Missing booking ID'}), 400
    
    booking_id = data.get('booking_id')
    reason = data.get('reason', 'Cancelled by coach')
    
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if coach is authorized
        coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
        if booking.coach_id != coach.id:
            return jsonify({'error': 'Unauthorized to cancel this booking'}), 403
        
        # Check if booking can be cancelled
        if booking.status != 'upcoming':
            return jsonify({'error': 'Cannot cancel a booking that is not upcoming'}), 400
        
        # Cancel the booking
        booking.status = 'cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_by_id = current_user.id
        booking.cancelled_at = datetime.utcnow()
        
        # Update availability
        if booking.availability_id:
            availability = Availability.query.get(booking.availability_id)
            if availability:
                availability.is_booked = False
        
        # Create notification for student
        from app.models.notification import Notification
        notification = Notification(
            user_id=booking.student_id,
            title='Booking Cancelled',
            message=f'Your booking on {booking.date.strftime("%b %d, %Y")} at {booking.start_time.strftime("%I:%M %p")} has been cancelled. Reason: {reason}',
            notification_type='cancellation',
            related_id=booking.id
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Booking cancelled successfully'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling booking: {str(e)}")
        return jsonify({'error': 'Failed to cancel booking'}), 500

@bp.route('/coach/complete-session/<int:booking_id>', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def complete_session(booking_id):
    if not current_user.is_coach:
        flash('Access denied. You are not registered as a coach.')
        return redirect(url_for('main.index'))
    
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    # Get booking and verify it belongs to this coach
    booking = Booking.query.filter_by(id=booking_id, coach_id=coach.id, status='upcoming').first_or_404()
    
    # Update booking as complete and update states such as points, no. of sessions etc.
    booking.mark_completed()
    
    db.session.commit()
    
    flash('Session marked as completed')
    return redirect(url_for('coaches.session_detail', booking_id=booking_id))


@bp.route('/courts')
def get_courts():
    """API endpoint to get all courts"""
    courts = Court.query.all()
    courts_data = [
        {
            'id': court.id, 
            'name': court.name, 
            'address': court.address, 
            'city': court.city, 
            'state': court.state, 
            'zip_code': court.zip_code,
            'booking_link': court.booking_link
        } 
        for court in courts
    ]
    return jsonify(courts_data)

@bp.route('/coach/update-profile-picture', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def update_profile_picture():
    """Update the coach's profile picture"""
    try:
        if 'profile_picture' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Delete old profile picture if exists
        if current_user.profile_picture:
            delete_file(current_user.profile_picture)
        
        # Save new profile picture
        profile_pic_path = save_uploaded_file(
            file, 
            current_app.config['PROFILE_PICS_DIR'], 
            f"user_{current_user.id}"
        )
        
        if not profile_pic_path:
            return jsonify({'success': False, 'message': 'Failed to save profile picture'}), 400
        
        # Update user record
        current_user.profile_picture = profile_pic_path
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Profile picture updated successfully',
            'profile_picture_url': profile_pic_path
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@bp.route('/coach/remove-profile-picture', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def remove_profile_picture():
    """Remove the coach's profile picture"""
    if current_user.profile_picture:
        # Delete the file
        delete_file(current_user.profile_picture)
        
        # Update user record
        current_user.profile_picture = None
        db.session.commit()
    
    return jsonify({'success': True, 'message': 'Profile picture removed successfully'})

@bp.route('/coach/showcase-images', methods=['GET'])
@login_required
def get_showcase_images():
    """Get a coach's showcase images"""
    # Get the coach record
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    if not coach:
        return jsonify({'success': False, 'message': 'Coach record not found'}), 404
    
    # Get showcase images
    images = []
    for image in coach.showcase_images:
        images.append({
            'id': image.id,
            'url': f"/static/{image.image_path}",
            'created_at': image.created_at.isoformat()
        })
    
    return jsonify({'success': True, 'images': images})

@bp.route('/coach/session-logs/<int:log_id>')
@login_required
def get_session_log_details(log_id):
    """API endpoint to get details of a specific session log"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    log = SessionLog.query.filter_by(
        id=log_id,
        coach_id=coach.id
    ).first_or_404()
    
    log_data = {
        'id': log.id,
        'title': log.title,
        'notes': log.notes,
        'coach_notes': log.coach_notes,
        'created_at': log.created_at.isoformat(),
        'updated_at': log.updated_at.isoformat(),
        'student': {
            'id': log.student_id,
            'first_name': log.student.first_name,
            'last_name': log.student.last_name
        },
        'booking': {
            'id': log.booking_id,
            'date': log.booking.date.isoformat(),
            'start_time': log.booking.start_time.strftime('%H:%M:%S'),
            'end_time': log.booking.end_time.strftime('%H:%M:%S'),
            'court': {
                'id': log.booking.court_id,
                'name': log.booking.court.name
            }
        }
    }
    
    return jsonify(log_data)

@bp.route('/coach/session-logs/update', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def update_session_log():
    """API endpoint to create or update a session log"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    log_id = data.get('log_id')
    booking_id = data.get('booking_id')

    if log_id:
        log_id = int(log_id)
    if booking_id:
        booking_id = int(booking_id)

    print(booking_id)
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    log = None
    if log_id or booking_id:
        # Try to get existing log
        log = SessionLog.query.filter_by(
            booking_id=booking_id
        ).first()
    
    if log:
        # Update existing log
        log.title = data.get('title', log.title)
        log.notes = data.get('notes', log.notes)
        log.coach_notes = data.get('coach_notes', log.coach_notes)
        log.updated_at = datetime.utcnow()
    else:
        # Create new log
        if not booking_id:
            return jsonify({'error': 'Booking ID is required for new session logs'}), 400
        
        # Get booking to verify it belongs to this coach and get student ID
        booking = Booking.query.filter_by(
            id=booking_id,
            coach_id=coach.id
        ).first_or_404()
        
        log = SessionLog(
            booking_id=booking_id,
            coach_id=coach.id,
            student_id=booking.student_id,
            title=data.get('title', 'Pickleball Session'),
            notes=data.get('notes', ''),
            coach_notes=data.get('coach_notes', ''),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(log)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'log_id': log.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/courts')
@login_required
def get_coach_courts():
    """API endpoint to get courts for the current coach"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get coach courts
    coach_courts = CoachCourt.query.filter_by(coach_id=coach.id).all()
    court_ids = [cc.court_id for cc in coach_courts]
    
    courts = Court.query.filter(Court.id.in_(court_ids)).all()
    
    # Format courts data
    result = []
    for court in courts:
        result.append({
            'id': court.id,
            'name': court.name,
            'address': court.address,
            'city': court.city,
            'state': court.state,
            'zip_code': court.zip_code
        })
    
    return jsonify(result)

@bp.route('/coach/courts/add', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def api_add_court():
    """API endpoint to add a court to a coach's profile"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    court_id = data.get('court_id')
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Check if association already exists
    exists = CoachCourt.query.filter_by(coach_id=coach.id, court_id=court_id).first()
    if exists:
        return jsonify({'error': 'Court already associated with this coach'}), 400
    
    # Create new association
    coach_court = CoachCourt(coach_id=coach.id, court_id=court_id)
    
    try:
        db.session.add(coach_court)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/courts/remove', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def api_remove_court():
    """API endpoint to remove a court from a coach's profile"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    court_id = data.get('court_id')
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Find and delete the association
    coach_court = CoachCourt.query.filter_by(coach_id=coach.id, court_id=court_id).first_or_404()
    
    try:
        db.session.delete(coach_court)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/profile', methods=['PUT'])
@login_required
def update_coach_profile():
    """API endpoint to update a coach's profile"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Update user data
    user_data = data.get('user', {})
    current_user.first_name = user_data.get('first_name', current_user.first_name)
    current_user.last_name = user_data.get('last_name', current_user.last_name)
    current_user.email = user_data.get('email', current_user.email)
    current_user.gender = user_data.get('gender', current_user.gender)
    current_user.location = user_data.get('location', current_user.location)
    current_user.dupr_rating = user_data.get('dupr_rating', current_user.dupr_rating)
    
    # Update coach data
    coach_data = data.get('coach', {})
    coach.hourly_rate = coach_data.get('hourly_rate', coach.hourly_rate)
    coach.years_experience = coach_data.get('years_experience', coach.years_experience)
    coach.specialties = coach_data.get('specialties', coach.specialties)
    coach.biography = coach_data.get('biography', coach.biography)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'message': 'File too large. Maximum size is 16MB.'
    }), 413

@bp.errorhandler(400)
@bp.errorhandler(404)
@bp.errorhandler(500)
def handle_api_error(error):
    """Return JSON instead of HTML for API errors"""
    if request.path.startswith('/api/'):
        return jsonify({
            'error': str(error),
            'message': error.description if hasattr(error, 'description') else str(error)
        }), error.code
    return error

@bp.route('/coach/update-showcase-images', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def update_showcase_images():
    """Update a coach's showcase images"""
    # Get coach record
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    if not coach:
        return jsonify({'success': False, 'message': 'Coach record not found'}), 404
    
    try:
        # Handle deleted images
        if 'deleted_image_ids' in request.form:
            deleted_ids = json.loads(request.form['deleted_image_ids'])
            for image_id in deleted_ids:
                image = CoachImage.query.get(image_id)
                if image and image.coach_id == coach.id:
                    # Delete the file
                    delete_file(image.image_path)
                    # Delete the database record
                    db.session.delete(image)
        
        # Handle new images
        if 'new_images' in request.files:
            new_images = request.files.getlist('new_images')
            for file in new_images:
                if file and file.filename:
                    # Save the file
                    image_path = save_uploaded_file(
                        file, 
                        current_app.config['SHOWCASE_IMAGES_DIR'], 
                        f"coach_{coach.id}"
                    )
                    
                    if image_path:
                        # Create a new image record
                        coach_image = CoachImage(
                            coach_id=coach.id,
                            image_path=image_path
                        )
                        db.session.add(coach_image)
        
        # Commit changes
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Showcase images updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating images: {str(e)}'}), 500


@bp.route('/coach/confirm-venue', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def confirm_venue():
    """API endpoint for a coach to confirm venue booking"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    if not booking_id:
        return jsonify({'error': 'Booking ID is required'}), 400
    
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    # Get booking and verify it belongs to this coach
    booking = Booking.query.filter_by(
        id=booking_id, 
        coach_id=coach.id,
        status='upcoming'
    ).first_or_404()
    
    # Update booking status to 'venue_confirmed'
    booking.venue_confirmed = True
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/defer-booking', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def defer_booking():
    """API endpoint for a coach to reschedule a booking"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ['booking_id', 'date', 'start_time', 'end_time', 'court_id']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    # Get booking and verify it belongs to this coach
    booking = Booking.query.filter_by(
        id=data.get('booking_id'), 
        coach_id=coach.id,
        status='upcoming'
    ).first_or_404()
    
    try:
        # Parse date and times
        new_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        new_start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
        new_end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
        new_court_id = data.get('court_id')
        reason = data.get('reason', '')
        
        # Check if date is in the future
        if new_date < datetime.utcnow().date():
            return jsonify({'error': 'Cannot reschedule to a past date'}), 400
        
        # Check if end time is after start time
        if new_start_time >= new_end_time:
            return jsonify({'error': 'End time must be after start time'}), 400
        
        # Store original values for notification
        original_date = booking.date
        original_start_time = booking.start_time
        original_court_id = booking.court_id
        
        # Update booking with new schedule
        booking.date = new_date
        booking.start_time = new_start_time
        booking.end_time = new_end_time
        booking.court_id = new_court_id
        booking.venue_confirmed = False  # Reset venue confirmation
        
        # Add reschedule history if needed
        # This would be a good addition to track booking changes
        
        notification = Notification(
            user_id=booking.student_id,
            title="Booking rescheduled",
            message=f"Your booking has been rescheduled to {booking.date.strftime('%Y-%m-%d')} at {booking.start_time.strftime('%I:%M %p')}",
            notification_type="reschedule",
            related_id=booking.id
        )
        db.session.add(notification)

        #send_booking_rescheduled_notification(booking, original_date, original_start_time, original_court_id)
        
        db.session.commit()
        
        # Here you would typically send an email notification to the student
        # about the rescheduled session
        
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': f'Invalid date or time format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# @bp.route('/coach/payment-info', methods=['PUT'])
# @login_required
# def update_payment_info():
#     """API endpoint to update coach payment information"""
#     if not current_user.is_coach:
#         return jsonify({'error': 'Not a coach account'}), 403
    
#     data = request.get_json()
#     coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
#     # Update payment info
#     payment_info = {
#         'bank_name': data.get('bank_name'),
#         'account_name': data.get('account_name'),
#         'account_number': data.get('account_number'),
#         'qr_code_url': data.get('qr_code_url')
#     }
    
#     coach.payment_info = payment_info
    
#     # Update court booking instructions if provided
#     if 'court_booking_instructions' in data:
#         payment_info['court_booking_instructions'] = data.get('court_booking_instructions')
    
#     try:
#         db.session.commit()
#         return jsonify({'success': True})
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500

@bp.route('/coach/upload-qr-code', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def upload_qr_code():
    """API endpoint to upload QR code payment image"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    try:
        if 'qr_code' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['qr_code']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Save QR code image
        from app.utils.file_utils import save_uploaded_file
        
        qr_path = save_uploaded_file(
            file, 
            current_app.config['PAYMENT_QR_DIR'], 
            f"qr_code_coach_{current_user.id}"
        )
        
        if not qr_path:
            return jsonify({'success': False, 'message': 'Failed to save QR code'}), 400
        
        # Update coach payment info
        coach = Coach.query.filter_by(user_id=current_user.id).first()
        
        if not coach.payment_info:
            coach.payment_info = {}
        
        coach.payment_info['qr_code_url'] = qr_path
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'QR code updated successfully',
            'qr_code_url': qr_path
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@bp.route('/coach/packages/pending', methods=['GET'])
@login_required
@coach_or_academy_manager_required
def get_pending_packages():
    """Get pending package approvals for the coach"""
    try:
        # For coach, get pending packages
        if current_user.is_coach:
            coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
            # Get all pending packages for this coach
            pending_packages = BookingPackage.query.filter(
                BookingPackage.coach_id == coach.id,
                BookingPackage.status == 'pending'
            ).order_by(BookingPackage.purchase_date).all()
            
        # For academy manager, get pending packages for the academy
        else:
            academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
            academy_ids = [am.academy_id for am in academies]
            
            # Get all pending packages for these academies
            pending_packages = BookingPackage.query.filter(
                BookingPackage.academy_id.in_(academy_ids),
                BookingPackage.status == 'pending'
            ).order_by(BookingPackage.purchase_date).all()
        
        # Format the response
        result = []
        for pkg in pending_packages:
            pricing_plan = None
            if pkg.pricing_plan_id:
                pricing_plan = PricingPlan.query.get(pkg.pricing_plan_id)
            elif pkg.academy_pricing_plan_id:
                pricing_plan = AcademyPricingPlan.query.get(pkg.academy_pricing_plan_id)
            
            student = User.query.get(pkg.student_id)
            
            # Check for payment proof
            payment_proof = PaymentProof.query.filter_by(
                package_id=pkg.id,
                proof_type='package'
            ).first()
            
            payment_proof_url = None
            if payment_proof:
                payment_proof_url = payment_proof.image_path
                if not payment_proof_url.startswith('/'):
                    payment_proof_url = '/' + payment_proof_url
            
            result.append({
                'id': pkg.id,
                'purchase_date': pkg.purchase_date.isoformat(),
                'total_sessions': pkg.total_sessions,
                'total_price': pkg.total_price,
                'status': pkg.status,
                'payment_proof_url': payment_proof_url,
                'student': {
                    'id': student.id,
                    'name': f"{student.first_name} {student.last_name}"
                },
                'pricing_plan': {
                    'id': pricing_plan.id if pricing_plan else None,
                    'name': pricing_plan.name if pricing_plan else 'Custom Package'
                }
            })
        
        return jsonify(result)
    
    except Exception as e:
        current_app.logger.error(f"Error fetching pending packages: {str(e)}")
        return jsonify({'error': 'Failed to fetch pending packages'}), 500

@bp.route('/coach/packages/update-status', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def update_package_status():
    """API endpoint for coaches to approve/reject packages"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ['package_id', 'status']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    package_id = data['package_id']
    new_status = data['status']
    
    if new_status not in ['active', 'rejected']:
        return jsonify({'error': 'Invalid status value'}), 400
    
    # Get the package and verify it belongs to this coach
    package = BookingPackage.query.filter_by(
        id=package_id,
        coach_id=coach.id,
        status='pending'
    ).first_or_404()
    
    # Update package status
    package.status = new_status
    
    # If approved, set activation date (you might want to add this field)
    if new_status == 'active':
        package.activated_at = datetime.utcnow()
    
    # If rejected, add rejection reason
    if new_status == 'rejected' and 'reason' in data:
        package.rejection_reason = data['reason']
    
    # Create notification for student
    student = User.query.get(package.student_id)
    
    notification = Notification(
        user_id=package.student_id,
        title=f"Package {new_status.title()}",
        message=f"Your package purchase has been {new_status}.",
        notification_type="package_status",
        related_id=package.id
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'package_id': package.id,
        'status': new_status
    })


@bp.route('/upload-payment-proof/<int:booking_id>', methods=['POST'])
@login_required
def upload_payment_proof(booking_id):
    """API endpoint for users to upload payment proof"""
    user_type = 'student'
    if current_user.is_coach:
        user_type = 'coach'

    # Get booking and verify it belongs to this student
    booking = Booking.query.filter_by(
        id=booking_id,
        student_id=current_user.id
    ).first_or_404()
    
    # Check if proof type is provided
    proof_type = request.form.get('proof_type')
    if proof_type not in ['coaching', 'court']:
        return jsonify({'error': 'Invalid proof type'}), 400
    
    # Check if file is provided
    if 'proof_image' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['proof_image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save the image
    try:
        from app.utils.file_utils import save_uploaded_file
        
        # Create directory path for payment proofs
        import os
        proof_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payment_proofs')
        os.makedirs(proof_dir, exist_ok=True)
        
        # Save file with unique name
        filename = f"booking_{booking_id}_{proof_type}_{int(datetime.utcnow().timestamp())}"
        image_path = save_uploaded_file(file, proof_dir, filename)
        
        if not image_path:
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Create payment proof record
        proof = PaymentProof(
            booking_id=booking_id,
            image_path=image_path,
            proof_type=proof_type,
            status='pending' if not current_user.is_coach else 'approved'
        )
        
        db.session.add(proof)
        
        # Update booking status
        if proof_type == 'coaching':
            booking.coaching_payment_status = 'uploaded' 
        elif proof_type == 'court':
            booking.court_payment_status = 'uploaded' if not current_user.is_coach else 'approved'
        
        db.session.commit()
        
        # Create notification for coach
        from app.models.notification import Notification
        
        if not current_user.is_coach:
            notification = Notification(
                user_id=booking.coach.user_id,
                title=f"Payment proof uploaded",
                message=f"Student has uploaded {proof_type} payment proof for booking on {booking.date.strftime('%Y-%m-%d')}",
                notification_type='payment_proof',
                related_id=booking.id
            )
        
        db.session.add(notification)
        db.session.commit()
        
        # Send email notification
        from app.utils.email import send_coach_payment_proof_notification
        #send_coach_payment_proof_notification(booking, proof_type)
        
        return jsonify({
            'success': True,
            'message': f'{proof_type.capitalize()} payment proof uploaded successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/payment-proofs/<int:booking_id>')
@login_required
def get_payment_proofs(booking_id):
    """API endpoint for users to view payment proofs for a booking"""
    
    # Get booking and verify it belongs to this coach
    booking = Booking.query.filter_by(
        id=booking_id,
    ).first_or_404()
    
    # Get payment proofs
    proofs = PaymentProof.query.filter_by(booking_id=booking_id).all()
    
    result = []
    for proof in proofs:
        result.append({
            'id': proof.id,
            'proof_type': proof.proof_type,
            'status': proof.status,
            'image_url': url_for('static', filename=proof.image_path),
            'notes': proof.notes,
            'created_at': proof.created_at.isoformat()
        })
    
    return jsonify(result)

@bp.route('/coach/update-payment-status', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def update_payment_status():
    """API endpoint for coach to approve/reject payment proof"""
    if not current_user.is_coach:
        return jsonify({'error': 'Only coaches can update payment status'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    data = request.get_json()
    proof_id = data.get('proof_id')
    status = data.get('status')  # 'approved' or 'rejected'
    notes = data.get('notes', '')
    
    if not proof_id or status not in ['approved', 'rejected']:
        return jsonify({'error': 'Invalid parameters'}), 400
    
    # Get payment proof
    proof = PaymentProof.query.get_or_404(proof_id)
    
    # Verify booking belongs to this coach
    booking = Booking.query.get_or_404(proof.booking_id)
    if booking.coach_id != coach.id:
        return jsonify({'error': 'Payment proof does not belong to your booking'}), 403
    
    # Update proof status
    proof.status = status
    proof.notes = notes
    
    # Update booking status
    if proof.proof_type == 'coaching':
        booking.coaching_payment_status = status
    elif proof.proof_type == 'court':
        booking.court_payment_status = status
    
    db.session.commit()
    
    # Create notification for student
    from app.models.notification import Notification
    
    notification = Notification(
        user_id=booking.student_id,
        title=f"Payment proof {status}",
        message=f"Your {proof.proof_type} payment proof has been {status} by the coach",
        notification_type='payment_status',
        related_id=booking.id
    )
    
    if notes:
        notification.message += f": {notes}"
    
    db.session.add(notification)
    db.session.commit()
    
    # Send email notification
    from app.utils.email import send_student_payment_status_notification
    send_student_payment_status_notification(booking, proof.proof_type, status, notes)
    
    return jsonify({
        'success': True,
        'message': f'Payment proof {status}'
    })

# app/routes/api.py
@bp.route('/coach/tags')
@login_required
def get_coach_tags():
    """API endpoint to get coach's tags"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get coach's tags
    coach_tags = CoachTag.query.filter_by(coach_id=coach.id).all()
    
    result = []
    for ct in coach_tags:
        result.append({
            'id': ct.tag.id,
            'name': ct.tag.name
        })
    
    return jsonify(result)

@bp.route('/coach/tags/add', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def add_coach_tag():
    """API endpoint to add a tag to a coach's profile"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    tag_name = data.get('tag_name')
    
    if not tag_name:
        return jsonify({'error': 'Tag name is required'}), 400
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Find or create tag
    tag = Tag.query.filter_by(name=tag_name).first()
    if not tag:
        tag = Tag(name=tag_name)
        db.session.add(tag)
        db.session.flush()  # Get ID without committing
    
    # Check if coach already has this tag
    existing = CoachTag.query.filter_by(
        coach_id=coach.id,
        tag_id=tag.id
    ).first()
    
    if existing:
        return jsonify({'error': 'Tag already associated with your profile'}), 400
    
    # Create coach-tag association
    coach_tag = CoachTag(
        coach_id=coach.id,
        tag_id=tag.id
    )
    
    db.session.add(coach_tag)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'tag_id': tag.id,
        'tag_name': tag.name
    })

@bp.route('/coach/tags/remove', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def remove_coach_tag():
    """API endpoint to remove a tag from a coach's profile"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    tag_id = data.get('tag_id')
    
    if not tag_id:
        return jsonify({'error': 'Tag ID is required'}), 400
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Find coach-tag association
    coach_tag = CoachTag.query.filter_by(
        coach_id=coach.id,
        tag_id=tag_id
    ).first_or_404()
    
    db.session.delete(coach_tag)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/coach/students')
@login_required
def get_coach_students():
    """API endpoint to get all students who have bookings with this coach"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all students who have bookings with this coach
    # We'll use a subquery to get unique student IDs from bookings
    student_ids = db.session.query(Booking.student_id).filter(
        Booking.coach_id == coach.id
    ).distinct().all()
    
    student_ids = [sid[0] for sid in student_ids]
    
    if not student_ids:
        return jsonify([])
    
    # Get detailed student information
    students = User.query.filter(User.id.in_(student_ids)).all()
    
    # Format student data, including additional metrics
    result = []
    for student in students:
        # Count completed sessions
        completed_sessions = Booking.query.filter(
            Booking.student_id == student.id,
            Booking.coach_id == coach.id,
            Booking.status == 'completed'
        ).count()
        
        # Get next booking date if any
        next_booking = Booking.query.filter(
            Booking.student_id == student.id,
            Booking.coach_id == coach.id,
            Booking.status == 'upcoming',
            Booking.date >= datetime.utcnow().date()
        ).order_by(Booking.date, Booking.start_time).first()
        
        next_booking_date = next_booking.date.isoformat() if next_booking else None
        
        # Count active packages
        active_packages = BookingPackage.query.filter(
            BookingPackage.student_id == student.id,
            BookingPackage.status == 'active',
            db.or_(
                BookingPackage.coach_id == coach.id,
                BookingPackage.academy_id.in_(
                    db.session.query(AcademyCoach.academy_id).filter(
                        AcademyCoach.coach_id == coach.id,
                        AcademyCoach.is_active == True
                    )
                )
            )
        ).count()
        
        # Format student data
        student_data = {
            'id': student.id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'email': student.email,
            'phone': student.phone,
            'dupr_rating': student.dupr_rating,
            'profile_picture': student.profile_picture,
            'completed_sessions': completed_sessions,
            'next_booking_date': next_booking_date,
            'active_packages': active_packages,
            'availability_preferences': student.availability_preferences
        }
        
        result.append(student_data)
    
    return jsonify(result)

@bp.route('/coach/create-booking-for-student', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def create_booking_for_student():
    """API endpoint for coach to create a booking for a student using an existing package"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['student_id', 'package_id', 'court_id', 'date', 'start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Get student
        student = User.query.get_or_404(data['student_id'])
        
        # Get package
        package = BookingPackage.query.get_or_404(data['package_id'])
        
        # Verify package belongs to student and can be used with this coach
        if package.student_id != student.id:
            return jsonify({'error': 'Package does not belong to this student'}), 403
        
        if not package.can_use_for_coach(coach.id):
            return jsonify({'error': 'Package cannot be used with this coach'}), 403
        
        if package.sessions_booked >= package.total_sessions:
            return jsonify({'error': 'No sessions remaining in this package'}), 400
        
        if package.status != 'active':
            return jsonify({'error': 'Package is not active'}), 400
        
        # Parse date and times
        date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        # Check if date is in the future
        if date_obj < datetime.utcnow().date():
            return jsonify({'error': 'Cannot create booking for past dates'}), 400
        
        # Check if end time is after start time
        if start_time >= end_time:
            return jsonify({'error': 'End time must be after start time'}), 400
        
        # Check coach availability
        availability = Availability.query.filter(
            Availability.coach_id == coach.id,
            Availability.date == date_obj,
            Availability.start_time <= start_time,
            Availability.end_time >= end_time,
            Availability.is_booked == False
        ).first()
        
        # If no exact availability match, check if there's any availability that includes this time
        if not availability:
            return jsonify({'error': 'Coach is not available at this time'}), 400
        
        # Create booking
        # Calculate price (use hourly rate and any package discounts)
        hourly_rate = coach.hourly_rate
        
        # Calculate duration in hours
        start_datetime = datetime.combine(date_obj, start_time)
        end_datetime = datetime.combine(date_obj, end_time)
        duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
        
        base_price = hourly_rate * duration_hours
        
        # If package has discount, apply it
        discount_amount = 0
        discount_percentage = 0
        
        if package.pricing_plan_id:
            pricing_plan = PricingPlan.query.get(package.pricing_plan_id)
            if pricing_plan:
                if pricing_plan.percentage_discount:
                    discount_percentage = pricing_plan.percentage_discount
                    discount_amount = base_price * (discount_percentage / 100)
                elif pricing_plan.fixed_discount:
                    # Calculate proportional discount for this session
                    total_discount = pricing_plan.fixed_discount
                    per_session_discount = total_discount / pricing_plan.sessions_required
                    discount_amount = per_session_discount
                    discount_percentage = (discount_amount / base_price) * 100
        
        final_price = base_price - discount_amount
        
        # Determine court fee and coach fee components
        court_fee = 0  # Can be updated with actual court fee logic
        coach_fee = final_price - court_fee
        
        # Court booking responsibility
        court_booking_responsibility = 'coach'
        
        # Create booking record
        booking = Booking(
            student_id=student.id,
            coach_id=coach.id,
            court_id=data['court_id'],
            availability_id=availability.id,
            date=date_obj,
            start_time=start_time,
            end_time=end_time,
            base_price=base_price,
            price=final_price,
            court_fee=court_fee,
            coach_fee=coach_fee,
            status='upcoming',
            venue_confirmed=False,
            coaching_payment_required=False,  # Package covers payment
            coaching_payment_status='approved',
            court_payment_required=True,
            court_payment_status='pending',
            court_booking_responsibility=court_booking_responsibility,
            pricing_plan_id=package.pricing_plan_id,
            discount_amount=discount_amount,
            discount_percentage=discount_percentage
        )
        
        db.session.add(booking)
        
        # Mark availability as booked
        availability.is_booked = True
        
        # Update package sessions count
        package.sessions_booked += 1
        
        # Associate booking with package
        booking_assoc = booking_package_association.insert().values(
            package_id=package.id,
            booking_id=booking.id
        )
        db.session.execute(booking_assoc)
        
        # Create notification for student
        notification = Notification(
            user_id=student.id,
            title="New Booking Created",
            message=f"A new session has been scheduled for {date_obj.strftime('%Y-%m-%d')} at {start_time.strftime('%I:%M %p')}",
            notification_type="booking",
            related_id=booking.id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'booking_id': booking.id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/tags')
def get_all_tags():
    """API endpoint to get all available tags"""
    tags = Tag.query.all()
    
    result = []
    for tag in tags:
        result.append({
            'id': tag.id,
            'name': tag.name
        })
    
    return jsonify(result)

@bp.route('/academy/info', methods=['GET', 'PUT'])
@login_required
def academy_info():
    """Get and update academy information"""
    if not current_user.is_academy_manager:
        return jsonify({'error': 'Not an academy manager account'}), 403
    
    # Get academy ID from academy manager record
    academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first_or_404()
    academy = Academy.query.get_or_404(academy_manager.academy_id)
    
    if request.method == 'GET':
        # Format academy tags
        tags = [tag.name for tag in academy.tags] if academy.tags else []
        
        return jsonify({
            'id': academy.id,
            'name': academy.name,
            'description': academy.description,
            'website': academy.website,
            'logo': academy.logo_path,
            'private_url_code': academy.private_url_code,
            'tags': tags,
            'bank_name': academy.bank_name,
            'account_name': academy.account_name,
            'account_number': academy.account_number,
            'payment_reference': academy.payment_reference,
            'court_bank_name': academy.court_bank_name,
            'court_account_name': academy.court_account_name,
            'court_account_number': academy.court_account_number,
            'court_payment_reference': academy.court_payment_reference
        })
    else:  # PUT
        data = request.get_json()
        
        # Update academy information
        academy.name = data.get('name', academy.name)
        academy.description = data.get('description', academy.description)
        academy.website = data.get('website', academy.website)
        academy.private_url_code = data.get('private_url_code', academy.private_url_code)
        
        # Update academy tags if provided
        if 'tags' in data:
            # Clear existing tags
            academy.tags = []
            
            # Add new tags
            for tag_name in data['tags']:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                academy.tags.append(tag)
        
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@bp.route('/academy/coaches', methods=['GET'])
@login_required
def get_academy_coaches():
    """Get coaches for an academy"""
    if not current_user.is_academy_manager:
        return jsonify({'error': 'Not an academy manager account'}), 403
    
    # Get academy ID from academy manager record
    academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(academy_id=academy_manager.academy_id).all()
    
    result = []
    for ac in academy_coaches:
        coach = Coach.query.get(ac.coach_id)
        if not coach:
            continue
            
        user = User.query.get(coach.user_id)
        if not user:
            continue
            
        # Get average rating
        avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(
            CoachRating.coach_id == coach.id
        ).scalar() or 0
        
        coach_data = {
            'id': coach.id,
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'profile_picture': user.profile_picture,
            'dupr_rating': user.dupr_rating,
            'hourly_rate': coach.hourly_rate,
            'years_experience': coach.years_experience,
            'sessions_completed': coach.sessions_completed,
            'avg_rating': float(avg_rating),
            'academy_role': ac.role
        }
        
        result.append(coach_data)
    
    return jsonify(result)

@bp.route('/academy/analytics', methods=['GET'])
@login_required
def get_academy_analytics():
    """Get academy analytics"""
    if not current_user.is_academy_manager:
        return jsonify({'error': 'Not an academy manager account'}), 403
    
    # Get academy ID from academy manager record
    academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first_or_404()
    academy_id = academy_manager.academy_id
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(academy_id=academy_id).all()
    coach_ids = [ac.coach_id for ac in academy_coaches]
    
    # Get total sessions (completed bookings)
    total_sessions = Booking.query.filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed'
    ).count()
    
    # Get total students (unique students who have booked with academy coaches)
    total_students = db.session.query(func.count(func.distinct(Booking.student_id))).filter(
        Booking.coach_id.in_(coach_ids)
    ).scalar() or 0
    
    # Get total revenue
    total_revenue = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed'
    ).scalar() or 0
    
    # Get sessions by coach
    sessions_by_coach = {}
    for coach_id in coach_ids:
        coach = Coach.query.get(coach_id)
        if coach and coach.user:
            coach_name = f"{coach.user.first_name} {coach.user.last_name}"
            session_count = Booking.query.filter(
                Booking.coach_id == coach_id,
                Booking.status == 'completed'
            ).count()
            
            if session_count > 0:
                sessions_by_coach[coach_name] = session_count
    
    # Get revenue by month
    revenue_by_month = {}
    now = datetime.utcnow()
    
    for i in range(11, -1, -1):
        month_start = now.replace(day=1) - timedelta(days=i*30)
        month_key = month_start.strftime('%Y-%m')
        
        month_revenue = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id.in_(coach_ids),
            Booking.status == 'completed',
            extract('year', Booking.date) == month_start.year,
            extract('month', Booking.date) == month_start.month
        ).scalar() or 0
        
        revenue_by_month[month_key] = float(month_revenue)
    
    return jsonify({
        'total_sessions': total_sessions,
        'total_students': total_students,
        'total_revenue': float(total_revenue),
        'sessions_by_coach': sessions_by_coach,
        'revenue_by_month': revenue_by_month
    })

@bp.route('/academy/upload-logo', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def upload_academy_logo():
    """Upload academy logo"""
    if not current_user.is_academy_manager:
        return jsonify({'error': 'Not an academy manager account'}), 403
    
    try:
        if 'logo' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Get academy
        academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first_or_404()
        academy = Academy.query.get_or_404(academy_manager.academy_id)
        
        # Delete old logo if exists
        if academy.logo_path:
            delete_file(academy.logo_path)
        
        # Save new logo
        logo_path = save_uploaded_file(
            file, 
            current_app.config['ACADEMY_LOGOS_DIR'], 
            f"academy_{academy.id}"
        )
        
        if not logo_path:
            return jsonify({'success': False, 'message': 'Failed to save logo'}), 400
        
        # Update academy record
        academy.logo_path = logo_path
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Logo updated successfully',
            'logo_url': logo_path
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@bp.route('/academy/remove-logo', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def remove_academy_logo():
    """Remove academy logo"""
    if not current_user.is_academy_manager:
        return jsonify({'error': 'Not an academy manager account'}), 403
    
    # Get academy
    academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first_or_404()
    academy = Academy.query.get_or_404(academy_manager.academy_id)
    
    if academy.logo_path:
        # Delete the file
        delete_file(academy.logo_path)
        
        # Update academy record
        academy.logo_path = None
        db.session.commit()
    
    return jsonify({'success': True, 'message': 'Academy logo removed successfully'})

@bp.route('/academy/earnings', methods=['GET'])
@login_required
@coach_or_academy_manager_required
def get_academy_earnings():
    """Get academy earnings"""
    if not current_user.is_academy_manager:
        return jsonify({'error': 'Not an academy manager account'}), 403
    
    # Get academy ID from academy manager record
    academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first_or_404()
    academy_id = academy_manager.academy_id
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(academy_id=academy_id).all()
    coach_ids = [ac.coach_id for ac in academy_coaches]
    
    if not coach_ids:
        return jsonify({
            'total': 0,
            'monthly_average': 0,
            'this_month': 0,
            'last_month': 0,
            'monthly': {},
            'by_court': {},
            'breakdown': {}
        })
    
    # Get total earnings
    total_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed'
    ).scalar() or 0
    
    # Current month earnings
    now = datetime.utcnow()
    this_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed',
        extract('year', Booking.date) == now.year,
        extract('month', Booking.date) == now.month
    ).scalar() or 0
    
    # Last month earnings
    last_month = now.replace(day=1) - timedelta(days=1)
    last_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed',
        extract('year', Booking.date) == last_month.year,
        extract('month', Booking.date) == last_month.month
    ).scalar() or 0
    
    # Get monthly earnings for chart
    monthly_data = {}
    months_to_fetch = 12
    
    for i in range(months_to_fetch-1, -1, -1):
        month_date = now.replace(day=1) - timedelta(days=i*30)
        month_key = month_date.strftime('%Y-%m')
        month_name = month_date.strftime('%B %Y')
        
        month_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id.in_(coach_ids),
            Booking.status == 'completed',
            extract('year', Booking.date) == month_date.year,
            extract('month', Booking.date) == month_date.month
        ).scalar() or 0
        
        monthly_data[month_name] = float(month_earnings)
    
    # Get earnings by court
    court_earnings = {}
    courts = Court.query.all()
    for court in courts:
        court_total = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id.in_(coach_ids),
            Booking.court_id == court.id,
            Booking.status == 'completed'
        ).scalar() or 0
        
        if court_total > 0:
            court_earnings[court.name] = float(court_total)
    
    # Get earnings breakdown by discount type
    earnings_breakdown = {}
    
    # Regular sessions (no discount)
    regular_count = Booking.query.filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed',
        Booking.pricing_plan_id.is_(None)
    ).count()
    
    regular_amount = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed',
        Booking.pricing_plan_id.is_(None)
    ).scalar() or 0
    
    if regular_count > 0:
        earnings_breakdown['regular'] = {
            'sessions': regular_count,
            'amount': float(regular_amount)
        }
    
    # Discounted sessions by type
    for discount_type in ['first_time', 'package', 'seasonal', 'custom']:
        discount_count = Booking.query.join(PricingPlan).filter(
            Booking.coach_id.in_(coach_ids),
            Booking.status == 'completed',
            PricingPlan.discount_type == discount_type
        ).count()
        
        discount_amount = db.session.query(func.sum(Booking.price)).join(PricingPlan).filter(
            Booking.coach_id.in_(coach_ids),
            Booking.status == 'completed',
            PricingPlan.discount_type == discount_type
        ).scalar() or 0
        
        if discount_count > 0:
            earnings_breakdown[discount_type] = {
                'sessions': discount_count,
                'amount': float(discount_amount)
            }
    
    # Calculate monthly average
    months_with_earnings = sum(1 for e in monthly_data.values() if e > 0)
    monthly_average = total_earnings / months_with_earnings if months_with_earnings > 0 else 0
    
    return jsonify({
        'total': float(total_earnings),
        'monthly_average': float(monthly_average),
        'this_month': float(this_month_earnings),
        'last_month': float(last_month_earnings),
        'monthly': monthly_data,
        'by_court': court_earnings,
        'breakdown': earnings_breakdown
    })

@bp.route('/academy/earnings/breakdown/<period>', methods=['GET'])
@login_required
@coach_or_academy_manager_required
def get_academy_earnings_breakdown(period):
    """Get academy earnings breakdown by period"""
    if not current_user.is_academy_manager:
        return jsonify({'error': 'Not an academy manager account'}), 403
    
    # Get academy ID from academy manager record
    academy_manager = AcademyManager.query.filter_by(user_id=current_user.id).first_or_404()
    academy_id = academy_manager.academy_id
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(academy_id=academy_id).all()
    coach_ids = [ac.coach_id for ac in academy_coaches]
    
    if not coach_ids:
        return jsonify({'breakdown': {}})
    
    # Define date range based on period
    now = datetime.utcnow()
    start_date = None
    
    if period == 'this-month':
        start_date = now.replace(day=1)
    elif period == 'last-month':
        first_day_of_month = now.replace(day=1)
        start_date = first_day_of_month - timedelta(days=1)
        start_date = start_date.replace(day=1)
        # End date is the last day of last month
        end_date = first_day_of_month - timedelta(days=1)
    elif period == 'this-year':
        start_date = now.replace(month=1, day=1)
    elif period == 'all-time':
        # No date filter needed
        pass
    else:
        return jsonify({'error': 'Invalid period specified'}), 400
    
    # Get earnings breakdown by discount type
    breakdown = {}
    
    # Base query for completed bookings by academy coaches
    base_query = Booking.query.filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed'
    )
    
    # Apply date filter if needed
    if start_date:
        if period == 'last-month':
            base_query = base_query.filter(
                Booking.date >= start_date,
                Booking.date <= end_date
            )
        else:
            base_query = base_query.filter(Booking.date >= start_date)
    
    # Regular sessions (no discount)
    regular_count = base_query.filter(Booking.pricing_plan_id.is_(None)).count()
    
    regular_amount = db.session.query(func.sum(Booking.price)).filter(
        Booking.id.in_([b.id for b in base_query.filter(Booking.pricing_plan_id.is_(None)).all()])
    ).scalar() or 0
    
    breakdown['regular'] = {
        'sessions': regular_count,
        'amount': float(regular_amount)
    }
    
    # Discounted sessions by type
    for discount_type in ['first_time', 'package', 'seasonal', 'custom']:
        discount_bookings = base_query.join(PricingPlan).filter(
            PricingPlan.discount_type == discount_type
        ).all()
        
        discount_count = len(discount_bookings)
        
        discount_amount = db.session.query(func.sum(Booking.price)).filter(
            Booking.id.in_([b.id for b in discount_bookings])
        ).scalar() or 0
        
        breakdown[discount_type] = {
            'sessions': discount_count,
            'amount': float(discount_amount)
        }
    
    return jsonify({'breakdown': breakdown})

@bp.route('/coach/update-payment-details', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def update_payment_details():
    """Update coach payment details"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Update payment info
    payment_info = {
        'bank_name': data.get('bank_name'),
        'account_name': data.get('account_name'),
        'account_number': data.get('account_number'),
        'payment_reference': data.get('payment_reference')
    }
    
    # Update court payment details if provided
    if 'court_payment_details' in data:
        payment_info['court_payment_details'] = data.get('court_payment_details')
    
    coach.payment_info = payment_info

    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/default-booking-responsibility', methods=['GET'])
@login_required
def get_default_booking_responsibility():
    """Get default court booking responsibility"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    return jsonify({
        'default_responsibility': coach.default_court_booking_responsibility or 'student'
    })

@bp.route('/coach/update-default-booking-responsibility', methods=['POST'])
@login_required
def update_default_booking_responsibility():
    """Update default court booking responsibility"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    responsibility = data.get('default_responsibility')
    if responsibility not in ['coach', 'student']:
        return jsonify({'error': 'Invalid responsibility value'}), 400
    
    coach.default_court_booking_responsibility = responsibility
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/packages', methods=['GET'])
@login_required
def get_coach_packages():
    """Get coach packages"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get packages created by this coach
    packages = []
    
    # Get packages from PricingPlan with discount_type = 'package'
    pricing_plans = PricingPlan.query.filter_by(
        coach_id=coach.id,
        discount_type='package'
    ).all()
    
    for plan in pricing_plans:
        # Calculate effective price per session based on hourly rate and discount
        hourly_rate = coach.hourly_rate
        session_price = hourly_rate
        
        if plan.percentage_discount:
            discount = hourly_rate * (plan.percentage_discount / 100)
            session_price -= discount
        elif plan.fixed_discount:
            discount = plan.fixed_discount / plan.sessions_required
            session_price -= discount
        
        packages.append({
            'id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'sessions': plan.sessions_required,
            'price': session_price * plan.sessions_required,
            'validity_days': 90,  # Default validity period
            'is_active': plan.is_active,
            'created_at': plan.created_at.isoformat() if plan.created_at else None
        })
    
    return jsonify(packages)

@bp.route('/coach/packages/create', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def create_coach_package():
    """Create a new coach package"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Validate required fields
    if not all(key in data for key in ['name', 'sessions', 'price', 'validity_days', 'description']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Create package as a pricing plan with type 'package'
    sessions = int(data.get('sessions'))
    total_price = float(data.get('price'))
    hourly_rate = coach.hourly_rate
    
    # Calculate discount (either percentage or fixed amount)
    regular_price = hourly_rate * sessions
    discount = regular_price - total_price
    
    if discount <= 0:
        # No discount, use regular pricing
        plan = PricingPlan(
            coach_id=coach.id,
            name=data.get('name'),
            description=data.get('description'),
            discount_type='package',
            sessions_required=sessions,
            percentage_discount=0,
            fixed_discount=0,
            is_active=data.get('is_active', True)
        )
    else:
        # Apply discount as fixed amount
        plan = PricingPlan(
            coach_id=coach.id,
            name=data.get('name'),
            description=data.get('description'),
            discount_type='package',
            sessions_required=sessions,
            percentage_discount=0,
            fixed_discount=discount,
            is_active=data.get('is_active', True)
        )
    
    try:
        db.session.add(plan)
        db.session.commit()
        return jsonify({
            'success': True,
            'id': plan.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/packages/delete', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def delete_coach_package():
    """Delete a coach package"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    package_id = data.get('package_id')
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Find the package/pricing plan
    plan = PricingPlan.query.filter_by(
        id=package_id,
        coach_id=coach.id
    ).first_or_404()
    
    try:
        db.session.delete(plan)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/coach/packages/purchased', methods=['GET'])
@login_required
def get_purchased_packages():
    """Get purchased packages for a coach"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all packages purchased from this coach
    packages = BookingPackage.query.filter_by(coach_id=coach.id).all()
    
    result = []
    for package in packages:
        # Get student
        student = User.query.get(package.student_id)
        if not student:
            continue
        
        # Get pricing plan
        pricing_plan = None
        if package.pricing_plan_id:
            pricing_plan = PricingPlan.query.get(package.pricing_plan_id)
        
        # Get payment proof
        payment_proof = PaymentProof.query.filter_by(
            package_id=package.id,
            proof_type='package'
        ).first()
        
        package_data = {
            'id': package.id,
            'student': {
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'email': student.email
            },
            'pricing_plan': {
                'id': pricing_plan.id if pricing_plan else None,
                'name': pricing_plan.name if pricing_plan else 'Standard Package'
            },
            'total_sessions': package.total_sessions,
            'sessions_used': package.sessions_completed,
            'total_price': float(package.total_price),
            'purchase_date': package.purchase_date.isoformat(),
            'status': package.status,
            'expires_at': package.expires_at.isoformat() if package.expires_at else None
        }
        
        if payment_proof:
            package_data['payment_proof'] = {
                'id': payment_proof.id,
                'image_url': f"/static/{payment_proof.image_path}"
            }
        
        result.append(package_data)
    
    return jsonify(result)

@bp.route('/coach/packages/purchased/<int:package_id>', methods=['GET'])
@login_required
def get_purchased_packages_by_id(package_id):
    """Get purchased packages for a coach"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all packages purchased from this coach
    package = BookingPackage.query.filter_by(id=package_id).first_or_404()
    
    result = {}

    # Get student
    student = User.query.get(package.student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 403
    
    # Get pricing plan
    pricing_plan = None
    if package.pricing_plan_id:
        pricing_plan = PricingPlan.query.get(package.pricing_plan_id)
    
    # Get payment proof
    payment_proof = PaymentProof.query.filter_by(
        package_id=package.id,
        proof_type='package'
    ).first()
    
    package_data = {
        'id': package.id,
        'student': {
            'id': student.id,
            'name': f"{student.first_name} {student.last_name}",
            'email': student.email
        },
        'pricing_plan': {
            'id': pricing_plan.id if pricing_plan else None,
            'name': pricing_plan.name if pricing_plan else 'Standard Package'
        },
        'total_sessions': package.total_sessions,
        'sessions_used': package.sessions_completed,
        'total_price': float(package.total_price),
        'purchase_date': package.purchase_date.isoformat(),
        'status': package.status,
        'expires_at': package.expires_at.isoformat() if package.expires_at else None
    }
    
    if payment_proof:
        package_data['payment_proof'] = {
            'id': payment_proof.id,
            'image_url': f"/static/{payment_proof.image_path}"
        }
    
    result = package_data
    
    return jsonify(result)

@bp.route('/coach/packages/purchased/<int:package_id>/payment-proof', methods=['GET'])
@login_required
def get_purchased_packages_payment_proof(package_id):
    """Get purchased packages payment proof for a coach"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all packages purchased from this coach
    #package = BookingPackage.query.filter_by(pricing_plan_id=package_id).first_or_404()
    
    result = {}

        
    # Get payment proof
    payment_proof = PaymentProof.query.filter_by(
        package_id=package_id,
        proof_type='package'
    ).first()
    
    
    if payment_proof:
        result = {
            'id': payment_proof.id,
            'image_url': f"/static/uploads/{payment_proof.image_path}"
        }
        
    
    return jsonify(result)

@bp.route('/coach/packages/purchased/approve', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def approve_package_purchase():
    """Approve a package purchase"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    purchase_id = data.get('purchase_id')
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get the package
    package = BookingPackage.query.filter_by(
        id=purchase_id,
        coach_id=coach.id,
        status='pending'
    ).first_or_404()
    
    # Update status to active
    package.status = 'active'
    package.activated_at = datetime.utcnow()
    
    # Create notification for student
    notification = Notification(
        user_id=package.student_id,
        title="Package Approved",
        message=f"Your package purchase has been approved by the coach.",
        notification_type="package_status",
        related_id=package.id
    )
    
    db.session.add(notification)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'package_id': package.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# @bp.route('/coach/packages/purchased/reject', methods=['POST'])
# @login_required
# def reject_package_purchase():
#     """Reject a package purchase"""
#     if not current_user.is_coach:
#         return jsonify({'error': 'Not a coach account'}), 403
    
#     data = request.get_json()
#     purchase_id = data.get('purchase_id')
#     reason = data.get('reason', 'No reason provided')
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
#     # Get the package
#     package = BookingPackage.query.filter_by(
#         id=purchase_id,
#         coach_id=coach.id,
#         status='pending'
#     ).first_or_404()
    
#     # Update status to rejected
#     package.status = 'rejected'
#     package.rejection_reason = reason
    
#     # Create notification for student
#     notification = Notification(
#         user_id=package.student_id,
#         title="Package Rejected",
#         message=f"Your package purchase was rejected. Reason: {reason}",
#         notification_type="package_status",
#         related_id=package.id
#     )
    
#     db.session.add(notification)
    
#     try:
#         db.session.commit()
#         return jsonify({
#             'success': True,
#             'package_id': package.id
#         })
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500

@bp.route('/coach/packages/purchased/reject', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def reject_package_with_reason():
    """Reject a package purchase with reason"""
    data = request.get_json()
    
    if not data or 'purchase_id' not in data:
        return jsonify({'error': 'Missing purchase ID'}), 400
    
    purchase_id = data.get('purchase_id')
    reason = data.get('reason', 'Rejected by coach')
    
    try:
        package = BookingPackage.query.get_or_404(purchase_id)
        
        # Check authorization
        if current_user.is_coach:
            coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
            if package.coach_id != coach.id:
                return jsonify({'error': 'Unauthorized to reject this package'}), 403
        else:  # Academy manager
            academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
            academy_ids = [am.academy_id for am in academies]
            
            if package.academy_id not in academy_ids:
                return jsonify({'error': 'Unauthorized to reject this package'}), 403
        
        # Check if package can be rejected
        if package.status != 'pending':
            return jsonify({'error': 'Cannot reject a package that is not pending'}), 400
        
        # Reject the package
        package.status = 'rejected'
        package.rejection_reason = reason
        package.rejected_by_id = current_user.id
        package.rejected_at = datetime.utcnow()
        
        # Create notification for student
        notification = Notification(
            user_id=package.student_id,
            title='Package Purchase Rejected',
            message=f'Your package purchase "{package.pricing_plan.name if package.pricing_plan else "Custom Package"}" has been rejected. Reason: {reason}',
            notification_type='package_rejection',
            related_id=package.id
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Package rejected successfully'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting package: {str(e)}")
        return jsonify({'error': 'Failed to reject package'}), 500

@bp.route('/coach/upload-court-proof', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def upload_court_proof():
    """Upload court booking proof"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    if 'court_proof' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['court_proof']
    booking_id = request.form.get('booking_id')
    
    if not booking_id:
        return jsonify({'error': 'Booking ID is required'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Verify booking belongs to this coach
    booking = Booking.query.filter_by(
        id=booking_id,
        coach_id=coach.id
    ).first_or_404()
    
    try:
        # Create directory for proofs if it doesn't exist
        proofs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'booking_proofs')
        os.makedirs(proofs_dir, exist_ok=True)
        
        # Save the file with a unique name
        filename = f"court_proof_{booking_id}_{int(datetime.utcnow().timestamp())}"
        file_path = save_uploaded_file(file, proofs_dir, filename)
        
        if not file_path:
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Check if proof already exists
        existing_proof = PaymentProof.query.filter_by(
            booking_id=booking_id,
            proof_type='court'
        ).first()
        
        if existing_proof:
            # Update existing proof
            if existing_proof.image_path:
                delete_file(existing_proof.image_path)
            
            existing_proof.image_path = file_path
            existing_proof.status = 'approved'  # Auto-approve when coach uploads
        else:
            # Create new proof
            proof = PaymentProof(
                booking_id=booking_id,
                image_path=file_path,
                proof_type='court',
                status='approved'  # Auto-approve when coach uploads
            )
            db.session.add(proof)
        
        # Update booking status
        booking.court_payment_status = 'approved'
        
        # Create notification for student
        notification = Notification(
            user_id=booking.student_id,
            title="Court Booking Confirmed",
            message=f"Your coach has confirmed the court booking for your session on {booking.date.strftime('%Y-%m-%d')}",
            notification_type='court_booking',
            related_id=booking.id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Court booking proof uploaded successfully',
            'proof_url': file_path
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/support/request', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def submit_support_request():
    """Submit a support request"""
    data = request.get_json()
    subject = data.get('subject')
    message = data.get('message')
    
    if not subject or not message:
        return jsonify({'error': 'Subject and message are required'}), 400
    
    try:
        # Create support request record
        # This is a placeholder - you might want to create a SupportRequest model
        # For now, we'll just return success
        
        # Optionally, send an email to support team
        # send_support_email(current_user, subject, message)
        
        return jsonify({
            'success': True,
            'message': 'Your support request has been submitted.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/courts/update-instructions', methods=['POST'])
@login_required
@coach_or_academy_manager_required
def update_court_instructions():
    """Update court booking instructions"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    court_id = data.get('court_id')
    
    if not court_id:
        return jsonify({'error': 'Court ID is required'}), 400
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Verify coach is associated with this court
    coach_court = CoachCourt.query.filter_by(
        coach_id=coach.id,
        court_id=court_id
    ).first_or_404()
    
    # Update court booking instructions
    coach_court.booking_instructions = data.get('booking_instructions')
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/courts/<int:court_id>', methods=['GET'])
def get_court_details(court_id):
    """Get details for a specific court"""
    court = Court.query.get_or_404(court_id)
    
    result = {
        'id': court.id,
        'name': court.name,
        'address': court.address,
        'city': court.city,
        'state': court.state,
        'zip_code': court.zip_code,
        'indoor': court.indoor,
        'booking_link': court.booking_link
    }
    
    # If the user is a coach, get booking instructions for this court
    if current_user.is_authenticated and current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
        
        if coach:
            coach_court = CoachCourt.query.filter_by(
                coach_id=coach.id,
                court_id=court_id
            ).first()
            
            if coach_court:
                result['booking_instructions'] = coach_court.booking_instructions
                #result['booking_link'] = coach_court.booking_link
    
    return jsonify(result)
    
@bp.route('/notifications')
@login_required
def get_notifications():
    """API endpoint to get user notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get paginated notifications
    notifications = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()) \
        .paginate(page=page, per_page=per_page)
    
    result = []
    for notification in notifications.items:
        result.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'related_id': notification.related_id,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat()
        })
    
    return jsonify({
        'notifications': result,
        'total': notifications.total,
        'pages': notifications.pages,
        'current_page': page,
        'has_next': notifications.has_next,
        'has_prev': notifications.has_prev,
        'unread_count': current_user.unread_notifications_count
    })

@bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notification_read():
    """API endpoint to mark notification as read"""
    data = request.get_json()
    notification_id = data.get('notification_id')
    
    if not notification_id:
        return jsonify({'error': 'Notification ID is required'}), 400
    
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({
        'success': True,
        'unread_count': current_user.unread_notifications_count
    })

@bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """API endpoint to mark all notifications as read"""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'unread_count': 0
    })

@bp.route('/academy/<int:academy_id>/pricing-plans')
@login_required
@coach_or_academy_manager_required
def get_academy_pricing_plans(academy_id):
    """API endpoint to get academy pricing plans"""
    plans = AcademyPricingPlan.query.filter_by(
        academy_id=academy_id,
        is_active=True
    ).all()
    
    result = []
    for plan in plans:
        plan_data = {
            'id': plan.id,
            'academy_id': plan.academy_id,
            'name': plan.name,
            'description': plan.description,
            'discount_type': plan.discount_type,
            'sessions_required': plan.sessions_required,
            'percentage_discount': plan.percentage_discount,
            'fixed_discount': plan.fixed_discount,
            'first_time_only': plan.first_time_only,
            'valid_from': plan.valid_from.isoformat() if plan.valid_from else None,
            'valid_to': plan.valid_to.isoformat() if plan.valid_to else None
        }
        result.append(plan_data)
    
    return jsonify(result)

@bp.route('/packages/purchase', methods=['POST'])
@login_required
def purchase_package():
    """API endpoint to purchase a package"""
    try:
        # Get form data and files
        package_id = request.form.get('package_id')
        package_type = request.form.get('package_type')
        coach_id = request.form.get('coach_id')
        academy_id = request.form.get('academy_id')
        payment_proof = request.files.get('payment_proof')
        
        # Validate required fields
        if not package_id or not package_type:
            return jsonify({'error': 'Missing required fields'}), 400
            
        if package_type not in ['coach', 'academy']:
            return jsonify({'error': 'Invalid package type'}), 400
            
        if package_type == 'coach' and not coach_id:
            return jsonify({'error': 'Coach ID is required for coach packages'}), 400
            
        if package_type == 'academy' and not academy_id:
            return jsonify({'error': 'Academy ID is required for academy packages'}), 400
            
        # Validate payment proof
        if not payment_proof:
            return jsonify({'error': 'Payment proof is required'}), 400
            
        # Get the appropriate pricing plan
        if package_type == 'coach':
            pricing_plan = PricingPlan.query.get_or_404(int(package_id))
            coach = Coach.query.get_or_404(int(coach_id))
            
            # Calculate package price
            hourly_rate = coach.hourly_rate
            total_sessions = pricing_plan.sessions_required
            original_price = hourly_rate * total_sessions
            
            # Calculate discount
            discount_amount = 0
            if pricing_plan.percentage_discount:
                discount_amount = original_price * (pricing_plan.percentage_discount / 100)
                total_price = original_price - discount_amount
            elif pricing_plan.fixed_discount:
                discount_amount = pricing_plan.fixed_discount
                total_price = original_price - discount_amount
            else:
                total_price = original_price
                
            # Create package
            package = BookingPackage(
                student_id=current_user.id,
                coach_id=int(coach_id),
                pricing_plan_id=int(package_id),
                package_type='coach',
                total_sessions=total_sessions,
                sessions_booked=0,
                sessions_completed=0,
                total_price=total_price,
                original_price=original_price,
                discount_amount=discount_amount,
                status='pending',  # Set initial status to pending
                expires_at=datetime.utcnow() + timedelta(days=90)  # 90-day expiration
            )
                
        else:  # academy package
            pricing_plan = AcademyPricingPlan.query.get_or_404(int(package_id))
            academy = Academy.query.get_or_404(int(academy_id))
            
            # Get academy rate if available, or use coach rate
            academy_rate = getattr(pricing_plan, 'academy_rate', None)
            if academy_rate is None:
                # Find a coach in the academy to get their rate
                academy_coach = AcademyCoach.query.filter_by(academy_id=int(academy_id)).first()
                if academy_coach and academy_coach.coach:
                    academy_rate = academy_coach.coach.hourly_rate
                else:
                    academy_rate = 50  # Default rate if no coach found
            
            # Calculate package price
            total_sessions = pricing_plan.sessions_required
            original_price = academy_rate * total_sessions
            
            # Calculate discount
            discount_amount = 0
            if pricing_plan.percentage_discount:
                discount_amount = original_price * (pricing_plan.percentage_discount / 100)
                total_price = original_price - discount_amount
            elif pricing_plan.fixed_discount:
                discount_amount = pricing_plan.fixed_discount
                total_price = original_price - discount_amount
            else:
                total_price = original_price
                
            # Create package
            package = BookingPackage(
                student_id=current_user.id,
                academy_id=int(academy_id),
                academy_pricing_plan_id=int(package_id),
                package_type='academy',
                total_sessions=total_sessions,
                sessions_booked=0,
                sessions_completed=0,
                total_price=total_price,
                original_price=original_price,
                discount_amount=discount_amount,
                status='pending',  # Set initial status to pending
                expires_at=datetime.utcnow() + timedelta(days=90)  # 90-day expiration
            )
        
        # Save the package to the database
        db.session.add(package)
        db.session.flush()  # Get the package ID
        
        # Save payment proof
        if payment_proof:
            # Create directory for proofs if it doesn't exist
            proofs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'package_proofs')
            os.makedirs(proofs_dir, exist_ok=True)
            
            # Save the file with a unique name
            unique_id = uuid.uuid4().hex
            filename = f"package_{package.id}_{unique_id}_{secure_filename(payment_proof.filename)}"
            file_path = os.path.join(proofs_dir, filename)
            payment_proof.save(file_path)
            
            # Store the payment proof in the database
            # Let's create a PaymentProof entry for the package
            # This assumes we can use the same PaymentProof model with a new type
            relative_path = os.path.join('package_proofs', filename).replace('\\', '/')
            
            # Create a payment proof record
            from app.models.payment import PaymentProof
            proof = PaymentProof(
                booking_id=None,  # No booking associated
                package_id=package.id,  # Associate with package
                image_path=relative_path,
                proof_type='package',
                status='pending'
            )
            db.session.add(proof)
        
        # Commit the transaction
        db.session.commit()
        
        # Create notification for the coach or academy
        if package_type == 'coach':
            notify_user_id = coach.user_id
            name = f"{coach.user.first_name} {coach.user.last_name}"
        else:  # academy
            # Find an academy manager to notify
            academy_manager = AcademyManager.query.filter_by(academy_id=int(academy_id), is_owner=True).first()
            if academy_manager:
                notify_user_id = academy_manager.user_id
            else:
                # If no owner found, get any manager
                academy_manager = AcademyManager.query.filter_by(academy_id=int(academy_id)).first()
                notify_user_id = academy_manager.user_id if academy_manager else None
            
            name = academy.name
            
        if notify_user_id:
            notification = Notification(
                user_id=notify_user_id,
                title="New Package Purchase",
                message=f"{current_user.first_name} {current_user.last_name} purchased a package requiring approval.",
                notification_type="package_purchase",
                related_id=package.id
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'package_id': package.id,
            'total_sessions': package.total_sessions,
            'total_price': float(package.total_price),
            'status': 'pending'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/academies')
def get_academies():
    """API endpoint to get filtered academies data"""
    # Get query parameters
    search_query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')  # Default sort by name
    sort_direction = request.args.get('sort_direction', 'asc')
    
    # Base query - join with coaches to count them
    query = db.session.query(
        Academy,
        func.count(AcademyCoach.id).label('coaches_count')
    ).outerjoin(
        AcademyCoach, 
        db.and_(
            Academy.id == AcademyCoach.academy_id,
            AcademyCoach.is_active == True
        )
    )
    
    # Apply filters
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Academy.name.ilike(search_term),
                Academy.description.ilike(search_term)
            )
        )
    
    # Group by academy to support coach count
    query = query.group_by(Academy.id)
    
    # Apply sorting
    if sort_by == 'name':
        order_col = Academy.name
    elif sort_by == 'coaches':
        order_col = func.count(AcademyCoach.id)
    else:  # Default to name
        order_col = Academy.name
    
    if sort_direction == 'desc':
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())
    
    # Execute query
    academies_data = query.all()
    
    # Format response data
    result = []
    for academy, coaches_count in academies_data:

        # Get academy coaches with dynamic roles
        coaches_by_role = {}
        role_ordering = {}  # Track ordering for each role

        # Get the coaches in this academy
        academy_coaches = AcademyCoach.query.filter_by(
            academy_id=academy.id, 
            is_active=True
        ).all()
        
        for ac in academy_coaches:
            coach = Coach.query.get(ac.coach_id)
            if coach and coach.user:
                coach_info = {
                    'id': coach.id,
                    'name': f"{coach.user.first_name} {coach.user.last_name}",
                    'profile_picture': coach.user.profile_picture
                }
                
                # Get role name (or create default)
                if ac.role:
                    role_key = ac.role.name.lower().replace(' ', '_')
                    ordering = ac.role.ordering
                else:
                    # Fallback categories based on experience
                    if coach.years_experience >= 10:
                        role_key = 'head_coach'
                        ordering = 10
                    elif coach.years_experience >= 5:
                        role_key = 'senior_coach'
                        ordering = 20
                    else:
                        role_key = 'coach'
                        ordering = 30
                
                # Initialize the role category if it doesn't exist
                if role_key not in coaches_by_role:
                    coaches_by_role[role_key] = {
                        'role_name': ac.role.name if ac.role else role_key.replace('_', ' ').title(),
                        'ordering': ordering,
                        'coaches': []
                    }
                
                coaches_by_role[role_key]['coaches'].append(coach_info)

        # Get academy tags using the many-to-many relationship
        academy_tags = []
        for tag in academy.tags:
            academy_tags.append({
                'id': tag.id,
                'name': tag.name
            })   

        coach_ids = [ac.coach_id for ac in academy_coaches]
        
        ordered_roles = []
        for role_key, role_data in sorted(coaches_by_role.items(), key=lambda x: x[1]['ordering']):
            ordered_roles.append({
                'role_key': role_key,
                'role_name': role_data['role_name'],
                'ordering': role_data['ordering'],
                'coaches': role_data['coaches']
            })

        academy_data = {
            'id': academy.id,
            'name': academy.name,
            'description': academy.description,
            'logo_path': academy.logo_path,
            'website': academy.website,
            'private_url_code': academy.private_url_code,
            'coaches_count': coaches_count,
            'coach_ids': coach_ids,
            'coaches_by_role': ordered_roles,
            'tags': academy_tags
        }
        result.append(academy_data)
    
    return jsonify(result)

@bp.route('/academies/<string:private_url_code>')
def get_academy_by_url_code(private_url_code):
    """API endpoint to get academy details by private URL code"""
    academy = Academy.query.filter_by(private_url_code=private_url_code).first_or_404()
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(
        academy_id=academy.id,
        is_active=True
    ).all()
    
    coach_ids = [ac.coach_id for ac in academy_coaches]
    coaches = Coach.query.filter(Coach.id.in_(coach_ids)).all()
    
    # Format coach data
    formatted_coaches = []
    for coach in coaches:
        # Get coach rating
        avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(
            CoachRating.coach_id == coach.id
        ).scalar() or 0
        
        rating_count = CoachRating.query.filter_by(coach_id=coach.id).count()
        
        formatted_coaches.append({
            'id': coach.id,
            'user_id': coach.user_id,
            'first_name': coach.user.first_name,
            'last_name': coach.user.last_name,
            'profile_picture': coach.user.profile_picture,
            'hourly_rate': coach.hourly_rate,
            'sessions_completed': coach.sessions_completed,
            'avg_rating': round(float(avg_rating), 1),
            'rating_count': rating_count
        })
    
    # Get academy pricing plans
    pricing_plans = []
    academy_plans = AcademyPricingPlan.query.filter_by(
        academy_id=academy.id,
        is_active=True
    ).all()
    
    for plan in academy_plans:
        pricing_plans.append({
            'id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'discount_type': plan.discount_type,
            'sessions_required': plan.sessions_required,
            'percentage_discount': plan.percentage_discount,
            'fixed_discount': plan.fixed_discount
        })
    
    academy_data = {
        'id': academy.id,
        'name': academy.name,
        'description': academy.description,
        'logo_path': academy.logo_path,
        'website': academy.website,
        'coaches': formatted_coaches,
        'pricing_plans': pricing_plans
    }
    
    return jsonify(academy_data)


# @bp.route('/academies/<int:academy_id>/coaches')
# def get_academy_coaches(academy_id):
#     """API endpoint to get all coaches in an academy"""
#     # Verify academy exists
#     academy = Academy.query.get_or_404(academy_id)
    
#     # Get academy coaches
#     academy_coaches = AcademyCoach.query.filter_by(
#         academy_id=academy_id,
#         is_active=True
#     ).all()
    
#     coach_ids = [ac.coach_id for ac in academy_coaches]
    
#     # Apply additional filters just like in the coaches API
#     search_query = request.args.get('query', '')
#     min_price = request.args.get('min_price', type=float)
#     max_price = request.args.get('max_price', type=float)
#     min_dupr = request.args.get('min_dupr', type=float)
#     max_dupr = request.args.get('max_dupr', type=float)
#     min_rating = request.args.get('min_rating', type=float)
#     court_id = request.args.get('court_id', type=int)
#     sort_by = request.args.get('sort_by', 'name')
#     sort_direction = request.args.get('sort_direction', 'asc')
    
#     # Base query - get coaches that are part of this academy
#     query = db.session.query(
#         Coach, 
#         User, 
#         func.avg(CoachRating.rating).label('avg_rating'),
#         func.count(CoachRating.id).label('rating_count')
#     ).join(
#         User, Coach.user_id == User.id
#     ).outerjoin(
#         CoachRating, Coach.id == CoachRating.coach_id
#     ).filter(
#         Coach.id.in_(coach_ids)
#     )
    
#     # Apply filters
#     if search_query:
#         search_term = f"%{search_query}%"
#         query = query.filter(
#             db.or_(
#                 User.first_name.ilike(search_term),
#                 User.last_name.ilike(search_term)
#             )
#         )
    
#     if min_price is not None:
#         query = query.filter(Coach.hourly_rate >= min_price)
    
#     if max_price is not None:
#         query = query.filter(Coach.hourly_rate <= max_price)
    
#     if min_dupr is not None:
#         query = query.filter(User.dupr_rating >= min_dupr)
    
#     if max_dupr is not None:
#         query = query.filter(User.dupr_rating <= max_dupr)
    
#     if min_rating is not None and min_rating > 0:
#         query = query.having(func.avg(CoachRating.rating) >= min_rating)
    
#     if court_id:
#         query = query.join(CoachCourt, Coach.id == CoachCourt.coach_id).filter(CoachCourt.court_id == court_id)
    
#     # Group by coach and user
#     query = query.group_by(Coach.id, User.id)
    
#     # Apply sorting
#     if sort_by == 'price':
#         order_col = Coach.hourly_rate
#     elif sort_by == 'dupr':
#         order_col = User.dupr_rating
#     elif sort_by == 'rating':
#         order_col = func.avg(CoachRating.rating)
#     else:  # Default to name
#         order_col = User.first_name
    
#     if sort_direction == 'desc':
#         query = query.order_by(order_col.desc())
#     else:
#         query = query.order_by(order_col.asc())
    
#     # Execute query
#     coaches_data = query.all()
    
#     # Format response data
#     result = []
#     for coach, user, avg_rating, rating_count in coaches_data:
#         # Get coach's courts
#         courts = Court.query.join(CoachCourt).filter(CoachCourt.coach_id == coach.id).all()
#         court_names = [court.name for court in courts]
        
#         coach_data = {
#             'id': coach.id,
#             'first_name': user.first_name,
#             'last_name': user.last_name,
#             'dupr_rating': user.dupr_rating,
#             'hourly_rate': coach.hourly_rate,
#             'sessions_completed': coach.sessions_completed,
#             'avg_rating': round(float(avg_rating), 1) if avg_rating else 0,
#             'rating_count': rating_count,
#             'courts': court_names,
#             'biography': coach.biography,
#             'profile_picture': user.profile_picture
#         }
#         result.append(coach_data)
    
#     return jsonify(result)


@bp.route('/student/profile', methods=['GET'])
@login_required
def get_student_profile():
    """API endpoint to get the current student's profile data"""
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts cannot access student profiles'}), 403
    
    # Format response data
    response = {
        'id': current_user.id,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'email': current_user.email,
        'birth_date': current_user.birth_date.isoformat() if current_user.birth_date else None,
        'gender': current_user.gender,
        'location': current_user.location,
        'dupr_rating': current_user.dupr_rating,
        'phone': current_user.phone,
        'bio': current_user.bio,
        'profile_picture': current_user.profile_picture
    }
    
    return jsonify(response)

@bp.route('/student/profile', methods=['PUT'])
@login_required
def update_student_profile():
    """API endpoint to update student profile"""
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts cannot update student profiles'}), 403
    
    data = request.get_json()
    
    # Update user fields
    current_user.first_name = data.get('first_name', current_user.first_name)
    current_user.last_name = data.get('last_name', current_user.last_name)
    current_user.email = data.get('email', current_user.email)
    current_user.phone = data.get('phone', current_user.phone)
    
    # Handle optional fields
    if 'birth_date' in data and data['birth_date']:
        try:
            current_user.birth_date = datetime.fromisoformat(data['birth_date'])
        except ValueError:
            pass
    
    current_user.gender = data.get('gender', current_user.gender)
    current_user.location = data.get('location', current_user.location)
    current_user.dupr_rating = data.get('dupr_rating', current_user.dupr_rating)
    current_user.bio = data.get('bio', current_user.bio)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/student/change-password', methods=['POST'])
@login_required
def student_change_password():
    """API endpoint for students to change their password"""
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts should use the coach password change endpoint'}), 403
    
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Missing current or new password'}), 400
    
    if not current_user.verify_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    current_user.set_password(new_password)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/student/coaches', methods=['GET'])
def get_student_coaches():
    """API endpoint to get all coaches for student dashboard"""
    coaches = Coach.query.join(Coach.user).all()
    
    result = []
    for coach in coaches:
        # Get coach rating
        avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(CoachRating.coach_id == coach.id).scalar() or 0
        rating_count = CoachRating.query.filter_by(coach_id=coach.id).count()
        
        # Get coach courts
        coach_courts = CoachCourt.query.filter_by(coach_id=coach.id).all()
        courts = Court.query.filter(Court.id.in_([cc.court_id for cc in coach_courts])).all()
        court_data = [{'id': court.id, 'name': court.name} for court in courts]
        
        coach_data = {
            'id': coach.id,
            'user': {
                'first_name': coach.user.first_name,
                'last_name': coach.user.last_name,
                'dupr_rating': coach.user.dupr_rating,
                'profile_picture': coach.user.profile_picture
            },
            'hourly_rate': coach.hourly_rate,
            'sessions_completed': coach.sessions_completed,
            'years_experience': coach.years_experience,
            'specialties': coach.specialties,
            'biography': coach.biography,
            'avg_rating': round(float(avg_rating), 1),
            'rating_count': rating_count,
            'courts': court_data
        }
        
        result.append(coach_data)
    
    return jsonify(result)

@bp.route('/student/bookings/<status>', methods=['GET'])
@login_required
def get_student_bookings(status):
    """API endpoint to get student bookings by status"""
    
    if not current_user.is_coach:
        student_id = current_user.id
        query = Booking.query.filter(Booking.student_id == student_id)
    else:
        student_id = request.args.get('student_id', type=int)
        coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
        query = Booking.query.filter(Booking.student_id == student_id, Booking.coach_id == coach.id)

    # Define query based on status
    #query = Booking.query.filter(Booking.student_id == student_id)
    
    if status == 'upcoming':
        query = query.filter(
            Booking.status == 'upcoming',
            Booking.date >= datetime.utcnow().date()
        ).order_by(Booking.date, Booking.start_time)
    elif status == 'completed':
        query = query.filter(
            Booking.status == 'completed'
        ).order_by(Booking.date.desc())
    elif status == 'cancelled':
        query = query.filter(
            Booking.status == 'cancelled'
        ).order_by(Booking.date.desc())
    else:
        return jsonify({'error': 'Invalid status provided'}), 400
    
    bookings = query.all()
    
    # Format bookings data
    result = []
    for booking in bookings:
        coach = Coach.query.get(booking.coach_id)
        coach_user = User.query.get(coach.user_id)
        
        booking_data = {
            'id': booking.id,
            'coach_id': booking.coach_id,
            'coach': {
                'id': coach.id,
                'user': {
                    'first_name': coach_user.first_name,
                    'last_name': coach_user.last_name
                }
            },
            'court_id': booking.court_id,
            'court': {
                'id': booking.court.id,
                'name': booking.court.name
            },
            'date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M:%S'),
            'end_time': booking.end_time.strftime('%H:%M:%S'),
            'price': float(booking.price),
            'base_price': float(booking.base_price),
            'status': booking.status,
            'discount_amount': float(booking.discount_amount) if booking.discount_amount else None,
            'discount_percentage': float(booking.discount_percentage) if booking.discount_percentage else None
        }
        
        # Add session log if it exists
        if hasattr(booking, 'session_log') and booking.session_log:
            booking_data['session_log'] = {
                'id': booking.session_log.id,
                'title': booking.session_log.title,
                'notes': booking.session_log.notes
            }
        
        result.append(booking_data)
    
    return jsonify(result)

@bp.route('/student/bookings/cancel', methods=['POST'])
@login_required
def cancel_student_booking():
    """API endpoint for student to cancel a booking"""
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts should use the coach cancellation endpoint'}), 403
    
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    if not booking_id:
        return jsonify({'error': 'Booking ID is required'}), 400
    
    booking = Booking.query.filter_by(
        id=booking_id,
        student_id=current_user.id,
        status='upcoming'
    ).first()
    
    if not booking:
        return jsonify({'error': 'Booking not found or cannot be cancelled'}), 404
    
    # Check cancellation policy (e.g., 24-hour window)
    booking_datetime = datetime.combine(booking.date, booking.start_time)
    hours_until_booking = (booking_datetime - datetime.utcnow()).total_seconds() / 3600
    
    if hours_until_booking < 24:
        # Could implement a penalty here, but for now just warn
        pass
    
    # Mark as cancelled
    booking.status = 'cancelled'
    
    # Make availability available again
    if booking.availability_id:
        availability = Availability.query.get(booking.availability_id)
        if availability:
            availability.is_booked = False
    
    notification = Notification(
        user_id=coach.user_id if cancelled_by == 'student' else booking.student_id,
        title="Booking cancelled",
        message=f"Booking on {booking.date.strftime('%Y-%m-%d')} has been cancelled",
        notification_type="cancellation",
        related_id=booking.id
    )
    db.session.add(notification)

    #send_booking_cancelled_notification(booking, cancelled_by, reason)

    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/student/packages', methods=['GET'])
@login_required
def get_student_packages():
    """API endpoint to get student packages that can be used with a specific coach"""
    
    if not current_user.is_coach:
        student_id = current_user.id
        coach_id = request.args.get('coach_id', type=int)
    else:
        student_id = request.args.get('student_id', type=int)
        coach_id = current_user.id

    if not coach_id:
        # Get all student packages (both coach and academy packages)
        all_packages = BookingPackage.query.filter_by(student_id=student_id).all()
    
        result = []
        for package in all_packages:
            package_data = {
                'id': package.id,
                'package_type': package.package_type,
                'total_sessions': package.total_sessions,
                'sessions_booked': package.sessions_booked,
                'sessions_completed': package.sessions_completed,
                'total_price': float(package.total_price),
                'original_price': float(package.original_price),
                'discount_amount': float(package.discount_amount) if package.discount_amount else None,
                'purchase_date': package.purchase_date.isoformat(),
                'expires_at': package.expires_at.isoformat() if package.expires_at else None,
                'status': package.status
            }
            
            # Add pricing plan info
            if package.package_type == 'coach' and package.pricing_plan:
                package_data['pricing_plan'] = {
                    'id': package.pricing_plan_id,
                    'name': package.pricing_plan.name,
                    'description': package.pricing_plan.description
                }
            elif package.package_type == 'academy' and package.academy_pricing_plan:
                package_data['pricing_plan'] = {
                    'id': package.academy_pricing_plan_id,
                    'name': package.academy_pricing_plan.name,
                    'description': package.academy_pricing_plan.description
                }
            else:
                package_data['pricing_plan'] = {
                    'id': None,
                    'name': 'Standard Package',
                    'description': 'Basic coaching package'
                }
            
            # Add coach info if it's a coach package
            if package.package_type == 'coach' and package.coach_id:
                coach = Coach.query.get(package.coach_id)
                if coach and coach.user_id:
                    coach_user = User.query.get(coach.user_id)
                    package_data['coach_id'] = package.coach_id
                    package_data['coach'] = {
                        'id': coach.id,
                        'user': {
                            'first_name': coach_user.first_name,
                            'last_name': coach_user.last_name
                        }
                    }
            
            # Add academy info if it's an academy package
            if package.package_type == 'academy' and package.academy_id:
                academy = Academy.query.get(package.academy_id)
                if academy:
                    package_data['academy_id'] = package.academy_id
                    package_data['academy'] = {
                        'id': academy.id,
                        'name': academy.name,
                        'description': academy.description
                    }
            
            result.append(package_data)
        return jsonify(result)

    # Get packages created specifically for this coach
    coach_packages = BookingPackage.query.filter(
        BookingPackage.student_id == current_user.id,
        BookingPackage.coach_id == coach_id,
        BookingPackage.sessions_booked < BookingPackage.total_sessions,
        (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.utcnow()))
    ).all()
    
    # Get academies this coach belongs to
    coach_academies = AcademyCoach.query.filter_by(
        coach_id=coach_id,
        is_active=True
    ).all()
    
    academy_ids = [ca.academy_id for ca in coach_academies]
    
    # Get academy packages that can be used with this coach
    academy_packages = []
    if academy_ids:
        academy_packages = BookingPackage.query.filter(
            BookingPackage.student_id == current_user.id,
            BookingPackage.academy_id.in_(academy_ids),
            BookingPackage.package_type == 'academy',
            BookingPackage.sessions_booked < BookingPackage.total_sessions,
            (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.utcnow()))
        ).all()
    
    # Combine and format packages
    result = []
    for package in coach_packages + academy_packages:
        package_data = {
            'id': package.id,
            'package_type': package.package_type,
            'total_sessions': package.total_sessions,
            'sessions_booked': package.sessions_booked,
            'sessions_completed': package.sessions_completed,
            'total_price': float(package.total_price),
            'original_price': float(package.original_price),
            'discount_amount': float(package.discount_amount) if package.discount_amount else None,
            'purchase_date': package.purchase_date.isoformat(),
            'expires_at': package.expires_at.isoformat() if package.expires_at else None,
            'status': package.status
        }
        
        # Add pricing plan info
        if package.package_type == 'coach' and package.pricing_plan:
            package_data['pricing_plan'] = {
                'id': package.pricing_plan.id,
                'name': package.pricing_plan.name,
                'description': package.pricing_plan.description
            }
        elif package.package_type == 'academy' and package.academy_pricing_plan:
            package_data['pricing_plan'] = {
                'id': package.academy_pricing_plan.id,
                'name': package.academy_pricing_plan.name,
                'description': package.academy_pricing_plan.description
            }
        else:
            package_data['pricing_plan'] = {
                'id': None,
                'name': 'Standard Package',
                'description': 'Basic coaching package'
            }
        
        result.append(package_data)
    
    return jsonify(result)

@bp.route('/student/packages_for_coach', methods=['GET'])
@login_required
def get_student_packages_from_coach():
    """API endpoint to get student packages that can be used with a specific coach"""
    
    student_id = request.args.get('student_id', type=int)

    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    coach_id = coach.id

    # Get all student packages
    all_packages = BookingPackage.query.filter_by(student_id=student_id, coach_id=coach_id).all()
    result = []
    for package in all_packages:
        package_data = {
            'id': package.id,
            'coach_id': package.coach_id,
            'package_type': package.package_type,
            'total_sessions': package.total_sessions,
            'sessions_booked': package.sessions_booked,
            'sessions_completed': package.sessions_completed,
            'total_price': float(package.total_price),
            'original_price': float(package.original_price),
            'discount_amount': float(package.discount_amount) if package.discount_amount else None,
            'purchase_date': package.purchase_date.isoformat(),
            'expires_at': package.expires_at.isoformat() if package.expires_at else None,
            'status': package.status
        }
        
        # Add pricing plan info
        if package.package_type == 'coach' and package.pricing_plan:
            package_data['pricing_plan'] = {
                'id': package.pricing_plan_id,
                'name': package.pricing_plan.name,
                'description': package.pricing_plan.description
            }
        elif package.package_type == 'academy' and package.academy_pricing_plan:
            package_data['pricing_plan'] = {
                'id': package.academy_pricing_plan_id,
                'name': package.academy_pricing_plan.name,
                'description': package.academy_pricing_plan.description
            }
        else:
            package_data['pricing_plan'] = {
                'id': None,
                'name': 'Standard Package',
                'description': 'Basic coaching package'
            }
        
        # Add coach info if it's a coach package
        if package.package_type == 'coach' and package.coach_id:
            coach = Coach.query.get(package.coach_id)
            if coach and coach.user_id:
                coach_user = User.query.get(coach.user_id)
                package_data['coach_id'] = package.coach_id
                package_data['coach'] = {
                    'id': coach.id,
                    'user': {
                        'first_name': coach_user.first_name,
                        'last_name': coach_user.last_name
                    }
                }
        
        # Add academy info if it's an academy package
        if package.package_type == 'academy' and package.academy_id:
            academy = Academy.query.get(package.academy_id)
            if academy:
                package_data['academy_id'] = package.academy_id
                package_data['academy'] = {
                    'id': academy.id,
                    'name': academy.name,
                    'description': academy.description
                }
        
        result.append(package_data)
    return jsonify(result)


@bp.route('/student/session-logs', methods=['GET'])
@login_required
def get_student_session_logs():
    """API endpoint to get student session logs"""
    
    if not current_user.is_coach:
        student_id = current_user.id
        session_logs = SessionLog.query.filter_by(student_id=student_id).order_by(SessionLog.created_at.desc()).all()
    else:
        student_id = request.args.get('student_id', type=int)
        coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
        session_logs = SessionLog.query.filter_by(student_id=student_id, coach_id=coach.id).order_by(SessionLog.created_at.desc()).all()

    
    
    result = []
    for log in session_logs:
        coach = Coach.query.get(log.coach_id)
        coach_user = User.query.get(coach.user_id)
        booking = Booking.query.get(log.booking_id)
        
        log_data = {
            'id': log.id,
            'booking_id': log.booking_id,
            'coach_id': log.coach_id,
            'title': log.title,
            'coach_notes': log.coach_notes,
            'notes': log.notes,  # Assuming there's a student_notes field
            'created_at': log.created_at.isoformat(),
            'updated_at': log.updated_at.isoformat() if log.updated_at else None,
            'coach': {
                'id': coach.id,
                'user': {
                    'first_name': coach_user.first_name,
                    'last_name': coach_user.last_name
                }
            },
            'booking': {
                'id': booking.id,
                'date': booking.date.isoformat(),
                'start_time': booking.start_time.strftime('%H:%M:%S'),
                'end_time': booking.end_time.strftime('%H:%M:%S'),
                'court': {
                    'id': booking.court_id,
                    'name': booking.court.name
                }
            }
        }
        
        result.append(log_data)
    
    return jsonify(result)

@bp.route('/student/session-logs/<int:log_id>', methods=['GET'])
@login_required
def get_student_session_log(log_id):
    """API endpoint to get a specific session log for a student"""
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts cannot access student session logs'}), 403
    
    session_log = SessionLog.query.filter_by(id=log_id, student_id=current_user.id).first_or_404()
    
    coach = Coach.query.get(session_log.coach_id)
    coach_user = User.query.get(coach.user_id)
    booking = Booking.query.get(session_log.booking_id)
    
    log_data = {
        'id': session_log.id,
        'booking_id': session_log.booking_id,
        'coach_id': session_log.coach_id,
        'title': session_log.title,
        'coach_notes': session_log.coach_notes,
        'notes': session_log.notes,  # Assuming there's a student_notes field
        'created_at': session_log.created_at.isoformat(),
        'updated_at': session_log.updated_at.isoformat() if session_log.updated_at else None,
        'coach': {
            'id': coach.id,
            'user': {
                'first_name': coach_user.first_name,
                'last_name': coach_user.last_name
            }
        },
        'booking': {
            'id': booking.id,
            'date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M:%S'),
            'end_time': booking.end_time.strftime('%H:%M:%S'),
            'court': {
                'id': booking.court_id,
                'name': booking.court.name
            }
        }
    }
    
    return jsonify(log_data)

@bp.route('/student/session-logs/update-notes', methods=['POST'])
@login_required
def update_student_session_notes():
    """API endpoint for student to update their notes on a session log"""
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts cannot update student notes'}), 403
    
    data = request.get_json()
    log_id = data.get('log_id')
    student_notes = data.get('student_notes')
    
    if not log_id:
        return jsonify({'error': 'Session log ID is required'}), 400
    
    session_log = SessionLog.query.filter_by(id=log_id, student_id=current_user.id).first_or_404()
    
    # Update student notes 
    session_log.notes = student_notes
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/student/courts', methods=['GET'])
def get_all_courts():
    """API endpoint to get all courts"""
    courts = Court.query.all()
    
    result = []
    for court in courts:
        court_data = {
            'id': court.id,
            'name': court.name,
            'address': court.address,
            'city': court.city,
            'state': court.state,
            'zip_code': court.zip_code,
            'indoor': court.indoor
        }
        
        result.append(court_data)
    
    return jsonify(result)


@bp.route('/student/send-availability', methods=['POST'])
@login_required
def send_coach_availability():
    """API endpoint for student to send availability preferences"""
    data = request.get_json()
    coach_id = data.get('coach_id')
    availability = {
        'days': data.get('days', []),
        'times': data.get('times', []),
        'notes': data.get('notes', ''),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    if not coach_id:
        return jsonify({'error': 'Coach ID is required'}), 400
        
    # Store availability in the user model
    current_user.availability_preferences = availability
    
    # Create a notification for the coach
    coach = Coach.query.get_or_404(coach_id)
    notification = Notification(
        user_id=coach.user_id,
        title="New Availability Preferences",
        message=f"{current_user.first_name} {current_user.last_name} has shared their availability preferences",
        notification_type="availability",
        related_id=current_user.id
    )
    db.session.add(notification)
    
    try:
        db.session.commit()
        
        # Optionally send email notification to coach
        # send_availability_notification(coach, current_user, availability)
        
        return jsonify({
            'success': True,
            'message': 'Availability preferences sent to coach'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/student/get-availability', methods=['GET'])
@login_required
def get_student_availability():
    """API endpoint to get student's saved availability preferences"""
    if not current_user.availability_preferences:
        return jsonify({
            'days': [],
            'times': [],
            'notes': ''
        })
    
    return jsonify(current_user.availability_preferences)


# @bp.route('/student/packages')
# @login_required
# def get_student_packages_for_coach():
#     """API endpoint to get packages for a specific student that can be used with the current coach"""
#     if not current_user.is_coach:
#         return jsonify({'error': 'Not a coach account'}), 403
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
#     student_id = request.args.get('student_id', type=int)
    
#     if not student_id:
#         return jsonify({'error': 'Student ID is required'}), 400
    
#     # Get coach-specific packages
#     coach_packages = BookingPackage.query.filter(
#         BookingPackage.student_id == student_id,
#         BookingPackage.coach_id == coach.id,
#         BookingPackage.status == 'active',
#         BookingPackage.sessions_booked < BookingPackage.total_sessions,
#         (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.utcnow()))
#     ).all()
    
#     # Get academy packages that can be used with this coach
#     coach_academies = AcademyCoach.query.filter_by(
#         coach_id=coach.id,
#         is_active=True
#     ).all()
    
#     academy_ids = [ca.academy_id for ca in coach_academies]
    
#     academy_packages = []
#     if academy_ids:
#         academy_packages = BookingPackage.query.filter(
#             BookingPackage.student_id == student_id,
#             BookingPackage.academy_id.in_(academy_ids),
#             BookingPackage.package_type == 'academy',
#             BookingPackage.status == 'active',
#             BookingPackage.sessions_booked < BookingPackage.total_sessions,
#             (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.utcnow()))
#         ).all()
    
#     # Combine and format packages
#     result = []
#     for package in coach_packages + academy_packages:
#         package_data = {
#             'id': package.id,
#             'package_type': package.package_type,
#             'total_sessions': package.total_sessions,
#             'sessions_booked': package.sessions_booked,
#             'sessions_completed': package.sessions_completed,
#             'total_price': float(package.total_price),
#             'original_price': float(package.original_price),
#             'discount_amount': float(package.discount_amount) if package.discount_amount else None,
#             'purchase_date': package.purchase_date.isoformat(),
#             'expires_at': package.expires_at.isoformat() if package.expires_at else None,
#             'status': package.status
#         }
        
#         # Add pricing plan info
#         if package.package_type == 'coach' and package.pricing_plan:
#             package_data['pricing_plan'] = {
#                 'id': package.pricing_plan_id,
#                 'name': package.pricing_plan.name,
#                 'description': package.pricing_plan.description
#             }
#         elif package.package_type == 'academy' and package.academy_pricing_plan:
#             package_data['pricing_plan'] = {
#                 'id': package.academy_pricing_plan_id,
#                 'name': package.academy_pricing_plan.name,
#                 'description': package.academy_pricing_plan.description
#             }
#         else:
#             package_data['pricing_plan'] = {
#                 'id': None,
#                 'name': 'Standard Package',
#                 'description': 'Basic coaching package'
#             }
        
#         result.append(package_data)
    
#     return jsonify(result)

# @bp.route('/student/bookings/<status>')
# @login_required
# def get_student_bookings_for_coach(status):
#     """API endpoint to get bookings for a specific student with the current coach"""
#     if not current_user.is_coach:
#         return jsonify({'error': 'Not a coach account'}), 403
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
#     student_id = request.args.get('student_id', type=int)
    
#     if not student_id:
#         return jsonify({'error': 'Student ID is required'}), 400
    
#     # Define query based on status
#     query = Booking.query.filter(
#         Booking.student_id == student_id,
#         Booking.coach_id == coach.id
#     )
    
#     if status == 'upcoming':
#         query = query.filter(
#             Booking.status == 'upcoming',
#             Booking.date >= datetime.utcnow().date()
#         ).order_by(Booking.date, Booking.start_time)
#     elif status == 'completed':
#         query = query.filter(
#             Booking.status == 'completed'
#         ).order_by(Booking.date.desc())
#     elif status == 'cancelled':
#         query = query.filter(
#             Booking.status == 'cancelled'
#         ).order_by(Booking.date.desc())
#     else:
#         return jsonify({'error': 'Invalid status provided'}), 400
    
#     bookings = query.all()
    
#     # Format bookings data
#     result = []
#     for booking in bookings:
#         booking_data = {
#             'id': booking.id,
#             'date': booking.date.isoformat(),
#             'start_time': booking.start_time.strftime('%H:%M:%S'),
#             'end_time': booking.end_time.strftime('%H:%M:%S'),
#             'price': float(booking.price),
#             'base_price': float(booking.base_price),
#             'status': booking.status,
#             'venue_confirmed': booking.venue_confirmed,
#             'court_booking_responsibility': booking.court_booking_responsibility,
#             'court': {
#                 'id': booking.court.id,
#                 'name': booking.court.name
#             }
#         }
        
#         # Add pricing plan if available
#         if booking.pricing_plan_id:
#             pricing_plan = PricingPlan.query.get(booking.pricing_plan_id)
#             if pricing_plan:
#                 booking_data['pricing_plan'] = {
#                     'id': pricing_plan.id,
#                     'name': pricing_plan.name
#                 }
        
#         # Add session log if it exists
#         session_log = SessionLog.query.filter_by(booking_id=booking.id).first()
#         if session_log:
#             booking_data['session_log'] = {
#                 'id': session_log.id,
#                 'title': session_log.title,
#                 'notes': session_log.notes
#             }
        
#         result.append(booking_data)
    
#     return jsonify(result)

# @bp.route('/student/session-logs')
# @login_required
# def get_student_session_logs_for_coach():
#     """API endpoint to get session logs for a specific student with the current coach"""
#     if not current_user.is_coach:
#         return jsonify({'error': 'Not a coach account'}), 403
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
#     student_id = request.args.get('student_id', type=int)
    
#     if not student_id:
#         return jsonify({'error': 'Student ID is required'}), 400
    
#     # Get session logs
#     logs = SessionLog.query.filter_by(
#         coach_id=coach.id,
#         student_id=student_id
#     ).order_by(SessionLog.created_at.desc()).all()
    
#     # Format session logs data
#     result = []
#     for log in logs:
#         log_data = {
#             'id': log.id,
#             'title': log.title,
#             'notes': log.notes,
#             'coach_notes': log.coach_notes,
#             'created_at': log.created_at.isoformat(),
#             'updated_at': log.updated_at.isoformat() if log.updated_at else None
#         }
        
#         # Add booking data if available
#         booking = Booking.query.get(log.booking_id) if log.booking_id else None
#         if booking:
#             log_data['booking'] = {
#                 'id': booking.id,
#                 'date': booking.date.isoformat(),
#                 'start_time': booking.start_time.strftime('%H:%M:%S'),
#                 'end_time': booking.end_time.strftime('%H:%M:%S'),
#                 'court': {
#                     'id': booking.court_id,
#                     'name': booking.court.name
#                 }
#             }
        
#         result.append(log_data)
    
#     return jsonify(result)

