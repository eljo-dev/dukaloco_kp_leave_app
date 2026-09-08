from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    employee_id = db.Column(db.String(50), unique = True, nullable = False)
    full_name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(120), nullable = True)
    password_hash = db.Column(db.String(256), nullable = False)
    company = db.Column(db.String(50), nullable = False)
    role = db.Column(db.String(20), nullable = False, default = 'employee')

    hire_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    annual_leave_balance = db.Column(db.Float, default = 0.0)
    carried_over_leave = db.Column(db.Float, default=0.0)

    sick_leave_balance = db.Column(db.Integer, default = 14)
    maternity_leave_balance = db.Column(db.Integer, default = 90)
    paternity_leave_balance = db.Column(db.Interger, default = 14)

    leave_requests = db.relationship('LeaveRequest', backref = 'applicant', lazy = True)

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)

    leave_type = db.Column(db.String(50), nullable = False)
    start_date = db.Column(db.Date, nullable = False)
    end_date = db.Column(db.Date, nullable = False)
    total_days = db.Column(db.Integer, nullable = False)
    reason = db.Column(db.String(255), nullable = False)

    status = db.Column(db.String(20), nullable = False, default = 'Pending')
    applied_on = db.Column(db.DateTime, default = datetime.utcnow)
    manager_remarks = db.Column(db.String(255), nullable = True)