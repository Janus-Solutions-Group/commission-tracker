from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, TextAreaField, SelectField, IntegerField, PasswordField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError, Email, EqualTo
from models import Employee, Project, ProjectStaff, User, Company
from datetime import date

class SignupForm(FlaskForm):
    username = StringField('Name', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class LoginForm(FlaskForm):
    username = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(min=2, max=100)])
    project_id = StringField('Project ID', validators=[DataRequired(), Length(min=2, max=100)])
    client = StringField('Client', validators=[DataRequired(), Length(min=2, max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[])
    total_allocated_hours = FloatField('Total Allocated Hours', validators=[DataRequired(), NumberRange(min=0.01, max=10000)])
    
    # def validate_end_date(self, field):
    #     if field.data and self.start_date.data and field.data < self.start_date.data:
    #         raise ValidationError('End date must be after start date.')

class EmployeeForm(FlaskForm):
    name = StringField('Employee Name', validators=[DataRequired(), Length(min=2, max=100)])
    role = StringField('Role', validators=[DataRequired(), Length(min=2, max=50)])
    hourly_rate = FloatField('Hourly Rate ($)', validators=[DataRequired(), NumberRange(min=0.01, max=10000)])

class ProjectStaffForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    # role_on_project = StringField('Role on Project', validators=[DataRequired(), Length(min=2, max=50)])
    commission_percentage = FloatField('Commission Percentage (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    # is_director = BooleanField('Is Project Director')
    
    def __init__(self, *args, **kwargs):
        super(ProjectStaffForm, self).__init__(*args, **kwargs)
        from flask_login import current_user
        if current_user.is_authenticated:
            self.employee_id.choices = [(e.id, e.name) for e in Employee.query.filter_by(company_id=current_user.company_id).order_by(Employee.name).all()]
            self.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(company_id=current_user.company_id).order_by(Project.name).all()]
        else:
            self.employee_id.choices = []
            self.project_id.choices = []
    
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
        from flask_login import current_user
        if current_user.is_authenticated:
            self.employee_id.choices = [(e.id, e.name) for e in Employee.query.filter_by(company_id=current_user.company_id).order_by(Employee.name).all()]
            self.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(company_id=current_user.company_id).order_by(Project.name).all()]
        else:
            self.employee_id.choices = []
            self.project_id.choices = []
    
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
