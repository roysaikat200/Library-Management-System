from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    borrowed_records = db.relationship('BorrowRecord', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.name}', '{self.email}', '{self.role}')"
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    def get_current_borrows(self):
        from app.models.books import BorrowRecord
        return BorrowRecord.query.filter_by(user_id=self.id, is_returned=False).all()
    
    def get_borrow_history(self):
        from app.models.books import BorrowRecord
        return BorrowRecord.query.filter_by(user_id=self.id).order_by(BorrowRecord.borrow_date.desc()).all()
    
    def has_overdue_books(self):
        current_borrows = self.get_current_borrows()
        for record in current_borrows:
            if record.is_overdue:
                return True
        return False
