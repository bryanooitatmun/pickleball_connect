from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship
from app import db
from datetime import datetime
import random

class ConnectPointsConfig(db.Model):
    """Configuration for Connect Points system"""
    __tablename__ = 'connect_points_config'
    
    id = Column(Integer, primary_key=True)
    base_multiplier = Column(Float, default=1.0)  # Base multiplier for points calculation
    min_points_factor = Column(Float, default=0.8)  # Minimum factor for randomization
    max_points_factor = Column(Float, default=1.2)  # Maximum factor for randomization
    enabled = Column(Boolean, default=True)  # Whether the points system is enabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_active_config(cls):
        """Get the active configuration or create a default one"""
        config = cls.query.first()
        if not config:
            config = cls(
                base_multiplier=1.0,
                min_points_factor=0.8,
                max_points_factor=1.2,
                enabled=True
            )
            db.session.add(config)
            db.session.commit()
        return config

    @classmethod
    def calculate_points(cls, booking_price):
        """Calculate connect points for a booking"""
        config = cls.get_active_config()
        
        if not config.enabled:
            return 0
        
        # Base points calculation
        base_points = int(booking_price * config.base_multiplier)
        
        # Apply randomization factor
        random_factor = random.uniform(config.min_points_factor, config.max_points_factor)
        final_points = int(base_points * random_factor)
        
        # Ensure at least 1 point for any non-zero booking
        return max(1, final_points) if booking_price > 0 else 0


class ConnectPoints(db.Model):
    """Student Connect Points balance and transactions"""
    __tablename__ = 'connect_points'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    booking_id = Column(Integer, ForeignKey('booking.id'), nullable=True)
    voucher_id = Column(Integer, ForeignKey('connect_voucher.id'), nullable=True)
    points = Column(Integer, nullable=False)  # Positive for earned, negative for spent
    transaction_type = Column(String(20), nullable=False)  # 'booking_reward', 'voucher_redemption', 'admin_adjustment'
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking")
    voucher = relationship("ConnectVoucher")
    
    @classmethod
    def get_user_balance(cls, user_id):
        """Get the current points balance for a user"""
        total = db.session.query(db.func.sum(cls.points)).filter(cls.user_id == user_id).scalar() or 0
        return total

    @classmethod
    def award_booking_points(cls, booking_id):
        """Award points for a completed booking"""
        from app.models.booking import Booking
        
        # Get the booking
        booking = Booking.query.get(booking_id)
        if not booking or booking.status != 'completed':
            return None
        
        # Check if points were already awarded for this booking
        existing_points = cls.query.filter_by(booking_id=booking_id, transaction_type='booking_reward').first()
        if existing_points:
            return existing_points
        
        # Calculate points to award
        points_to_award = ConnectPointsConfig.calculate_points(booking.price)
        
        # Create points transaction
        points_transaction = cls(
            user_id=booking.student_id,
            booking_id=booking.id,
            points=points_to_award,
            transaction_type='booking_reward',
            description=f"Points earned from coaching session with {booking.coach.user.first_name} {booking.coach.user.last_name}"
        )
        
        db.session.add(points_transaction)
        db.session.commit()
        
        return points_transaction


class ConnectVoucher(db.Model):
    """Vouchers that can be redeemed with Connect Points"""
    __tablename__ = 'connect_voucher'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    points_cost = Column(Integer, nullable=False)
    discount_amount = Column(Float)  # Fixed amount discount
    discount_percentage = Column(Float)  # Percentage discount
    code = Column(String(20), unique=True)  # Voucher code
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    redemptions = relationship("ConnectPoints", back_populates="voucher")
    
    @classmethod
    def get_active_vouchers(cls):
        """Get all active vouchers"""
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def redeem_voucher(cls, voucher_id, user_id):
        """Redeem a voucher for a user"""
        voucher = cls.query.get(voucher_id)
        if not voucher or not voucher.is_active:
            return None, "Voucher not available"
        
        # Check if user has enough points
        user_balance = ConnectPoints.get_user_balance(user_id)
        if user_balance < voucher.points_cost:
            return None, "Insufficient points"
        
        # Create redemption transaction
        redemption = ConnectPoints(
            user_id=user_id,
            voucher_id=voucher.id,
            points=-voucher.points_cost,  # Negative points for spending
            transaction_type='voucher_redemption',
            description=f"Redeemed voucher: {voucher.name}"
        )
        
        db.session.add(redemption)
        db.session.commit()
        
        return redemption, voucher.code
