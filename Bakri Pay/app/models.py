import uuid
from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import UUID
from app import db

# Helper function to generate UUIDs
def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model, UserMixin):
    """User model for authentication and user information"""
    __tablename__ = 'users'
    
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    pin_hash = db.Column(db.String(200), nullable=False)
    cnic_number = db.Column(db.String(15), unique=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    account_locked = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    accounts = db.relationship('Account', back_populates='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.mobile_number}>'
    
    def get_id(self):
        """Override for Flask-Login to use user_id as the identifier"""
        return str(self.user_id)
    
    def set_pin(self, pin):
        """Set a hashed PIN for the user"""
        self.pin_hash = generate_password_hash(pin)
    
    def check_pin(self, pin):
        """Validate a PIN against the hash"""
        return check_password_hash(self.pin_hash, pin)


class Account(db.Model):
    """Bank account model"""
    __tablename__ = 'accounts'
    
    account_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(db.Numeric(precision=12, scale=2), default=0)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='accounts')
    cards = db.relationship('Card', back_populates='account', lazy='dynamic')
    
    def __repr__(self):
        return f'<Account {self.account_number}>'


class Card(db.Model):
    """Card model for virtual and physical cards"""
    __tablename__ = 'cards'
    
    card_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.account_id'), nullable=False)
    card_number = db.Column(db.String(20), unique=True, nullable=False)
    expiry_date = db.Column(db.String(5), nullable=False)  # MM/YY format
    cvv_hash = db.Column(db.String(200), nullable=False)
    is_virtual = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deactivated_at = db.Column(db.DateTime, nullable=True)
    deactivation_reason = db.Column(db.String(50), nullable=True)
    delivery_address = db.Column(db.JSON, nullable=True)
    
    # Relationships
    account = db.relationship('Account', back_populates='cards')
    
    def __repr__(self):
        return f'<Card {self.card_number[-4:]}>'


class Transaction(db.Model):
    """Transaction model for tracking all money movements"""
    __tablename__ = 'transactions'
    
    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_account_id = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.account_id'), nullable=True)
    to_account_id = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.account_id'), nullable=False)
    amount = db.Column(db.Numeric(precision=12, scale=2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # transfer, deposit, withdrawal
    reference = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    is_fraudulent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    sender_account = db.relationship('Account', foreign_keys=[from_account_id], backref='sent_transactions')
    receiver_account = db.relationship('Account', foreign_keys=[to_account_id], backref='received_transactions')
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id} {self.amount}>'


class FraudAlert(db.Model):
    """Model for tracking potential fraudulent activity"""
    __tablename__ = 'fraud_alerts'
    
    alert_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = db.Column(UUID(as_uuid=True), db.ForeignKey('transactions.transaction_id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    action_taken = db.Column(db.String(50), default='flagged')  # flagged, blocked, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    transaction = db.relationship('Transaction', backref='fraud_alerts')
    
    def __repr__(self):
        return f'<FraudAlert {self.alert_id}>'


class OTP(db.Model):
    """One-time password model for verifications"""
    __tablename__ = 'otps'
    
    otp_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    otp_code = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # verification, login, transaction
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='otps')
    
    def __repr__(self):
        return f'<OTP {self.otp_id}>'


class Notification(db.Model):
    """Notification model for user alerts and messages"""
    __tablename__ = 'notifications'
    
    notification_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.notification_id}>'
