from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug. security import generate_password_hash, check_password_hash
from models import db, User, LeaveRequest
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dukaloco-kp-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id').strip()
        full_name = request.form.get('full_name').strip()
        company = request.form.get('company').strip()
        password = request.form.get('password').strip()
        role = request.form.get('role', 'employee').strip()

        existing_user = User.query.filter_by(employee_id=employee_id).first()
        if existing_user:
            flash('Employee ID already registered. Please log in.', 'warning')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)

        new_user = User(
            employee_id=employee_id,
            full_name=full_name,
            company=company,
            password_hash=hashed_password,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id').strip()
        password = request.form.get('password')
        company = request.form.get('company')

        user = User.query.filter_by(employee_id=employee_id, company=company).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Employee ID, Company, or Password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():

    if current_user.role == 'manager':
        return redirect(url_for('manager_dashboard'))

    if current_user.company == 'Dukaloco':
        return render_template('dukaloco_dashboard.html', user=current_user)
    elif current_user.company == 'KP':
        return render_template('kp_dashboard.html', user=current_user)
    else:
        return 'Invalid company association.', 400

@app.route('/apply_leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if request.method == 'POST':
        leave_type = request.form.get('leave_type')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        reason = request.form.get('reason').strip()

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format provided.' 'danger')
            return redirect(url_for('apply_leave'))

        if end_date < start_date:
            flash('End date cannot be earlier than start date.' 'danger')
            return redirect(url_for('apply_leave'))

        total_days = (end_date-start_date).days+1

        if leave_type == 'Annual' and total_days > current_user.annual_leave_balance:
            flash(f'Insufficient Annual Leave Balance. You requested {total_days} days, but only have {current_user.annual_leave_balance} remaining.' 'warning')
            return redirect(url_for('apply_leave'))
        elif leave_type == 'Sick' and total_days > current_user.sick_leave_balance:
            flash(f'Insufficient Sick Leave Balance. You requested {total_days} days, but only have {current_user.sick_leave_balance} remaining.' 'warning')
            return redirect(url_for('apply_leave'))
        elif leave_type == 'Casual' and total_days > current_user.casual_leave_balance:
            flash(f'Insufficient Casual Leave Balance. You requested {total_days} days, but only have {current_user.casual_leave_balance} remaining.' 'warning')
            return redirect(url_for('apply_leave'))

        new_request = LeaveRequest(
            user_id=current_user.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            status='Pending'
        )

        db.session.add(new_request)
        db.session.commit()

        flash('Leave application submitted successfully! Pending manager review.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('apply_leave.html')

@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    pending_requests = LeaveRequest.query.filter_by(status='Pending').all()

    processed_requests = LeaveRequest.query.filter(
        LeaveRequest.status.in_(['Approved', 'Rejected'])
    ).all()

    return render_template(
        'manager_dashboard.html',
        pending_requests=pending_requests,
        processed_requests=processed_requests
    )


@app.route('/approve_leave/<int:request_id>', methods=['POST'])
@login_required
def approve_leave(request_id):
    if current_user.role != 'manager':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('dashboard'))

    leave_req = LeaveRequest.query.get_or_404(request_id)
    applicant = leave_req.applicant

    if leave_req.status != 'Pending':
        flash('This request has already been processed.', 'info')
        return redirect(url_for('manager_dashboard'))

    if leave_req.leave_type == 'Annual':
        if applicant.annual_leave_balance >= leave_req.total_days:
            applicant.annual_leave_balance -= leave_req.total_days
        else:
            flash(f'Cannot approve. {applicant.full_name} only has {applicant.annual_leave_balance} Annual days left.', 'danger')
            return redirect(url_for('manager_dashboard'))

    elif leave_req.leave_type == 'Sick':
        if applicant.sick_leave_balance >= leave_req.total_days:
            applicant.sick_leave_balance -= leave_req.total_days
        else:
            flash(f'Cannot approve. {applicant.full_name} only has {applicant.sick_leave_balance} Sick days left.', 'danger')
            return redirect(url_for('manager_dashboard'))

    elif leave_req.leave_type == 'Casual':
        if applicant.casual_leave_balance >= leave_req.total_days:
            applicant.casual_leave_balance -= leave_req.total_days
        else:
            flash(f'Cannot approve. {applicant.full_name} only has {applicant.casual_leave_balance} Casual days left.', 'danger')
            return redirect(url_for('manager_dashboard'))

    leave_req.status = 'Approved'
    leave_req.manager_remarks = request.form.get('remarks', 'Approved by manager')
    db.session.commit()

    flash(f'Leave request for {applicant.full_name} ({applicant.company}) approved.', 'success')
    return redirect(url_for('manager_dashboard'))


@app.route('/reject_leave/<int:request_id>', methods=['POST'])
@login_required
def reject_leave(request_id):
    if current_user.role != 'manager':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('dashboard'))

    leave_req = LeaveRequest.query.get_or_404(request_id)
    applicant = leave_req.applicant

    if leave_req.status != 'Pending':
            flash('This request has already been processed.', 'info')
            return redirect(url_for('manager_dashboard'))

    leave_req.status = 'Rejected'
    leave_req.manager_remarks = request.form.get('remarks', 'Rejected by manager')
    db.session.commit()

    flash(f'Leave request for {applicant.full_name} ({applicant.company}) rejected.', 'info')
    return redirect(url_for('manager_dashboard'))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(employee_id='MGR-001').first():
            group_mgr = User(
                employee_id='MGR-001',
                full_name='Group Manager',
                company='Group',
                password_hash=generate_password_hash('admin123'),
                role='manager'
            )
            db.session.add(group_mgr)
            db.session.commit()

    app.run(debug=True)