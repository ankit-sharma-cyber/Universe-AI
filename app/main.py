"""FastAPI backend for the Universe AI system.

Two surfaces coexist:

- The **student portal** (`/api/*`): token-authenticated REST endpoints the React
  UI consumes. Every student-scoped route derives the student from the session
  token — the client never supplies a student id, so it cannot act as anyone else.
- The **orchestrator demo API** (no prefix): unauthenticated endpoints for the
  three hackathon demo workflows, live SSE traces, and human-in-the-loop approval.
"""

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import db
from data import store
from data.models import Student
from orchestrator import graph
from rag.retriever import Retriever
from tools.base import HEALTH
from tools.registry import get_tool, tool_schemas


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="Universe AI API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------

class LoginRequest(BaseModel):
    student_id: str
    email: str


def current_student(authorization: Annotated[str | None, Header()] = None) -> Student:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in")
    student_id = db.student_for_token(authorization.split(" ", 1)[1].strip())
    if not student_id:
        raise HTTPException(status_code=401, detail="Session expired — please sign in again")
    student = store.get_student(student_id)
    if not student:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return student


Me = Annotated[Student, Depends(current_student)]


@app.post("/api/auth/login")
def login(body: LoginRequest) -> dict:
    student = store.get_student(body.student_id.strip().upper())
    # compare on email too so a known roll number alone is not enough
    if not student or student.email.lower() != body.email.strip().lower():
        raise HTTPException(status_code=401, detail="Roll number and email do not match our records")
    if student.status != "active":
        raise HTTPException(status_code=403, detail=f"This account is {student.status}")
    return {"token": db.create_session(student.id), "student": student.model_dump()}


