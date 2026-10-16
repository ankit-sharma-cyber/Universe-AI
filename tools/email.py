from typing import Any

from tools.base import BaseTool, ToolResult

OUTBOX: list[dict[str, Any]] = []


class EmailTool(BaseTool):
    name = "email"
    description = "Draft or send an email from a student's campus mailbox."

    def run(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "send")
        if action == "draft":
            return self._draft(kwargs)
        if action == "send":
            return self._send(kwargs)
        if action == "outbox":
            return ToolResult.success(messages=list(OUTBOX))
        return ToolResult.failure(f"Unknown email action '{action}'.")

    def _draft(self, kwargs: dict[str, Any]) -> ToolResult:
        guarded = self._guard()
        if guarded:
            return guarded
        to = kwargs.get("to")
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        if not all([to, subject, body]):
            return ToolResult.failure("email.draft requires 'to', 'subject' and 'body'.")
        payload = {"action": "draft", "to": to, "subject": subject, "body": body}
        real = self._real_post("EMAIL_API_URL", "EMAIL_API_KEY", payload)
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"email external call failed: {real.get('error')}")
            return ToolResult.success(message=real.get("message", payload), status=real.get("status", "drafted"))
        draft = {"to": to, "subject": subject, "body": body, "status": "draft"}
        OUTBOX.append(draft)
        return ToolResult.success(message=draft, status="drafted")

    def _send(self, kwargs: dict[str, Any]) -> ToolResult:
        guarded = self._guard()
        if guarded:
            return guarded
        to = kwargs.get("to")
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        if not all([to, subject, body]):
            return ToolResult.failure("email.send requires 'to', 'subject' and 'body'.")
        payload = {"action": "send", "to": to, "subject": subject, "body": body}
        real = self._real_post("EMAIL_API_URL", "EMAIL_API_KEY", payload)
        if real is not None:
            if real.get("_fallback"):
                return ToolResult.failure(f"email external call failed: {real.get('error')}")
            return ToolResult.success(message=real.get("message", payload), status=real.get("status", "sent"))
        message = {"to": to, "subject": subject, "body": body, "status": "sent"}
        OUTBOX.append(message)
        return ToolResult.success(message=message, status="sent")
