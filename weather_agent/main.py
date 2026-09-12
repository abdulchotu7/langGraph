"""Entrypoint: uv run weather-agent | .venv/bin/python -m weather_agent.main"""

from . import config as _config  # noqa: F401 — validates env on import
from .graph import graph


def main() -> None:
    result = graph.invoke({"messages": [{"role": "user", "content": "what is the weather in London?"}]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
