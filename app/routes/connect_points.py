from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.connect_points import ConnectPoints, ConnectPointsConfig, ConnectVoucher
from datetime import datetime
from functools import wraps

bp = Blueprint('connect_points', __name__, url_prefix='/api/connect-points')

# Helper decorator to check if user is admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/balance')
@login_required
def get_balance():
    """Get the current user's point balance and recent transactions"""
    # Get user balance
    balance = ConnectPoints.get_user_balance(current_user.id)
    
    # Get recent transactions (last 10)
    transactions = ConnectPoints.query.filter_by(user_id=current_user.id) \
        .order_by(ConnectPoints.created_at.desc()).limit(10).all()
    
    # Format transactions for response
    transaction_data = []
    for t in transactions:
        transaction_info = {
            'id': t.id,
            'points': t.points,
            'transaction_type': t.transaction_type,
            'description': t.description,
            'created_at': t.created_at.isoformat()
        }
        
        # Add booking info if available
        if t.booking_id:
            if t.booking:
                transaction_info['booking'] = {
                    'id': t.booking.id,
                    'date': t.booking.date.isoformat() if t.booking.date else None,
                    'coach_name': f"{t.booking.coach.user.first_name} {t.booking.coach.user.last_name}" if t.booking.coach else "Unknown"
                }
        
        # Add voucher info if available
        if t.voucher_id:
            if t.voucher:
                transaction_info['voucher'] = {
                    'id': t.voucher.id,
                    'name': t.voucher.name
                }
        
        transaction_data.append(transaction_info)
    
    return jsonify({
        'balance': balance,
        'transactions': transaction_data
    })

@bp.route('/transactions')
@login_required
def get_transactions():
    """Get all point transactions for the current user"""
    # Get page and per_page parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get transactions with pagination
    pagination = ConnectPoints.query.filter_by(user_id=current_user.id) \
        .order_by(ConnectPoints.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
    
    # Format transactions for response
    transaction_data = []
    for t in pagination.items:
        transaction_info = {
            'id': t.id,
            'points': t.points,
            'transaction_type': t.transaction_type,
            'description': t.description,
            'created_at': t.created_at.isoformat()
        }
        
        # Add booking info if available
        if t.booking_id and t.booking:
            transaction_info['booking'] = {
                'id': t.booking.id,
                'date': t.booking.date.isoformat() if t.booking.date else None,
                'coach_name': f"{t.booking.coach.user.first_name} {t.booking.coach.user.last_name}" if t.booking.coach else "Unknown"
            }
        
        # Add voucher info if available
        if t.voucher_id and t.voucher:
            transaction_info['voucher'] = {
                'id': t.voucher.id,
                'name': t.voucher.name
            }
        
        transaction_data.append(transaction_info)
    
    return jsonify({
        'transactions': transaction_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page
    })

@bp.route('/vouchers')
@login_required
def get_vouchers():
    """Get all available vouchers for redemption"""
    # Get active vouchers
    vouchers = ConnectVoucher.get_active_vouchers()
    
    # Get user balance
    balance = ConnectPoints.get_user_balance(current_user.id)
    
    # Format vouchers for response
    voucher_data = []
    for v in vouchers:
        voucher_info = {
            'id': v.id,
            'name': v.name,
            'description': v.description,
            'points_cost': v.points_cost,
            'can_redeem': balance >= v.points_cost
        }
        
        # Add discount info
        if v.discount_amount:
            voucher_info['discount_type'] = 'amount'
            voucher_info['discount_value'] = v.discount_amount
        elif v.discount_percentage:
            voucher_info['discount_type'] = 'percentage'
            voucher_info['discount_value'] = v.discount_percentage
        
        voucher_data.append(voucher_info)
    
    return jsonify({
        'vouchers': voucher_data,
        'user_balance': balance
    })

@bp.route('/vouchers/redeem', methods=['POST'])
@login_required
def redeem_voucher():
    """Redeem a voucher with connect points"""
    # Get voucher ID from request
    data = request.get_json()
    voucher_id = data.get('voucher_id')
    
    if not voucher_id:
        return jsonify({'error': 'Voucher ID is required'}), 400
    
    # Attempt redemption
    redemption, message = ConnectVoucher.redeem_voucher(voucher_id, current_user.id)
    
    if not redemption:
        return jsonify({'error': message}), 400
    
    # Return success response with voucher code
    return jsonify({
        'success': True,
        'voucher_code': message,
        'new_balance': ConnectPoints.get_user_balance(current_user.id)
    })

# Admin routes for managing the points system

@bp.route('/admin/config', methods=['GET'])
@login_required
@admin_required
def get_config():
    """Get current connect points configuration"""
    config = ConnectPointsConfig.get_active_config()
    
    return jsonify({
        'id': config.id,
        'base_multiplier': config.base_multiplier,
        'min_points_factor': config.min_points_factor,
        'max_points_factor': config.max_points_factor,
        'enabled': config.enabled,
        'created_at': config.created_at.isoformat(),
        'updated_at': config.updated_at.isoformat()
    })

@bp.route('/admin/config', methods=['PUT'])
@login_required
@admin_required
def update_config():
    """Update connect points configuration"""
    data = request.get_json()
    config = ConnectPointsConfig.get_active_config()
    
    # Update configuration fields
    if 'base_multiplier' in data:
        config.base_multiplier = float(data['base_multiplier'])
    if 'min_points_factor' in data:
        config.min_points_factor = float(data['min_points_factor'])
    if 'max_points_factor' in data:
        config.max_points_factor = float(data['max_points_factor'])
    if 'enabled' in data:
        config.enabled = bool(data['enabled'])
    
    # Ensure min factor is less than max factor
    if config.min_points_factor > config.max_points_factor:
        return jsonify({'error': 'Minimum factor must be less than maximum factor'}), 400
    
    # Save changes
    config.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': config.id,
        'base_multiplier': config.base_multiplier,
        'min_points_factor': config.min_points_factor,
        'max_points_factor': config.max_points_factor,
        'enabled': config.enabled,
        'updated_at': config.updated_at.isoformat()
    })

