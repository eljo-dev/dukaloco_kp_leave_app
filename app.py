from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug. security import generate_password_hash, check_password_hash
from models import db, User, LeaveRequest
from datetime import datetime, timedelta, date
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER =os.path.join(app.root_path, 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

PUBLIC_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day
    "2026-04-03",  # Good Friday
    "2026-04-06",  # Easter Monday
    "2026-05-01",  # Labour Day
    "2026-06-01",  # Madaraka Day
    "2026-10-20",  # Mashujaa Day
    "2026-12-12",  # Jamhuri Day
    "2026-12-25",  # Christmas Day
    "2026-12-26",  # Utamaduni / Boxing Day
}

def calculate_working_days(start_date, end_date, work_saturdays):
    #print(f"--> DEBUG: start={start_date}, end={end_date}, work_saturdays={work_saturdays}")
    current_date = start_date
    working_days = 0

    while current_date <= end_date:
        weekday = current_date.weekday()
        date_str = current_date.strftime("%Y-%m-%d")
        is_holiday = date_str in PUBLIC_HOLIDAYS_2026

        sunday = (weekday == 6)
        saturday_off = (weekday == 5 and not work_saturdays)

        if not sunday and not saturday_off and not is_holiday:
            working_days += 1

        current_date += timedelta(days=1)

    return working_days

app.config['SECRET_KEY'] = 'dukaloco-kp-secret-key-2026'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:5331@localhost:5432/leave_portal_db'
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
        new_employee_id = request.form.get('employee_id', '').strip().upper()
        full_name = request.form.get('full_name').strip()
        company = request.form.get('company').strip()
        password = request.form.get('password').strip()
        role = request.form.get('role', 'employee').strip()

        existing_user = User.query.filter_by(employee_id=new_employee_id).first()
        if existing_user:
            flash('Employee ID already registered. Please log in.', 'warning')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)

        new_user = User(
            employee_id=new_employee_id,
            full_name=full_name,
            company=company,
            password_hash=hashed_password,
            role=role,
            hire_date=date.today()
            )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip().upper()
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
        reason = request.form.get('reason', '').strip()

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format provided.' 'danger')
            return redirect(url_for('apply_leave'))

        if end_date < start_date:
            flash('End date cannot be earlier than start date.' 'danger')
            return redirect(url_for('apply_leave'))

        total_days = calculate_working_days(start_date, end_date, current_user.work_saturdays)

        if total_days == 0:
            flash('Selected date range contains no working days (weekends or public holidays only).', 'warning')
            return redirect(url_for('apply_leave'))

        if leave_type == 'Annual' and total_days > current_user.current_annual_leave_balance:
            flash(f'Insufficient Annual Leave balance. Requested: {total_days} day(s), Available: {current_user.current_annual_leave_balance}.', 'warning')
            return redirect(url_for('apply_leave'))

        elif leave_type == 'Sick' and total_days > current_user.current_sick_leave_paid_balance:
            flash(f'Insufficient Sick Leave balance. Requested: {total_days} day(s), Available: {current_user.sick_leave_paid_balance}.', 'warning')
            return redirect(url_for('apply_leave'))

        elif leave_type == 'Maternity' and total_days > current_user.maternity_leave_balance:
            flash(f'Insufficient Maternity Leave balance. Requested: {total_days} day(s), Available: {current_user.maternity_leave_balance}.', 'warning')
            return redirect(url_for('apply_leave'))

        elif leave_type == 'Paternity' and total_days > current_user.paternity_leave_balance:
            flash(f'Insufficient Paternity Leave balance. Requested: {total_days} day(s), Available: {current_user.paternity_leave_balance}.', 'warning')
            return redirect(url_for('apply_leave'))

        filename=None
        file = request.files.get('sick_sheet')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_request = LeaveRequest(
            user_id=current_user.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            status='Pending',
            medical_certificate=filename
        )

        db.session.add(new_request)
        db.session.commit()

        flash('Leave application submitted successfully! Pending manager review.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('apply_leave.html')

@app.route('/manager_dashboard')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    pending_requests = LeaveRequest.query.filter_by(status='Pending').all()
    processed_requests = LeaveRequest.query.filter(LeaveRequest.status != 'Pending').all()
    
    employees = User.query.filter(User.role !='manager').order_by(User.company, User.full_name).all()

    return render_template(
        'manager_dashboard.html',
        pending_requests=pending_requests,
        processed_requests=processed_requests,
        employees=employees
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

    days = leave_req.total_days
    print("Leave type:", leave_req.leave_type)
    print("Days:", days)

    if leave_req.leave_type == 'Annual':
        if applicant.current_annual_leave_balance >= leave_req.total_days:
            pass
        else:
            flash(f'Cannot approve. {applicant.full_name} only has {applicant.annual_leave_balance} Annual day(s) left.', 'danger')
            return redirect(url_for('manager_dashboard'))

    elif leave_req.leave_type == 'Sick Leave':
        if days > applicant.sick_leave_paid_balance:
            flash(
                f'Cannot approve. {applicant.full_name} only has '
                f'{applicant.sick_leave_paid_balance} Sick day(s) available.',
                'danger'
            )
            return redirect(url_for('manager_dashboard'))
        applicant.sick_leave_paid_balance -= days
        print("Sick balance after deduction:", applicant.sick_leave_paid_balance)

    elif leave_req.leave_type == 'Maternity':
        if applicant.maternity_leave_balance < days:
            flash(f'Cannot approve. {applicant.full_name} only has {applicant.maternity_leave_balance} Maternity day(s) left.', 'danger')
            return redirect(url_for('manager_dashboard'))
        applicant.maternity_leave_balance -= days

    elif leave_req.leave_type == 'Paternity':
        if applicant.paternity_leave_balance < days:
            flash(f'Cannot approve. {applicant.full_name} only has {applicant.paternity_leave_balance} Paternity day(s) left.', 'danger')
            return redirect(url_for('manager_dashboard'))
        applicant.paternity_leave_balance -= days
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

@app.route('/edit_employee/<int:user_id>', methods=['POST'])
@login_required
def edit_employee(user_id):
    if current_user.role != 'manager':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    employee = User.query.get_or_404(user_id)
    hire_date_str = request.form.get('hire_date')
    employee.work_saturdays = 'work_saturdays' in request.form
    db.session.commit()

    if hire_date_str:
        try:
            employee.hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
            
            if 'carried_over_leave' in request.form:
                employee.carried_over_leave = float(request.form.get('carried_over_leave') or 0)

            db.session.commit()
            flash(f"Updated profile for {employee.full_name} successfully.", 'success')
        except ValueError:
            flash('Invalid date or number format provided.', 'danger')

    return redirect(url_for('manager_dashboard'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not check_password_hash(current_user.password_hash, old_password):
        flash('Incorrect current password.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    if new_password != confirm_password:
        flash('New password and confirmation do not match.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    flash('Password updated successfully!', 'success')
    return redirect(request.referrer or url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)