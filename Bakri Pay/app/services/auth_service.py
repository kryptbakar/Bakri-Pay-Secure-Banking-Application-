from flask import current_app, session
from werkzeug.exceptions import Forbidden, Unauthorized
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
from datetime import datetime, timedelta
import logging

from app import db
from app.models import User, OTP

class AuthService:
    """Service class for authentication related operations"""
    
    @staticmethod
    def register_user(mobile_number, pin, full_name, email, cnic_number):
        """
        Register a new user with enhanced validation and security
        
        Args:
            mobile_number (str): User's mobile number in international format
            pin (str): User's chosen PIN
            full_name (str): User's full name
            email (str): User's email address
            cnic_number (str): User's CNIC or identification number
            
        Returns:
            User: The newly created user object
            
        Raises:
            ValueError: If mobile number, email, or CNIC already exists
        """
        # Check if user with given mobile already exists
        if User.query.filter_by(mobile_number=mobile_number).first():
            raise ValueError("A user with this mobile number already exists")
            
        # Check if user with given email already exists
        if User.query.filter_by(email=email).first():
            raise ValueError("A user with this email already exists")
            
        # Check if user with given CNIC already exists
        if User.query.filter_by(cnic_number=cnic_number).first():
            raise ValueError("A user with this CNIC number already exists")
        
        # Create new user
        user = User(
            mobile_number=mobile_number,
            email=email,
            full_name=full_name,
            cnic_number=cnic_number
        )
        user.set_pin(pin)
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
        logging.info(f"New user registered: {user.user_id}")
        return user
    
    @staticmethod
    def login_user(mobile_number, pin):
        """
        Authenticate user with brute force protection
        
        Args:
            mobile_number (str): User's mobile number
            pin (str): User's PIN
            
        Returns:
            User: The authenticated user
            
        Raises:
            Unauthorized: If credentials are invalid
            Forbidden: If account is locked
        """
        # Find user by mobile number
        user = User.query.filter_by(mobile_number=mobile_number).first()
        
        # Check if user exists
        if not user:
            raise Unauthorized("Invalid mobile number or PIN")
            
        # Check if account is locked
        if user.account_locked:
            raise Forbidden("Account is locked due to too many failed attempts")
        
        # Verify PIN
        if not user.check_pin(pin):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= 5:
                user.account_locked = True
                db.session.commit()
                raise Forbidden("Account has been locked due to too many failed attempts")
                
            db.session.commit()
            raise Unauthorized("Invalid mobile number or PIN")
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Store user in session
        session['user_id'] = str(user.user_id)
        session['full_name'] = user.full_name
        
        logging.info(f"User logged in: {user.user_id}")
        return user
    
    @staticmethod
    def logout_user():
        """
        Log out the current user
        """
        session.pop('user_id', None)
        session.pop('full_name', None)
        logging.info("User logged out")
    
    @staticmethod
    def reset_pin(user_id, old_pin, new_pin):
        """
        Securely change user PIN
        
        Args:
            user_id (str): User ID
            old_pin (str): Current PIN
            new_pin (str): New PIN
            
        Returns:
            bool: True if successful
            
        Raises:
            Unauthorized: If old PIN is incorrect
            ValueError: If new PIN does not meet requirements
        """
        user = User.query.get(user_id)
        
        if not user:
            raise ValueError("User not found")
            
        if not user.check_pin(old_pin):
            raise Unauthorized("Current PIN is incorrect")
        
        # Set new PIN
        user.set_pin(new_pin)
        db.session.commit()
        
        logging.info(f"PIN reset for user: {user.user_id}")
        return True
    
    @staticmethod
    def generate_otp(user_id, purpose="verification", expiry_minutes=5):
        """
        Generate a one-time password for user verification
        
        Args:
            user_id (str): User ID
            purpose (str): Purpose of OTP (verification, login, transaction)
            expiry_minutes (int): Expiry time in minutes
            
        Returns:
            str: Generated OTP code
        """
        import random
        
        # Generate a 6-digit OTP
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Calculate expiry time
        expiry_time = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # Create OTP record
        otp = OTP(
            user_id=user_id,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expiry_time
        )
        
        db.session.add(otp)
        db.session.commit()
        
        logging.info(f"OTP generated for user: {user_id}, purpose: {purpose}")
        return otp_code
    
    @staticmethod
    def verify_otp(user_id, otp_code, purpose="verification"):
        """
        Verify an OTP code
        
        Args:
            user_id (str): User ID
            otp_code (str): OTP code to verify
            purpose (str): Purpose of OTP
            
        Returns:
            bool: True if verified successfully
            
        Raises:
            Unauthorized: If OTP is invalid, expired, or used
        """
        # Find the latest OTP for this user and purpose
        otp = OTP.query.filter_by(
            user_id=user_id,
            purpose=purpose,
            is_used=False
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            raise Unauthorized("No valid OTP found")
            
        # Check if OTP has expired
        if datetime.utcnow() > otp.expires_at:
            raise Unauthorized("OTP has expired")
            
        # Check if OTP matches
        if otp.otp_code != otp_code:
            raise Unauthorized("Invalid OTP code")
            
        # Mark OTP as used
        otp.is_used = True
        
        # Mark user as verified if purpose is verification
        if purpose == "verification":
            user = User.query.get(user_id)
            user.is_verified = True
            
        db.session.commit()
        
        logging.info(f"OTP verified for user: {user_id}, purpose: {purpose}")
        return True