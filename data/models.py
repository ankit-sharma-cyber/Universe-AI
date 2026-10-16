from pydantic import BaseModel


class SemesterGrade(BaseModel):
    semester: int
    credits: int
    sgpa: float


class Student(BaseModel):
    id: str
    name: str
    email: str
    department: str
    year: int
    cgpa: float
    attendance_pct: float
    interests: list[str]
    status: str
    backlogs: int
    placement_status: str | None = None
    semester_gpa: list[SemesterGrade] = []


class Course(BaseModel):
    code: str
    title: str
    department: str
    credits: int
    semester: int
    instructor: str


class TimetableSlot(BaseModel):
    day: str
    code: str
    start: str
    end: str
    room: str
    building: str
    instructor: str


class Event(BaseModel):
    id: str
    title: str
    type: str
    category: str
    date: str
    start_time: str
    end_time: str
    location: str
    capacity: int
    registered_count: int
    status: str
    tags: list[str]
    eligible_years: list[int]
    eligible_departments: list[str]


class Club(BaseModel):
    id: str
    name: str
    category: str
    tags: list[str]
    meeting: str
    description: str
    faculty_advisor: str
    president: str
    email: str
    members: int
    recruitment_open: bool


class FAQ(BaseModel):
    id: str
    question: str
    answer: str
    category: str

class Faculty(BaseModel):
    id: str
    name: str
    department: str
    designation: str
    email: str
    office: str

class Hostel(BaseModel):
    id: str
    name: str
    type: str
    capacity: int
    occupied: int
    warden: str
    contact: str

class Placement(BaseModel):
    id: str
    company: str
    role: str
    package_lpa: float
    eligibility_cgpa: float
    eligible_departments: list[str]
    drive_date: str
    location: str
    application_deadline: str
    status: str

class LostFound(BaseModel):
    id: str
    item: str
    category: str
    location: str
    date_reported: str
    contact: str
    status: str


class Scholarship(BaseModel):
    id: str
    name: str
    amount: float
    eligibility: str
    deadline: str
    department: str


class Transport(BaseModel):
    id: str
    route: str
    timing: str
    vehicle_type: str
    capacity: int
    contact: str


class Grievance(BaseModel):
    id: str
    category: str
    subject: str
    status: str
    last_updated: str


class Assignment(BaseModel):
    id: str
    course_code: str
    course_title: str
    department: str
    title: str
    type: str
    max_marks: int
    due_date: str
    due_time: str


class Submission(BaseModel):
    student_id: str
    assignment_id: str
    submitted_at: str
    marks: int | None = None
    status: str