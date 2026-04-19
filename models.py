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
    extra_hours = db.Column(db.Float, nullable=False, default=0.0)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project_staff = db.relationship('ProjectStaff', backref='project', lazy=True, cascade='all, delete-orphan')
    hours_entries = db.relationship('HoursEntry', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def total_hours_worked(self):
        if '_prefetched_hours_worked' in self.__dict__:
            return self.__dict__['_prefetched_hours_worked']
        return db.session.query(func.sum(HoursEntry.hours_worked)).filter_by(project_id=self.id).scalar() or 0

    @property
    def total_hours_billed(self):
        return db.session.query(func.sum(HoursEntry.hours_billed)).filter_by(project_id=self.id).scalar() or 0

    @property
    def total_revenue(self):
        if '_prefetched_revenue' in self.__dict__:
            return self.__dict__['_prefetched_revenue']
        return db.session.query(
            func.coalesce(func.sum(HoursEntry.revenue), 0)
        ).filter_by(project_id=self.id).scalar() or 0
    
    @property
    def remaining_hours(self):
        return (self.total_allocated_hours + self.extra_hours) - self.total_hours_worked

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False)
    override_percentage = db.Column(db.Float, nullable=False, default=0.0)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project_staff = db.relationship('ProjectStaff', backref='employee', lazy=True, cascade='all, delete-orphan')
    hours_entries = db.relationship('HoursEntry', backref='employee', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Employee {self.name}>'
    
    @property
    def total_commission(self):
        if self.role.lower() == 'associate':
            return db.session.query(
                func.coalesce(func.sum(HoursEntry.commission_earned), 0)
            ).filter_by(employee_id=self.id).scalar() or 0
        records = StaffCommissionRecord.query.filter_by(employee_id=self.id).all()
        return sum(r.direct_commission + r.override_commission for r in records)

    @property
    def total_revenue(self):
        return db.session.query(
            func.coalesce(func.sum(HoursEntry.revenue), 0)
        ).filter_by(employee_id=self.id).scalar() or 0
    
    @property
    def total_hours_worked(self):
        if '_prefetched_hours_worked' in self.__dict__:
            return self.__dict__['_prefetched_hours_worked']
        return db.session.query(func.sum(HoursEntry.hours_worked)).filter_by(employee_id=self.id).scalar() or 0

    @property
    def total_hours_billed(self):
        return db.session.query(func.sum(HoursEntry.hours_billed)).filter_by(employee_id=self.id).scalar() or 0

class ProjectStaff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    commission_percentage = db.Column(db.Float, nullable=False, default=0.0)
    hourly_rate = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('employee_id', 'project_id', 'hourly_rate', name='unique_employee_project_hourly_rate'),)
    

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
        return (total_associate_revenue * self.employee.override_percentage / 100) if self.employee.override_percentage else 0

class HoursEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours_billed = db.Column(db.Float, nullable=False)
    hours_worked = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    # Stored at creation time so rate/commission changes don't retroactively alter history
    revenue = db.Column(db.Float, nullable=True)
    commission_earned = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<HoursEntry {self.id} - {self.date}>'


class StaffCommissionRecord(db.Model):
    """Aggregate commission snapshot for non-associate staff per project.
    Updated whenever any HoursEntry in the project is created, edited, or deleted."""
    __tablename__ = 'staff_commission_record'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    revenue = db.Column(db.Float, nullable=False, default=0.0)
    direct_commission = db.Column(db.Float, nullable=False, default=0.0)
    override_commission = db.Column(db.Float, nullable=False, default=0.0)
    commission_pct = db.Column(db.Float, nullable=False, default=0.0)   # fraction e.g. 0.10 for 10%
    override_pct = db.Column(db.Float, nullable=False, default=0.0)     # fraction e.g. 0.02 for 2%
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', foreign_keys=[employee_id])
    project = db.relationship('Project', foreign_keys=[project_id])

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'project_id', name='uq_staff_commission_emp_proj'),
    )

    def __repr__(self):
        return f'<StaffCommissionRecord emp={self.employee_id} proj={self.project_id}>'