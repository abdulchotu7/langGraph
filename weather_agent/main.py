"""Entrypoint: uv run weather-agent | .venv/bin/python -m weather_agent.main"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from weather_agent import config as _config  # noqa: F401 — validates env on import
from weather_agent.graph import builder


def main() -> None:
    # Dev server injects its own persistence; the CLI needs one for interrupts.
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "cli"}}
    state = graph.invoke({"messages": [{"role": "user", "content": "what is the weather in Delhi?"}]}, config)
    while (snapshot := graph.get_state(config)) and snapshot.interrupts:
        payload = snapshot.interrupts[0].value
        print("Approval needed:", payload.get("question"))
        for c in payload.get("tool_calls", []):
            print(f"  - {c['name']} {c['args']}")
        answer = input("approve? [y/N] ").strip().lower()
        state = graph.invoke(Command(resume={"approve": answer == "y"}), config)
    print(state["messages"][-1].content)


if __name__ == "__main__":
    main()
