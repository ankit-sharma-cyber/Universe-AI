from datetime import datetime, timedelta

from tools.registry import get_tool

NAME = "notification_calendar"


def run(request: str, student_id: str, **ctx) -> dict:
    request_lower = request.lower()
    output: dict = {}

    if "calendar" in request_lower or "schedule" in request_lower or "add" in request_lower:
        output["calendar"] = _calendar_actions(request_lower, student_id)

    if "remind" in request_lower or "reminder" in request_lower or "notification" in request_lower:
        output["reminders"] = _reminder_actions(request_lower, student_id)

    if not output:
        return {
            "output": None,
            "error": "Could not identify a calendar or reminder action.",
            "confidence": 0.5,
            "trace": "no matching action detected",
        }

    return {"output": output, "error": None, "confidence": 0.9, "trace": f"Handled calendar/notification actions for {student_id}."}


def add_calendar_entry(
    student_id: str,
    title: str,
    date: str | None = None,
    start_time: str | None = None,
    location: str = "Campus",
    reminder_before_min: int = 60,
) -> dict:
    """Single owner of the calendar tool's 'add' action."""
    tool = get_tool("calendar")
    result = tool.run(
        action="add",
        student_id=student_id,
        title=title,
        date=date,
        start_time=start_time,
        location=location,
        reminder_before_min=reminder_before_min,
    )
    if not result.ok:
        return {"ok": False, "error": result.error}
    return {"ok": True, "entry": result.data.get("entry")}


def schedule_reminder(student_id: str, message: str, at: str) -> dict:
    """Single owner of the notification tool's 'schedule' action."""
    tool = get_tool("notification")
    result = tool.run(action="schedule", student_id=student_id, message=message, at=at)
    if not result.ok:
        return {"ok": False, "error": result.error}
    return {"ok": True, "reminder": result.data.get("reminder")}


def _calendar_actions(request_lower: str, student_id: str) -> dict:
    tool = get_tool("calendar")
    if "list" in request_lower or "show" in request_lower or "view" in request_lower:
        result = tool.run(action="list", student_id=student_id)
        if not result.ok:
            return {"ok": False, "error": result.error}
        return {"ok": True, "events": result.data.get("events", [])}

    title = "Campus Event"
    if "workshop" in request_lower:
        title = "Workshop"
    elif "hackathon" in request_lower:
        title = "Hackathon"
    elif "exam" in request_lower:
        title = "Exam"

    result = add_calendar_entry(student_id=student_id, title=title)
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error")}
    return {"ok": True, "added": result.get("entry")}


def _reminder_actions(request_lower: str, student_id: str) -> dict:
    tool = get_tool("notification")
    if "list" in request_lower or "show" in request_lower or "view" in request_lower:
        result = tool.run(action="list", student_id=student_id)
        if not result.ok:
            return {"ok": False, "error": result.error}
        return {"ok": True, "reminders": result.data.get("reminders", [])}

    message = "Campus reminder"
    if "workshop" in request_lower:
        message = "Reminder: Workshop starts in 60 minutes."
    elif "hackathon" in request_lower:
        message = "Reminder: Hackathon starts in 60 minutes."
    elif "exam" in request_lower:
        message = "Reminder: Exam starts in 60 minutes."

    at = (datetime.now() + timedelta(hours=1)).isoformat()
    result = schedule_reminder(student_id=student_id, message=message, at=at)
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error")}
    return {"ok": True, "scheduled": result.get("reminder")}
