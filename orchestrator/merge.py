def merge_node(state):
    intent = state.get("intent", "general")
    final = _render(intent, state.get("results", {}))
    return {
        "final": final,
        "error": None,
        "confidence": _overall_confidence(state),
        "messages": [{"role": "assistant", "content": final}],
    }


def _overall_confidence(state: dict) -> float:
    """Blend planner routing confidence with the executing agents' confidences."""
    planner_confidence = state.get("confidence")
    if not isinstance(planner_confidence, (int, float)):
        planner_confidence = 0.5
    confidences = []
    for result in (state.get("results") or {}).values():
        if isinstance(result, dict) and isinstance(result.get("confidence"), (int, float)):
            confidences.append(float(result["confidence"]))
    agent_avg = sum(confidences) / len(confidences) if confidences else 0.5
    return round(0.5 * float(planner_confidence) + 0.5 * agent_avg, 2)


def _render(intent: str, results: dict) -> str:
    renderer = _RENDERERS.get(intent, _render_general)
    return renderer(results)


def _render_chain(results: dict) -> str:
    lines = ["**Multi-step action completed**", ""]
    knowledge = _agent_output(results, "knowledge")
    placement = _agent_output(results, "placement")
    registration = _agent_output(results, "events").get("registration", {})

    if knowledge:
        lines.append("**Policy reference (RAG):**")
        if error := _error_note("knowledge", knowledge):
            lines.append(error)
        else:
            for chunk in knowledge[:2]:
                lines.append(f"- *{chunk['source']}* — {chunk['heading']}")
        lines.append("")

    if placement:
        if error := _error_note("placement", placement):
            lines.append(error)
        else:
            eligible = placement.get("eligible", False)
            lines.append(f"**Eligibility check ({placement.get('internship')}):** "
                         f"{'ELIGIBLE' if eligible else 'NOT ELIGIBLE'}")
            for check in placement.get("checks", []):
                mark = "✓" if check["met"] else "✗"
                lines.append(f"- {mark} {check['criterion']}: {check['detail']}")
            if a2a := placement.get("a2a"):
                lines.append("")
                lines.append(f"**Inter-agent message → {a2a['to']} agent:** {a2a['message']}")
                lines.append(f"**{a2a['to']} agent replied:**")
                for rec in a2a["reply"]:
                    lines.append(f"- {rec}")
        lines.append("")

    if registration.get("registered"):
        lines.append(f"**Registered:** {registration['title']}")
        for step in registration.get("steps", []):
            lines.append(f"- {'✓' if step['ok'] else '✗'} {step['tool']}: {step['detail']}")
        if registration.get("errors"):
            lines.append(f"- ⚠ partial failure: {registration['errors']}")
    elif registration.get("skipped"):
        lines.append(f"**Registration:** skipped — {registration['skipped']}")

    return "\n".join(lines)


def _render_reason(results: dict) -> str:
    lines = ["**Reasoning + generation complete**", ""]
    knowledge = _agent_output(results, "knowledge")
    academic = _agent_output(results, "academic")
    email = _agent_output(results, "communication")

    if knowledge:
        lines.append("**Examination regulations summary (from RAG):**")
        if error := _error_note("knowledge", knowledge):
            lines.append(error)
        else:
            summary = next((c.get("summary") for c in knowledge if isinstance(c, dict) and c.get("summary")), None)
            if summary:
                lines.append(summary)
                lines.append("")
                lines.append("_Sources:_")
            seen = set()
            for chunk in knowledge:
                if not isinstance(chunk, dict):
                    continue
                if chunk.get("heading") in seen:
                    continue
                seen.add(chunk.get("heading"))
                lines.append(f"- **{chunk.get('heading')}** ({chunk.get('source')}): {_chunk_text(chunk)[:220]}...")
        lines.append("")

    if academic:
        if error := _error_note("academic", academic):
            lines.append(error)
        else:
            lines.append("**Attendance eligibility:**")
            lines.append(f"- Attendance: {academic['attendance_pct']}% — status: **{academic['eligibility']}**")
            lines.append(f"- {academic['note']}")
        lines.append("")

    if email:
        if error := _error_note("communication", email):
            lines.append(error)
        else:
            lines.append("**Drafted email:**")
            lines.append(f"- To: {email['to']} | Subject: {email['subject']} | Status: {email['status']}")
            lines.append(f"- Body:\n{email['body']}")

    return "\n".join(lines)


def _render_personalize(results: dict) -> str:
    lines = ["**Personalized recommendations**", ""]
    academic = _agent_output(results, "academic")
    events = _agent_output(results, "events")

    if academic:
        if error := _error_note("academic", academic):
            lines.append(error)
        else:
            classes = academic.get("classes", [])
            lines.append(f"**Today's classes ({academic.get('day')}):**")
            if classes:
                for cls in classes:
                    lines.append(f"- {cls['start']}–{cls['end']} {cls['title']} ({cls['code']}) @ {cls['room']}")
            else:
                lines.append("- No classes scheduled.")
        lines.append("")

    if events:
        if error := _error_note("events", events):
            lines.append(error)
        else:
            recs = events.get("recommendations", {})
            event_list = recs.get("events", [])
            lines.append("**Upcoming AI/ML events:**")
            if event_list:
                for event in event_list:
                    lines.append(f"- {event['date']} {event['start']} — {event['title']} ({event['type']}) @ {event['location']}")
            else:
                lines.append("- None found.")
            lines.append("")
            club_list = recs.get("clubs", [])
            lines.append("**Suggested clubs:**")
            if club_list:
                for club in club_list:
                    lines.append(f"- {club['name']} — {', '.join(club['tags'])} ({club['meeting']})")
            else:
                lines.append("- None found.")

    return "\n".join(lines)


