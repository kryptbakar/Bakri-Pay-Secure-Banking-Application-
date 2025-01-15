import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration with shared settings."""
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    SESSION_COOKIE_SECURE = True  # HTTPS required
    SESSION_COOKIE_HTTPONLY = True

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 30,
    }

    PERMANENT_SESSION_LIFETIME = 3600
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'username@example.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')


config_class = os.getenv('FLASK_CONFIG', 'config.DevelopmentConfig')  # Adjusted config path


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Enforce HTTPS in production


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory database for testing
