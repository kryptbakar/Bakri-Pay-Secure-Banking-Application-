import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from create_app import create_app

# App initialization
config_class = os.getenv('FLASK_CONFIG', 'config.DevelopmentConfig')
app = create_app(config_class=config_class)

if __name__ == '__main__':
    # App server settings
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    app.run(host=host, port=port, debug=debug)