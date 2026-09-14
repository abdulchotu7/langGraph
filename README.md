# Coding Agent (LangGraph)

A small but real coding agent: Gemini + file tools + web research, with human
approval gates, failure handling, and per-project workspaces. Built to learn
LangGraph by debugging real incidents — see `notes.md` for the full story.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in keys
```

| Var | Needed for |
|---|---|
| `GOOGLE_API_KEY` | the model (required) |
| `WEATHER_API_KEY` | weather tool |
| `EXA_API_KEY` | web search + page fetch |
| `LANGSMITH_*` | tracing (automatic once set) |
| `REASONING_EFFORT` | minimal/low/medium/high (default `low`) |
| `WORKSPACE` | target project dir (defaults to this repo) |
| `LANGGRAPH_DEFAULT_RECURSION_LIMIT` | step budget for Studio/`up` (default 50) |

Requires Python ≥3.12 (`uv` handles it). Never use system `python3`.

## Run

```bash
# CLI — single question, terminal approvals (y/n)
uv run weather-agent
uv run weather-agent "write demo.txt containing pineapple"

# Work on a REAL project (reads, writes, bash, conventions all follow it)
WORKSPACE=~/Projects/my-app uv run weather-agent "…"
# tip: use a scratch git branch, keep approvals on

# LangGraph Studio (hot-reload dev server, thread panel, Approve/Deny UI)
langgraph dev        # API :2024 — needs Docker Desktop running

# Prod-shaped (API + Postgres + Redis containers)
langgraph up         # API :8123
```

## Behavior

- **Safe tools pass silently** (read, search, weather). **Edits + mutating
  shell commands pause** for approval — approve-all or deny-all per batch.
- **Multi-step tasks** get a plan (`update_todos`); check the `[plan]` echoes.
- **3 strikes**: one failing approach 3× → it stops and reports instead of looping.
- **Research standard**: ≥3 sources, fetch full pages for numbers, flag single-sourced claims.
- Threads persist per conversation (Studio panel or `thread_id`); cross-thread
  memory is still on the roadmap.

## Layout

```
weather_agent/config.py    env loading, fails fast on missing keys
weather_agent/tools/       one file per tool (bash, read, write, patch,
                           exa search/fetch, plan, skills, weather, …)
weather_agent/mcp.py       fff file-search via MCP (skipped if binary missing)
weather_agent/prompt.py    system prompt: RULES + target AGENTS.md + skill menu
weather_agent/graph.py     state, nodes, wiring (policies live in policies.py)
weather_agent/policies.py  approval gate + failure surrender (append here)
weather_agent/main.py      CLI entrypoint (own in-memory persistence)
notes.md                   learnings, incidents, gotchas
```

## Troubleshooting

- `langgraph dev` fails → is Docker Desktop running? (`docker ps`)
- `Recursion limit reached` → long task; raise the limit (Studio run config
  or `LANGGRAPH_DEFAULT_RECURSION_LIMIT`), ~3 ticks per agent loop.
- `langgraph up` build fails on Python version → `python_version` in
  `langgraph.json` must satisfy `requires-python`.
- Run stuck `running` → server died; cancel it
  (`POST /threads/{id}/runs/{run_id}/cancel`) and restart.
- approval gate + `uv run` pipes → `uv` eats stdin; use `.venv/bin/python -m`
  when piping answers.
