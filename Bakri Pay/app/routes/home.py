from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

# Create blueprint
home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def index():
    """Handle the root URL - redirect to dashboard if logged in, otherwise show landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('accounts.dashboard'))
    return render_template('home/index.html')