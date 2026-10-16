from data import store
from llm.client import complete
from tools.registry import get_tool

NAME = "communication"


def run(request: str, student_id: str, **ctx) -> dict:
    student = store.get_student(student_id)
    if not student:
        return {"output": None, "error": f"Unknown student {student_id}.", "confidence": 0.2, "trace": "student lookup failed"}

    request_lower = request.lower()
    to = "hod@campus.edu"
    subject, body, draft_source = _compose(request, request_lower, student, ctx.get("state") or {})

    action = "send" if "send" in request_lower else "draft"
    result = get_tool("email").run(action=action, to=to, subject=subject, body=body)
    if not result.ok:
        return {"output": None, "error": result.error, "confidence": 0.4, "trace": "email tool failed"}

    return {
        "output": {
            "to": to,
            "subject": subject,
            "body": body,
            "status": result.data.get("status"),
            "draft_source": draft_source,
        },
        "error": None,
        "confidence": 0.9,
        "trace": f"{action.title()}ed an email to {to} for {student.name} ({draft_source}).",
    }


def _compose(request: str, request_lower: str, student, state: dict) -> tuple[str, str, str]:
    academic = ((state.get("results") or {}).get("academic") or {}).get("output") or {}
    attendance = academic.get("attendance_pct", student.attendance_pct)
    eligibility = academic.get("eligibility")

    if "makeup" in request_lower or "permission" in request_lower:
        subject = "Request for Permission — Makeup Examination"
        template_body = _makeup_template(student, attendance, eligibility)
    else:
        subject = "Enquiry from Student"
        template_body = (
            f"Respected {student.department} department office,\n\n"
            f"I, {student.name} ({student.id}), would like to inquire about the following: {request}\n\n"
            f"Thanking you,\n{student.name}\n{student.email}"
        )

    llm_body = complete(
        f"Write a polite formal email body for this campus request.\n"
        f"Student: {student.name} ({student.id}), {student.department}, Year {student.year}, "
        f"email {student.email}, attendance {attendance}%.\n"
        f"Request: {request}\n"
        f"Suggested subject: {subject}\n"
        f"Return only the email body text, no subject line.",
        system="You draft concise formal emails for university students. No markdown.",
        max_tokens=400,
    )
    if llm_body:
        return subject, llm_body, "llm"
    return subject, template_body, "template"


def _makeup_template(student, attendance, eligibility) -> str:
    if attendance < 75:
        shortfall = f"My current attendance is {attendance}%, which falls below the required 75%."
    else:
        shortfall = (
            f"My current attendance is {attendance}%; although I meet the attendance "
            f"requirement, I would like to appear for a makeup examination due to [valid reason]."
        )
    eligibility_line = f" System status: {eligibility}." if eligibility else ""
    return (
        f"Respected Head of Department,\n\n"
        f"I, {student.name} ({student.id}, {student.department}, Year {student.year}), am writing to "
        f"respectfully request permission to appear for a makeup examination. {shortfall}"
        f"{eligibility_line} "
        f"I would be grateful if you would consider my request.\n\n"
        f"Thanking you,\n{student.name}\n{student.email}"
    )
