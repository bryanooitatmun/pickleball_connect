# app/utils/scheduler.py
from datetime import datetime
from app import db
from app.models.booking import AvailabilityReservation

def cleanup_expired_reservations():
    """Delete expired reservations"""
    try:
        deleted_count = AvailabilityReservation.query.filter(
            AvailabilityReservation.expires_at < datetime.utcnow()
        ).delete()
        db.session.commit()
        print(f"Cleanup: Deleted {deleted_count} expired reservations at {datetime.utcnow()}")
    except Exception as e:
        db.session.rollback()
        print(f"Error cleaning up reservations: {str(e)}")

def init_scheduler_jobs(scheduler):
    """Initialize scheduled jobs"""
    # Run cleanup every 5 minutes
    scheduler.add_job(
        id='cleanup_expired_reservations',
        func=cleanup_expired_reservations,
        trigger='interval',
        minutes=5,
        replace_existing=True
    )