from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# =========================
# Configuration (edit here)
# =========================
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "my-bucket"
INFLUX_TOKEN = "SUPER_ADMIN_TOKEN_123"
# =========================
# Helpers
# =========================
def _client() -> InfluxDBClient:
    if not INFLUX_TOKEN:
        raise ValueError("INFLUX_TOKEN is required.")
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)


def _ensure_dt(ts: Optional[Union[str, datetime]]) -> datetime:
    """
    Accepts:
      - None => now UTC
      - datetime => used (naive assumed UTC)
      - str ISO 8601 => parsed
    """
    if ts is None:
        return datetime.now(timezone.utc)

    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _flux_time(ts: str) -> str:
    """
    Converts ISO8601 string to a Flux time literal.
    Example:
      "2025-12-20T10:00:00Z" -> time(v: "2025-12-20T10:00:00+00:00")
    """
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # Basic safety: wrap as Flux time(v:"...")
    return f'time(v: "{s}")'


def _stop_clause(stop: Optional[str]) -> str:
    """
    Flux range() accepts:
      range(start: -7d)
      range(start: -7d, stop: time(v:"..."))
    """
    return f", stop: {_flux_time(stop)}" if stop else ""


# ==========================================================
# 1) get_student_activity(studentID)
# ==========================================================
def get_student_activity(
    student_id: str,
    start: str = "-7d",
    stop: Optional[str] = None,
) -> Dict[str, Any]:

    stop_clause = _stop_clause(stop)

    flux = f"""
    // =========================
    // 1) Login count (single row)
    // =========================
    logins =
      from(bucket: "{INFLUX_BUCKET}")
        |> range(start: {start}{stop_clause})
        |> filter(fn: (r) => r._measurement == "student_login_events")
        |> filter(fn: (r) => r.student_id == "{student_id}")
        |> filter(fn: (r) => r._field == "event")
        |> count()
        |> keep(columns: ["_value"])
        |> map(fn: (r) => ({{ kind: "login_count", course_id: "", value: r._value }}))

    // =========================
    // 2) Visits per course
    // =========================
    visits =
      from(bucket: "{INFLUX_BUCKET}")
        |> range(start: {start}{stop_clause})
        |> filter(fn: (r) => r._measurement == "student_course_activity")
        |> filter(fn: (r) => r.student_id == "{student_id}")
        |> filter(fn: (r) => r.activity_type == "view_course")
        |> group(columns: ["course_id"])
        |> count()
        |> map(fn: (r) => ({{ kind: "visits", course_id: r.course_id, value: r._value }}))
        |> keep(columns: ["kind","course_id","value"])

    // =========================
    // 3) Submissions per course
    // =========================
    submissions =
      from(bucket: "{INFLUX_BUCKET}")
        |> range(start: {start}{stop_clause})
        |> filter(fn: (r) => r._measurement == "student_course_activity")
        |> filter(fn: (r) => r.student_id == "{student_id}")
        |> filter(fn: (r) => r.activity_type == "submit")
        |> group(columns: ["course_id"])
        |> count()
        |> map(fn: (r) => ({{ kind: "submissions", course_id: r.course_id, value: r._value }}))
        |> keep(columns: ["kind","course_id","value"])

    union(tables: [logins, visits, submissions])
    """

    client = _client()
    try:
        tables = client.query_api().query(flux, org=INFLUX_ORG)

        login_count = 0
        courses: Dict[str, Dict[str, int]] = {}

        for table in tables:
            for rec in table.records:
                kind = rec.values.get("kind")
                course_id = rec.values.get("course_id") or ""
                value = rec.values.get("value")

                # value might come as float/int; normalize safely
                try:
                    value_int = int(value)
                except Exception:
                    value_int = 0

                if kind == "login_count":
                    login_count = value_int
                    continue

                if not course_id:
                    continue

                courses.setdefault(course_id, {"visit_count": 0, "submitted_assignments": 0})

                if kind == "visits":
                    courses[course_id]["visit_count"] = value_int
                elif kind == "submissions":
                    courses[course_id]["submitted_assignments"] = value_int

        # Optional: sort courses by id for clean output
        courses_sorted = {k: courses[k] for k in sorted(courses.keys())}

        return {
            "student_id": student_id,
            "courses": courses_sorted,
            "login_count": login_count,
        }

    finally:
        client.close()




