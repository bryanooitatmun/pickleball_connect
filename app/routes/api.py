# app/routes/api.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.coach import Coach, CoachImage
from app.models.user import User
from app.models.court import Court, CoachCourt
from app.models.booking import Availability, Booking, AvailabilityTemplate
from app.models.package import BookingPackage
from app.models.session_log import SessionLog
from app.models.rating import CoachRating
from app.models.pricing import PricingPlan  # Add missing import for PricingPlan
from app.forms.coach import CoachProfileForm, AvailabilityForm, SessionLogForm  # Also add the missing form import
from app.models.academy import Academy, AcademyCoach, AcademyManager
from app.models.academy_pricing import AcademyPricingPlan
from app.models.user import User
from app.utils.file_utils import save_uploaded_file, delete_file
from datetime import datetime, timedelta
from app.models.payment import PaymentProof
from app.models.notification import Notification
import os
import json
import uuid 
from sqlalchemy import func, or_, extract 

bp = Blueprint('api', __name__, url_prefix='/api')

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
        'specialties': coach.specialties
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
        Booking.date >= datetime.now().date()
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
        month_start = datetime.now().replace(day=1) - timedelta(days=i*30)
        month_name = month_start.strftime('%B %Y')
        
        month_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach.id,
            Booking.status == 'completed',
            extract('year', Booking.date) == month_start.year,
            extract('month', Booking.date) == month_start.month
        ).scalar() or 0
        
        monthly_earnings[month_name] = float(month_earnings)
    
    return jsonify({
        'completed_sessions': coach.sessions_completed,
        'upcoming_sessions': upcoming_sessions,
        'total_earnings': float(total_earnings),
        'average_rating': float(avg_rating),
        'rating_count': rating_count,
        'monthly_earnings': monthly_earnings
    })

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
@login_required
def get_pricing_plans_by_coachid(coach_id):
    """API endpoint to get coach pricing plans"""
    
    coach = Coach.query.filter_by(user_id=coach_id).first_or_404()
    
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
        Availability.date >= datetime.now().date()
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
        if date_obj < datetime.now().date():
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
            student_books_court=data.get('student_books_court', False)  # New field
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
def delete_availability():
    """API endpoint to delete availability"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    availability_id = data.get('availability_id')
    
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
                    student_books_court=slot_data.get('student_books_court', False)  # New field
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
    
    if start_date < datetime.now().date():
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
    now = datetime.now()
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
            Booking.date >= datetime.now().date()
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
            'venue_confirmed': booking.venue_confirmed
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
        Booking.date >= datetime.now().date()
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

@bp.route('/coach/cancel-session', methods=['POST'])
@login_required
def api_cancel_session():
    """API endpoint to cancel a session"""
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
    
    # Mark as cancelled
    booking.status = 'cancelled'
    
    # Make availability available again
    if booking.availability:
        booking.availability.is_booked = False
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/complete-session/<int:booking_id>', methods=['POST'])
@login_required
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
def update_session_log():
    """API endpoint to update a session log"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    log_id = data.get('log_id')
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    log = SessionLog.query.filter_by(
        id=log_id,
        coach_id=coach.id
    ).first_or_404()
    
    # Update log fields
    log.title = data.get('title', log.title)
    log.notes = data.get('notes', log.notes)
    log.coach_notes = data.get('coach_notes', log.coach_notes)
    log.updated_at = datetime.now()
    
    try:
        db.session.commit()
        return jsonify({'success': True})
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
        if new_date < datetime.now().date():
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

        send_booking_rescheduled_notification(booking, original_date, original_start_time, original_court_id)
        
        db.session.commit()
        
        # Here you would typically send an email notification to the student
        # about the rescheduled session
        
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': f'Invalid date or time format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/payment-info', methods=['PUT'])
@login_required
def update_payment_info():
    """API endpoint to update coach payment information"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    data = request.get_json()
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Update payment info
    payment_info = {
        'bank_name': data.get('bank_name'),
        'account_name': data.get('account_name'),
        'account_number': data.get('account_number'),
        'qr_code_url': data.get('qr_code_url')
    }
    
    coach.payment_info = payment_info
    
    # Update court booking instructions if provided
    if 'court_booking_instructions' in data:
        coach.court_booking_instructions = data.get('court_booking_instructions')
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/coach/upload-qr-code', methods=['POST'])
@login_required
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

@bp.route('/coach/packages/pending')
@login_required
def get_pending_packages():
    """API endpoint for coaches to get pending packages"""
    if not current_user.is_coach:
        return jsonify({'error': 'Not a coach account'}), 403
    
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get pending packages for this coach
    pending_packages = BookingPackage.query.filter_by(
        coach_id=coach.id,
        status='pending'
    ).all()
    
    result = []
    for package in pending_packages:
        student = User.query.get(package.student_id)
        pricing_plan = PricingPlan.query.get(package.pricing_plan_id)
        
        # Get payment proof
        from app.models.payment import PaymentProof
        proof = PaymentProof.query.filter_by(
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
                'id': pricing_plan.id,
                'name': pricing_plan.name
            },
            'total_sessions': package.total_sessions,
            'total_price': float(package.total_price),
            'purchase_date': package.purchase_date.isoformat(),
            'status': package.status
        }
        
        if proof:
            package_data['payment_proof'] = {
                'id': proof.id,
                'image_url': f"/static/{proof.image_path}"
            }
            
        result.append(package_data)
    
    return jsonify(result)

@bp.route('/coach/packages/update-status', methods=['POST'])
@login_required
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
        package.activated_at = datetime.now()
    
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
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts cannot access student bookings'}), 403
    
    # Define query based on status
    query = Booking.query.filter(Booking.student_id == current_user.id)
    
    if status == 'upcoming':
        query = query.filter(
            Booking.status == 'upcoming',
            Booking.date >= datetime.now().date()
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
    hours_until_booking = (booking_datetime - datetime.now()).total_seconds() / 3600
    
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

    send_booking_cancelled_notification(booking, cancelled_by, reason)

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
    coach_id = request.args.get('coach_id', type=int)
    
    if not coach_id:
        # Get all student packages (both coach and academy packages)
        all_packages = BookingPackage.query.filter_by(student_id=current_user.id).all()
    
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
        (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.now()))
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
            (BookingPackage.expires_at.is_(None) | (BookingPackage.expires_at >= datetime.now()))
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

@bp.route('/student/session-logs', methods=['GET'])
@login_required
def get_student_session_logs():
    """API endpoint to get student session logs"""
    if current_user.is_coach:
        return jsonify({'error': 'Coach accounts cannot access student session logs'}), 403
    
    session_logs = SessionLog.query.filter_by(student_id=current_user.id).order_by(SessionLog.created_at.desc()).all()
    
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


@bp.route('/support/request', methods=['POST'])
@login_required
def submit_support_request():
    """API endpoint for students to submit support requests"""
    data = request.get_json()
    subject = data.get('subject')
    message = data.get('message')
    
    if not subject or not message:
        return jsonify({'error': 'Subject and message are required'}), 400
    
    # Here you would typically create a support ticket in your database
    # or send an email to your support team
    # For now, we'll just return success
    
    return jsonify({
        'success': True,
        'message': 'Your support request has been submitted.'
    })


@bp.route('/upload-payment-proof/<int:booking_id>', methods=['POST'])
@login_required
def upload_payment_proof(booking_id):
    """API endpoint for student to upload payment proof"""
    if current_user.is_coach:
        return jsonify({'error': 'Coaches cannot upload payment proofs'}), 403
    
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
        filename = f"booking_{booking_id}_{proof_type}_{int(datetime.now().timestamp())}"
        image_path = save_uploaded_file(file, proof_dir, filename)
        
        if not image_path:
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Create payment proof record
        proof = PaymentProof(
            booking_id=booking_id,
            image_path=image_path,
            proof_type=proof_type,
            status='pending'
        )
        
        db.session.add(proof)
        
        # Update booking status
        if proof_type == 'coaching':
            booking.coaching_payment_status = 'uploaded'
        elif proof_type == 'court':
            booking.court_payment_status = 'uploaded'
        
        db.session.commit()
        
        # Create notification for coach
        from app.models.notification import Notification
        
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
        send_coach_payment_proof_notification(booking, proof_type)
        
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
                expires_at=datetime.now() + timedelta(days=90)  # 90-day expiration
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
                expires_at=datetime.now() + timedelta(days=90)  # 90-day expiration
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