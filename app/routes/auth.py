# app/routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models.user import User
from app.models.coach import Coach, CoachImage
from app.models.court import Court, CoachCourt
from app.forms.auth import LoginForm, RegistrationForm, CoachRegistrationForm, PasswordChangeForm
from werkzeug.security import generate_password_hash
from app.utils.file_utils import save_profile_picture, save_showcase_image
import json
from datetime import datetime

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Handle AJAX POST requests for login
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        
        if not data or not 'email' in data or not 'password' in data:
            return jsonify({'error': 'Missing email or password'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        if user is None or not user.verify_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        remember_me = data.get('remember_me', False)
        login_user(user, remember=remember_me)
        
        # Determine redirect URL based on user type
        if user.is_admin:
            redirect_url = url_for('admin.dashboard')
        elif user.is_coach:
            redirect_url = url_for('coaches.dashboard')
        else:
            redirect_url = url_for('students.dashboard')
            
        # Check for next parameter in the original request
        next_page = request.args.get('next')
        if next_page and url_parse(next_page).netloc == '':
            redirect_url = next_page
            
        return jsonify({'success': True, 'redirect': redirect_url})
    
    # Handle regular form submission for non-JS clients
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('public.index'))
        
        login_user(user, remember=form.remember_me.data)
        
        # Redirect to the page the user was trying to access
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            if user.is_admin:
                next_page = url_for('admin.dashboard')
            elif user.is_coach:
                next_page = url_for('coaches.dashboard')
            else:
                next_page = url_for('students.dashboard')
        
        return redirect(next_page)
    
    return render_template('public/index.html', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('public.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
    
    # Handle AJAX POST requests for registration
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        birth_date_str = data.get('birth_date')
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date() if birth_date_str else None

        # Create new user
        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            birth_date=birth_date,
            gender=data.get('gender'),
            location=data.get('location'),
            dupr_rating=data.get('dupr_rating'),
            bio=data.get('bio'),
            phone=data.get('phone'),
            is_coach=False
        )
        user.set_password(data['password'])
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Automatically log in the new user
            login_user(user)
            
            return jsonify({'success': True, 'redirect': url_for('students.dashboard')})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    # Handle regular form submission for non-JS clients
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            birth_date=form.birth_date.data,
            gender=form.gender.data,
            location=form.location.data,
            dupr_rating=form.dupr_rating.data,
            bio=form.bio.data,
            is_coach=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('public.index'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/register/coach', methods=['POST'])
def register_coach():
    # Handle AJAX POST requests for coach registration
    if request.method == 'POST':
        try:
            # Extract user data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            birth_date_str = request.form.get('birth_date')
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date() if birth_date_str else None

            gender = request.form.get('gender')
            location = request.form.get('location')
            dupr_rating = request.form.get('dupr_rating')
            password = request.form.get('password')
            phone = request.form.get('phone')
            biography = request.form.get('biography')

            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return jsonify({'success': False, 'message': 'A user with this email already exists'}), 400
            
            # Handle profile picture upload
            profile_picture = request.files.get('profile_picture')
            if not profile_picture:
                return jsonify({'success': False, 'message': 'Profile picture is required'}), 400
            
            profile_pic_path = save_profile_picture(profile_picture)
            if not profile_pic_path:
                return jsonify({'success': False, 'message': 'Failed to upload profile picture. Please check the file format.'}), 400
            
            # Create new user
            new_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                birth_date=birth_date,
                gender=gender,
                location=location,
                dupr_rating=float(dupr_rating) if dupr_rating else None,
                is_coach=True,
                profile_picture=profile_pic_path,
                phone=phone,
                bio=biography
            )
            
            # Set password
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.flush()  # Get user ID without committing
            
            # Extract coach data
            hourly_rate = request.form.get('hourly_rate')
            years_experience = request.form.get('years_experience')
            specialties = request.form.get('specialties')
            
            
            # Get selected courts
            selected_courts = json.loads(request.form.get('selected_courts', '[]'))
            
            # Create coach profile
            new_coach = Coach(
                user_id=new_user.id,
                hourly_rate=float(hourly_rate) if hourly_rate else 0,
                years_experience=int(years_experience) if years_experience else 0,
                specialties=specialties,
                biography=biography,
                phone=phone
            )
            
            db.session.add(new_coach)
            db.session.flush()  # Get coach ID without committing
            
            # Handle showcase images
            showcase_images = request.files.getlist('showcase_images')
            if showcase_images:
                for image in showcase_images:
                    image_path = save_showcase_image(image, new_coach.id)
                    if image_path:
                        coach_image = CoachImage(
                            coach_id=new_coach.id,
                            image_path=image_path
                        )
                        db.session.add(coach_image)
            
            # Add coach-court associations
            for court_id in selected_courts:
                coach_court = CoachCourt(
                    coach_id=new_coach.id,
                    court_id=court_id
                )
                db.session.add(coach_court)
            
            # Commit all changes
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Coach registration successful'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 500
    
    return render_template('coaches/register_coach.html')

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect')
            return redirect(url_for('auth.change_password'))
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Your password has been updated')
        return redirect(url_for('students.dashboard') if not current_user.is_coach else url_for('coaches.dashboard'))
    
    return render_template('auth/change_password.html', form=form)