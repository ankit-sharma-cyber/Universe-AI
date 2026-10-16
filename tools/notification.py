from typing import Any

from tools.base import BaseTool, ToolResult

REMINDERS: dict[str, list[dict[str, Any]]] = {}


class NotificationTool(BaseTool):
    name = "notification"
    description = "Schedule a reminder/notification for a student at a given time."

    def run(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "schedule")
        if action == "schedule":
            return self._schedule(kwargs)
        if action == "list":
            return self._list(kwargs.get("student_id"))
        return ToolResult.failure(f"Unknown notification action '{action}'.")

    def _schedule(self, kwargs: dict[str, Any]) -> ToolResult:
        guarded = self._guard()
        if guarded:
            return guarded
        student_id = kwargs.get("student_id")
        message = kwargs.get("message")
        at = kwargs.get("at")
        if not all([student_id, message, at]):
            return ToolResult.failure("notification.schedule requires 'student_id', 'message' and 'at'.")
        payload = {"action": "schedule", "student_id": student_id, "message": message, "at": at}
        real = self._real_post("NOTIFICATION_API_URL", "NOTIFICATION_API_KEY", payload)
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"notification external call failed: {real.get('error')}")
            return ToolResult.success(reminder=real.get("reminder", payload))
        reminder = {"message": message, "at": at, "status": "scheduled"}
        REMINDERS.setdefault(student_id, []).append(reminder)
        return ToolResult.success(reminder=reminder)

    def _list(self, student_id: str | None) -> ToolResult:
        if not student_id:
            return ToolResult.failure("notification.list requires 'student_id'.")
        real = self._real_post("NOTIFICATION_API_URL", "NOTIFICATION_API_KEY", {"action": "list", "student_id": student_id})
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"notification external call failed: {real.get('error')}")
            return ToolResult.success(reminders=real.get("reminders", []))
        return ToolResult.success(reminders=REMINDERS.get(student_id, []))
