import random
from datetime import datetime, timedelta, timezone

from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from services.analytics_service import _client
from pymongo import MongoClient

# =========================
# CONFIG
# =========================
DAYS_BACK = 30
MIN_LOGINS = 5
MAX_LOGINS = 30

MIN_VISITS = 3
MAX_VISITS = 15

# =========================
# MongoDB
# =========================
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["university_portal"]

students_col = mongo_db["students"]
enrollments_col = mongo_db["enrollments"]

# =========================
# Helpers
# =========================
def random_time_within_days(days: int) -> datetime:
    now = datetime.now(timezone.utc)
    delta = timedelta(
        days=random.randint(0, days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return now - delta


# =========================
# Seed Logins
# =========================
def seed_student_logins(write_api):
    print("🔐 Seeding student login events...")

    points = []

    for s in students_col.find({}, {"student_id": 1, "_id": 0}):
        student_id = s["student_id"]
        login_count = random.randint(MIN_LOGINS, MAX_LOGINS)

        for _ in range(login_count):
            p = (
                Point("student_login_events")
                .tag("student_id", student_id)
                .field("event", 1)
                .time(random_time_within_days(DAYS_BACK), WritePrecision.NS)
            )
            points.append(p)

    write_api.write(
    bucket="my-bucket",
    org="my-org",
    record=points
)

    print(f"✅ Login events inserted: {len(points)}")


# =========================
# Seed Course Activity
# =========================
def seed_course_activity(write_api):
    print("📘 Seeding course activity (NO submissions)...")

    points = []

    enrollments = list(enrollments_col.find({}, {"_id": 0}))

    for e in enrollments:
        student_id = e["student_id"]
        course_id = e["course_id"]

        # ---- add_course (once) ----
        p_add = (
            Point("student_course_activity")
            .tag("student_id", student_id)
            .tag("course_id", course_id)
            .tag("activity_type", "add_course")
            .field("value", 1)
            .time(random_time_within_days(DAYS_BACK), WritePrecision.NS)
        )
        points.append(p_add)

        # ---- view_course (multiple) ----
        visit_count = random.randint(MIN_VISITS, MAX_VISITS)
        for _ in range(visit_count):
            p_view = (
                Point("student_course_activity")
                .tag("student_id", student_id)
                .tag("course_id", course_id)
                .tag("activity_type", "view_course")
                .field("value", 1)
                .time(random_time_within_days(DAYS_BACK), WritePrecision.NS)
            )
            points.append(p_view)

        # ❌ NO submit events

    write_api.write(
    bucket="my-bucket",
    org="my-org",
    record=points
)

    print(f"✅ Course activity events inserted: {len(points)}")


# =========================
# MASTER
# =========================
def run_influx_seed():
    print("\n🚀 STARTING INFLUX SEED (NO SUBMISSIONS)\n")

    client = _client()
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)

        seed_student_logins(write_api)
        seed_course_activity(write_api)

        print("\n🎉 INFLUX SEED COMPLETED SUCCESSFULLY")
        print("❗ No assignment submissions were generated (as required)\n")

    finally:
        client.close()


if __name__ == "__main__":
    run_influx_seed()
