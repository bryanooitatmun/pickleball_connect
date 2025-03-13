# app/models/tag.py
from app import db
from datetime import datetime

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    

class CoachTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    coach = db.relationship('Coach', backref='coach_tags')
    tag = db.relationship('Tag', backref='coach_tags')
    
    # Ensure each coach-tag pair is unique
    __table_args__ = (
        db.UniqueConstraint('coach_id', 'tag_id', name='unique_coach_tag'),
    )
    