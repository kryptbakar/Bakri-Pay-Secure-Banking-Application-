import re
from datetime import datetime
from functools import wraps

import phonenumbers
from flask import jsonify, request

from app.utils.error_handlers import InvalidInputError


def validate_mobile_number(number):
    """
    Validate international mobile number format
    Returns:
        str: Normalized number if valid
    Raises:
        InvalidInputError: If invalid
    """
    try:
        if not number.startswith('+'):
            raise InvalidInputError("Number must start with country code (e.g. +92...)", field="mobile_number")

        parsed = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(parsed):
            raise InvalidInputError("Invalid phone number", field="mobile_number")

        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )
    except Exception as e:
        if isinstance(e, InvalidInputError):
            raise e
        raise InvalidInputError("Invalid phone number format", field="mobile_number")


def validate_pin(pin):
    """Validate 4-6 digit PIN"""
    if not (pin.isdigit() and 4 <= len(pin) <= 6):
        raise InvalidInputError("PIN must be 4-6 digits", field="pin")
    
    # Check for simple sequences or repeated digits
    if len(set(pin)) <= 2:
        raise InvalidInputError("PIN is too simple (avoid repeated digits)", field="pin")
    
    return pin


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
    if not re.match(pattern, email.lower()):
        raise InvalidInputError("Invalid email address", field="email")
    return email.lower().strip()


def validate_cnic(cnic):
    """Validate Pakistani CNIC format (XXXXX-XXXXXXX-X)"""
    if not re.match(r'^\d{5}-\d{7}-\d$', cnic):
        raise InvalidInputError("CNIC must be in XXXXX-XXXXXXX-X format", field="cnic")
    return cnic


def validate_amount(amount):
    """Validate positive amount with 2 decimal places"""
    try:
        amount = float(amount)
        if amount <= 0:
            raise InvalidInputError("Amount must be positive", field="amount")
        return round(amount, 2)
    except ValueError:
        raise InvalidInputError("Invalid amount", field="amount")


def validate_date(date_str, fmt='%Y-%m-%d'):
    """Validate date format"""
    try:
        return datetime.strptime(date_str, fmt).date()
    except ValueError:
        raise InvalidInputError(f"Date must be in {fmt} format", field="date")


def validate_card_expiry(expiry):
    """Validate MM/YY format and future date"""
    try:
        if not re.match(r'^(0[1-9]|1[0-2])\/?([0-9]{2})$', expiry):
            raise ValueError
        
        # Normalize format by ensuring there's a '/'
        if '/' not in expiry:
            expiry = f"{expiry[:2]}/{expiry[2:]}"

        month, year = map(int, expiry.split('/'))
        current_year = datetime.now().year % 100
        current_month = datetime.now().month

        if year < current_year or (year == current_year and month < current_month):
            raise InvalidInputError("Card has expired", field="expiry")

        return expiry
    except InvalidInputError:
        raise
    except:
        raise InvalidInputError("Expiry must be in MM/YY format", field="expiry")


def validate_request(schema):
    """Decorator to validate request data against schema"""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = request.get_json()
                if not data:
                    raise InvalidInputError("Missing request body")
                    
                validated_data = {}
                for field, validator in schema.items():
                    if field not in data:
                        raise InvalidInputError(f"Missing required field: {field}", field=field)
                    validated_data[field] = validator(data[field])
                
                # Add validated data to request for the route handler
                request.validated_data = validated_data
                return f(*args, **kwargs)
            except InvalidInputError as e:
                return jsonify({"error": e.message, "field": e.field, "code": "VALIDATION_ERROR"}), e.code

        return wrapper

    return decorator