@bp.route('/admin/vouchers', methods=['GET'])
@login_required
@admin_required
def admin_get_vouchers():
    """Get all vouchers for admin management"""
    vouchers = ConnectVoucher.query.all()
    
    voucher_data = []
    for v in vouchers:
        voucher_info = {
            'id': v.id,
            'name': v.name,
            'description': v.description,
            'points_cost': v.points_cost,
            'code': v.code,
            'is_active': v.is_active,
            'created_at': v.created_at.isoformat(),
            'updated_at': v.updated_at.isoformat()
        }
        
        # Add discount info
        if v.discount_amount:
            voucher_info['discount_type'] = 'amount'
            voucher_info['discount_value'] = v.discount_amount
        elif v.discount_percentage:
            voucher_info['discount_type'] = 'percentage'
            voucher_info['discount_value'] = v.discount_percentage
        
        # Get redemption count
        redemption_count = ConnectPoints.query.filter_by(
            voucher_id=v.id, 
            transaction_type='voucher_redemption'
        ).count()
        
        voucher_info['redemption_count'] = redemption_count
        
        voucher_data.append(voucher_info)
    
    return jsonify({
        'vouchers': voucher_data
    })

@bp.route('/admin/vouchers', methods=['POST'])
@login_required
@admin_required
def create_voucher():
    """Create a new voucher"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'points_cost']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Field {field} is required'}), 400
    
    # Validate discount information
    discount_amount = data.get('discount_amount')
    discount_percentage = data.get('discount_percentage')
    
    if discount_amount is None and discount_percentage is None:
        return jsonify({'error': 'Either discount_amount or discount_percentage must be provided'}), 400
    
    if discount_amount is not None and discount_percentage is not None:
        return jsonify({'error': 'Cannot provide both discount_amount and discount_percentage'}), 400
    
    # Generate unique voucher code if not provided
    code = data.get('code')
    if not code:
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Check if code already exists
        while ConnectVoucher.query.filter_by(code=code).first():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # Create voucher
    voucher = ConnectVoucher(
        name=data['name'],
        description=data.get('description', ''),
        points_cost=int(data['points_cost']),
        discount_amount=float(discount_amount) if discount_amount is not None else None,
        discount_percentage=float(discount_percentage) if discount_percentage is not None else None,
        code=code,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(voucher)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': voucher.id,
        'name': voucher.name,
        'code': voucher.code
    })

@bp.route('/admin/vouchers/<int:voucher_id>', methods=['PUT'])
@login_required
@admin_required
def update_voucher(voucher_id):
    """Update an existing voucher"""
    data = request.get_json()
    voucher = ConnectVoucher.query.get_or_404(voucher_id)
    
    # Update voucher fields
    if 'name' in data:
        voucher.name = data['name']
    if 'description' in data:
        voucher.description = data['description']
    if 'points_cost' in data:
        voucher.points_cost = int(data['points_cost'])
    if 'is_active' in data:
        voucher.is_active = bool(data['is_active'])
    
    # Handle discount updates
    if 'discount_amount' in data and data['discount_amount'] is not None:
        voucher.discount_amount = float(data['discount_amount'])
        voucher.discount_percentage = None
    elif 'discount_percentage' in data and data['discount_percentage'] is not None:
        voucher.discount_percentage = float(data['discount_percentage'])
        voucher.discount_amount = None
    
    # Update code if provided
    if 'code' in data and data['code']:
        # Check if code already exists (except for this voucher)
        existing = ConnectVoucher.query.filter(
            ConnectVoucher.code == data['code'],
            ConnectVoucher.id != voucher_id
        ).first()
        
        if existing:
            return jsonify({'error': 'Voucher code already exists'}), 400
        
        voucher.code = data['code']
    
    voucher.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': voucher.id,
        'name': voucher.name,
        'updated_at': voucher.updated_at.isoformat()
    })

@bp.route('/admin/vouchers/<int:voucher_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_voucher(voucher_id):
    """Delete a voucher"""
    voucher = ConnectVoucher.query.get_or_404(voucher_id)
    
    # Check if voucher has been redeemed
    redemption_count = ConnectPoints.query.filter_by(
        voucher_id=voucher_id, 
        transaction_type='voucher_redemption'
    ).count()
    
    if redemption_count > 0:
        # Instead of deleting, just deactivate
        voucher.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Voucher has been deactivated instead of deleted because it has already been redeemed'
        })
    
    db.session.delete(voucher)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Voucher deleted successfully'
    })

@bp.route('/admin/stats', methods=['GET'])
@login_required
@admin_required
def get_stats():
    """Get statistics about the connect points system"""
    # Total points awarded
    total_points_awarded = db.session.query(func.sum(ConnectPoints.points)).filter(
        ConnectPoints.points > 0
    ).scalar() or 0
    
    # Total points redeemed
    total_points_redeemed = db.session.query(func.sum(ConnectPoints.points)).filter(
        ConnectPoints.points < 0
    ).scalar() or 0
    
    # Current points in circulation
    points_in_circulation = total_points_awarded + total_points_redeemed
    
    # Number of vouchers redeemed
    vouchers_redeemed = ConnectPoints.query.filter_by(
        transaction_type='voucher_redemption'
    ).count()
    
    # Top 5 users by point balance
    top_users = db.session.query(
        ConnectPoints.user_id,
        func.sum(ConnectPoints.points).label('total_points')
    ).group_by(ConnectPoints.user_id).order_by(
        func.sum(ConnectPoints.points).desc()
    ).limit(5).all()
    
    top_users_data = []
    for user_id, points in top_users:
        from app.models.user import User
        user = User.query.get(user_id)
        
        if user:
            top_users_data.append({
                'user_id': user_id,
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'points': points
            })
    
    return jsonify({
        'total_points_awarded': total_points_awarded,
        'total_points_redeemed': abs(total_points_redeemed),
        'points_in_circulation': points_in_circulation,
        'vouchers_redeemed': vouchers_redeemed,
        'top_users': top_users_data
    })

@bp.route('/admin/adjust-points', methods=['POST'])
@login_required
@admin_required
def adjust_points():
    """Manually adjust points for a user (admin function)"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['user_id', 'points', 'reason']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Field {field} is required'}), 400
    
    user_id = data['user_id']
    points = int(data['points'])
    reason = data['reason']
    
    from app.models.user import User
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Create points adjustment
    adjustment = ConnectPoints(
        user_id=user_id,
        points=points,
        transaction_type='admin_adjustment',
        description=f"Admin adjustment: {reason}"
    )
    
    db.session.add(adjustment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'user_name': f"{user.first_name} {user.last_name}",
        'points_adjusted': points,
        'new_balance': ConnectPoints.get_user_balance(user_id)
    })