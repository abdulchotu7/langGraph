from abduls_pi.tools.bash import FAILURE_MARKERS as _bash_markers
from abduls_pi.tools.bash import bash
from abduls_pi.tools.currency import FAILURE_MARKERS as _currency_markers
from abduls_pi.tools.currency import convert_currency
from abduls_pi.tools.exa import FAILURE_MARKERS as _exa_markers
from abduls_pi.tools.exa import fetch_exa, search_exa
from abduls_pi.tools.patch import FAILURE_MARKERS as _patch_markers
from abduls_pi.tools.patch import patch_file
from abduls_pi.tools.plan import FAILURE_MARKERS as _plan_markers
from abduls_pi.tools.plan import update_todos
from abduls_pi.tools.read import FAILURE_MARKERS as _read_markers
from abduls_pi.tools.read import read_file
from abduls_pi.tools.skills import FAILURE_MARKERS as _skills_markers
from abduls_pi.tools.skills import list_skills, load_skill
from abduls_pi.tools.weather import FAILURE_MARKERS as _weather_markers
from abduls_pi.tools.weather import call_weather_api
from abduls_pi.tools.wikipedia import FAILURE_MARKERS as _wikipedia_markers
from abduls_pi.tools.wikipedia import search_wikipedia
from abduls_pi.tools.write import FAILURE_MARKERS as _write_markers
from abduls_pi.tools.write import write_file

# Failure vocabulary lives with the tool that emits it; the review
# failure-counter aggregates instead of hardcoding mirrored strings.
FAILURE_MARKERS: tuple[str, ...] = tuple(
    dict.fromkeys(
        _bash_markers + _currency_markers + _exa_markers + _patch_markers + _plan_markers + _read_markers + _skills_markers + _weather_markers + _wikipedia_markers + _write_markers
    )
)

__all__ = ["bash", "call_weather_api", "convert_currency", "fetch_exa", "list_skills", "load_skill", "patch_file", "read_file", "search_exa", "search_wikipedia", "update_todos", "write_file"]
