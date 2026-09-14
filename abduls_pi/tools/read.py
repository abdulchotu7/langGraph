from langchain_core.tools import tool

from abduls_pi.tools._sandbox import allowed_read

FAILURE_MARKERS = ("Error",)


@tool
def read_file(file_path: str) -> str:
    """Read a text file from the project (e.g. 'notes.md') or a global skill file (e.g. 'tdd/mocking.md')."""
    try:
        p = allowed_read(file_path)
        if p is None:
            return "Error: file not found in project or skills library, or path escapes allowed roots."
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > 50_000:
            return text[:50_000] + f"\n... [truncated, {len(text)} chars total]"
        return text
    except Exception as e:
        return f"Error reading file: {e}"