# ==========================================================
# 2) get_student_course_activity(studentID, courseID)
# ==========================================================
def get_student_course_activity(
    student_id: str,
    course_id: str,
    start: str = "-7d",
    stop: Optional[str] = None,
) -> Dict[str, Any]:

    stop_clause = _stop_clause(stop)

    # =========================
    # 1) Visit count query
    # =========================
    visit_flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}{stop_clause})
      |> filter(fn: (r) =>
          r._measurement == "student_course_activity" and
          r.student_id == "{student_id}" and
          r.course_id == "{course_id}" and
          r.activity_type == "view_course"
      )
      |> count()
    """

    # =========================
    # 2) Submissions query
    # =========================
    submission_flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}{stop_clause})
      |> filter(fn: (r) =>
          r._measurement == "student_course_activity" and
          r.student_id == "{student_id}" and
          r.course_id == "{course_id}" and
          r.activity_type == "submit"
      )
    """

    client = _client()
    try:
        # -------- visits --------
        visit_tables = client.query_api().query(visit_flux, org=INFLUX_ORG)
        visit_count = 0
        for table in visit_tables:
            for rec in table.records:
                visit_count = int(rec.get_value())

        # -------- submissions --------
        submission_tables = client.query_api().query(submission_flux, org=INFLUX_ORG)
        submitted_assignments = []

        for table in submission_tables:
            for rec in table.records:
                assignment_id = rec.values.get("assignment_id")
                submitted_at = rec.get_time()

                if assignment_id and submitted_at:
                    submitted_assignments.append({
                        "assignment_id": assignment_id,
                        "submitted_at": submitted_at,
                    })

        submitted_assignments.sort(key=lambda x: x["submitted_at"])

        return {
            "student_id": student_id,
            "course_id": course_id,
            "visit_count": visit_count,
            "submitted_assignments": submitted_assignments,
        }

    finally:
        client.close()


# ==========================================================
# 3) log_student_login(studentID, loginevent)
# ==========================================================
def log_student_login(
    student_id: str,
    loginevent: Optional[str] = None,  # kept to match your signature
    login_time: Optional[Union[str, datetime]] = None,
) -> None:
    """
    Writes ONE login event to Measurement: student_login_events

    Required in InfluxDB:
      - At least one FIELD must exist.
    Design:
      Tags: student_id
      Fields: event=1 (and optionally login_event string)
      Timestamp: login_time
    """
    t = _ensure_dt(login_time)

    p = Point("student_login_events").tag("student_id", student_id)

    # Fields (required)
    p = p.field("event", 1)
    if loginevent is not None:
        p = p.field("login_event", str(loginevent))

    p = p.time(t, WritePrecision.NS)

    client = _client()
    try:
        client.write_api(write_options=SYNCHRONOUS).write(
            bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p
        )
    finally:
        client.close()


