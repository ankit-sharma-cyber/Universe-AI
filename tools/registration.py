from typing import Any

from data import store
from tools.base import BaseTool, ToolResult

REGISTRATIONS: dict[str, list[str]] = {}


class RegistrationTool(BaseTool):
    name = "registration"
    description = "Register a student for an event after validating eligibility and capacity."

    def run(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "register")
        if action == "register":
            return self._register(kwargs)
        if action == "list":
            return self._list(kwargs.get("student_id"))
        return ToolResult.failure(f"Unknown registration action '{action}'.")

    def _register(self, kwargs: dict[str, Any]) -> ToolResult:
        guarded = self._guard()
        if guarded:
            return guarded
        student_id = kwargs.get("student_id")
        event_id = kwargs.get("event_id")
        student = store.get_student(student_id)
        event = store.get_event(event_id)
        if not student:
            return ToolResult.failure(f"Unknown student '{student_id}'.")
        if not event:
            return ToolResult.failure(f"Unknown event '{event_id}'.")
        if student.year not in event.eligible_years:
            return ToolResult.failure(
                f"{student.name} (year {student.year}) is not eligible for '{event.title}' "
                f"(open to years {event.eligible_years})."
            )
        if student.department not in event.eligible_departments:
            return ToolResult.failure(
                f"{student.department} is not eligible for '{event.title}' "
                f"(open to {event.eligible_departments})."
            )
        attendees = REGISTRATIONS.setdefault(event_id, [])
        if student_id in attendees:
            return ToolResult.failure(f"{student.name} is already registered for '{event.title}'.")
        if len(attendees) >= event.capacity:
            return ToolResult.failure(f"'{event.title}' is at full capacity.")
        payload = {
            "action": "register",
            "student_id": student_id,
            "event_id": event_id,
            "student_name": student.name,
            "event_title": event.title,
            "seats_left": event.capacity - len(attendees) - 1,
        }
        real = self._real_post("REGISTRATION_API_URL", "REGISTRATION_API_KEY", payload)
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"registration external call failed: {real.get('error')}")
            return ToolResult.success(
                event_id=real.get("event_id", event_id),
                title=real.get("title", event.title),
                student_id=real.get("student_id", student_id),
                seats_left=real.get("seats_left", 0),
            )
        attendees.append(student_id)
        return ToolResult.success(
            event_id=event_id,
            title=event.title,
            student_id=student_id,
            seats_left=event.capacity - len(attendees),
        )

    def _list(self, student_id: str | None) -> ToolResult:
        if not student_id:
            return ToolResult.failure("registration.list requires 'student_id'.")
        real = self._real_post("REGISTRATION_API_URL", "REGISTRATION_API_KEY", {"action": "list", "student_id": student_id})
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"registration external call failed: {real.get('error')}")
            return ToolResult.success(event_ids=real.get("event_ids", []))
        return ToolResult.success(
            event_ids=[eid for eid, students in REGISTRATIONS.items() if student_id in students]
        )
