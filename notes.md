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
- `model.bind_tools([...])` gives the model the option to emit tool calls
  instead of a final answer.
- `ToolNode` executes the requested tools; `tools_condition` routes:
  model → tools → model → … → END when no more tool calls.
- Pattern: `add_edge(START, "model")`, `add_conditional_edges("model",
  tools_condition)`, `add_edge("tools", "model")`.

## 5. LangSmith tracing
- LangGraph apps trace **automatically** — just set `LANGSMITH_TRACING=true`,
  `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` in `.env`. Zero code changes.
- Do NOT put `@traceable` on graph nodes: each node run is already a span,
  so the decorator only adds a duplicate nested span (noise).
- `@traceable` is for **standalone functions outside a graph** (helpers,
  scripts) that you want visible in a trace.

## 4. Gotchas we actually hit
- **Wrong interpreter**: system python has no deps → `ModuleNotFoundError`.
  Always `.venv/bin/python` or `uv run`.
- **`getpass` on import crashes non-tty runs** (`EOFError`). Read keys from
  env/`.env`, fail fast with a clear message instead.
- **AFC warning** ("use Chat.send_message instead of Models.generate_content"):
  Automatic Function Calling = the SDK auto-looping tool calls internally.
  Comes from inside langchain_google_genai, harmless when we run our own
  LangGraph tool loop. Ignorable noise.
