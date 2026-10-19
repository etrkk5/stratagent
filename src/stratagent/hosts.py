"""Trusted, pure host adapters; no runtime plugin loading or installation."""
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable

from .common import StratagentError, canonical


@dataclass(frozen=True)
class HostAdapter:
    name: str
    skill_root: str
    agent_root: str | None = None
    agent_header: str = ""
    mcp_renderer: Callable[[str, dict], tuple[str, bytes]] | None = None

    def role_path(self, name):
        if self.agent_root is not None:
            return f"{self.agent_root}/{name}.md"
        return f"{self.skill_root}/{name}/SKILL.md"

    def owns_resource(self, path):
        return (path.startswith(self.skill_root + "/") and path.endswith("/SKILL.md")) or (
            self.agent_root is not None and path.startswith(self.agent_root + "/") and path.endswith(".md"))

    def capabilities(self):
        return {"id": self.name, "skills": True, "skill_root": self.skill_root,
                "role_format": "native-agent" if self.agent_root is not None else "portable-skill",
                "role_root": self.agent_root or self.skill_root, "mcp_proposals": self.mcp_renderer is not None,
                "automatic_execution": False}


def claude_mcp(name, selected):
    entry = ({"type": "http", "url": selected["url"]} if selected["type"] == "http"
             else {"command": selected["command"], "args": selected["args"]})
    return "claude.mcp.json", canonical({"mcpServers": {name: entry}}) + b"\n"


def codex_mcp(name, selected):
    content = f'[mcp_servers."{name}"]\nenabled = false\n'
    if selected["type"] == "http":
        content += "url = " + json.dumps(selected["url"]) + "\n"
    else:
        content += "command = \"npx\"\nargs = " + json.dumps(selected["args"]) + "\n"
    return "codex.config.toml", content.encode()


def antigravity_mcp(name, selected):
    entry = ({"serverUrl": selected["url"], "disabled": True} if selected["type"] == "http"
             else {"command": selected["command"], "args": selected["args"], "disabled": True})
    return "antigravity.mcp_config.json", canonical({"mcpServers": {name: entry}}) + b"\n"


ADAPTERS = MappingProxyType({adapter.name: adapter for adapter in (
    HostAdapter("claude", ".claude/skills", ".claude/agents", "tools: Read, Grep, Glob\npermissionMode: plan\n", claude_mcp),
    HostAdapter("codex", ".agents/skills", mcp_renderer=codex_mcp),
    HostAdapter("antigravity", ".agents/skills", ".agents/agents",
                'tools: [view_file, grep_search]\nmainAgent: false\nsubagent: true\nmodel: inherit\ncommandExecutionPolicy: "off"\n', antigravity_mcp),
    HostAdapter("generic", ".stratagent/portable/skills"),
)})
DEFAULT_TARGETS = ("claude", "codex", "antigravity")


def platforms(values):
    if not isinstance(values, list) or not values or any(not isinstance(value, str) or value not in ADAPTERS for value in values):
        raise StratagentError("Platforms must be a nonempty list of " + ", ".join(sorted(ADAPTERS)) + ".")
    return sorted(set(values))


def get_adapter(name):
    platforms([name])
    return ADAPTERS[name]


def catalog():
    return {"schema_version": 1, "platforms": [ADAPTERS[name].capabilities() for name in sorted(ADAPTERS)],
            "defaults": list(DEFAULT_TARGETS),
            "note": "Generic exports portable Agent Skills and a task plan; host-specific MCP settings require a supported adapter. No external adapters are loaded automatically."}


def resource_paths(outputs, targets):
    adapters = [get_adapter(target) for target in platforms(targets)]
    return [output["path"] for output in outputs if any(adapter.owns_resource(output["path"]) for adapter in adapters)]


def merge_outputs(destination, outputs):
    for path, data in outputs.items():
        if path in destination and destination[path] != data:
            raise StratagentError(f"Adapters produced conflicting content for the same output: {path}")
        destination[path] = data
