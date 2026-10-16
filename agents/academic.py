from datetime import datetime, timedelta

from data import store

NAME = "academic"
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def run(request: str, student_id: str, **ctx) -> dict:
    student = store.get_student(student_id)
    if not student:
        return {"output": None, "error": f"Unknown student {student_id}.", "confidence": 0.2, "trace": "student lookup failed"}

    day, classes, day_note = _classes_for_today()
    attendance = student.attendance_pct
    if attendance >= 75:
        eligibility, note = "eligible", "Meets the 75% minimum attendance requirement for exams."
    elif attendance >= 60:
        eligibility, note = "makeup_eligible", (
            "Below 75% but above 60%: may apply for a makeup examination under the Examination Regulations."
        )
    else:
        eligibility, note = "ineligible", (
            "Below 60%: disqualified from writing exams this semester; courses must be repeated."
        )

    output = {
        "student": student.name,
        "day": day,
        "classes": classes,
        "attendance_pct": attendance,
        "eligibility": eligibility,
        "note": note,
        "day_note": day_note,
    }
    faculty = _faculty_info(request.lower(), student)
    if faculty is not None:
        output["faculty"] = faculty
    improvement = _improvement_recommendations(request.lower(), student)
    if improvement is not None:
        output["improvement_recommendations"] = improvement

    return {
        "output": output,
        "error": None,
        "confidence": 0.9 if classes else 0.6,
        "trace": f"Computed {len(classes)} classes for {day} and attendance eligibility for {student.name}.",
    }


def _faculty_info(request_lower: str, student) -> dict | None:
    if not any(k in request_lower for k in ("faculty", "professor", "teacher", "instructor", "who teaches", "office")):
        return None

    all_faculty = store.load_faculty()

    def matches(f) -> bool:
        haystack = f"{f.name} {f.department} {f.designation}".lower()
        return any(len(token) > 3 and token in haystack
                   for token in request_lower.replace(",", " ").split())

    matched = [f for f in all_faculty if matches(f)]
    if not matched:
        matched = [f for f in all_faculty if f.department == student.department]
    return {
        "type": "faculty",
        "faculty": [
            {"id": f.id, "name": f.name, "department": f.department,
             "designation": f.designation, "email": f.email, "office": f.office}
            for f in matched
        ],
    }


def _improvement_recommendations(request_lower: str, student) -> dict | None:
    if not any(k in request_lower for k in ("recommend", "improve", "eligibility")):
        return None
    recs = []
    if student.cgpa < 8.0:
        recs.append("Enroll in a DSA elective (CS305) to lift your CGPA toward the 8.0 threshold.")
    if student.attendance_pct < 75:
        recs.append(f"Raise attendance above 75% — current level ({student.attendance_pct}%) is below the cutoff.")
    if student.backlogs > 0:
        recs.append("Clear all active backlogs; most placement drives require zero backlogs.")
    if not recs:
        recs.append("Maintain your CGPA and attendance; add AI/ML electives to strengthen your profile.")
    return {"type": "improvement_recommendations", "recommendations": recs}


def _classes_for_today() -> tuple[str, list[dict], str | None]:
    """Return (day_label, classes, note). On weekends, roll forward to next weekday with classes."""
    today = datetime.now()
    courses = {c.code: c.title for c in store.load_courses()}
    timetable = store.load_timetable()

    for offset in range(0, 7):
        day = (today + timedelta(days=offset)).strftime("%A")
        slots = [s for s in timetable if s.day == day]
        if not slots:
            continue
        classes = [
            {
                "code": s.code,
                "title": courses.get(s.code, s.code),
                "start": s.start,
                "end": s.end,
                "room": s.room,
                "instructor": s.instructor,
            }
            for s in slots
        ]
        note = None
        if offset > 0:
            note = f"No classes on {today.strftime('%A')}; showing next scheduled day ({day})."
        return day, classes, note

    return today.strftime("%A"), [], "No timetable slots found."
