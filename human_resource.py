from app import app, db, User
from werkzeug.security import generate_password_hash

def hr_manager():
    with app.app_context():
        db.create_all()
        manager = User.query.filter_by(role='manager').first()
        if not manager:
            new_manager = User(
                employee_id="MGR-001",
                full_name="Group Manager",
                company="Group",
                role="manager",
                password_hash=generate_password_hash("Admin@123")
            )
            db.session.add(new_manager)
            db.session.commit()
            print("--------------------------------------------------")
            print("Manager account created successfully!")
            print("Employee ID: MGR-001")
            print("Password:    Admin@123")
            print("--------------------------------------------------")
        else:
            print("Manager account already exists in the database.")

if __name__ == "__main__":
    hr_manager()