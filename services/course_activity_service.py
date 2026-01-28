from typing import Any, List, Optional
import redis
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
import json

from services.academic_network_service import get_course_students

mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["university_portal"]
assignments_col: Collection = mongo_db["assignments"]
courses_col = mongo_db["courses"]
assignments_col.create_index([("assignment_id", 1)], unique=True)
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

DEFAULT_CACHE_TTL = 600 


# Redis Key Helpers

def _k_instructor_courses(instructor_id: str) -> str:
    return f"instructor_courses:{instructor_id}"

def _k_available_courses(student_id: str) -> str:
    return f"available_courses:{student_id}"

def _k_instructor_course_assignments(instructor_id: str) -> str:
    return f"instructor_course_assignments:{instructor_id}"

def _k_course_assignments(course_id: str) -> str:
    return f"assignment_list:{course_id}"

def _k_enrolled_students(course_id: str) -> str:
    return f"enrolled_students:{course_id}"

def _k_student_courses(student_id: str) -> str:
    return f"student_courses:{student_id}"

def _k_student_course_details(student_id: str, course_id: str) -> str:
    return f"student_course_details:{student_id}:{course_id}"

def _k_pending_tasks(student_id: str) -> str:
    return f"pending_tasks:{student_id}"


# Redis Invalidation Functions

def invalidate_instructor_courses_cache(instructorID: str) -> dict:
    redis_client.delete(_k_instructor_courses(instructorID))
    return {"success": True}

def invalidate_available_courses_cache() -> dict:
    keys = redis_client.keys("available_courses:*")
    if keys:
        redis_client.delete(*keys)
    return {"success": True, "deleted_keys": len(keys)}

def invalidate_course_details_cache(courseID: str) -> dict:
    pattern = _k_student_course_details("*", courseID)

    cursor = 0
    deleted = 0

    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match=pattern)
        if keys:
            redis_client.delete(*keys)
            deleted += len(keys)

        if cursor == 0:
            break

    return {
        "success": True,
        "deleted_keys": deleted
    }

def invalidate_student_available_courses_cache(student_id) -> dict:
    redis_client.delete(_k_available_courses(student_id)) 
    return {"success": True}

def invalidate_instructor_course_assignments_cache(courseID: str) -> dict:
    redis_client.delete(_k_course_assignments(courseID))
    return {"success": True}

def invalidate_student_course_details_cache(studentID: str, courseID: str) -> dict:
    redis_client.delete(_k_student_course_details(studentID, courseID))
    return {"success": True}

def invalidate_enrolled_students_cache(courseID: str) -> dict:
    redis_client.delete(_k_enrolled_students(courseID))
    return {"success": True}

def invalidate_student_courses_cache(studentID: str) -> dict:
    redis_client.delete(_k_student_courses(studentID))
    return {"success": True}

def invalidate_student_pending_task_cache(studentID: str) -> dict:
    redis_client.delete(_k_pending_tasks(studentID))
    return {"success": True}

def invalidate_pending_tasks_cache_for_course(courseID: str):
    try:
        enrolled_students = get_course_students(courseID)
        students = enrolled_students.get("students", [])

        for student in students:
            student_id = student["studentID"]
            key = _k_pending_tasks(student_id)
            redis_client.delete(key) 

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Redis Cache Functions

def cache_instructor_courses(instructorID: str, courses: List[dict]) -> dict:
    key = _k_instructor_courses(instructorID)
    redis_client.set(key, json.dumps(courses))
    redis_client.expire(key, DEFAULT_CACHE_TTL)
    return {"success": True}

def cache_course_assignments(courseID: str, assignments: List[dict]) -> dict:
    key = _k_course_assignments(courseID)
    redis_client.set(key, json.dumps(assignments))
    redis_client.expire(key, DEFAULT_CACHE_TTL)
    return {"success": True}

def cache_enrolled_students(courseID: str, students: List[dict]) -> dict:
    key = _k_enrolled_students(courseID)
    redis_client.set(key, json.dumps(students))
    redis_client.expire(key, DEFAULT_CACHE_TTL)
    return {"success": True}

def cache_available_courses(studentID: str, courses: List[dict]) -> dict:
    key = _k_available_courses(studentID)
    redis_client.set(key, json.dumps(courses))
    redis_client.expire(key, DEFAULT_CACHE_TTL)
    return {"success": True}

def cache_student_courses(studentID: str, courses: List[dict]) -> dict:
    key = _k_student_courses(studentID)
    redis_client.set(key, json.dumps(courses))
    redis_client.expire(key, DEFAULT_CACHE_TTL)
    return {"success": True}

def cache_student_course_details(studentID: str, courseID: str, courseDetails: dict) -> dict:
    key = _k_student_course_details(studentID, courseID)
    redis_client.set(key, json.dumps(courseDetails))
    redis_client.expire(key, DEFAULT_CACHE_TTL)
    return {"success": True}

def cache_pending_tasks(studentID: str, tasks: List[dict]) -> dict:
    key = _k_pending_tasks(studentID)
    redis_client.set(key, json.dumps(tasks))
    redis_client.expire(key, DEFAULT_CACHE_TTL)
    return {"success": True}


