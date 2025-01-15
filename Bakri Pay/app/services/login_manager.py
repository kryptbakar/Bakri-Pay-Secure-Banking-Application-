from flask_login import LoginManager
from flask import redirect, url_for, flash
import logging

from app.models import User

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    """
    LoadUser callback function for Flask-Login
    
    Args:
        user_id (str): User ID to load
        
    Returns:
        User: User object or None
    """
    try:
        return User.query.get(user_id)
    except Exception as e:
        logging.error(f"Error loading user: {e}")
        return None

def setup_login_manager(app):
    """
    Initialize the login manager with the flask app
    
    Args:
        app: Flask application instance
        
    Returns:
        LoginManager: Configured login manager
    """
    login_manager.init_app(app)
    return login_manager