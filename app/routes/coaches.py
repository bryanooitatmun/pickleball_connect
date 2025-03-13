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
from app.models.pricing import PricingPlan  # Add missing import for PricingPlan
from app.forms.coach import CoachProfileForm, AvailabilityForm, SessionLogForm  # Also add the missing form import
from app.models.academy import Academy, AcademyCoach, AcademyManager, AcademyCoachRole
from app.models.academy_pricing import AcademyPricingPlan
from datetime import datetime, timedelta
from sqlalchemy import func, or_, extract  # Add missing import for or_

bp = Blueprint('coaches', __name__)

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

@bp.route('/coach/dashboard')
@login_required
def dashboard():
    if not current_user.is_coach:
        flash('Access denied. You are not registered as a coach.')
        return redirect(url_for('main.index'))
    
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    
    # Get showcase images count
    showcase_images_count = CoachImage.query.filter_by(coach_id=coach.id).count()

    # Get upcoming bookings
    upcoming_bookings = Booking.query.filter(
        Booking.coach_id == coach.id,
        Booking.status == 'upcoming',
        Booking.date >= datetime.now().date()
    ).order_by(Booking.date, Booking.start_time).all()
    
    # Get recent session logs
    recent_logs = SessionLog.query.filter_by(coach_id=coach.id).order_by(SessionLog.created_at.desc()).limit(5).all()
    
    # Calculate total earnings
    total_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.coach_id == coach.id,
        Booking.status == 'completed'
    ).scalar() or 0
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')

    return render_template(
        'coaches/dashboard.html', 
        profile_picture=profile_picture,
        coach=coach, 
        showcase_images_count=showcase_images_count,
        upcoming_bookings=upcoming_bookings,
        recent_logs=recent_logs,
        total_earnings=total_earnings,
        now=datetime.now()
    )

# @bp.route('/coach/account', methods=['GET', 'POST'])
# @login_required
# def account():
#     if not current_user.is_coach:
#         flash('Access denied. You are not registered as a coach.')
#         return redirect(url_for('main.index'))
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first()
#     form = CoachProfileForm(obj=coach)
    
#     if form.validate_on_submit():
#         # Update coach profile
#         coach.biography = form.biography.data
#         coach.hourly_rate = form.hourly_rate.data
#         coach.years_experience = form.years_experience.data
#         coach.specialties = form.specialties.data
        
#         # Update user profile
#         current_user.first_name = form.first_name.data
#         current_user.last_name = form.last_name.data
#         current_user.email = form.email.data
#         current_user.location = form.location.data
#         current_user.dupr_rating = form.dupr_rating.data
        
#         db.session.commit()
#         flash('Your profile has been updated')
#         return redirect(url_for('coaches.account'))
    
#     elif request.method == 'GET':
#         # Populate form with user data
#         form.first_name.data = current_user.first_name
#         form.last_name.data = current_user.last_name
#         form.email.data = current_user.email
#         form.location.data = current_user.location
#         form.dupr_rating.data = current_user.dupr_rating
    
#     return render_template('coaches/account.html', form=form, coach=coach)

# @bp.route('/coach/courts', methods=['GET', 'POST'])
# @login_required
# def manage_courts():
#     if not current_user.is_coach:
#         flash('Access denied. You are not registered as a coach.')
#         return redirect(url_for('main.index'))
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first()
    
#     # Get all courts this coach is associated with
#     coach_courts = CoachCourt.query.filter_by(coach_id=coach.id).all()
#     court_ids = [cc.court_id for cc in coach_courts]
#     courts = Court.query.filter(Court.id.in_(court_ids)).all()
    
#     # Get all available courts
#     all_courts = Court.query.all()
    
#     return render_template('coaches/courts.html', coach=coach, courts=courts, all_courts=all_courts)

# @bp.route('/coach/courts/add', methods=['POST'])
# @login_required
# def add_court():
#     if not current_user.is_coach:
#         flash('Access denied. You are not registered as a coach.')
#         return redirect(url_for('main.index'))
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first()
#     court_id = request.form.get('court_id')
    
#     if court_id:
#         # Check if association already exists
#         exists = CoachCourt.query.filter_by(coach_id=coach.id, court_id=court_id).first()
#         if not exists:
#             coach_court = CoachCourt(coach_id=coach.id, court_id=court_id)
#             db.session.add(coach_court)
#             db.session.commit()
#             flash('Court added successfully')
#         else:
#             flash('This court is already associated with your profile')
    
#     return redirect(url_for('coaches.manage_courts'))

# @bp.route('/coach/courts/remove/<int:court_id>', methods=['POST'])
# @login_required
# def remove_court(court_id):
#     if not current_user.is_coach:
#         flash('Access denied. You are not registered as a coach.')
#         return redirect(url_for('main.index'))
    
#     coach = Coach.query.filter_by(user_id=current_user.id).first()
    
#     # Delete the association
#     CoachCourt.query.filter_by(coach_id=coach.id, court_id=court_id).delete()
#     db.session.commit()
    
#     flash('Court removed successfully')
#     return redirect(url_for('coaches.manage_courts'))
