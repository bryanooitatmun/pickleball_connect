# app/forms/coach.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange

class CoachProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    location = StringField('Location', validators=[Optional()])
    dupr_rating = FloatField('DUPR Rating', validators=[Optional(), NumberRange(min=1.0, max=8.0)])
    biography = TextAreaField('Biography', validators=[Optional()])
    hourly_rate = FloatField('Hourly Rate', validators=[DataRequired(), NumberRange(min=0)])
    years_experience = StringField('Years of Experience', validators=[Optional()])
    specialties = StringField('Specialties', validators=[Optional()])
    submit = SubmitField('Save Changes')

class AvailabilityForm(FlaskForm):
    court_id = SelectField('Court', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    submit = SubmitField('Add Availability')

class SessionLogForm(FlaskForm):
    title = StringField('Session Title', validators=[DataRequired()])
    coach_notes = TextAreaField('Coach Notes', validators=[Optional()])
    notes = TextAreaField('Student Notes', validators=[Optional()])
    submit = SubmitField('Save Notes')