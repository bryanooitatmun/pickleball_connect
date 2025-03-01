# app/forms/student.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange

class StudentProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    birth_date = DateField('Birth Date', validators=[Optional()])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[Optional()])
    location = StringField('Location', validators=[Optional()])
    dupr_rating = FloatField('DUPR Rating', validators=[Optional(), NumberRange(min=1.0, max=8.0)])
    bio = TextAreaField('Bio', validators=[Optional()])
    submit = SubmitField('Save Changes')

class RatingForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField('Comment', validators=[Optional()])
    submit = SubmitField('Submit Rating')
