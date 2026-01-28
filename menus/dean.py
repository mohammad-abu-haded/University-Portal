import time

from pymongo import MongoClient
from services.academic_network_service import create_instructor_node, create_student_node, get_student_network, link_instructor_to_course
from services.analytics_service import get_student_activity, get_top_courses, get_top_courses_by_major, get_worst_courses, get_worst_courses_by_major
from services.auth_user_service import validate_session, refresh_user_session
from services.course_activity_service import invalidate_available_courses_cache, invalidate_instructor_courses_cache
from services.student_information_service import create_course, create_major, get_all_majors, get_available_instructors, get_available_rooms, get_course_ids_by_major, get_student_basic_info, get_student_performance, register_instructor, register_student
import secrets
import string
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from math import ceil
from collections import defaultdict
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["university_portal"]
students_col = mongo_db["students"]
instructors_col = mongo_db["instructors"]
courses_col = mongo_db["courses"]
def generate_next_id(prefix: str, last_id: str, width: int = 4):
    """
    prefix: 'II'
    last_id: 'II0019'
    width: 
    """
    number = int(last_id.replace(prefix, ""))
    next_number = number + 1
    return f"{prefix}{str(next_number).zfill(width)}"

def generate_next_instructor_id():
    last = instructors_col.find_one(
        {},
        sort=[("instructor_id", -1)]
    )

    if not last:
        return "II0000"

    return generate_next_id("II", last["instructor_id"])

def generate_next_student_id():
    last = students_col.find_one(
        {},
        sort=[("student_id", -1)]
    )

    if not last:
        return "220000"

    return generate_next_id("22", last["student_id"])

def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))

def save_credentials(filename, user_id, full_name, password):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{user_id} | {full_name} | {password}\n")

def ensure_session(session):

    if not validate_session(session["sessionID"])["valid"]:
        print("⚠️ Session expired. Please login again.")
        time.sleep(2)
        return False
    return True

def is_session_valid(session) -> bool:
    return validate_session(session["sessionID"])["valid"]

def dean_dashboard(session):

    while True:
        if not ensure_session(session):
            break
        print("\n--- Dean Menu ---")
        print("1. Add Course")
        print("2. Create Student")
        print("3. Create Instructor")
        print("4. Create Major")
        print("5. Student Stats")
        print("6. Course Analytics")
        print("7. Exit")

        choice = input("Enter your choice: ")
        if not ensure_session(session):
            break
        refresh_user_session(session["sessionID"])
        match choice:
            case "1":
                add_course_screen(session)

            case "2":
                create_student_screen(session)

            case "3":
                create_instructor_screen(session)

            case "4":
                create_major_name_screen(session)

            case "5":
                student_statistics_screen(session)

            case "6":
                course_analytics_screen(session)


            case "7":
                break


            case _:
                print("❗Invalid choice, please try again.")
                time.sleep(1)


