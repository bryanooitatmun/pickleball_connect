# Add to app/routes/admin.py (create this file if it doesn't exist)
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.models.court import Court
from app.models.court_fee import CourtFee
from app.models.user import User
from datetime import datetime, time
from functools import wraps

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

@bp.route('/courts')
@login_required
@admin_required
def courts():
    """Admin interface for courts management"""
    courts = Court.query.all()
    return render_template('admin/courts.html', courts=courts)

@bp.route('/courts/<int:court_id>/fees')
@login_required
@admin_required
def court_fees(court_id):
    """Admin interface for managing court fees"""
    court = Court.query.get_or_404(court_id)
    fees = CourtFee.query.filter_by(court_id=court_id).order_by(CourtFee.start_time).all()
    return render_template('admin/court_fees.html', court=court, fees=fees)

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