from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import app, db
from models import Project, Employee, ProjectStaff, HoursEntry, User, Company
from forms import ProjectForm, EmployeeForm, ProjectStaffForm, HoursEntryForm, SignupForm, LoginForm, CommissionReportForm, DateRangeForm
from utils import get_paginated_query, is_admin_email
from sqlalchemy.orm import joinedload

# Authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        app.logger.info(f"Signup attempt while already logged in as {current_user.email}")
        return redirect(url_for('index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        app.logger.debug("Signup form submitted")
        # Check if username or email already exists
        existing_user = User.query.filter((User.email == form.email.data)).first()
        if existing_user:
            app.logger.warning(f"Signup failed: Email {form.email.data} already exists")
            flash('Username or email already exists', 'error')
            return render_template('auth/signup.html', form=form)
        if is_admin_email(form.email.data):
            app.logger.info(f"Admin signup detected for email: {form.email.data}")
            company_id = 5
            company = Company.query.filter_by(id=company_id).first()
        else: # Check if company already exists
            company = Company.query.filter_by(name=form.company_name.data).first()
            if not company:
                company = Company(name=form.company_name.data)
                db.session.add(company)
                db.session.flush()
                app.logger.info(f"Created new company: {company.name}")
        # Create user
        user = User(
            username=form.name.data,
            email=form.email.data,
            company_id=company.id,
            is_owner=True  # First user of company becomes owner
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        app.logger.info(f"New user registered: {user.email} (Company: {company.name})")
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    app.logger.debug("Rendering signup form")
    return render_template('auth/signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        app.logger.info(f"Login attempt while already logged in as {current_user.email}")
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        app.logger.debug("Login form submitted")
        user = User.query.filter_by(email=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            app.logger.info(f"User logged in: {user.email}")
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)

        app.logger.warning(f"Failed login attempt for email: {form.username.data}")
        flash('Invalid username or password', 'error')
    
    app.logger.debug("Rendering login form")
    return render_template('auth/login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    app.logger.info(f"User logged out: {current_user.email}")
    logout_user()
    return redirect(url_for('login'))
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    app.logger.debug(f"Index page accessed by {current_user.email}")

    form = CommissionReportForm()
    form.set_employee_choices(current_user.company_id)

    report_data = []
    employee = None
    direct_commission = 0.0
    override_commission = 0.0

    if form.validate_on_submit():
        employee_id = form.employee_id.data
        date_from = form.date_from.data
        date_to = form.date_to.data

        app.logger.info(
            f"Commission report requested by {current_user.email} "
            f"for employee_id={employee_id}, date range={date_from} to {date_to}"
        )

        employee = Employee.query.get_or_404(employee_id)

        projects = Project.query.options(
            joinedload(Project.project_staff).joinedload(ProjectStaff.employee)
        ).all()

        all_hours = HoursEntry.query.filter(
            HoursEntry.employee_id == employee_id,
            HoursEntry.date >= date_from,
            HoursEntry.date <= date_to
        ).all()

        app.logger.debug(f"Fetched {len(all_hours)} hours entries for employee_id={employee_id}")

        # Map hours by project
        project_hours_map = {}
        for entry in all_hours:
            project_hours_map.setdefault(entry.project_id, []).append(entry)

        for project in projects:
            hours_entries = project_hours_map.get(project.id, [])
            staff_map = {ps.employee_id: ps for ps in project.project_staff}
            staff = staff_map.get(employee_id)
            if not staff:
                continue

            emp = staff.employee
            hours = sum(e.hours_worked for e in hours_entries)
            revenue = hours * (emp.hourly_rate or 0)
            
            total_project_revenue = sum(
                he.hours_worked * (staff_map.get(he.employee_id).employee.hourly_rate or 0)
                for he in HoursEntry.query.filter(
                    HoursEntry.project_id == project.id,
                    HoursEntry.date >= date_from,
                    HoursEntry.date <= date_to
                )
                if staff_map.get(he.employee_id)
            )

            # Commission calculation
            if emp.role.lower() == 'associate':
                direct_comm = revenue * (staff.commission_percentage or 0) / 100
                override_comm = 0
                note = "Associate: own hours commission"
            elif emp.role.lower() == 'director':
                direct_comm = revenue * (staff.commission_percentage or 0) / 100
                override_comm = (total_project_revenue * employee.override_percentage / 100) if employee.override_percentage else 0
                note = "Director: direct + 2% override"
            else:
                direct_comm = total_project_revenue * (staff.commission_percentage or 0) / 100
                override_comm = 0
                note = "Other: % of associate revenue"

            app.logger.debug(
                f"Project {project.name} — role={emp.role}, hours={hours}, "
                f"revenue={revenue}, direct_comm={direct_comm}, override_comm={override_comm}"
            )

            direct_commission += direct_comm
            override_commission += override_comm
            report_data.append({
                "project_number": project.project_id,
                "project_name": project.name,
                "hours_billed": hours,
                "bill_rate": emp.hourly_rate or 0,
                "direct_commission": direct_comm,
                "override_commission": override_comm,
                "total_commission": direct_comm + override_comm,
            })

    app.logger.info(
        f"Index report generated — direct_commission={direct_commission}, "
        f"override_commission={override_commission}, total={direct_commission + override_commission}"
    )

    return render_template(
        'index.html',
        form=form,
        report_data=report_data,
        employee=employee,
        direct_commission=direct_commission,
        override_commission=override_commission,
        total_commission=direct_commission + override_commission
    )


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    app.logger.debug(f"Dashboard accessed by {current_user.email}")

    form = DateRangeForm()

    date_from = form.date_from.data
    date_to = form.date_to.data
    app.logger.info(f"Dashboard date range filter: {date_from} to {date_to}")

    projects = Project.query.options(
        joinedload(Project.project_staff).joinedload(ProjectStaff.employee)
    ).filter_by(company_id=current_user.company_id)

    query = HoursEntry.query
    if date_from:
        query = query.filter(HoursEntry.date >= date_from)
    if date_to:
        query = query.filter(HoursEntry.date <= date_to)
    all_hours = query.all()

    app.logger.debug(f"Fetched {len(all_hours)} hours entries for dashboard")

    # Map hours by project
    project_hours_map = {}
    for entry in all_hours:
        project_hours_map.setdefault(entry.project_id, []).append(entry)

    employee_summary = {}

    for project in projects:
        hours_entries = project_hours_map.get(project.id, [])
        staff_map = {ps.employee_id: ps for ps in project.project_staff}

        emp_hours = {}
        emp_revenue = {}
        total_project_revenue = 0

        for entry in hours_entries:
            staff = staff_map.get(entry.employee_id)
            if not staff:
                continue

            emp_hours[entry.employee_id] = emp_hours.get(entry.employee_id, 0) + entry.hours_worked
            revenue = entry.hours_worked * (staff.employee.hourly_rate or 0)
            emp_revenue[entry.employee_id] = emp_revenue.get(entry.employee_id, 0) + revenue
            total_project_revenue += revenue

        for emp_id, staff in staff_map.items():
            employee = staff.employee
            hours = emp_hours.get(emp_id, 0)
            revenue = emp_revenue.get(emp_id, 0)
            commission = 0.0

            if employee.role.lower() == 'associate':
                direct_comm = revenue * (staff.commission_percentage or 0) / 100
                override_comm = 0
            elif employee.role.lower() == 'director':
                direct_comm = revenue * (staff.commission_percentage or 0) / 100
                override_comm = (total_project_revenue * employee.override_percentage / 100) if employee.override_percentage else 0
            else:
                direct_comm = total_project_revenue * (staff.commission_percentage or 0) / 100
                override_comm = 0

            commission = direct_comm + override_comm

            if emp_id not in employee_summary:
                employee_summary[emp_id] = {
                    'employee': employee,
                    'total_hours': 0.0,
                    'total_revenue': 0.0,
                    'total_commission': 0.0,
                    'notes': set(),
                    "by_project": [],
                    "by_type": {},
                }

            summary = employee_summary[emp_id]
            summary['total_hours'] += hours
            summary['total_revenue'] += revenue
            summary['total_commission'] += commission
            summary['notes'].add(employee.role)
            summary['by_project'].append({"project": project.name, "hours": hours, "revenue": revenue, "commission": commission})

        app.logger.debug(f"Processed project: {project.name}")

    report_data = []
    for summary in employee_summary.values():
        report_data.append({
            'employee': summary['employee'],
            'total_hours': round(summary['total_hours'], 2),
            'total_revenue': round(summary['total_revenue'], 2),
            'total_commission': round(summary['total_commission'], 2),
            'notes': ", ".join(summary['notes']),
            "by_project": summary['by_project'],
        })

    app.logger.info(f"Dashboard report generated with {len(report_data)} employees summarised")

    return render_template('dashboard.html', form=form, report_data=report_data)


# Projects routes
@app.route('/projects')
@login_required
def projects_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    app.logger.info(f"[Projects List] Fetching projects for company_id={current_user.company_id}, page={page}")
    projects = get_paginated_query(
        Project.query.filter_by(company_id=current_user.company_id).order_by(Project.name), 
        page, per_page
    )
    app.logger.debug(f"[Projects List] Retrieved {len(projects.items)} projects on page {page}")
    return render_template('projects/list.html', projects=projects)


@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def projects_new():
    app.logger.info(f"[Projects New] Request method={request.method}")
    form = ProjectForm()
    if form.validate_on_submit():
        app.logger.debug(f"[Projects New] Creating project '{form.name.data}' for company_id={current_user.company_id}")
        project = Project(
            name=form.name.data,
            project_id=form.project_id.data,
            client=form.client.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            total_allocated_hours=form.total_allocated_hours.data,
            extra_hours=form.extra_hours.data,
            company_id=current_user.company_id
        )
        db.session.add(project)
        db.session.commit()
        app.logger.info(f"[Projects New] Project '{project.name}' created successfully with id={project.id}")
        flash('Project created successfully!', 'success')
        return redirect(url_for('projects_list'))
    return render_template('projects/form.html', form=form, title='New Project')


@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def projects_edit(id):
    app.logger.info(f"[Projects Edit] Editing project id={id} for company_id={current_user.company_id}")
    project = Project.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        app.logger.debug(f"[Projects Edit] Updating project id={project.id}")
        form.populate_obj(project)
        db.session.commit()
        app.logger.info(f"[Projects Edit] Project id={project.id} updated successfully")
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects_list'))
    return render_template('projects/form.html', form=form, title='Edit Project', project=project)


@app.route('/projects/<int:id>/delete', methods=['POST'])
@login_required
def projects_delete(id):
    app.logger.info(f"[Projects Delete] Deleting project id={id} for company_id={current_user.company_id}")
    project = Project.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    db.session.delete(project)
    db.session.commit()
    app.logger.info(f"[Projects Delete] Project id={id} deleted successfully")
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects_list'))


@app.route('/projects/<int:id>')
@login_required
def projects_detail(id):
    app.logger.info(f"[Projects Detail] Fetching details for project id={id} (company_id={current_user.company_id})")
    project = Project.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    
    hour_entries = HoursEntry.query.filter_by(project_id=project.id).order_by(
        HoursEntry.date.desc(), HoursEntry.created_at.desc()
    ).all()
    app.logger.debug(f"[Projects Detail] Retrieved {len(hour_entries)} hour entries for project id={project.id}")
    
    return render_template('projects/detail.html', project=project, hour_entries=hour_entries)

# Employees routes
@app.route('/employees')
@login_required
def employees_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    app.logger.info(f"[Employees List] Fetching employees for company_id={current_user.company_id}, page={page}")
    employees = get_paginated_query(
        Employee.query.filter_by(company_id=current_user.company_id).order_by(Employee.name), 
        page, per_page
    )
    app.logger.debug(f"[Employees List] Retrieved {len(employees.items)} employees on page {page}")
    return render_template('employees/list.html', employees=employees)


@app.route('/employees/new', methods=['GET', 'POST'])
@login_required
def employees_new():
    app.logger.info(f"[Employees New] Request method={request.method}")
    form = EmployeeForm()
    if form.validate_on_submit():
        app.logger.debug(f"[Employees New] Creating employee '{form.name.data}' for company_id={current_user.company_id}")
        print(form.role.data,form.override_percentage.data, form.override_percentage.data if form.role.data == 'Director' else 0.0, "override_percentage")
        employee = Employee(
            name=form.name.data,
            role=form.role.data,
            hourly_rate=form.hourly_rate.data,
            override_percentage=(form.override_percentage.data or 2.0) if form.role.data == 'Director' else 0.0,
            company_id=current_user.company_id
        )
        db.session.add(employee)
        db.session.commit()
        app.logger.info(f"[Employees New] Employee '{employee.name}' created successfully with id={employee.id}")
        flash('Employee created successfully!', 'success')
        return redirect(url_for('employees_list'))
    return render_template('employees/form.html', form=form, title='New Employee')


@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def employees_edit(id):
    app.logger.info(f"[Employees Edit] Editing employee id={id} for company_id={current_user.company_id}")
    employee = Employee.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        app.logger.debug(f"[Employees Edit] Updating employee id={employee.id}")
        form.populate_obj(employee)
        if employee.role == "Director":
            employee.override_percentage = form.override_percentage.data or 2.0
        else:
            employee.override_percentage = 0.0
        db.session.commit()
        app.logger.info(f"[Employees Edit] Employee id={employee.id} updated successfully")
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees_list'))
    return render_template('employees/form.html', form=form, title='Edit Employee', employee=employee)


@app.route('/employees/<int:id>/delete', methods=['POST'])
@login_required
def employees_delete(id):
    app.logger.info(f"[Employees Delete] Deleting employee id={id} for company_id={current_user.company_id}")
    employee = Employee.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    db.session.delete(employee)
    db.session.commit()
    app.logger.info(f"[Employees Delete] Employee id={id} deleted successfully")
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('employees_list'))

# Project Staff routes
@app.route('/project-staff')
@login_required
def project_staff_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    app.logger.info(f"[ProjectStaff List] Fetching for company_id={current_user.company_id}, page={page}")
    project_staff = get_paginated_query(
        ProjectStaff.query.join(Project).filter(Project.company_id == current_user.company_id).order_by(ProjectStaff.created_at.desc()), 
        page, per_page
    )
    app.logger.debug(f"[ProjectStaff List] Retrieved {len(project_staff.items)} assignments on page {page}")
    return render_template('project_staff/list.html', project_staff=project_staff)


@app.route('/project-staff/new', methods=['GET', 'POST'])
@login_required
def project_staff_new():
    app.logger.info(f"[ProjectStaff New] Request method={request.method}")
    form = ProjectStaffForm()
    if form.validate_on_submit():
        app.logger.debug(f"[ProjectStaff New] Assigning employee_id={form.employee_id.data} to project_id={form.project_id.data}")
        project_staff = ProjectStaff(
            company_id=current_user.company_id,
            employee_id=form.employee_id.data,
            project_id=form.project_id.data,
            commission_percentage=form.commission_percentage.data,
        )
        db.session.add(project_staff)
        db.session.commit()
        app.logger.info(f"[ProjectStaff New] Assignment created with id={project_staff.id}")
        flash('Employee assigned to project successfully!', 'success')
        return redirect(url_for('project_staff_list'))
    return render_template('project_staff/form.html', form=form, title='Assign Employee to Project')


@app.route('/project-staff/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def project_staff_edit(id):
    app.logger.info(f"[ProjectStaff Edit] Editing assignment id={id} for company_id={current_user.company_id}")
    project_staff = ProjectStaff.query.join(Project).filter(
        ProjectStaff.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    form = ProjectStaffForm(obj=project_staff)
    if form.validate_on_submit():
        app.logger.debug(f"[ProjectStaff Edit] Updating assignment id={project_staff.id}")
        form.populate_obj(project_staff)
        db.session.commit()
        app.logger.info(f"[ProjectStaff Edit] Assignment id={project_staff.id} updated successfully")
        flash('Project assignment updated successfully!', 'success')
        return redirect(url_for('project_staff_list'))
    return render_template('project_staff/form.html', form=form, title='Edit Project Assignment', project_staff=project_staff)


@app.route('/project-staff/<int:id>/delete', methods=['POST'])
@login_required
def project_staff_delete(id):
    app.logger.info(f"[ProjectStaff Delete] Deleting assignment id={id} for company_id={current_user.company_id}")
    project_staff = ProjectStaff.query.join(Project).filter(
        ProjectStaff.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    db.session.delete(project_staff)
    db.session.commit()
    app.logger.info(f"[ProjectStaff Delete] Assignment id={id} deleted successfully")
    flash('Project assignment removed successfully!', 'success')
    return redirect(url_for('project_staff_list'))


# Hours Entry routes
@app.route('/hours')
@login_required
def hours_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    app.logger.info(f"[Hours List] Fetching hours for company_id={current_user.company_id}, page={page}")
    hours = get_paginated_query(
        HoursEntry.query.join(Project).filter(Project.company_id == current_user.company_id).order_by(HoursEntry.date.desc()), 
        page, per_page
    )
    app.logger.debug(f"[Hours List] Retrieved {len(hours.items)} entries on page {page}")
    return render_template('hours/list.html', hours=hours)


@app.route('/hours/new', methods=['GET', 'POST'])
@login_required
def hours_new():
    app.logger.info(f"[Hours New] Request method={request.method}")
    form = HoursEntryForm()
    if form.validate_on_submit():
        app.logger.debug(f"[Hours New] Adding hours for employee_id={form.employee_id.data} on project_id={form.project_id.data}")
        hours_entry = HoursEntry(
            employee_id=form.employee_id.data,
            project_id=form.project_id.data,
            date=form.date.data,
            hours_worked=form.hours_billed.data,  # same for now
            hours_billed=form.hours_billed.data,
            description=form.description.data,
            company_id=current_user.company_id
        )
        db.session.add(hours_entry)
        db.session.commit()
        app.logger.info(f"[Hours New] Hours entry created with id={hours_entry.id}")
        flash('Hours entry created successfully!', 'success')
        return redirect(url_for('hours_list'))
    return render_template('hours/form.html', form=form, title='New Hours Entry')


@app.route('/hours/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def hours_edit(id):
    app.logger.info(f"[Hours Edit] Editing hours entry id={id} for company_id={current_user.company_id}")
    hours_entry = HoursEntry.query.join(Project).filter(
        HoursEntry.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    form = HoursEntryForm(obj=hours_entry)
    if form.validate_on_submit():
        app.logger.debug(f"[Hours Edit] Updating hours entry id={hours_entry.id}")
        form.populate_obj(hours_entry)
        db.session.commit()
        app.logger.info(f"[Hours Edit] Hours entry id={hours_entry.id} updated successfully")
        flash('Hours entry updated successfully!', 'success')
        return redirect(url_for('hours_list'))
    return render_template('hours/form.html', form=form, title='Edit Hours Entry', hours_entry=hours_entry)


@app.route('/hours/<int:id>/delete', methods=['POST'])
@login_required
def hours_delete(id):
    app.logger.info(f"[Hours Delete] Deleting hours entry id={id} for company_id={current_user.company_id}")
    hours_entry = HoursEntry.query.join(Project).filter(
        HoursEntry.id == id, 
        Project.company_id == current_user.company_id
    ).first_or_404()
    db.session.delete(hours_entry)
    db.session.commit()
    app.logger.info(f"[Hours Delete] Hours entry id={id} deleted successfully")
    flash('Hours entry deleted successfully!', 'success')
    return redirect(url_for('hours_list'))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    app.logger.warning(f"[404 Not Found] URL: {request.path} | Method: {request.method} | Error: {error}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"[500 Internal Error] URL: {request.path} | Method: {request.method} | Error: {error}", exc_info=True)
    db.session.rollback()
    return render_template('500.html'), 500


# Static routes
@app.route('/privacy-policy')
def privacy_policy():
    app.logger.info(f"[Privacy Policy] Page accessed from IP: {request.remote_addr}")
    return render_template('privacy_policy.html')

@app.route('/terms-conditions')
def terms_conditions():
    app.logger.info(f"[Terms & Conditions] Page accessed from IP: {request.remote_addr}")
    return render_template('terms_conditions.html')