def add_course_screen(session):
    # ===============================
    # Select Days (NEW STYLE)
    # ===============================
    days_map = {
        1: "Sunday",
        2: "Monday",
        3: "Tuesday",
        4: "Wednesday",
        5: "Thursday"
    }

    print("=== Select the day(s) ===")
    for k, v in days_map.items():
        print(f"{k}. {v}")

    print("Enter day numbers separated by commas (e.g. 1,3,5):")

    while True:
        choice = input("Your choice: ").strip()
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            if not indices:
                raise ValueError
            if any(i not in days_map for i in indices):
                raise ValueError

            days = list(dict.fromkeys(days_map[i] for i in indices))
            break

        except ValueError:
            print("❗ Invalid input. Example: 1,2 or 1,3,5")

    
    print("Time format: HH:M - e.g. 14:30")
    start_time  = input("Enter start time: ")
    end_time  = input("Enter end time: ")
    schedule = {
        "days": days,
        "start_time": start_time,
        "end_time": end_time
    }

    input("Press any key to Find Availability...")
    if not is_session_valid(session):
        return
    refresh_user_session(session["sessionID"])

    available_rooms = get_available_rooms(schedule)
    available_instructors = get_available_instructors(schedule)

    print(", ".join(days), f": {start_time} - {end_time}")
    if not available_rooms:
        print("❌ No rooms available at this time.")
        time.sleep(1)
        return
    
    while True:
        print("\n--- Available Rooms ---")
        print("-" * 35)
        for i, room in enumerate(available_rooms, start=1):
            print(f"{i:>2}. Room: {room['room']}")
            print(f"     👥 Capacity: {room['capacity']}")
            print("-" * 35)

        room_choice = input("Enter your choice: ")
        if not room_choice.isdigit():
            print("❗ Invalid choice, please enter a number.")
            time.sleep(1)
            continue
        room_index = int(room_choice)

        if room_index < 1 or room_index > len(available_rooms):
            print("❗Invalid choice, please try again.")
        else:
            selected_room = available_rooms[room_index - 1]['room']
            break

    if not available_instructors:
        print("❌ No instructors available at this time.")
        time.sleep(1)
        return
    
    while True:
        print("Instructors:")
        for i, instructor in enumerate(available_instructors, start=1):
            print(f"{i}.  - {instructor['full_name']}")

        instructor_choice = input("Enter your choice: ")
        if not instructor_choice.isdigit():
            print("❗ Invalid choice, please enter a number.")
            time.sleep(1)
            continue
        instructor_index = int(instructor_choice)

        if instructor_index < 1 or instructor_index > len(available_instructors):
            print("❗Invalid choice, please try again.")
        else:
            selected_instructor = available_instructors[instructor_index - 1]
            instructor_id = selected_instructor['instructor_id']
            break

    # ===============================
    # Select Majors (NEW)
    # ===============================
    majors = get_all_majors()
    if not majors:
        print("❌ No majors available. Please create majors first.")
        time.sleep(1)
        return

    print("\n=== Select Majors for this Course ===")
    for i, major in enumerate(majors, start=1):
        print(f"{i}. {major['major_name']} ({major['major_id']})")

    print("Enter major numbers separated by commas (e.g. 1,3):")
    while True:
        choices = input("Your choice: ").strip()
        try:
            indices = [int(x.strip()) for x in choices.split(",")]
            if any(i < 1 or i > len(majors) for i in indices):
                raise ValueError
            selected_majors = [majors[i - 1]["major_id"] for i in indices]
            break
        except ValueError:
            print("❗ Invalid input. Example: 1,2")

    course_id = input("Enter course code (e.g. 8999): ").strip().upper()
    course_name = input("Insert Course Name: ")

    courseData = {
        "course_id": course_id,
        "major_ids": selected_majors,
        "details": {
            "course_name": course_name,
            "schedule": schedule,
            "room": selected_room,
            "instructor_name": selected_instructor['full_name'],
            "registered_students_count": 0,
        }
    }

    input("Press any key to Create Course...")
    if not is_session_valid(session):
        return
    refresh_user_session(session["sessionID"])

    result = create_course(courseData)
    if not result["success"]:
        print("⚠️", result["error"])
    else:
        print("✅", result["message"])
        link_instructor_to_course(selected_instructor['instructor_id'], course_id)

    invalidate_instructor_courses_cache(selected_instructor['instructor_id'])
    invalidate_available_courses_cache()


def create_student_screen(session):
    print("=== Create Student ===")

    full_name = input("Insert full name: ").strip()
    student_id = generate_next_student_id()


    # ===============================
    # Select Major
    # ===============================
    majors = get_all_majors()

    if not majors:
        print("❌ No majors available. Please create a major first.")
        time.sleep(1)
        return

    print("\n=== Available Majors ===")
    for i, major in enumerate(majors, start=1):
        print(f"{i}. {major['major_name']} ({major['major_id']})")

    while True:
        choice = input("Select Major Number: ")
        if not choice.isdigit():
            print("❗ Please enter a valid number.")
            continue

        choice = int(choice)
        if choice < 1 or choice > len(majors):
            print("❗ Invalid choice, try again.")
        else:
            selected_major = majors[choice - 1]
            break

    password = generate_password()
    input("Press any key to Create Student...")

    if not is_session_valid(session):
        return

    refresh_user_session(session["sessionID"])

    studentData = {
        "student_id": student_id,
        "full_name": full_name,
        "major_id": selected_major["major_id"]
    }

    userData = {
        "user_id": student_id,
        "password": password,
        "role": "student"
    }

    result = register_student(studentData, userData)

    if result["success"]:
        create_student_node(student_id, full_name)
        save_credentials(
            "students_credentials.txt",
            student_id,
            full_name,
            password
        )
        print("✅ Student created successfully")
        print(f"🎓 Major: {selected_major['major_name']}")
    else:
        print("⚠️", result["error"])

        

def create_instructor_screen(session):
    print("===Create Instructor===")
    full_name = input("Insert full name: ")
    instructor_id = generate_next_instructor_id()
    password = generate_password()
    input("Press any key to  Create instructor...")
    if not is_session_valid(session):
        return
    refresh_user_session(session["sessionID"])
    instructorData = {
        "instructor_id": instructor_id,
        "full_name": full_name
    }
    userData = {
        "user_id": instructor_id,
        "password": password,
        "role": "instructor"
    }

    result = register_instructor(instructorData, userData)
    if result["success"]:
        create_instructor_node(instructor_id)
        save_credentials(
            "instructors_credentials.txt",
            instructor_id,
            full_name,
            password
        )
        print("✅ Instructor created successfully")
    else:
        print("⚠️", result["error"])


