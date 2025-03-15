from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.models.connect_points import ConnectPoints, ConnectPointsConfig, ConnectVoucher
from app.models.user import User
from functools import wraps
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import uuid

bp = Blueprint('admin_connect_points', __name__, url_prefix='/admin/connect-points')

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard for Connect Points system"""
    # Get config
    config = ConnectPointsConfig.get_active_config()
    
    # Get points statistics
    total_points_awarded = db.session.query(func.sum(ConnectPoints.points)).filter(
        ConnectPoints.points > 0
    ).scalar() or 0
    
    total_points_redeemed = db.session.query(func.sum(ConnectPoints.points)).filter(
        ConnectPoints.points < 0
    ).scalar() or 0
    
    points_in_circulation = total_points_awarded + total_points_redeemed
    
    # Number of vouchers redeemed
    vouchers_redeemed = ConnectPoints.query.filter_by(
        transaction_type='voucher_redemption'
    ).count()
    
    # Recent transactions
    recent_transactions = ConnectPoints.query.order_by(ConnectPoints.created_at.desc()).limit(10).all()
    
    # Active vouchers count
    active_vouchers_count = ConnectVoucher.query.filter_by(is_active=True).count()
    
    return render_template(
        'admin/connect_points/index.html',
        config=config,
        total_points_awarded=total_points_awarded,
        total_points_redeemed=abs(total_points_redeemed),
        points_in_circulation=points_in_circulation,
        vouchers_redeemed=vouchers_redeemed,
        recent_transactions=recent_transactions,
        active_vouchers_count=active_vouchers_count
    )

@bp.route('/config', methods=['GET', 'POST'])
@login_required
@admin_required
def config():
    """Manage Connect Points configuration"""
    config = ConnectPointsConfig.get_active_config()
    
    if request.method == 'POST':
        try:
            # Update configuration
            config.base_multiplier = float(request.form.get('base_multiplier', 1.0))
            config.min_points_factor = float(request.form.get('min_points_factor', 0.8))
            config.max_points_factor = float(request.form.get('max_points_factor', 1.2))
            config.enabled = request.form.get('enabled') == 'on'
            
            # Validate values
            if config.min_points_factor > config.max_points_factor:
                flash('Minimum randomization factor must be less than maximum factor.', 'error')
                return redirect(url_for('admin_connect_points.config'))
            
            if config.base_multiplier < 0:
                flash('Base multiplier must be a positive number.', 'error')
                return redirect(url_for('admin_connect_points.config'))
            
            # Save changes
            config.updated_at = datetime.now()
            db.session.commit()
            
            flash('Connect Points configuration updated successfully!', 'success')
            return redirect(url_for('admin_connect_points.config'))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('admin_connect_points.config'))
    
    # Sample calculations for the current settings
    sample_prices = [50.00, 75.00, 100.00, 150.00]
    sample_calculations = []
    
    for price in sample_prices:
        base_points = int(price * config.base_multiplier)
        min_points = int(base_points * config.min_points_factor)
        max_points = int(base_points * config.max_points_factor)
        
        sample_calculations.append({
            'price': price,
            'base_points': base_points,
            'min_points': min_points,
            'max_points': max_points
        })
    
    return render_template(
        'admin/connect_points/config.html',
        config=config,
        sample_calculations=sample_calculations
    )

@bp.route('/vouchers')
@login_required
@admin_required
def vouchers():
    """Manage Connect Points vouchers"""
    vouchers = ConnectVoucher.query.all()
    
    # Get redemption counts for each voucher
    redemption_counts = {}
    for voucher in vouchers:
        count = ConnectPoints.query.filter_by(
            voucher_id=voucher.id,
            transaction_type='voucher_redemption'
        ).count()
        redemption_counts[voucher.id] = count
    
    return render_template(
        'admin/connect_points/vouchers.html',
        vouchers=vouchers,
        redemption_counts=redemption_counts
    )

@bp.route('/vouchers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_voucher():
    """Add a new Connect Points voucher"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description', '')
            points_cost = int(request.form.get('points_cost', 0))
            discount_type = request.form.get('discount_type')
            discount_value = float(request.form.get('discount_value', 0))
            code = request.form.get('code', '').strip().upper()
            is_active = request.form.get('is_active') == 'on'
            
            # Validate required fields
            if not name or points_cost <= 0:
                flash('Voucher name and a positive points cost are required.', 'error')
                return redirect(url_for('admin_connect_points.add_voucher'))
            
            if not discount_type or discount_value <= 0:
                flash('Please specify a valid discount type and value.', 'error')
                return redirect(url_for('admin_connect_points.add_voucher'))
            
            # Generate code if not provided
            if not code:
                code = f"PBC-{uuid.uuid4().hex[:6].upper()}"
            
            # Check if code already exists
            existing_code = ConnectVoucher.query.filter_by(code=code).first()
            if existing_code:
                flash(f'Voucher code {code} already exists. Please choose a different code.', 'error')
                return redirect(url_for('admin_connect_points.add_voucher'))
            
            # Create voucher
            voucher = ConnectVoucher(
                name=name,
                description=description,
                points_cost=points_cost,
                code=code,
                is_active=is_active
            )
            
            # Set discount based on type
            if discount_type == 'amount':
                voucher.discount_amount = discount_value
                voucher.discount_percentage = None
            else:  # percentage
                voucher.discount_percentage = discount_value
                voucher.discount_amount = None
            
            db.session.add(voucher)
            db.session.commit()
            
            flash(f'Voucher "{name}" created successfully!', 'success')
            return redirect(url_for('admin_connect_points.vouchers'))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('admin_connect_points.add_voucher'))
    
    return render_template('admin/connect_points/add_voucher.html')

