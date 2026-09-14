import re
from pathlib import Path

from langchain_core.tools import tool

from weather_agent.tools._sandbox import GLOBAL_SKILLS, ROOT

FAILURE_MARKERS = ("Error",)

# Project skills first, then the user's global collection. Project wins on collision.


def _roots() -> list[tuple[str, Path]]:
    roots = [("project", ROOT / "skills")]
    if GLOBAL_SKILLS.is_dir():
        roots.append(("global", GLOBAL_SKILLS))
    return roots


def _frontmatter(path: Path) -> tuple[str, str]:
    """Return (description, body) from a SKILL.md file. No yaml dep needed."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return "", text
    desc = ""
    for line in m.group(1).splitlines():
        if line.startswith("description:"):
            desc = line.split(":", 1)[1].strip()
    return desc, m.group(2).strip()


def _find(skill: str) -> Path | None:
    for _, root in _roots():
        p = (root / skill / "SKILL.md").resolve()
        if str(p).startswith(str(root.resolve())) and p.is_file():
            return p
    return None


@tool
def list_skills() -> str:
    """List available skills as 'name: description'. The menu is also in your system prompt; call this to refresh it mid-session."""
    out = skill_overview()
    return "\n".join(out) if out else "No skills installed."


def skill_overview() -> list[str]:
    """Same listing without the tool wrapper, for baking into the system prompt."""
    seen, out = set(), []
    for scope, root in _roots():
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            f = d / "SKILL.md"
            if d.is_dir() and f.is_file() and d.name not in seen:
                seen.add(d.name)
                desc, _ = _frontmatter(f)
                tag = "" if scope == "project" else " [global]"
                out.append(f"{d.name}{tag}: {desc or 'no description'}")
    return out


@tool
def load_skill(skill: str) -> str:
    """Load a skill's full instructions by name. Args: skill: skill name from list_skills, e.g. 'tdd'."""
    p = _find(skill)
    if p is None:
        return f"Error: no skill named '{skill}'."
    text = p.read_text(encoding="utf-8")
    if len(text) > 30_000:
        return text[:30_000] + f"\n... [truncated, {len(text)} chars total]"
    return text


if __name__ == "__main__":
    print("roots:", _roots())