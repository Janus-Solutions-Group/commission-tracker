from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, TextAreaField, SelectField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError, Email, EqualTo, Optional
from models import Employee, Project, ProjectStaff, User, Company
from datetime import date

class SignupForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=4, max=20)])
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
    end_date = DateField('End Date', validators=[Optional()]) 
    total_allocated_hours = FloatField('Total Allocated Hours', validators=[DataRequired(), NumberRange(min=0.01, max=10000)])
    extra_hours = FloatField('Extra Hours', default=0.0, validators=[NumberRange(min=0, max=10000)])
    
    # def validate_end_date(self, field):
    #     if field.data and self.start_date.data and field.data < self.start_date.data:
    #         raise ValidationError('End date must be after start date.')

class EmployeeForm(FlaskForm):
    name = StringField('Employee Name', validators=[DataRequired(), Length(min=2, max=100)])
    role = SelectField(
        "Role",
        choices=[
            ("Associate", "Associate"),
            ("Director", "Director"),
            ("Project Manager", "Project Manager"),
            ("Analyst", "Analyst"),
            ("Consultant", "Consultant")
        ],
        validators=[DataRequired()]
    )
    hourly_rate = FloatField('Hourly Rate ($)', validators=[DataRequired(), NumberRange(min=0.01, max=10000)])
    override_percentage = FloatField('Override Percentage (%)', default=2.0, validators=[NumberRange(min=0, max=100)])

class ProjectStaffForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    commission_percentage = FloatField('Commission Percentage (%)', validators=[NumberRange(min=0, max=100)])
    
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
        
        # # Check if this employee is already assigned to this project
        # existing = ProjectStaff.query.filter_by(
        #     employee_id=self.employee_id.data,
        #     project_id=self.project_id.data
        # ).first()
        
        # if existing:
        #     self.employee_id.errors.append('This employee is already assigned to this project.')
        #     return False
        
        return True

class HoursEntryForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    hours_worked = FloatField('Hours Worked', validators=[Optional(), NumberRange(min=0.01, max=24)])
    hours_billed = FloatField('Hours Billed', validators=[Optional(), NumberRange(min=0.01, max=24)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    
    def __init__(self, *args, **kwargs):
        super(HoursEntryForm, self).__init__(*args, **kwargs)
        from flask_login import current_user
        if current_user.is_authenticated:
            self.employee_id.choices = [
                (e.id, e.name)
                for e in Employee.query
                    .filter_by(company_id=current_user.company_id)
                    .filter(Employee.role.in_(["Associate", "Director"]))
                    .order_by(Employee.name)
                    .all()
            ]

            self.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(company_id=current_user.company_id).order_by(Project.name).all()]
        else:
            self.employee_id.choices = []
            self.project_id.choices = []
    
    # def validate_hours_billed(self, field):
    #     if field.data > self.hours_worked.data:
    #         raise ValidationError('Hours billed cannot exceed hours worked.')
    
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

class CommissionReportForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    date_from = DateField('Date From', validators=[DataRequired()])
    date_to = DateField('Date To', validators=[DataRequired()])
    submit = SubmitField('Generate Report')

    def set_employee_choices(self, company_id):
        from app import db
        self.employee_id.choices = [
            (e.id, e.name) for e in Employee.query.filter(
                Employee.company_id == company_id,
            ).order_by(Employee.name).all()
        ]

class DateRangeForm(FlaskForm):
    date_from = DateField("From", validators=[DataRequired()])
    date_to = DateField("To", validators=[DataRequired()])
    submit = SubmitField("Filter")