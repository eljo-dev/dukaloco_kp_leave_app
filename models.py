from datetime import date, datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    company = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')
    hire_date = db.Column(db.Date, nullable=False, default=date.today)
    carried_over_leave = db.Column(db.Float, default=0.0)
    sick_leave_paid_balance = db.Column(db.Float, default=7.0)
    #sick_leave_unpaid_balance = db.Column(db.Float, default=7.0)
    maternity_leave_balance = db.Column(db.Float, default=90.0)
    paternity_leave_balance = db.Column(db.Float, default=14.0)
    leave_requests = db.relationship('LeaveRequest', backref='applicant', lazy=True)
    work_saturdays = db.Column(db.Boolean, default=False)

    @property
    def current_annual_leave_balance(self):
        """
        Dynamically calculates available annual leave balance:
        - Accrues 1.75 days per full month worked since hire_date (max 21.0 days/year).
        - Includes any carried over leave days.
        - Subtracts total approved Annual leave days taken.
        """
        today = date.today()


        hire = self.hire_date if self.hire_date else today

        months_worked = (today.year - hire.year) * 12 + (today.month - hire.month)
        months_worked = max(0, months_worked)

        carried = self.carried_over_leave if self.carried_over_leave is not None else 0.0

        total_accrued = min(21.0, round(months_worked * 1.75, 2)) + carried

        approved_taken = sum(
            req.total_days for req in self.leave_requests 
            if req.leave_type == 'Annual' and req.status == 'Approved'
        )

        return max(0.0, round(total_accrued - approved_taken, 2))


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)

    status = db.Column(db.String(20), nullable=False, default='Pending')
    applied_on = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    manager_remarks = db.Column(db.String(255), nullable=True)
    medical_certificate = db.Column(db.String(255), nullable=True)