# initial empty file for the app package

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_login import LoginManager
from config import Config

logging.basicConfig(level=logging.DEBUG)

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    
    # Disable CSRF protection for now as we're just prototyping
    app.config['WTF_CSRF_ENABLED'] = False

    # Initialize Flask extensions
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp as auth
    from app.routes.books import books_bp as books
    from app.routes.user import user_bp as user
    
    app.register_blueprint(auth)
    app.register_blueprint(books)
    app.register_blueprint(user)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        
        # Check if admin user exists, if not create one
        from app.models.user import User
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            from app.utils import create_default_admin
            create_default_admin()
    
    return app
