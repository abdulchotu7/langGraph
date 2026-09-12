"""LangGraph agent: model <-> tools loop."""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .tools import call_weather_api

model = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_retries=2)
model_with_tools = model.bind_tools([call_weather_api])


def call_model(state: MessagesState):
    return {"messages": model_with_tools.invoke(state["messages"])}


graph = StateGraph(MessagesState)
graph.add_node("model", call_model)
graph.add_node("tools", ToolNode([call_weather_api]))
graph.add_edge(START, "model")
graph.add_conditional_edges("model", tools_condition)
graph.add_edge("tools", "model")
graph = graph.compile()
