"""Local file tools. Reads are allowed in the project and the skills library;
execution (bash) stays jailed to the project."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GLOBAL_SKILLS = Path.home() / ".agents" / "skills"


def allowed_read(user_path: str) -> Path | None:
    """Resolve user_path against each readable root. None if it escapes all of them."""
    for base in (ROOT, GLOBAL_SKILLS):
        p = (base / user_path).resolve()
        try:
            if str(p).startswith(str(base.resolve())) and p.is_file():
                return p
        except OSError:
            continue
    return None
