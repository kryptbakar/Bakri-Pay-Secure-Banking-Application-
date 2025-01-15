import re
from datetime import datetime
from functools import wraps

import phonenumbers
from flask import jsonify


class ValidationError(Exception):
    """Custom validation error class"""

    def __init__(self, message, code=400):
        self.message = message
        self.code = code


def validate_mobile_number(number):
    """
    Validate international mobile number format
    Returns:
        str: Normalized number if valid
    Raises:
        ValidationError: If invalid
    """
    try:
        if not number.startswith('+'):
            raise ValidationError("Number must start with country code (e.g. +92...)")

        parsed = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(parsed):
            raise ValidationError("Invalid phone number")

        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )
    except Exception as e:
        raise ValidationError("Invalid phone number format") from e


def validate_pin(pin):
    """Validate 4-6 digit PIN"""
    if not (pin.isdigit() and 4 <= len(pin) <= 6):
        raise ValidationError("PIN must be 4-6 digits")
    return pin


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
    if not re.match(pattern, email.lower()):
        raise ValidationError("Invalid email address")
    return email.lower().strip()


def validate_cnic(cnic):
    """Validate Pakistani CNIC format (XXXXX-XXXXXXX-X)"""
    if not re.match(r'^\d{5}-\d{7}-\d$', cnic):
        raise ValidationError("CNIC must be in XXXXX-XXXXXXX-X format")
    return cnic


def validate_amount(amount):
    """Validate positive amount with 2 decimal places"""
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValidationError("Amount must be positive")
        return round(amount, 2)
    except ValueError:
        raise ValidationError("Invalid amount")


def validate_date(date_str, fmt='%Y-%m-%d'):
    """Validate date format"""
    try:
        return datetime.strptime(date_str, fmt).date()
    except ValueError:
        raise ValidationError(f"Date must be in {fmt} format")


def validate_card_expiry(expiry):
    """Validate MM/YY format and future date"""
    try:
        if not re.match(r'^(0[1-9]|1[0-2])\/?([0-9]{2})$', expiry):
            raise ValueError

        month, year = map(int, expiry.split('/'))
        current_year = datetime.now().year % 100
        current_month = datetime.now().month

        if year < current_year or (year == current_year and month < current_month):
            raise ValidationError("Card has expired")

        return expiry
    except:
        raise ValidationError("Expiry must be in MM/YY format")


def validate_request(schema):
    """Decorator to validate request data against schema"""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = request.get_json()
                for field, validator in schema.items():
                    if field not in data:
                        raise ValidationError(f"Missing {field}")
                    data[field] = validator(data[field])
                return f(*args, **kwargs)
            except ValidationError as e:
                return jsonify({"error": e.message}), e.code

        return wrapper

    return decorator
