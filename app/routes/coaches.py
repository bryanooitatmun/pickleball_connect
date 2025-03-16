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
    
@bp.route('/')
def index():
    coaches = Coach.query.join(Coach.user).all()
    return render_template('coaches/index.html', coaches=coaches)

@bp.route('/register')
def register():
    if current_user.is_authenticated and current_user.is_coach:
        return redirect(url_for('coaches.dashboard'))
    return render_template('coaches/register_coach.html')

@bp.route('/api/coaches')
def get_coaches():
    """API endpoint to get filtered coaches data"""
    # Get query parameters
    search_query = request.args.get('query', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_dupr = request.args.get('min_dupr', type=float)
    max_dupr = request.args.get('max_dupr', type=float)
    min_rating = request.args.get('min_rating', type=float)
    court_id = request.args.get('court_id', type=int)
    sort_by = request.args.get('sort_by', 'name')  # Default sort by name
    sort_direction = request.args.get('sort_direction', 'asc')

    academy_id = request.args.get('academy_id', -1, type=int)

    # Base query - join Coach with User to access user details
    query = db.session.query(
        Coach, 
        User, 
        func.avg(CoachRating.rating).label('avg_rating'),
        func.count(CoachRating.id).label('rating_count')
    ).join(
        User, Coach.user_id == User.id
    ).outerjoin(
        CoachRating, Coach.id == CoachRating.coach_id
    )
    
    academy = None
    academy_coaches = None
    coach_ids = None

    if academy_id != -1:
        # Verify academy exists
        academy = Academy.query.get_or_404(academy_id)
        
        # Get academy coaches
        academy_coaches = AcademyCoach.query.filter_by(
            academy_id=academy_id,
            is_active=True
        ).all()

        coach_ids = [ac.coach_id for ac in academy_coaches]
        
        query = query.filter(
            Coach.id.in_(coach_ids)
        )

    # Apply filters
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )
    
    if min_price is not None:
        query = query.filter(Coach.hourly_rate >= min_price)
    
    if max_price is not None:
        query = query.filter(Coach.hourly_rate <= max_price)
    
    if min_dupr is not None:
        query = query.filter(User.dupr_rating >= min_dupr)
    
    if max_dupr is not None:
        query = query.filter(User.dupr_rating <= max_dupr)
    
    if min_rating is not None and min_rating > 0:
        query = query.having(func.avg(CoachRating.rating) >= min_rating)
    
    if court_id:
        query = query.join(CoachCourt, Coach.id == CoachCourt.coach_id).filter(CoachCourt.court_id == court_id)
    
    # Group by coach and user to support aggregations
    query = query.group_by(Coach.id, User.id)
    
    # Apply sorting
    if sort_by == 'price':
        order_col = Coach.hourly_rate
    elif sort_by == 'dupr':
        order_col = User.dupr_rating
    elif sort_by == 'rating':
        order_col = func.avg(CoachRating.rating)
    else:  # Default to name
        order_col = User.first_name
    
    if sort_direction == 'desc':
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())
    
    # Execute query
    coaches_data = query.all()
    


    # Add academy pricing plans data at the response level, not per coach
    academy_data = None

    if academy_id != -1 and academy:
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
                'fixed_discount': plan.fixed_discount,
                'valid_from': plan.valid_from.isoformat() if plan.valid_from else None,
                'valid_to': plan.valid_to.isoformat() if plan.valid_to else None
            })
        
        # Get academy roles with proper ordering for display
        coaches_by_role = []
        role_mapping = {}
        role_ordering = {}
        
        for ac in academy_coaches:
            coach = Coach.query.get(ac.coach_id)
            if coach and coach.user:
                coach_info = {
                    'id': coach.id,
                    'name': f"{coach.user.first_name} {coach.user.last_name}",
                    'profile_picture': coach.user.profile_picture
                }
                
                # Determine role and ordering
                if ac.role:
                    role_key = ac.role.name.lower().replace(' ', '_')
                    role_name = ac.role.name
                    ordering = ac.role.ordering
                else:
                    # Fallback based on experience
                    if coach.years_experience >= 10:
                        role_key = 'head_coach'
                        role_name = 'Head Coach'
                        ordering = 10
                    elif coach.years_experience >= 5:
                        role_key = 'senior_coach'
                        role_name = 'Senior Coach'
                        ordering = 20
                    else:
                        role_key = 'coach'
                        role_name = 'Coach'
                        ordering = 30
                
                # Initialize the role category if needed
                if role_key not in role_mapping:
                    role_mapping[role_key] = {
                        'role_name': role_name,
                        'ordering': ordering,
                        'coaches': []
                    }
                    role_ordering[role_key] = ordering
                
                role_mapping[role_key]['coaches'].append(coach_info)
        
        # Sort and convert to list
        for role_key in sorted(role_mapping.keys(), key=lambda x: role_ordering.get(x, 100)):
            coaches_by_role.append({
                'role_key': role_key,
                'role_name': role_mapping[role_key]['role_name'],
                'ordering': role_mapping[role_key]['ordering'],
                'coaches': role_mapping[role_key]['coaches']
            })
            
        # Get academy tags
        academy_tags = []
        if hasattr(academy, 'tags'):
            for tag in academy.tags:
                academy_tags.append({
                    'id': tag.id,
                    'name': tag.name
                })
        
        # Create the academy data object
        academy_data = {
            'id': academy.id,
            'name': academy.name,
            'description': academy.description,
            'logo_path': academy.logo_path,
            'website': academy.website,
            'private_url_code': academy.private_url_code,
            'coaches_count': len(coach_ids),
            'coaches_by_role': coaches_by_role,
            'tags': academy_tags,
            'pricing_plans': pricing_plans
        }
        
    # Format response data
    result = []

    for coach, user, avg_rating, rating_count in coaches_data:
        # Get coach's courts
        courts = Court.query.join(CoachCourt).filter(CoachCourt.coach_id == coach.id).all()
        court_names = [court.name for court in courts]
        
        # Get coach's tags
        tags = []
        coach_tags = CoachTag.query.filter_by(coach_id=coach.id).all()
        for ct in coach_tags:
            tag = Tag.query.get(ct.tag_id)
            if tag:
                tags.append({
                    'id': tag.id,
                    'name': tag.name
                })

        # Get coach's academies
        academy_affiliations = []
        academy_coaches = AcademyCoach.query.filter_by(
            coach_id=coach.id,
            is_active=True
        ).all()
        
        for ac in academy_coaches:
            academy = Academy.query.get(ac.academy_id)
            if academy:
                role_name = "Coach"
                if ac.role:
                    role_name = ac.role.name
                if academy_id == -1:
                    academy_affiliations.append({
                        'id': academy.id,
                        'name': academy.name,
                        'private_url_code': academy.private_url_code,
                        'role': role_name
                    })
                elif academy_id == academy.id:
                    academy_affiliations.append({
                        'id': academy.id,
                        'name': academy.name,
                        'private_url_code': academy.private_url_code,
                        'role': role_name
                    })

        coach_data = {
            'id': coach.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'dupr_rating': user.dupr_rating,
            'hourly_rate': coach.hourly_rate,
            'sessions_completed': coach.sessions_completed,
            'avg_rating': round(avg_rating, 1) if avg_rating else 0,
            'rating_count': rating_count,
            'courts': court_names,
            'biography': coach.biography,
            'profile_picture': user.profile_picture,
            'tags': tags,
            'academy_affiliations': academy_affiliations
        }
        result.append(coach_data)
    
    return jsonify({
        'coaches': result,
        'academy': academy_data
    })


