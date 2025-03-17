# app/routes/coaches.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.models.coach import Coach, CoachImage
from app.models.user import User
from app.models.court import Court, CoachCourt
from app.models.booking import Availability, Booking
from app.models.session_log import SessionLog
from app.models.rating import CoachRating
from app.models.tag import Tag, CoachTag
from app.models.pricing import PricingPlan
from app.models.package import BookingPackage
from app.models.academy import Academy, AcademyCoach, AcademyManager, AcademyCoachRole
from app.models.academy_pricing import AcademyPricingPlan
from datetime import datetime, timedelta
from sqlalchemy import func, or_, extract
from functools import wraps

bp = Blueprint('coaches', __name__)

# Decorator to check if user is a coach
def coach_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_coach:
            flash('Access denied. You are not registered as a coach.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check if user is a coach or academy manager
def coach_or_academy_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.is_coach and not current_user.is_academy_manager):
            flash('Access denied. You must be registered as a coach or academy manager.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function
    
@bp.route('/dashboard')
@login_required
@coach_or_academy_manager_required
def dashboard():
    """Main dashboard view"""
    # Get coach profile if exists
    coach = None
    if current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    # Get showcase images count
    showcase_images_count = CoachImage.query.filter_by(coach_id=coach.id).count() if coach else 0

    # Get upcoming bookings
    upcoming_bookings = []
    if coach:
        upcoming_bookings = Booking.query.filter(
            Booking.coach_id == coach.id,
            Booking.status == 'upcoming',
            Booking.date >= datetime.utcnow().date()
        ).order_by(Booking.date, Booking.start_time).all()
    elif current_user.is_academy_manager:
        # For academy managers, get bookings for all academy coaches
        academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
        academy_ids = [am.academy_id for am in academies]
        
        if academy_ids:
            # Get all coaches from these academies
            academy_coaches = AcademyCoach.query.filter(
                AcademyCoach.academy_id.in_(academy_ids),
                AcademyCoach.is_active == True
            ).all()
            
            coach_ids = [ac.coach_id for ac in academy_coaches]
            
            if coach_ids:
                upcoming_bookings = Booking.query.filter(
                    Booking.coach_id.in_(coach_ids),
                    Booking.status == 'upcoming',
                    Booking.date >= datetime.utcnow().date()
                ).order_by(Booking.date, Booking.start_time).all()
    
    # Get recent session logs
    recent_logs = []
    if coach:
        recent_logs = SessionLog.query.filter_by(coach_id=coach.id).order_by(SessionLog.created_at.desc()).limit(5).all()
    
    # Calculate total earnings
    total_earnings = 0
    if coach:
        total_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach.id,
            Booking.status == 'completed'
        ).scalar() or 0
    elif current_user.is_academy_manager:
        # For academy managers, calculate earnings for all academy coaches
        if coach_ids:
            total_earnings = db.session.query(func.sum(Booking.price)).filter(
                Booking.coach_id.in_(coach_ids),
                Booking.status == 'completed'
            ).scalar() or 0
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')

    return render_template(
        'dashboard/coach/base.html', 
        active_tab='dashboard',
        profile_picture=profile_picture,
        coach=coach, 
        showcase_images_count=showcase_images_count,
        upcoming_bookings=upcoming_bookings,
        recent_logs=recent_logs,
        total_earnings=total_earnings,
        now=datetime.utcnow()
    )

@bp.route('/coach/profile')
@login_required
@coach_required
def dashboard_profile():
    """Coach profile management view"""
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get coach rating
    avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(CoachRating.coach_id == coach.id).scalar() or 0
    rating_count = CoachRating.query.filter_by(coach_id=coach.id).count()
    
    # Get coach images
    showcase_images = CoachImage.query.filter_by(coach_id=coach.id).all()
    
    # Get coach tags
    coach_tags = CoachTag.query.filter_by(coach_id=coach.id).all()
    tags = []
    for ct in coach_tags:
        tag = Tag.query.get(ct.tag_id)
        if tag:
            tags.append(tag)
    
    # Get all available tags for the dropdown
    all_tags = Tag.query.all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='profile',
        profile_picture=profile_picture,
        coach=coach,
        avg_rating=avg_rating,
        rating_count=rating_count,
        showcase_images=showcase_images,
        tags=tags,
        all_tags=all_tags
    )

