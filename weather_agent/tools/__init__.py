from weather_agent.tools.bash import FAILURE_MARKERS as _bash_markers
from weather_agent.tools.bash import bash
from weather_agent.tools.currency import FAILURE_MARKERS as _currency_markers
from weather_agent.tools.currency import convert_currency
from weather_agent.tools.exa import FAILURE_MARKERS as _exa_markers
from weather_agent.tools.exa import fetch_exa, search_exa
from weather_agent.tools.patch import FAILURE_MARKERS as _patch_markers
from weather_agent.tools.patch import patch_file
from weather_agent.tools.plan import FAILURE_MARKERS as _plan_markers
from weather_agent.tools.plan import update_todos
from weather_agent.tools.read import FAILURE_MARKERS as _read_markers
from weather_agent.tools.read import read_file
from weather_agent.tools.skills import FAILURE_MARKERS as _skills_markers
from weather_agent.tools.skills import list_skills, load_skill
from weather_agent.tools.weather import FAILURE_MARKERS as _weather_markers
from weather_agent.tools.weather import call_weather_api
from weather_agent.tools.wikipedia import FAILURE_MARKERS as _wikipedia_markers
from weather_agent.tools.wikipedia import search_wikipedia
from weather_agent.tools.write import FAILURE_MARKERS as _write_markers
from weather_agent.tools.write import write_file

# Failure vocabulary lives with the tool that emits it; the review
# failure-counter aggregates instead of hardcoding mirrored strings.
FAILURE_MARKERS: tuple[str, ...] = tuple(
    dict.fromkeys(
        _bash_markers + _currency_markers + _exa_markers + _patch_markers + _plan_markers + _read_markers + _skills_markers + _weather_markers + _wikipedia_markers + _write_markers
    )
)

__all__ = ["bash", "call_weather_api", "convert_currency", "fetch_exa", "list_skills", "load_skill", "patch_file", "read_file", "search_exa", "search_wikipedia", "update_todos", "write_file"]
