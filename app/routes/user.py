from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.books import Book, BorrowRecord
from app.forms import ProfileUpdateForm, UserRoleForm
from datetime import datetime

user_bp = Blueprint('user_blueprint', __name__, url_prefix='/user')

@user_bp.route('/')
def index():
    # Featured/newest books for home page
    recent_books = Book.query.order_by(Book.created_at.desc()).limit(6).all()
    return render_template('index.html', recent_books=recent_books)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # If admin, redirect to admin dashboard
    if current_user.is_admin:
        return redirect(url_for('user_blueprint.admin_dashboard'))
    
    # Get currently borrowed books
    borrowed_books = BorrowRecord.query.filter_by(
        user_id=current_user.id,
        is_returned=False
    ).order_by(BorrowRecord.due_date).all()
    
    # Get recently returned books (last 5)
    returned_books = BorrowRecord.query.filter_by(
        user_id=current_user.id,
        is_returned=True
    ).order_by(BorrowRecord.return_date.desc()).limit(5).all()
    
    # Calculate statistics
    total_borrowed = BorrowRecord.query.filter_by(user_id=current_user.id).count()
    currently_borrowed = len(borrowed_books)
    overdue_count = sum(1 for record in borrowed_books if record.is_overdue)
    total_fine = sum(record.fine_amount for record in BorrowRecord.query.filter_by(user_id=current_user.id))
    
    # Add current datetime for template calculations
    now = datetime.utcnow()
    
    return render_template(
        'dashboard.html',
        borrowed_books=borrowed_books,
        returned_books=returned_books,
        stats={
            'total_borrowed': total_borrowed,
            'currently_borrowed': currently_borrowed,
            'overdue_count': overdue_count,
            'total_fine': total_fine
        },
        now=now,
        title='Dashboard'
    )

@user_bp.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('user_blueprint.dashboard'))
    
    # Get statistics
    total_books = Book.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_borrows = BorrowRecord.query.count()
    available_books = sum(book.available_copies for book in Book.query.all())
    borrowed_books = sum(book.total_copies - book.available_copies for book in Book.query.all())
    
    # Recent activities (borrows and returns)
    recent_activities = BorrowRecord.query.order_by(
        BorrowRecord.borrow_date.desc()
    ).limit(10).all()
    
    # Overdue books
    overdue_books = BorrowRecord.query.filter(
        BorrowRecord.is_returned == False,
        BorrowRecord.due_date < datetime.utcnow()
    ).order_by(BorrowRecord.due_date).all()
    
    return render_template(
        'admin_dashboard.html',
        stats={
            'total_books': total_books,
            'total_users': total_users,
            'total_borrows': total_borrows,
            'available_books': available_books,
            'borrowed_books': borrowed_books
        },
        recent_activities=recent_activities,
        overdue_books=overdue_books,
        title='Admin Dashboard'
    )

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm()
    
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('user_blueprint.profile'))
    
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
    
    return render_template('user_profile.html', form=form, title='Profile')

@user_bp.route('/borrowed')
@login_required
def borrowed_books():
    # Get all borrow records for current user
    current_borrows = BorrowRecord.query.filter_by(
        user_id=current_user.id,
        is_returned=False
    ).order_by(BorrowRecord.due_date).all()
    
    borrow_history = BorrowRecord.query.filter_by(
        user_id=current_user.id,
        is_returned=True
    ).order_by(BorrowRecord.return_date.desc()).all()
    
    # Add current datetime for template calculations
    now = datetime.utcnow()
    
    return render_template(
        'borrowed_books.html',
        current_borrows=current_borrows,
        borrow_history=borrow_history,
        now=now,
        title='My Books'
    )

@user_bp.route('/admin/users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('user_blueprint.dashboard'))
    
    users = User.query.order_by(User.name).all()
    return render_template('manage_users.html', users=users, title='Manage Users')

@user_bp.route('/admin/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('user_blueprint.dashboard'))
    
    user_to_edit = User.query.get_or_404(user_id)
    form = UserRoleForm()
    
    if form.validate_on_submit():
        user_to_edit.role = form.role.data
        db.session.commit()
        flash(f'Role updated for {user_to_edit.name}', 'success')
        return redirect(url_for('user_blueprint.manage_users'))
    
    elif request.method == 'GET':
        form.role.data = user_to_edit.role
    
    # Get user's borrow history
    borrow_history = BorrowRecord.query.filter_by(user_id=user_id).order_by(BorrowRecord.borrow_date.desc()).all()
    
    return render_template(
        'edit_user.html',
        user=user_to_edit,
        form=form,
        borrow_history=borrow_history,
        title=f'Edit User - {user_to_edit.name}'
    )

@user_bp.route('/admin/reports')
@login_required
def admin_reports():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('user_blueprint.dashboard'))
    
    # Most borrowed books
    most_borrowed_query = db.session.query(
        Book.id, Book.title, Book.author, 
        db.func.count(BorrowRecord.id).label('borrow_count')
    ).join(BorrowRecord).group_by(Book.id).order_by(db.desc('borrow_count')).limit(10)
    
    most_borrowed = most_borrowed_query.all()
    
    # Users with most borrows
    most_active_users_query = db.session.query(
        User.id, User.name, User.email,
        db.func.count(BorrowRecord.id).label('borrow_count')
    ).join(BorrowRecord).group_by(User.id).order_by(db.desc('borrow_count')).limit(10)
    
    most_active_users = most_active_users_query.all()
    
    # Overdue statistics
    overdue_count = BorrowRecord.query.filter(
        BorrowRecord.is_returned == False,
        BorrowRecord.due_date < datetime.utcnow()
    ).count()
    
    total_fines = db.session.query(db.func.sum(BorrowRecord.fine_amount)).scalar() or 0
    
    return render_template(
        'admin_reports.html',
        most_borrowed=most_borrowed,
        most_active_users=most_active_users,
        overdue_count=overdue_count,
        total_fines=total_fines,
        title='Library Reports'
    )