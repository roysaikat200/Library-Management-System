from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField, SelectField, EmailField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
from app.models.user import User

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class SignupForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    accept_tos = BooleanField('I accept the Terms of Service', validators=[
        DataRequired(message='You must accept the Terms of Service to register')
    ])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please log in or use a different email.')

class ResetPasswordRequestForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=100)])
    author = StringField('Author', validators=[DataRequired(), Length(min=1, max=100)])
    genre = StringField('Genre', validators=[DataRequired(), Length(min=1, max=50)])
    description = TextAreaField('Description')
    total_copies = IntegerField('Total Copies', validators=[
        DataRequired(),
        NumberRange(min=1, message='Must have at least 1 copy')
    ])
    submit = SubmitField('Save Book')

class SearchForm(FlaskForm):
    search = StringField('Search')
    genre = SelectField('Genre', choices=[('', 'All Genres')], validate_choice=False)
    submit = SubmitField('Search')

class ProfileUpdateForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Update Profile')

    def __init__(self, original_email=None, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already in use. Please use a different email.')

class UserRoleForm(FlaskForm):
    role = SelectField('Role', choices=[('user', 'Regular User'), ('admin', 'Administrator')], validators=[DataRequired()])
    submit = SubmitField('Update Role')
