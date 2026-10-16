from langgraph.types import interrupt


def approval_node(state):
    """Pause the graph for human-in-the-loop approval before action-taking steps."""
    placement = (state.get("results") or {}).get("placement") or {}
    eligible = (placement.get("output") or {}).get("eligible")
    student_id = state.get("student_id")

    if eligible is False:
        return {
            "approved": True,
            "step": state.get("step", 0) + 1,
            "trace": [
                *state.get("trace", []),
                {"node": "approval", "detail": "no approval required: candidate is not eligible"},
            ],
        }

    decision = interrupt({
        "action": "register_for_workshop",
        "student_id": student_id,
        "message": "The orchestrator verified eligibility. Approve registering the student for the placement workshop?",
    })
    approved = bool(decision.get("approved"))
    return {
        "approved": approved,
        "step": state.get("step", 0) + 1,
        "trace": [
            *state.get("trace", []),
            {"node": "approval", "detail": f"human-in-the-loop decision: {'granted' if approved else 'declined'}"},
        ],
    }
