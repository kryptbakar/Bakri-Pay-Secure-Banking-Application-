import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.services.auth_service import AuthService
from app.utils.validators import validate_mobile_number, validate_pin, validate_request, validate_email, validate_cnic
from app.utils.error_handlers import InvalidInputError

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration endpoint"""
    if request.method == 'GET':
        return render_template('login.html', action='register')
    
    try:
        data = request.form if request.form else request.get_json()
        
        if not data:
            raise InvalidInputError("No data provided", code=400)
        
        required_fields = ['mobile_number', 'pin', 'full_name', 'email', 'cnic_number']
        for field in required_fields:
            if field not in data:
                raise InvalidInputError(f"Missing required field: {field}", field=field, code=400)
        
        # Validate inputs
        mobile_number = validate_mobile_number(data['mobile_number'])
        pin = validate_pin(data['pin'])
        email = validate_email(data['email'])
        cnic = validate_cnic(data['cnic_number'])
        
        # Registration logic
        user = AuthService.register_user(
            mobile_number=mobile_number,
            pin=pin,
            full_name=data['full_name'],
            email=email,
            cnic_number=cnic
        )
        
        if request.is_json:
            return jsonify({
                'message': 'Registration successful, verification required',
                'user_id': str(user.user_id)
            }), 201
        else:
            flash('Registration successful! Please verify your account.', 'success')
            return redirect(url_for('auth.login'))
            
    except InvalidInputError as e:
        logger.warning(f"Registration validation error: {e.message}")
        if request.is_json:
            return jsonify({
                'error': e.message,
                'field': getattr(e, 'field', None),
                'code': 'VALIDATION_ERROR'
            }), e.code
        else:
            flash(e.message, 'danger')
            return render_template('login.html', action='register', error=e.message)
            
    except ValueError as e:
        # This catches specific validation errors like duplicate email/mobile
        logger.error(f"Registration error: {str(e)}")
        if request.is_json:
            return jsonify({
                'error': str(e),
                'code': 'VALIDATION_ERROR'
            }), 400
        else:
            flash(str(e), 'danger')
            return render_template('login.html', action='register', error=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        if request.is_json:
            return jsonify({
                'error': 'Registration failed',
                'code': 'SERVER_ERROR'
            }), 500
        else:
            flash('Registration failed. Please try again.', 'danger')
            return render_template('login.html', action='register', error='Registration failed')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login endpoint"""
    if request.method == 'GET':
        return render_template('login.html', action='login')
    
    try:
        data = request.form if request.form else request.get_json()
        
        if not data or 'mobile_number' not in data or 'pin' not in data:
            raise InvalidInputError("Mobile number and PIN required", code=400)
        
        # Login logic
        user = AuthService.login_user(
            mobile_number=data['mobile_number'],
            pin=data['pin']
        )
        
        # Use Flask-Login to log in the user
        login_user(user)
        session['last_activity'] = datetime.utcnow().isoformat()
        
        if request.is_json:
            return jsonify({
                'message': 'Login successful',
                'user_id': str(user.user_id)
            }), 200
        else:
            return redirect(url_for('accounts.dashboard'))
            
    except InvalidInputError as e:
        if request.is_json:
            return jsonify({
                'error': e.message,
                'field': getattr(e, 'field', None),
                'code': 'VALIDATION_ERROR'
            }), e.code
        else:
            flash(e.message, 'danger')
            return render_template('login.html', action='login', error=e.message)
            
    except ValueError as e:
        # Handle specific user-facing errors
        logger.warning(f"Login error: {str(e)}")
        if request.is_json:
            return jsonify({
                'error': str(e),
                'code': 'AUTH_ERROR'
            }), 401
        else:
            flash(str(e), 'danger')
            return render_template('login.html', action='login', error=str(e))
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        if request.is_json:
            return jsonify({
                'error': 'Login failed',
                'code': 'AUTH_ERROR'
            }), 401
        else:
            flash('Login failed. Please check your credentials.', 'danger')
            return render_template('login.html', action='login', error='Login failed')


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Logout endpoint"""
    logout_user()  # Flask-Login's logout function
    session.clear()
    
    if request.is_json:
        return jsonify({'message': 'Logged out successfully'}), 200
    else:
        flash('You have been logged out', 'info')
        return redirect(url_for('auth.login'))


@auth_bp.route('/verify', methods=['POST'])
def verify_otp():
    """Verify OTP for user registration or other purposes"""
    try:
        data = request.form if request.form else request.get_json()
        
        if not data or 'user_id' not in data or 'otp_code' not in data or 'purpose' not in data:
            raise InvalidInputError("Missing required fields", code=400)
        
        # Verify OTP
        success = AuthService.verify_otp(
            user_id=data['user_id'],
            otp_code=data['otp_code'],
            purpose=data['purpose']
        )
        
        if success:
            if request.is_json:
                return jsonify({'message': 'Verification successful'}), 200
            else:
                flash('Verification successful', 'success')
                return redirect(url_for('auth.login'))
        else:
            raise InvalidInputError("Invalid or expired OTP", code=400)
            
    except InvalidInputError as e:
        if request.is_json:
            return jsonify({
                'error': e.message,
                'code': 'VALIDATION_ERROR'
            }), e.code
        else:
            flash(e.message, 'danger')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        logger.error(f"OTP verification error: {str(e)}")
        if request.is_json:
            return jsonify({
                'error': 'Verification failed',
                'code': 'SERVER_ERROR'
            }), 500
        else:
            flash('Verification failed', 'danger')
            return redirect(url_for('auth.login'))


@auth_bp.route('/reset-pin', methods=['POST'])
@login_required
def reset_pin():
    """Reset PIN endpoint"""
    try:
        data = request.form if request.form else request.get_json()
        
        if not data or 'old_pin' not in data or 'new_pin' not in data:
            raise InvalidInputError("Missing required fields", code=400)
        
        # Validate new PIN
        new_pin = validate_pin(data['new_pin'])
        
        # Reset PIN using current_user's ID
        success = AuthService.reset_pin(
            user_id=current_user.user_id,
            old_pin=data['old_pin'],
            new_pin=new_pin
        )
        
        if success:
            if request.is_json:
                return jsonify({'message': 'PIN reset successful'}), 200
            else:
                flash('PIN reset successful', 'success')
                return redirect(url_for('accounts.dashboard'))
        else:
            raise Exception("PIN reset failed")
            
    except InvalidInputError as e:
        if request.is_json:
            return jsonify({
                'error': e.message,
                'code': 'VALIDATION_ERROR'
            }), e.code
        else:
            flash(e.message, 'danger')
            return redirect(url_for('accounts.dashboard'))
            
    except ValueError as e:
        # Handle specific validation errors
        logger.warning(f"PIN reset validation error: {str(e)}")
        if request.is_json:
            return jsonify({
                'error': str(e),
                'code': 'VALIDATION_ERROR'
            }), 400
        else:
            flash(str(e), 'danger')
            return redirect(url_for('accounts.dashboard'))
    except Exception as e:
        logger.error(f"PIN reset error: {str(e)}")
        if request.is_json:
            return jsonify({
                'error': 'PIN reset failed',
                'code': 'SERVER_ERROR'
            }), 500
        else:
            flash('PIN reset failed', 'danger')
            return redirect(url_for('accounts.dashboard'))
