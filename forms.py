from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError
from models import Employee, Project, ProjectStaff
from datetime import date

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(min=2, max=100)])
    client = StringField('Client', validators=[DataRequired(), Length(min=2, max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[])
    
    def validate_end_date(self, field):
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('End date must be after start date.')

class EmployeeForm(FlaskForm):
    name = StringField('Employee Name', validators=[DataRequired(), Length(min=2, max=100)])
    role = StringField('Role', validators=[DataRequired(), Length(min=2, max=50)])
    hourly_rate = FloatField('Hourly Rate ($)', validators=[DataRequired(), NumberRange(min=0.01, max=10000)])
    commission_percentage = FloatField('Commission Percentage (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])

class ProjectStaffForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    role_on_project = StringField('Role on Project', validators=[DataRequired(), Length(min=2, max=50)])
    
    def __init__(self, *args, **kwargs):
        super(ProjectStaffForm, self).__init__(*args, **kwargs)
        self.employee_id.choices = [(e.id, e.name) for e in Employee.query.order_by(Employee.name).all()]
        self.project_id.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        
        # Check if this employee is already assigned to this project
        existing = ProjectStaff.query.filter_by(
            employee_id=self.employee_id.data,
            project_id=self.project_id.data
        ).first()
        
        if existing:
            self.employee_id.errors.append('This employee is already assigned to this project.')
            return False
        
        return True

class HoursEntryForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    hours_worked = FloatField('Hours Worked', validators=[DataRequired(), NumberRange(min=0.01, max=24)])
    hours_billed = FloatField('Hours Billed', validators=[DataRequired(), NumberRange(min=0.01, max=24)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    
    def __init__(self, *args, **kwargs):
        super(HoursEntryForm, self).__init__(*args, **kwargs)
        self.employee_id.choices = [(e.id, e.name) for e in Employee.query.order_by(Employee.name).all()]
        self.project_id.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    def validate_hours_billed(self, field):
        if field.data > self.hours_worked.data:
            raise ValidationError('Hours billed cannot exceed hours worked.')
    
    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        
        # Check if employee is assigned to the project
        assignment = ProjectStaff.query.filter_by(
            employee_id=self.employee_id.data,
            project_id=self.project_id.data
        ).first()
        
        if not assignment:
            self.employee_id.errors.append('This employee is not assigned to the selected project.')
            return False
        
        return True