@bp.route('/coach/courts')
@login_required
@coach_or_academy_manager_required
def courts():
    """Court management view"""
    # Get coach profile if exists
    coach = None
    coach_courts = []
    
    if current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
        if coach:
            coach_courts = CoachCourt.query.filter_by(coach_id=coach.id).all()
    
    # Get all courts for dropdown
    all_courts = Court.query.all()
    
    # For academy managers, get all courts used by academy coaches
    academy_courts = set()
    if current_user.is_academy_manager:
        academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
        academy_ids = [am.academy_id for am in academies]
        
        if academy_ids:
            # Get all coaches from these academies
            academy_coaches = AcademyCoach.query.filter(
                AcademyCoach.academy_id.in_(academy_ids),
                AcademyCoach.is_active == True
            ).all()
            
            coach_ids = [ac.coach_id for ac in academy_coaches]
            
            if coach_ids:
                # Get courts used by these coaches
                ac_courts = CoachCourt.query.filter(CoachCourt.coach_id.in_(coach_ids)).all()
                for court in ac_courts:
                    academy_courts.add(court)
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='courts',
        profile_picture=profile_picture,
        coach=coach,
        coach_courts=coach_courts,
        academy_courts=list(academy_courts) if academy_courts else [],
        all_courts=all_courts
    )

@bp.route('/coach/availability')
@login_required
@coach_or_academy_manager_required
def availability():
    """Availability management view"""
    # Get coach profile if exists
    coach = None
    availabilities = []
    
    if current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
        if coach:
            availabilities = Availability.query.filter(
                Availability.coach_id == coach.id,
                Availability.date >= datetime.utcnow().date()
            ).order_by(Availability.date, Availability.start_time).all()
    
    # For academy managers, get availabilities for selected coach or all coaches
    academy_coaches = []
    selected_coach_id = request.args.get('coach_id', type=int)
    
    if current_user.is_academy_manager:
        academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
        academy_ids = [am.academy_id for am in academies]
        
        if academy_ids:
            # Get all coaches from these academies
            academy_coaches_assoc = AcademyCoach.query.filter(
                AcademyCoach.academy_id.in_(academy_ids),
                AcademyCoach.is_active == True
            ).all()
            
            coach_ids = [ac.coach_id for ac in academy_coaches_assoc]
            academy_coaches = Coach.query.filter(Coach.id.in_(coach_ids)).all()
            
            if selected_coach_id and selected_coach_id in coach_ids:
                # Get availabilities for selected coach
                availabilities = Availability.query.filter(
                    Availability.coach_id == selected_coach_id,
                    Availability.date >= datetime.utcnow().date()
                ).order_by(Availability.date, Availability.start_time).all()
    
    # Get all courts for dropdown
    all_courts = Court.query.all()
    coach_courts = []
    
    if coach:
        coach_courts = CoachCourt.query.filter_by(coach_id=coach.id).all()
    elif selected_coach_id:
        coach_courts = CoachCourt.query.filter_by(coach_id=selected_coach_id).all()
    
    # Get availability templates
    templates = []
    if coach:
        from app.models.booking import AvailabilityTemplate
        templates = AvailabilityTemplate.query.filter_by(coach_id=coach.id).all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='availability',
        profile_picture=profile_picture,
        coach=coach,
        availabilities=availabilities,
        all_courts=all_courts,
        coach_courts=coach_courts,
        templates=templates,
        academy_coaches=academy_coaches,
        selected_coach_id=selected_coach_id
    )

