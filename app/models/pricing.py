# app/models/pricing.py
from app import db
from datetime import datetime

class PricingPlan(db.Model):
    __tablename__ = 'pricing_plan'  # Explicitly define the table name

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Discount type: 'first_time', 'package', 'seasonal', 'custom'
    discount_type = db.Column(db.String(20), nullable=False)
    
    # For package deals
    sessions_required = db.Column(db.Integer, nullable=True)
    
    # Discount amount
    percentage_discount = db.Column(db.Float, nullable=True)  # e.g., 10.0 for 10%
    fixed_discount = db.Column(db.Float, nullable=True)       # e.g., 50.0 for $50 off
    
    # For first-time deals
    first_time_only = db.Column(db.Boolean, default=False)
    
    # For seasonal/time-limited deals
    valid_from = db.Column(db.Date, nullable=True)
    valid_to = db.Column(db.Date, nullable=True)
    
    # Relationship
    coach = db.relationship('Coach', back_populates='pricing_plans')
    
    def __repr__(self):
        return f'<PricingPlan {self.name} for Coach {self.coach_id}>'