@bp.route('/vouchers/<int:voucher_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_voucher(voucher_id):
    """Edit an existing Connect Points voucher"""
    voucher = ConnectVoucher.query.get_or_404(voucher_id)
    
    # Get redemption count for this voucher
    redemption_count = ConnectPoints.query.filter_by(
        voucher_id=voucher.id,
        transaction_type='voucher_redemption'
    ).count()
    
    if request.method == 'POST':
        try:
            # Get form data
            voucher.name = request.form.get('name')
            voucher.description = request.form.get('description', '')
            voucher.points_cost = int(request.form.get('points_cost', 0))
            discount_type = request.form.get('discount_type')
            discount_value = float(request.form.get('discount_value', 0))
            new_code = request.form.get('code', '').strip().upper()
            voucher.is_active = request.form.get('is_active') == 'on'
            
            # Validate required fields
            if not voucher.name or voucher.points_cost <= 0:
                flash('Voucher name and a positive points cost are required.', 'error')
                return redirect(url_for('admin_connect_points.edit_voucher', voucher_id=voucher_id))
            
            if not discount_type or discount_value <= 0:
                flash('Please specify a valid discount type and value.', 'error')
                return redirect(url_for('admin_connect_points.edit_voucher', voucher_id=voucher_id))
            
            # Check if code is being changed and if it already exists
            if new_code and new_code != voucher.code:
                existing_code = ConnectVoucher.query.filter(
                    ConnectVoucher.code == new_code,
                    ConnectVoucher.id != voucher_id
                ).first()
                
                if existing_code:
                    flash(f'Voucher code {new_code} already exists. Please choose a different code.', 'error')
                    return redirect(url_for('admin_connect_points.edit_voucher', voucher_id=voucher_id))
                
                voucher.code = new_code
            
            # Set discount based on type
            if discount_type == 'amount':
                voucher.discount_amount = discount_value
                voucher.discount_percentage = None
            else:  # percentage
                voucher.discount_percentage = discount_value
                voucher.discount_amount = None
            
            voucher.updated_at = datetime.now()
            db.session.commit()
            
            flash(f'Voucher "{voucher.name}" updated successfully!', 'success')
            return redirect(url_for('admin_connect_points.vouchers'))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('admin_connect_points.edit_voucher', voucher_id=voucher_id))
    
    # Determine discount type and value for display
    discount_type = 'amount' if voucher.discount_amount is not None else 'percentage'
    discount_value = voucher.discount_amount if discount_type == 'amount' else voucher.discount_percentage
    
    return render_template(
        'admin/connect_points/edit_voucher.html',
        voucher=voucher,
        discount_type=discount_type,
        discount_value=discount_value,
        redemption_count=redemption_count
    )

