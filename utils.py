from flask import request, url_for

def get_paginated_query(query, page, per_page=10):
    """Helper function to paginate queries"""
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}"

def format_hours(hours):
    """Format hours with proper decimal places"""
    if hours is None:
        return "0.00"
    return f"{hours:.2f}"

def calculate_efficiency(hours_billed, hours_worked):
    """Calculate billing efficiency percentage"""
    if not hours_worked or hours_worked == 0:
        return 0
    return (hours_billed / hours_worked) * 100

# Template filters
def register_template_filters(app):
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['hours'] = format_hours
    app.jinja_env.filters['efficiency'] = calculate_efficiency

def is_admin_email(email):
    allowed_domains = [
        "@corpbizadvisors.com",
        "@biz-solve.com",
        "@blujaxaccountants.com"
    ]
    return any(email.lower().endswith(domain) for domain in allowed_domains)
