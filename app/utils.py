import os
import secrets
from datetime import datetime, timedelta
from flask import url_for
from flask_mail import Message
from app import bcrypt, mail, db
from app.models.user import User

def send_verification_email(user):
    token = user.verification_token
    verification_url = url_for('auth_blueprint.verify_email', token=token, _external=True)
    
    # Check if we're in development mode (using environment variable or checking for debug mode)
    if os.environ.get('FLASK_DEBUG', 'True') == 'True':
        # In development, print the verification URL to console instead of sending email
        print(f"===== DEVELOPMENT EMAIL =====")
        print(f"Email Verification Link for {user.email}:")
        print(f"{verification_url}")
        print(f"=============================")
        return True
    
    # In production, try to send the actual email
    msg = Message('Verify Your Library Account',
                 sender=os.environ.get('MAIL_USERNAME', 'library@example.com'),
                 recipients=[user.email])
    
    msg.body = f'''To verify your account, please visit the following link:
{verification_url}

If you did not make this request, please ignore this email and no changes will be made.

This link will expire in 24 hours.

Thank you,
The Library Management Team
'''
    
    msg.html = f'''
<p>To verify your account, please click the link below:</p>
<p><a href="{verification_url}">Verify Your Account</a></p>
<p>If you did not make this request, please ignore this email and no changes will be made.</p>
<p>This link will expire in 24 hours.</p>
<p>Thank you,<br>The Library Management Team</p>
'''
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False

def send_reset_email(user):
    """
    Send password reset link to users
    """
    token = user.verification_token
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    # Check if we're in development mode (using environment variable or checking for debug mode)
    if os.environ.get('FLASK_DEBUG', 'True') == 'True':
        # In development, print the reset URL to console instead of sending email
        print(f"===== DEVELOPMENT EMAIL =====")
        print(f"Password Reset Link for {user.email}:")
        print(f"{reset_url}")
        print(f"=============================")
        return True
    
    # In production, try to send the actual email
    msg = Message('Reset Your Library Account Password',
                 sender=os.environ.get('MAIL_USERNAME', 'library@example.com'),
                 recipients=[user.email])
    
    msg.body = f'''To reset your password, please visit the following link:
{reset_url}

If you did not request a password reset, please ignore this email and no changes will be made.

This link will expire in 1 hour.

Thank you,
The Library Management Team
'''
    
    msg.html = f'''
<p>To reset your password, please click the link below:</p>
<p><a href="{reset_url}">Reset Your Password</a></p>
<p>If you did not request a password reset, please ignore this email and no changes will be made.</p>
<p>This link will expire in 1 hour.</p>
<p>Thank you,<br>The Library Management Team</p>
'''
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending reset email: {e}")
        return False

def send_due_notification(user, borrow_record):
    """
    Send notifications for books due soon
    """
    book = borrow_record.book
    days_remaining = (borrow_record.due_date - datetime.utcnow()).days
    
    subject = 'Book Due Soon' if days_remaining > 0 else 'Book Overdue Notice'
    
    # Check if we're in development mode
    if os.environ.get('FLASK_DEBUG', 'True') == 'True':
        # In development, print the notification to console instead of sending email
        print(f"===== DEVELOPMENT EMAIL =====")
        print(f"Due/Overdue Notification for {user.email}:")
        if days_remaining > 0:
            print(f"Book: {book.title} is due in {days_remaining} days (due on {borrow_record.due_date.strftime('%Y-%m-%d')})")
        else:
            days_overdue = abs(days_remaining)
            fine_amount = days_overdue * 0.50  # $0.50 per day
            print(f"Book: {book.title} is {days_overdue} days overdue (was due on {borrow_record.due_date.strftime('%Y-%m-%d')})")
            print(f"Fine amount: ${fine_amount:.2f}")
        print(f"=============================")
        return True
    
    # In production, try to send the actual email
    msg = Message(subject,
                 sender=os.environ.get('MAIL_USERNAME', 'library@example.com'),
                 recipients=[user.email])
    
    if days_remaining > 0:
        msg.body = f'''Dear {user.name},

This is a reminder that the book "{book.title}" is due in {days_remaining} days.
Please return it by {borrow_record.due_date.strftime('%Y-%m-%d')} to avoid late fees.

You can renew this book online if you need more time.

Thank you,
The Library Management Team
'''
        
        msg.html = f'''
<p>Dear {user.name},</p>
<p>This is a reminder that the book <strong>"{book.title}"</strong> is due in <strong>{days_remaining} days</strong>.</p>
<p>Please return it by <strong>{borrow_record.due_date.strftime('%Y-%m-%d')}</strong> to avoid late fees.</p>
<p>You can renew this book online if you need more time.</p>
<p>Thank you,<br>The Library Management Team</p>
'''
    else:
        days_overdue = abs(days_remaining)
        fine_amount = days_overdue * 0.50  # $0.50 per day
        
        msg.body = f'''Dear {user.name},

The book "{book.title}" is {days_overdue} days overdue. 
It was due on {borrow_record.due_date.strftime('%Y-%m-%d')}.

Current fine: ${fine_amount:.2f} (${0.50:.2f} per day).

Please return the book as soon as possible to avoid additional fees.

Thank you,
The Library Management Team
'''
        
        msg.html = f'''
<p>Dear {user.name},</p>
<p>The book <strong>"{book.title}"</strong> is <strong>{days_overdue} days overdue</strong>. 
It was due on {borrow_record.due_date.strftime('%Y-%m-%d')}.</p>
<p>Current fine: <strong>${fine_amount:.2f}</strong> (${0.50:.2f} per day).</p>
<p>Please return the book as soon as possible to avoid additional fees.</p>
<p>Thank you,<br>The Library Management Team</p>
'''
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending due notification: {e}")
        return False

def create_default_admin():
    """
    Create a default admin user if no admin exists
    """
    default_admin_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@library.com')
    default_admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'Admin@123')
    
    admin = User.query.filter_by(email=default_admin_email).first()
    
    if not admin:
        hashed_password = bcrypt.generate_password_hash(default_admin_password).decode('utf-8')
        
        admin = User(
            name='System Administrator',
            email=default_admin_email,
            password=hashed_password,
            role='admin',
            is_verified=True
        )
        
        db.session.add(admin)
        db.session.commit()
        print(f"Created default admin user: {default_admin_email}")
        return True
    
    return False

def check_and_notify_due_books():
    """
    Check for books due soon or overdue and send notifications
    """
    from app.models.books import BorrowRecord
    
    # Books due in the next 2 days
    soon_due_records = BorrowRecord.query.filter(
        BorrowRecord.is_returned == False,
        BorrowRecord.due_date.between(
            datetime.utcnow(),
            datetime.utcnow() + timedelta(days=2)
        )
    ).all()
    
    # Books that are overdue
    overdue_records = BorrowRecord.query.filter(
        BorrowRecord.is_returned == False,
        BorrowRecord.due_date < datetime.utcnow()
    ).all()
    
    # Send notifications for books due soon
    for record in soon_due_records:
        send_due_notification(record.user, record)
    
    # Send notifications for overdue books
    for record in overdue_records:
        # Only send overdue notices every 3 days to avoid spamming
        days_overdue = (datetime.utcnow() - record.due_date).days
        if days_overdue % 3 == 0:  # Send on days 3, 6, 9, etc.
            send_due_notification(record.user, record)
    
    return len(soon_due_records), len(overdue_records)