@bp.route('/api/coach/<int:coach_id>')
def get_coach_profile(coach_id):
    """API endpoint to get a specific coach's profile data"""
    coach = Coach.query.get_or_404(coach_id)
    user = User.query.get_or_404(coach.user_id)
    
    # Get coach rating
    avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(CoachRating.coach_id == coach_id).scalar() or 0
    rating_count = CoachRating.query.filter_by(coach_id=coach_id).count()
    
    # Get coach courts
    coach_courts = CoachCourt.query.filter_by(coach_id=coach_id).all()
    courts = Court.query.filter(Court.id.in_([cc.court_id for cc in coach_courts])).all()
    
    # Format court data with booking links
    court_data = []
    for court in courts:
        court_data.append({
            'id': court.id, 
            'name': court.name,
            'booking_link': court.booking_link
        })
    
    # Get profile picture URL
    profile_picture = url_for('static', filename=user.profile_picture) if user.profile_picture else None
    
    # Get showcase images
    showcase_images = []
    for image in coach.showcase_images:
        showcase_images.append(url_for('static', filename=image.image_path))
        
    # Get coach's academies
    academy_affiliations = []
    academy_coaches = AcademyCoach.query.filter_by(
        coach_id=coach.id,
        is_active=True
    ).all()
    
    for ac in academy_coaches:
        academy = Academy.query.get(ac.academy_id)
        if academy:
            role_name = "Coach"
            if ac.role:
                role_name = ac.role.name
            academy_affiliations.append({
                'id': academy.id,
                'name': academy.name,
                'private_url_code': academy.private_url_code,
                'role': role_name
            })

    # Format response data
    coach_data = {
        'id': coach.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'dupr_rating': user.dupr_rating,
        'hourly_rate': coach.hourly_rate,
        'sessions_completed': coach.sessions_completed,
        'avg_rating': round(avg_rating, 1),
        'rating_count': rating_count,
        'courts': court_data,
        'biography': coach.biography,
        'profile_picture': profile_picture,
        'showcase_images': showcase_images,
        'location': user.location,
        'specialties': coach.specialties,
        'academy_affiliations': academy_affiliations  # Add academy affiliations
    }
    
    return jsonify(coach_data)