@app.post("/api/auth/logout")
def logout(authorization: Annotated[str | None, Header()] = None) -> dict:
    if authorization and authorization.lower().startswith("bearer "):
        db.delete_session(authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@app.get("/api/auth/me")
def me(student: Me) -> dict:
    return student.model_dump()


# --------------------------------------------------------------------------
# portal helpers
# --------------------------------------------------------------------------

def _today() -> date:
    return datetime.now().date()


def _registered_event_ids(student_id: str) -> list[str]:
    result = get_tool("registration")(action="list", student_id=student_id)
    return result.data.get("event_ids", []) if result.ok else []


def _classes_for(day: str) -> list[dict]:
    courses = {c.code: c for c in store.load_courses()}
    slots = sorted((s for s in store.load_timetable() if s.day == day), key=lambda s: s.start)
    return [
        {
            "code": s.code,
            "title": courses[s.code].title if s.code in courses else s.code,
            "credits": courses[s.code].credits if s.code in courses else None,
            "start": s.start,
            "end": s.end,
            "room": s.room,
            "building": s.building,
            "instructor": s.instructor,
        }
        for s in slots
    ]


def _attendance_standing(pct: float) -> dict:
    if pct >= 75:
        return {"status": "eligible", "note": "Meets the 75% minimum attendance requirement for exams."}
    if pct >= 60:
        return {
            "status": "makeup_eligible",
            "note": "Below 75% but above 60%: you may apply for a makeup examination.",
        }
    return {"status": "ineligible", "note": "Below 60%: not eligible to sit exams this semester."}


def _event_view(event, registered_ids: list[str], student: Student) -> dict:
    eligible = student.year in event.eligible_years and student.department in event.eligible_departments
    reasons = []
    if student.year not in event.eligible_years:
        reasons.append(f"Open to years {', '.join(map(str, event.eligible_years))}")
    if student.department not in event.eligible_departments:
        reasons.append(f"Open to {', '.join(event.eligible_departments)}")
    seats_left = max(event.capacity - event.registered_count, 0)
    return {
        **event.model_dump(),
        "registered": event.id in registered_ids,
        "eligible": eligible,
        "ineligible_reasons": reasons,
        "seats_left": seats_left,
        "is_full": seats_left == 0,
        "is_past": event.date < _today().isoformat(),
    }


# --------------------------------------------------------------------------
# dashboard
# --------------------------------------------------------------------------

@app.get("/api/me/dashboard")
def dashboard(student: Me) -> dict:
    today = _today()
    day_name = today.strftime("%A")
    registered_ids = _registered_event_ids(student.id)

    upcoming = sorted(
        (e for e in store.load_events() if e.date >= today.isoformat() and e.status != "cancelled"),
        key=lambda e: (e.date, e.start_time),
    )
    my_events = [_event_view(e, registered_ids, student) for e in upcoming if e.id in registered_ids]

    open_drives = [
        p for p in store.load_placements()
        if p.status == "open"
        and p.application_deadline >= today.isoformat()
        and student.department in p.eligible_departments
        and student.cgpa >= p.eligibility_cgpa
    ]

    calendar = get_tool("calendar")(action="list", student_id=student.id)
    reminders = get_tool("notification")(action="list", student_id=student.id)

    return {
        "day": day_name,
        "date": today.isoformat(),
        "classes": _classes_for(day_name),
        "attendance": {"pct": student.attendance_pct, **_attendance_standing(student.attendance_pct)},
        "my_events": my_events,
        "suggested_events": [
            _event_view(e, registered_ids, student)
            for e in upcoming
            if e.id not in registered_ids
            and student.year in e.eligible_years
            and student.department in e.eligible_departments
        ][:4],
        "open_drives": [p.model_dump() for p in open_drives][:4],
        "calendar": calendar.data.get("events", []) if calendar.ok else [],
        "reminders": reminders.data.get("reminders", []) if reminders.ok else [],
    }


# --------------------------------------------------------------------------
# academics
# --------------------------------------------------------------------------

@app.get("/api/timetable")
def timetable(student: Me) -> dict:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    return {
        "today": _today().strftime("%A"),
        "days": [{"day": day, "classes": _classes_for(day)} for day in days],
    }


@app.get("/api/courses")
def courses(student: Me) -> list[dict]:
    return [c.model_dump() for c in store.load_courses() if c.department == student.department]


@app.get("/api/me/attendance")
def attendance(student: Me) -> dict:
    return {"pct": student.attendance_pct, **_attendance_standing(student.attendance_pct)}


# --------------------------------------------------------------------------
# profile + assignments
# --------------------------------------------------------------------------

def _assignment_view(assignment, submission: dict | None) -> dict:
    """One assignment as the student sees it: deadline maths plus their submission."""
    due = date.fromisoformat(assignment.due_date)
    days_left = (due - _today()).days
    if submission:
        state = submission["status"]  # graded | submitted | late
    elif days_left < 0:
        state = "missed"
    else:
        state = "open"
    return {
        **assignment.model_dump(),
        "days_left": days_left,
        "is_overdue": state == "missed",
        "due_soon": state == "open" and 0 <= days_left <= 3,
        "state": state,
        "submitted_at": submission.get("submitted_at") if submission else None,
        "marks": submission.get("marks") if submission else None,
        "percent": (
            round(100 * submission["marks"] / assignment.max_marks)
            if submission and submission.get("marks") is not None and assignment.max_marks
            else None
        ),
    }


def _assignments_for(student: Student) -> list[dict]:
    """Seed submissions, overlaid with anything submitted through the portal."""
    seeded = {
        s.assignment_id: s.model_dump()
        for s in store.load_submissions()
        if s.student_id == student.id
    }
    seeded.update(db.submissions_for(student.id))
    mine = [
        a for a in store.load_assignments()
        if a.department in (student.department, "COMMON")
    ]
    views = [_assignment_view(a, seeded.get(a.id)) for a in mine]
    return sorted(views, key=lambda a: a["due_date"])


@app.get("/api/me/profile")
def profile(student: Me) -> dict:
    semesters = [s.model_dump() for s in student.semester_gpa]
    assignments = _assignments_for(student)
    graded = [a for a in assignments if a["marks"] is not None]
    total_credits = sum(s["credits"] for s in semesters)
    best = max(semesters, key=lambda s: s["sgpa"], default=None)

    return {
        "student": student.model_dump(),
        "semesters": semesters,
        "current_semester": len(semesters) + 1,
        "total_credits": total_credits,
        "best_semester": best,
        "attendance": {"pct": student.attendance_pct, **_attendance_standing(student.attendance_pct)},
        "assignment_summary": {
            "total": len(assignments),
            "submitted": sum(1 for a in assignments if a["state"] in ("submitted", "graded", "late")),
            "open": sum(1 for a in assignments if a["state"] == "open"),
            "missed": sum(1 for a in assignments if a["state"] == "missed"),
            "average_percent": (
                round(sum(a["percent"] for a in graded) / len(graded)) if graded else None
            ),
        },
    }


@app.get("/api/me/assignments")
def assignments(student: Me, scope: str = "all") -> list[dict]:
    items = _assignments_for(student)
    if scope == "open":
        items = [a for a in items if a["state"] == "open"]
    elif scope == "submitted":
        items = [a for a in items if a["state"] in ("submitted", "graded", "late")]
    elif scope == "missed":
        items = [a for a in items if a["state"] == "missed"]
    return items


@app.post("/api/me/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: str, student: Me) -> dict:
    assignment = store.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.department not in (student.department, "COMMON"):
        raise HTTPException(status_code=403, detail="This assignment is not on your course list")

    existing = {s.assignment_id for s in store.load_submissions() if s.student_id == student.id}
    if assignment_id in existing or assignment_id in db.submissions_for(student.id):
        raise HTTPException(status_code=409, detail="You have already submitted this assignment")

    overdue = date.fromisoformat(assignment.due_date) < _today()
    record = db.record_submission(student.id, assignment_id, "late" if overdue else "submitted")
    return {"assignment": _assignment_view(assignment, record)}


# --------------------------------------------------------------------------
# events
# --------------------------------------------------------------------------

@app.get("/api/events")
def events(student: Me, scope: str = "upcoming", category: str | None = None) -> list[dict]:
    registered_ids = _registered_event_ids(student.id)
    today = _today().isoformat()
    items = store.load_events()
    if scope == "upcoming":
        items = [e for e in items if e.date >= today]
    elif scope == "past":
        items = [e for e in items if e.date < today]
    elif scope == "registered":
        items = [e for e in items if e.id in registered_ids]
    if category:
        items = [e for e in items if e.category == category or e.type == category]
    items = sorted(items, key=lambda e: (e.date, e.start_time))
    return [_event_view(e, registered_ids, student) for e in items]


@app.post("/api/events/{event_id}/register")
def register_for_event(event_id: str, student: Me) -> dict:
    event = store.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = get_tool("registration")(action="register", student_id=student.id, event_id=event_id)
    if not result.ok:
        raise HTTPException(status_code=409, detail=result.error)

    # mirror the agent workflow: a registration also lands on the calendar
    get_tool("calendar")(
        action="add",
        student_id=student.id,
        title=event.title,
        date=event.date,
        start_time=event.start_time,
        location=event.location,
        reminder_before_min=60,
    )
    registered_ids = _registered_event_ids(student.id)
    return {"registration": result.data, "event": _event_view(event, registered_ids, student)}


@app.get("/api/me/registrations")
def my_registrations(student: Me) -> list[dict]:
    registered_ids = _registered_event_ids(student.id)
    items = [e for e in store.load_events() if e.id in registered_ids]
    items = sorted(items, key=lambda e: (e.date, e.start_time))
    return [_event_view(e, registered_ids, student) for e in items]


@app.get("/api/me/calendar")
def my_calendar(student: Me) -> list[dict]:
    result = get_tool("calendar")(action="list", student_id=student.id)
    return result.data.get("events", []) if result.ok else []


@app.get("/api/me/reminders")
def my_reminders(student: Me) -> list[dict]:
    result = get_tool("notification")(action="list", student_id=student.id)
    return result.data.get("reminders", []) if result.ok else []


# --------------------------------------------------------------------------
# placements
# --------------------------------------------------------------------------

@app.get("/api/placements")
def placements(student: Me) -> list[dict]:
    today = _today().isoformat()
    out = []
    for p in sorted(store.load_placements(), key=lambda p: p.drive_date):
        checks = [
            {"criterion": "CGPA", "met": student.cgpa >= p.eligibility_cgpa,
             "detail": f"Requires {p.eligibility_cgpa} — you have {student.cgpa}"},
            {"criterion": "Department", "met": student.department in p.eligible_departments,
             "detail": f"Open to {', '.join(p.eligible_departments)} — you are {student.department}"},
            {"criterion": "Backlogs", "met": student.backlogs == 0,
             "detail": f"No active backlogs required — you have {student.backlogs}"},
            {"criterion": "Deadline", "met": p.application_deadline >= today,
             "detail": f"Applications close {p.application_deadline}"},
        ]
        out.append({**p.model_dump(), "checks": checks, "eligible": all(c["met"] for c in checks)})
    return out


# --------------------------------------------------------------------------
# campus directory
# --------------------------------------------------------------------------

@app.get("/api/clubs")
def clubs(student: Me) -> list[dict]:
    interests = {i.lower() for i in student.interests}
    out = []
    for club in store.load_clubs():
        tags = {t.lower() for t in club.tags}
        out.append({**club.model_dump(), "matches_interests": bool(tags & interests)})
    return sorted(out, key=lambda c: (not c["matches_interests"], c["name"]))


@app.get("/api/faqs")
def faqs(student: Me) -> list[dict]:
    return [f.model_dump() for f in store.load_faqs()]


@app.get("/api/policies")
def policies(student: Me) -> list[dict]:
    return store.load_policies()


@app.get("/api/faculty")
def faculty(student: Me) -> list[dict]:
    return [f.model_dump() for f in store.load_faculty()]


@app.get("/api/hostels")
def hostels(student: Me) -> list[dict]:
    return [h.model_dump() for h in store.load_hostels()]


@app.get("/api/lostfound")
def lostfound(student: Me) -> list[dict]:
    return [i.model_dump() for i in store.load_lostfound()]


# --------------------------------------------------------------------------
# portal assistant
# --------------------------------------------------------------------------

class PortalChatRequest(BaseModel):
    request: str
    conversation_id: str | None = None


class PortalApprovalRequest(BaseModel):
    conversation_id: str
    approved: bool


class PortalChatResponse(BaseModel):
    conversation_id: str
    final: str | None = None
    intent: str | None = None
    plan: list[str] = Field(default_factory=list)
    trace: list[dict] = Field(default_factory=list)
    error: str | None = None
    pending_approval: dict | None = None


def _interrupt_payload(result: dict) -> dict | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    value = getattr(interrupts[0], "value", interrupts[0])
    return value if isinstance(value, dict) else {"message": str(value)}


def _finish(result: dict, conversation_id: str) -> PortalChatResponse:
    pending = _interrupt_payload(result)
    response = PortalChatResponse(
        conversation_id=conversation_id,
        final=result.get("final"),
        intent=result.get("intent"),
        plan=result.get("plan", []),
        trace=result.get("trace", []),
        error=result.get("error"),
        pending_approval=pending,
    )
    # only persist a completed turn; a paused graph has no answer yet
    if pending is None and response.final:
        db.add_message(conversation_id, "assistant", response.final, response.intent, response.trace)
    return response


@app.post("/api/chat", response_model=PortalChatResponse)
def portal_chat(body: PortalChatRequest, student: Me) -> PortalChatResponse:
    text = body.request.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message must not be empty")

    conversation_id = body.conversation_id
    if conversation_id:
        if not db.owns_conversation(student.id, conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation_id = db.create_conversation(student.id, text)

    db.add_message(conversation_id, "user", text)
    try:
        # the graph thread is the conversation, so an interrupt resumes in place
        result = graph.run(text, student_id=student.id, thread_id=conversation_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _finish(result, conversation_id)


@app.post("/api/approve", response_model=PortalChatResponse)
def portal_approve(body: PortalApprovalRequest, student: Me) -> PortalChatResponse:
    if not db.owns_conversation(student.id, body.conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        result = graph.run(thread_id=body.conversation_id, resume={"approved": body.approved})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _finish(result, body.conversation_id)


@app.get("/api/conversations")
def conversations(student: Me) -> list[dict]:
    return db.list_conversations(student.id)


@app.get("/api/conversations/{conversation_id}")
def conversation(conversation_id: str, student: Me) -> dict:
    if not db.owns_conversation(student.id, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"id": conversation_id, "messages": db.load_messages(conversation_id)}


@app.delete("/api/conversations/{conversation_id}")
def remove_conversation(conversation_id: str, student: Me) -> dict:
    if not db.delete_conversation(student.id, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


# --------------------------------------------------------------------------
# portal system
# --------------------------------------------------------------------------

@app.get("/api/health")
def api_health() -> dict:
    return {"status": "ok", "tools": dict(HEALTH)}


@app.get("/api/system/tools")
def system_tools(student: Me) -> list[dict]:
    return [{**schema, "healthy": HEALTH.get(schema["name"], True)} for schema in tool_schemas()]


# --------------------------------------------------------------------------
# orchestrator demo API (unauthenticated, for the live demo)
# --------------------------------------------------------------------------

DEMO_WORKFLOWS = [
    {
        "id": "chained-action",
        "title": "Chained action",
        "prompt": (
            "I'm a third-year CSE student. Am I eligible for the Google internship? If yes, "
            "register me for tomorrow's placement workshop, add it to my calendar, and remind me "
            "one hour before the event."
        ),
    },
    {
        "id": "reasoning-generation",
        "title": "Reasoning + generation",
        "prompt": (
            "Summarize the examination regulations, calculate my attendance eligibility, and draft "
            "an email requesting permission for a makeup exam."
        ),
    },
    {
        "id": "personalization",
        "title": "Personalization",
        "prompt": "Show today's classes, recommend upcoming AI workshops, and suggest clubs related to Machine Learning.",
    },
]


class ChatRequest(BaseModel):
    request: str
    student_id: str = "S2023001"
    thread_id: str = "default"


class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool


@app.get("/")
def root() -> dict:
    return {
        "service": "Universe AI Multi-Agent API",
        "docs": "/docs",
        "endpoints": ["/health", "/students", "/workflows", "/chat", "/chat/stream", "/approve"],
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "rag_available": Retriever().available,
        "tools": dict(HEALTH) or {schema["name"]: True for schema in tool_schemas()},
    }


@app.get("/students")
def students() -> dict:
    return {
        "students": [
            {
                "id": s.id,
                "name": s.name,
                "department": s.department,
                "year": s.year,
                "cgpa": s.cgpa,
                "attendance_pct": s.attendance_pct,
                "interests": s.interests,
            }
            for s in store.load_students()
        ]
    }


@app.get("/workflows")
def workflows() -> dict:
    return {"workflows": DEMO_WORKFLOWS}


@app.post("/chat")
def chat(body: ChatRequest) -> dict:
    if not body.request.strip():
        raise HTTPException(status_code=400, detail="request must not be empty")
    try:
        result = graph.run(body.request, student_id=body.student_id, thread_id=body.thread_id)
    except Exception as exc:  # orchestrator must never leak a raw 500 to the client
        return {"status": "error", "thread_id": body.thread_id, "error": str(exc)}
    return graph.serialize_result(result, body.thread_id)


@app.post("/approve")
def approve(body: ApprovalRequest) -> dict:
    try:
        result = graph.run(thread_id=body.thread_id, resume={"approved": body.approved})
    except Exception as exc:
        return {"status": "error", "thread_id": body.thread_id, "error": str(exc)}
    return graph.serialize_result(result, body.thread_id)


@app.post("/chat/stream")
def chat_stream(body: ChatRequest) -> StreamingResponse:
    if not body.request.strip():
        raise HTTPException(status_code=400, detail="request must not be empty")

    def event_source():
        try:
            for event in graph.stream_events(
                body.request, student_id=body.student_id, thread_id=body.thread_id
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.post("/approve/stream")
def approve_stream(body: ApprovalRequest) -> StreamingResponse:
    def event_source():
        try:
            for event in graph.stream_events(
                thread_id=body.thread_id, resume={"approved": body.approved}
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
