import httpx
from langchain_core.tools import tool

from weather_agent.config import EXA_API_KEY


@tool
def search_exa(query: str) -> str:
    """Search the web with Exa and return highlights from the top results. Args: query: search query, e.g. 'Qwen3 benchmarks'."""
    if not EXA_API_KEY:
        return "Error: EXA_API_KEY is not set. Add it to .env."
    try:
        res = httpx.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": EXA_API_KEY},
            json={"query": query, "contents": {"highlights": True}},
            timeout=30,
        )
        data = res.json()
    except Exception as e:
        return f"Error: Exa search failed: {e}"
    results = data.get("results", [])
    if not results:
        return f"No Exa results for '{query}'."
    out = []
    for r in results:
        highlights = " ".join(r.get("highlights", [])[:3])
        out.append(f"{r.get('title', 'untitled')} — {r.get('url', '')}\n{highlights}")
    return "\n\n".join(out)
