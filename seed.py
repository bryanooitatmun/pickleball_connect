# Modify seed.py to include court fees, coach images, and support tickets

from app import create_app, db
from app.models.user import User
from app.models.coach import Coach, CoachImage
from app.models.court import Court, CoachCourt
from app.models.booking import Booking, Availability
from app.models.session_log import SessionLog
from app.models.rating import CoachRating
from app.models.pricing import PricingPlan
from app.models.package import BookingPackage, booking_package_association
from app.models.court_fee import CourtFee 
from app.models.support import SupportTicket, TicketResponse
from datetime import datetime, timedelta, time
import random
import uuid
import os
import shutil

app = create_app()

def seed_database():
    with app.app_context():
        # Clear existing data
        db.session.query(booking_package_association).delete()
        db.session.query(BookingPackage).delete()
        db.session.query(SessionLog).delete()
        db.session.query(Booking).delete()
        db.session.query(Availability).delete()
        db.session.query(CoachRating).delete()
        db.session.query(PricingPlan).delete()
        db.session.query(CoachCourt).delete()
        db.session.query(CourtFee).delete()
        db.session.query(TicketResponse).delete()
        db.session.query(SupportTicket).delete()
        db.session.query(CoachImage).delete()  # Delete coach showcase images
        db.session.query(Coach).delete()
        db.session.query(Court).delete()
        db.session.query(User).delete()
        db.session.commit()
        
        # Create courts
        courts = [
            Court(name="City Park Courts", address="123 Park Ave", city="New York", state="NY", zip_code="10001"),
            Court(name="Downtown Club", address="456 Main St", city="New York", state="NY", zip_code="10002"),
            Court(name="Riverside Courts", address="789 River Rd", city="New York", state="NY", zip_code="10003")
        ]
        
        db.session.add_all(courts)
        db.session.commit()
        
        # Create court fees for different time slots
        court_fees = []
        
        # City Park Courts fees (varies by time of day)
        court_fees.extend([
            CourtFee(court_id=courts[0].id, start_time=time(6, 0), end_time=time(12, 0), fee=25.0),  # Morning
            CourtFee(court_id=courts[0].id, start_time=time(12, 0), end_time=time(17, 0), fee=30.0), # Afternoon
            CourtFee(court_id=courts[0].id, start_time=time(17, 0), end_time=time(22, 0), fee=35.0)  # Evening peak
        ])
        
        # Downtown Club fees (premium venue, higher fees)
        court_fees.extend([
            CourtFee(court_id=courts[1].id, start_time=time(6, 0), end_time=time(12, 0), fee=35.0),  # Morning
            CourtFee(court_id=courts[1].id, start_time=time(12, 0), end_time=time(17, 0), fee=40.0), # Afternoon
            CourtFee(court_id=courts[1].id, start_time=time(17, 0), end_time=time(22, 0), fee=50.0)  # Evening peak
        ])
        
        # Riverside Courts fees (lowest fees)
        court_fees.extend([
            CourtFee(court_id=courts[2].id, start_time=time(6, 0), end_time=time(12, 0), fee=20.0),  # Morning
            CourtFee(court_id=courts[2].id, start_time=time(12, 0), end_time=time(17, 0), fee=25.0), # Afternoon
            CourtFee(court_id=courts[2].id, start_time=time(17, 0), end_time=time(22, 0), fee=30.0)  # Evening peak
        ])
        
        db.session.add_all(court_fees)
        db.session.commit()
        
        # Create users and coaches
        # Admin user
        admin = User(
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            is_coach=False,
            is_admin=True,  # Add admin flag
            dupr_rating=4.0,
            location="New York, NY"
        )
        admin.set_password("password123")
        
        # Create profile picture for admin
        admin_profile_pic = f"static/uploads/profile_pics/{uuid.uuid4()}_admin_profile.jpeg"
        admin.profile_picture = admin_profile_pic
        db.session.add(admin)
        
        # Coaches
        john = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            is_coach=True,
            dupr_rating=5.2,
            location="New York, NY",
            bio="John is a passionate pickleball coach with over 5 years of experience."
        )
        john.set_password("password123")
        
        # Create profile picture for John
        john_profile_pic = f"static/uploads/profile_pics/{uuid.uuid4()}_coach_john.jpeg"
        john.profile_picture = john_profile_pic
        db.session.add(john)
        
        jane = User(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            is_coach=True,
            dupr_rating=5.5,
            location="New York, NY",
            bio="Jane is a tournament champion and experienced coach."
        )
        jane.set_password("password123")
        
        # Create profile picture for Jane
        jane_profile_pic = f"static/uploads/profile_pics/{uuid.uuid4()}_coach_jane.jpeg"
        jane.profile_picture = jane_profile_pic
        db.session.add(jane)
        
        # Regular students (5 students)
        students = []
        student_data = [
            ("Alice", "Johnson", "alice@example.com", 3.5, "Beginner player looking to improve"),
            ("Bob", "Smith", "bob@example.com", 4.2, "Intermediate player focusing on strategy"),
            ("Charlie", "Brown", "charlie@example.com", 4.5, "Advanced player working on tournament play"),
            ("Diana", "Lee", "diana@example.com", 3.8, "Intermediate player who loves doubles"),
            ("Ethan", "Davis", "ethan@example.com", 4.0, "Working on improving my third shot drop")
        ]
        
        for first, last, email, rating, bio in student_data:
            student = User(
                first_name=first,
                last_name=last,
                email=email,
                is_coach=False,
                dupr_rating=rating,
                location="New York, NY",
                bio=bio
            )
            student.set_password("password123")
            
            # 50% chance to have a profile picture
            if random.random() < 0.5:
                student_profile_pic = f"static/uploads/profile_pics/{uuid.uuid4()}_{first.lower()}_profile.jpeg"
                student.profile_picture = student_profile_pic
            
            db.session.add(student)
            students.append(student)
        
        db.session.commit()
        
        # Create coach profiles
        john_coach = Coach(
            user_id=john.id,
            hourly_rate=50.0,
            sessions_completed=120,
            biography="John is a passionate pickleball coach with over 5 years of experience. He specializes in helping beginners develop their skills and advanced players refine their strategies.",
            years_experience=5,
            specialties="Beginner Training, Strategy Development, Footwork"
        )
        db.session.add(john_coach)
        
        jane_coach = Coach(
            user_id=jane.id,
            hourly_rate=60.0,
            sessions_completed=150,
            biography="Jane is a tournament champion and experienced coach. She focuses on competitive play and advanced techniques.",
            years_experience=7,
            specialties="Tournament Preparation, Advanced Techniques, Mental Game"
        )
        db.session.add(jane_coach)
        
        db.session.commit()
        
        # Create coach showcase images
        showcase_images = []
        
        # John's showcase images (3-6 images)
        john_image_count = random.randint(3, 6)
        for i in range(john_image_count):
            image_path = f"static/uploads/showcase_images/{uuid.uuid4()}_john_showcase_{i+1}.jpeg"
            showcase_images.append(CoachImage(
                coach_id=john_coach.id,
                image_path=image_path,
                description=f"Coach John teaching {random.choice(['serves', 'dinks', 'strategy', 'footwork', 'technique'])}",
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            ))
        
        # Jane's showcase images (3-6 images)
        jane_image_count = random.randint(3, 6)
        for i in range(jane_image_count):
            image_path = f"static/uploads/showcase_images/{uuid.uuid4()}_jane_showcase_{i+1}.jpeg"
            showcase_images.append(CoachImage(
                coach_id=jane_coach.id,
                image_path=image_path,
                description=f"Coach Jane demonstrating {random.choice(['advanced serves', 'tournament play', 'doubles strategy', 'volley technique', 'third shot drops'])}",
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            ))
        
        db.session.add_all(showcase_images)
        db.session.commit()
        
        # Associate coaches with courts
        for court in courts:
            db.session.add(CoachCourt(coach_id=john_coach.id, court_id=court.id))
            db.session.add(CoachCourt(coach_id=jane_coach.id, court_id=court.id))
        
        db.session.commit()
        
        # Create pricing plans for coaches
        # John's pricing plans
        john_plans = [
            PricingPlan(
                coach_id=john_coach.id,
                name="First-Time Student Deal",
                description="Special discount for first-time students",
                discount_type="first_time",
                percentage_discount=15.0,
                first_time_only=True,
                is_active=True
            ),
            PricingPlan(
                coach_id=john_coach.id,
                name="5-Session Package",
                description="Bundle of 5 sessions at a discounted rate",
                discount_type="package",
                sessions_required=5,
                percentage_discount=10.0,
                is_active=True
            ),
            PricingPlan(
                coach_id=john_coach.id,
                name="Summer Special",
                description="Special summer discount for all sessions",
                discount_type="seasonal",
                percentage_discount=12.0,
                valid_from=datetime.now() - timedelta(days=30),
                valid_to=datetime.now() + timedelta(days=60),
                is_active=True
            )
        ]
        
        # Jane's pricing plans
        jane_plans = [
            PricingPlan(
                coach_id=jane_coach.id,
                name="Welcome Discount",
                description="Discount for first-time students",
                discount_type="first_time",
                fixed_discount=20.0,
                first_time_only=True,
                is_active=True
            ),
            PricingPlan(
                coach_id=jane_coach.id,
                name="10-Session Package",
                description="Intensive training package of 10 sessions",
                discount_type="package",
                sessions_required=10,
                percentage_discount=15.0,
                is_active=True
            ),
            PricingPlan(
                coach_id=jane_coach.id,
                name="Weekend Special",
                description="Special discount for weekend sessions",
                discount_type="custom",
                percentage_discount=8.0,
                is_active=True
            )
        ]
        
        db.session.add_all(john_plans + jane_plans)
        db.session.commit()
        
        # Create availability for the next 14 days
        today = datetime.now().date()
        
        # Each coach has 3 available time slots per day for the next 2 weeks
        for day in range(14):
            current_date = today + timedelta(days=day)
            
            # Skip availability creation for past dates
            if current_date < today:
                continue
            
            # John's availability
            john_slots = [
                (time(9), time(10), courts[0].id),  # Morning at City Park
                (time(13), time(14), courts[1].id),  # Afternoon at Downtown Club
                (time(17), time(18), courts[2].id)   # Evening at Riverside
            ]
            
            for start, end, court_id in john_slots:
                is_booked = random.random() < 0.3  # 30% chance of being booked
                availability = Availability(
                    coach_id=john_coach.id,
                    court_id=court_id,
                    date=current_date,
                    start_time=start,
                    end_time=end,
                    is_booked=is_booked
                )
                db.session.add(availability)
            
            # Jane's availability
            jane_slots = [
                (time(10), time(11), courts[0].id),  # Morning at City Park
                (time(14), time(15), courts[1].id),  # Afternoon at Downtown Club
                (time(18), time(19), courts[2].id)   # Evening at Riverside
            ]
            
            for start, end, court_id in jane_slots:
                is_booked = random.random() < 0.3  # 30% chance of being booked
                availability = Availability(
                    coach_id=jane_coach.id,
                    court_id=court_id,
                    date=current_date,
                    start_time=start,
                    end_time=end,
                    is_booked=is_booked
                )
                db.session.add(availability)
        
        db.session.commit()
        
        # Create bookings and session logs
        # Past bookings (completed)
        past_bookings = []
        
        # Generate past bookings for both coaches with all students
        for day in range(1, 31):  # Last 30 days
            past_date = today - timedelta(days=day)
            
            # For each coach, create 0-1 bookings per day
            for coach in [john_coach, jane_coach]:
                num_bookings = random.randint(0, 1)
                for _ in range(num_bookings):
                    # Pick a random student
                    student = random.choice(students)
                    
                    # Pick a random court
                    court = random.choice(courts)
                    
                    # Create a random time slot
                    hour = random.randint(9, 18)
                    start_time = time(hour)
                    end_time = time(hour+1)
                    
                    # Get court fee for this time
                    court_fee = 0
                    for fee in court_fees:
                        if fee.court_id == court.id and fee.start_time <= start_time <= fee.end_time:
                            court_fee = fee.fee
                            break
                    
                    # Coach fee
                    coach_fee = coach.hourly_rate
                    
                    # Base price (coach + court fee)
                    base_price = coach_fee + court_fee
                    price = base_price
                    
                    # Maybe apply a pricing plan
                    pricing_plan = None
                    discount_amount = None
                    discount_percentage = None
                    
                    # 50% chance of applying a discount
                    if random.random() < 0.5:
                        if coach == john_coach:
                            pricing_plan = random.choice(john_plans)
                        else:
                            pricing_plan = random.choice(jane_plans)
                        
                        # Apply discount (only to coach fee, not court fee)
                        if pricing_plan.percentage_discount:
                            discount_percentage = pricing_plan.percentage_discount
                            discount_amount = coach_fee * (discount_percentage / 100)
                            price = base_price - discount_amount
                        elif pricing_plan.fixed_discount:
                            discount_amount = pricing_plan.fixed_discount
                            price = base_price - discount_amount
                    
                    # Create booking
                    booking = Booking(
                        student_id=student.id,
                        coach_id=coach.id,
                        court_id=court.id,
                        availability_id=1,  # This is a placeholder as we're generating past bookings
                        date=past_date,
                        start_time=start_time,
                        end_time=end_time,
                        base_price=base_price,
                        price=price,
                        coach_fee=coach_fee,    # New field
                        court_fee=court_fee,    # New field
                        status="completed",
                        pricing_plan_id=pricing_plan.id if pricing_plan else None,
                        discount_amount=discount_amount,
                        discount_percentage=discount_percentage
                    )
                    
                    db.session.add(booking)
                    db.session.flush()  # Get the booking ID
                    
                    # Create a session log for this booking
                    session_log = SessionLog(
                        booking_id=booking.id,
                        coach_id=coach.id,
                        student_id=student.id,
                        title=f"Pickleball Session with {student.first_name}",
                        notes=f"Worked on {random.choice(['serves', 'returns', 'dinks', 'third shot drops', 'volleying', 'strategy'])} today. {student.first_name} is making good progress!",
                        coach_notes=f"Continue focusing on {random.choice(['footwork', 'paddle position', 'consistency', 'shot selection', 'court positioning'])}"
                    )
                    
                    db.session.add(session_log)
                    past_bookings.append(booking)
        
        db.session.commit()
        
        # Create upcoming bookings (future dates)
        future_bookings = []
        
        # Get all availabilities
        availabilities = Availability.query.filter(
            Availability.date >= today,
            Availability.is_booked == True
        ).all()
        
        # Create a booking for each booked availability
        for availability in availabilities:
            # Pick a random student
            student = random.choice(students)
            
            # Get court fee for this time
            court_fee = 0
            for fee in court_fees:
                if fee.court_id == availability.court_id and fee.start_time <= availability.start_time <= fee.end_time:
                    court_fee = fee.fee
                    break
            
            # Coach fee
            coach_fee = availability.coach.hourly_rate
            
            # Base price (coach + court fee)
            base_price = coach_fee + court_fee
            price = base_price
            
            # Maybe apply a pricing plan
            pricing_plan = None
            discount_amount = None
            discount_percentage = None
            
            # 50% chance of applying a discount
            if random.random() < 0.5:
                if availability.coach_id == john_coach.id:
                    pricing_plan = random.choice(john_plans)
                else:
                    pricing_plan = random.choice(jane_plans)
                
                # Apply discount (only to coach fee, not court fee)
                if pricing_plan.percentage_discount:
                    discount_percentage = pricing_plan.percentage_discount
                    discount_amount = coach_fee * (discount_percentage / 100)
                    price = base_price - discount_amount
                elif pricing_plan.fixed_discount:
                    discount_amount = pricing_plan.fixed_discount
                    price = base_price - discount_amount
            
            # Create booking
            booking = Booking(
                student_id=student.id,
                coach_id=availability.coach_id,
                court_id=availability.court_id,
                availability_id=availability.id,
                date=availability.date,
                start_time=availability.start_time,
                end_time=availability.end_time,
                base_price=base_price,
                price=price,
                coach_fee=coach_fee,    # New field
                court_fee=court_fee,    # New field
                status="upcoming",
                pricing_plan_id=pricing_plan.id if pricing_plan else None,
                discount_amount=discount_amount,
                discount_percentage=discount_percentage
            )
            
            db.session.add(booking)
            future_bookings.append(booking)
        
        db.session.commit()
        
        # Create coach ratings
        for coach in [john_coach, jane_coach]:
            # Each coach gets rated by 70% of their past students
            coach_students = set([booking.student_id for booking in past_bookings if booking.coach_id == coach.id])
            for student_id in coach_students:
                # 70% chance to rate
                if random.random() < 0.7:
                    # Ratings between 3-5
                    rating_value = random.randint(3, 5)
                    
                    # Create the rating
                    coach_rating = CoachRating(
                        coach_id=coach.id,
                        student_id=student_id,
                        rating=rating_value,
                        comment=random.choice([
                            "Great coach! Really helped me improve my game.",
                            "Very knowledgeable and patient coach.",
                            "Excellent teaching style. Would recommend!",
                            "Helped me a lot with my technique.",
                            "Fantastic coach, learned a lot in our sessions."
                        ]) if random.random() < 0.7 else None  # 70% chance to have a comment
                    )
                    
                    db.session.add(coach_rating)
        
        db.session.commit()
        
        # Create booking packages
        for coach in [john_coach, jane_coach]:
            # Find package pricing plans
            package_plans = PricingPlan.query.filter_by(
                coach_id=coach.id,
                discount_type="package"
            ).all()
            
            # Each student has a 40% chance of having bought a package
            for student in students:
                if random.random() < 0.4 and package_plans:
                    # Choose a random package plan
                    plan = random.choice(package_plans)
                    
                    # Calculate price
                    total_sessions = plan.sessions_required
                    original_price = coach.hourly_rate * total_sessions
                    
                    if plan.percentage_discount:
                        discount_amount = original_price * (plan.percentage_discount / 100)
                    elif plan.fixed_discount:
                        discount_amount = plan.fixed_discount
                    else:
                        discount_amount = 0
                    
                    total_price = original_price - discount_amount
                    
                    # Randomly decide how many sessions have been used
                    sessions_booked = random.randint(0, total_sessions)
                    sessions_completed = random.randint(0, sessions_booked)
                    
                    # Create package
                    package = BookingPackage(
                        student_id=student.id,
                        coach_id=coach.id,
                        pricing_plan_id=plan.id,
                        total_sessions=total_sessions,
                        sessions_booked=sessions_booked,
                        sessions_completed=sessions_completed,
                        total_price=total_price,
                        original_price=original_price,
                        discount_amount=discount_amount,
                        purchase_date=datetime.now() - timedelta(days=random.randint(5, 30)),
                        expires_at=datetime.now() + timedelta(days=random.randint(30, 90))
                    )
                    
                    db.session.add(package)
                    
                    # Associate some random bookings with this package
                    if sessions_booked > 0:
                        # Get the student's bookings with this coach
                        student_bookings = [b for b in past_bookings + future_bookings 
                                            if b.student_id == student.id and b.coach_id == coach.id]
                        
                        # Randomly select up to sessions_booked bookings
                        if student_bookings:
                            num_to_associate = min(sessions_booked, len(student_bookings))
                            for booking in random.sample(student_bookings, num_to_associate):
                                # Add to the association table
                                stmt = booking_package_association.insert().values(
                                    package_id=package.id,
                                    booking_id=booking.id
                                )
                                db.session.execute(stmt)
        
        # Create support tickets
        support_tickets = []
        
        # Support ticket subjects and message templates
        ticket_subjects = [
            "Booking issue with coach",
            "Payment problem",
            "Need to reschedule session",
            "Court reservation confusion",
            "App feature request",
            "Account access issue",
            "Feedback on coaching session",
            "Package discount not applied",
            "Court fee question",
            "Can't update profile"
        ]
        
        ticket_messages = [
            "I'm having trouble with my recent booking with Coach {coach}. The system shows {issue}.",
            "My payment for the session on {date} didn't go through, but I was charged. Can you help?",
            "I need to reschedule my upcoming session on {date} due to a personal emergency.",
            "I'm confused about the court reservation system. When I try to book {court}, it shows as unavailable but the schedule looks open.",
            "It would be great if the app could include a feature to {feature_request}.",
            "I'm unable to access my account since yesterday. It keeps showing an error message.",
            "I wanted to provide feedback about my recent session with Coach {coach}. Overall it was {quality}, but {feedback}.",
            "I purchased a package deal, but the discount wasn't applied to my recent booking.",
            "I'm confused about the court fees at {court}. Can you explain how they're calculated?",
            "I've been trying to update my profile picture, but I keep getting an error message."
        ]
        
        # Create 10-15 tickets from students
        num_tickets = random.randint(10, 15)
        
        # Status options and priorities
        statuses = ["open", "in_progress", "resolved"]
        priorities = ["low", "medium", "high"]
        
        for i in range(num_tickets):
            # Select a random student
            student = random.choice(students)
            
            # Select a random coach for references in the ticket
            coach_user = random.choice([john, jane])
            
            # Random subject and message
            subject_idx = random.randint(0, len(ticket_subjects) - 1)
            subject = ticket_subjects[subject_idx]
            
            # Generate message with placeholders filled
            message = ticket_messages[subject_idx].format(
                coach=f"{coach_user.first_name} {coach_user.last_name}",
                issue=random.choice(["a double booking", "incorrect pricing", "wrong time slot"]),
                date=datetime.now().strftime("%B %d"),
                court=random.choice([c.name for c in courts]),
                feature_request=random.choice(["see my progress over time", "rate coaches after each session", "get notifications for court availability"]),
                quality=random.choice(["excellent", "good", "satisfactory", "disappointing"]),
                feedback=random.choice(["I'd like more focus on strategy", "we spent too much time on drills", "the pace was too slow for my level", "I learned a lot"])
            )
            
            # Random status with weighting (more open/in-progress than resolved)
            status_weights = [0.4, 0.4, 0.2]  # 40% open, 40% in-progress, 20% resolved
            status = random.choices(statuses, weights=status_weights, k=1)[0]
            
            # Random priority
            priority_weights = [0.3, 0.5, 0.2]  # 30% low, 50% medium, 20% high
            priority = random.choices(priorities, weights=priority_weights, k=1)[0]
            
            # Create timestamp (newer for open/in-progress, older for resolved)
            if status == "resolved":
                created_at = datetime.now() - timedelta(days=random.randint(7, 30))
                resolved_at = created_at + timedelta(days=random.randint(1, 5))
                resolved_by_id = admin.id
            else:
                created_at = datetime.now() - timedelta(days=random.randint(0, 7))
                resolved_at = None
                resolved_by_id = None
            
            # Assignment status (only for in-progress)
            assigned_to_id = admin.id if status == "in_progress" else None
            
            # Create ticket
            ticket = SupportTicket(
                user_id=student.id,
                subject=subject,
                message=message,
                status=status,
                priority=priority,
                assigned_to_id=assigned_to_id,
                resolved_by_id=resolved_by_id,
                created_at=created_at,
                updated_at=created_at,
                resolved_at=resolved_at
            )
            
            db.session.add(ticket)
            support_tickets.append(ticket)
        
        # Create 5-10 tickets from coaches
        num_coach_tickets = random.randint(5, 10)
        
        for i in range(num_coach_tickets):
            # Select a random coach
            coach_user = random.choice([john, jane])
            
            # Coach-specific subjects
            coach_subjects = [
                "Issue with availability schedule",
                "Need to update my court access",
                "Student booking problem",
                "Payment distribution question",
                "Session log not saving properly",
                "Need to cancel multiple sessions",
                "Showcase image upload issue",
                "Rating system question",
                "Pricing plan configuration help"
            ]
            
            # Coach-specific messages
            coach_messages = [
                "I'm having trouble setting my availability for next week. The system won't let me add slots for {court}.",
                "I need to update my court access to include {court}, but I don't see an option to add it.",
                "My student {student} is having trouble booking a session with me. Can you help resolve this?",
                "I have a question about the payment distribution for my sessions. The fee calculation seems off for {court}.",
                "I've been trying to save my session logs, but they're not being saved properly.",
                "I need to cancel several upcoming sessions due to a personal issue. Is there a way to do this in bulk?",
                "I'm having trouble uploading new showcase images. The system keeps giving me an error message.",
                "Could you explain how the rating system works? I'm not sure why my average rating isn't updating.",
                "I need help configuring a new pricing plan for package deals. The discount isn't calculating correctly."
            ]
            
            # Select random subject and message
            subject_idx = random.randint(0, len(coach_subjects) - 1)
            subject = coach_subjects[subject_idx]
            
            # Generate message with placeholders filled
            message = coach_messages[subject_idx].format(
                court=random.choice([c.name for c in courts]),
                student=random.choice(students).first_name
            )
            
            # Random status with weighting (more open/in-progress than resolved)
            status_weights = [0.4, 0.4, 0.2]  # 40% open, 40% in-progress, 20% resolved
            status = random.choices(statuses, weights=status_weights, k=1)[0]
            
            # Random priority (coaches get higher priority on average)
            priority_weights = [0.2, 0.5, 0.3]  # 20% low, 50% medium, 30% high
            priority = random.choices(priorities, weights=priority_weights, k=1)[0]
            
            # Create timestamp (newer for open/in-progress, older for resolved)
            if status == "resolved":
                created_at = datetime.now() - timedelta(days=random.randint(7, 30))
                resolved_at = created_at + timedelta(days=random.randint(1, 5))
                resolved_by_id = admin.id
            else:
                created_at = datetime.now() - timedelta(days=random.randint(0, 7))
                resolved_at = None
                resolved_by_id = None
            
            # Assignment status (only for in-progress)
            assigned_to_id = admin.id if status == "in_progress" else None
            
            # Create ticket
            ticket = SupportTicket(
                user_id=coach_user.id,
                subject=subject,
                message=message,
                status=status,
                priority=priority,
                assigned_to_id=assigned_to_id,
                resolved_by_id=resolved_by_id,
                created_at=created_at,
                updated_at=created_at,
                resolved_at=resolved_at
            )
            
            db.session.add(ticket)
            support_tickets.append(ticket)
        
        db.session.commit()
        
        # Create ticket responses for in-progress and resolved tickets
        for ticket in support_tickets:
            if ticket.status in ["in_progress", "resolved"]:
                # Admin response
                admin_response = TicketResponse(
                    ticket_id=ticket.id,
                    user_id=admin.id,
                    message=random.choice([
                        f"Thank you for reaching out. I'm looking into this issue for you.",
                        f"I'm reviewing your concern and will get back to you shortly.",
                        f"I understand your issue with {ticket.subject.lower()}. Let me check what's happening.",
                        f"I've reviewed your request and I'm working on a solution.",
                        f"Thanks for your patience. I'm coordinating with our team to resolve this."
                    ]),
                    created_at=ticket.created_at + timedelta(hours=random.randint(1, 24))
                )
                db.session.add(admin_response)
                
                # If resolved, add a resolution response
                if ticket.status == "resolved":
                    resolution_response = TicketResponse(
                        ticket_id=ticket.id,
                        user_id=admin.id,
                        message=random.choice([
                            f"I've resolved the issue you reported. Please let us know if you have any further questions.",
                            f"The {ticket.subject.lower()} has been fixed. Thank you for bringing this to our attention.",
                            f"I've made the necessary adjustments to address your concern. Please check and confirm if this resolves your issue.",
                            f"This issue has been resolved. If you experience any further problems, please let us know.",
                            f"We've completed the changes you requested. Thank you for your patience."
                        ]),
                        created_at=ticket.resolved_at - timedelta(hours=random.randint(1, 5))
                    )
                    db.session.add(resolution_response)
                    
                    # 70% chance of user thanking for resolution
                    if random.random() < 0.7:
                        thank_response = TicketResponse(
                            ticket_id=ticket.id,
                            user_id=ticket.user_id,
                            message=random.choice([
                                "Thank you for resolving this so quickly!",
                                "Perfect, that fixed the issue. Thanks for your help.",
                                "Thank you for your assistance. Everything works now.",
                                "Much appreciated! Problem solved.",
                                "Thanks for the quick response and solution."
                            ]),
                            created_at=ticket.resolved_at - timedelta(minutes=random.randint(10, 50))
                        )
                        db.session.add(thank_response)
                
                # If in-progress, add a follow-up question from the user in some cases
                elif ticket.status == "in_progress" and random.random() < 0.5:
                    follow_up = TicketResponse(
                        ticket_id=ticket.id,
                        user_id=ticket.user_id,
                        message=random.choice([
                            "Do you have an update on this issue?",
                            "I'm wondering if there's any progress on resolving this?",
                            "Just checking in - any news on this matter?",
                            "Is there any additional information you need from me to resolve this?",
                            "I'd appreciate an update when you have a moment."
                        ]),
                        created_at=admin_response.created_at + timedelta(hours=random.randint(6, 48))
                    )
                    db.session.add(follow_up)
                    
                    # Admin response to follow-up
                    admin_follow_up = TicketResponse(
                        ticket_id=ticket.id,
                        user_id=admin.id,
                        message=random.choice([
                            "I'm still working on resolving this issue. Thank you for your patience.",
                            "We're making progress, but need a bit more time to fully address this.",
                            "Thanks for checking in. I'm coordinating with our technical team on a solution.",
                            "I should have a resolution for you by tomorrow. Thank you for your understanding.",
                            "We're in the final stages of resolving this issue. I'll update you once it's complete."
                        ]),
                        created_at=follow_up.created_at + timedelta(hours=random.randint(1, 24))
                    )
                    db.session.add(admin_follow_up)
        
        db.session.commit()
        
        # Note: In a real production system, you would create actual image files
        # The following code would simulate file existence by creating placeholder files
        # For development purposes, this commented code shows how you might create placeholder files:
        
        # Create directories if they don't exist
        # profile_pics_dir = os.path.join(app.static_folder, 'uploads/profile_pics')
        # showcase_dir = os.path.join(app.static_folder, 'uploads/showcase_images')
        # os.makedirs(profile_pics_dir, exist_ok=True)
        # os.makedirs(showcase_dir, exist_ok=True)
        
        # Create placeholder profile pictures
        # for user in User.query.all():
        #     if user.profile_picture:
        #         # Extract filename from path
        #         filename = user.profile_picture.split('/')[-1]
        #         filepath = os.path.join(profile_pics_dir, filename)
        #         # Create an empty file
        #         with open(filepath, 'w') as f:
        #             f.write('Placeholder for profile image')
        
        # Create placeholder showcase images
        # for image in CoachImage.query.all():
        #     if image.image_path:
        #         # Extract filename from path
        #         filename = image.image_path.split('/')[-1]
        #         filepath = os.path.join(showcase_dir, filename)
        #         # Create an empty file
        #         with open(filepath, 'w') as f:
        #             f.write('Placeholder for showcase image')
        
        print("Database seeded successfully!")

if __name__ == "__main__":
    seed_database()