def create_major_name_screen(session):
    print("=== Create Major ===")

    major_id = input("Insert Major ID (e.g. CS): ").strip().upper()
    major_name = input("Insert Major Name: ").strip()

    if not major_id or not major_name:
        print("❗ Major ID and Name are required.")
        time.sleep(1)
        return

    input("Press any key to Create Major...")

    if not is_session_valid(session):
        return

    refresh_user_session(session["sessionID"])

    majorData = {
        "major_id": major_id,
        "major_name": major_name
    }

    result = create_major(majorData)

    if result["success"]:
        print("✅ Major created successfully")
        print(f"   ID   : {major_id}")
        print(f"   Name : {major_name}")
    else:
        print("⚠️", result["error"])

    time.sleep(1.5)


def student_statistics_screen(session):
    while True:
        print("1. Insert Student ID")
        print("2. Exit")
        choice = input("Enter your choice: ")   
        if not is_session_valid(session):
            return
        refresh_user_session(session["sessionID"])

        match choice :
            case '1' :
                student_id = input("Insert Student ID: ")
                if not is_session_valid(session):
                    return
                refresh_user_session(session["sessionID"])
                student_performance = get_student_performance(student_id)
                student_info = get_student_basic_info(student_id)
                if not student_info:
                    print("❌ Student not found!")
                    continue
                if not student_performance :
                    print("Student is not enrolled in any courses yet.!")
                    continue
                student_network = get_student_network(student_id)
                student_activity = get_student_activity(student_id)
                show_student_statistics_for_dean(student_performance, student_network, student_activity, session, student_info)
            case '2' :
                return
            
            case _:
                print("❗ Invalid choice, please try again.")

def course_analytics_screen(session):
    while True:
        print("\n" + "=" * 60)
        print("📊 COURSE ANALYTICS")
        print("=" * 60)
        print("1. Top Courses (All)")
        print("2. Top Courses by Major")
        print("3. Worst Courses (All)")
        print("4. Worst Courses by Major")
        print("5. Back")

        choice = input("Enter your choice: ").strip()

        if not is_session_valid(session):
            return
        refresh_user_session(session["sessionID"])

        match choice:
            case "1":
                top_courses_statistics_screen(session)

            case "2":
                top_courses_by_major_screen(session)

            case "3":
                worst_courses_statistics_screen(session)

            case "4":
                worst_courses_by_major_screen(session)

            case "5":
                return

            case _:
                print("❗ Invalid choice, please try again.")

def show_student_statistics_for_dean(student_performance, student_network, student_activity, session, student_info):
    print("\n" + "=" * 70)
    print(f"👤 Student : {student_info['full_name']}")
    print(f"🎓 Major   : {student_info['major_name']}")
    print("🎓 STUDENT FULL ACADEMIC DASHBOARD — DEAN VIEW")
    print("=" * 70)

    total_graded = total_pending = total_missing = 0
    course_percentages = {}

    for course in student_performance:
        print(f"\n📘 Course: {course['course_name']}")
        print(f"📌 Status: {course['status']}")

        grade = course["grade"]
        assignments = course["assignments"]

        graded = len(assignments["graded"])
        pending = len(assignments["submitted_not_graded"])
        missing = len(assignments["missing"])
        total = assignments["total"]

        total_graded += graded
        total_pending += pending
        total_missing += missing

        if grade["percentage"] is not None:
            course_percentages[course["course_name"]] = grade["percentage"]
            print(f"📊 Current Grade: {grade['total_grade']} / {grade['max_total']} ({grade['percentage']}%)")
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

    # ========= ACTIVITY SUMMARY =========
    logins = student_activity.get("login_count", 0)
    visits = sum(v["visit_count"] for v in student_activity.get("courses", {}).values())
    submissions = sum(v["submitted_assignments"] for v in student_activity.get("courses", {}).values())

    print("\n⚡ Student Activity")
    print(f"- Logins       : {logins}")
    print(f"- Visits       : {visits}")
    print(f"- Submissions  : {submissions}")

    # ========= NETWORK SUMMARY =========
    peers = student_network.get("network", [])
    print("\n👥 Social Network")
    print(f"- Peers in courses: {len(peers)}")

    # ========= MENU =========
    print("\n" + "-" * 70)
    print("1. Show Charts")
    print("2. Exit")

    choice = input("Enter your choice: ")
    if not is_session_valid(session):
        return

    refresh_user_session(session["sessionID"])
    if choice == "1":
        show_student_charts(student_performance, student_network, student_activity)




