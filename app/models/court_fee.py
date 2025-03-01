# app/models/court_fee.py
from app import db
from datetime import datetime, time

class CourtFee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)  # Start time for this fee rate
    end_time = db.Column(db.Time, nullable=False)    # End time for this fee rate
    fee = db.Column(db.Float, nullable=False)        # Hourly fee during this time period
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    court = db.relationship('Court', backref='fees')
    
    def __repr__(self):
        return f'<CourtFee {self.court_id} {self.start_time}-{self.end_time}: ${self.fee}>'