# app/models/rating.py
from app import db
from datetime import datetime

class CoachRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    rating = db.Column(db.Float, nullable=False)  # Rating from 1 to 5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', backref='ratings_given')
    
    # Ensure each student can only rate a coach once per booking
    __table_args__ = (
        db.UniqueConstraint('student_id', 'booking_id', name='unique_student_booking_rating'),
    )
    
    def __repr__(self):
        return f'<CoachRating {self.student_id} -> {self.coach_id}: {self.rating}>'