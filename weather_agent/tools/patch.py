from langchain_core.tools import tool

from weather_agent.tools._sandbox import ROOT

FAILURE_MARKERS = ("Error",)


@tool
def patch_file(file_path: str, old_text: str, new_text: str) -> str:
    """Replace one exact block of text in a project file. Args: file_path: path relative to project root; old_text: must occur exactly once; new_text: replacement."""
    try:
        p = (ROOT / file_path).resolve()
        if not p.is_relative_to(ROOT):
            return "Error: path escapes the project directory."
        if not p.is_file():
            return f"Error: '{file_path}' does not exist."
        text = p.read_text(encoding="utf-8", errors="replace")
        n = text.count(old_text)
        if n == 0:
            return "Error: old_text not found in file."
        if n > 1:
            return f"Error: old_text matches {n} times, must be unique."
        p.write_text(text.replace(old_text, new_text), encoding="utf-8")
        return f"Patched '{file_path}'."
    except Exception as e:
        return f"Error patching file: {e}"
