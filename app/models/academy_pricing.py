# app/models/academy_pricing.py
from app import db
from datetime import datetime

class AcademyPricingPlan(db.Model):
    __tablename__ = 'academy_pricing_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Discount type: 'package', 'seasonal', 'custom'
    discount_type = db.Column(db.String(20), nullable=False)
    
    # For package deals
    sessions_required = db.Column(db.Integer, nullable=True)
    
    # Discount amount
    percentage_discount = db.Column(db.Float, nullable=True)
    fixed_discount = db.Column(db.Float, nullable=True)
    
    # For first-time deals
    first_time_only = db.Column(db.Boolean, default=False)
    
    # For seasonal/time-limited deals
    valid_from = db.Column(db.Date, nullable=True)
    valid_to = db.Column(db.Date, nullable=True)
    
    # Relationship
    academy = db.relationship('Academy', backref='pricing_plans')
    
    def __repr__(self):
        return f'<AcademyPricingPlan {self.name} for Academy {self.academy_id}>'