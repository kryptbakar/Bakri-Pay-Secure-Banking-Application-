# config/__init__.py

class DevelopmentConfig:
    """Development configuration class."""
    DEBUG = True
    TESTING = False
    SECRET_KEY = 'replace-with-a-secure-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///development.db'  # Example database URI
