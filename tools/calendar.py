from datetime import datetime, timedelta
from typing import Any

from tools.base import BaseTool, ToolResult

CALENDAR: dict[str, list[dict[str, Any]]] = {}


def _now() -> datetime:
    return datetime.now()


class CalendarTool(BaseTool):
    name = "calendar"
    description = "Add events to a student's calendar, optionally with a reminder before the event."

    def run(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "add")
        if action == "list":
            return self._list(kwargs.get("student_id"))
        return self._add(kwargs)

    def _add(self, kwargs: dict[str, Any]) -> ToolResult:
        guarded = self._guard()
        if guarded:
            return guarded
        student_id = kwargs.get("student_id")
        title = kwargs.get("title")
        if not student_id or not title:
            return ToolResult.failure("calendar.add requires 'student_id' and 'title'.")
        entry = {
            "student_id": student_id,
            "title": title,
            "date": kwargs.get("date"),
            "start_time": kwargs.get("start_time"),
            "location": kwargs.get("location"),
            "reminder_before_min": kwargs.get("reminder_before_min"),
        }
        reminder_min = kwargs.get("reminder_before_min")
        if reminder_min:
            event_dt = self._event_dt(entry["date"], entry["start_time"])
            entry["reminder_at"] = (event_dt - timedelta(minutes=int(reminder_min))).isoformat()
        real = self._real_post("CALENDAR_API_URL", "CALENDAR_API_KEY", {"action": "add", **entry})
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"calendar external call failed: {real.get('error')}")
            entry = real.get("entry", entry)
            return ToolResult.success(entry=entry, calendar_size=real.get("calendar_size", 1))
        if reminder_min:
            event_dt = self._event_dt(entry["date"], entry["start_time"])
            entry["reminder_at"] = (event_dt - timedelta(minutes=int(reminder_min))).isoformat()
            entry["reminder_before_min"] = int(reminder_min)
        CALENDAR.setdefault(student_id, []).append(entry)
        return ToolResult.success(entry=entry, calendar_size=len(CALENDAR[student_id]))

    def _list(self, student_id: str | None) -> ToolResult:
        if not student_id:
            return ToolResult.failure("calendar.list requires 'student_id'.")
        real = self._real_post("CALENDAR_API_URL", "CALENDAR_API_KEY", {"action": "list", "student_id": student_id})
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"calendar external call failed: {real.get('error')}")
            return ToolResult.success(events=real.get("events", []))
        return ToolResult.success(events=CALENDAR.get(student_id, []))

    @staticmethod
    def _event_dt(date: str | None, start_time: str | None) -> datetime:
        if date and start_time:
            try:
                return datetime.fromisoformat(f"{date}T{start_time}:00")
            except ValueError:
                pass
        return _now() + timedelta(hours=1)
