# run.py
from app import create_app, db
from app.models.user import User
from app.models.coach import Coach
from app.models.court import Court, CoachCourt
from app.models.court_fee import CourtFee
from app.models.support import SupportTicket
from app.models.booking import Availability, Booking

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Coach': Coach, 
        'Court': Court,
        'CoachCourt': CoachCourt,
        'CoachFee': CoachFee,
        'Availability': Availability,
        'Booking': Booking,
        'SessionLog': SessionLog,
        'PricingPlan': PricingPlan,
        'BookingPackage': BookingPackage,
        'SupportTicket': SupportTicket
    }