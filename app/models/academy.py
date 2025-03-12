from app import db
from datetime import datetime

class Academy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    logo_path = db.Column(db.String(255))
    website = db.Column(db.String(128))
    private_url_code = db.Column(db.String(32), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    coaches = db.relationship('AcademyCoach', back_populates='academy', lazy='dynamic')
    managers = db.relationship('AcademyManager', back_populates='academy', lazy='dynamic')
    
    def __repr__(self):
        return f'<Academy {self.name}>'

class AcademyCoach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    academy = db.relationship('Academy', back_populates='coaches')
    coach = db.relationship('Coach', backref='academies')
    
    # Ensure each coach-academy pair is unique
    __table_args__ = (
        db.UniqueConstraint('academy_id', 'coach_id', name='unique_academy_coach'),
    )
    
    def __repr__(self):
        return f'<AcademyCoach {self.academy_id} - {self.coach_id}>'

class AcademyManager(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_owner = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    academy = db.relationship('Academy', back_populates='managers')
    user = db.relationship('User', backref='academy_manager_roles')
    
    # Ensure each user-academy pair is unique
    __table_args__ = (
        db.UniqueConstraint('academy_id', 'user_id', name='unique_academy_manager'),
    )
    
    def __repr__(self):
        return f'<AcademyManager {self.academy_id} - {self.user_id}>'