import re
from datetime import datetime, timedelta
from functools import wraps

import phonenumbers
from flask import session, jsonify, current_app, redirect, url_for, request
from werkzeug.security import check_password_hash, generate_password_hash


# Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not verify_active_session():
            if request.is_json:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'UNAUTHORIZED'
                }), 401
            else:
                return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'is_admin' not in session or not session['is_admin']:
            return jsonify({
                'error': 'Admin privileges required',
                'code': 'FORBIDDEN'
            }), 403
        return f(*args, **kwargs)

    return decorated_function


# Session Management
def verify_active_session():
    """Check if session is still valid"""
    last_activity = session.get('last_activity')
    if not last_activity or (datetime.utcnow() - datetime.fromisoformat(last_activity)) > timedelta(minutes=30):
        session.clear()
        return False
    session['last_activity'] = datetime.utcnow().isoformat()
    return True


def get_current_user_id():
    """Get user ID with session validation"""
    if verify_active_session():
        return session.get('user_id')
    return None


# Security Utilities
def validate_mobile_number(number):
    """Strict phone number validation with country code"""
    try:
        parsed = phonenumbers.parse(number, None)
        return phonenumbers.is_valid_number(parsed) and \
            phonenumbers.is_possible_number(parsed)
    except:
        return False


def validate_pin(pin):
    """Secure PIN validation"""
    return len(pin) >= 4 and len(pin) <= 6 and \
        pin.isdigit() and \
        len(set(pin)) > 2  # Prevent simple sequences


def validate_password(password):
    """Password complexity checker"""
    return len(password) >= 8 and \
        any(c.isupper() for c in password) and \
        any(c.isdigit() for c in password) and \
        any(not c.isalnum() for c in password)


def validate_email(email):
    """Comprehensive email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_cnic(cnic):
    """CNIC validation for Pakistani format"""
    return re.match(r'^[0-9]{5}-[0-9]{7}-[0-9]$', cnic) is not None


# Password Hashing
def hash_pin(pin):
    """Secure PIN hashing with app secret"""
    secret = current_app.config['SECRET_KEY']
    return generate_password_hash(f"{pin}{secret}")


def verify_pin(pin_hash, pin):
    """PIN verification with timing attack protection"""
    secret = current_app.config['SECRET_KEY']
    return check_password_hash(pin_hash, f"{pin}{secret}")
