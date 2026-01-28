"""
SYSTEM FULL SEED
================
This file seeds:
1) MongoDB + Neo4j (base data)
2) Assignment submissions (Mongo + Influx)
3) InfluxDB activity (logins, visits, add_course)

Used by admin_tools.py with ONE function call.
"""

# =========================
# 1️⃣ Base System Seed
# =========================
from services.admin.full_seed import run_full_seed


# =========================
# 2️⃣ Assignment Submissions (Mongo + Influx)
# =========================
from services.admin.assignment_submission_seed import seed_assignment_submissions


# =========================
# 3️⃣ Influx Activity Seed (logins + visits)
# =========================
from services.admin.influx_seed import run_influx_seed


# =========================
# MASTER FUNCTION
# =========================
def seed_entire_system():
    print("\n🚀 STARTING FULL SYSTEM SEED\n")

    print("🔹 Step 1: Seeding base system data (Mongo + Neo4j)")
    run_full_seed()

    print("\n🔹 Step 2: Seeding assignment submissions (Mongo + Influx)")
    seed_assignment_submissions()

    print("\n🔹 Step 3: Seeding InfluxDB activity (logins & visits)")
    run_influx_seed()

    print("\n🎉 FULL SYSTEM SEED COMPLETED SUCCESSFULLY\n")
