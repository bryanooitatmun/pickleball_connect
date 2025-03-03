# app/models/support.py
from app import db
from datetime import datetime

class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='support_tickets')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_tickets')
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id], backref='resolved_tickets')
    responses = db.relationship('TicketResponse', backref='ticket', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<SupportTicket {self.id}: {self.subject}>'

class TicketResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='ticket_responses')
    
    def __repr__(self):
        return f'<TicketResponse {self.id} for Ticket {self.ticket_id}>'