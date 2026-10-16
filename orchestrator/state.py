import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    request: str
    student_id: str
    intent: str
    plan: list[str]
    step: int
    results: dict[str, Any]
    trace: list[dict]
    approved: bool
    messages: Annotated[list[dict], operator.add]
    error: str
    final: str
    confidence: float
    replan: dict | None
