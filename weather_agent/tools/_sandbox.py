"""Local file tools. Both are jailed: the model can never reach outside the project."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]