from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
# Initialize SQLAlchemy (will be configured in app.py)
db = SQLAlchemy()

# User model
'''class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    profile_photo = db.Column(db.String(120))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    date_joined = db.Column(db.Date, default=datetime.utcnow)
    assessments = db.relationship('Assessment', backref='user', lazy=True)'''

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique = True)
    email = db.Column(db.String(50), unique = True)
    password = db.Column(db.String(80))
    courses = db.relationship('Course', backref='user', lazy=True)
    date_joined = db.Column(db.DateTime, default=datetime.now)
    profile_photo = db.Column(db.String(100), nullable=True)  # New column
    total_coins = db.Column(db.Integer, default=0)  # New column for coins
    assessments = db.relationship('Assessment', backref='user', lazy=True)#new

# Assessment model
class Assessment(db.Model):
    __tablename__ = 'assessments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100))
    num_questions = db.Column(db.Integer)
    num_correct = db.Column(db.Integer)
    num_choices = db.Column(db.Integer)
    rank = db.Column(db.String(20), nullable=False, default='Depromoted')
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)