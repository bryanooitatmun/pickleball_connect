from flask import Blueprint, render_template
from flask_login import current_user
from datetime import datetime
bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    now = datetime.utcnow()
    return render_template('index.html', title='Home', now=now)

@bp.route('/about')
def about():
    now = datetime.utcnow()
    return render_template('about.html', title='About Us', now=now)