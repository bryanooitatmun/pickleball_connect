# app/models/coach.py
from app import db
from datetime import datetime

class Coach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False)
    sessions_completed = db.Column(db.Integer, default=0)
    biography = db.Column(db.Text)
    years_experience = db.Column(db.Integer)
    specialties = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone = db.Column(db.String(20))
    payment_info = db.Column(db.JSON, nullable=True)  # Store bank details, QR code path, etc.
    court_booking_instructions = db.Column(db.Text, nullable=True)  # Store specific court booking instructions
    default_court_booking_responsibility = db.Column(db.String(20), default='student')  # 'coach' or 'student'
    
    # Relationships
    user = db.relationship('User', backref='coach_profile')
    courts = db.relationship('CoachCourt', backref='coach', lazy='dynamic')
    availabilities = db.relationship('Availability', backref='coach', lazy='dynamic')
    bookings = db.relationship('Booking', foreign_keys='Booking.coach_id', backref='coach', lazy='dynamic')
    session_logs = db.relationship('SessionLog', backref='coach', lazy='dynamic')
    pricing_plans = db.relationship('PricingPlan', back_populates='coach', lazy='dynamic')
    tags = db.relationship('Tag', secondary='coach_tag', backref='coaches', lazy='dynamic')
    
    def __repr__(self):
        return f'<Coach {self.user.first_name} {self.user.last_name}>'

class CoachImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Coach model
    coach = db.relationship('Coach', backref='showcase_images')