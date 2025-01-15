from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
import sys

# Ensure the parent directory of "app" is in sys.path (for module search)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class='config.DevelopmentConfig'):
    """Application factory for creating Flask apps."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    with app.app_context():
        from app.routes.auth import auth_bp  # Absolute import
        app.register_blueprint(auth_bp)

        # Import models for migrations
        from app import models  # Absolute import

    return app
