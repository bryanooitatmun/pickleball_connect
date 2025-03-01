# app/models/package.py
from app import db
from datetime import datetime

class BookingPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    pricing_plan_id = db.Column(db.Integer, db.ForeignKey('pricing_plan.id'), nullable=False)
    
    total_sessions = db.Column(db.Integer, nullable=False)
    sessions_booked = db.Column(db.Integer, default=0)
    sessions_completed = db.Column(db.Integer, default=0)
    
    total_price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float, nullable=False)  # Without discount
    discount_amount = db.Column(db.Float, nullable=True)
    
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    coach = db.relationship('Coach')
    student = db.relationship('User', foreign_keys=[student_id])
    pricing_plan = db.relationship('PricingPlan')
    bookings = db.relationship('Booking', secondary='booking_package_association')
    
    def __repr__(self):
        return f'<BookingPackage {self.id} Student:{self.student_id} Coach:{self.coach_id}>'

# Association table for many-to-many relationship between packages and bookings
booking_package_association = db.Table('booking_package_association',
    db.Column('package_id', db.Integer, db.ForeignKey('booking_package.id')),
    db.Column('booking_id', db.Integer, db.ForeignKey('booking.id'))
)