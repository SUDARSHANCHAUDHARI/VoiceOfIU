"""
MCP server manager — loads configured MCP servers and makes them available as tools.
Config file: ~/.config/VoiceOfIU/mcp_servers.json

Format:
{
  "servers": [
    {"name": "home-assistant", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-home-assistant"]},
    {"name": "github", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"]}
  ]
}
"""

import json
import logging
import os

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.expanduser("~/.config/VoiceOfIU/mcp_servers.json")
_servers: list[dict] = []


def load():
    global _servers
    if not os.path.exists(CONFIG_PATH):
        _servers = []
        return
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        _servers = data.get("servers", [])
        log.info(f"MCP: loaded {len(_servers)} server(s)")
    except Exception as e:
        log.warning(f"MCP config load failed: {e}")
        _servers = []


def list_servers() -> list[str]:
    return [s["name"] for s in _servers]


def get_server_config(name: str) -> dict | None:
    return next((s for s in _servers if s["name"] == name), None)


def save_default_config():
    """Write an example config so the user knows the format."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    example = {
        "servers": [
            {"name": "example", "command": "npx",
             "args": ["-y", "@modelcontextprotocol/server-example"],
             "note": "Replace with real MCP server — see https://github.com/modelcontextprotocol"}
        ]
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(example, f, indent=2)
    log.info(f"MCP example config written to {CONFIG_PATH}")