import json
from typing import List, Optional

def get_cached_instructor_courses(instructorID: str) -> Optional[List[dict]]:
    key = _k_instructor_courses(instructorID)
    data = redis_client.get(key)
    if not data:
        return None
    return json.loads(data)

def get_cached_course_assignments(courseID: str) -> Optional[List[dict]]:
    key = _k_course_assignments(courseID)
    data = redis_client.get(key)
    if not data:
        return None
    return json.loads(data)

def get_cached_enrolled_students(courseID: str) -> Optional[List[dict]]:
    key = _k_enrolled_students(courseID)
    data = redis_client.get(key)
    if not data:
        return None
    return json.loads(data)

def get_cached_available_courses(studentID: str) -> Optional[List[dict]]:
    key = _k_available_courses(studentID)
    data = redis_client.get(key)
    if not data:
        return None
    return json.loads(data)

def get_cached_student_courses(studentID: str) -> Optional[List[dict]]:
    key = _k_student_courses(studentID)
    data = redis_client.get(key)
    if not data:
        return None
    return json.loads(data)

def get_cached_student_course_details(studentID: str, courseID: str) -> Optional[dict]:
    key = _k_student_course_details(studentID, courseID)
    data = redis_client.get(key)
    if not data:
        return None
    return json.loads(data)

def get_cached_pending_tasks(studentID: str) -> Optional[List[dict]]:
    key = _k_pending_tasks(studentID)
    data = redis_client.get(key)
    if not data:
        return None
    return json.loads(data)


# MongoDB Functions

def create_assignment(courseID: str, assignmentData: dict) -> dict:
    """
    assignmentData must include:
    - assignment_id
    - title
    - description
    - deadline
    - max_grade
    """
    try:
        doc = {
            "course_id": courseID,
            **assignmentData,
            "grades": [],
            "answer_text": []
        }
        assignments_col.insert_one(doc)
        return {"success": True}
    except PyMongoError as e:
        return {"success": False, "error": str(e)}


def get_answer(studentID: str, assignmentID: str) -> dict:
    assignment = assignments_col.find_one(
        {"assignment_id": assignmentID},
        {"_id": 0, "answer_text": 1, "max_grade": 1, "grades": 1}
    )

    if not assignment:
        return {"success": False, "answer": None, "grade": None}

    student_answer = None
    for ans in assignment.get("answer_text", []):
        if ans["student_id"] == studentID:
            student_answer = ans["text"]
            break

    student_grade = None
    for g in assignment.get("grades", []):
        if g["student_id"] == studentID:
            student_grade = g["grade"]
            break

    if student_answer is not None or student_grade is not None:
        return {
            "success": True,
            "answer": student_answer,
            "grade": student_grade,
            "maxGrade": assignment.get("max_grade", "00")
        }

    return {"success": False, "answer": None, "grade": None, "maxGrade": assignment.get("max_grade", "00")}



def update_grades(assignmentID: str, studentID: str, grade: float) -> dict:
    try:
        assignments_col.update_one(
            {"assignment_id": assignmentID},
            {"$pull": {"grades": {"student_id": studentID}}}
        )

        assignments_col.update_one(
            {"assignment_id": assignmentID},
            {"$push": {"grades": {"student_id": studentID, "grade": grade}}}
        )

        return {"success": True}
    except PyMongoError as e:
        return {"success": False, "error": str(e)}


def create_answer_document(studentID: str, assignmentID: str, answerData: dict) -> dict:
    """
    answerData must include:
    - student_id
    - text
    """
    try:
        assignments_col.update_one(
            {"assignment_id": assignmentID},
            {"$pull": {"answer_text": {"student_id": studentID}}}
        )

        assignments_col.update_one(
            {"assignment_id": assignmentID},
            {"$push": {
                "answer_text": {
                    "student_id": studentID,
                    "text": answerData["text"]
                }
            }}
        )

        return {"success": True}
    except PyMongoError as e:
        return {"success": False, "error": str(e)}


def get_pending_assignments_for_courses(studentID: str, courseIDs: List[str]) -> dict:
    try:
        assignments = list(assignments_col.find(
            {"course_id": {"$in": courseIDs}},
            {"_id": 0, "assignment_id": 1, "course_id": 1, "title": 1, "description": 1, "deadline": 1, "max_grade": 1, "answer_text": 1}
        ))

        pending = []

        for a in assignments:
            submitted_students = {ans["student_id"] for ans in a.get("answer_text", [])}
            if studentID not in submitted_students:
                course = courses_col.find_one(
                    {"course_id": a["course_id"]},
                    {"_id": 0, "details.course_name": 1} 
                )
                course_name = course["details"]["course_name"] if course and "details" in course else "Unknown Course"

                pending.append({
                    "course_name": course_name,
                    "assignment_id": a["assignment_id"],
                    "title": a["title"],
                    "description": a["description"],
                    "deadline": a["deadline"],
                    "max_grade": a["max_grade"]
                })

        return {"success": True, "tasks": pending}
    except PyMongoError as e:
        return {"success": False, "error": str(e)}

