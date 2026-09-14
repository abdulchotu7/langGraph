from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command

FAILURE_MARKERS = ("Error",)

STATUSES = ("pending", "in_progress", "completed")


def _render(todos: list) -> str:
    done = sum(1 for t in todos if t.get("status") == "completed")
    lines = [f"[plan] {done}/{len(todos)} done"]
    for t in todos:
        mark = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[t.get("status", "pending")]
        lines.append(f"- {mark} {t.get('subject', '?')}")
    return "\n".join(lines)


@tool
def update_todos(todos: list, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """Maintain the multi-step task plan. Pass the FULL list every time: [{'subject': str, 'status': 'pending'|'in_progress'|'completed'}], exactly one in_progress. Args: todos: the complete updated plan."""
    if not isinstance(todos, list) or not todos:
        return "Error: pass a non-empty list of {subject, status} dicts."
    for t in todos:
        if not isinstance(t, dict) or not t.get("subject") or t.get("status") not in STATUSES:
            return "Error: each item needs a subject and a status of pending/in_progress/completed."
    if sum(1 for t in todos if t.get("status") == "in_progress") > 1:
        return "Error: exactly one todo may be in_progress."
    # ToolNode requires a matching ToolMessage for every Command-returning
    # tool call; the rendered plan rides in it (a collapsed tool result in
    # Studio) instead of a fake-human message in the transcript.
    return Command(
        update={
            "todos": todos,
            "messages": [ToolMessage(content=_render(todos), tool_call_id=tool_call_id)],
        }
    )
