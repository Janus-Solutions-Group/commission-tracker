"""
migrate_commission_pct.py — Run once to add commission_pct column to hours_entry
and backfill it from the current ProjectStaff.commission_percentage assignment
for each entry.

commission_pct is stored as a decimal fraction (e.g. 0.05 for 5%) so the
display layer can recalculate non-associate commissions using the rate that was
in effect when the entry was created, even if the rate changes later.

Usage:
    python migrate_commission_pct.py
"""
import psycopg2

DATABASE_URL = "postgresql://postgres.wfpbsrcskmklqiibxyvg:26GLyzU6v%40CSAiK@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Step 1: Add column (idempotent)
cur.execute("ALTER TABLE hours_entry ADD COLUMN IF NOT EXISTS commission_pct FLOAT")
conn.commit()
print("Column commission_pct added (or already existed).")

# Step 2: Backfill commission_pct from the matching ProjectStaff assignment.
# Uses commission_percentage / 100 to convert the stored percentage to a decimal.
# Only updates rows where commission_pct is NULL so re-running is safe.
cur.execute("""
    UPDATE hours_entry he
    SET commission_pct = ps.commission_percentage / 100.0
    FROM project_staff ps
    WHERE ps.employee_id = he.employee_id
      AND ps.project_id  = he.project_id
      AND he.commission_pct IS NULL
""")
updated = cur.rowcount
conn.commit()
print(f"Backfilled commission_pct for {updated} rows from ProjectStaff assignments.")

# Step 3: Report entries that had no matching ProjectStaff (unassigned hours).
# These are left as NULL — the app falls back to the current rate for them.
cur.execute("""
    SELECT COUNT(*)
    FROM hours_entry
    WHERE commission_pct IS NULL
""")
remaining = cur.fetchone()[0]
if remaining:
    print(
        f"NOTE: {remaining} entries still have NULL commission_pct "
        "(no matching ProjectStaff row — the app will use the current "
        "assignment rate for these entries at report time)."
    )
else:
    print("All entries backfilled successfully.")

cur.close()
conn.close()
