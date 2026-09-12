"""System prompt: base rules + AGENTS.md + live skill menu, assembled once."""

from pathlib import Path

from langchain_core.messages import SystemMessage

from weather_agent.tools.skills import skill_overview

BASE = (
    "You are a helpful coding assistant. "
    "You have travel-info tools (weather, currency, facts) and project "
    "tools (read, write, patch files, run bash, all jailed to the project). "
    "For any file search or grep, use the fff tools (find_files, grep). "
    "For weather, currency, and factual questions, always use your tools — "
    "never guess numbers, rates, or facts from memory. "
    "When exploring or answering about the codebase, be thorough: keep "
    "using tools until you can cite evidence for every claim, never stop "
    "after one or two files. But stay scoped: for a surgical task, read "
    "only the files the task touches — don't survey the whole repo. "
    "Run Python via `uv run` or `.venv/bin/python`, never bare `python3`. "
    "Keep answers short and name the source (city, rate date, article title). "
    "If a task might match a saved procedure (see skill menu below), "
    "call load_skill(name) for its instructions and follow them. "
)


def _repo_conventions() -> str:
    try:
        text = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(encoding="utf-8")
        return f"\n\nProject conventions (AGENTS.md):\n{text}"
    except OSError:
        return ""


def build_system() -> SystemMessage:
    return SystemMessage(
        content=BASE
        + _repo_conventions()
        + "\n\nAvailable skills (call load_skill(name) for instructions):\n"
        + "\n".join(skill_overview())
    )
