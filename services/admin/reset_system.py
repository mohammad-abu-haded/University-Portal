from datetime import datetime, timezone
from pymongo import MongoClient
from neo4j import GraphDatabase
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError
import os

# =========================
# MongoDB
# =========================
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["university_portal"]

users_col = mongo_db["users"]
students_col = mongo_db["students"]
instructors_col = mongo_db["instructors"]
courses_col = mongo_db["courses"]
enrollments_col = mongo_db["enrollments"]
assignments_col = mongo_db["assignments"]
rooms_col = mongo_db["rooms"]

# =========================
# Neo4j
# =========================
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "test1234"

neo4j_driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASS)
)

# =========================
# InfluxDB (✔️ FIXED)
# =========================
INFLUX_URL = "http://localhost:8086"

# ⛔️ ضع التوكن الحقيقي هنا
INFLUX_TOKEN = "SUPER_ADMIN_TOKEN_123"

INFLUX_ORG = "my-org"
INFLUX_BUCKET = "my-bucket"

INFLUX_MEASUREMENTS = [
    "student_login_events",
    "student_course_activity",
    "student_assignment_events"
]

# =========================
# RESET FUNCTION
# =========================
def reset_entire_system():
    print("\n🧹 RESETTING ENTIRE SYSTEM\n")

    # -------------------------
    # MongoDB
    # -------------------------
    print("🟢 Clearing MongoDB collections...")
    users_col.delete_many({})
    students_col.delete_many({})
    instructors_col.delete_many({})
    courses_col.delete_many({})
    enrollments_col.delete_many({})
    assignments_col.delete_many({})
    rooms_col.delete_many({})
    print("✅ MongoDB cleared")

    # -------------------------
    # Neo4j
    # -------------------------
    print("🔵 Clearing Neo4j database...")
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("✅ Neo4j cleared")

    # -------------------------
    # InfluxDB
    # -------------------------
    print("🟣 Clearing InfluxDB measurements...")

    try:
        client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG,
            timeout=60_000
        )

        delete_api = client.delete_api()

        start = "1970-01-01T00:00:00Z"
        stop = datetime.now(timezone.utc).isoformat()

        for measurement in INFLUX_MEASUREMENTS:
            delete_api.delete(
                bucket=INFLUX_BUCKET,
                org=INFLUX_ORG,
                start=start,
                stop=stop,
                predicate=f'_measurement="{measurement}"'
            )
            print(f"   🧹 Cleared measurement: {measurement}")

        client.close()
        print("✅ InfluxDB measurements cleared")

    except InfluxDBError as e:
        print("❌ InfluxDB Error")
        print(e)

    except Exception as e:
        print("❌ Unexpected Error")
        print(e)

    print("\n🎉 SYSTEM RESET COMPLETED SUCCESSFULLY\n")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    reset_entire_system()
