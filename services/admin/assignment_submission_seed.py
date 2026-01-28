import random

from services.student_information_service import (
    enrollments_col,
    assignments_col
)

from services.course_activity_service import (
    create_answer_document,
     update_grades,
)
from services.analytics_service import (
    log_student_event_submit_assignment
)



def seed_assignment_submissions():
    print("\n📝 Seeding assignment submissions & grades (WITH INFLUX)...\n")

    enrollments = list(enrollments_col.find({}, {"_id": 0}))
    print(f"📚 Enrollments loaded: {len(enrollments)}")

    total_submitted = 0
    total_graded = 0
    total_skipped = 0

    for enrollment in enrollments:
        student_id = enrollment["student_id"]
        course_id = enrollment["course_id"]

        assignments = list(assignments_col.find(
            {"course_id": course_id},
            {"_id": 0, "assignment_id": 1, "max_grade": 1}
        ))

        for assignment in assignments:
            assignment_id = assignment["assignment_id"]
            max_grade = assignment.get("max_grade", 100)

            roll = random.random()

            # ❌ 20% NOT SUBMITTED
            if roll < 0.2:
                total_skipped += 1
                continue

            # ✅ SUBMITTED
            answer_text = random.choice([
                "Solved all questions.",
                "Submitted assignment.",
                "Please find my solution.",
                "My answers are attached.",
                "Completed to the best of my ability."
            ])

            answerData = {
                "student_id": student_id,
                "text": answer_text
            }

            # MongoDB submission
            create_answer_document(
                student_id,
                assignment_id,
                answerData
            )

            # 🔥🔥🔥 InfluxDB submit event (THE FIX)
            log_student_event_submit_assignment(
                student_id,
                course_id,
                assignment_id
            )

            total_submitted += 1

            # 🧮 60% GRADED
            if roll < 0.8:
                grade = round(
                    random.uniform(max_grade * 0.4, max_grade),
                    2
                )
                grade = min(grade, max_grade)

                update_grades(
                    assignment_id,
                    student_id,
                    grade
                )
                total_graded += 1

    print("\n✅ Assignment submissions seeding completed")
    print(f"📝 Submitted : {total_submitted}")
    print(f"🧮 Graded    : {total_graded}")
    print(f"❌ Skipped   : {total_skipped}\n")
