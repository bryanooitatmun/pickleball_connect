# app/models/booking.py (updated)
from app import db
from datetime import datetime

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_booked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    court = db.relationship('Court')
    
    __table_args__ = (
        db.UniqueConstraint('coach_id', 'date', 'start_time', name='unique_coach_timeslot'),
    )
    
    def __repr__(self):
        return f'<Availability {self.coach_id} {self.date} {self.start_time}>'
        
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=False)
    availability_id = db.Column(db.Integer, db.ForeignKey('availability.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    base_price = db.Column(db.Float, nullable=False)  # Original price before discount
    price = db.Column(db.Float, nullable=False)       # Final price after discount
    court_fee = db.Column(db.Float, nullable=False, default=0.0)  # Court fee component
    coach_fee = db.Column(db.Float, nullable=False)               # Coach fee component
    status = db.Column(db.String(20), default='upcoming')  # 'upcoming', 'completed', 'cancelled'
    venue_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Track applied discount if any
    pricing_plan_id = db.Column(db.Integer, db.ForeignKey('pricing_plan.id'), nullable=True)
    discount_amount = db.Column(db.Float, nullable=True)
    discount_percentage = db.Column(db.Float, nullable=True)
    
    # Unique constraint to prevent double bookings
    __table_args__ = (
        db.UniqueConstraint('coach_id', 'date', 'start_time', name='unique_booking_timeslot'),
    )
    
    # Relationships
    availability = db.relationship('Availability')
    court = db.relationship('Court')
    session_log = db.relationship('SessionLog', backref='booking', uselist=False)
    pricing_plan = db.relationship('PricingPlan')

    def mark_completed(self):
        """Mark booking as completed and award connect points"""
        if self.status != 'completed':
            self.status = 'completed'
            
            # Increment coach's completed sessions count
            if self.coach:
                self.coach.sessions_completed += 1
            
            db.session.commit()
        
        # Award connect points
        try:
            from app.models.connect_points import ConnectPoints
            ConnectPoints.award_booking_points(self.id)
        except Exception as e:
            # Log error but don't stop booking completion
            from flask import current_app
            current_app.logger.error(f"Error awarding connect points: {str(e)}")
        
        return self

    def get_connect_points(self):
        """Get connect points awarded for this booking"""
        from app.models.connect_points import ConnectPoints
        points = ConnectPoints.query.filter_by(
            booking_id=self.id, 
            transaction_type='booking_reward'
        ).first()
        
        return points
        


class AvailabilityTemplate(db.Model):
    """Model for saved availability templates"""
    __tablename__ = 'availability_template'
    
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    settings = db.Column(db.JSON, nullable=False)  # Store template settings as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    coach = db.relationship('Coach', backref=db.backref('availability_templates', lazy=True))
    
    def __repr__(self):
        return f'<AvailabilityTemplate {self.name}>'