# ==========================================================
# 4) update_weekly_login_count(studentID)
# ==========================================================
def update_weekly_login_count(
    student_id: str,
    write_summary: bool = True,
) -> int:
    """
    Counts logins for the last 7 days for this student.
    Optionally writes a summary point to:
      Measurement: student_login_weekly_summary
      Tags: student_id
      Fields: login_count (int)
      Timestamp: now
    """
    flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -7d)
      |> filter(fn: (r) => r._measurement == "student_login_events")
      |> filter(fn: (r) => r.student_id == "{student_id}")
      |> filter(fn: (r) => r._field == "event")
      |> count()
    """

    client = _client()
    try:
        tables = client.query_api().query(flux, org=INFLUX_ORG)

        count_val = 0
        for table in tables:
            for rec in table.records:
                v = rec.get_value()
                try:
                    count_val += int(v)
                except Exception:
                    pass

        if write_summary:
            now = datetime.now(timezone.utc)
            summary_point = (
                Point("student_login_weekly_summary")
                .tag("student_id", student_id)
                .field("login_count", int(count_val))
                .time(now, WritePrecision.NS)
            )
            client.write_api(write_options=SYNCHRONOUS).write(
                bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=summary_point
            )

        return int(count_val)
    finally:
        client.close()


# ==========================================================
# 5) log_student_event_add_course(studentID, courseID, timestamp)
# ==========================================================
def log_student_event_add_course(
    student_id: str,
    course_id: str,
    timestamp: Optional[Union[str, datetime]] = None,
) -> None:
    """
    Writes to Measurement: student_course_activity
      Tags: student_id, course_id
      Fields: activity_type="add_course"
      Timestamp: activity_time
    """
    t = _ensure_dt(timestamp)

    p = (
        Point("student_course_activity")
        .tag("student_id", student_id)
        .tag("course_id", course_id)
        .tag("activity_type", "add_course")   # ← TAG
        .field("value", 1)                    # ← FIELD
        .time(t, WritePrecision.NS)
    )


    client = _client()
    try:
        client.write_api(write_options=SYNCHRONOUS).write(
            bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p
        )
    finally:
        client.close()


# ==========================================================
# 6) log_student_event_visit_course(studentID, courseID, timestamp)
# ==========================================================
def log_student_event_visit_course(
    student_id: str,
    course_id: str,
    timestamp: Optional[Union[str, datetime]] = None,
) -> None:
    """
    Writes to Measurement: student_course_activity
      Tags: student_id, course_id
      Fields: activity_type="view_course"
      Timestamp: activity_time
    """
    t = _ensure_dt(timestamp)

    p = (
        Point("student_course_activity")
        .tag("student_id", student_id)
        .tag("course_id", course_id)
        .tag("activity_type", "view_course")  # ← TAG
        .field("value", 1)                    # ← FIELD
        .time(t, WritePrecision.NS)
    )


    client = _client()
    try:
        client.write_api(write_options=SYNCHRONOUS).write(
            bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p
        )
    finally:
        client.close()


# ==========================================================
# 7) log_student_event_submit_assignment(studentID, courseID, assignmentID, timestamp)
# ==========================================================
def log_student_event_submit_assignment(
    student_id: str,
    course_id: str,
    assignment_id: str,
    timestamp: Optional[Union[str, datetime]] = None,
) -> None:
    """
    Writes TWO points:
      A) Behavior log in student_course_activity:
         Tags: student_id, course_id, assignment_id
         Fields: activity_type="submit"
         Timestamp: activity_time

      B) Official submission log in course_submission_activity:
         Tags: course_id, assignment_id, student_id
         Fields: submitted=1 (required)
         Timestamp: submission_time
    """
    t = _ensure_dt(timestamp)

    activity_point = (
        Point("student_course_activity")
        .tag("student_id", student_id)
        .tag("course_id", course_id)
        .tag("assignment_id", assignment_id)
        .tag("activity_type", "submit")
        .field("value", 1)
        .time(t, WritePrecision.NS)
    )


    submission_point = (
        Point("course_submission_activity")
        .tag("course_id", course_id)
        .tag("assignment_id", assignment_id)
        .tag("student_id", student_id)
        # Fields (required)
        .field("submitted", 1)
        .time(t, WritePrecision.NS)
    )

    client = _client()
    try:
        client.write_api(write_options=SYNCHRONOUS).write(
            bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=[activity_point, submission_point]
        )
    finally:
        client.close()

def get_top_courses(
    limit: int = 10,
    start: str = "-30d",
    stop: Optional[str] = None,
):
    stop_clause = _stop_clause(stop)

    flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}{stop_clause})
      |> filter(fn: (r) =>
          r._measurement == "student_course_activity" and
          (r.activity_type == "view_course" or r.activity_type == "submit")
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          metric: r.activity_type,
          value: 1
      }}))
      |> group(columns: ["course_id", "metric"])
      |> sum(column: "value")
      |> pivot(
          rowKey: ["course_id"],
          columnKey: ["metric"],
          valueColumn: "value"
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          visits: if exists r.view_course then r.view_course else 0,
          submissions: if exists r.submit then r.submit else 0,
          score:
              (if exists r.view_course then r.view_course else 0)
            + (if exists r.submit then r.submit else 0) * 2
      }}))
      |> group()                      // ✅ مهم جدًا
      |> sort(columns: ["score"], desc: true)
      |> limit(n: {limit})
    """

    client = _client()
    try:
        tables = client.query_api().query(flux, org=INFLUX_ORG)

        results = []
        for table in tables:
            for rec in table.records:
                results.append({
                    "course_id": rec.values.get("course_id"),
                    "visits": int(rec.values.get("visits", 0)),
                    "submissions": int(rec.values.get("submissions", 0)),
                    "score": int(rec.values.get("score", 0)),
                })

        return results

    finally:
        client.close()



