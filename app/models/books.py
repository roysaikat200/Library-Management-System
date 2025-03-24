from datetime import datetime
from app import db

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    borrowed_records = db.relationship('BorrowRecord', backref='book', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"Book('{self.title}', '{self.author}', '{self.genre}')"

class BorrowRecord(db.Model):
    __tablename__ = 'borrow_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    is_returned = db.Column(db.Boolean, default=False)
    fine_amount = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f"BorrowRecord(User: {self.user_id}, Book: {self.book_id}, Borrowed: {self.borrow_date}, Due: {self.due_date})"
    
    @property
    def is_overdue(self):
        if not self.is_returned and datetime.utcnow() > self.due_date:
            return True
        return False
    
    @property
    def days_overdue(self):
        if self.is_overdue:
            delta = datetime.utcnow() - self.due_date
            return delta.days
        return 0
