"""Session context helpers: resolve short follow-ups using conversation history."""

from __future__ import annotations

FOLLOWUP_MARKERS = (
    "what about",
    "and me",
    "same for",
    "do the same",
    "also for",
    "how about",
    "my turn",
    "for me too",
    "again",
    "same thing",
    "that again",
)


def last_user_content(messages: list[dict] | None) -> str | None:
    if not messages:
        return None
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return str(message["content"])
    return None


def is_followup(request: str) -> bool:
    q = request.lower().strip()
    if len(q.split()) <= 6 and any(m in q for m in FOLLOWUP_MARKERS):
        return True
    if q in {"same", "again", "continue", "yes", "yep", "ok do it", "go ahead"}:
        return True
    return False


def resolve_request(request: str, messages: list[dict] | None = None) -> tuple[str, str | None]:
    """Return (effective_request, rewrite_note).

    Short follow-ups inherit the previous user request so the planner can re-route.
    """
    prior = None
    if messages:
        # messages already includes the current user turn when invoked from graph.run;
        # look at the previous user turn only.
        user_turns = [m["content"] for m in messages if m.get("role") == "user" and m.get("content")]
        if len(user_turns) >= 2:
            prior = user_turns[-2]
        elif len(user_turns) == 1 and is_followup(request):
            # current request is the only user turn but marked follow-up — no prior
            prior = None

    if prior and is_followup(request):
        combined = f"{prior}\n\nFollow-up from user: {request}"
        return combined, f"resolved follow-up using prior request: {prior[:80]}"
    return request, None
