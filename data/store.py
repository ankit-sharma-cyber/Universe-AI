import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from data.models import (
    Assignment,
    Club,
    Course,
    Event,
    Faculty,
    FAQ,
    Grievance,
    Hostel,
    LostFound,
    Placement,
    Scholarship,
    Student,
    Submission,
    TimetableSlot,
    Transport,
)

DATA_DIR = Path(__file__).resolve().parent

# Relative offsets keep the three demo workflows working regardless of calendar day.
# Absolute "date" fields in JSON are treated as fallbacks when days_from_today is absent.
_EVENT_DAY_OFFSETS = {
    "E101": 1,   # tomorrow — placement workshop (workflow 1)
    "E102": 5,
    "E103": 3,
    "E104": 13,
    "E105": 8,
}


def _load(filename: str) -> list[dict]:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache
def load_students() -> list[Student]:
    return [Student.model_validate(row) for row in _load("students.json")]


@lru_cache
def load_courses() -> list[Course]:
    return [Course.model_validate(row) for row in _load("courses.json")]


@lru_cache
def load_timetable() -> list[TimetableSlot]:
    return [TimetableSlot.model_validate(row) for row in _load("timetable.json")]


def load_events() -> list[Event]:
    """Resolve event dates relative to today so demo 'tomorrow' flows stay valid."""
    today = date.today()
    events: list[Event] = []
    for row in _load("events.json"):
        data = dict(row)
        offset = data.pop("days_from_today", None)
        if offset is None:
            offset = _EVENT_DAY_OFFSETS.get(data.get("id"))
        if offset is not None:
            data["date"] = (today + timedelta(days=int(offset))).isoformat()
        events.append(Event.model_validate(data))
    return events


@lru_cache
def load_clubs() -> list[Club]:
    return [Club.model_validate(row) for row in _load("clubs.json")]


@lru_cache
def load_hostels() -> list[Hostel]:
    return [Hostel.model_validate(row) for row in _load("hostel.json")]


@lru_cache
def load_lostfound() -> list[LostFound]:
    return [LostFound.model_validate(row) for row in _load("lostfound.json")]


@lru_cache
def load_scholarships() -> list[Scholarship]:
    return [Scholarship.model_validate(row) for row in _load("scholarships.json")]


@lru_cache
def load_transport() -> list[Transport]:
    return [Transport.model_validate(row) for row in _load("transport.json")]


@lru_cache
def load_grievances() -> list[Grievance]:
    return [Grievance.model_validate(row) for row in _load("grievances.json")]


@lru_cache
def load_faculty() -> list[Faculty]:
    return [Faculty.model_validate(row) for row in _load("faculty.json")]


@lru_cache
def load_faqs() -> list[FAQ]:
    return [FAQ.model_validate(row) for row in _load("faqs.json")]


@lru_cache
def load_placements() -> list[Placement]:
    return [Placement.model_validate(row) for row in _load("placement.json")]


@lru_cache
def load_policies() -> list[dict]:
    """Policy handbooks as raw markdown, keyed by slug."""
    docs = []
    for path in sorted((DATA_DIR / "policies").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("#")), path.stem)
        docs.append({"slug": path.stem, "title": title, "body": text})
    return docs


@lru_cache
def load_assignments() -> list[Assignment]:
    return [Assignment.model_validate(row) for row in _load("assignments.json")]


@lru_cache
def load_submissions() -> list[Submission]:
    return [Submission.model_validate(row) for row in _load("submissions.json")]


def get_assignment(assignment_id: str) -> Assignment | None:
    return next((a for a in load_assignments() if a.id == assignment_id), None)


def get_student(student_id: str) -> Student | None:
    return next((s for s in load_students() if s.id == student_id), None)


def get_event(event_id: str) -> Event | None:
    return next((e for e in load_events() if e.id == event_id), None)


def get_placement(placement_id: str) -> Placement | None:
    return next((p for p in load_placements() if p.id == placement_id), None)
