import time
import uuid
from services.academic_network_service import get_course_assignments, get_course_students, get_student_course_network, link_assignment_to_course
from services.analytics_service import get_student_course_activity
from services.auth_user_service import validate_session, refresh_user_session
from services.course_activity_service import cache_course_assignments, cache_enrolled_students, create_assignment, get_answer, get_cached_course_assignments, get_cached_enrolled_students, invalidate_course_details_cache, invalidate_instructor_course_assignments_cache, invalidate_pending_tasks_cache_for_course, invalidate_student_course_details_cache, invalidate_student_pending_task_cache, update_grades
from services.student_information_service import get_student_basic_info, get_student_course_performance
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
def ensure_session(session):

    if not validate_session(session["sessionID"])["valid"]:
        print("⚠️ Session expired. Please login again.")
        time.sleep(2)
        return False
    return True

def is_session_valid(session) -> bool:
    return validate_session(session["sessionID"])["valid"]

def instructor_dashboard(courses_details, session, user_id):

    while True:
        if not ensure_session(session):
            break
        print("\n--- Instructor Menu ---")
        print("\n=== Courses Assigned to You ===")
        for i, course_details in enumerate(courses_details, start=1):
            print(
                f"{i}. {course_details['details']['course_name']} "
            )

        print(f"{len(courses_details) + 1}. Exit")
        choice = input("Enter your choice: ")
        if not ensure_session(session):
            break
        refresh_user_session(session["sessionID"])
        if not choice.isdigit():
            print("❗ Invalid choice, please enter a number.")
            time.sleep(1)
            continue
        choice = int(choice)
        if choice == (len(courses_details) + 1):
            break
        if choice < 1 or choice > len(courses_details):
            print("❗Invalid choice, please try again.")
            time.sleep(1)
        else:
            view_course_screen(courses_details[choice - 1], session, user_id)

            
def view_course_screen(course_details, session, user_id):

    print("\n=== Course Details ===")
    print(f"{course_details['details']['course_name']}")
    print("Time:")
    schedule = course_details["details"]["schedule"]
    print(
        f"Days: {', '.join(schedule['days'])} | "
        f"Time: {schedule['start_time']} - {schedule['end_time']}"
    )

    print(f"Room: {course_details['details']['room']}")
    print(f"Registered Students: {course_details['details']['registered_students_count']}")

    while True:
        if not is_session_valid(session):
            break
        print("\n1. Add Assignment")
        print("2. Insert Grades")
        print("3. View Enrolled Students")
        print("4. Exit")
        choice = input("Enter your choice: ")
        if not is_session_valid(session):
            break
        refresh_user_session(session["sessionID"])
        match choice:
            case "1":
                add_assignment_screen(session, course_details['course_id'],  user_id,)

            case "2":
                grade_assignment_screen(session, course_details['course_id'])

            case "3":
                view_students_screen(session, course_details['course_id'])

            case "4":
                break

            case _:
                print("❗Invalid choice, please try again.")
                time.sleep(1)

def add_assignment_screen(session, course_id, user_id):
    assignment_title = input("Enter Assignment title: ")
    description = input("Enter Description: ")
    end_date = input("Enter deadline end date (YYYY-MM-DD): ")
    end_time = input("Enter deadline end time (HH:MM): ")
    while True:
        try:
            max_grade = float(input("Enter assignment maximum grade: "))
            break
        except ValueError:
            print("❌ Please enter a valid number")
            continue
    assignmentData = {
        "assignment_id": str(uuid.uuid4()),
        "title": assignment_title,
        "description": description,
        "deadline": f"{end_date} {end_time}",
        "max_grade": max_grade
    }
    input("Press any key to add assignment...")
    if not is_session_valid(session):
        return
    refresh_user_session(session["sessionID"])
    result = create_assignment(course_id, assignmentData)
    if not result["success"]:
        print("❌ Failed to create assignment:", result["error"])
        return
    print("✅ Assignment created successfully")
    link_assignment_to_course(assignmentData["assignment_id"], course_id, assignmentData["title"])
    invalidate_instructor_course_assignments_cache(course_id)
    invalidate_course_details_cache(course_id)
    invalidate_pending_tasks_cache_for_course(course_id)

