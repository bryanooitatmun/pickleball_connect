# app/utils/email.py
from flask import current_app, render_template
from flask_mail import Message
from app import mail
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, text_body, html_body):
    msg = Message(subject, sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    
    # Send email asynchronously
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_booking_confirmation(booking):
    """Send booking confirmation email to student"""
    student = booking.student
    coach = booking.coach.user
    
    subject = f"Booking Confirmation - Pickleball Connect"
    recipients = [student.email]
    
    text_body = render_template('email/booking_confirmation.txt', 
                               booking=booking,
                               student=student,
                               coach=coach)
    html_body = render_template('email/booking_confirmation.html', 
                               booking=booking,
                               student=student,
                               coach=coach)
    
    send_email(subject, recipients, text_body, html_body)

def send_coach_booking_notification(booking):
    """Notify coach about new booking"""
    student = booking.student
    coach = booking.coach.user
    
    subject = f"New Booking - Pickleball Connect"
    recipients = [coach.email]
    
    text_body = render_template('email/coach_booking_notification.txt', 
                               booking=booking,
                               student=student,
                               coach=coach)
    html_body = render_template('email/coach_booking_notification.html', 
                               booking=booking,
                               student=student,
                               coach=coach)
    
    send_email(subject, recipients, text_body, html_body)

def send_coach_payment_proof_notification(booking, proof_type):
    """Notify coach about payment proof upload"""
    student = booking.student
    coach = booking.coach.user
    
    subject = f"Payment Proof Uploaded - Pickleball Connect"
    recipients = [coach.email]
    
    text_body = render_template('email/payment_proof_notification.txt', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               proof_type=proof_type)
    html_body = render_template('email/payment_proof_notification.html', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               proof_type=proof_type)
    
    send_email(subject, recipients, text_body, html_body)

def send_student_payment_status_notification(booking, proof_type, status, notes):
    """Notify student about payment proof status update"""
    student = booking.student
    coach = booking.coach.user
    
    subject = f"Payment Proof {status.capitalize()} - Pickleball Connect"
    recipients = [student.email]
    
    text_body = render_template('email/payment_status_notification.txt', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               proof_type=proof_type,
                               status=status,
                               notes=notes)
    html_body = render_template('email/payment_status_notification.html', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               proof_type=proof_type,
                               status=status,
                               notes=notes)
    
    send_email(subject, recipients, text_body, html_body)

def send_booking_cancelled_notification(booking, cancelled_by, reason=''):
    """Notify about booking cancellation"""
    student = booking.student
    coach = booking.coach.user
    
    # Determine recipient based on who cancelled
    if cancelled_by == 'coach':
        subject = f"Your Booking has been Cancelled - Pickleball Connect"
        recipients = [student.email]
    else:  # cancelled_by == 'student'
        subject = f"Booking Cancellation - Pickleball Connect"
        recipients = [coach.email]
    
    text_body = render_template('email/booking_cancelled.txt', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               cancelled_by=cancelled_by,
                               reason=reason)
    html_body = render_template('email/booking_cancelled.html', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               cancelled_by=cancelled_by,
                               reason=reason)
    
    send_email(subject, recipients, text_body, html_body)

def send_booking_rescheduled_notification(booking, old_date, old_time, old_court):
    """Notify student about rescheduled booking"""
    student = booking.student
    coach = booking.coach.user
    
    subject = f"Your Booking has been Rescheduled - Pickleball Connect"
    recipients = [student.email]
    
    text_body = render_template('email/booking_rescheduled.txt', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               old_date=old_date,
                               old_time=old_time,
                               old_court=old_court)
    html_body = render_template('email/booking_rescheduled.html', 
                               booking=booking,
                               student=student,
                               coach=coach,
                               old_date=old_date,
                               old_time=old_time,
                               old_court=old_court)
    
    send_email(subject, recipients, text_body, html_body)