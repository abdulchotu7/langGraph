Goal:

Learn LangGraph clearly — all important parts of it — then finally build a
production app with tools, MCP, and memory for my agent.

Tech stack:
- language: python (>=3.12)
- env: uv (.venv, pyproject.toml — no requirements.txt, no pip)
- LLM: Gemini via langchain-google-genai (GOOGLE_API_KEY)
- graph: langgraph

Layout (standard package, flat):
- weather_agent/config.py — env loading, fails fast if keys missing
- weather_agent/tools/ — one file per tool, exported via __init__.py
- weather_agent/graph.py — pure graph definition (no I/O on import)
- weather_agent/main.py — entrypoint only

Commands:
- run: `uv run weather-agent` or `.venv/bin/python -m weather_agent.main`
- Never run with system `python3` (Apple 3.9, no deps) — always `.venv` or `uv run`

Env (.env, see .env.example):
- GOOGLE_API_KEY — Gemini
- WEATHER_API_KEY — weatherstack
- LANGSMITH_TRACING=true, LANGSMITH_API_KEY, LANGSMITH_PROJECT — tracing (no code needed)

Conventions:
- Nodes take full state, return a state update dict (e.g. `{"messages": ...}`).
- Never pass a raw chat model to add_node — wrap it in a function.
- Absolute imports inside the package (`from weather_agent.tools import ...`) —
  the LangGraph server loads graph.py by file path, so relative imports crash
  with `GraphLoadError: attempted relative import with no known parent package`.
- No graph.invoke() at import time — I/O lives in main.py under __main__.
- notes.md is interview prep notes — keep appending LangGraph learnings there.
