from datetime import date, datetime, timedelta

from agents.notification_calendar import add_calendar_entry, schedule_reminder
from data import store
from tools.registry import get_tool

NAME = "events"


def run(request: str, student_id: str, **ctx) -> dict:
    student = store.get_student(student_id)
    if not student:
        return {"output": None, "error": f"Unknown student {student_id}.", "confidence": 0.2, "trace": "student lookup failed"}

    request_lower = request.lower()
    output: dict = {}
    if "register" in request_lower or "calendar" in request_lower or "remind" in request_lower:
        output["registration"] = _register_flow(request_lower, student, ctx.get("state") or {})
    else:
        output["recommendations"] = _recommend(request_lower, student)
    registration = output.get("registration") or {}
    if "recommendations" in output:
        recs = output["recommendations"]
        confidence = 0.85 if (recs.get("events") or recs.get("clubs")) else 0.6
    else:
        confidence = 0.9 if registration.get("registered") else 0.7
    return {
        "output": output,
        "error": None,
        "confidence": confidence,
        "trace": f"Handled event actions and recommendations for {student.name}.",
    }


def _register_flow(request_lower: str, student, state: dict) -> dict:
    placement = (state.get("results") or {}).get("placement") or {}
    eligible = (placement.get("output") or {}).get("eligible")
    if eligible is False:
        return {"registered": False, "skipped": "Not eligible per placement agent; registration skipped.", "steps": []}
    if state.get("approved") is False:
        return {"registered": False, "skipped": "Registration was declined by the user.", "steps": []}

    event = _find_target_event(request_lower)
    if event is None:
        return {"registered": False, "skipped": "No matching upcoming event found.", "steps": []}

    steps: list[dict] = []
    errors: list[str] = []

    reg = get_tool("registration").run(action="register", student_id=student.id, event_id=event.id)
    if not reg.ok:
        return {"registered": False, "skipped": reg.error, "steps": []}
    steps.append({"tool": "registration", "ok": True, "detail": f"Registered for {event.title} ({event.id})."})

    cal = add_calendar_entry(
        student_id=student.id,
        title=event.title,
        date=event.date,
        start_time=event.start_time,
        location=event.location,
        reminder_before_min=60,
    )
    reminder_at = None
    if cal.get("ok"):
        entry = cal["entry"]
        reminder_at = entry.get("reminder_at")
        steps.append({
            "tool": "calendar",
            "ok": True,
            "detail": f"Added to calendar on {event.date} {event.start_time} "
                      f"with a {entry['reminder_before_min']}-minute reminder.",
        })
    else:
        errors.append(cal["error"])
        steps.append({"tool": "calendar", "ok": False, "detail": cal["error"]})

    if reminder_at:
        notif = schedule_reminder(
            student_id=student.id,
            message=f"Reminder: {event.title} starts in 60 minutes.",
            at=reminder_at,
        )
        if notif.get("ok"):
            steps.append({"tool": "notification", "ok": True, "detail": f"Reminder scheduled for {reminder_at}."})
        else:
            errors.append(notif["error"])
            steps.append({"tool": "notification", "ok": False, "detail": notif["error"]})

    return {"registered": True, "event": event.id, "title": event.title, "steps": steps, "errors": errors}


def _find_target_event(request_lower: str):
    today = date.today()
    events = store.load_events()

    if "tomorrow" in request_lower:
        target = today + timedelta(days=1)
        for event in events:
            if event.date == target.isoformat():
                return event

    for event in events:
        if event.date >= today.isoformat() and any(word in request_lower for word in event.title.lower().split()):
            return event

    upcoming = sorted((e for e in events if e.date >= today.isoformat()), key=lambda e: e.date)
    return upcoming[0] if upcoming else None


def _recommend(request_lower: str, student) -> dict:
    today = date.today().isoformat()
    ai_ml_tags = {"ai", "ml", "llm", "python", "data science", "open-innovation"}

    def matches(event) -> bool:
        if event.date < today:
            return False
        tags = {t.lower() for t in event.tags}
        if "machine learning" in request_lower or " ml" in request_lower or "ai" in request_lower:
            return bool(ai_ml_tags & tags)
        if "workshop" in request_lower:
            return event.type == "workshop"
        if "hackathon" in request_lower:
            return event.type == "hackathon"
        return bool(ai_ml_tags & tags)

    events = [
        {
            "id": e.id,
            "title": e.title,
            "type": e.type,
            "date": e.date,
            "start": e.start_time,
            "location": e.location,
            "tags": e.tags,
        }
        for e in store.load_events()
        if matches(e)
    ]

    interest_tags = {t.lower() for t in student.interests}
    keywords = {w for w in request_lower.replace(",", " ").split() if len(w) > 1}
    clubs = []
    for club in store.load_clubs():
        tags = {t.lower() for t in club.tags}
        score = len(interest_tags & tags) + len(keywords & tags)
        if score > 0:
            clubs.append({"id": club.id, "name": club.name, "tags": club.tags, "meeting": club.meeting, "score": score})
    clubs.sort(key=lambda c: c["score"], reverse=True)

    return {"events": events, "clubs": clubs}
