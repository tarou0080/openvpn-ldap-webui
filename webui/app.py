#!/usr/bin/env python3

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from flask import Flask, make_response, request, redirect, url_for
from flask_wtf.csrf import CSRFProtect

# Import custom modules
from config import (
    SECRET_KEY, LOG_ROTATION_TYPE, LOG_MAX_SIZE_MB, 
    LOG_BACKUP_COUNT, LOG_ROTATION_WHEN, LOG_ROTATION_INTERVAL
)
from database import init_db
from routes_user import user_bp
from routes_admin_certs import admin_certs_bp
from routes_admin_system import admin_system_bp
from routes_admin_logs import admin_logs_bp
from translations import load_translations, inject_i18n, get_supported_languages

# Initialize Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Enable CSRF protection
csrf = CSRFProtect(app)

# Logging configuration
os.makedirs('/app/data/logs', exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Log format
log_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

# File handler (switch based on type)
if LOG_ROTATION_TYPE == 'time':
    # Time-based rotation
    file_handler = TimedRotatingFileHandler(
        '/app/data/logs/app.log',
        when=LOG_ROTATION_WHEN,
        interval=LOG_ROTATION_INTERVAL,
        backupCount=LOG_BACKUP_COUNT
    )
    logger.info(f"Log rotation: time-based ({LOG_ROTATION_WHEN}, interval={LOG_ROTATION_INTERVAL}, backupCount={LOG_BACKUP_COUNT})")
else:
    # Size-based rotation
    file_handler = RotatingFileHandler(
        '/app/data/logs/app.log',
        maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT
    )
    logger.info(f"Log rotation: size-based ({LOG_MAX_SIZE_MB}MB, backupCount={LOG_BACKUP_COUNT})")

file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# Also maintain console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

# Apply to Flask logger as well
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Load translation dictionaries
load_translations()

# Inject translation function into Jinja2 templates
app.context_processor(inject_i18n)

# Language switching route
@app.route('/change-language')
def change_language():
    """Language switching"""
    lang = request.args.get('lang', 'en')
    
    # Check if language is supported
    if lang not in get_supported_languages():
        lang = 'en'
    
    # Get current referrer URL (return destination)
    redirect_url = request.referrer or url_for('user.index')
    
    # Create response and set Cookie
    response = make_response(redirect(redirect_url))
    response.set_cookie('lang', lang, max_age=60*60*24*365)  # Valid for 1 year
    
    return response

# Register Blueprints
app.register_blueprint(user_bp)
app.register_blueprint(admin_certs_bp)
app.register_blueprint(admin_system_bp)
app.register_blueprint(admin_logs_bp)

if __name__ == '__main__':
    # Initialize database
    from config import DATABASE_PATH
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()
    
    # Start Flask
    app.run(host='0.0.0.0', port=5000, debug=False)