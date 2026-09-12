"""LangGraph agent: model <-> tools loop."""

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from weather_agent.config import REASONING_EFFORT
from weather_agent.mcp import load_mcp_tools
from weather_agent.prompt import build_system
from weather_agent.tools import bash, call_weather_api, convert_currency, list_skills, load_skill, patch_file, read_file, search_wikipedia, write_file

ALL_TOOLS = [bash, call_weather_api, convert_currency, list_skills, load_skill, patch_file, read_file, search_wikipedia, write_file, *load_mcp_tools()]

model = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_retries=2, reasoning_effort=REASONING_EFFORT)
model_with_tools = model.bind_tools(ALL_TOOLS)
SYSTEM = build_system()


def call_model(state: MessagesState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM, *messages]
    return {"messages": model_with_tools.invoke(messages)}


graph = StateGraph(MessagesState)
graph.add_node("model", call_model)
graph.add_node("tools", ToolNode(ALL_TOOLS))
graph.add_edge(START, "model")
graph.add_conditional_edges("model", tools_condition)
graph.add_edge("tools", "model")
graph = graph.compile()
