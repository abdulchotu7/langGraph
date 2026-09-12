from pathlib import Path

from langchain_core.tools import tool

from weather_agent.tools._sandbox import ROOT


@tool
def read_file(file_path: str) -> str:
    """Read a text file inside the project. Args: file_path: path relative to project root, e.g. 'notes.md'."""
    try:
        p = (ROOT / file_path).resolve()
        if not p.is_relative_to(ROOT):
            return "Error: path escapes the project directory."
        if not p.is_file():
            return f"Error: '{file_path}' does not exist or is not a file."
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > 50_000:
            return text[:50_000] + f"\n... [truncated, {len(text)} chars total]"
        return text
    except Exception as e:
        return f"Error reading file: {e}"
