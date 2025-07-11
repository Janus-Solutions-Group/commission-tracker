from datetime import datetime
from app import db
from sqlalchemy import func

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    client = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
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
        for entry in self.hours_entries:
            total += entry.hours_billed * entry.employee.hourly_rate
        return total

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False)
    commission_percentage = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project_staff = db.relationship('ProjectStaff', backref='employee', lazy=True, cascade='all, delete-orphan')
    hours_entries = db.relationship('HoursEntry', backref='employee', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Employee {self.name}>'
    
    @property
    def total_commission(self):
        total = 0
        for entry in self.hours_entries:
            total += entry.hours_billed * self.hourly_rate * (self.commission_percentage / 100)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('employee_id', 'project_id', name='unique_employee_project'),)
    
    def __repr__(self):
        return f'<ProjectStaff {self.employee.name} on {self.project.name}>'

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
        return f'<HoursEntry {self.employee.name} - {self.project.name} - {self.date}>'
    
    @property
    def commission_earned(self):
        return self.hours_billed * self.employee.hourly_rate * (self.employee.commission_percentage / 100)
    
    @property
    def revenue_generated(self):
        return self.hours_billed * self.employee.hourly_rate
