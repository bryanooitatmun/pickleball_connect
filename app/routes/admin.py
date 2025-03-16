from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from sqlalchemy import func, extract, desc
from app import db
from app.models.court import Court, CoachCourt
from app.models.court_fee import CourtFee
from app.models.user import User
from app.models.coach import Coach, CoachImage
from app.models.booking import Booking, Availability
from app.models.session_log import SessionLog
from app.models.rating import CoachRating
from app.models.pricing import PricingPlan
from app.models.rating import CoachRating
from app.models.package import BookingPackage, booking_package_association
from app.models.support import SupportTicket, TicketResponse
from app.models.academy import Academy, AcademyCoach, AcademyManager
from app.models.academy_pricing import AcademyPricingPlan  # New model
from app.models.payment import PaymentProof
from app.models.notification import Notification
from app.models.tag import Tag, CoachTag
from datetime import datetime, timedelta, time
from sqlalchemy import inspect
from functools import wraps
import calendar
import json

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard home"""
    # Get basic stats for dashboard
    users_count = User.query.count()
    coaches_count = Coach.query.count()
    courts_count = Court.query.count()
    bookings_count = Booking.query.count()
    
    # Get revenue stats
    total_revenue = db.session.query(func.sum(Booking.price)).filter(Booking.status == 'completed').scalar() or 0
    
    # Get monthly revenue for current year
    current_year = datetime.utcnow().year
    monthly_revenue = {}
    
    for month in range(1, 13):
        month_revenue = db.session.query(func.sum(Booking.price)).filter(
            Booking.status == 'completed',
            extract('year', Booking.date) == current_year,
            extract('month', Booking.date) == month
        ).scalar() or 0
        
        month_name = calendar.month_name[month]
        monthly_revenue[month_name] = float(month_revenue)
    
    # Get recent bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    
    return render_template(
        'dashboard/admin/index.html', 
        users_count=users_count,
        coaches_count=coaches_count,
        courts_count=courts_count,
        bookings_count=bookings_count,
        total_revenue=total_revenue,
        monthly_revenue=monthly_revenue,
        recent_bookings=recent_bookings
    )

@bp.route('/courts/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_court():
    """Add a new court"""
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        indoor = request.form.get('indoor') == 'on'
        number_of_courts = request.form.get('number_of_courts', type=int)
        booking_link = request.form.get('booking_link')
        
        if not name:
            flash('Court name is required.', 'error')
            return redirect(url_for('admin.add_court'))
        
        court = Court(
            name=name,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            indoor=indoor,
            number_of_courts=number_of_courts,
            booking_link=booking_link
        )
        
        try:
            db.session.add(court)
            db.session.commit()
            flash('Court added successfully!', 'success')
            return redirect(url_for('admin.courts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding court: {str(e)}', 'error')
    
    return render_template('dashboard/admin/add_court.html')

@bp.route('/courts/<int:court_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_court(court_id):
    """Edit an existing court"""
    court = Court.query.get_or_404(court_id)
    
    if request.method == 'POST':
        court.name = request.form.get('name')
        court.address = request.form.get('address')
        court.city = request.form.get('city')
        court.state = request.form.get('state')
        court.zip_code = request.form.get('zip_code')
        court.indoor = request.form.get('indoor') == 'on'
        court.number_of_courts = request.form.get('number_of_courts', type=int)
        court.booking_link = request.form.get('booking_link')
        
        try:
            db.session.commit()
            flash('Court updated successfully!', 'success')
            return redirect(url_for('admin.courts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating court: {str(e)}', 'error')
    
    return render_template('dashboard/admin/edit_court.html', court=court)

@bp.route('/courts/<int:court_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_court(court_id):
    """Delete a court"""
    court = Court.query.get_or_404(court_id)
    
    try:
        db.session.delete(court)
        db.session.commit()
        flash('Court deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting court: {str(e)}', 'error')
    
    return redirect(url_for('admin.courts'))

# Court fees routes
@bp.route('/courts/<int:court_id>/fees')
@login_required
@admin_required
def court_fees(court_id):
    """Admin interface for managing court fees"""
    court = Court.query.get_or_404(court_id)
    fees = CourtFee.query.filter_by(court_id=court_id).order_by(CourtFee.start_time).all()
    return render_template('dashboard/admin/court_fees.html', court=court, fees=fees)

@bp.route('/api/courts/<int:court_id>/fees', methods=['GET'])
@login_required
@admin_required
def get_court_fees(court_id):
    """API endpoint to get court fees"""
    fees = CourtFee.query.filter_by(court_id=court_id).order_by(CourtFee.start_time).all()
    
    result = []
    for fee in fees:
        result.append({
            'id': fee.id,
            'start_time': fee.start_time.strftime('%H:%M'),
            'end_time': fee.end_time.strftime('%H:%M'),
            'fee': fee.fee
        })
    
    return jsonify(result)

@bp.route('/api/courts/<int:court_id>/fees', methods=['POST'])
@login_required
@admin_required
def add_court_fee(court_id):
    """API endpoint to add a court fee"""
    data = request.json
    
    # Validate required fields
    if not all(key in data for key in ['start_time', 'end_time', 'fee']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Parse times
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            return jsonify({'error': 'End time must be after start time'}), 400
        
        # Check for overlapping time ranges
        overlapping = CourtFee.query.filter_by(court_id=court_id).filter(
            (CourtFee.start_time <= end_time) & (CourtFee.end_time >= start_time)
        ).first()
        
        if overlapping:
            return jsonify({'error': 'The time range overlaps with an existing fee schedule'}), 400
        
        # Create new court fee
        fee = CourtFee(
            court_id=court_id,
            start_time=start_time,
            end_time=end_time,
            fee=float(data['fee'])
        )
        
        db.session.add(fee)
        db.session.commit()
        
        return jsonify({
            'id': fee.id,
            'start_time': fee.start_time.strftime('%H:%M'),
            'end_time': fee.end_time.strftime('%H:%M'),
            'fee': fee.fee
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/courts/fees/<int:fee_id>', methods=['PUT'])
@login_required
@admin_required
def update_court_fee(fee_id):
    """API endpoint to update a court fee"""
    fee = CourtFee.query.get_or_404(fee_id)
    data = request.json
    
    try:
        if 'start_time' in data:
            fee.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            
        if 'end_time' in data:
            fee.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            
        if 'fee' in data:
            fee.fee = float(data['fee'])
            
        # Validate time range
        if fee.start_time >= fee.end_time:
            return jsonify({'error': 'End time must be after start time'}), 400
            
        # Check for overlapping time ranges (excluding this fee)
        overlapping = CourtFee.query.filter_by(court_id=fee.court_id).filter(
            CourtFee.id != fee.id,
            CourtFee.start_time <= fee.end_time,
            CourtFee.end_time >= fee.start_time
        ).first()
        
        if overlapping:
            return jsonify({'error': 'The time range overlaps with an existing fee schedule'}), 400
            
        db.session.commit()
        
        return jsonify({
            'id': fee.id,
            'start_time': fee.start_time.strftime('%H:%M'),
            'end_time': fee.end_time.strftime('%H:%M'),
            'fee': fee.fee
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/courts/fees/<int:fee_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_court_fee(fee_id):
    """API endpoint to delete a court fee"""
    fee = CourtFee.query.get_or_404(fee_id)
    
    try:
        db.session.delete(fee)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# User management
@bp.route('/users')
@login_required
@admin_required
def users():
    """Admin interface for user management"""
    users = User.query.all()
    return render_template('dashboard/admin/users.html', users=users)

@bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_details(user_id):
    """View user details"""
    user = User.query.get_or_404(user_id)
    return render_template('dashboard/admin/user_details.html', user=user)

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.email = request.form.get('email')
        user.location = request.form.get('location')
        user.phone = request.form.get('phone')
        user.dupr_rating = request.form.get('dupr_rating', type=float)
        user.is_coach = request.form.get('is_coach') == 'on'
        user.is_admin = request.form.get('is_admin') == 'on'
        
        try:
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('dashboard/admin/edit_user.html', user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

# Coach management
@bp.route('/coaches')
@login_required
@admin_required
def coaches():
    """Admin interface for coach management"""
    coaches = Coach.query.join(User).all()
    return render_template('dashboard/admin/coaches.html', coaches=coaches)

@bp.route('/coaches/<int:coach_id>')
@login_required
@admin_required
def coach_details(coach_id):
    """View coach details"""
    coach = Coach.query.get_or_404(coach_id)
    return render_template('dashboard/admin/coach_details.html', coach=coach)

# Earnings analytics
@bp.route('/earnings')
@login_required
@admin_required
def earnings():
    """View earnings analytics"""
    # Get overall earnings
    total_earnings = db.session.query(func.sum(Booking.price)).filter(Booking.status == 'completed').scalar() or 0
    
    # Get earnings by month for the current year
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month
    monthly_earnings = []
    
    for month in range(1, 13):
        month_earnings = db.session.query(func.sum(Booking.price)).filter(
            Booking.status == 'completed',
            extract('year', Booking.date) == current_year,
            extract('month', Booking.date) == month
        ).scalar() or 0
        
        month_name = calendar.month_name[month]
        monthly_earnings.append({
            'month': month_name,
            'earnings': float(month_earnings)
        })
    
    # Calculate this month and last month earnings
    this_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.status == 'completed',
        extract('year', Booking.date) == current_year,
        extract('month', Booking.date) == current_month
    ).scalar() or 0
    
    # Calculate last month earnings
    last_month = current_month - 1 if current_month > 1 else 12
    last_month_year = current_year if current_month > 1 else current_year - 1
    
    last_month_earnings = db.session.query(func.sum(Booking.price)).filter(
        Booking.status == 'completed',
        extract('year', Booking.date) == last_month_year,
        extract('month', Booking.date) == last_month
    ).scalar() or 0
    
    # Get earnings by court
    court_earnings = db.session.query(
        Court.name,
        func.sum(Booking.price).label('earnings')
    ).join(Booking, Booking.court_id == Court.id).filter(
        Booking.status == 'completed'
    ).group_by(Court.name).all()
    
    # Get earnings by coach
    coach_earnings = db.session.query(
        User.first_name,
        User.last_name,
        func.sum(Booking.price).label('earnings')
    ).join(Coach, Coach.id == Booking.coach_id).join(
        User, User.id == Coach.user_id
    ).filter(
        Booking.status == 'completed'
    ).group_by(User.first_name, User.last_name).all()
    
    return render_template(
        'dashboard/admin/earnings.html',
        total_earnings=total_earnings,
        monthly_earnings=monthly_earnings,
        this_month_earnings=this_month_earnings,
        last_month_earnings=last_month_earnings,
        court_earnings=court_earnings,
        coach_earnings=coach_earnings
    )

# Support ticket system (assuming you'll implement a basic support ticket model)
@bp.route('/support')
@login_required
@admin_required
def support_tickets():
    """View and manage support tickets"""
    # This assumes you have a SupportTicket model
    # If not, you'll need to create one
    try:
        # Attempt to import the model and query tickets
        from app.models.support import SupportTicket
        tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    except ImportError:
        # If the model doesn't exist, show a message
        tickets = []
        flash('Support Ticket model is not implemented yet.', 'info')
    
    return render_template('dashboard/admin/support_tickets.html', tickets=tickets)

# Database management interface
@bp.route('/database')
@login_required
@admin_required
def database():
    """General database management interface"""
    # Get all table names in the database using SQLAlchemy's inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    return render_template('dashboard/admin/database.html', tables=tables)

@bp.route('/database/<table>')
@login_required
@admin_required
def table_view(table):
    """View records from a specific table with pagination"""
    # Make sure the table exists
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        flash(f'Table {table} does not exist', 'error')
        return redirect(url_for('admin.database'))
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # Default 20 records per page
    
    # Get search parameter
    search = request.args.get('search', '')
    
    # Dynamically get the model class for the table
    model_map = {
        'user': User,
        'coach': Coach,
        'court': Court,
        'court_fee': CourtFee,
        'booking': Booking,
        'availability': Availability,
        'session_log': SessionLog,
        'pricing_plan': PricingPlan,
        'coach_rating': CoachRating,
        'coach_image': CoachImage,
        'coach_court': CoachCourt,
        'booking_package': BookingPackage,
        'support_ticket': SupportTicket,
        'ticket_response': TicketResponse,
        'academy': Academy,
        'academy_coach': AcademyCoach,
        'academy_manager': AcademyManager,
        'coach_tag': CoachTag,
        'payment_proof': PaymentProof,
        'notification': Notification,
        'academy_pricing_plan': AcademyPricingPlan,
        'tag': Tag
    }
    
    if table.lower() not in model_map:
        flash(f'No model mapping available for table {table}', 'error')
        return redirect(url_for('admin.database'))
    
    model = model_map[table.lower()]
    
    # Build query
    query = model.query
    
    # Apply search if provided
    if search:
        # Try to find searchable columns (string-based columns)
        searchable_columns = []
        for column in model.__table__.columns:
            if isinstance(column.type, db.String) or isinstance(column.type, db.Text):
                searchable_columns.append(column)
        
        # Build search filter
        if searchable_columns:
            search_filter = []
            for column in searchable_columns:
                search_filter.append(column.ilike(f'%{search}%'))
            
            if search_filter:
                query = query.filter(db.or_(*search_filter))
    
    # Get total count for pagination
    total_count = query.count()
    
    # Paginate the results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    records = pagination.items
    
    # Get column names
    columns = [column.name for column in model.__table__.columns]
    
    return render_template(
        'dashboard/admin/table_view.html', 
        table=table, 
        records=records, 
        columns=columns,
        pagination=pagination,
        search=search,
        per_page=per_page,
        total_count=total_count
    )

@bp.route('/database/<table>/<int:record_id>')
@login_required
@admin_required
def record_view(table, record_id):
    """View a specific record"""
    # Make sure the table exists
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        flash(f'Table {table} does not exist', 'error')
        return redirect(url_for('admin.database'))
    
    # Dynamically get the model class for the table
    model_map = {
        'user': User,
        'coach': Coach,
        'court': Court,
        'court_fee': CourtFee,
        'booking': Booking,
        'availability': Availability,
        'session_log': SessionLog,
        'pricing_plan': PricingPlan,
        'coach_rating': CoachRating,
        'coach_image': CoachImage,
        'coach_court': CoachCourt,
        'booking_package': BookingPackage,
        'support_ticket': SupportTicket,
        'ticket_response': TicketResponse
    }
    
    
    if table.lower() not in model_map:
        flash(f'No model mapping available for table {table}', 'error')
        return redirect(url_for('admin.database'))
    
    model = model_map[table.lower()]
    record = model.query.get_or_404(record_id)
    
    # Get column names and values
    columns = []
    for column in model.__table__.columns:
        value = getattr(record, column.name)
        columns.append({
            'name': column.name,
            'value': value,
            'type': str(column.type)
        })
    
    return render_template('dashboard/admin/record_view.html', table=table, record=record, columns=columns)

@bp.route('/database/<table>/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def record_edit(table, record_id):
    """Edit a specific record"""
    # This is a simplified implementation and might not handle all field types correctly
    # A production version would need more robust handling
    
    # Make sure the table exists
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        flash(f'Table {table} does not exist', 'error')
        return redirect(url_for('admin.database'))
    
    # Dynamically get the model class for the table
    model_map = {
        'user': User,
        'coach': Coach,
        'court': Court,
        'court_fee': CourtFee,
        'booking': Booking,
        'availability': Availability,
        'session_log': SessionLog,
        'pricing_plan': PricingPlan,
        'coach_rating': CoachRating,
        'coach_image': CoachImage,
        'coach_court': CoachCourt,
        'booking_package': BookingPackage,
        'support_ticket': SupportTicket,
        'ticket_response': TicketResponse
    }
    
    
    if table.lower() not in model_map:
        flash(f'No model mapping available for table {table}', 'error')
        return redirect(url_for('admin.database'))
    
    model = model_map[table.lower()]
    record = model.query.get_or_404(record_id)
    
    # For POST requests, update the record
    if request.method == 'POST':
        try:
            # Update each field
            for column in model.__table__.columns:
                # Skip the primary key
                if column.primary_key:
                    continue
                
                # Get the field from the form
                field_name = column.name
                field_value = request.form.get(field_name)
                
                # Convert the value to the appropriate type
                if field_value is not None:
                    if isinstance(column.type, db.Boolean):
                        field_value = field_value == 'on'
                    elif isinstance(column.type, db.Integer):
                        field_value = int(field_value) if field_value else None
                    elif isinstance(column.type, db.Float):
                        field_value = float(field_value) if field_value else None
                    elif isinstance(column.type, db.Date):
                        field_value = datetime.strptime(field_value, '%Y-%m-%d').date() if field_value else None
                    elif isinstance(column.type, db.Time):
                        field_value = datetime.strptime(field_value, '%H:%M').time() if field_value else None
                    elif isinstance(column.type, db.DateTime):
                        field_value = datetime.strptime(field_value, '%Y-%m-%d %H:%M:%S') if field_value else None
                
                # Set the attribute
                setattr(record, field_name, field_value)
            
            # Save the changes
            db.session.commit()
            flash('Record updated successfully!', 'success')
            return redirect(url_for('admin.table_view', table=table))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating record: {str(e)}', 'error')
    
    # Get column names and values
    columns = []
    for column in model.__table__.columns:
        value = getattr(record, column.name)
        columns.append({
            'name': column.name,
            'value': value,
            'type': str(column.type),
            'primary_key': column.primary_key
        })
    
    return render_template('dashboard/admin/record_edit.html', table=table, record=record, columns=columns)

@bp.route('/database/<table>/<int:record_id>/delete', methods=['POST'])
@login_required
@admin_required
def record_delete(table, record_id):
    """Delete a specific record"""
    # Make sure the table exists
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        flash(f'Table {table} does not exist', 'error')
        return redirect(url_for('admin.database'))
    
    # Dynamically get the model class for the table
    model_map = {
        'user': User,
        'coach': Coach,
        'court': Court,
        'court_fee': CourtFee,
        'booking': Booking,
        'availability': Availability,
        'session_log': SessionLog,
        'pricing_plan': PricingPlan,
        'coach_rating': CoachRating,
        'coach_image': CoachImage,
        'coach_court': CoachCourt,
        'booking_package': BookingPackage,
        'support_ticket': SupportTicket,
        'ticket_response': TicketResponse
    }
    
    
    if table.lower() not in model_map:
        flash(f'No model mapping available for table {table}', 'error')
        return redirect(url_for('admin.database'))
    
    model = model_map[table.lower()]
    record = model.query.get_or_404(record_id)
    
    try:
        db.session.delete(record)
        db.session.commit()
        flash('Record deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting record: {str(e)}', 'error')
    
    return redirect(url_for('admin.table_view', table=table))

# Bookings management
@bp.route('/bookings')
@login_required
@admin_required
def bookings():
    """Admin interface for bookings management"""
    bookings = Booking.query.order_by(Booking.date.desc(), Booking.start_time).all()
    return render_template('dashboard/admin/bookings.html', bookings=bookings)

@bp.route('/bookings/<int:booking_id>')
@login_required
@admin_required
def booking_details(booking_id):
    """View booking details"""
    booking = Booking.query.get_or_404(booking_id)
    return render_template('dashboard/admin/booking_details.html', booking=booking)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/courts')
@login_required
@admin_required
def courts():
    """Admin interface for courts management"""
    courts = Court.query.all()
    return render_template('dashboard/admin/courts.html', courts=courts)

