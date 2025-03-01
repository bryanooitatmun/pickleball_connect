# app/routes/api.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.coach import Coach, CoachImage
from app.models.user import User
from app.utils.file_utils import save_uploaded_file, delete_file
import os
import json

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/coach/update-profile-picture', methods=['POST'])
@login_required
def update_profile_picture():
    """Update the coach's profile picture"""
    try:
        if 'profile_picture' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Delete old profile picture if exists
        if current_user.profile_picture:
            delete_file(current_user.profile_picture)
        
        # Save new profile picture
        profile_pic_path = save_uploaded_file(
            file, 
            current_app.config['PROFILE_PICS_DIR'], 
            f"user_{current_user.id}"
        )
        
        if not profile_pic_path:
            return jsonify({'success': False, 'message': 'Failed to save profile picture'}), 400
        
        # Update user record
        current_user.profile_picture = profile_pic_path
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Profile picture updated successfully',
            'profile_picture_url': profile_pic_path
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@bp.route('/coach/remove-profile-picture', methods=['POST'])
@login_required
def remove_profile_picture():
    """Remove the coach's profile picture"""
    if current_user.profile_picture:
        # Delete the file
        delete_file(current_user.profile_picture)
        
        # Update user record
        current_user.profile_picture = None
        db.session.commit()
    
    return jsonify({'success': True, 'message': 'Profile picture removed successfully'})

@bp.route('/coach/showcase-images', methods=['GET'])
@login_required
def get_showcase_images():
    """Get a coach's showcase images"""
    # Get the coach record
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    if not coach:
        return jsonify({'success': False, 'message': 'Coach record not found'}), 404
    
    # Get showcase images
    images = []
    for image in coach.showcase_images:
        images.append({
            'id': image.id,
            'url': f"/static/{image.image_path}",
            'created_at': image.created_at.isoformat()
        })
    
    return jsonify({'success': True, 'images': images})

@bp.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'message': 'File too large. Maximum size is 16MB.'
    }), 413

@bp.route('/coach/update-showcase-images', methods=['POST'])
@login_required
def update_showcase_images():
    """Update a coach's showcase images"""
    # Get coach record
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    if not coach:
        return jsonify({'success': False, 'message': 'Coach record not found'}), 404
    
    try:
        # Handle deleted images
        if 'deleted_image_ids' in request.form:
            deleted_ids = json.loads(request.form['deleted_image_ids'])
            for image_id in deleted_ids:
                image = CoachImage.query.get(image_id)
                if image and image.coach_id == coach.id:
                    # Delete the file
                    delete_file(image.image_path)
                    # Delete the database record
                    db.session.delete(image)
        
        # Handle new images
        if 'new_images' in request.files:
            new_images = request.files.getlist('new_images')
            for file in new_images:
                if file and file.filename:
                    # Save the file
                    image_path = save_uploaded_file(
                        file, 
                        current_app.config['SHOWCASE_IMAGES_DIR'], 
                        f"coach_{coach.id}"
                    )
                    
                    if image_path:
                        # Create a new image record
                        coach_image = CoachImage(
                            coach_id=coach.id,
                            image_path=image_path
                        )
                        db.session.add(coach_image)
        
        # Commit changes
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Showcase images updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating images: {str(e)}'}), 500