def show_student_charts(student_performance, student_network, student_activity):
    courses = student_performance
    index = 0

    fig = plt.figure(figsize=(16, 10))

    def draw_course(idx):
        plt.clf()
        course = courses[idx]

        course_name = course["course_name"]
        assignments = course["assignments"]
        grade = course["grade"]

        graded = len(assignments["graded"])
        pending = len(assignments["submitted_not_graded"])
        missing = len(assignments["missing"])
        total = assignments["total"]

        progress = (graded / total) * 100 if total else 0
        current_grade = grade["percentage"] or 0

        ax1 = plt.subplot(2, 2, 1)
        ax1.bar(["Graded", "Pending", "Missing"], [graded, pending, missing])
        ax1.set_title("Assignments Status")

        ax2 = plt.subplot(2, 2, 2)
        ax2.bar(["Current Grade", "Evaluation Progress"], [current_grade, progress])
        ax2.set_ylim(0, 100)
        ax2.set_title("Grade vs Progress")

        logins = student_activity.get("login_count", 0)
        activity = student_activity.get("courses", {}).get(course.get("course_id"), {})
        visits = activity.get("visit_count", 0)
        submissions = activity.get("submitted_assignments", 0)

        ax3 = plt.subplot(2, 2, 3)
        ax3.bar(["Logins", "Visits", "Submissions"], [logins, visits, submissions])
        ax3.set_title("Student Activity")

        plt.suptitle(f"🎓 {course_name} ({idx+1}/{len(courses)})", fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        fig.canvas.draw_idle()

    def on_key(event):
        nonlocal index
        if event.key == "right":
            index = (index + 1) % len(courses)
        elif event.key == "left":
            index = (index - 1) % len(courses)
        draw_course(index)

    fig.canvas.mpl_connect("key_press_event", on_key)

    draw_course(index)
    plt.show()

    show_separate_course_networks(student_network)



def show_separate_course_networks(student_network_data):
    course_data = defaultdict(list)

    for peer in student_network_data.get("network", []):
        course_id = peer.get("courseID")
        student_id = peer.get("studentID")
        student_name = peer.get("studentName")

        if course_id and student_id:
            course_data[course_id].append({
                "id": student_id,
                "name": student_name or student_id
            })

    if not course_data:
        print("❌ No network data available")
        return

    courses = list(course_data.items())
    index = 0
    fig = plt.figure(figsize=(14, 10))

    def draw_course(idx):
        plt.clf()
        course_id, students = courses[idx]

        G = nx.Graph()

        center_node = f"course_{course_id}"
        G.add_node(center_node)

        labels = {center_node: course_id}

        for s in students:
            node_id = f"student_{s['id']}"
            G.add_node(node_id)
            G.add_edge(center_node, node_id)
            labels[node_id] = s["name"]

        pos = {center_node: (0, 0)}
        radius = max(3, len(students) * 0.25)

        for i, s in enumerate(students):
            angle = 2 * np.pi * i / len(students)
            pos[f"student_{s['id']}"] = (
                radius * np.cos(angle),
                radius * np.sin(angle)
            )

        node_colors = [
            "#FF4757" if n == center_node else "#1E90FF"
            for n in G.nodes()
        ]

        node_sizes = [
            4500 if n == center_node else 2200
            for n in G.nodes()
        ]

        nx.draw(
            G, pos,
            labels=labels,
            with_labels=True,
            node_color=node_colors,
            node_size=node_sizes,
            font_size=10,
            edge_color="#444",
            linewidths=2
        )

        plt.title(f"🎓 {course_id} ({idx+1}/{len(courses)})", fontsize=16)
        plt.axis("off")
        plt.tight_layout()
        fig.canvas.draw_idle()

    def on_key(event):
        nonlocal index
        if event.key == "right":
            index = (index + 1) % len(courses)
        elif event.key == "left":
            index = (index - 1) % len(courses)
        draw_course(index)

    fig.canvas.mpl_connect("key_press_event", on_key)
    draw_course(index)
    plt.show()


def top_courses_statistics_screen(session):
    while True:
        print("\n" + "=" * 60)
        print("📊 TOP COURSES STATISTICS")
        print("=" * 60)
        print("1. Show Top Courses")
        print("2. Back")

        choice = input("Enter your choice: ").strip()

        if not is_session_valid(session):
            return
        refresh_user_session(session["sessionID"])

        if choice == "1":
            try:
                n = int(input("Enter number of top courses to display: ").strip())
                if n <= 0:
                    print("❌ Please enter a positive number.")
                    continue
            except ValueError:
                print("❌ Invalid number.")
                continue

            top_courses = get_top_courses(limit=n)

            if not top_courses:
                print("❌ No data available.")
                continue

            print("\n🏆 Top Courses:\n")
            for i, course in enumerate(top_courses, start=1):
                print(
                    f"{i}. Course ID: {course['course_id']} | "
                    f"Visits: {course['visits']} | "
                    f"Submissions: {course['submissions']} | "
                    f"Score: {course['score']}"
                )

            input("\nPress Enter to continue...")

        elif choice == "2":
            return

        else:
            print("❗ Invalid choice, please try again.")


def worst_courses_statistics_screen(session):
    while True:
        print("\n" + "=" * 60)
        print("📉 WORST COURSES STATISTICS")
        print("=" * 60)
        print("1. Show Worst Courses")
        print("2. Back")

        choice = input("Enter your choice: ").strip()

        if not is_session_valid(session):
            return
        refresh_user_session(session["sessionID"])

        if choice == "1":
            try:
                n = int(input("Enter number of worst courses to display: ").strip())
                if n <= 0:
                    print("❌ Please enter a positive number.")
                    continue
            except ValueError:
                print("❌ Invalid number.")
                continue

            worst_courses = get_worst_courses(limit=n)

            if not worst_courses:
                print("❌ No data available.")
                continue

            print("\n🚨 Worst Courses:\n")
            for i, course in enumerate(worst_courses, start=1):
                print(
                    f"{i}. Course ID: {course['course_id']} | "
                    f"Visits: {course['visits']} | "
                    f"Submissions: {course['submissions']} | "
                    f"Score: {course['score']}"
                )

            input("\nPress Enter to continue...")

        elif choice == "2":
            return

        else:
            print("❗ Invalid choice, please try again.")

def select_major():
    majors = get_all_majors()
    if not majors:
        print("❌ No majors available.")
        return None

    print("\n=== Select Major ===")
    for i, m in enumerate(majors, start=1):
        print(f"{i}. {m['major_name']} ({m['major_id']})")

    while True:
        choice = input("Select Major Number: ")
        if choice.isdigit() and 1 <= int(choice) <= len(majors):
            return majors[int(choice) - 1]
        print("❗ Invalid choice")
        
def top_courses_by_major_screen(session):
    major = select_major()
    if not major:
        return

    course_ids = get_course_ids_by_major(major["major_id"])
    if not course_ids:
        print("❌ No courses for this major.")
        input("Press Enter to continue...")
        return

    while True:
        n_input = input("Enter number of top courses to display: ").strip()

        if not n_input:
            print("❗ Please enter a number.")
            continue
        if not n_input.isdigit():
            print("❗ Invalid number.")
            continue

        n = int(n_input)
        if n <= 0:
            print("❌ Please enter a positive number.")
            continue
        break

    results = get_top_courses_by_major(course_ids, limit=n)
    if not results:
        print("❌ No analytics data available.")
        input("Press Enter to continue...")
        return

    print(f"\n🏆 Top Courses — {major['major_name']}\n")
    for i, c in enumerate(results, start=1):
        print(
            f"{i}. Course ID: {c['course_id']} | "
            f"Visits: {c['visits']} | "
            f"Submissions: {c['submissions']} | "
            f"Score: {c['score']}"
        )

    input("\nPress Enter to continue...")
  
def worst_courses_by_major_screen(session):
    major = select_major()
    if not major:
        return

    course_ids = get_course_ids_by_major(major["major_id"])
    if not course_ids:
        print("❌ No courses found for this major.")
        input("Press Enter to continue...")
        return

    while True:
        n_input = input("Enter number of worst courses to display: ").strip()

        if not n_input:
            print("❗ Please enter a number.")
            continue
        if not n_input.isdigit():
            print("❗ Invalid number.")
            continue

        n = int(n_input)
        if n <= 0:
            print("❌ Please enter a positive number.")
            continue
        break

    worst_courses = get_worst_courses_by_major(course_ids, limit=n)
    if not worst_courses:
        print("❌ No analytics data available.")
        input("Press Enter to continue...")
        return

    print(f"\n🚨 Worst Courses — {major['major_name']}\n")
    for i, course in enumerate(worst_courses, start=1):
        print(
            f"{i}. Course ID: {course['course_id']} | "
            f"Visits: {course['visits']} | "
            f"Submissions: {course['submissions']} | "
            f"Score: {course['score']}"
        )

    input("\nPress Enter to continue...")
