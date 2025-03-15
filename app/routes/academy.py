# app/routes/academy.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.models.academy import Academy, AcademyCoach, AcademyManager
from app.models.coach import Coach
from app.models.user import User
from app.models.booking import Booking, Availability
from functools import wraps
import uuid

bp = Blueprint('academy', __name__, url_prefix='/academy')

# Academy manager access decorator
def academy_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_academy_manager:
            flash('Access denied. Academy manager privileges required.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/<string:private_url_code>')
def academy_page(private_url_code):
    """Academy-specific page to show its coaches"""
    # Fetch academy data
    academy = Academy.query.filter_by(private_url_code=private_url_code).first_or_404()
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(
        academy_id=academy.id,
        is_active=True
    ).all()
    
    coach_ids = [ac.coach_id for ac in academy_coaches]
    coaches_count = len(coach_ids)
    
    # Get roles with ordering information
    coaches_by_role = []
    
    # Group coaches by role
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
            'coaches': role_mapping[role_key]['coaches']
        })
    
    # Get academy tags
    academy_tags = []
    for tag in academy.tags:
        academy_tags.append({
            'id': tag.id,
            'name': tag.name
        })
    
    # Prepare the context
    academy_data = {
        'id': academy.id,
        'name': academy.name,
        'description': academy.description,
        'logo_path': academy.logo_path,
        'website': academy.website,
        'coaches_count': coaches_count,
        'coaches_by_role': coaches_by_role,
        'tags': academy_tags
    }
    
    return render_template(
        'coaches/index.html',  # Use the same template
        page_type='academy_page',  # Set page type
        academy=academy_data
    )

@bp.route('/dashboard')
@login_required
@academy_manager_required
def dashboard():
    """Academy manager dashboard"""
    # Get all academies this user manages
    managed_academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
    academy_ids = [am.academy_id for am in managed_academies]
    academies = Academy.query.filter(Academy.id.in_(academy_ids)).all()
    
    if not academies:
        flash('You are not managing any academies.')
        return redirect(url_for('main.index'))
    
    # If only one academy, go directly to that academy's dashboard
    if len(academies) == 1:
        return redirect(url_for('academy.academy_dashboard', academy_id=academies[0].id))
    
    return render_template(
        'academy/dashboard.html',
        academies=academies
    )

@bp.route('/<int:academy_id>/dashboard')
@login_required
@academy_manager_required
def academy_dashboard(academy_id):
    """Dashboard for a specific academy"""
    # Check if user is authorized for this academy
    manager = AcademyManager.query.filter_by(
        academy_id=academy_id,
        user_id=current_user.id
    ).first_or_404()
    
    academy = Academy.query.get_or_404(academy_id)
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(
        academy_id=academy_id,
        is_active=True
    ).all()
    
    coach_ids = [ac.coach_id for ac in academy_coaches]
    coaches = Coach.query.filter(Coach.id.in_(coach_ids)).all()
    
    # Get upcoming bookings for all academy coaches
    upcoming_bookings = Booking.query.filter(
        Booking.coach_id.in_(coach_ids),
        Booking.status == 'upcoming',
        Booking.date >= datetime.now().date()
    ).order_by(Booking.date, Booking.start_time).all()
    
    # Get coach statistics
    coach_stats = []
    for coach in coaches:
        total_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.coach_id == coach.id,
            Booking.status == 'completed'
        ).scalar() or 0
        
        coach_stats.append({
            'coach': coach,
            'user': coach.user,
            'bookings_count': Booking.query.filter_by(coach_id=coach.id).count(),
            'total_earnings': float(total_earnings)
        })
    
    return render_template(
        'academy/academy_dashboard.html',
        academy=academy,
        coaches=coaches,
        coach_stats=coach_stats,
        upcoming_bookings=upcoming_bookings,
        is_owner=manager.is_owner
    )

