import subprocess

from langchain_core.tools import tool

from weather_agent.tools._sandbox import ROOT

_DENY = ("rm -rf", "sudo", "mkfs", ":(){", "shutdown", "reboot", "> /dev/")


@tool
def bash(command: str) -> str:
    """Run a bash command inside the project directory. Args: command: the command, e.g. 'ls'. 30s timeout, output truncated."""
    if any(d in command for d in _DENY):
        return "Error: command blocked for safety."
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=ROOT)
        out = (r.stdout + r.stderr)[-20_000:]
        return out if out.strip() else f"(no output, exit {r.returncode})"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30s."
    except Exception as e:
        return f"Error: {e}"
