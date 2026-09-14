import httpx
from langchain_core.tools import tool

from abduls_pi.config import WEATHER_API_KEY

FAILURE_MARKERS = ("Weather lookup failed",)


@tool
def call_weather_api(query: str) -> str:
    """Get the current weather for a city. Args: query: city name, e.g. 'London'."""
    res = httpx.get(
        "http://api.weatherstack.com/current",
        params={"access_key": WEATHER_API_KEY, "query": query},
        timeout=10,
    )
    data = res.json()
    if "current" not in data:
        return f"Weather lookup failed: {data.get('error', {}).get('info', data)}"
    c = data["current"]
    desc = c["weather_descriptions"][0] if c.get("weather_descriptions") else ""
    return f"{query}: {c['temperature']}C, {desc}, humidity {c['humidity']}%, wind {c['wind_speed']} kph"
