from llm.client import available, complete_json
from orchestrator.context import resolve_request

AGENT_REASONS = {
    "academic": "request involves classes, timetable, attendance or exam eligibility",
    "events": "request involves workshops, events, registration, calendars or clubs",
    "communication": "request involves drafting or sending emails",
    "knowledge": "request needs policies from the institutional knowledge base (RAG)",
    "placement": "request involves internship or placement eligibility",
    "student_services": "request involves hostel, library, scholarships, transport or grievances",
    "notification_calendar": "request involves calendar updates or reminders",
    "approval": "action-taking step needs human-in-the-loop approval before execution",
}

VALID_AGENTS = {
    "academic",
    "events",
    "communication",
    "knowledge",
    "placement",
    "student_services",
    "notification_calendar",
    "approval",
}

# Rule classifier signal groups. A request is scored by which domains it touches;
# composite intents are derived from the signal set, not from keyword priority order.
SIGNALS = {
    "academic": (
        "class", "classes", "timetable", "exam", "exams", "attendance", "faculty",
        "professor", "teacher", "instructor", "assignment", "sgpa", "gpa", "course", "lecture",
    ),
    "events": ("workshop", "workshops", "event", "events", "hackathon", "club", "clubs", "bootcamp", "seminar"),
    "communication": ("email", "draft", "send", "mail", "compose", "write to", "makeup exam", "permission"),
    "knowledge": ("policy", "policies", "rule", "rules", "regulation", "regulations", "handbook", "faq", "guideline"),
    "placement": ("internship", "placement", "placements", "eligible", "eligibility", "drive", "cgpa", "backlog"),
    "student_services": ("hostel", "library", "scholarship", "scholarships", "transport", "grievance", "lost", "found", "bus", "shuttle"),
    "notification_calendar": ("remind", "reminder", "reminders", "calendar", "schedule", "notification", "notify", "add it to my"),
}

# Composite intent trigger words that make a single-domain signal a workflow.
COMPOSITE = {
    "reason": ("summarize", "summary", "explain", "draft", "calculate"),
    "personalize": ("recommend", "suggest", "show me", "today's", "upcoming", "best"),
    "chain": ("register", "book", "sign up", "enroll", "add", "remind", "then"),
}

_PLAN_CAP = 6

_LLM_SYSTEM = """You are the routing planner for a smart-campus multi-agent system.
Given a student request, return JSON only with keys:
  "intent": one of chain|reason|personalize|placement|academic|events|knowledge|student_services|notification_calendar|general
  "agents": ordered list of agent names to run from:
    academic, placement, events, communication, knowledge, student_services, notification_calendar, approval

Routing guide:
- Eligibility + register/calendar/remind → intent=chain, agents=[knowledge, placement, approval, events]
- Summarize regulations + attendance + draft email → intent=reason, agents=[knowledge, academic, communication]
- Today's classes + recommend workshops/clubs → intent=personalize, agents=[academic, events]
- Only placement/eligibility → intent=placement, agents=[placement]
- Only classes/attendance/exam → intent=academic, agents=[academic]
- Only events/workshops/clubs → intent=events, agents=[events]
- Only policy/FAQ/handbook → intent=knowledge, agents=[knowledge]
- Only hostel/library/scholarships/transport/grievances → intent=student_services, agents=[student_services]
- Only calendar/reminder actions → intent=notification_calendar, agents=[notification_calendar]
Always include "approval" before "events" when the plan registers or mutates calendar state.
Never repeat an agent. Keep the list under 6 agents.
"""


def _signals(request: str) -> set[str]:
    q = request.lower()
    return {
        domain
        for domain, keywords in SIGNALS.items()
        if any(k in q for k in keywords)
    }


def _has_composite(request: str, group: str) -> bool:
    q = request.lower()
    return any(k in q for k in COMPOSITE[group])


def classify_rules(request: str) -> tuple[str, list[str]]:
    """Score domains first, then derive composite vs single-domain intents."""
    signals = _signals(request)
    reason = _has_composite(request, "reason")
    personalize = _has_composite(request, "personalize")
    chain = _has_composite(request, "chain")

    # Composite workflows — a multi-domain request with an action/verb.
    if chain and ("placement" in signals or "knowledge" in signals):
        return "chain", ["knowledge", "placement", "approval", "events"]
    if reason and ({"academic", "knowledge"} & signals) and "communication" in signals:
        return "reason", ["knowledge", "academic", "communication"]
    if personalize and {"academic", "events"} & signals:
        return "personalize", ["academic", "events"]

    # Single-domain routes.
    if "placement" in signals and not signals - {"placement"}:
        return "placement", ["placement"]
    if "student_services" in signals and not signals - {"student_services"}:
        return "student_services", ["student_services"]
    if "knowledge" in signals:
        return "knowledge", ["knowledge"]
    if "academic" in signals and not signals - {"academic"}:
        return "academic", ["academic"]
    if "events" in signals and not signals - {"events"}:
        return "events", ["events"]
    if "communication" in signals and not signals - {"communication"}:
        return "communication", ["communication"]
    if "notification_calendar" in signals:
        return "notification_calendar", ["notification_calendar"]
    return "general", ["knowledge"]


