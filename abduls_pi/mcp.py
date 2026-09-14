"""MCP servers: spawn once at startup, tools join ALL_TOOLS like locals."""

import asyncio
import os
import shutil
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

from abduls_pi.tools._sandbox import ROOT


def load_mcp_tools() -> list:
    binary = os.environ.get("FFF_MCP_BIN") or shutil.which("fff-mcp") or str(Path.home() / ".local/bin/fff-mcp")
    if not Path(binary).is_file():
        raise RuntimeError(f"fff-mcp binary not found at {binary}. Install: brew install dmtrKovalenko/fff/fff-mcp")
    client = MultiServerMCPClient({"fff": {"command": binary, "args": [str(ROOT)], "transport": "stdio"}})
    return asyncio.run(client.get_tools())