@bp.route('/coach/bookings')
@login_required
@coach_or_academy_manager_required
def bookings():
    """Bookings management view"""
    # Get coach profile if exists
    coach = None
    upcoming_bookings = []
    completed_bookings = []
    cancelled_bookings = []
    
    if current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
        if coach:
            # Get upcoming bookings
            upcoming_bookings = Booking.query.filter(
                Booking.coach_id == coach.id,
                Booking.status == 'upcoming',
                Booking.date >= datetime.utcnow().date()
            ).order_by(Booking.date, Booking.start_time).all()
            
            # Get completed bookings
            completed_bookings = Booking.query.filter(
                Booking.coach_id == coach.id,
                Booking.status == 'completed'
            ).order_by(Booking.date.desc()).all()
            
            # Get cancelled bookings
            cancelled_bookings = Booking.query.filter(
                Booking.coach_id == coach.id,
                Booking.status == 'cancelled'
            ).order_by(Booking.date.desc()).all()
    
    # For academy managers, get bookings for selected coach or all coaches
    academy_coaches = []
    selected_coach_id = request.args.get('coach_id', type=int)
    
    if current_user.is_academy_manager:
        academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
        academy_ids = [am.academy_id for am in academies]
        
        if academy_ids:
            # Get all coaches from these academies
            academy_coaches_assoc = AcademyCoach.query.filter(
                AcademyCoach.academy_id.in_(academy_ids),
                AcademyCoach.is_active == True
            ).all()
            
            coach_ids = [ac.coach_id for ac in academy_coaches_assoc]
            academy_coaches = Coach.query.filter(Coach.id.in_(coach_ids)).all()
            
            if selected_coach_id and selected_coach_id in coach_ids:
                # Get bookings for selected coach
                upcoming_bookings = Booking.query.filter(
                    Booking.coach_id == selected_coach_id,
                    Booking.status == 'upcoming',
                    Booking.date >= datetime.utcnow().date()
                ).order_by(Booking.date, Booking.start_time).all()
                
                completed_bookings = Booking.query.filter(
                    Booking.coach_id == selected_coach_id,
                    Booking.status == 'completed'
                ).order_by(Booking.date.desc()).all()
                
                cancelled_bookings = Booking.query.filter(
                    Booking.coach_id == selected_coach_id,
                    Booking.status == 'cancelled'
                ).order_by(Booking.date.desc()).all()
            else:
                # Get bookings for all academy coaches
                if coach_ids:
                    upcoming_bookings = Booking.query.filter(
                        Booking.coach_id.in_(coach_ids),
                        Booking.status == 'upcoming',
                        Booking.date >= datetime.utcnow().date()
                    ).order_by(Booking.date, Booking.start_time).all()
                    
                    completed_bookings = Booking.query.filter(
                        Booking.coach_id.in_(coach_ids),
                        Booking.status == 'completed'
                    ).order_by(Booking.date.desc()).all()
                    
                    cancelled_bookings = Booking.query.filter(
                        Booking.coach_id.in_(coach_ids),
                        Booking.status == 'cancelled'
                    ).order_by(Booking.date.desc()).all()
    
    # Get all courts for filter dropdown
    all_courts = Court.query.all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='bookings',
        profile_picture=profile_picture,
        coach=coach,
        upcoming_bookings=upcoming_bookings,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings,
        all_courts=all_courts,
        academy_coaches=academy_coaches,
        selected_coach_id=selected_coach_id
    )

@bp.route('/coach/session-logs')
@login_required
@coach_required
def session_logs():
    """Session logs management view"""
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all session logs
    logs = SessionLog.query.filter_by(coach_id=coach.id).order_by(SessionLog.created_at.desc()).all()
    
    # Get all courts for filter
    courts = Court.query.join(CoachCourt).filter(CoachCourt.coach_id == coach.id).all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='session-logs',
        profile_picture=profile_picture,
        coach=coach,
        logs=logs,
        courts=courts
    )

