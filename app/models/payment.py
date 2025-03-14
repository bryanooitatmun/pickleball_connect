# app/models/payment.py
from app import db
from datetime import datetime

class PaymentProof(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)  # Changed to nullable
    package_id = db.Column(db.Integer, db.ForeignKey('booking_package.id'), nullable=True)  # Added package_id
    image_path = db.Column(db.String(255), nullable=False)
    proof_type = db.Column(db.String(20), nullable=False)  # 'coaching', 'court', or 'package'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = db.relationship('Booking', backref='payment_proofs', foreign_keys=[booking_id])
    package = db.relationship('BookingPackage', backref='payment_proofs', foreign_keys=[package_id])
    
    # Add constraint to ensure either booking_id or package_id is set, but not both
    __table_args__ = (
        db.CheckConstraint(
            '(booking_id IS NOT NULL AND package_id IS NULL) OR (booking_id IS NULL AND package_id IS NOT NULL)',
            name='check_payment_proof_association'
        ),
    )
    
    def __repr__(self):
        if self.booking_id:
            return f'<PaymentProof {self.id} {self.proof_type} for Booking {self.booking_id}>'
        else:
            return f'<PaymentProof {self.id} {self.proof_type} for Package {self.package_id}>'
