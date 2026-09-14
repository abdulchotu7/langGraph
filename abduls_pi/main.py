"""Entrypoint: uv run weather-agent | .venv/bin/python -m abduls_pi.main"""

import asyncio
import sys

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from abduls_pi import config as _config  # noqa: F401 — validates env on import
from abduls_pi.graph import builder


async def amain(question: str) -> None:
    # Dev server injects its own persistence; the CLI needs one for interrupts.
    # Async invoke: MCP tools are async-only and crash under sync invoke.
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "cli"}}
    state = await graph.ainvoke({"messages": [{"role": "user", "content": question}]}, config)
    while (snapshot := await graph.aget_state(config)) and snapshot.interrupts:
        payload = snapshot.interrupts[0].value
        print("Approval needed:", payload.get("question"))
        for c in payload.get("tool_calls", []):
            print(f"  - {c['name']} {c['args']}")
        answer = input("approve? [y/N] ").strip().lower()
        state = await graph.ainvoke(Command(resume={"approve": answer == "y"}), config)
    print(state["messages"][-1].content)


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "what is the weather in Delhi?"
    asyncio.run(amain(question))


if __name__ == "__main__":
    main()
