# app/models/user.py
from app import db, login
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(16))
    location = db.Column(db.String(128))
    phone = db.Column(db.String(20))  # Added phone field
    dupr_rating = db.Column(db.Float)  # Pickleball skill rating
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255))  # Path to profile picture
    is_coach = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_temporary = db.Column(db.Boolean, default=False)  # Flag for temporary users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Bookings as a student
    bookings = db.relationship('Booking', 
                               foreign_keys='Booking.student_id', 
                               backref='student', 
                               lazy='dynamic')
    
    # @property
    # def password(self):
    #     raise AttributeError('password is not a readable attribute')
    
    # @password.setter
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<User {self.email}>'

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))