@bp.route('/vouchers/<int:voucher_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_voucher(voucher_id):
    """Delete a Connect Points voucher"""
    voucher = ConnectVoucher.query.get_or_404(voucher_id)
    
    # Check if voucher has been redeemed
    redemption_count = ConnectPoints.query.filter_by(
        voucher_id=voucher_id,
        transaction_type='voucher_redemption'
    ).count()
    
    if redemption_count > 0:
        flash(f'Cannot delete voucher "{voucher.name}" because it has been redeemed {redemption_count} times. You can deactivate it instead.', 'error')
        return redirect(url_for('admin_connect_points.vouchers'))
    
    voucher_name = voucher.name
    db.session.delete(voucher)
    db.session.commit()
    
    flash(f'Voucher "{voucher_name}" deleted successfully!', 'success')
    return redirect(url_for('admin_connect_points.vouchers'))

@bp.route('/transactions')
@login_required
@admin_required
def transactions():
    """View Connect Points transactions"""
    # Get filter parameters
    user_id = request.args.get('user_id', type=int)
    transaction_type = request.args.get('transaction_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = ConnectPoints.query
    
    if user_id:
        query = query.filter(ConnectPoints.user_id == user_id)
    
    if transaction_type:
        query = query.filter(ConnectPoints.transaction_type == transaction_type)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ConnectPoints.created_at >= date_from)
        except ValueError:
            flash('Invalid "From" date format.', 'error')
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            # Include the full day by setting to the end of the day
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query = query.filter(ConnectPoints.created_at <= date_to)
        except ValueError:
            flash('Invalid "To" date format.', 'error')
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(ConnectPoints.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    transactions = pagination.items
    
    # Get list of users for filter dropdown
    users_with_transactions = db.session.query(
        User.id, User.first_name, User.last_name
    ).join(ConnectPoints, User.id == ConnectPoints.user_id).distinct().all()
    
    return render_template(
        'admin/connect_points/transactions.html',
        transactions=transactions,
        pagination=pagination,
        users=users_with_transactions,
        filters={
            'user_id': user_id,
            'transaction_type': transaction_type,
            'date_from': date_from,
            'date_to': date_to
        }
    )

@bp.route('/users')
@login_required
@admin_required
def users():
    """View user points balances"""
    # Get search parameter
    search = request.args.get('search', '')
    
    # Build query for users with points
    query = db.session.query(
        User,
        func.sum(ConnectPoints.points).label('points_balance')
    ).outerjoin(
        ConnectPoints,
        User.id == ConnectPoints.user_id
    ).group_by(User.id)
    
    # Apply search if provided
    if search:
        query = query.filter(db.or_(
            User.first_name.ilike(f'%{search}%'),
            User.last_name.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%')
        ))
    
    # Order by points balance (highest first)
    query = query.order_by(desc('points_balance'))
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    user_points = pagination.items
    
    return render_template(
        'admin/connect_points/users.html',
        user_points=user_points,
        pagination=pagination,
        search=search
    )

@bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_points(user_id):
    """View points history for a specific user"""
    user = User.query.get_or_404(user_id)
    
    # Get user's point transactions
    transactions = ConnectPoints.query.filter_by(user_id=user_id).order_by(ConnectPoints.created_at.desc()).all()
    
    # Calculate total balance
    balance = ConnectPoints.get_user_balance(user_id)
    
    # Calculate statistics
    total_earned = db.session.query(func.sum(ConnectPoints.points)).filter(
        ConnectPoints.user_id == user_id,
        ConnectPoints.points > 0
    ).scalar() or 0
    
    total_spent = db.session.query(func.sum(ConnectPoints.points)).filter(
        ConnectPoints.user_id == user_id,
        ConnectPoints.points < 0
    ).scalar() or 0
    
    # Get vouchers redeemed
    vouchers_redeemed = ConnectPoints.query.filter_by(
        user_id=user_id,
        transaction_type='voucher_redemption'
    ).all()
    
    return render_template(
        'admin/connect_points/user_points.html',
        user=user,
        transactions=transactions,
        balance=balance,
        total_earned=total_earned,
        total_spent=abs(total_spent),
        vouchers_redeemed=vouchers_redeemed
    )

@bp.route('/users/<int:user_id>/adjust', methods=['GET', 'POST'])
@login_required
@admin_required
def adjust_user_points(user_id):
    """Manually adjust points for a user"""
    user = User.query.get_or_404(user_id)
    current_balance = ConnectPoints.get_user_balance(user_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            points = int(request.form.get('points', 0))
            reason = request.form.get('reason', '').strip()
            
            # Validate input
            if points == 0:
                flash('Points adjustment cannot be zero.', 'error')
                return redirect(url_for('admin_connect_points.adjust_user_points', user_id=user_id))
            
            if not reason:
                flash('Please provide a reason for the points adjustment.', 'error')
                return redirect(url_for('admin_connect_points.adjust_user_points', user_id=user_id))
            
            # Create points adjustment
            adjustment = ConnectPoints(
                user_id=user_id,
                points=points,
                transaction_type='admin_adjustment',
                description=f"Admin adjustment: {reason}"
            )
            
            db.session.add(adjustment)
            db.session.commit()
            
            # Get updated balance
            new_balance = ConnectPoints.get_user_balance(user_id)
            
            flash(f'Successfully adjusted points for {user.first_name} {user.last_name}. New balance: {new_balance} points.', 'success')
            return redirect(url_for('admin_connect_points.user_points', user_id=user_id))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('admin_connect_points.adjust_user_points', user_id=user_id))
    
    return render_template(
        'admin/connect_points/adjust_points.html',
        user=user,
        current_balance=current_balance
    )

@bp.route('/reports')
@login_required
@admin_required
def reports():
    """Connect Points reports and analytics"""
    # Time period for report
    period = request.args.get('period', 'all_time')
    
    # Define time ranges
    now = datetime.now()
    
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'this_week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'last_30_days':
        start_date = now - timedelta(days=30)
    elif period == 'last_90_days':
        start_date = now - timedelta(days=90)
    else:  # all_time
        start_date = None
    
    # Basic statistics
    query = db.session.query(
        func.sum(ConnectPoints.points).filter(ConnectPoints.points > 0).label('total_awarded'),
        func.sum(ConnectPoints.points).filter(ConnectPoints.points < 0).label('total_redeemed'),
        func.count().filter(ConnectPoints.transaction_type == 'booking_reward').label('booking_rewards'),
        func.count().filter(ConnectPoints.transaction_type == 'voucher_redemption').label('voucher_redemptions'),
        func.count().filter(ConnectPoints.transaction_type == 'admin_adjustment').label('admin_adjustments')
    )
    
    if start_date:
        query = query.filter(ConnectPoints.created_at >= start_date)
    
    stats = query.one()
    
    # Monthly points awarded (for chart)
    monthly_data = []
    
    # Get data for the last 6 months
    for i in range(5, -1, -1):
        month_start = now.replace(day=1) - timedelta(days=i*30)
        month_name = month_start.strftime('%B %Y')
        
        # Points awarded that month
        month_awarded = db.session.query(func.sum(ConnectPoints.points)).filter(
            ConnectPoints.points > 0,
            extract('year', ConnectPoints.created_at) == month_start.year,
            extract('month', ConnectPoints.created_at) == month_start.month
        ).scalar() or 0
        
        # Points redeemed that month
        month_redeemed = db.session.query(func.sum(ConnectPoints.points)).filter(
            ConnectPoints.points < 0,
            extract('year', ConnectPoints.created_at) == month_start.year,
            extract('month', ConnectPoints.created_at) == month_start.month
        ).scalar() or 0
        
        monthly_data.append({
            'month': month_name,
            'awarded': float(month_awarded),
            'redeemed': abs(float(month_redeemed))
        })
    
    # Top vouchers redeemed
    top_vouchers = db.session.query(
        ConnectVoucher.id,
        ConnectVoucher.name,
        func.count().label('redemption_count')
    ).join(
        ConnectPoints,
        ConnectPoints.voucher_id == ConnectVoucher.id
    ).filter(
        ConnectPoints.transaction_type == 'voucher_redemption'
    )
    
    if start_date:
        top_vouchers = top_vouchers.filter(ConnectPoints.created_at >= start_date)
    
    top_vouchers = top_vouchers.group_by(
        ConnectVoucher.id,
        ConnectVoucher.name
    ).order_by(desc('redemption_count')).limit(5).all()
    
    return render_template(
        'admin/connect_points/reports.html',
        stats=stats,
        monthly_data=monthly_data,
        top_vouchers=top_vouchers,
        period=period
    )