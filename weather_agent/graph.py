"""LangGraph agent: model <-> review <-> tools loop, human approval before edits."""

import re

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from weather_agent.config import REASONING_EFFORT
from weather_agent.mcp import load_mcp_tools
from weather_agent.prompt import build_system
from weather_agent.tools import bash, call_weather_api, convert_currency, fetch_exa, list_skills, load_skill, patch_file, read_file, search_exa, search_wikipedia, write_file

try:
    MCP_TOOLS = load_mcp_tools()
except Exception as e:  # fff-mcp missing (e.g. prod container): run degraded, don't kill graph load
    print(f"Warning: MCP tools unavailable ({e}). Continuing with local tools only.")
    MCP_TOOLS = []

ALL_TOOLS = [bash, call_weather_api, convert_currency, fetch_exa, list_skills, load_skill, patch_file, read_file, search_exa, search_wikipedia, write_file, *MCP_TOOLS]

model = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_retries=2, timeout=60, reasoning_effort=REASONING_EFFORT)
model_with_tools = model.bind_tools(ALL_TOOLS)
SYSTEM = build_system()


class AgentState(MessagesState):
    consecutive_failures: int


def call_model(state: AgentState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM, *messages]
    return {"messages": model_with_tools.invoke(messages)}


FAIL_MARKERS = ("Error", "Currency conversion failed", "Weather lookup failed", "No Exa results", "No content found", "No Wikipedia article")
MAX_FAILURES = 3
SOURCE_NUDGE = "Source check: your answer contains numbers but no page was fetched"


def _batch_failed(messages: list) -> bool:
    """True if the previous turn's tool results were all failures."""
    batch = []
    for m in reversed(messages[:-1]):  # skip pending AI message
        if m.type != "tool":
            break
        batch.append(m)
    return bool(batch) and all(str(m.content).startswith(FAIL_MARKERS) for m in batch)


def _needs_sources(messages: list) -> bool:
    """Final answer has digits, search was used, but nothing was ever fetched. Once only."""
    last = messages[-1]
    if getattr(last, "tool_calls", None):
        return False
    text = last.content if isinstance(last.content, str) else str(last.content)
    if not re.search(r"\d", text):
        return False
    called, nudged = set(), False
    for m in messages:
        for c in (getattr(m, "tool_calls", None) or []):
            called.add(c["name"])
        if m.type == "system" and str(m.content).startswith("Source check:"):
            nudged = True
    return "search_exa" in called and "fetch_exa" not in called and not nudged


EDIT_TOOLS = {"write_file", "patch_file"}
RISKY_BASH = (">", "rm ", "mv ", "cp ", "mkdir", "touch ", "tee ", "chmod", "pip install", "pip uninstall", "uv add", "uv remove", "npm install")


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


def review(state: AgentState) -> Command:
    calls = getattr(state["messages"][-1], "tool_calls", None) or []
    failures = state.get("consecutive_failures", 0) + 1 if _batch_failed(state["messages"]) else 0
    if failures >= MAX_FAILURES:
        return Command(
            goto="model",
            update={
                "messages": [SystemMessage(content="Stop: one approach has failed 3 times. Do not call more tools. Report what you tried and ask the user how to proceed.")],
                "consecutive_failures": 0,
            },
        )
    if not calls:
        if _needs_sources(state["messages"]):
            return Command(
                goto="model",
                update={
                    "messages": [SystemMessage(content=SOURCE_NUDGE + ": call fetch_exa on the key URLs behind those digits (or drop/flag numbers you cannot source), then answer again.")],
                    "consecutive_failures": failures,
                },
            )
        return Command(goto=END, update={"consecutive_failures": failures})
    risky = [c for c in calls if _risky(c)]
    if not risky:
        return Command(goto="tools", update={"consecutive_failures": failures})
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


builder = StateGraph(AgentState)
builder.add_node("model", call_model)
builder.add_node("review", review)
builder.add_node("tools", ToolNode(ALL_TOOLS))
builder.add_edge(START, "model")
builder.add_edge("model", "review")
builder.add_edge("tools", "model")
graph = builder.compile()
