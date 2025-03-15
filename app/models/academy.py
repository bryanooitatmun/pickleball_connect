from app import db
from datetime import datetime

academy_tag = db.Table('academy_tag',
    db.Column('academy_id', db.Integer, db.ForeignKey('academy.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Academy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    logo_path = db.Column(db.String(255))
    website = db.Column(db.String(128))
    private_url_code = db.Column(db.String(32), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    payment_info = db.Column(db.JSON, nullable=True)  # Store bank details, payment reference, etc.
    court_payment_details = db.Column(db.JSON, nullable=True)  # For separate court payment info
    
    # Relationships
    coaches = db.relationship('AcademyCoach', back_populates='academy', lazy='dynamic')
    managers = db.relationship('AcademyManager', back_populates='academy', lazy='dynamic')
    tags = db.relationship('Tag', secondary=academy_tag, backref=db.backref('academies', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Academy {self.name}>'

class AcademyCoach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('academy_coach_role.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    academy = db.relationship('Academy', back_populates='coaches')
    coach = db.relationship('Coach', backref='academies')
    role = db.relationship('AcademyCoachRole', backref='academy_coaches')
    
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

class AcademyCoachRole(db.Model):
    """Model for coach roles within an academy"""
    __tablename__ = 'academy_coach_role'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    ordering = db.Column(db.Integer, default=100)  # Lower numbers appear first
    
    def __repr__(self):
        return f'<AcademyCoachRole {self.name}>'