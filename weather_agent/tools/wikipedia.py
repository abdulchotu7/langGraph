import httpx
from langchain_core.tools import tool

_HEADERS = {"User-Agent": "weather-agent/0.1 (learning project)"}

FAILURE_MARKERS = ("No Wikipedia article",)


@tool
def search_wikipedia(query: str) -> str:
    """Search Wikipedia and return a short summary of the top match. Args: query: topic to look up."""
    hits = httpx.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": query, "srlimit": 1, "format": "json"},
        headers=_HEADERS,
        timeout=10,
    ).json()
    search = hits.get("query", {}).get("search", [])
    if not search:
        return f"No Wikipedia article found for '{query}'."
    title = search[0]["title"]
    summary = httpx.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
        headers=_HEADERS,
        timeout=10,
    ).json()
    return f"{summary.get('title', title)}: {summary.get('extract', 'no summary available')}"
