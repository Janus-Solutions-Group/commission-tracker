"""
migrate_staff_commission_rates.py — Run once to add commission_pct and override_pct
columns to the existing staff_commission_record table and backfill their values
from the current ProjectStaff and Employee assignments.

commission_pct  — stored as a decimal fraction (e.g. 0.10 for 10%)
                  sourced from project_staff.commission_percentage / 100
override_pct    — stored as a decimal fraction (e.g. 0.02 for 2%)
                  sourced from employee.override_percentage / 100

Safe to re-run: column additions use IF NOT EXISTS; the UPDATE only touches rows
where the values are still at their default (0.0).

Usage:
    python migrate_staff_commission_rates.py
"""
import psycopg2

DATABASE_URL = "postgresql://postgres.wfpbsrcskmklqiibxyvg:26GLyzU6v%40CSAiK@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Step 1: Add columns (idempotent)
for stmt in [
    "ALTER TABLE staff_commission_record ADD COLUMN IF NOT EXISTS commission_pct FLOAT NOT NULL DEFAULT 0.0",
    "ALTER TABLE staff_commission_record ADD COLUMN IF NOT EXISTS override_pct   FLOAT NOT NULL DEFAULT 0.0",
]:
    cur.execute(stmt)
    print(f"Executed: {stmt}")
conn.commit()
print("Columns added (or already existed).")

# Step 2: Backfill commission_pct from project_staff.commission_percentage
cur.execute("""
    UPDATE staff_commission_record scr
    SET commission_pct = ps.commission_percentage / 100.0
    FROM project_staff ps
    WHERE ps.employee_id = scr.employee_id
      AND ps.project_id  = scr.project_id
      AND scr.commission_pct = 0.0
""")
print(f"Backfilled commission_pct for {cur.rowcount} rows.")

# Step 3: Backfill override_pct from employee.override_percentage (directors only)
cur.execute("""
    UPDATE staff_commission_record scr
    SET override_pct = e.override_percentage / 100.0
    FROM employee e
    WHERE e.id = scr.employee_id
      AND LOWER(e.role) = 'director'
      AND scr.override_pct = 0.0
""")
print(f"Backfilled override_pct for {cur.rowcount} director rows.")

conn.commit()

# Step 4: Verify — report any rows still at 0 that have a non-zero staff assignment
cur.execute("""
    SELECT COUNT(*)
    FROM staff_commission_record scr
    JOIN project_staff ps ON ps.employee_id = scr.employee_id AND ps.project_id = scr.project_id
    WHERE scr.commission_pct = 0.0
      AND ps.commission_percentage > 0
""")
remaining = cur.fetchone()[0]
if remaining:
    print(f"WARNING: {remaining} rows have commission_pct=0 but a non-zero ProjectStaff percentage.")
else:
    print("All rows backfilled successfully.")

cur.close()
conn.close()
print("Done.")
