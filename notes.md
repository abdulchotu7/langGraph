# LangGraph — interview prep notes

## 1. Core building blocks
- **StateGraph** — you define a graph over a shared state object; nodes read
  it, return updates, edges route between nodes.
- **MessagesState** — the standard state schema: just `{"messages": [...]}`,
  where messages merge via the `add_messages` reducer (appends, doesn't
  overwrite). `invoke` takes `{"messages": [{"role": "user", ...}]}`.
- **START / END** — entry and terminal markers; every run goes START → … → END.
- **compile()** — turns the builder into a runnable graph. Always compile last.

## 2. Nodes
- `add_node(name, action)` — **name first, then the function**. Swapped args
  was our first real bug (`add_node(model, name="model")` silently misregisters).
- A node receives the **full state dict**, not a slice of it. That's why a raw
  chat model can't be a node — it expects a message list, but gets
  `{"messages": [...]}`. Wrap it:
  ```python
  def call_model(state: MessagesState):
      return {"messages": model.invoke(state["messages"])}
  ```

## 3. Tools (the agent loop)
- `@tool` turns a function into an LLM-callable tool. Its **docstring is the
  tool description** the model sees — write it well, it affects tool choice.
- Verified live: the docstring goes to the model **verbatim** — the request
  payload contains `"description": "<your docstring>"` alongside `name`
  and `parameters` (built from type hints). No paraphrasing, no hidden layer.
- The user never names the tool. Each turn the model gets the message + the
  full tool menu and matches intent → description itself. It may also pick
  *none* ("Hi!" matches nothing → straight to END).
- Corollaries: descriptions compete (vague tools misfire as count grows),
  and the model only emits the call as JSON — `ToolNode` executes it.
- `model.bind_tools([...])` gives the model the option to emit tool calls
  instead of a final answer.
- `ToolNode` executes the requested tools; `tools_condition` routes:
  model → tools → model → … → END when no more tool calls.
- Pattern: `add_edge(START, "model")`, `add_conditional_edges("model",
  tools_condition)`, `add_edge("tools", "model")`.
- Multiple tools: just extend both lists (`bind_tools` + `ToolNode`) — the
  model picks the right one per turn from names + docstrings. Ours now:
  weather (weatherstack), currency (Frankfurter, no key), Wikipedia search.
- A tool can chain HTTP calls internally (Wikipedia: search → summary).
  One tool = one job from the model's view, however many requests inside.

## 5. LangSmith tracing
- LangGraph apps trace **automatically** — just set `LANGSMITH_TRACING=true`,
  `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` in `.env`. Zero code changes.
- Do NOT put `@traceable` on graph nodes: each node run is already a span,
  so the decorator only adds a duplicate nested span (noise).
- `@traceable` is for **standalone functions outside a graph** (helpers,
  scripts) that you want visible in a trace.

## 6. System prompt
- No system prompt = model on defaults + tool descriptions. Works until an
  ambiguous query gets answered from memory instead of via a tool.
- Bake it into the node (prepend `SystemMessage` if none present), not the
  entrypoint — then CLI, API server, and Studio all get it.
- Ours: travel assistant persona + "always use tools, never guess numbers
  from memory" (models hallucinate rates) + short answers with source named.
- AGENTS.md is injected into the system prompt at startup (read once,
  appended under a header). A model can't follow conventions it can't see —
  this is the same trick Cursor/Claude use.

## 7. Tool safety (local/powerful tools)
- An LLM with bash + file read will eventually get a malicious or confused
  instruction (prompt injection) — so jail first, wire second.
- `read_file`: resolve the path and require it to stay under project root
  (`is_relative_to`); `../../.ssh/id_rsa` returns an error string, not data.
