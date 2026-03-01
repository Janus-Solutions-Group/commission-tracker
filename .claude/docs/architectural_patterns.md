# Architectural Patterns

Patterns and conventions observed across the codebase. Follow these when making changes.

## 1. Multi-Tenant Data Isolation

Every data model (except User itself) carries a `company_id` foreign key. All queries in routes filter by `current_user.company_id` to enforce tenant boundaries.

**Pattern**: When creating a new entity, always set `company_id=current_user.company_id`.

**Examples**:
- `routes.py:331` — Project creation
- `routes.py:410-411` — Employee creation
- `routes.py:481` — ProjectStaff creation
- `routes.py:567` — HoursEntry creation

**Query filtering**:
- Direct models: `Model.query.filter_by(company_id=current_user.company_id)` — see `routes.py:309`
- Join-filtered: `ProjectStaff.query.join(Project).filter(Project.company_id == ...)` — see `routes.py:465`

## 2. CRUD Route Pattern

Every resource follows the same 4-5 route structure. Routes are registered directly on the `app` object (no Blueprints).

```
GET  /<resource>              — list (paginated)
GET  /<resource>/new          — create form
POST /<resource>/new          — create handler
GET  /<resource>/<id>/edit    — edit form
POST /<resource>/<id>/edit    — edit handler
POST /<resource>/<id>/delete  — delete handler
```

**Convention**:
- List routes use `get_paginated_query()` from `utils.py:3` with 10 items per page
- Create/edit routes use `form.validate_on_submit()` guard
- Edit routes pre-populate forms with `Form(obj=model_instance)` — see `routes.py:346`
- Edit routes apply changes with `form.populate_obj(model_instance)` — see `routes.py:349`
- Delete routes accept only POST
- All mutating routes end with `flash()` + `redirect()`
- Templates live in `templates/<resource>/list.html` and `templates/<resource>/form.html`

**Examples**: Projects (`routes.py:302-380`), Employees (`routes.py:383-449`), Hours (`routes.py:539-613`)

## 3. Form Initialization with Dynamic Choices

Forms with SelectField choices populate options in `__init__` by querying the database, scoped to the current user's company.

**Pattern**: Override `__init__`, call `super().__init__()`, then set `self.<field>.choices`.

**Examples**:
- `forms.py:54-62` — ProjectStaffForm loads employees and projects
- `forms.py:88-104` — HoursEntryForm loads only Associate/Director employees + projects
- `forms.py:132-138` — CommissionReportForm uses a `set_employee_choices()` method instead

## 4. Computed Properties on Models

Business calculations are implemented as `@property` methods on SQLAlchemy models rather than stored columns. These query the database on each access.

**Pattern**: Use `@property` on models for derived values. Query via `db.session.query()` or `Model.query`.

**Examples**:
- `models.py:58-64` — `Project.total_hours_worked`, `total_hours_billed` (aggregate queries)
- `models.py:66-74` — `Project.total_revenue` (iterates entries, joins employee rate)
- `models.py:96-110` — `Employee.total_commission`
- `models.py:179-185` — `HoursEntry.revenue_generated`
- `models.py:187-244` — `HoursEntry.commission_earned` (role-based branching)

**Caveat**: These properties execute queries per access — N+1 risk in loops. The routes work around this by pre-computing aggregates inline (see `routes.py:130-180` for the commission report approach).

## 5. Role-Based Commission Branching

Commission calculations branch on `employee.role.lower()` with three categories:

1. `'associate'` — earns on own hours
2. `'director'` — earns on own hours + override on total project revenue
3. Everything else — earns percentage of total associate revenue in the project

This pattern appears in three places (must be kept in sync):
- `models.py:208-243` — `HoursEntry.commission_earned` property
- `routes.py:152-163` — Commission report (index route)
- `routes.py:253-261` — Dashboard aggregation

The override percentage comes from `Employee.override_percentage` (default 2% for Directors, 0 for others). Set in `routes.py:409` (create) and `routes.py:429-432` (edit).

## 6. Cascading Deletes via Relationships

Parent models define `cascade='all, delete-orphan'` on relationships so deleting a parent removes children automatically.

**Examples**:
- `models.py:52-53` — Deleting a Project cascades to its ProjectStaff and HoursEntry records
- `models.py:90-91` — Deleting an Employee cascades to their ProjectStaff and HoursEntry records

## 7. Jinja2 Template Filter Registration

Custom filters are defined in `utils.py:11-27` and registered via `register_template_filters()` at `app.py:66`.

**Available filters**: `currency`, `hours`, `efficiency`

**Usage in templates**: `{{ amount | currency }}`, `{{ value | hours }}`

To add a new filter: define the function in `utils.py`, add it in `register_template_filters()`.

## 8. Admin Email Domain Allowlist

Admin users are identified by email domain rather than a database role. Hardcoded in `utils.py:35-41`. Admin users are assigned to `company_id=5` (`routes.py:28`).

## 9. Authentication Guard Pattern

All data routes use `@login_required` decorator (Flask-Login). The login manager redirects unauthenticated users to the login page (`app.py:27`).

The user loader at `app.py:52-55` fetches the user by primary key for session restoration.

Open redirect protection on login: `routes.py:70-72` checks `urlparse(next_page).netloc`.

## 10. Error Handling in CRUD

- IntegrityError from unique constraints is caught with try/except + `db.session.rollback()` — see `routes.py:492-495` (ProjectStaff create) and `routes.py:516-519` (ProjectStaff edit)
- 404 errors use `first_or_404()` or `get_or_404()` after company-scoped queries
- 500 handler rolls back the DB session (`routes.py:621-625`)
