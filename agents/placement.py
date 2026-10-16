from agents.academic import run as academic_run
from data import store
from data.models import Placement, Student

NAME = "placement"


def run(request: str, student_id: str, **ctx) -> dict:
    student = store.get_student(student_id)
    if not student:
        return {"output": None, "error": f"Unknown student {student_id}.", "confidence": 0.2, "trace": "student lookup failed"}

    drives = [d for d in store.load_placements() if d.status in ("open", "upcoming")]
    company = _match_company(request.lower(), drives)

    if company is not None:
        evaluation = _evaluate(student, company)
        output = {
            **evaluation,
            "recommendation": "Crack the Technical Interview (E101)" if evaluation["eligible"] else None,
        }
        if not evaluation["eligible"]:
            output["a2a"] = _ask_academic(student, company)
    else:
        output = _general_result(student, drives)

    trace = f"Evaluated {student.name} against placement drives: " \
            f"{'eligible' if output['eligible'] else 'not eligible'}."
    if output.get("a2a"):
        trace += f" Messaged {output['a2a']['to']} agent for improvement recommendations."
    confidence = 0.95 if company is not None else 0.8
    return {
        "output": output,
        "error": None,
        "confidence": confidence,
        "trace": trace,
    }


def _ask_academic(student: Student, drive: Placement) -> dict:
    """A2A: ask the academic agent which courses/actions would improve eligibility."""
    reply = academic_run(
        f"Recommend courses and actions to improve placement eligibility.",
        student.id,
    )
    recs = (((reply or {}).get("output") or {}).get("improvement_recommendations") or {}).get("recommendations", [])
    return {
        "from": "placement",
        "to": "academic",
        "message": f"{student.name} is not eligible for {drive.company}. Recommend courses/actions to improve eligibility.",
        "reply": recs,
    }


def _match_company(request_lower: str, drives: list[Placement]) -> Placement | None:
    for drive in drives:
        if drive.company.lower() in request_lower:
            return drive
    return None


def _general_result(student: Student, drives: list[Placement]) -> dict:
    evaluations = [_evaluate(student, drive) for drive in drives]
    matched = [e for e in evaluations if e["eligible"]]
    eligible = bool(matched)
    return {
        "internship": "General placement drive",
        "eligible": eligible,
        "checks": [
            {
                "criterion": "upcoming drives",
                "met": eligible,
                "detail": f"Qualifies for {len(matched)} of {len(drives)} open/upcoming drives"
                          + (f" — best match {matched[0]['drive']['company']}." if matched else ""),
            }
        ],
        "drives": [e["drive"] for e in matched],
        "recommendation": None,
    }


def _evaluate(student: Student, drive: Placement) -> dict:
    checks = [
        ("year", student.year in (3, 4), f"Year 3 or 4 (student: Year {student.year})"),
        ("branch", student.department in drive.eligible_departments,
         f"Branch in {drive.eligible_departments} (student: {student.department})"),
        ("cgpa", student.cgpa >= drive.eligibility_cgpa,
         f"CGPA >= {drive.eligibility_cgpa} (student: {student.cgpa})"),
        ("backlogs", student.backlogs == 0, f"No active backlogs (student: {student.backlogs})"),
        ("attendance", student.attendance_pct >= 75,
         f"Attendance >= 75% (student: {student.attendance_pct}%)"),
    ]
    eligible = all(met for _, met, _ in checks)
    label = "Google Summer Internship" if drive.company.lower() == "google" else f"{drive.company} {drive.role}"
    return {
        "internship": label,
        "eligible": eligible,
        "checks": [{"criterion": c, "met": m, "detail": d} for c, m, d in checks],
        "drive": {
            "id": drive.id,
            "company": drive.company,
            "role": drive.role,
            "package_lpa": drive.package_lpa,
            "drive_date": drive.drive_date,
            "application_deadline": drive.application_deadline,
            "status": drive.status,
        },
    }
