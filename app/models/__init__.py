# app/models/__init__.py
from app.models.user import User
from app.models.coach import Coach
from app.models.court import Court, CoachCourt
from app.models.court_fee import CourtFee
from app.models.pricing import PricingPlan  # Import this before Booking
from app.models.booking import Availability, Booking
from app.models.session_log import SessionLog 
from app.models.package import BookingPackage, booking_package_association