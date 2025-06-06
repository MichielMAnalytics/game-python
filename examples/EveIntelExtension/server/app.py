from flask import Flask
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app(config_object="config"):
    """
    Application factory function that creates and configures the Flask app
    """
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Configure CORS
    CORS(app)
    
    # Set up logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/eve_intel.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('EveIntel backend startup')
    
    # Register routes
    from routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register error handlers
    from utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    return app 