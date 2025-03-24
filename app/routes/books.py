from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from app import db
from app.models.books import Book, BorrowRecord
from app.forms import BookForm, SearchForm
from app.utils import send_due_notification

books_bp = Blueprint('books_blueprint', __name__, url_prefix='/books')

@books_bp.route('/books', methods=['GET'])
def book_list():
    form = SearchForm()
    query = Book.query
    
    search_term = request.args.get('search', '')
    genre_filter = request.args.get('genre', '')
    
    if search_term:
        query = query.filter(
            (Book.title.ilike(f'%{search_term}%')) | 
            (Book.author.ilike(f'%{search_term}%'))
        )
    
    if genre_filter:
        query = query.filter_by(genre=genre_filter)
    
    # Get all unique genres for filter dropdown
    genres = [g[0] for g in db.session.query(Book.genre).distinct()]
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    books_pagination = query.order_by(Book.title).paginate(page=page, per_page=per_page)
    
    return render_template(
        'book_list.html', 
        books=books_pagination.items,
        pagination=books_pagination,
        form=form,
        search_term=search_term,
        genre_filter=genre_filter,
        genres=genres,
        title='Book Catalog'
    )

@books_bp.route('/books/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('book_detail.html', book=book, title=book.title)

@books_bp.route('/books/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('books_blueprint.book_list'))
    
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            genre=form.genre.data,
            description=form.description.data,
            total_copies=form.total_copies.data,
            available_copies=form.total_copies.data
        )
        
        db.session.add(book)
        db.session.commit()
        flash('Book has been added successfully!', 'success')
        return redirect(url_for('books_blueprint.book_list'))
    
    return render_template('add_book.html', form=form, title='Add Book')

@books_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('books_blueprint.book_list'))
    
    book = Book.query.get_or_404(book_id)
    form = BookForm()
    
    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data
        book.genre = form.genre.data
        book.description = form.description.data
        
        # Handle copy count changes intelligently
        new_total = form.total_copies.data
        borrowed_count = book.total_copies - book.available_copies
        
        if new_total < borrowed_count:
            flash('Cannot reduce total copies below currently borrowed amount.', 'danger')
        else:
            book.total_copies = new_total
            book.available_copies = new_total - borrowed_count
            db.session.commit()
            flash('Book has been updated successfully!', 'success')
            return redirect(url_for('books_blueprint.book_list'))
    
    elif request.method == 'GET':
        form.title.data = book.title
        form.author.data = book.author
        form.genre.data = book.genre
        form.description.data = book.description
        form.total_copies.data = book.total_copies
    
    return render_template('edit_book.html', form=form, book=book, title='Edit Book')

@books_bp.route('/books/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('books_blueprint.book_list'))
    
    book = Book.query.get_or_404(book_id)
    
    # Check if any copies are currently borrowed
    if book.available_copies < book.total_copies:
        flash('This book cannot be deleted as some copies are currently borrowed.', 'danger')
        return redirect(url_for('books_blueprint.book_list'))
    
    db.session.delete(book)
    db.session.commit()
    flash('Book has been deleted successfully!', 'success')
    return redirect(url_for('books_blueprint.book_list'))

@books_bp.route('/books/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if user already has this book
    existing_borrow = BorrowRecord.query.filter_by(
        user_id=current_user.id,
        book_id=book.id,
        is_returned=False
    ).first()
    
    if existing_borrow:
        flash('You already have this book borrowed.', 'warning')
        return redirect(url_for('books_blueprint.book_list'))
    
    # Check if the book is available
    if book.available_copies <= 0:
        flash('Sorry, this book is currently not available.', 'warning')
        return redirect(url_for('books.book_list'))
    
    # Create a new borrow record
    due_date = datetime.utcnow() + timedelta(days=14)  # 2 weeks loan period
    borrow_record = BorrowRecord(
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=datetime.utcnow(),
        due_date=due_date
    )
    
    # Update book availability
    book.available_copies -= 1
    
    db.session.add(borrow_record)
    db.session.commit()
    
    flash(f'You have successfully borrowed "{book.title}". It is due on {due_date.strftime("%Y-%m-%d")}', 'success')
    return redirect(url_for('user_blueprint.borrowed_books'))

@books_bp.route('/books/return/<int:borrow_id>', methods=['POST'])
@login_required
def return_book(borrow_id):
    borrow_record = BorrowRecord.query.get_or_404(borrow_id)
    
    # Ensure the user owns this borrow record
    if borrow_record.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Make sure it's not already returned
    if borrow_record.is_returned:
        flash('This book has already been returned.', 'warning')
        return redirect(url_for('user_blueprint.borrowed_books'))
    
    # Update the borrow record
    borrow_record.is_returned = True
    borrow_record.return_date = datetime.utcnow()
    
    # Calculate fine if overdue
    if borrow_record.is_overdue:
        # $0.50 per day overdue
        fine_rate = 0.50
        fine = borrow_record.days_overdue * fine_rate
        borrow_record.fine_amount = fine
        
        if fine > 0:
            flash(f'This book was returned {borrow_record.days_overdue} days late. A fine of ${fine:.2f} has been applied.', 'warning')
    
    # Update book availability
    book = Book.query.get(borrow_record.book_id)
    book.available_copies += 1
    
    db.session.commit()
    
    flash(f'You have successfully returned "{book.title}".', 'success')
    return redirect(url_for('user_blueprint.borrowed_books'))

@books_bp.route('/books/renew/<int:borrow_id>', methods=['POST'])
@login_required
def renew_book(borrow_id):
    borrow_record = BorrowRecord.query.get_or_404(borrow_id)
    
    # Ensure the user owns this borrow record
    if borrow_record.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Make sure it's not already returned
    if borrow_record.is_returned:
        flash('Cannot renew a book that has already been returned.', 'warning')
        return redirect(url_for('user_blueprint.borrowed_books'))
    
    # Check if it's overdue
    if borrow_record.is_overdue:
        flash('Overdue books cannot be renewed. Please return this book first.', 'warning')
        return redirect(url_for('user_blueprint.borrowed_books'))
    
    # Extend due date by 7 days
    borrow_record.due_date = borrow_record.due_date + timedelta(days=7)
    db.session.commit()
    
    flash(f'Due date extended to {borrow_record.due_date.strftime("%Y-%m-%d")}', 'success')
    return redirect(url_for('user_blueprint.borrowed_books'))
