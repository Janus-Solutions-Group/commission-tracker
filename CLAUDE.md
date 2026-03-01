# Commission Tracker

Multi-tenant web app for tracking project profitability, employee hours, and commission calculations. Companies manage projects, assign staff with per-project hourly rates and commission percentages, log hours worked/billed, and generate commission reports.

## Tech Stack

- **Backend**: Python 3.11+ / Flask 3.1.1
- **ORM**: SQLAlchemy 2.0 via Flask-SQLAlchemy (declarative base at `app.py:13`)
- **Database**: PostgreSQL (Supabase-hosted), configured at `app.py:33-47`
- **Auth**: Flask-Login (session-based) + Flask-JWT-Extended
- **Forms**: WTForms / Flask-WTF with server-side validation and CSRF
- **Frontend**: Jinja2 templates + Bootstrap 5 + Feather Icons
- **Deployment**: Zappa (AWS Lambda) via `zappa_settings.json`, also Replit-ready via `.replit`

## Project Structure

```
app.py          — Flask app factory, DB config, login manager, extension init
main.py         — Entry point (runs dev server on :5000)
models.py       — 6 SQLAlchemy models: Company, User, Project, Employee, ProjectStaff, HoursEntry
routes.py       — All 27 route handlers (auth, CRUD, reports, error handlers)
forms.py        — 8 WTForms classes with validation logic
utils.py        — Pagination helper, Jinja2 filters (currency/hours/efficiency), admin email check
seed_data.py    — Demo data seeder for testing
templates/      — Jinja2 templates organized by domain (auth/, projects/, employees/, hours/, project_staff/, components/)
static/         — Logo and background image
```

## Domain Models

Six models in `models.py`, all scoped to a Company (multi-tenant):

| Model | Line | Purpose |
|-------|------|---------|
| Company | `models.py:8` | Tenant isolation — all data belongs to a company |
| User | `models.py:21` | Auth (UserMixin), linked to one company, `is_owner` flag |
| Project | `models.py:39` | Tracks allocated/extra hours, computed properties for revenue/remaining |
| Employee | `models.py:80` | 5 roles (Associate, Director, PM, Analyst, Consultant), hourly rate, override % |
| ProjectStaff | `models.py:120` | Assignment join table with per-project rate and commission %, unique constraint on (employee, project, rate) |
| HoursEntry | `models.py:165` | Time entries with `commission_earned` property containing role-based calculation engine (`models.py:208-243`) |

## Commission Rules

Three-tier calculation in `HoursEntry.commission_earned` (`models.py:208-243`):

1. **Associate**: `hours_worked * hourly_rate * commission_pct`
2. **Director**: Same as Associate + `total_project_revenue * override_percentage`
3. **Other roles** (PM, Analyst, Consultant): `total_associate_revenue_in_project * commission_pct`

Report-level calculation duplicated in `routes.py:152-163` (dashboard) and `routes.py:253-261`.

## Run Commands

```bash
# Development server
python main.py                                          # Flask dev server, port 5000
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app  # Production-like

# Seed demo data
python seed_data.py

# Deploy to AWS Lambda
zappa deploy production
zappa update production
```

## Key Route Groups

All protected routes require `@login_required` and filter by `current_user.company_id`.

| Prefix | Routes File Lines | Purpose |
|--------|-------------------|---------|
| `/signup`, `/login`, `/logout` | `routes.py:11-87` | Auth (session-based) |
| `/` | `routes.py:88-195` | Commission report (homepage) |
| `/dashboard` | `routes.py:198-298` | Employee performance analytics |
| `/projects/*` | `routes.py:302-380` | Project CRUD + detail view |
| `/employees/*` | `routes.py:383-455` | Employee CRUD + JSON rate endpoint |
| `/project-staff/*` | `routes.py:458-535` | Staff assignment CRUD |
| `/hours/*` | `routes.py:539-613` | Hours entry CRUD |

Single JSON API endpoint: `GET /employees/<id>/rate` (`routes.py:451-455`).

## Database

- No migration tool (Alembic) — tables auto-created via `db.create_all()` at `app.py:62`
- Connection pooling: 300s recycle, pre-ping enabled (`app.py:44-47`)
- To add a new model: define in `models.py`, it will be created on next app startup

## Testing

No test framework configured. Manual testing only. Seed data available via `seed_data.py`.

## Additional Documentation

Check these files for deeper context on specific topics:

| File | When to Check |
|------|---------------|
| [Architectural Patterns](.claude/docs/architectural_patterns.md) | Before adding new routes, models, forms, or modifying commission logic |
