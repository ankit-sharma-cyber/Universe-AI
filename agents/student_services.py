from data import store

NAME = "student_services"


def run(request: str, student_id: str, **ctx) -> dict:
    student = store.get_student(student_id)
    if not student:
        return {"output": None, "error": f"Unknown student {student_id}.", "confidence": 0.2, "trace": "student lookup failed"}

    request_lower = request.lower()
    output: dict = {}
    if "hostel" in request_lower:
        output["hostel"] = _hostel_info(request_lower)
    if "library" in request_lower:
        output["library"] = _library_info(request_lower)
    if "scholarship" in request_lower:
        output["scholarships"] = _scholarship_info(request_lower, student)
    if "transport" in request_lower or "bus" in request_lower or "shuttle" in request_lower:
        output["transport"] = _transport_info(request_lower)
    if "grievance" in request_lower or "complaint" in request_lower:
        output["grievances"] = _grievance_info(request_lower)
    if "lost" in request_lower or "found" in request_lower or "forgot" in request_lower:
        output["lostfound"] = _lostfound_info(request_lower)

    if not output:
        return {
            "output": None,
            "error": "Could not identify a student services topic (hostel, library, scholarship, transport, grievance).",
            "confidence": 0.5,
            "trace": "no matching service detected",
        }

    return {"output": output, "error": None, "confidence": 0.9, "trace": f"Resolved student services for {student.name}."}


def _hostel_info(request_lower: str) -> dict:
    hostels = store.load_hostels()
    if "available" in request_lower or "vacancy" in request_lower or "occupancy" in request_lower:
        items = []
        for h in hostels:
            items.append(
                {
                    "id": h.id,
                    "name": h.name,
                    "type": h.type,
                    "available": h.capacity - h.occupied,
                    "warden": h.warden,
                    "contact": h.contact,
                }
            )
        return {"type": "hostel_vacancy", "hostels": items}
    return {"type": "hostel_list", "hostels": [{"id": h.id, "name": h.name, "type": h.type, "warden": h.warden, "contact": h.contact} for h in hostels]}


def _library_info(request_lower: str) -> dict:
    faqs = store._load("faqs.json") if hasattr(store, "_load") else []
    library_faqs = [f for f in faqs if f.get("category") == "library"]
    return {
        "type": "library_info",
        "timing": "8:00 AM to 10:00 PM on all working days.",
        "faqs": library_faqs,
    }


def _scholarship_info(request_lower: str, student) -> dict:
    scholarships = store.load_scholarships()
    items = []
    for s in scholarships:
        eligible = s.department in ("ALL", student.department)
        items.append(
            {
                "id": s.id,
                "name": s.name,
                "amount": s.amount,
                "eligibility": s.eligibility,
                "deadline": s.deadline,
                "likely_eligible": eligible,
            }
        )
    return {"type": "scholarships", "scholarships": items}


def _transport_info(request_lower: str) -> dict:
    routes = store.load_transport()
    return {
        "type": "transport",
        "routes": [
            {
                "id": r.id,
                "route": r.route,
                "timing": r.timing,
                "vehicle_type": r.vehicle_type,
                "contact": r.contact,
            }
            for r in routes
        ],
    }


def _grievance_info(request_lower: str) -> dict:
    items = store.load_grievances()
    if "status" in request_lower or "track" in request_lower:
        return {"type": "grievances_track", "grievances": [{"id": g.id, "category": g.category, "subject": g.subject, "status": g.status, "last_updated": g.last_updated} for g in items]}
    return {"type": "grievances_list", "grievances": [{"id": g.id, "category": g.category, "subject": g.subject, "status": g.status} for g in items]}


def _lostfound_info(request_lower: str) -> dict:
    items = store.load_lostfound()
    tokens = [w for w in request_lower.replace(",", " ").split() if len(w) > 3]
    matched = [i for i in items if any(t in i.item.lower() or t in i.category.lower() for t in tokens)]
    if not matched:
        matched = items
    return {
        "type": "lostfound",
        "items": [
            {"id": i.id, "item": i.item, "category": i.category,
             "location": i.location, "status": i.status, "contact": i.contact}
            for i in matched
        ],
    }
