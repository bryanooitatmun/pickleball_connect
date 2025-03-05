# app/__init__.py
from flask import Flask, Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
import os
import logging
from logging.handlers import RotatingFileHandler

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.coaches import bp as coaches_bp
    from app.routes.students import bp as students_bp
    from app.routes.bookings import bp as bookings_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.api import bp as api_bp
    from app.routes.admin_connect_points import bp as admin_connect_points_bp
    from app.routes.connect_points import bp as connect_points_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(coaches_bp, url_prefix='/coach')
    app.register_blueprint(students_bp, url_prefix='/student')
    app.register_blueprint(bookings_bp, url_prefix='/booking')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(admin_connect_points_bp, url_prefix='/admin/connect-points')
    app.register_blueprint(connect_points_bp, url_prefix='/api/connect-points')
    
    # Ensure the upload directories exist
    os.makedirs(app.config['PROFILE_PICS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SHOWCASE_IMAGES_FOLDER'], exist_ok=True)
    
    @login.user_loader
    def load_user(id):
        from app.models.user import User
        return User.query.get(int(id))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Configure static files with longer cache time for uploaded images
    @app.route('/static/uploads/<path:filename>')
    def serve_uploads(filename):
        response = send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        cache_time = app.config.get('STATIC_CACHE_TIMEOUT', 60*60*24*7)  # Default to 7 days
        response.headers['Cache-Control'] = f'max-age={cache_time}, public'
        return response

    # Set up logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/pickleball_connect.log',
                                           maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Pickleball Connect startup')

    return app