@bp.route('/api/availability/<int:coach_id>/<int:court_id>/<string:date>')
def get_coach_availability(coach_id, court_id, date):
    """API endpoint to get coach availability for a specific date and court"""
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Get all availability slots
        availabilities = Availability.query.filter(
            Availability.coach_id == coach_id,
            Availability.court_id == court_id,
            Availability.date == date_obj,
            Availability.is_booked == False
        ).all()
        
        # Get booked slots (for display purposes)
        bookings = Booking.query.filter(
            Booking.coach_id == coach_id,
            Booking.court_id == court_id,
            Booking.date == date_obj
        ).all()
        
        available_slots = []
        booked_slots = []
        
        for a in availabilities:
            available_slots.append({
                'id': a.id,
                'time': a.start_time.strftime('%I:%M %p')
            })
            
        for b in bookings:
            booked_slots.append({
                'time': b.start_time.strftime('%I:%M %p')
            })
            
        return jsonify({
            'available': available_slots,
            'booked': booked_slots
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/coaches/<int:coach_id>')
def profile(coach_id):
    coach = Coach.query.get_or_404(coach_id)
    
    # Get coach rating
    avg_rating = db.session.query(func.avg(CoachRating.rating)).filter(CoachRating.coach_id == coach_id).scalar() or 0
    rating_count = CoachRating.query.filter_by(coach_id=coach_id).count()
    
    # Get coach courts
    courts = Court.query.join(CoachCourt).filter(CoachCourt.coach_id == coach_id).all()

    # Get coach's showcase images
    showcase_images = []
    for image in coach.showcase_images:
        showcase_images.append({
            'id': image.id,
            'url': url_for('static', filename=image.image_path)
        })
        
    # Get coach's tags
    coach_tags = []
    tag_associations = CoachTag.query.filter_by(coach_id=coach_id).all()
    for tag_assoc in tag_associations:
        tag = Tag.query.get(tag_assoc.tag_id)
        if tag:
            coach_tags.append({
                'id': tag.id,
                'name': tag.name
            })

    return render_template(
        'coaches/profile.html', 
        coach=coach, 
        showcase_images=showcase_images,
        avg_rating=round(avg_rating, 1), 
        rating_count=rating_count,
        courts=courts,
        coach_tags=coach_tags,  # Pass coach tags to the template
        userIsLoggedIn=current_user.is_authenticated # Pass login status to template
    )

# @bp.route('/coach/dashboard')
# @login_required
# def dashboard():
#     if not current_user.is_coach and not current_user.is_academy_manager:
#         flash('Access denied. You are not registered as a coach or academy manager.')
#         return redirect(url_for('main.index'))
    
#     # For academy managers, redirect to academy dashboard if they don't have a coach profile
#     if current_user.is_academy_manager and not current_user.is_coach:
#         return redirect(url_for('academy.dashboard'))
    
#     # For coaches, load coach profile
#     coach = Coach.query.filter_by(user_id=current_user.id).first()
    
#     # Get showcase images count
#     showcase_images_count = CoachImage.query.filter_by(coach_id=coach.id).count() if coach else 0

#     # Get upcoming bookings
#     upcoming_bookings = Booking.query.filter(
#         Booking.coach_id == coach.id,
#         Booking.status == 'upcoming',
#         Booking.date >= datetime.utcnow().date()
#     ).order_by(Booking.date, Booking.start_time).all() if coach else []
    
#     # Get recent session logs
#     recent_logs = SessionLog.query.filter_by(coach_id=coach.id).order_by(SessionLog.created_at.desc()).limit(5).all() if coach else []
    
#     # Calculate total earnings
#     total_earnings = db.session.query(func.sum(Booking.price)).filter(
#         Booking.coach_id == coach.id,
#         Booking.status == 'completed'
#     ).scalar() or 0 if coach else 0
    
#     profile_picture = None
#     if current_user.profile_picture:
#         profile_picture = current_user.profile_picture.replace('\\', '/')

#     return render_template(
#         'dashboard/coach/base.html', 
#         active_tab='dashboard',
#         profile_picture=profile_picture,
#         coach=coach, 
#         showcase_images_count=showcase_images_count,
#         upcoming_bookings=upcoming_bookings,
#         recent_logs=recent_logs,
#         total_earnings=total_earnings,
#         now=datetime.utcnow()
#     )

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