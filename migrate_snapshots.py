"""
migrate_snapshots.py — Run once to add revenue and commission_earned columns
to hours_entry and backfill from current data.

Usage:
    DATABASE_URL=<url> python migrate_snapshots.py
"""
import os
import psycopg2

DATABASE_URL = "postgresql://postgres.wfpbsrcskmklqiibxyvg:26GLyzU6v%40CSAiK@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
if not DATABASE_URL:
    raise SystemExit("ERROR: DATABASE_URL environment variable is required.")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Step 1: Add columns (idempotent)
for stmt in [
    "ALTER TABLE hours_entry ADD COLUMN IF NOT EXISTS revenue FLOAT",
    "ALTER TABLE hours_entry ADD COLUMN IF NOT EXISTS commission_earned FLOAT",
]:
    cur.execute(stmt)
    print(f"Executed: {stmt}")
conn.commit()
print("Columns added.")

# Step 2: Backfill revenue = hours_billed * employee.hourly_rate
cur.execute("""
    UPDATE hours_entry he
    SET revenue = he.hours_billed * e.hourly_rate
    FROM employee e
    WHERE he.employee_id = e.id
      AND he.revenue IS NULL
""")
print(f"Backfilled revenue for {cur.rowcount} rows.")
conn.commit()

# Step 3: Backfill commission_earned using role-based rules in Python
# We need Python here because commission rules involve aggregates and role logic.
cur.execute("""
    SELECT he.id, he.employee_id, he.project_id, he.hours_worked, he.revenue,
           e.role, e.override_percentage,
           ps.commission_percentage
    FROM hours_entry he
    JOIN employee e ON he.employee_id = e.id
    JOIN project_staff ps ON ps.employee_id = he.employee_id AND ps.project_id = he.project_id
    WHERE he.commission_earned IS NULL
    ORDER BY he.project_id, he.id
""")
entries = cur.fetchall()
print(f"Computing commission for {len(entries)} entries...")

# Build per-project revenue maps for aggregate calculations
cur.execute("SELECT project_id, employee_id, SUM(revenue) FROM hours_entry WHERE revenue IS NOT NULL GROUP BY project_id, employee_id")
project_emp_revenue = {}
for proj_id, emp_id, rev in cur.fetchall():
    project_emp_revenue.setdefault(proj_id, {})[emp_id] = float(rev or 0)

# Build associate employee id sets per project
cur.execute("""
    SELECT ps.project_id, ps.employee_id
    FROM project_staff ps
    JOIN employee e ON ps.employee_id = e.id
    WHERE LOWER(e.role) = 'associate'
""")
project_assoc_ids = {}
for proj_id, emp_id in cur.fetchall():
    project_assoc_ids.setdefault(proj_id, set()).add(emp_id)

updates = []
for row in entries:
    entry_id, emp_id, proj_id, hours_worked, revenue, role, override_pct, commission_pct_raw = row
    revenue = float(revenue or 0)
    commission_pct = (float(commission_pct_raw or 0)) / 100
    override_pct = float(override_pct or 0)
    role = (role or '').lower()

    if role == 'associate':
        commission = hours_worked * (revenue / max(1, hours_worked) if hours_worked else 0) * commission_pct
        # Simpler: commission = revenue * commission_pct (since revenue = hours_billed * rate, same as hours_worked * rate for this app)
        commission = revenue * commission_pct

    elif role == 'director':
        total_project_revenue = sum(project_emp_revenue.get(proj_id, {}).values())
        direct = revenue * commission_pct
        override = total_project_revenue * override_pct / 100
        commission = direct + override

    else:
        assoc_ids = project_assoc_ids.get(proj_id, set())
        total_assoc_revenue = sum(
            v for eid, v in project_emp_revenue.get(proj_id, {}).items()
            if eid in assoc_ids
        )
        commission = total_assoc_revenue * commission_pct

    updates.append((commission, entry_id))

if updates:
    cur.executemany("UPDATE hours_entry SET commission_earned = %s WHERE id = %s", updates)
    print(f"Backfilled commission_earned for {cur.rowcount} rows.")
    conn.commit()

# Step 4: Report any remaining nulls
cur.execute("SELECT COUNT(*) FROM hours_entry WHERE revenue IS NULL OR commission_earned IS NULL")
remaining = cur.fetchone()[0]
if remaining:
    print(f"WARNING: {remaining} rows still have NULL values (likely no matching ProjectStaff).")
else:
    print("All rows backfilled successfully.")

cur.close()
conn.close()
