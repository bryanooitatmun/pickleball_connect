# app/routes/students.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
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
        Booking.date >= datetime.now().date()
    ).order_by(Booking.date, Booking.start_time).all()
    
    # Get recent completed sessions
    completed_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.status == 'completed'
    ).order_by(Booking.date.desc()).limit(5).all()
    
    return render_template(
        'students/dashboard.html', 
        upcoming_bookings=upcoming_bookings,
        completed_bookings=completed_bookings
    )

@bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if current_user.is_coach:
        # If user is a coach, redirect to coach account
        return redirect(url_for('coaches.account'))
    
    form = StudentProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        current_user.birth_date = form.birth_date.data
        current_user.gender = form.gender.data
        current_user.location = form.location.data
        current_user.dupr_rating = form.dupr_rating.data
        current_user.bio = form.bio.data
        
        
        db.session.commit()
        flash('Your profile has been updated')
        return redirect(url_for('students.account'))
    
    return render_template('students/account.html', form=form)

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
    
@bp.route('/bookings')
@login_required
def bookings():
    if current_user.is_coach:
        return redirect(url_for('coaches.sessions'))
    
    # Get upcoming bookings
    upcoming_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.status == 'upcoming',
        Booking.date >= datetime.now().date()
    ).order_by(Booking.date, Booking.start_time).all()
    
    # Get completed bookings
    completed_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.status == 'completed'
    ).order_by(Booking.date.desc()).all()
    
    return render_template(
        'students/bookings.html', 
        upcoming_bookings=upcoming_bookings,
        completed_bookings=completed_bookings
    )

@bp.route('/booking/<int:booking_id>')
@login_required
def booking_detail(booking_id):
    if current_user.is_coach:
        return redirect(url_for('coaches.session_detail', booking_id=booking_id))
    
    # Get booking and verify it belongs to this student
    booking = Booking.query.filter_by(id=booking_id, student_id=current_user.id).first_or_404()
    
    # Get session log if it exists
    session_log = SessionLog.query.filter_by(booking_id=booking.id).first()
    
    # Check if student has already rated this coach
    existing_rating = CoachRating.query.filter_by(
        coach_id=booking.coach_id, 
        student_id=current_user.id
    ).first()
    
    rating_form = RatingForm(obj=existing_rating) if booking.status == 'completed' else None
    
    return render_template(
        'students/booking_detail.html', 
        booking=booking, 
        session_log=session_log,
        existing_rating=existing_rating,
        rating_form=rating_form
    )

@bp.route('/rate-coach/<int:booking_id>', methods=['POST'])
@login_required
def rate_coach(booking_id):
    if current_user.is_coach:
        flash('Coaches cannot rate other coaches')
        return redirect(url_for('main.index'))
    
    # Get booking and verify it belongs to this student and is completed
    booking = Booking.query.filter_by(
        id=booking_id, 
        student_id=current_user.id,
        status='completed'
    ).first_or_404()
    
    form = RatingForm()
    if form.validate_on_submit():
        # Check if rating already exists
        existing_rating = CoachRating.query.filter_by(
            coach_id=booking.coach_id, 
            student_id=current_user.id
        ).first()
        
        if existing_rating:
            # Update existing rating
            existing_rating.rating = form.rating.data
            existing_rating.comment = form.comment.data
        else:
            # Create new rating
            rating = CoachRating(
                coach_id=booking.coach_id,
                student_id=current_user.id,
                rating=form.rating.data,
                comment=form.comment.data
            )
            db.session.add(rating)
        
        db.session.commit()
        flash('Your rating has been submitted')
    
    return redirect(url_for('students.booking_detail', booking_id=booking_id))

@bp.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    if current_user.is_coach:
        flash('Please use the coach interface to manage bookings')
        return redirect(url_for('coaches.sessions'))
    
    # Get booking and verify it belongs to this student and is upcoming
    booking = Booking.query.filter_by(
        id=booking_id, 
        student_id=current_user.id,
        status='upcoming'
    ).first_or_404()
    
    # Check cancellation policy (e.g., must be at least 24 hours before session)
    session_datetime = datetime.combine(booking.date, booking.start_time)
    if datetime.now() > (session_datetime - timedelta(hours=24)):
        flash('Cancellations must be made at least 24 hours in advance')
        return redirect(url_for('students.booking_detail', booking_id=booking_id))
    
    # Mark the booking as cancelled
    booking.status = 'cancelled'
    
    # Mark the availability as not booked
    availability = booking.availability
    availability.is_booked = False
    
    db.session.commit()
    
    flash('Your booking has been cancelled')
    return redirect(url_for('students.bookings'))