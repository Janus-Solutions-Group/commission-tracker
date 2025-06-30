from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import Project, Employee, ProjectStaff, HoursEntry
from forms import ProjectForm, EmployeeForm, ProjectStaffForm, HoursEntryForm
from utils import get_paginated_query
from sqlalchemy import func, desc

@app.route('/')
def index():
    """Dashboard with overview statistics"""
    # Get summary statistics
    total_projects = Project.query.count()
    total_employees = Employee.query.count()
    
    # Total commission
    total_commission = db.session.query(
        func.sum(HoursEntry.hours_billed * Employee.hourly_rate * Employee.commission_percentage / 100)
    ).join(Employee).scalar() or 0
    
    # Total revenue
    total_revenue = db.session.query(
        func.sum(HoursEntry.hours_billed * Employee.hourly_rate)
    ).join(Employee).scalar() or 0
    
    # Recent hours entries
    recent_entries = HoursEntry.query.order_by(desc(HoursEntry.created_at)).limit(5).all()
    
    # Top performers by commission
    top_performers = db.session.query(
        Employee,
        func.sum(HoursEntry.hours_billed * Employee.hourly_rate * Employee.commission_percentage / 100).label('total_commission')
    ).join(HoursEntry).group_by(Employee.id).order_by(desc('total_commission')).limit(5).all()
    
    return render_template('index.html',
                         total_projects=total_projects,
                         total_employees=total_employees,
                         total_commission=total_commission,
                         total_revenue=total_revenue,
                         recent_entries=recent_entries,
                         top_performers=top_performers)

@app.route('/dashboard')
def dashboard():
    """Detailed dashboard with commission calculations and analytics"""
    # Employee commission summary
    employee_stats = db.session.query(
        Employee,
        func.sum(HoursEntry.hours_worked).label('total_worked'),
        func.sum(HoursEntry.hours_billed).label('total_billed'),
        func.sum(HoursEntry.hours_billed * Employee.hourly_rate * Employee.commission_percentage / 100).label('total_commission'),
        func.sum(HoursEntry.hours_billed * Employee.hourly_rate).label('total_revenue')
    ).outerjoin(HoursEntry).group_by(Employee.id).all()
    
    # Project summary
    project_stats = db.session.query(
        Project,
        func.sum(HoursEntry.hours_worked).label('total_worked'),
        func.sum(HoursEntry.hours_billed).label('total_billed'),
        func.sum(HoursEntry.hours_billed * Employee.hourly_rate).label('total_revenue')
    ).outerjoin(HoursEntry).outerjoin(Employee).group_by(Project.id).all()
    
    return render_template('dashboard.html',
                         employee_stats=employee_stats,
                         project_stats=project_stats)

# Projects routes
@app.route('/projects')
def projects_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    projects = get_paginated_query(Project.query.order_by(Project.name), page, per_page)
    return render_template('projects/list.html', projects=projects)

@app.route('/projects/new', methods=['GET', 'POST'])
def projects_new():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            client=form.client.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data
        )
        db.session.add(project)
        db.session.commit()
        flash('Project created successfully!', 'success')
        return redirect(url_for('projects_list'))
    return render_template('projects/form.html', form=form, title='New Project')

@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
def projects_edit(id):
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects_list'))
    return render_template('projects/form.html', form=form, title='Edit Project', project=project)

@app.route('/projects/<int:id>/delete', methods=['POST'])
def projects_delete(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects_list'))

# Employees routes
@app.route('/employees')
def employees_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    employees = get_paginated_query(Employee.query.order_by(Employee.name), page, per_page)
    return render_template('employees/list.html', employees=employees)

@app.route('/employees/new', methods=['GET', 'POST'])
def employees_new():
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee(
            name=form.name.data,
            role=form.role.data,
            hourly_rate=form.hourly_rate.data,
            commission_percentage=form.commission_percentage.data
        )
        db.session.add(employee)
        db.session.commit()
        flash('Employee created successfully!', 'success')
        return redirect(url_for('employees_list'))
    return render_template('employees/form.html', form=form, title='New Employee')

@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
def employees_edit(id):
    employee = Employee.query.get_or_404(id)
    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        form.populate_obj(employee)
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees_list'))
    return render_template('employees/form.html', form=form, title='Edit Employee', employee=employee)

@app.route('/employees/<int:id>/delete', methods=['POST'])
def employees_delete(id):
    employee = Employee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('employees_list'))

# Project Staff routes
@app.route('/project-staff')
def project_staff_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    project_staff = get_paginated_query(ProjectStaff.query.order_by(ProjectStaff.created_at.desc()), page, per_page)
    return render_template('project_staff/list.html', project_staff=project_staff)

@app.route('/project-staff/new', methods=['GET', 'POST'])
def project_staff_new():
    form = ProjectStaffForm()
    if form.validate_on_submit():
        project_staff = ProjectStaff(
            employee_id=form.employee_id.data,
            project_id=form.project_id.data,
            role_on_project=form.role_on_project.data
        )
        db.session.add(project_staff)
        db.session.commit()
        flash('Employee assigned to project successfully!', 'success')
        return redirect(url_for('project_staff_list'))
    return render_template('project_staff/form.html', form=form, title='Assign Employee to Project')

@app.route('/project-staff/<int:id>/edit', methods=['GET', 'POST'])
def project_staff_edit(id):
    project_staff = ProjectStaff.query.get_or_404(id)
    form = ProjectStaffForm(obj=project_staff)
    if form.validate_on_submit():
        form.populate_obj(project_staff)
        db.session.commit()
        flash('Project assignment updated successfully!', 'success')
        return redirect(url_for('project_staff_list'))
    return render_template('project_staff/form.html', form=form, title='Edit Project Assignment', project_staff=project_staff)

@app.route('/project-staff/<int:id>/delete', methods=['POST'])
def project_staff_delete(id):
    project_staff = ProjectStaff.query.get_or_404(id)
    db.session.delete(project_staff)
    db.session.commit()
    flash('Project assignment removed successfully!', 'success')
    return redirect(url_for('project_staff_list'))

# Hours Entry routes
@app.route('/hours')
def hours_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    hours = get_paginated_query(HoursEntry.query.order_by(HoursEntry.date.desc()), page, per_page)
    return render_template('hours/list.html', hours=hours)

@app.route('/hours/new', methods=['GET', 'POST'])
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
def hours_edit(id):
    hours_entry = HoursEntry.query.get_or_404(id)
    form = HoursEntryForm(obj=hours_entry)
    if form.validate_on_submit():
        form.populate_obj(hours_entry)
        db.session.commit()
        flash('Hours entry updated successfully!', 'success')
        return redirect(url_for('hours_list'))
    return render_template('hours/form.html', form=form, title='Edit Hours Entry', hours_entry=hours_entry)

@app.route('/hours/<int:id>/delete', methods=['POST'])
def hours_delete(id):
    hours_entry = HoursEntry.query.get_or_404(id)
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
