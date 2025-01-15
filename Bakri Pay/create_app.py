import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app(config_class='config.DevelopmentConfig'):
    """
    Application factory function to create and configure the Flask app
    
    Args:
        config_class: Configuration class path to load
        
    Returns:
        Configured Flask application
    """
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create Flask application
    app = Flask(__name__, 
                template_folder='app/templates',
                static_folder='app/static')
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Configure for proxy use if behind one
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    from app import db
    db.init_app(app)
    
    # Setup login manager
    from app.services.login_manager import setup_login_manager
    setup_login_manager(app)
    
    # Register error handlers
    with app.app_context():
        from app.utils.error_handlers import register_error_handlers
        register_error_handlers(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.accounts import accounts_bp
    from app.routes.transactions import transactions_bp
    from app.routes.cards import cards_bp
    from app.routes.home import home_bp
    
    app.register_blueprint(home_bp)  # No prefix for home routes to handle root URL
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(accounts_bp, url_prefix='/accounts')
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    app.register_blueprint(cards_bp, url_prefix='/cards')
    
    # Ensure database tables are created
    with app.app_context():
        db.create_all()
        logging.info("Database tables created or verified")
    
    return app