def grade_assignment_screen(session, course_id):
    course_assignments = get_cached_course_assignments(course_id)
    if not course_assignments:
        course_assignments = get_course_assignments(course_id)
        cache_course_assignments(course_id, course_assignments)
        print("from neo4j")
    else:
        print("from redis")

    assignments = course_assignments.get("assignments", [])

    if not assignments:
        print("No assignments found for this course.")
        input("Press any key to back...")
        return
    else:
        print("Assignments:")
        for i, s in enumerate(assignments, start=1):
            print(f"{i}. {s['assignmentTitle']}")

    print(f"{len(assignments) + 1}. Exit")

    while True:
        choice = input("Enter your choice: ")
        if not is_session_valid(session):
            return
        refresh_user_session(session["sessionID"])
        if not choice.isdigit():
            print("❗ Invalid choice, please enter a number.")
            time.sleep(1)
            continue
        choice = int(choice)
        if choice == (len(assignments) + 1):
            return
        if choice < 1 or choice > len(assignments):
            print("❗Invalid choice, please try again.")
            time.sleep(1)
        else:
            assignment = assignments[choice - 1]
            break

    enrolled_students = get_cached_enrolled_students(course_id)
    if not enrolled_students:
        enrolled_students = get_course_students(course_id)
        cache_enrolled_students(course_id, enrolled_students)
        print("from neo4j")
    else:
        print("from redis")

    students = enrolled_students.get("students", [])

    if not students:
        print("No students enrolled in this course.")
        input("Press any key to back...")
        return
    else:
        print("Students:")
        for i, s in enumerate(students, start=1):
            print(f"{i}. {s['studentName']}")

    print(f"{len(students) + 1}. Exit")

    while True:
        choice = input("Enter your choice: ")
        if not is_session_valid(session):
            return
        refresh_user_session(session["sessionID"])
        if not choice.isdigit():
            print("❗ Invalid choice, please enter a number.")
            time.sleep(1)
            continue
        choice = int(choice)
        if choice == (len(students) + 1):
            return
        if choice < 1 or choice > len(students):
            print("❗Invalid choice, please try again.")
            time.sleep(1)
        else:
            student = students[choice - 1]
            break
    student_name = student['studentName']
    assignment_title = assignment['assignmentTitle']
    student_id = student['studentID']
    assignment_id = assignment['assignmentID']
    student_assignment = get_answer(student_id, assignment_id)
    student_answer = student_assignment['answer']
    max_grade = student_assignment.get('maxGrade', "00")
    grade_str = student_assignment.get('grade', "Not graded yet")
    print("\n--- Student Assignment ---")
    print(f"Student Name : {student_name}")
    print(f"Assignment   : {assignment_title}")
    print(f"Answer       : {student_answer if student_answer else 'No answer submitted'}")
    print(f"Max Grade    : {max_grade}")
    print(f"Grade        : {grade_str}")
    print("-------------------------\n")
    while True:
        print("1. Input the grade")
        print("2. Exit")
        choice = input("Enter your choice: ")
        match choice:
            case "1":
                try:
                    grade_input = float(input("Enter the grade for this assignment: "))
                except ValueError:
                    print("❌ Please enter a valid number")
                    continue
                input("Press any key to submit grade...")
                if not is_session_valid(session):
                    return
                refresh_user_session(session["sessionID"])
                update_grades(assignment_id, student_id, grade_input)
                invalidate_student_course_details_cache(student_id, course_id)
                return

            case "2":
                return
            
            case _:
                print("❗Invalid choice, please try again.")
                time.sleep(1)
    

def view_students_screen(session, course_id):
    enrolled_students = get_cached_enrolled_students(course_id)
    if not enrolled_students:
        enrolled_students = get_course_students(course_id)
        cache_enrolled_students(course_id, enrolled_students)
        print("from neo4j")
    else:
        print("from redis")

    students = enrolled_students.get("students", [])

    if not students:
        print("No students enrolled in this course.")
        input("Press any key to back...")
        return
    else:
        print("Students:")
        for i, s in enumerate(students, start=1):
            print(f"{i}. {s['studentName']}")

    print(f"{len(students) + 1}. Exit")

    while True:
        choice = input("Enter your choice: ")
        if not is_session_valid(session):
            return
        refresh_user_session(session["sessionID"])
        if not choice.isdigit():
            print("❗ Invalid choice, please enter a number.")
            time.sleep(1)
            continue
        choice = int(choice)
        if choice == (len(students) + 1):
            return
        if choice < 1 or choice > len(students):
            print("❗Invalid choice, please try again.")
            time.sleep(1)
        else:
            student = students[choice - 1]
            break
    student_id = student['studentID']
    student_course_performance = get_student_course_performance(student_id, course_id)
    student_course_network = get_student_course_network(student_id, course_id)
    student_course_activity = get_student_course_activity(student_id, course_id)
    student_info = get_student_basic_info(student_id)
    show_student_statistics_for_instructor(
        student_course_performance,
        student_course_network,
        student_course_activity,
        student_info
    )
    


