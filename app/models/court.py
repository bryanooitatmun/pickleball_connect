# app/models/court.py
from app import db
from datetime import datetime

class Court(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    address = db.Column(db.String(256))
    city = db.Column(db.String(64))
    state = db.Column(db.String(32))
    zip_code = db.Column(db.String(16))
    indoor = db.Column(db.Boolean, default=False)
    number_of_courts = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Court {self.name}>'

class CoachCourt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure each coach-court pair is unique
    __table_args__ = (
        db.UniqueConstraint('coach_id', 'court_id', name='unique_coach_court'),
    )
    
    def __repr__(self):
        return f'<CoachCourt {self.coach_id} - {self.court_id}>'