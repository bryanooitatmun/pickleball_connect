# app/forms/pricing.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField, SelectField, DateField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError

class PricingPlanForm(FlaskForm):
    name = StringField('Plan Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    discount_type = SelectField('Discount Type', choices=[
        ('first_time', 'First-Time Student Discount'),
        ('package', 'Package Deal'),
        ('seasonal', 'Seasonal/Promotional Discount'),
        ('custom', 'Custom Discount')
    ], validators=[DataRequired()])
    
    # For package deals
    sessions_required = IntegerField('Number of Sessions', validators=[Optional(), NumberRange(min=2)])
    
    # Discount amount fields
    percentage_discount = FloatField('Percentage Discount (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    fixed_discount = FloatField('Fixed Discount Amount ($)', validators=[Optional(), NumberRange(min=0)])
    
    # For seasonal discounts
    valid_from = DateField('Valid From', validators=[Optional()])
    valid_to = DateField('Valid To', validators=[Optional()])
    
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Pricing Plan')
    
    def validate(self):
        if not super().validate():
            return False
        
        # At least one discount type must be provided
        if not self.percentage_discount.data and not self.fixed_discount.data:
            self.percentage_discount.errors.append('Please provide either a percentage or fixed discount.')
            return False
        
        # Package deals must specify number of sessions
        if self.discount_type.data == 'package' and not self.sessions_required.data:
            self.sessions_required.errors.append('Number of sessions is required for package deals.')
            return False
        
        # Seasonal discounts must have date range
        if self.discount_type.data == 'seasonal':
            if not self.valid_from.data:
                self.valid_from.errors.append('Start date is required for seasonal discounts.')
                return False
            if not self.valid_to.data:
                self.valid_to.errors.append('End date is required for seasonal discounts.')
                return False
            if self.valid_from.data > self.valid_to.data:
                self.valid_to.errors.append('End date must be after start date.')
                return False
        
        return True