def get_worst_courses(
    limit: int = 10,
    start: str = "-30d",
    stop: Optional[str] = None,
):
    stop_clause = _stop_clause(stop)

    flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}{stop_clause})
      |> filter(fn: (r) =>
          r._measurement == "student_course_activity" and
          (r.activity_type == "view_course" or r.activity_type == "submit")
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          metric: r.activity_type,
          value: 1
      }}))
      |> group(columns: ["course_id", "metric"])
      |> sum(column: "value")
      |> pivot(
          rowKey: ["course_id"],
          columnKey: ["metric"],
          valueColumn: "value"
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          visits: if exists r.view_course then r.view_course else 0,
          submissions: if exists r.submit then r.submit else 0,
          score:
              (if exists r.view_course then r.view_course else 0)
            + (if exists r.submit then r.submit else 0) * 2
      }}))
      |> group()
      |> sort(columns: ["score"], desc: false)   // ⬅️ الفرق الأساسي
      |> limit(n: {limit})
    """

    client = _client()
    try:
        tables = client.query_api().query(flux, org=INFLUX_ORG)

        results = []
        for table in tables:
            for rec in table.records:
                results.append({
                    "course_id": rec.values.get("course_id"),
                    "visits": int(rec.values.get("visits", 0)),
                    "submissions": int(rec.values.get("submissions", 0)),
                    "score": int(rec.values.get("score", 0)),
                })

        return results

    finally:
        client.close()

def get_top_courses_by_major(
    course_ids,
    limit: int = 10,
    start: str = "-30d",
    stop: Optional[str] = None,
):
    if not course_ids:
        return []

    stop_clause = _stop_clause(stop)
    ids_array = "[" + ",".join(f'"{cid}"' for cid in course_ids) + "]"

    flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}{stop_clause})
      |> filter(fn: (r) =>
          r._measurement == "student_course_activity" and
          contains(value: r.course_id, set: {ids_array}) and
          (r.activity_type == "view_course" or r.activity_type == "submit")
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          metric: r.activity_type,
          value: 1
      }}))
      |> group(columns: ["course_id", "metric"])
      |> sum(column: "value")
      |> pivot(
          rowKey: ["course_id"],
          columnKey: ["metric"],
          valueColumn: "value"
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          visits: if exists r.view_course then r.view_course else 0,
          submissions: if exists r.submit then r.submit else 0,
          score:
              (if exists r.view_course then r.view_course else 0)
            + (if exists r.submit then r.submit else 0) * 2
      }}))
      |> group()
      |> sort(columns: ["score"], desc: true)
      |> limit(n: {limit})
    """

    client = _client()
    try:
        tables = client.query_api().query(flux, org=INFLUX_ORG)

        results = []
        for table in tables:
            for rec in table.records:
                results.append({
                    "course_id": rec.values.get("course_id"),
                    "visits": int(rec.values.get("visits", 0)),
                    "submissions": int(rec.values.get("submissions", 0)),
                    "score": int(rec.values.get("score", 0)),
                })

        return results

    finally:
        client.close()

def get_worst_courses_by_major(
    course_ids,
    limit: int = 10,
    start: str = "-30d",
    stop: Optional[str] = None,
):
    if not course_ids:
        return []

    stop_clause = _stop_clause(stop)
    ids_array = "[" + ",".join(f'"{cid}"' for cid in course_ids) + "]"

    flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}{stop_clause})
      |> filter(fn: (r) =>
          r._measurement == "student_course_activity" and
          contains(value: r.course_id, set: {ids_array}) and
          (r.activity_type == "view_course" or r.activity_type == "submit")
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          metric: r.activity_type,
          value: 1
      }}))
      |> group(columns: ["course_id", "metric"])
      |> sum(column: "value")
      |> pivot(
          rowKey: ["course_id"],
          columnKey: ["metric"],
          valueColumn: "value"
      )
      |> map(fn: (r) => ({{
          course_id: r.course_id,
          visits: if exists r.view_course then r.view_course else 0,
          submissions: if exists r.submit then r.submit else 0,
          score:
              (if exists r.view_course then r.view_course else 0)
            + (if exists r.submit then r.submit else 0) * 2
      }}))
      |> group()
      |> sort(columns: ["score"], desc: false)
      |> limit(n: {limit})
    """

    client = _client()
    try:
        tables = client.query_api().query(flux, org=INFLUX_ORG)

        results = []
        for table in tables:
            for rec in table.records:
                results.append({
                    "course_id": rec.values.get("course_id"),
                    "visits": int(rec.values.get("visits", 0)),
                    "submissions": int(rec.values.get("submissions", 0)),
                    "score": int(rec.values.get("score", 0)),
                })

        return results

    finally:
        client.close()
