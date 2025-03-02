# app/routes/api.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.coach import Coach, CoachImage
from app.models.user import User
from app.models.court import Court, CoachCourt
from app.models.booking import Availability, Booking
from app.models.session_log import SessionLog
from app.models.rating import CoachRating
from app.models.pricing import PricingPlan  # Add missing import for PricingPlan
from app.forms.coach import CoachProfileForm, AvailabilityForm, SessionLogForm  # Also add the missing form import
from app.models.user import User
from app.utils.file_utils import save_uploaded_file, delete_file
from datetime import datetime, timedelta
import os
import json
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
            }
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
        db.session.commit()
        return jsonify({'success': True})
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
    
    # Mark the booking as completed
    booking.status = 'completed'
    
    # Increment the coach's sessions count
    coach.sessions_completed += 1
    
    db.session.commit()
    
    flash('Session marked as completed')
    return redirect(url_for('coaches.session_detail', booking_id=booking_id))




@bp.route('/courts')
def get_courts():
    """API endpoint to get all courts"""
    courts = Court.query.all()
    courts_data = [{'id': court.id, 'name': court.name, 'address':court.address, 'city':court.city, 'state':court.state, 'zip_code':court.zip_code} for court in courts]
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
    log.updated_at = datetime.utcnow()
    
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