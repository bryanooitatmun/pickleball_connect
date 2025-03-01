# app/models/session_log.py
from app import db
from datetime import datetime

class SessionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False, unique=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(128), default='Pickleball Session')
    notes = db.Column(db.Text)
    coach_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])
    
    def __repr__(self):
        return f'<SessionLog {self.id} {self.title}>'