# Add routes for CRUD operations on academies, coaches, managers
@bp.route('/create', methods=['GET', 'POST'])
@login_required
@academy_manager_required
def create_academy():
    """Create a new academy"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        website = request.form.get('website')
        
        if not name:
            flash('Academy name is required.')
            return redirect(url_for('academy.create_academy'))
        
        # Generate private URL code
        private_url_code = str(uuid.uuid4())[:8]
        
        # Create academy
        academy = Academy(
            name=name,
            description=description,
            website=website,
            private_url_code=private_url_code
        )
        
        try:
            db.session.add(academy)
            db.session.flush()
            
            # Make current user the owner
            manager = AcademyManager(
                academy_id=academy.id,
                user_id=current_user.id,
                is_owner=True
            )
            
            db.session.add(manager)
            db.session.commit()
            
            # Update user status if needed
            if not current_user.is_academy_manager:
                current_user.is_academy_manager = True
                db.session.commit()
            
            flash('Academy created successfully!')
            return redirect(url_for('academy.academy_dashboard', academy_id=academy.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating academy: {str(e)}')
    
    return render_template('academy/create_academy.html')

# API endpoints for academy management
@bp.route('/api/<int:academy_id>/coaches')
@login_required
@academy_manager_required
def api_get_academy_coaches(academy_id):
    """API to get coaches for a specific academy"""
    # Check if user is authorized for this academy
    AcademyManager.query.filter_by(
        academy_id=academy_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Get academy coaches
    academy_coaches = AcademyCoach.query.filter_by(
        academy_id=academy_id,
        is_active=True
    ).all()
    
    coach_ids = [ac.coach_id for ac in academy_coaches]
    coaches = Coach.query.filter(Coach.id.in_(coach_ids)).all()
    
    result = []
    for coach in coaches:
        result.append({
            'id': coach.id,
            'user_id': coach.user_id,
            'first_name': coach.user.first_name,
            'last_name': coach.user.last_name,
            'hourly_rate': coach.hourly_rate,
            'sessions_completed': coach.sessions_completed,
            'profile_picture': coach.user.profile_picture
        })
    
    return jsonify(result)

@bp.route('/api/<int:academy_id>/add-coach', methods=['POST'])
@login_required
@academy_manager_required
def api_add_academy_coach(academy_id):
    """API to add a coach to an academy"""
    # Check if user is authorized for this academy
    AcademyManager.query.filter_by(
        academy_id=academy_id,
        user_id=current_user.id
    ).first_or_404()
    
    data = request.get_json()
    coach_id = data.get('coach_id')
    
    if not coach_id:
        return jsonify({'error': 'Coach ID is required'}), 400
    
    # Check if coach exists
    coach = Coach.query.get(coach_id)
    if not coach:
        return jsonify({'error': 'Coach not found'}), 404
    
    # Check if coach is already in academy
    existing = AcademyCoach.query.filter_by(
        academy_id=academy_id,
        coach_id=coach_id
    ).first()
    
    if existing:
        if existing.is_active:
            return jsonify({'error': 'Coach is already in this academy'}), 400
        else:
            # Reactivate coach
            existing.is_active = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'Coach reactivated in academy'})
    
    # Add coach to academy
    academy_coach = AcademyCoach(
        academy_id=academy_id,
        coach_id=coach_id
    )
    
    db.session.add(academy_coach)
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/api/<int:academy_id>/remove-coach', methods=['POST'])
@login_required
@academy_manager_required
def api_remove_academy_coach(academy_id):
    """API to remove a coach from an academy"""
    # Check if user is authorized for this academy
    AcademyManager.query.filter_by(
        academy_id=academy_id,
        user_id=current_user.id
    ).first_or_404()
    
    data = request.get_json()
    coach_id = data.get('coach_id')
    
    if not coach_id:
        return jsonify({'error': 'Coach ID is required'}), 400
    
    # Find coach in academy
    academy_coach = AcademyCoach.query.filter_by(
        academy_id=academy_id,
        coach_id=coach_id,
        is_active=True
    ).first_or_404()
    
    # Instead of deleting, mark as inactive
    academy_coach.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/profile')
@login_required
@academy_manager_required
def profile():
    """Academy profile management view"""
    # Get all academies this user manages
    managed_academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
    academy_ids = [am.academy_id for am in managed_academies]
    
    # Get selected academy or first in the list
    selected_academy_id = request.args.get('academy_id', type=int)
    if selected_academy_id and selected_academy_id not in academy_ids:
        selected_academy_id = None
    
    if not selected_academy_id and academy_ids:
        selected_academy_id = academy_ids[0]
    
    academy = Academy.query.get(selected_academy_id) if selected_academy_id else None
    
    # Get all available academies for dropdown
    academies = Academy.query.filter(Academy.id.in_(academy_ids)).all()
    
    # Get academy tags
    academy_tags = []
    all_tags = []
    
    if academy:
        academy_tags = academy.tags.all() if academy.tags else []
        all_tags = Tag.query.all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/base.html',
        active_tab='academy-profile',
        profile_picture=profile_picture,
        academy=academy,
        academies=academies,
        academy_tags=academy_tags,
        all_tags=all_tags
    )

@bp.route('/coaches')
@login_required
@academy_manager_required
def coaches():
    """Academy coaches management view"""
    # Get all academies this user manages
    managed_academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
    academy_ids = [am.academy_id for am in managed_academies]
    
    # Get selected academy or first in the list
    selected_academy_id = request.args.get('academy_id', type=int)
    if selected_academy_id and selected_academy_id not in academy_ids:
        selected_academy_id = None
    
    if not selected_academy_id and academy_ids:
        selected_academy_id = academy_ids[0]
    
    academy = Academy.query.get(selected_academy_id) if selected_academy_id else None
    
    # Get all available academies for dropdown
    academies = Academy.query.filter(Academy.id.in_(academy_ids)).all()
    
    # Get academy coaches
    academy_coaches = []
    if academy:
        academy_coaches = AcademyCoach.query.filter_by(
            academy_id=academy.id,
            is_active=True
        ).all()
    
    # Get all available coaches not already in the academy
    coach_ids = [ac.coach_id for ac in academy_coaches]
    available_coaches = []
    
    if academy:
        available_coaches = Coach.query.filter(
            ~Coach.id.in_(coach_ids) if coach_ids else True
        ).all()
    
    # Get coach roles
    coach_roles = AcademyCoachRole.query.order_by(AcademyCoachRole.ordering).all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/base.html',
        active_tab='academy-coaches',
        profile_picture=profile_picture,
        academy=academy,
        academies=academies,
        academy_coaches=academy_coaches,
        available_coaches=available_coaches,
        coach_roles=coach_roles
    )

@bp.route('/packages')
@login_required
@academy_manager_required
def packages():
    """Academy packages management view"""
    # Get all academies this user manages
    managed_academies = AcademyManager.query.filter_by(user_id=current_user.id).all()
    academy_ids = [am.academy_id for am in managed_academies]
    
    # Get selected academy or first in the list
    selected_academy_id = request.args.get('academy_id', type=int)
    if selected_academy_id and selected_academy_id not in academy_ids:
        selected_academy_id = None
    
    if not selected_academy_id and academy_ids:
        selected_academy_id = academy_ids[0]
    
    academy = Academy.query.get(selected_academy_id) if selected_academy_id else None
    
    # Get all available academies for dropdown
    academies = Academy.query.filter(Academy.id.in_(academy_ids)).all()
    
    # Get academy packages
    academy_packages = []
    if academy:
        academy_packages = BookingPackage.query.filter_by(
            academy_id=academy.id,
            package_type='academy'
        ).order_by(BookingPackage.status, BookingPackage.purchase_date.desc()).all()
    
    # Get academy pricing plans
    pricing_plans = []
    if academy:
        pricing_plans = AcademyPricingPlan.query.filter_by(academy_id=academy.id).all()
    
    profile_picture = None
    if current_user.profile_picture:
        profile_picture = current_user.profile_picture.replace('\\', '/')
    
    return render_template(
        'dashboard/base.html',
        active_tab='academy-packages',
        profile_picture=profile_picture,
        academy=academy,
        academies=academies,
        academy_packages=academy_packages,
        pricing_plans=pricing_plans
    )

