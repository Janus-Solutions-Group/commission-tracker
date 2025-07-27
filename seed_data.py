from datetime import date, timedelta, datetime
from app import app, db
from models import Project, Employee, ProjectStaff, HoursEntry, Company
import random

def seed_commission_data():
    # Step 1: Create a company
    company = Company.query.get(1)
    # Step 2: Create a project
    project = Project(
        name="Alpha Project",
        client="BigClient Inc.",
        start_date=date(2025, 7, 1),
        end_date=None,
        total_allocated_hours=50,
        company_id=1
    )
    db.session.add(project)
    db.session.commit()

    # Step 3: Define employees
    employees_data = [
        {"name": "Christie Owens",       "role": "Associate",       "rate": 1000, "commission": 15, "hours": 10, 'company_id': 1},
        {"name": "Jacqueline Dinwiddie", "role": "Director",        "rate": 1500, "commission": 30, "hours": 2, 'company_id': 1},
        {"name": "John Doe",             "role": "Project Manager", "rate": 2000, "commission": 10, "hours": 0, 'company_id': 1},
        {"name": "Steve Smith",          "role": "Analyst",         "rate": 900,  "commission": 5,  "hours": 0, 'company_id': 1},
        {"name": "Crystal",              "role": "Consultant",      "rate": 800,  "commission": 10, "hours": 0, 'company_id': 1},
    ]

    employees = []

    # Step 4: Create Employee, ProjectStaff, and HoursEntry
    for emp_data in employees_data:
        emp = Employee(
            name=emp_data["name"],
            role=emp_data["role"],
            hourly_rate=emp_data["rate"],
            company_id=1
        )
        db.session.add(emp)
        db.session.flush()  # So we get emp.id

        # Assign to project
        staff = ProjectStaff(
            employee_id=emp.id,
            project_id=project.id,
            commission_percentage=emp_data["commission"],
            company_id=1
        )
        db.session.add(staff)

        # Log hours if > 0
        if emp_data["hours"] > 0:
            entry = HoursEntry(
                employee_id=emp.id,
                project_id=project.id,
                hours_worked=emp_data["hours"],
                hours_billed=emp_data["hours"],
                date=datetime.utcnow(),
                company_id=1
            )
            db.session.add(entry)

        employees.append(emp)

    db.session.commit()
    print("Seed data inserted successfully.")

if __name__ == "__main__":
  with app.app_context():
        seed_commission_data()