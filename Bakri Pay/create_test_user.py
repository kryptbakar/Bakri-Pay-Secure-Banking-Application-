"""
Script to create a test user in the database
"""
import sys
from flask import Flask
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime

# Import models from your application
from app.models import User, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = sys.argv[1] if len(sys.argv) > 1 else "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def create_test_user():
    """Create a test user directly in the database"""
    with app.app_context():
        # Check if test user already exists
        existing_user = User.query.filter_by(mobile_number="+923001234567").first()
        if existing_user:
            print(f"Test user already exists with ID: {existing_user.user_id}")
            return existing_user

        # Create new test user
        test_user = User(
            user_id=uuid.uuid4(),
            mobile_number="+923001234567",
            email="testuser@example.com",
            full_name="Test User",
            pin_hash=generate_password_hash("123456"),  # PIN: 123456
            cnic_number="12345-1234567-1",
            is_verified=True,
            account_locked=False,
            failed_login_attempts=0,
            created_at=datetime.utcnow()
        )
        
        db.session.add(test_user)
        db.session.commit()
        
        print(f"Test user created successfully!")
        print(f"User ID: {test_user.user_id}")
        print(f"Mobile: {test_user.mobile_number}")
        print(f"Email: {test_user.email}")
        print(f"PIN: 123456")
        
        return test_user

if __name__ == "__main__":
    create_test_user()