def show_student_statistics_for_instructor(
    student_course_performance,
    student_course_network,
    student_course_activity,
    student_info
):
    print("\n" + "=" * 70)
    print(f"👤 Student : {student_info['full_name']}")
    print(f"🎓 Major   : {student_info['major_name']}")

    print("🎓 STUDENT COURSE DASHBOARD — INSTRUCTOR VIEW")
    print("=" * 70)

    course = student_course_performance

    print(f"\n📘 Course: {course['course_name']}")
    print(f"📌 Status: {course['status']}")

    grade = course["grade"]
    assignments = course["assignments"]

    graded = len(assignments["graded"])
    pending = len(assignments["submitted_not_graded"])
    missing = len(assignments["missing"])
    total = assignments["total"]

    if grade["percentage"] is not None:
        print(
            f"📊 Current Grade: "
            f"{grade['total_grade']} / {grade['max_total']} "
            f"({grade['percentage']}%)"
        )
    else:
        print("📊 Current Grade: Not graded yet")

    progress = round((graded / total) * 100, 2) if total else 0
    print(f"📈 Evaluation Progress: {progress}%")

    print("\n📝 Assignments Details:")

    for a in assignments["graded"]:
        print(f"  ✅ {a['display']}")

    for a in assignments["submitted_not_graded"]:
        print(f"  🕒 {a['display']}")

    for a in assignments["missing"]:
        print(f"  ❌ {a['display']}")

    # ========= ACTIVITY =========
    visits = student_course_activity.get("visit_count", 0)
    submissions = len(student_course_activity.get("submitted_assignments", []))

    print("\n⚡ Student Activity (This Course)")
    print(f"- Visits      : {visits}")
    print(f"- Submissions : {submissions}")

    # ========= NETWORK =========
    peers = student_course_network.get("students", [])
    print("\n👥 Course Network")
    print(f"- Peers in course: {len(peers)}")

    # ========= MENU =========
    print("\n" + "-" * 70)
    print("1. Show Charts")
    print("2. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":
        show_student_course_charts(
            student_course_performance,
            student_course_activity
        )
        show_course_student_network(student_course_network)
def show_student_course_charts(
    student_course_performance,
    student_course_activity
):
    

    course = student_course_performance
    assignments = course["assignments"]
    grade = course["grade"]

    graded = len(assignments["graded"])
    pending = len(assignments["submitted_not_graded"])
    missing = len(assignments["missing"])
    total = assignments["total"]

    progress = (graded / total) * 100 if total else 0
    current_grade = grade["percentage"] or 0

    visits = student_course_activity.get("visit_count", 0)
    submissions = len(student_course_activity.get("submitted_assignments", []))

    fig = plt.figure(figsize=(14, 8))

    plt.subplot(2, 2, 1)
    plt.bar(["Graded", "Pending", "Missing"], [graded, pending, missing])
    plt.title("Assignments Status")

    plt.subplot(2, 2, 2)
    plt.bar(["Current Grade", "Evaluation Progress"], [current_grade, progress])
    plt.ylim(0, 100)
    plt.title("Grade vs Progress")

    plt.subplot(2, 2, 3)
    plt.bar(["Visits", "Submissions"], [visits, submissions])
    plt.title("Student Activity")

    plt.suptitle(
        f"🎓 {course['course_name']} — Student Analysis",
        fontsize=16
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
    plt.close(fig)


def show_course_student_network(student_course_network):
    import networkx as nx
    import matplotlib.pyplot as plt
    import numpy as np

    course_id = student_course_network.get("course_id")
    center_student = student_course_network.get("center_student")
    students = student_course_network.get("students", [])

    if not center_student:
        print("❌ No center student provided")
        return

    if not students:
        print("❌ No students in this course")
        return

    # ===== Graph =====
    G = nx.DiGraph()

    # Unique internal node IDs
    center_node = f"center_{center_student['id']}"
    peer_nodes = [
        f"peer_{s['id']}"
        for s in students
        if s.get("id")
    ]

    # ===== Labels =====
    labels = {
        center_node: f"{center_student.get('name', center_student['id'])}\n📘 {course_id}"
    }

    for s in students:
        labels[f"peer_{s['id']}"] = s.get("name", s["id"])

    # ===== Add nodes =====
    G.add_node(center_node)
    for p in peer_nodes:
        G.add_node(p)

    # ===== Add edges (students ➜ center) =====
    for p in peer_nodes:
        G.add_edge(p, center_node)

    # ===== Layout =====
    pos = {center_node: (0, 0)}
    radius = 4

    for i, p in enumerate(peer_nodes):
        angle = 2 * np.pi * i / len(peer_nodes)
        pos[p] = (radius * np.cos(angle), radius * np.sin(angle))

    # ===== Draw =====
    node_colors = [
        "#FF4757" if n == center_node else "#1E90FF"
        for n in G.nodes()
    ]

    node_sizes = [
        5200 if n == center_node else 2600
        for n in G.nodes()
    ]

    nx.draw(
        G,
        pos,
        labels=labels,
        with_labels=True,
        node_color=node_colors,
        node_size=node_sizes,
        edge_color="#2F3542",
        arrows=True,
        arrowsize=18,
        font_size=10,
        linewidths=2
    )

    plt.title(
        f"🎓 Student Course Network — {course_id}",
        fontsize=16
    )
    plt.axis("off")
    plt.tight_layout()
    plt.show()

