from services.academic_network_service import driver

def create_indexes():
    with driver.session() as session:
        session.run(
            "CREATE INDEX student_id IF NOT EXISTS FOR (s:Student) ON (s.id)"
        )
        session.run(
            "CREATE INDEX instructor_id IF NOT EXISTS FOR (i:Instructor) ON (i.id)"
        )
        session.run(
            "CREATE INDEX course_id IF NOT EXISTS FOR (c:Course) ON (c.id)"
        )
        session.run(
            "CREATE INDEX assignment_id IF NOT EXISTS FOR (a:Assignment) ON (a.id)"
        )

    print("✅ Neo4j indexes created (or already exist)")
create_indexes()
