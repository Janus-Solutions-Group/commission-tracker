from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import app, db
from models import Project, Employee, ProjectStaff, HoursEntry, User, Company
from forms import ProjectForm, EmployeeForm, ProjectStaffForm, HoursEntryForm, SignupForm, LoginForm
from utils import get_paginated_query
from sqlalchemy import func, desc

# Authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        if existing_user:
            flash('Username or email already exists', 'error')
            return render_template('auth/signup.html', form=form)
        
        # Check if company already exists
        company = Company.query.filter_by(name=form.company_name.data).first()
        if not company:
            company = Company(name=form.company_name.data)
            db.session.add(company)
            db.session.flush()  # To get company.id
        
        # Create user
        user = User(
            username=form.username.data,
            email=form.email.data,
            company_id=company.id,
            is_owner=True  # First user of company becomes owner
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.username.data).first()
        print(user)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Detailed dashboard with commission calculations and analytics"""

    # Employee commission summary for current company
    employee_stats = db.session.query(
        Employee,
        func.coalesce(func.sum(HoursEntry.hours_worked), 0).label('total_worked'),
        func.coalesce(func.sum(HoursEntry.hours_billed), 0).label('total_billed'),
        func.coalesce(
            func.sum(HoursEntry.hours_billed * Employee.hourly_rate * ProjectStaff.commission_percentage / 100), 0
        ).label('total_commission'),
        func.coalesce(
            func.sum(HoursEntry.hours_billed * Employee.hourly_rate), 0
        ).label('total_revenue')
    ).join(HoursEntry, HoursEntry.employee_id == Employee.id
    ).join(Project, HoursEntry.project_id == Project.id
    ).join(ProjectStaff, (ProjectStaff.employee_id == Employee.id) & (ProjectStaff.project_id == Project.id)
    ).filter(Employee.company_id == current_user.company_id
    ).group_by(Employee.id).all()

    # Project summary for current company
    project_stats = db.session.query(
        Project,
        func.coalesce(func.sum(HoursEntry.hours_worked), 0).label('total_worked'),
        func.coalesce(func.sum(HoursEntry.hours_billed), 0).label('total_billed'),
        func.coalesce(
            func.sum(HoursEntry.hours_billed * Employee.hourly_rate), 0
        ).label('total_revenue')
    ).join(HoursEntry, HoursEntry.project_id == Project.id
    ).join(Employee, HoursEntry.employee_id == Employee.id
    ).filter(Project.company_id == current_user.company_id
    ).group_by(Project.id).all()
    director_stats = []
    directors = db.session.query(Employee).filter(Employee.role == 'Director').all()

    for director in directors:
        project_ids = db.session.query(ProjectStaff.project_id).filter(ProjectStaff.employee_id == director.id).subquery()

        # Get all associates (excluding director) assigned to those projects
        associate_ids = db.session.query(ProjectStaff.employee_id).filter(
            ProjectStaff.project_id.in_(project_ids)
        ).filter(ProjectStaff.employee_id != director.id).distinct().subquery()

        associates = db.session.query(Employee).filter(Employee.id.in_(associate_ids)).all()

        total_worked = 0
        total_billed = 0
        total_revenue = 0
        total_commission = 0
        for associate in associates:
            # Get all ProjectStaff rows for this associate in the relevant projects
            ps_entries = db.session.query(ProjectStaff).filter(
                ProjectStaff.employee_id == associate.id,
                ProjectStaff.project_id.in_(project_ids)
            ).all()

            for ps in ps_entries:
                # Get total hours worked and billed by the associate on this project
                worked = db.session.query(func.sum(HoursEntry.hours_worked)).filter(
                    HoursEntry.employee_id == associate.id,
                    HoursEntry.project_id == ps.project_id
                ).scalar() or 0

                billed = db.session.query(func.sum(HoursEntry.hours_billed)).filter(
                    HoursEntry.employee_id == associate.id,
                    HoursEntry.project_id == ps.project_id
                ).scalar() or 0

                revenue = billed * (associate.hourly_rate or 0)
                total_worked += worked
                total_billed += billed
                total_revenue += revenue


        director_stats.append({
            'director': director,
            'worked': total_worked,
            'billed': total_billed,
            'commission': total_revenue * 0.02,  # 2% override commission
            'revenue': total_revenue ,
        })

    return render_template('dashboard.html',
                           employee_stats=employee_stats,
                           project_stats=project_stats,
                           director_stats=director_stats)

# Projects routes
@app.route('/projects')
@login_required
def projects_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    projects = get_paginated_query(
        Project.query.filter_by(company_id=current_user.company_id).order_by(Project.name), 
        page, per_page
    )
    return render_template('projects/list.html', projects=projects)

@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def projects_new():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            project_id=form.project_id.data,
            client=form.client.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            total_allocated_hours=form.total_allocated_hours.data,
            company_id=current_user.company_id
        )
        db.session.add(project)
        db.session.commit()
        flash('Project created successfully!', 'success')
        return redirect(url_for('projects_list'))
    return render_template('projects/form.html', form=form, title='New Project')

@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def projects_edit(id):
    project = Project.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects_list'))
    return render_template('projects/form.html', form=form, title='Edit Project', project=project)

@app.route('/projects/<int:id>/delete', methods=['POST'])
@login_required
def projects_delete(id):
    project = Project.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects_list'))

@app.route('/projects/<int:id>')
@login_required
def projects_detail(id):
    project = Project.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    
    # Get all hour entries for this project
    hour_entries = HoursEntry.query.filter_by(project_id=project.id).order_by(
        HoursEntry.date.desc(), HoursEntry.created_at.desc()
    ).all()
    
    return render_template('projects/detail.html', project=project, hour_entries=hour_entries)

# Employees routes
@app.route('/employees')
@login_required
def employees_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    employees = get_paginated_query(
        Employee.query.filter_by(company_id=current_user.company_id).order_by(Employee.name), 
        page, per_page
    )
    return render_template('employees/list.html', employees=employees)

@app.route('/employees/new', methods=['GET', 'POST'])
@login_required
def employees_new():
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee(
            name=form.name.data,
            role=form.role.data,
            hourly_rate=form.hourly_rate.data,
            company_id=current_user.company_id
        )
        db.session.add(employee)
        db.session.commit()
        flash('Employee created successfully!', 'success')
        return redirect(url_for('employees_list'))
    return render_template('employees/form.html', form=form, title='New Employee')

@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def employees_edit(id):
    employee = Employee.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        form.populate_obj(employee)
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees_list'))
    return render_template('employees/form.html', form=form, title='Edit Employee', employee=employee)

@app.route('/employees/<int:id>/delete', methods=['POST'])
@login_required
def employees_delete(id):
    employee = Employee.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    db.session.delete(employee)
    db.session.commit()
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('employees_list'))

# Project Staff routes
@app.route('/project-staff')
@login_required
def project_staff_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    project_staff = get_paginated_query(
        ProjectStaff.query.join(Project).filter(Project.company_id == current_user.company_id).order_by(ProjectStaff.created_at.desc()), 
        page, per_page
    )
    return render_template('project_staff/list.html', project_staff=project_staff)

@app.route('/project-staff/new', methods=['GET', 'POST'])
@login_required
def project_staff_new():
    form = ProjectStaffForm()
    if form.validate_on_submit():# Fetch employee details
        employee = Employee.query.get(form.employee_id.data)

        # Fallbacks in case employee doesn't exist
        role = employee.role if employee else 'Unknown'
        is_director = employee.role.lower() == 'director' if employee else False

        project_staff = ProjectStaff(
            employee_id=form.employee_id.data,
            project_id=form.project_id.data,
            role_on_project=role,
            commission_percentage=form.commission_percentage.data,
            is_director=is_director
        )

        db.session.add(project_staff)
        db.session.commit()
        flash('Employee assigned to project successfully!', 'success')
        return redirect(url_for('project_staff_list'))
    return render_template('project_staff/form.html', form=form, title='Assign Employee to Project')

@app.route('/project-staff/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def project_staff_edit(id):
    project_staff = ProjectStaff.query.join(Project).filter(
        ProjectStaff.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    form = ProjectStaffForm(obj=project_staff)
    if form.validate_on_submit():
        form.populate_obj(project_staff)
        db.session.commit()
        flash('Project assignment updated successfully!', 'success')
        return redirect(url_for('project_staff_list'))
    return render_template('project_staff/form.html', form=form, title='Edit Project Assignment', project_staff=project_staff)

@app.route('/project-staff/<int:id>/delete', methods=['POST'])
@login_required
def project_staff_delete(id):
    project_staff = ProjectStaff.query.join(Project).filter(
        ProjectStaff.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    db.session.delete(project_staff)
    db.session.commit()
    flash('Project assignment removed successfully!', 'success')
    return redirect(url_for('project_staff_list'))

# Hours Entry routes
@app.route('/hours')
@login_required
def hours_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    hours = get_paginated_query(
        HoursEntry.query.join(Project).filter(Project.company_id == current_user.company_id).order_by(HoursEntry.date.desc()), 
        page, per_page
    )
    return render_template('hours/list.html', hours=hours)

@app.route('/hours/new', methods=['GET', 'POST'])
@login_required
def hours_new():
    form = HoursEntryForm()
    if form.validate_on_submit():
        hours_entry = HoursEntry(
            employee_id=form.employee_id.data,
            project_id=form.project_id.data,
            date=form.date.data,
            hours_worked=form.hours_worked.data,
            hours_billed=form.hours_billed.data,
            description=form.description.data
        )
        db.session.add(hours_entry)
        db.session.commit()
        flash('Hours entry created successfully!', 'success')
        return redirect(url_for('hours_list'))
    return render_template('hours/form.html', form=form, title='New Hours Entry')

@app.route('/hours/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def hours_edit(id):
    hours_entry = HoursEntry.query.join(Project).filter(
        HoursEntry.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    form = HoursEntryForm(obj=hours_entry)
    if form.validate_on_submit():
        form.populate_obj(hours_entry)
        db.session.commit()
        flash('Hours entry updated successfully!', 'success')
        return redirect(url_for('hours_list'))
    return render_template('hours/form.html', form=form, title='Edit Hours Entry', hours_entry=hours_entry)

@app.route('/hours/<int:id>/delete', methods=['POST'])
@login_required
def hours_delete(id):
    hours_entry = HoursEntry.query.join(Project).filter(
        HoursEntry.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    db.session.delete(hours_entry)
    db.session.commit()
    flash('Hours entry deleted successfully!', 'success')
    return redirect(url_for('hours_list'))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms-conditions')
def terms_conditions():
    return render_template('terms_conditions.html')