def _normalize_plan(intent: str, agents: list[str], request: str) -> list[str]:
    """Enforce plan invariants: known agents only, no repeats, approval before mutation,
    canonical composite routes, and a hard cap."""
    cleaned = [a for a in agents if isinstance(a, str) and a in VALID_AGENTS]
    seen: list[str] = []
    for agent in cleaned:
        if agent not in seen:
            seen.append(agent)

    if intent in ("chain", "reason", "personalize"):
        canonical = {
            "chain": ["knowledge", "placement", "approval", "events"],
            "reason": ["knowledge", "academic", "communication"],
            "personalize": ["academic", "events"],
        }[intent]
        seen = [a for a in canonical if a in seen] or seen

    # Approval must guard any mutation (register/calendar/remind).
    q = request.lower()
    mutates = any(k in q for k in ("register", "calendar", "remind", "book", "add it to my"))
    if mutates and "events" in seen and "approval" not in seen:
        idx = seen.index("events")
        seen.insert(idx, "approval")

    return seen[: _PLAN_CAP]


def classify_llm(request: str) -> tuple[str, list[str]] | None:
    raw = complete_json(
        f"Student request:\n{request}\n\nReturn JSON with intent and agents.",
        system=_LLM_SYSTEM,
    )
    if not raw or not isinstance(raw, dict):
        return None
    intent = raw.get("intent")
    agents = raw.get("agents")
    if not isinstance(intent, str) or not isinstance(agents, list) or not agents:
        return None
    cleaned = _normalize_plan(intent, agents, request)
    if not cleaned:
        return None
    return intent, cleaned


def classify(request: str) -> tuple[str, list[str]]:
    """Prefer LLM routing when configured; always fall back to deterministic rules."""
    if available():
        llm_plan = classify_llm(request)
        if llm_plan is not None:
            return llm_plan
    return classify_rules(request)


def planner_node(state):
    replan = state.get("replan")
    if replan:
        return _repair_plan(state, replan)

    raw_request = state.get("request") or ""
    effective, rewrite_note = resolve_request(raw_request, state.get("messages"))
    rules_intent, rules_agents = classify_rules(effective)

    source = "rules"
    if available():
        llm_plan = classify_llm(effective)
        if llm_plan is not None:
            intent, agents = llm_plan
            source = "llm"
        else:
            intent, agents = rules_intent, rules_agents
            source = "rules (llm unavailable or invalid)"
    else:
        intent, agents = rules_intent, rules_agents

    reasons = [{"node": name, "detail": AGENT_REASONS.get(name, name)} for name in agents]
    if source == "llm":
        planner_confidence = 0.95
    elif intent == "general":
        planner_confidence = 0.4
    else:
        planner_confidence = 0.9
    trace = [
        {
            "node": "planner",
            "detail": f"classified request as '{intent}' via {source}; route -> {agents}"
                      f" (confidence {planner_confidence})",
        },
        *reasons,
    ]
    if rewrite_note:
        trace.insert(0, {"node": "planner", "detail": rewrite_note})

    return {
        "request": effective,
        "intent": intent,
        "plan": agents,
        "step": 0,
        "results": {},
        "replan": None,
        "confidence": planner_confidence,
        "trace": trace,
    }


# Fallback agent used when a domain agent fails mid-plan (adaptive re-planning).
_REPLAN_FALLBACKS = {
    "knowledge": "student_services",
    "communication": None,
    "notification_calendar": "events",
    "events": None,
}


def _repair_plan(state, replan: dict) -> dict:
    """Reroute around a failed plan step. Returns the original plan with the failed
    agent replaced by a fallback (or dropped) plus a trace entry explaining the repair."""
    failed = replan.get("agent")
    reason = replan.get("reason", "agent error")
    original = state.get("plan") or []
    fallback = _REPLAN_FALLBACKS.get(failed)

    repaired = []
    for agent in original:
        if agent == failed:
            if fallback and fallback not in repaired and fallback not in original:
                repaired.append(fallback)
            continue
        repaired.append(agent)
    if not repaired:
        repaired = ["knowledge"]

    trace = [
        *state.get("trace", []),
        {
            "node": "planner",
            "detail": f"replanned: '{failed}' failed ({reason})"
                      f"{f'; substituted {fallback}' if fallback else '; step dropped'}"
                      f" -> {repaired}",
        },
    ]
    return {
        "intent": state.get("intent") or "general",
        "plan": repaired,
        "step": 0,
        "results": state.get("results") or {},
        "replan": None,
        "confidence": round((state.get("confidence") or 0.5) * 0.8, 2),
        "trace": trace,
    }
