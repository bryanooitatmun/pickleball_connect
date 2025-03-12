# app/models/package.py
from app import db
from datetime import datetime

class BookingPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=True)  # Now nullable
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=True)  # New field
    pricing_plan_id = db.Column(db.Integer, db.ForeignKey('pricing_plan.id'), nullable=True)  # Now nullable
    academy_pricing_plan_id = db.Column(db.Integer, db.ForeignKey('academy_pricing_plan.id'), nullable=True)  # New field
    
    package_type = db.Column(db.String(20), default='coach')  # 'coach' or 'academy'
    
    total_sessions = db.Column(db.Integer, nullable=False)
    sessions_booked = db.Column(db.Integer, default=0)
    sessions_completed = db.Column(db.Integer, default=0)
    
    total_price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, nullable=True)
    
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    coach = db.relationship('Coach', foreign_keys=[coach_id])
    academy = db.relationship('Academy', foreign_keys=[academy_id], backref='packages')
    student = db.relationship('User', foreign_keys=[student_id])
    pricing_plan = db.relationship('PricingPlan')
    academy_pricing_plan = db.relationship('AcademyPricingPlan')
    bookings = db.relationship('Booking', secondary='booking_package_association')
    
    # Ensure either coach_id or academy_id is set, but not both
    __table_args__ = (
        db.CheckConstraint('(coach_id IS NOT NULL AND academy_id IS NULL) OR (coach_id IS NULL AND academy_id IS NOT NULL)', 
                          name='check_coach_or_academy'),
        db.CheckConstraint('(pricing_plan_id IS NOT NULL AND academy_pricing_plan_id IS NULL) OR (pricing_plan_id IS NULL AND academy_pricing_plan_id IS NOT NULL)', 
                          name='check_pricing_plan_type')
    )
    
    def can_use_for_coach(self, coach_id):
        """Check if this package can be used for a specific coach"""
        # Coach-specific package must match exactly
        if self.package_type == 'coach':
            return self.coach_id == coach_id
        
        # Academy package - check if coach is in the academy
        if self.package_type == 'academy':
            from app.models.academy import AcademyCoach
            return AcademyCoach.query.filter_by(
                academy_id=self.academy_id,
                coach_id=coach_id,
                is_active=True
            ).first() is not None
        
        return False

# Association table for many-to-many relationship between packages and bookings
booking_package_association = db.Table('booking_package_association',
    db.Column('package_id', db.Integer, db.ForeignKey('booking_package.id')),
    db.Column('booking_id', db.Integer, db.ForeignKey('booking.id'))
)