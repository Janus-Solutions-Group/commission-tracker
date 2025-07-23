from datetime import datetime
from app import db
from sqlalchemy import func
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='company', lazy=True)
    projects = db.relationship('Project', backref='company', lazy=True)
    employees = db.relationship('Employee', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    is_owner = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    client = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    total_allocated_hours = db.Column(db.Float, nullable=False, default=0.0)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project_staff = db.relationship('ProjectStaff', backref='project', lazy=True, cascade='all, delete-orphan')
    hours_entries = db.relationship('HoursEntry', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def total_hours_worked(self):
        return db.session.query(func.sum(HoursEntry.hours_worked)).filter_by(project_id=self.id).scalar() or 0
    
    @property
    def total_hours_billed(self):
        return db.session.query(func.sum(HoursEntry.hours_billed)).filter_by(project_id=self.id).scalar() or 0
    
    @property
    def total_revenue(self):
        total = 0
        entries = HoursEntry.query.filter_by(project_id=self.id).all()
        for entry in entries:
            employee = Employee.query.get(entry.employee_id)
            if employee:
                total += entry.hours_billed * employee.hourly_rate
        return total
    
    @property
    def remaining_hours(self):
        return self.total_allocated_hours - self.total_hours_worked

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project_staff = db.relationship('ProjectStaff', backref='employee', lazy=True, cascade='all, delete-orphan')
    hours_entries = db.relationship('HoursEntry', backref='employee', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Employee {self.name}>'
    
    @property
    def total_commission(self):
        from sqlalchemy.orm import joinedload
        total = 0
        entries = db.session.query(HoursEntry).filter_by(employee_id=self.id).all()
        for entry in entries:
            # Get commission percentage from project assignment
            project_staff = ProjectStaff.query.filter_by(
                employee_id=self.id, 
                project_id=entry.project_id
            ).first()
            if project_staff:
                commission_rate = project_staff.commission_percentage / 100
                total += entry.hours_billed * self.hourly_rate * commission_rate
        return total
    
    @property
    def total_hours_worked(self):
        return db.session.query(func.sum(HoursEntry.hours_worked)).filter_by(employee_id=self.id).scalar() or 0
    
    @property
    def total_hours_billed(self):
        return db.session.query(func.sum(HoursEntry.hours_billed)).filter_by(employee_id=self.id).scalar() or 0

class ProjectStaff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    role_on_project = db.Column(db.String(50), nullable=False)
    commission_percentage = db.Column(db.Float, nullable=False, default=0.0)
    is_director = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('employee_id', 'project_id', name='unique_employee_project'),)
    
    def __repr__(self):
        return f'<ProjectStaff {self.id}>'
    
    @property
    def override_commission(self):
        """Calculate 2% override commission for directors based on associate revenue"""
        if not self.is_director:
            return 0.0
        
        # Get all associates (non-directors) in this project
        associate_staff = ProjectStaff.query.filter_by(
            project_id=self.project_id, 
            is_director=False
        ).all()
        
        total_associate_revenue = 0
        for associate in associate_staff:
            # Get hours entries for this associate on this project
            entries = HoursEntry.query.filter_by(
                employee_id=associate.employee_id,
                project_id=self.project_id
            ).all()
            
            for entry in entries:
                employee = Employee.query.get(associate.employee_id)
                if employee:
                    revenue = entry.hours_billed * employee.hourly_rate
                    total_associate_revenue += revenue
        
        # Director gets 2% override on associate revenue
        return total_associate_revenue * 0.02

class HoursEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours_billed = db.Column(db.Float, nullable=False)
    hours_worked = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<HoursEntry {self.id} - {self.date}>'
    
    @property
    def commission_earned(self):
        # Get commission percentage from project assignment
        project_staff = ProjectStaff.query.filter_by(
            employee_id=self.employee_id, 
            project_id=self.project_id
        ).first()
        
        if not project_staff:
            return 0.0
            
        commission_rate = project_staff.commission_percentage / 100
        # Get employee hourly rate
        employee = Employee.query.get(self.employee_id)
        if not employee:
            return 0.0
            
        base_commission = self.hours_billed * employee.hourly_rate * commission_rate
        
        # Add override commission if this employee is a director
        override_commission = project_staff.override_commission if project_staff.is_director else 0.0
        
        return base_commission + override_commission
    
    @property
    def revenue_generated(self):
        employee = Employee.query.get(self.employee_id)
        if not employee:
            return 0.0
        return self.hours_billed * employee.hourly_rate
