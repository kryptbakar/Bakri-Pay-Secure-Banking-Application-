from datetime import datetime

from werkzeug.exceptions import Conflict, Unauthorized, Forbidden

from sadapay.project.app import db
from ..models import User
from ..utils.security import hash_pin, verify_pin


class AuthService:
    @staticmethod
    def register_user(mobile_number, pin, full_name, email, cnic_number):
        """
        Register a new user with enhanced validation and security
        Returns: User object
        Raises: Conflict if user exists, ValueError for invalid data
        """
        # Check existing users
        existing_mobile = User.query.filter_by(mobile_number=mobile_number).first()
        existing_email = User.query.filter_by(email=email).first()
        existing_cnic = User.query.filter_by(cnic_number=cnic_number).first()

        if existing_mobile:
            raise Conflict(description='Mobile number already registered')
        if existing_email:
            raise Conflict(description='Email already registered')
        if existing_cnic:
            raise Conflict(description='CNIC already registered')

        # Create user with enhanced security
        user = User(
            mobile_number=mobile_number,
            pin_hash=hash_pin(pin),  # Using centralized security utility
            full_name=full_name.strip(),
            email=email.lower().strip(),
            cnic_number=cnic_number.strip(),
            is_verified=False,
            created_at=datetime.utcnow()
        )

        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def login_user(mobile_number, pin):
        """
        Authenticate user with brute force protection
        Returns: User object
        Raises: Unauthorized for invalid credentials, Forbidden for locked accounts
        """
        user = User.query.filter_by(mobile_number=mobile_number).first()

        if not user:
            raise Unauthorized(description='Invalid mobile number or PIN')

        # Verify PIN with timing attack protection
        if not verify_pin(user.pin_hash, pin):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.account_locked = True
                db.session.commit()
                raise Forbidden(description='Account locked after multiple failed attempts')
            db.session.commit()
            raise Unauthorized(description='Invalid mobile number or PIN')

        if user.account_locked:
            raise Forbidden(description='Account locked. Please contact support.')

        # Successful login
        user.last_login = datetime.utcnow()
        user.failed_login_attempts = 0
        db.session.commit()
        return user

    @staticmethod
    def reset_password(user_id, old_pin, new_pin):
        """
        Securely change user PIN
        """
        user = User.query.get(user_id)
        if not user:
            raise Unauthorized(description='User not found')

        if not verify_pin(user.pin_hash, old_pin):
            raise Unauthorized(description='Invalid current PIN')

        user.pin_hash = hash_pin(new_pin)
        db.session.commit()
        return True
