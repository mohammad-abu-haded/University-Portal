from services.student_information_service import (
    users_col,
    students_col,
    instructors_col,
    courses_col,
    enrollments_col,
    assignments_col,
    rooms_col
)
from services.academic_network_service import driver


def fetch_all_data_summary():
    print("\n📦 ===== FETCH ALL DATA SUMMARY =====")

    # =========================
    # MongoDB
    # =========================
    print("\n🟢 MongoDB:")

    print(f"👤 Users       : {users_col.count_documents({})}")
    print(f"👨‍🎓 Students    : {students_col.count_documents({})}")
    print(f"👨‍🏫 Instructors : {instructors_col.count_documents({})}")
    print(f"📘 Courses     : {courses_col.count_documents({})}")
    print(f"📝 Assignments : {assignments_col.count_documents({})}")
    print(f"🏫 Rooms       : {rooms_col.count_documents({})}")
    print(f"🧾 Enrollments : {enrollments_col.count_documents({})}")

    # =========================
    # Neo4j
    # =========================
    print("\n🔵 Neo4j:")
    with driver.session() as session:
        counts = {
            "Students": session.run(
                "MATCH (s:Student) RETURN count(s) AS c"
            ).single()["c"],
            "Instructors": session.run(
                "MATCH (i:Instructor) RETURN count(i) AS c"
            ).single()["c"],
            "Courses": session.run(
                "MATCH (c:Course) RETURN count(c) AS c"
            ).single()["c"],
            "Assignments": session.run(
                "MATCH (a:Assignment) RETURN count(a) AS c"
            ).single()["c"],
            "ENROLLED_IN": session.run(
                "MATCH (:Student)-[r:ENROLLED_IN]->(:Course) RETURN count(r) AS c"
            ).single()["c"],
            "TEACHES": session.run(
                "MATCH (:Instructor)-[r:TEACHES]->(:Course) RETURN count(r) AS c"
            ).single()["c"],
        }

    for k, v in counts.items():
        print(f"{k:<12}: {v}")

    print("\n✅ ==================================\n")
