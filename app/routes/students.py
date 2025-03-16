# app/routes/students.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.models.booking import Booking
from app.models.session_log import SessionLog
from app.models.rating import CoachRating
from app.forms.student import StudentProfileForm, RatingForm
from datetime import datetime

bp = Blueprint('students', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_coach:
        # If user is a coach, redirect to coach dashboard
        return redirect(url_for('coaches.dashboard'))
    
    # Get upcoming bookings
    upcoming_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.status == 'upcoming',
        Booking.date >= datetime.utcnow().date()
    ).order_by(Booking.date, Booking.start_time).all()
    
    # Get recent completed sessions
    completed_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.status == 'completed'
    ).order_by(Booking.date.desc()).limit(5).all()
    
    return render_template(
        'dashboard/students/dashboard.html', 
        upcoming_bookings=upcoming_bookings,
        completed_bookings=completed_bookings
    )

@bp.route('/connect-points')
@login_required
def connect_points():
    """Student Connect Points page"""
    if current_user.is_coach:
        return redirect(url_for('coaches.dashboard'))
    
    # Get balance and recent transactions (for initial page load)
    from app.models.connect_points import ConnectPoints
    
    points_balance = ConnectPoints.get_user_balance(current_user.id)
    
    # Get recent transactions
    recent_transactions = ConnectPoints.query.filter_by(user_id=current_user.id) \
        .order_by(ConnectPoints.created_at.desc()).limit(5).all()
    
    return render_template(
        'dashboard/students/connect_points.html',
        points_balance=points_balance,
        recent_transactions=recent_transactions
    )
    
@bp.route('/api/student/has-previous-bookings/<int:coach_id>', methods=['GET'])
@login_required
def has_previous_bookings(coach_id):
    """Check if the current student has previous bookings with this coach"""
    previous_bookings = Booking.query.filter_by(
        student_id=current_user.id,
        coach_id=coach_id
    ).first()
    
    return jsonify({
        'has_previous_bookings': previous_bookings is not None
    })
    


# @bp.route('/rate-coach/<int:booking_id>', methods=['POST'])
# @login_required
# def rate_coach(booking_id):
#     if current_user.is_coach:
#         flash('Coaches cannot rate other coaches')
#         return redirect(url_for('main.index'))
    
#     # Get booking and verify it belongs to this student and is completed
#     booking = Booking.query.filter_by(
#         id=booking_id, 
#         student_id=current_user.id,
#         status='completed'
#     ).first_or_404()
    
#     form = RatingForm()
#     if form.validate_on_submit():
#         # Check if rating already exists
#         existing_rating = CoachRating.query.filter_by(
#             coach_id=booking.coach_id, 
#             student_id=current_user.id
#         ).first()
        
#         if existing_rating:
#             # Update existing rating
#             existing_rating.rating = form.rating.data
#             existing_rating.comment = form.comment.data
#         else:
#             # Create new rating
#             rating = CoachRating(
#                 coach_id=booking.coach_id,
#                 student_id=current_user.id,
#                 rating=form.rating.data,
#                 comment=form.comment.data
#             )
#             db.session.add(rating)
        
#         db.session.commit()
#         flash('Your rating has been submitted')
    
#     return redirect(url_for('students.booking_detail', booking_id=booking_id))
