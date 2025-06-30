from datetime import date, timedelta
from app import app, db
from models import Project, Employee, ProjectStaff, HoursEntry
import random

def create_seed_data():
    """Create sample data for testing the application"""
    with app.app_context():
        # Clear existing data
        HoursEntry.query.delete()
        ProjectStaff.query.delete()
        Project.query.delete()
        Employee.query.delete()
        
        # Create employees
        employees = [
            Employee(name="John Smith", role="Senior Developer", hourly_rate=85.0, commission_percentage=10.0),
            Employee(name="Sarah Johnson", role="Project Manager", hourly_rate=75.0, commission_percentage=12.0),
            Employee(name="Mike Chen", role="UI/UX Designer", hourly_rate=65.0, commission_percentage=8.0),
            Employee(name="Emily Davis", role="Frontend Developer", hourly_rate=70.0, commission_percentage=9.0),
            Employee(name="David Wilson", role="Backend Developer", hourly_rate=80.0, commission_percentage=10.0),
            Employee(name="Lisa Brown", role="QA Engineer", hourly_rate=55.0, commission_percentage=7.0),
        ]
        
        for employee in employees:
            db.session.add(employee)
        
        # Create projects
        projects = [
            Project(name="E-commerce Platform", client="TechCorp Inc.", 
                   start_date=date(2024, 1, 15), end_date=date(2024, 6, 30)),
            Project(name="Mobile Banking App", client="SecureBank", 
                   start_date=date(2024, 3, 1), end_date=date(2024, 8, 15)),
            Project(name="Inventory Management System", client="RetailMax", 
                   start_date=date(2024, 2, 10), end_date=date(2024, 5, 20)),
            Project(name="Customer Portal", client="ServicePlus", 
                   start_date=date(2024, 4, 1), end_date=None),
            Project(name="Data Analytics Dashboard", client="DataInsights", 
                   start_date=date(2024, 5, 15), end_date=None),
        ]
        
        for project in projects:
            db.session.add(project)
        
        db.session.commit()
        
        # Assign employees to projects
        project_assignments = [
            # E-commerce Platform
            ProjectStaff(employee_id=1, project_id=1, role_on_project="Lead Developer"),
            ProjectStaff(employee_id=2, project_id=1, role_on_project="Project Manager"),
            ProjectStaff(employee_id=3, project_id=1, role_on_project="UI Designer"),
            ProjectStaff(employee_id=4, project_id=1, role_on_project="Frontend Developer"),
            
            # Mobile Banking App
            ProjectStaff(employee_id=5, project_id=2, role_on_project="Backend Developer"),
            ProjectStaff(employee_id=2, project_id=2, role_on_project="Project Manager"),
            ProjectStaff(employee_id=6, project_id=2, role_on_project="QA Engineer"),
            
            # Inventory Management
            ProjectStaff(employee_id=1, project_id=3, role_on_project="Senior Developer"),
            ProjectStaff(employee_id=5, project_id=3, role_on_project="Backend Developer"),
            ProjectStaff(employee_id=6, project_id=3, role_on_project="QA Engineer"),
            
            # Customer Portal
            ProjectStaff(employee_id=4, project_id=4, role_on_project="Frontend Lead"),
            ProjectStaff(employee_id=3, project_id=4, role_on_project="UI/UX Designer"),
            
            # Data Analytics Dashboard
            ProjectStaff(employee_id=1, project_id=5, role_on_project="Full Stack Developer"),
            ProjectStaff(employee_id=5, project_id=5, role_on_project="Data Engineer"),
        ]
        
        for assignment in project_assignments:
            db.session.add(assignment)
        
        db.session.commit()
        
        # Create hours entries
        start_date = date(2024, 1, 15)
        end_date = date(2024, 6, 30)
        current_date = start_date
        
        # Get all project staff assignments
        assignments = ProjectStaff.query.all()
        
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
                for assignment in assignments:
                    # Random chance of working on this day
                    if random.random() < 0.7:  # 70% chance of working
                        hours_worked = random.uniform(4, 9)  # 4-9 hours worked
                        hours_billed = hours_worked * random.uniform(0.8, 1.0)  # 80-100% billing efficiency
                        
                        hours_entry = HoursEntry(
                            employee_id=assignment.employee_id,
                            project_id=assignment.project_id,
                            date=current_date,
                            hours_worked=round(hours_worked, 2),
                            hours_billed=round(hours_billed, 2),
                            description=f"Work on {assignment.project.name} as {assignment.role_on_project}"
                        )
                        db.session.add(hours_entry)
            
            current_date += timedelta(days=1)
        
        db.session.commit()
        print("Seed data created successfully!")

if __name__ == "__main__":
    create_seed_data()