@bp.route('/coach/pricing')
@login_required
@coach_required
def pricing():
    """Pricing plans management view"""
    coach = Coach.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all pricing plans
    plans = PricingPlan.query.filter_by(coach_id=coach.id).all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='pricing',
        profile_picture=profile_picture,
        coach=coach,
        plans=plans
    )

@bp.route('/coach/packages')
@login_required
@coach_or_academy_manager_required
def packages():
    """Packages management view"""
    # Get coach profile if exists
    coach = None
    coach_packages = []
    
    if current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
        if coach:
            # Get packages for this coach
            coach_packages = BookingPackage.query.filter_by(
                coach_id=coach.id,
                package_type='coach'
            ).order_by(BookingPackage.status, BookingPackage.purchase_date.desc()).all()
    
    # For academy managers, get academy packages
    academy_packages = []
    if current_user.is_academy_manager:
        academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
        academy_ids = [am.academy_id for am in academies]
        
        if academy_ids:
            # Get packages for these academies
            academy_packages = BookingPackage.query.filter(
                BookingPackage.academy_id.in_(academy_ids),
                BookingPackage.package_type == 'academy'
            ).order_by(BookingPackage.status, BookingPackage.purchase_date.desc()).all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='packages',
        profile_picture=profile_picture,
        coach=coach,
        coach_packages=coach_packages,
        academy_packages=academy_packages
    )

@bp.route('/coach/earnings')
@login_required
@coach_or_academy_manager_required
def earnings():
    """Earnings view"""
    # Get coach profile if exists
    coach = None
    earnings_data = None
    
    if current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
        if coach:
            # Get earnings for this coach
            earnings_data = get_coach_earnings(coach.id)
    
    # For academy managers, get earnings for selected coach or all coaches
    academy_coaches = []
    selected_coach_id = request.args.get('coach_id', type=int)
    
    if current_user.is_academy_manager:
        academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
        academy_ids = [am.academy_id for am in academies]
        
        if academy_ids:
            # Get all coaches from these academies
            academy_coaches_assoc = AcademyCoach.query.filter(
                AcademyCoach.academy_id.in_(academy_ids),
                AcademyCoach.is_active == True
            ).all()
            
            coach_ids = [ac.coach_id for ac in academy_coaches_assoc]
            academy_coaches = Coach.query.filter(Coach.id.in_(coach_ids)).all()
            
            if selected_coach_id and selected_coach_id in coach_ids:
                # Get earnings for selected coach
                earnings_data = get_coach_earnings(selected_coach_id)
            else:
                # Get combined earnings for all academy coaches
                earnings_data = get_academy_earnings(academy_ids)
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='earnings',
        profile_picture=profile_picture,
        coach=coach,
        earnings_data=earnings_data,
        academy_coaches=academy_coaches,
        selected_coach_id=selected_coach_id
    )

@bp.route('/coach/help')
@login_required
@coach_or_academy_manager_required
def help():
    """Help center view"""
    coach = None
    if current_user.is_coach:
        coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/coach/base.html',
        active_tab='help',
        profile_picture=profile_picture,
        coach=coach
    )

