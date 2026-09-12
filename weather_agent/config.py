"""Centralised settings. Fails fast with a clear message if keys are missing."""

import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to .env (see .env.example).")
    return value


GOOGLE_API_KEY: str = _required("GOOGLE_API_KEY")
WEATHER_API_KEY: str = _required("WEATHER_API_KEY")
