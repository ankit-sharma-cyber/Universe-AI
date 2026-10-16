from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from agents import academic, communication, events, knowledge, notification_calendar, placement, student_services
from orchestrator import approval, merge, planner
from orchestrator.state import AgentState

AGENT_MODULES = {
    "academic": academic,
    "events": events,
    "communication": communication,
    "knowledge": knowledge,
    "placement": placement,
    "student_services": student_services,
    "notification_calendar": notification_calendar,
}
NODE_NAMES = [*AGENT_MODULES, "approval", "merge", "planner"]

_DEFAULT_SAVER = InMemorySaver()
_COMPILED = None


def _next_node(state):
    if state.get("replan"):
        return "planner"
    plan = state.get("plan") or []
    step = state.get("step", 0)
    if step < len(plan):
        return plan[step]
    return "merge"


def _agent_node(module):
    def node(state):
        step = state.get("step", 0)
        try:
            result = module.run(
                state.get("request", ""),
                state.get("student_id", "S2023001"),
                state=state,
            )
            trace_detail = result.get("trace", "")
        except Exception as exc:
            result = {"output": None, "error": str(exc), "confidence": 0.1}
            trace_detail = f"agent error: {exc}"
        result.setdefault("confidence", 0.5)
        update = {
            "results": {**state.get("results", {}), module.NAME: result},
            "trace": [*state.get("trace", []), {"node": module.NAME, "detail": trace_detail}],
            "step": step + 1,
        }
        if result.get("error"):
            # Adaptive re-planning: signal a failed step so the planner can reroute.
            update["replan"] = {"agent": module.NAME, "reason": result["error"]}
        return update

    return node


def build(saver=None):
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner.planner_node)
    for name, module in AGENT_MODULES.items():
        graph.add_node(name, _agent_node(module))
    graph.add_node("approval", approval.approval_node)
    graph.add_node("merge", merge.merge_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", _next_node, NODE_NAMES)
    for name in [*AGENT_MODULES, "approval"]:
        graph.add_conditional_edges(name, _next_node, NODE_NAMES)
    graph.add_edge("merge", END)

    return graph.compile(checkpointer=saver or _DEFAULT_SAVER)


def get_graph(saver=None):
    """Reuse a process-wide compiled graph so session memory survives across HTTP calls."""
    global _COMPILED
    if saver is not None:
        return build(saver)
    if _COMPILED is None:
        _COMPILED = build(_DEFAULT_SAVER)
    return _COMPILED


def run(
    request: str | None = None,
    student_id: str = "S2023001",
    thread_id: str = "default",
    saver=None,
    resume: dict | None = None,
) -> dict:
    graph = get_graph(saver) if saver is None else build(saver)
    config = {"configurable": {"thread_id": thread_id}}
    if resume is not None:
        return graph.invoke(Command(resume=resume), config=config)
    return graph.invoke(_initial_state(request, student_id), config=config)


def _initial_state(request: str | None, student_id: str) -> dict:
    return {
        "request": request,
        "student_id": student_id,
        "messages": [{"role": "user", "content": request}],
        # reset per-turn fields so prior plan/results do not leak via checkpointer
        "intent": None,
        "plan": [],
        "step": 0,
        "results": {},
        "trace": [],
        "approved": None,
        "final": None,
        "error": None,
        "confidence": None,
        "replan": None,
    }


def stream_events(
    request: str | None = None,
    student_id: str = "S2023001",
    thread_id: str = "default",
    saver=None,
    resume: dict | None = None,
):
    """Yield normalized per-node events as the graph executes (for SSE / live timelines)."""
    graph = get_graph(saver) if saver is None else build(saver)
    config = {"configurable": {"thread_id": thread_id}}
    stream_input = Command(resume=resume) if resume is not None else _initial_state(request, student_id)

    final_seen = False
    for update in graph.stream(stream_input, config=config, stream_mode="updates"):
        if "__interrupt__" in update:
            yield {"event": "needs_approval", "thread_id": thread_id, **_interrupt_payload(update["__interrupt__"])}
            return
        for node, delta in update.items():
            if not isinstance(delta, dict):
                continue
            event = {
                "event": "node",
                "node": node,
                "thread_id": thread_id,
                "trace": delta.get("trace", []),
            }
            if delta.get("intent") is not None:
                event["intent"] = delta["intent"]
            if delta.get("plan"):
                event["plan"] = delta["plan"]
            if delta.get("final") is not None:
                event["final"] = delta["final"]
                final_seen = True
            if delta.get("confidence") is not None:
                event["confidence"] = delta["confidence"]
            yield event

    if final_seen:
        yield {"event": "done", "thread_id": thread_id}


def _interrupt_payload(interrupt) -> dict:
    payload = interrupt[0].value if isinstance(interrupt, tuple | list) and interrupt else interrupt
    if hasattr(payload, "value"):
        payload = payload.value
    return {"interrupt": payload}


def serialize_result(result: dict, thread_id: str) -> dict:
    """Normalize a LangGraph result for API clients."""
    if result is None:
        return {"status": "error", "error": "Empty orchestrator result", "thread_id": thread_id}

    interrupt = result.get("__interrupt__")
    if interrupt:
        return {
            "status": "needs_approval",
            "thread_id": thread_id,
            **_interrupt_payload(interrupt),
            "intent": result.get("intent"),
            "plan": result.get("plan"),
            "confidence": result.get("confidence"),
            "trace": result.get("trace", []),
            "results": _public_results(result.get("results")),
            "messages": result.get("messages", []),
        }

    return {
        "status": "ok",
        "thread_id": thread_id,
        "final": result.get("final"),
        "intent": result.get("intent"),
        "plan": result.get("plan"),
        "confidence": result.get("confidence"),
        "trace": result.get("trace", []),
        "results": _public_results(result.get("results")),
        "messages": result.get("messages", []),
        "error": result.get("error"),
    }


def _public_results(results: dict | None) -> dict:
    if not results:
        return {}
    public = {}
    for name, value in results.items():
        if not isinstance(value, dict):
            public[name] = value
            continue
        public[name] = {
            "output": value.get("output"),
            "error": value.get("error"),
            "confidence": value.get("confidence"),
            "trace": value.get("trace"),
        }
    return public
