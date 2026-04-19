"""
migrate_staff_commission.py — Run once to create the staff_commission_record table
and backfill historical commission values for all non-associate staff.

For each non-associate employee assigned to a project, commission is computed
from the stored HoursEntry.revenue values already in the DB:
  - Director:  direct = own_revenue * commission_pct
               override = total_project_revenue * override_pct / 100
  - Other:     direct = total_associate_revenue * commission_pct
               override = 0

Safe to re-run: table creation and inserts are idempotent.

Usage:
    python migrate_staff_commission.py
"""
import psycopg2
from datetime import datetime

DATABASE_URL = "postgresql://postgres.wfpbsrcskmklqiibxyvg:26GLyzU6v%40CSAiK@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Step 1: Create table (idempotent)
cur.execute("""
    CREATE TABLE IF NOT EXISTS staff_commission_record (
        id                SERIAL PRIMARY KEY,
        employee_id       INTEGER NOT NULL REFERENCES employee(id),
        project_id        INTEGER NOT NULL REFERENCES project(id),
        company_id        INTEGER NOT NULL REFERENCES company(id),
        revenue           FLOAT NOT NULL DEFAULT 0.0,
        direct_commission FLOAT NOT NULL DEFAULT 0.0,
        override_commission FLOAT NOT NULL DEFAULT 0.0,
        updated_at        TIMESTAMP DEFAULT NOW(),
        CONSTRAINT uq_staff_commission_emp_proj UNIQUE (employee_id, project_id)
    )
""")
conn.commit()
print("Table staff_commission_record created (or already existed).")

# Step 2: Load per-project revenue aggregates from stored HoursEntry values
cur.execute("""
    SELECT project_id, employee_id, COALESCE(SUM(revenue), 0)
    FROM hours_entry
    WHERE revenue IS NOT NULL
    GROUP BY project_id, employee_id
""")
# project_emp_revenue[project_id][employee_id] = revenue
project_emp_revenue = {}
for proj_id, emp_id, rev in cur.fetchall():
    project_emp_revenue.setdefault(proj_id, {})[emp_id] = float(rev)

# Step 3: Load associate employee IDs per project
cur.execute("""
    SELECT ps.project_id, ps.employee_id
    FROM project_staff ps
    JOIN employee e ON ps.employee_id = e.id
    WHERE LOWER(e.role) = 'associate'
""")
project_assoc_ids = {}
for proj_id, emp_id in cur.fetchall():
    project_assoc_ids.setdefault(proj_id, set()).add(emp_id)

# Step 4: Fetch all non-associate project staff assignments
cur.execute("""
    SELECT ps.employee_id, ps.project_id, ps.company_id,
           ps.commission_percentage,
           e.role, e.override_percentage
    FROM project_staff ps
    JOIN employee e ON ps.employee_id = e.id
    WHERE LOWER(e.role) != 'associate'
""")
staff_rows = cur.fetchall()
print(f"Computing commission records for {len(staff_rows)} non-associate staff assignments...")

now = datetime.utcnow()
records = []
for emp_id, proj_id, company_id, commission_pct_raw, role, override_pct_raw in staff_rows:
    commission_pct = float(commission_pct_raw or 0) / 100
    override_pct = float(override_pct_raw or 0)
    role = (role or '').lower()

    emp_revenue_map = project_emp_revenue.get(proj_id, {})
    total_project_revenue = sum(emp_revenue_map.values())
    assoc_ids = project_assoc_ids.get(proj_id, set())
    total_assoc_revenue = sum(v for eid, v in emp_revenue_map.items() if eid in assoc_ids)
    own_revenue = emp_revenue_map.get(emp_id, 0.0)

    if role == 'director':
        direct = own_revenue * commission_pct
        override = total_project_revenue * override_pct / 100
    else:
        direct = total_assoc_revenue * commission_pct
        override = 0.0

    records.append((emp_id, proj_id, company_id, own_revenue, direct, override, now))

if records:
    cur.executemany("""
        INSERT INTO staff_commission_record
            (employee_id, project_id, company_id, revenue, direct_commission, override_commission, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (employee_id, project_id) DO UPDATE SET
            revenue             = EXCLUDED.revenue,
            direct_commission   = EXCLUDED.direct_commission,
            override_commission = EXCLUDED.override_commission,
            updated_at          = EXCLUDED.updated_at
    """, records)
    print(f"Upserted {cur.rowcount} staff_commission_record rows.")
    conn.commit()
else:
    print("No non-associate staff assignments found — nothing to backfill.")

# Step 5: Verify
cur.execute("SELECT COUNT(*) FROM staff_commission_record")
total = cur.fetchone()[0]
print(f"Total rows in staff_commission_record: {total}")

cur.close()
conn.close()
print("Done.")
