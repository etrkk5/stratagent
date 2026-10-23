# Documentation-based host setup

Official documentation reviewed October 23, 2026. These are setup instructions and format checks, not recordings of native host sessions. The [P5 scope decision](interoperability.md#scope-decision--october-23-2026) waives live multi-host sessions, 30 human reviews and independent installation trials for the current checkpoint.

## Shared local bridge

Install StratAgent in a virtual environment, then start a session in an existing project with `stratagent session-start` as described in [orchestration.md](orchestration.md). Replace the Python path, workspace path and `SESSION_ID` in the snippets below with your actual values. On Windows use the virtual environment's absolute `Scripts/python.exe` path and JSON/TOML escaping for backslashes.

The command is the local environment's Python executable. Arguments are separate strings: `-m`, `stratagent`, `serve`, `--workspace`, the absolute project directory, `--orchestration`, and the session ID. This scopes the bridge to proposal request/submission for that one session. Leaving out `--orchestration` deliberately selects the broader default read-only tool set instead; it is not the same integration.

Review and manually connect the bridge using the host's settings interface. These snippets are not written to active settings by StratAgent. Connecting starts the local StratAgent process; it does not authorize search, install external resources or activate their MCP proposals. Separately approve research and installation through the CLI. Authentication, context handling and any other host tools remain the host's responsibility.

## Claude Code

Local project skills use `.claude/skills/<name>/SKILL.md`; project agents use `.claude/agents/<name>.md`. StratAgent limits generated agent headers to `Read, Grep, Glob` and requests `permissionMode: plan`. Parent permission settings can override that mode; the header alone is not enforcement evidence. [Official skills](https://code.claude.com/docs/en/skills), [subagents](https://code.claude.com/docs/en/sub-agents).

Claude reserves the local skill names `synced` and `anthropic-skills`. Adapter 1.1.0 maps those to `sa-synced` and `sa-anthropic-skills` in both the destination and generated `name`; references/notices remain beside the exported skill. Other hosts retain their original names. Existing destination collisions still stop installation, and source evidence is unchanged. Source names containing `:` are already refused by StratAgent's portable-name policy. Cloud/Cowork skill loading differs from local Claude Code and is outside this adapter's declared scope.

Review this bridge JSON through Claude Code's MCP configuration flow:

```json
{
  "mcpServers": {
    "stratagent": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["-m", "stratagent", "serve", "--workspace", "/absolute/path/to/project", "--orchestration", "SESSION_ID"]
    }
  }
}
```

The documented project MCP file is `.mcp.json`. Using the snippet in active settings or passing it to a client permits startup; an inert proposal's location is what keeps StratAgent's external-server exports inactive. Do not assume the Antigravity `disabled` field works in Claude. Use Claude's `/mcp` management and documented project trust controls. For a temporary config, consult `--mcp-config` and `--strict-mcp-config` for your installed version. [Official MCP configuration](https://code.claude.com/docs/en/mcp).

## Codex

The supported export is `.agents/skills/<name>/SKILL.md`, including role instructions represented as skills. This adapter does not generate native Codex multi-agent runtime configuration. Explicit skill invocation uses `$<skill-name>`. [Official OpenAI skills documentation](https://learn.chatgpt.com/docs/build-skills).

Review a project `.codex/config.toml` or user configuration entry:

```toml
[mcp_servers.stratagent]
enabled = false
command = "/absolute/path/to/venv/bin/python"
args = ["-m", "stratagent", "serve", "--workspace", "/absolute/path/to/project", "--orchestration", "SESSION_ID"]
```

This starts disabled. After reviewing the local bridge, enable it using the host's supported configuration/UI, then reconnect. Check `codex mcp get stratagent --json` and `/mcp`; parsing a configuration does not prove a model used its tools. The documented TOML uses `mcp_servers`, `command`/`args` for stdio, `url` for Streamable HTTP and `enabled: false` semantics. [Official OpenAI MCP documentation](https://learn.chatgpt.com/docs/extend/mcp).

## Antigravity

Current official docs support `.agents/skills/<name>/SKILL.md` and, for App/CLI custom agents, `.agents/agents/<name>.md` as well as the folder form `<name>/agent.md`. StratAgent uses the flat file form. Its headers use documented read tools `view_file`/`grep_search`, `subagent: true`, `mainAgent: false`, inherited model and command execution `off`. These settings do not establish OS sandboxing or universal IDE agent compatibility. [Official skills](https://antigravity.google/docs/skills), [custom agents](https://antigravity.google/docs/subagents?tab=cli). The `/agents` guide emphasizes the folder form; both forms appear in the custom-agent schema, so the existing flat renderer is retained.

Review a workspace `.agents/mcp_config.json` entry:

```json
{
  "mcpServers": {
    "stratagent": {
      "disabled": true,
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["-m", "stratagent", "serve", "--workspace", "/absolute/path/to/project", "--orchestration", "SESSION_ID"]
    }
  }
}
```

Enable only after review through the host's MCP controls. Remote proposals use `serverUrl`; local proposals use `command`/`args`; `disabled: true` is documented. Do not copy Codex's `enabled` field or legacy `httpUrl` into this schema. These are manual setup instructions, not a recorded successful Antigravity connection. [Official MCP configuration](https://antigravity.google/docs/mcp).

## Compatibility assumptions

The reviewed docs describe supported current formats, not a tested minimum version range. Local CLI/App sessions are assumed to honor their documented discovery, field and tool behavior; older versions, account policies, managed settings and cloud surfaces may differ. Human usefulness and independent onboarding are explicitly unevaluated. Original hash approval, conflict refusal, source policy and inactive external-MCP output remain enforced by StratAgent; the scope waiver does not bypass them.