# Helper function to get coach earnings
def get_coach_earnings(coach_id):
    # Total earnings
    total_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach_id,
        Booking.status == 'completed'
    ).scalar() or 0
    
    # Current month earnings
    now = datetime.utcnow()
    this_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach_id,
        Booking.status == 'completed',
        extract('year', Booking.date) == now.year,
        extract('month', Booking.date) == now.month
    ).scalar() or 0
    
    # Last month earnings
    last_month = now.replace(day=1) - timedelta(days=1)
    last_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach_id,
        Booking.status == 'completed',
        extract('year', Booking.date) == last_month.year,
        extract('month', Booking.date) == last_month.month
    ).scalar() or 0
    
    # Monthly earnings for chart
    monthly_data = {}
    months_to_fetch = 12
    
    for i in range(months_to_fetch-1, -1, -1):
        month_date = now.replace(day=1) - timedelta(days=i*30)
        month_key = month_date.strftime('%Y-%m')
        month_name = month_date.strftime('%B %Y')
        
        month_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach_id,
            Booking.status == 'completed',
            extract('year', Booking.date) == month_date.year,
            extract('month', Booking.date) == month_date.month
        ).scalar() or 0
        
        monthly_data[month_name] = float(month_earnings)
    
    # Earnings by court
    court_earnings = {}
    courts = Court.query.join(CoachCourt).filter(CoachCourt.coach_id == coach_id).all()
    for court in courts:
        court_total = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach_id,
            Booking.court_id == court.id,
            Booking.status == 'completed'
        ).scalar() or 0
        
        if court_total > 0:
            court_earnings[court.name] = float(court_total)
    
    # Earnings breakdown by discount type
    earnings_breakdown = {}
    # Regular sessions (no discount)
    regular_count = Booking.query.filter(
        Booking.coach_id == coach_id,
        Booking.status == 'completed',
        Booking.pricing_plan_id.is_(None)
    ).count()
    
    regular_amount = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach_id,
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
            Booking.coach_id == coach_id,
            Booking.status == 'completed',
            PricingPlan.discount_type == discount_type
        ).count()
        
        discount_amount = db.session.query(func.sum(Booking.price)).join(PricingPlan).filter(
            Booking.coach_id == coach_id,
            Booking.status == 'completed',
            PricingPlan.discount_type == discount_type
        ).scalar() or 0
        
        if discount_count > 0:
            earnings_breakdown[discount_type] = {
                'sessions': discount_count,
                'amount': float(discount_amount)
            }
    
    return {
        'total': float(total_earnings),
        'this_month': float(this_month_earnings),
        'last_month': float(last_month_earnings),
        'monthly': monthly_data,
        'by_court': court_earnings,
        'breakdown': earnings_breakdown
    }

# Helper function to get academy earnings
def get_academy_earnings(academy_ids):
    # Get coach IDs for these academies
    academy_coaches = AcademyCoach.query.filter(
        AcademyCoach.academy_id.in_(academy_ids),
        AcademyCoach.is_active == True
    ).all()
    
    coach_ids = [ac.coach_id for ac in academy_coaches]
    
    if not coach_ids:
        return {
            'total': 0.0,
            'this_month': 0.0,
            'last_month': 0.0,
            'monthly': {},
            'by_court': {},
            'breakdown': {},
            'by_coach': {}
        }
    
    # Total earnings
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
    
    # Monthly earnings for chart
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
    
    # Earnings by court
    court_earnings = {}
    # Get all courts used by these coaches
    courts = Court.query.join(
        Booking, Booking.court_id == Court.id
    ).filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'completed'
    ).distinct().all()
    
    for court in courts:
        court_total = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id.in_(coach_ids),
            Booking.court_id == court.id,
            Booking.status == 'completed'
        ).scalar() or 0
        
        if court_total > 0:
            court_earnings[court.name] = float(court_total)
    
    # Earnings breakdown by discount type
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
    
    # Earnings by coach
    by_coach = {}
    for coach_id in coach_ids:
        coach = Coach.query.get(coach_id)
        if coach and coach.user:
            coach_earnings = db.session.query(func.sum(Booking.price)).filter(
                Booking.coach_id == coach_id,
                Booking.status == 'completed'
            ).scalar() or 0
            
            if coach_earnings > 0:
                by_coach[f"{coach.user.first_name} {coach.user.last_name}"] = float(coach_earnings)
    
    return {
        'total': float(total_earnings),
        'this_month': float(this_month_earnings),
        'last_month': float(last_month_earnings),
        'monthly': monthly_data,
        'by_court': court_earnings,
        'breakdown': earnings_breakdown,
        'by_coach': by_coach
    }