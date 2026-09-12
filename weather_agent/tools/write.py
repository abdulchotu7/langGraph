from langchain_core.tools import tool

from weather_agent.tools._sandbox import ROOT


@tool
def write_file(file_path: str, content: str) -> str:
    """Create or overwrite a text file inside the project. Args: file_path: path relative to project root; content: full file text."""
    try:
        if len(content) > 200_000:
            return "Error: content too large (200k char cap)."
        p = (ROOT / file_path).resolve()
        if not p.is_relative_to(ROOT):
            return "Error: path escapes the project directory."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to '{file_path}'."
    except Exception as e:
        return f"Error writing file: {e}"
