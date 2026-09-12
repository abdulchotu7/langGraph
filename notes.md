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
