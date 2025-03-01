from flask_wtf import FlaskForm
from wtforms import SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired

class BookingForm(FlaskForm):
    court_id = SelectField('Court', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Book Sessions')