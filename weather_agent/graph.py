"""LangGraph agent: model <-> tools loop."""

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pathlib import Path

from weather_agent.tools import bash, call_weather_api, convert_currency, list_skills, load_skill, patch_file, read_file, search_wikipedia, write_file
from weather_agent.tools.skills import skill_overview

model = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_retries=2)
model_with_tools = model.bind_tools([bash, call_weather_api, convert_currency, list_skills, load_skill, patch_file, read_file, search_wikipedia, write_file])


def _repo_conventions() -> str:
    try:
        text = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(encoding="utf-8")
        return f"\n\nProject conventions (AGENTS.md):\n{text}"
    except OSError:
        return ""


SYSTEM = SystemMessage(
    content=(
        "You are a helpful coding assistant. "
        "You have travel-info tools (weather, currency, facts) and project "
        "tools (read, write, patch files, run bash, all jailed to the project). "
        "For weather, currency, and factual questions, always use your tools — "
        "never guess numbers, rates, or facts from memory. "
        "When exploring or answering about the codebase, be thorough: keep "
        "using tools until you can cite evidence for every claim, never stop "
        "after one or two files. But stay scoped: for a surgical task, read "
        "only the files the task touches — don't survey the whole repo. "
        "Run Python via `uv run` or `.venv/bin/python`, never bare `python3`. "
        "Keep answers short and name the source (city, rate date, article title). "
        "If a task might match a saved procedure (see skill menu below), "
        "call load_skill(name) for its instructions and follow them. "    )
    + _repo_conventions()
    + "\n\nAvailable skills (call load_skill(name) for instructions):\n"
    + "\n".join(skill_overview())
)


def call_model(state: MessagesState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM, *messages]
    return {"messages": model_with_tools.invoke(messages)}


graph = StateGraph(MessagesState)
graph.add_node("model", call_model)
graph.add_node("tools", ToolNode([bash, call_weather_api, convert_currency, list_skills, load_skill, patch_file, read_file, search_wikipedia, write_file]))
graph.add_edge(START, "model")
graph.add_conditional_edges("model", tools_condition)
graph.add_edge("tools", "model")
graph = graph.compile()