- Reads are allowed in TWO roots — project + `~/.agents/skills` — so the
  agent can follow skill-referenced sibling files (e.g. TDD's `mocking.md`).
  Bash stays project-jailed: reading outside is safe, executing outside isn't.
- `bash`: fixed cwd (project root), 30s timeout, truncated output, small
  denylist (`rm -rf`, `sudo`, …). Denylists are theater against a real
  adversary — the cwd jail + timeout do the real work.
- Tools return error **strings**, never raise: a raised exception fails the
  whole run, an error string lets the model recover and try again.
  Seen live: `patch_file` with `old_text=""` returned
  "matches 914 times, must be unique" — the model re-anchored and carried on.

## 8. Skills (progressive disclosure)
- `skills/<name>/SKILL.md` with frontmatter (`name`, `description`).
- `list_skills` returns name + description lines (cheap, model calls it to
  discover); `load_skill(name)` returns the full instructions, jailed to
  `skills/`. Bodies stay out of context until relevant — same pattern as
  Claude Code skills.
- Two roots: project `skills/` first, then `~/.agents/skills` (tagged
  `[global]`), project wins on collision. 38 skills live, zero copies.

## 9. MCP (fff file search)
- MCP tools join the same two lists via `MultiServerMCPClient` (stdio) +
  `asyncio.run(client.get_tools())` once at startup. No special casing —
  `bind_tools`/`ToolNode` treat them like locals. 12 tools now, 3 via MCP.
- Binary resolved env → PATH → `~/.local/bin`, fail fast if missing.
- New *dependency* (pyproject) needs a server restart — hot reload can't pip-install.

## 10. Gotchas we actually hit
- **Wrong interpreter**: system python has no deps → `ModuleNotFoundError`.
  Always `.venv/bin/python` or `uv run`.
- **`getpass` on import crashes non-tty runs** (`EOFError`). Read keys from
  env/`.env`, fail fast with a clear message instead.
- **AFC warning** ("use Chat.send_message instead of Models.generate_content"):
  Automatic Function Calling = the SDK auto-looping tool calls internally.
  Comes from inside langchain_google_genai, harmless when we run our own
  LangGraph tool loop. Ignorable noise.
- **MCP tools are async-only**: `langchain-mcp-adapters` tools define
  `_arun` but no `_run`, so any MCP call under sync `graph.invoke()` dies
  with `NotImplementedError: StructuredTool does not support sync
  invocation`. The CLI must use `await graph.ainvoke()` (the dev server is
  async, which is why this only bites locally). Found live: a deny-path
  test crashed only *after* refusing — the model reached for MCP grep to
  suggest an alternative.

## 11. langgraph dev ops (learned debugging a stuck run)
- `langgraph dev` needs the Docker daemon; "worked yesterday, broken today"
  was Docker Desktop down. The graph itself imported fine standalone — always
  split graph bugs from server bugs first:
  `.venv/bin/python -c "import weather_agent.graph"`.
- The server API is all curl-able (`:2024`): `GET /threads/{id}/state`
  (next node, per-task errors, messages), `GET .../history?limit=N`
  (checkpoint trail), `GET .../runs` (statuses),
  `POST .../runs/{run_id}/cancel`, `DELETE /threads/{id}`.
- A dead server leaves runs stuck at `running` forever — status is just a DB
  row. Ours "ran 2 days"; real activity was a ~70s burst, the rest was a
  stale row. Cancel flips it to `interrupted`.
- New thread ≠ kill old: old threads persist in server storage (disk only,
  idle). Delete in Studio, or set `ttl` in langgraph.json for auto-expiry.

## 12. Recursion limit: the server default is 10011, not 25
- Library default is 25, but the dev/API server reads
  `LANGGRAPH_DEFAULT_RECURSION_LIMIT`, default **10011** (found in
  langgraph_api source). Our 500-checkpoint loop never tripped anything.
- Set it in `.env` (`LANGGRAPH_DEFAULT_RECURSION_LIMIT=50`) — dev loads
  `.env` into the server process (verified in the CLI source). Needs a
  server restart to take effect. An explicit per-run value (Studio Config
  panel) overrides this default.
- Can't be set in graph.py: the server requires the export to be a `Pregel`
  and rejects `with_config` wrappers (checked `langgraph_api/graph.py`).
  Per-run override lives in Studio's Config panel.
- **How it's measured** (read `pregel/_loop.py`, v1.2.11 — not docs lore):
  the unit is the **tick (super-step), not the node call**. Each tick runs
  all currently-triggered nodes (parallel ones share one tick); the guard
  `step > start_step + recursion_limit + 1` fires `out_of_steps` →
  GraphRecursionError. The "stop condition" in the message just means the
  graph running out of work (tasks empty → `done`, i.e. reaching END).
- Consequences: sequential nodes burn budget 1:1. Our loop is
  model → review → tools = **3 ticks per agent round**, so limit 30 ≈ 10
  tool rounds (the review node made each loop 50% pricier than the old
  2-node cycle). And the budget **re-arms on every resume** (`stop` is
  recomputed from the current step each invoke) — the cap bounds
  unattended stretches, not total length across human approvals.

## 13. Runaway-loop anatomy (the Exa incident)
- 500+ checkpoints but max Pregel step 17: the damage was **parallel
  fan-out** (dozens of write_file/bash calls per step), not deep recursion.
  A step cap would NOT have caught it.
- Why it spiraled: tools return error *strings* (good for recovery) + no Exa
  tool existed + the skill said `pip install` (no pip in a uv-only project)
  → the model kept getting try-again material instead of a hard stop.
- Fixes applied: model `timeout=60` (ChatGoogleGenerativeAI `timeout`, alias
  `request_timeout`), recursion cap 50, native search/fetch tools. Still
  open: `parallel_tool_calls=False` to serialize tool use.

## 14. Native tools vs skills vs MCP (Exa verdict)
- The `build-with-exa` skill led with the pip-install SDK path and the agent
  followed it literally → 100+ files. Skill removed; native tools replaced it.
- `search_exa(query)`: fixed minimal request (query + highlights — the skill's
  own recommended shape), 30s timeout, errors as strings. `fetch_exa(url)`:
  POST /contents, highlights only, 8000-char cap to protect context.
- MCP ≠ more capable: Exa MCP wraps the same endpoints
  (search/fetch/agent) — packaging, not power. For a small model, 1 tool
  with 1 param beats 4 tools with dozens of params (fewer decisions =
  fewer loops). No new deps: httpx was already there, skipped exa-py.

## 15. Checkpointers & Persistence
- **Definition**: Checkpointers save a snapshot of graph state at each super-step boundary, organized into threads (`thread_id`).
- **Core Capabilities**:
  - **Human-in-the-Loop**: Inspect, interrupt, approve, and resume execution.
  - **Memory / Threads**: Persist conversation history and state across sessions using `thread_id` in config.
  - **Time Travel**: Replay prior graph executions, debug steps, or fork state at arbitrary checkpoints.
  - **Fault Tolerance**: Recover from crashes or node failures without re-running successfully completed tasks in the same super-step (via task-level `checkpoint_writes`).
- **Durability Modes**:
  - `"exit"`: Persists only on graph exit (fastest, no mid-execution crash recovery).
  - `"async"`: Persists asynchronously while next step runs.
  - `"sync"`: Persists synchronously before next step starts (highest durability, slower).
- **Delta Channels (Beta)**: Stores sentinels (`MISSING`) instead of full channel values in checkpoint blobs, reconstructing state by replaying ancestor writes (`O(1)` per step for accumulating channels like `messages`).

## 16. Human-in-the-Loop & Interrupts (`interrupt()` + `Command`)
- **`interrupt()`**: Pauses graph execution inside a node and yields arbitrary payload (e.g. proposed tool calls) to the caller. Requires a checkpointer (e.g., `InMemorySaver`) to persist graph state at the pause.
- **`Command` Routing**: Used to resume from an interrupt by returning `Command(resume=...)`. The value passed to `resume` is received by the interrupted `interrupt()` call.
- **Node implementation**: Inspects incoming tool calls (`state["messages"][-1].tool_calls`), identifies risky actions (`_risky`: file writes, patches, risky bash commands), calls `interrupt()`, and conditionally routes:
  - If approved (`_approved(decision)`): `Command(goto="tools")`.
  - If denied: `Command(goto="model", update={"messages": [ToolMessage(...)]})` so the model receives rejection feedback and can explain or adjust.

## 17. MCP (Model Context Protocol) Integration
- **Client**: `MultiServerMCPClient` from `langchain_mcp_adapters.client` connects to MCP servers over `stdio` (e.g. `fff-mcp` for lightning-fast file search).
- **Startup Loading**: `asyncio.run(client.get_tools())` fetches MCP tools once at application startup.
- **Seamless Merging**: MCP tools are combined directly with local tools into `ALL_TOOLS` (`bind_tools` and `ToolNode`), requiring zero special-casing in graph execution.
