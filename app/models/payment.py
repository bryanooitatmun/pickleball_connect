# app/models/payment.py
from app import db
from datetime import datetime

class PaymentProof(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    proof_type = db.Column(db.String(20), nullable=False)  # 'coaching' or 'court'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    booking = db.relationship('Booking', backref='payment_proofs')
    
    def __repr__(self):
        return f'<PaymentProof {self.id} {self.proof_type} for Booking {self.booking_id}>'