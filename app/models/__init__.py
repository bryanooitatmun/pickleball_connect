# app/models/__init__.py
from app.models.user import User
from app.models.coach import Coach
from app.models.court import Court, CoachCourt
from app.models.court_fee import CourtFee
from app.models.connect_points import ConnectPointsConfig, ConnectPoints, ConnectVoucher
from app.models.support import SupportTicket
from app.models.pricing import PricingPlan
from app.models.booking import Availability, Booking
from app.models.session_log import SessionLog 
from app.models.package import BookingPackage, booking_package_association
from app.models.academy import Academy, AcademyCoach, AcademyManager
from app.models.academy_pricing import AcademyPricingPlan  # New model
from app.models.payment import PaymentProof
from app.models.notification import Notification
from app.models.tag import Tag, CoachTag
from app.models.booking import Availability, Booking, AvailabilityReservation