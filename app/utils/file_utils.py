# app/utils/file_utils.py
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image

def resize_image(file_path, max_size=(800, 800)):
    """Resize an image to be within max dimensions while preserving aspect ratio"""
    try:
        img = Image.open(file_path)
        img.thumbnail(max_size, Image.LANCZOS)
        img.save(file_path, optimize=True, quality=85)
        return True
    except Exception as e:
        print(f"Error resizing image: {str(e)}")
        return False

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_profile_picture(file):
    """Save a profile picture and return the filename"""

    return save_uploaded_file(file, current_app.config['PROFILE_PICS_FOLDER'])

def save_showcase_image(file, coach_id):
    """Save a showcase image and return the filename"""
    
    return save_uploaded_file(file, current_app.config['SHOWCASE_IMAGES_FOLDER'], prefix=f"coach_{coach_id}")

def save_uploaded_file(file, directory, prefix=''):
    """Save an uploaded file and return the filename"""
    if file and allowed_file(file.filename):
        # Create a unique filename
        filename = f"{prefix}_{uuid.uuid4()}_{secure_filename(file.filename)}"
        upload_path = os.path.join(directory, filename).replace('\\', '/')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        
        # Save the file
        file.save(upload_path)

        # Resize image
        resize_image(upload_path)
        
        # Return the relative path for storing in the database
        return os.path.join(os.path.basename(directory), filename)
    
    return None

def delete_file(file_path):
    """Delete a file from the filesystem"""
    if file_path:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
    return False