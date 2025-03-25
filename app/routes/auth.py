from flask import Blueprint, render_template, redirect, url_for, flash, request, session
import os
from datetime import datetime, timedelta
import secrets
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models.user import User
from app.forms import LoginForm, SignupForm, ResetPasswordRequestForm, ResetPasswordForm
from app.utils import send_verification_email, send_reset_email
from urllib.parse import urlparse, urljoin

auth_bp = Blueprint('auth_blueprint', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user_blueprint.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            # Add remember_me duration
            if form.remember.data:
                session.permanent = True
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if next_page and url_is_safe(next_page):
                return redirect(next_page)
            return redirect(url_for('user_blueprint.dashboard'))
        flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', form=form)

def url_is_safe(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    form = SignupForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        token = secrets.token_hex(16)
        token_expiry = datetime.utcnow() + timedelta(hours=24)
        
        # Check if we're in development mode
        if os.environ.get('FLASK_DEBUG', 'True') == 'True':
            # In development, auto-verify accounts
            user = User(
                name=form.name.data,
                email=form.email.data,
                password=hashed_password,
                verification_token=token,
                token_expiry=token_expiry,
                is_verified=True  # Auto-verify in development
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('Your account has been created! You can now log in.', 'success')
            print(f"Development mode: Created auto-verified account for {form.email.data}")
        else:
            # In production, require email verification
            user = User(
                name=form.name.data,
                email=form.email.data,
                password=hashed_password,
                verification_token=token,
                token_expiry=token_expiry
            )
            
            db.session.add(user)
            db.session.commit()
            
            # Send verification email
            send_verification_email(user)
            
            flash('Your account has been created! Please check your email to verify your account.', 'success')
        
        return redirect(url_for('auth.login'))
    
    return render_template('signup.html', form=form, title='Sign Up')

@auth_bp.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        if user.token_expiry and user.token_expiry > datetime.utcnow():
            user.is_verified = True
            user.verification_token = None
            user.token_expiry = None
            db.session.commit()
            flash('Your email has been verified! You can now log in.', 'success')
        else:
            flash('The verification link has expired. Please request a new one.', 'warning')
    else:
        flash('Invalid verification link.', 'danger')
    
    return redirect(url_for('auth_blueprint.login'))

@auth_bp.route('/resend_verification')
def resend_verification():
    email = request.args.get('email', '')
    user = User.query.filter_by(email=email).first()
    
    if user and not user.is_verified:
        token = secrets.token_hex(16)
        user.verification_token = token
        user.token_expiry = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        
        send_verification_email(user)
        flash('A new verification email has been sent. Please check your inbox.', 'info')
    elif user and user.is_verified:
        flash('This account is already verified. You can log in.', 'info')
    else:
        flash('Email not found. Please sign up first.', 'warning')
    
    return redirect(url_for('auth_blueprint.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth_blueprint.login'))

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('user_blueprint.dashboard'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = secrets.token_hex(16)
            user.verification_token = token
            user.token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # In development mode, display the reset link in console
            if os.environ.get('FLASK_DEBUG', 'True') == 'True':
                reset_url = url_for('auth_blueprint.reset_password', token=token, _external=True)
                print(f"===== DEVELOPMENT PASSWORD RESET =====")
                print(f"Password Reset Link for {user.email}:")
                print(f"{reset_url}")
                print(f"=======================================")
            
            # Send email (in prod) or log to console (in dev)
            send_reset_email(user)
        
        flash('If an account with that email exists, we have sent you instructions to reset your password.', 'info')
        return redirect(url_for('auth_blueprint.login'))
    
    return render_template('reset_password_request.html', form=form, title='Reset Password')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('user_blueprint.dashboard'))
    
    user = User.query.filter_by(verification_token=token).first()
    if not user or (user.token_expiry and user.token_expiry < datetime.utcnow()):
        flash('The password reset link is invalid or has expired.', 'warning')
        return redirect(url_for('auth_blueprint.reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        user.verification_token = None
        user.token_expiry = None
        db.session.commit()
        
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form, title='Reset Password')
