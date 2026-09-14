"""Review policies: approval gate + failure surrender. Append new policies to POLICIES; review stays untouched."""

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command, interrupt

from abduls_pi.tools import FAILURE_MARKERS

MAX_FAILURES = 3
STOP_NUDGE = "[automated check] Stop: one approach has failed 3 times. Do not call more tools. Report what you tried and ask the user how to proceed."

EDIT_TOOLS = {"write_file", "patch_file"}
RISKY_BASH = (">", "rm ", "mv ", "cp ", "mkdir", "touch ", "tee ", "chmod", "pip install", "pip uninstall", "uv add", "uv remove", "npm install")


def _batch_failed(messages: list) -> bool:
    """True if the previous turn's tool results were all failures."""
    batch = []
    for m in reversed(messages[:-1]):  # skip pending AI message
        if m.type != "tool":
            break
        batch.append(m)
    return bool(batch) and all(str(m.content).startswith(FAILURE_MARKERS) for m in batch)


def _risky(call: dict) -> bool:
    if call["name"] in EDIT_TOOLS:
        return True
    if call["name"] == "bash":
        return any(t in call["args"].get("command", "") for t in RISKY_BASH)
    return False


def _approved(value) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.lower() in ("approve", "accept", "continue", "yes")
    if isinstance(value, dict):
        decision = value.get("approve", value.get("action"))
        return decision is True or (isinstance(decision, str) and decision.lower() in ("approve", "accept", "continue"))
    return False


def _stop_policy(state, calls: list, failures: int) -> Command | None:
    if failures < MAX_FAILURES:
        return None
    # Answer pending calls + end on a user turn: Gemini rejects a
    # trailing AI/system turn ("model prefilling" error).
    skipped = [ToolMessage(content="Skipped: repeated failures, do not retry.", tool_call_id=c["id"]) for c in calls]
    return Command(
        goto="model",
        update={
            "messages": skipped + [HumanMessage(content=STOP_NUDGE)],
            "consecutive_failures": 0,
        },
    )


def _approval_policy(state, calls: list, failures: int) -> Command | None:
    risky = [c for c in calls if _risky(c)]
    if not risky:
        return None
    decision = interrupt({
        "question": "Allow these file edits / shell commands?",
        "tool_calls": [{"name": c["name"], "args": c["args"]} for c in risky],
    })
    if _approved(decision):
        return Command(goto="tools", update={"consecutive_failures": failures})
    return Command(
        goto="model",
        update={
            "messages": [ToolMessage(content="Denied by user. Do not perform it; explain briefly and suggest a safer alternative.", tool_call_id=c["id"]) for c in calls],
            "consecutive_failures": failures,
        },
    )


# Ordered: first match wins.
POLICIES = [_stop_policy, _approval_policy]