def _render_single(results: dict, agent_name: str, header: str) -> str:
    lines = [f"**{header}**", ""]
    output = _agent_output(results, agent_name)
    if error := _error_note(agent_name, output):
        lines.append(error)
        return "\n".join(lines)
    if not output:
        return "\n".join(lines)
    if agent_name == "knowledge":
        for chunk in output[:3]:
            lines.append(f"- *{chunk['source']}* — **{chunk['heading']}**")
            lines.append(f"  {_chunk_text(chunk)[:200]}...")
    elif agent_name == "placement":
        lines.append(f"{output.get('internship')}: "
                     f"{'ELIGIBLE' if output.get('eligible') else 'NOT ELIGIBLE'}")
        for check in output.get("checks", []):
            mark = "✓" if check["met"] else "✗"
            lines.append(f"- {mark} {check['criterion']}: {check['detail']}")
        for drive in output.get("drives", []):
            lines.append(f"- {drive['company']} {drive['role']} — ₹{drive['package_lpa']} LPA | "
                         f"{drive['drive_date']} | deadline {drive['application_deadline']}")
        if a2a := output.get("a2a"):
            lines.append("")
            lines.append(f"**Inter-agent message → {a2a['to']} agent:** {a2a['message']}")
            lines.append(f"**{a2a['to']} agent replied:**")
            for rec in a2a["reply"]:
                lines.append(f"- {rec}")
    elif agent_name == "communication":
        lines.append(f"To: {output.get('to')} | Subject: {output.get('subject')} | Status: {output.get('status')}")
        lines.append(output.get("body", ""))
    elif agent_name == "academic":
        lines.append(f"Day: {output.get('day')} | Attendance: {output.get('attendance_pct')}% — "
                     f"**{output.get('eligibility')}**")
        if output.get("day_note"):
            lines.append(f"- {output['day_note']}")
        for cls in output.get("classes", []):
            lines.append(f"- {cls['start']}–{cls['end']} {cls['title']} ({cls['code']}) @ {cls['room']}")
        if output.get("faculty"):
            lines.append("")
            lines.append("**Faculty:**")
            for f in output["faculty"]["faculty"]:
                lines.append(f"- {f['name']} ({f['designation']}, {f['department']}) — {f['office']}")
    elif agent_name == "student_services":
        lines.extend(_render_student_services(output))
    elif agent_name == "events":
        for k, v in output.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append(str(output))
    return "\n".join(lines)


def _render_student_services(output: dict) -> list[str]:
    lines = []
    for key, section in output.items():
        stype = section.get("type", key)
        lines.append(f"- **{stype}:**")
        if stype == "hostel_vacancy":
            for h in section.get("hostels", []):
                lines.append(f"    {h['name']} ({h['type']}) — {h['available']} seats free | Warden: {h['warden']} | {h['contact']}")
        elif stype == "hostel_list":
            for h in section.get("hostels", []):
                lines.append(f"    {h['name']} ({h['type']}) | Warden: {h['warden']} | {h['contact']}")
        elif stype == "library_info":
            lines.append(f"    {section.get('timing')}")
        elif stype == "scholarships":
            for s in section.get("scholarships", []):
                flag = "✓ likely eligible" if s.get("likely_eligible") else "✗ not eligible"
                lines.append(f"    {s['name']} — ₹{s['amount']} | {flag} | deadline {s['deadline']}")
        elif stype == "transport":
            for r in section.get("routes", []):
                lines.append(f"    {r['route']} ({r['vehicle_type']}) — {r['timing']} | {r['contact']}")
        elif stype in ("grievances_list", "grievances_track"):
            for g in section.get("grievances", []):
                suffix = f" | updated {g['last_updated']}" if g.get("last_updated") else ""
                lines.append(f"    {g['id']} — {g['subject']} ({g['status']}){suffix}")
        elif stype == "lostfound":
            for item in section.get("items", []):
                lines.append(f"    {item['item']} ({item['category']}) @ {item['location']} — {item['status']} | {item['contact']}")
        else:
            lines.append(f"    {section}")
    return lines


def _render_general(results: dict) -> str:
    for name in ("knowledge", "academic", "placement", "events", "communication", "student_services", "notification_calendar"):
        if name in results:
            return _render_single(results, name, name.capitalize() + " agent result")
    return "I could not process the request."


_RENDERERS = {
    "chain": _render_chain,
    "reason": _render_reason,
    "personalize": _render_personalize,
    "placement": lambda r: _render_single(r, "placement", "Placement eligibility"),
    "academic": lambda r: _render_single(r, "academic", "Academic info"),
    "events": lambda r: _render_single(r, "events", "Events"),
    "knowledge": lambda r: _render_single(r, "knowledge", "Knowledge base"),
    "student_services": lambda r: _render_single(r, "student_services", "Student services"),
    "notification_calendar": lambda r: _render_single(r, "notification_calendar", "Notification/Calendar"),
    "general": _render_general,
}


def _agent_output(results: dict, agent_name: str) -> dict | None:
    result = results.get(agent_name)
    if not result:
        return None
    if result.get("error"):
        return {"error": result["error"]}
    return result.get("output") or {}


def _error_note(agent_name: str, output) -> str | None:
    if isinstance(output, dict) and output.get("error"):
        return f"⚠ {agent_name} agent unavailable — {output['error']}"
    return None


def _chunk_text(chunk: dict) -> str:
    lines = chunk["text"].splitlines()
    if lines and lines[0].strip() == chunk["heading"]:
        lines = lines[1:]
    return "\n".join(lines).strip()
