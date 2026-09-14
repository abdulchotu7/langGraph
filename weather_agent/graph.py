"""LangGraph agent: model <-> review <-> tools loop, human approval before edits."""

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from weather_agent.config import REASONING_EFFORT
from weather_agent.mcp import load_mcp_tools
from weather_agent.prompt import build_system
from weather_agent.tools import bash, call_weather_api, convert_currency, fetch_exa, list_skills, load_skill, patch_file, read_file, search_exa, search_wikipedia, write_file

ALL_TOOLS = [bash, call_weather_api, convert_currency, fetch_exa, list_skills, load_skill, patch_file, read_file, search_exa, search_wikipedia, write_file, *load_mcp_tools()]

model = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_retries=2, timeout=60, reasoning_effort=REASONING_EFFORT)
model_with_tools = model.bind_tools(ALL_TOOLS)
SYSTEM = build_system()


def call_model(state: MessagesState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM, *messages]
    return {"messages": model_with_tools.invoke(messages)}


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


def review(state: MessagesState) -> Command:
    calls = getattr(state["messages"][-1], "tool_calls", None) or []
    if not calls:
        return Command(goto=END)
    risky = [c for c in calls if _risky(c)]
    if not risky:
        return Command(goto="tools")
    decision = interrupt({
        "question": "Allow these file edits / shell commands?",
        "tool_calls": [{"name": c["name"], "args": c["args"]} for c in risky],
    })
    if _approved(decision):
        return Command(goto="tools")
    return Command(
        goto="model",
        update={"messages": [ToolMessage(content="Denied by user. Do not perform it; explain briefly and suggest a safer alternative.", tool_call_id=c["id"]) for c in calls]},
    )


builder = StateGraph(MessagesState)
builder.add_node("model", call_model)
builder.add_node("review", review)
builder.add_node("tools", ToolNode(ALL_TOOLS))
builder.add_edge(START, "model")
builder.add_edge("model", "review")
builder.add_edge("tools", "model")
graph = builder.compile()
