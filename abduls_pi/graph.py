"""LangGraph agent: model <-> review <-> tools loop, human approval before edits."""

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from abduls_pi.config import REASONING_EFFORT
from abduls_pi.mcp import load_mcp_tools
from abduls_pi.policies import POLICIES, _batch_failed
from abduls_pi.prompt import build_system
from abduls_pi.tools import bash, call_weather_api, convert_currency, fetch_exa, list_skills, load_skill, patch_file, read_file, search_exa, search_wikipedia, update_todos, write_file

try:
    MCP_TOOLS = load_mcp_tools()
except Exception as e:  # fff-mcp missing (e.g. prod container): run degraded, don't kill graph load
    print(f"Warning: MCP tools unavailable ({e}). Continuing with local tools only.")
    MCP_TOOLS = []

ALL_TOOLS = [bash, call_weather_api, convert_currency, fetch_exa, list_skills, load_skill, patch_file, read_file, search_exa, search_wikipedia, update_todos, write_file, *MCP_TOOLS]

model = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_retries=2, timeout=60, reasoning_effort=REASONING_EFFORT)
model_with_tools = model.bind_tools(ALL_TOOLS)
SYSTEM = build_system()


class AgentState(MessagesState):
    consecutive_failures: int
    todos: list


def call_model(state: AgentState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM, *messages]
    return {"messages": model_with_tools.invoke(messages)}


def review(state: AgentState) -> Command:
    calls = getattr(state["messages"][-1], "tool_calls", None) or []
    failures = state.get("consecutive_failures", 0) + 1 if _batch_failed(state["messages"]) else 0
    for policy in POLICIES:
        verdict = policy(state, calls, failures)
        if verdict is not None:
            return verdict
    if not calls:
        return Command(goto=END, update={"consecutive_failures": failures})
    return Command(goto="tools", update={"consecutive_failures": failures})


builder = StateGraph(AgentState)
builder.add_node("model", call_model)
builder.add_node("review", review)
builder.add_node("tools", ToolNode(ALL_TOOLS))
builder.add_edge(START, "model")
builder.add_edge("model", "review")
builder.add_edge("tools", "model")
graph = builder.compile()
