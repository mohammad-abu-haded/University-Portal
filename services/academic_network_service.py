from typing import List, Dict, Optional, Any
import os
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


# Neo4j Connection 
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "test1234")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
def write(query: str,) -> None:
    def _tx(tx):
        tx.run(query)
    with driver.session() as session:
        session.execute_write(_tx)
def read(query: str):
    def _tx(tx):
        return list(tx.run(query))
    with driver.session() as session:
        return session.execute_read(_tx)




# Nodes creation 
def create_student_node(studentID: str, name: str) -> dict:
    try:
        write(f"MERGE (s:Student {{id:'{studentID}'}}) SET s.name = '{name}'")
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}


def create_instructor_node(instructorID: str) -> dict:
    try:
        write(f"MERGE (i:Instructor {{id:'{instructorID}'}})")
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}


def create_course_node(courseID: str) -> dict:
    try:
        write(f"MERGE (c:Course {{id:'{courseID}'}}) ")
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}


def create_assignment_node(assignmentID: str, assignment_title: str) -> dict:
    try:
        write(
            f"MERGE (a:Assignment {{id:'{assignmentID}'}}) "
            f"SET a.title = '{assignment_title}'"
        )
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}






# Relationships
def link_instructor_to_course(
    instructorID: str,
    courseID: str,
) -> dict:
    try:
        create_instructor_node(instructorID)
        create_course_node(courseID)

        write(
            f"MATCH (i:Instructor {{id:'{instructorID}'}}), (c:Course {{id:'{courseID}'}}) "
            f"MERGE (i)-[:TEACHES]->(c)"
        )
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}


def link_student_to_course(
    studentID: str,
    studentName: str,
    courseID: str,
) -> dict:
    try:
        create_student_node(studentID,studentName)
        create_course_node(courseID)

        write(
            f"MATCH (s:Student {{id:'{studentID}'}}), (c:Course {{id:'{courseID}'}}) "
            f"MERGE (s)-[:ENROLLED_IN]->(c)"
        )
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}


def link_assignment_to_course(
    assignmentID: str,
    courseID: str,
    assignment_title: str

) -> dict:
    try:
        create_assignment_node(assignmentID, assignment_title)
        create_course_node(courseID)

        write(
            f"MATCH (a:Assignment {{id:'{assignmentID}'}}), (c:Course {{id:'{courseID}'}}) "
            f"MERGE (a)-[:BELONGS_TO]->(c)"
        )
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}


def link_student_to_assignment(
    studentID: str,
    studentName: str,
    assignmentID: str,
    assignment_title: str
) -> dict:
    try:
        create_student_node(studentID, studentName)
        create_assignment_node(assignmentID, assignment_title)

        write(
            f"MATCH (s:Student {{id:'{studentID}'}}), (a:Assignment {{id:'{assignmentID}'}}) "
            f"MERGE (s)-[:SUBMITTED]->(a)"
        )
        return {"success": True}
    except Neo4jError as e:
        return {"error": str(e)}




# Queries
def get_instructor_courses_ids(instructorID: str) -> list[str]:
    try:
        rows = read(
            f"MATCH (i:Instructor {{id:'{instructorID}'}})-[:TEACHES]->(c:Course) "
            f"RETURN c.id"
        )
        return [row["c.id"] for row in rows]

    except Neo4jError:
        return []

    

def get_student_enrolled_course_ids(studentID: str) -> list[str]:
    try:
        rows = read(
            f"MATCH (s:Student {{id:'{studentID}'}})-[:ENROLLED_IN]->(c:Course) "
            f"RETURN c.id"
        )
        return [row["c.id"] for row in rows]

    except Neo4jError:
        return []



def get_course_students(courseID: str) -> dict:
    try:
        rows = read(
            f"MATCH (s:Student)-[:ENROLLED_IN]->(c:Course {{id:'{courseID}'}}) "
            f"RETURN s.id, s.name"
        )

        students = [
            {
                "studentID": row["s.id"],
                "studentName": row["s.name"]
            }
            for row in rows
        ]

        return {"students": students}

    except Neo4jError as e:
        return {"error": str(e)}



def get_course_assignments(courseID: str) -> dict:
    try:
        rows = read(
            f"MATCH (a:Assignment)-[:BELONGS_TO]->(c:Course {{id:'{courseID}'}}) "
            f"RETURN a.id, a.title"
        )

        assignments = [
            {
                "assignmentID": row["a.id"],
                "assignmentTitle": row["a.title"]
            }
            for row in rows
        ]

        return {"assignments": assignments}

    except Neo4jError as e:
        return {"error": str(e)}



def get_student_network(studentID: str) -> dict:
    try:
        rows = read(
            f"""
            MATCH (s:Student {{id:'{studentID}'}})-[:ENROLLED_IN]->(c:Course)
            <-[:ENROLLED_IN]-(other:Student)
            RETURN c.id AS courseID, other.id AS studentID, other.name AS studentName
            """
        )

        network = [
            {
                "courseID": row["courseID"],
                "studentID": row["studentID"],
                "studentName": row["studentName"]
            }
            for row in rows
        ]

        return {"network": network}

    except Neo4jError as e:
        return {"error": str(e)}




def get_student_course_network(studentID: str, courseID: str) -> dict:
    try:
        rows = read(
            f"""
            MATCH (s:Student {{id:'{studentID}'}})-[:ENROLLED_IN]->(c:Course {{id:'{courseID}'}})
            OPTIONAL MATCH (i:Instructor)-[:TEACHES]->(c)
            OPTIONAL MATCH (other:Student)-[:ENROLLED_IN]->(c)
            WHERE other.id <> s.id
            RETURN
                c.id AS courseID,
                s.id AS studentID,
                s.name AS studentName,
                collect(DISTINCT {{id: i.id}}) AS instructors,
                collect(
                    DISTINCT {{
                        id: other.id,
                        name: other.name
                    }}
                ) AS students
            """
        )

        if not rows:
            return {
                "course_id": courseID,
                "center_student": None,
                "instructors": [],
                "students": []
            }

        r = rows[0]

        return {
            "course_id": r["courseID"],

            "center_student": {
                "id": r["studentID"],
                "name": r["studentName"]
            },

            "instructors": [
                i for i in r["instructors"]
                if i.get("id") is not None
            ],

            "students": [
                s for s in r["students"]
                if s.get("id") is not None
            ]
        }

    except Neo4jError as e:
        return {"error": str(e)}

