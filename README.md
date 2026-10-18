# Stratagent

[![Tests](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml/badge.svg)](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml)

**A reviewable supply chain for agent skills.**

Describe what you are building. Discover relevant skills and sub-agent definitions on GitHub, inspect their source and policy findings, and assemble approved configurations for Claude Code, Codex and portable Agent Skills environments.

Stratagent treats reusable agent instructions as software dependencies: **pin the source, inspect the content, approve the exact plan, and record what was installed.**

The CLI-first MVP combines transparent candidate ranking, commit-pinned snapshots, repository allowlists, content-bound approval and a provenance lockfile. A read-only MCP server exposes analysis, discovery and inspection to coding environments while keeping installation authority in the local CLI.

Python 3.11+. No third-party runtime dependencies, LLM API key or Git CLI required.

## Why Stratagent

A reusable skill can carry instructions, references, scripts, permissions and license obligations. Installing it is a dependency decision. Stratagent makes that decision inspectable:

| Question | Evidence Stratagent provides |
| --- | --- |
| What is this resource relevant to? | Keyword matches, documentation structure signals and task-role recommendations |
| Where did it come from? | Repository, immutable commit, entry path and verified Git blob identities |
| What will be installed? | Exact output paths, file sizes and SHA-256 hashes in a deterministic dry-run |
| What did I approve? | A full plan digest bound to source content, destination and generated outputs |
| Has anything changed? | A provenance lockfile and verification of every installed output |

This is an early, working release. Planning is deterministic, static checks require human interpretation, and agent processes are not launched automatically.

## Quick start

Clone the repository and install locally:

```sh
git clone https://github.com/etrkk5/stratagent.git
cd stratagent
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/stratagent --help
.venv/bin/stratagent demo --workspace ./demo-workspace --apply
.venv/bin/stratagent verify --workspace ./demo-workspace
```

The offline demo uses original examples included in this project. Omit `--apply` to prepare review evidence and dry-run plans without activating platform files. Use a new directory for each demo. Its synthetic commits are explicitly labeled `demo-offline` in provenance.

Run directly from source without installing:

```sh
PYTHONPATH=src python3 -m stratagent plan "Build a Python API agent for data analysis"
PYTHONPATH=src python3 -m stratagent demo --workspace ./another-demo --apply
```

## Discover, review, approve

```sh
mkdir my-agent
.venv/bin/stratagent init "Build a Python API agent with data analysis, tests and security review" \
  --workspace ./my-agent --platforms claude,codex,generic

.venv/bin/stratagent discover --workspace ./my-agent \
  --repo openai/skills \
  --repo VoltAgent/awesome-claude-code-subagents --limit 4

.venv/bin/stratagent recommend --workspace ./my-agent
```

Without `--repo`, discovery combines GitHub repository search with the seed catalogs `openai/skills`, `anthropics/skills` and `VoltAgent/awesome-claude-code-subagents`. Seeds are discovery sources, not trusted repositories. Search uses repository search followed by pinned Git tree/blob API calls; authenticated code search is not required. Results are bounded, not exhaustive.

Review a candidate using its `id` from the JSON output:

```sh
# Replace CANDIDATE_ID and APPROVAL_SHA256 with values from the output.
.venv/bin/stratagent inspect CANDIDATE_ID --content --workspace ./my-agent
.venv/bin/stratagent install CANDIDATE_ID --dry-run --workspace ./my-agent

# After reviewing all source files, licenses, findings and output paths:
.venv/bin/stratagent allow owner/repo --workspace ./my-agent
.venv/bin/stratagent install CANDIDATE_ID --apply \
  --approve APPROVAL_SHA256 --workspace ./my-agent
```

Use the candidate's actual repository name for `allow`. Installation requires the full `approval` SHA-256 from its dry-run, not the separate `review_digest`. Approval binds the absolute destination, source commit, source hashes, license, scanner version and generated file hashes. Changes invalidate the approval. Blocked candidates have no force-install option.

Generate task configurations after installing the resources you selected:

```sh
.venv/bin/stratagent configure --dry-run --workspace ./my-agent
# Use this configuration preview's own approval value:
.venv/bin/stratagent configure --apply --approve APPROVAL_SHA256 --workspace ./my-agent
.venv/bin/stratagent verify --workspace ./my-agent
.venv/bin/stratagent status --workspace ./my-agent
```

Configuration produces a five-role task graph covering architecture, implementation, testing, security review and integration. Only explicitly installed resources that pass verification are associated with tasks. Recommendations do not install or approve resources. Launching coding-agent processes is outside this MVP.

## CLI reference

All results are JSON. `--workspace` works before or after the subcommand.

| Command | Behavior |
| --- | --- |
| `plan PROMPT` | Analyze requirements and tasks without writing files |
| `init PROMPT` | Create a manifest, empty lockfile and empty repository allowlist |
| `discover` | Discover, pin, assess and rank GitHub definitions; cache review evidence |
| `inspect ID --content` | Read findings and all cached, untrusted source text |
| `recommend` | Suggest eligible candidates for each task |
| `allow owner/repo` | Explicitly allow one exact repository locally |
| `install ID` | Preview by default; write only with `--apply --approve HASH` |
| `configure` | Preview or approve generated task configurations |
| `verify` | Check SHA-256 hashes of every locked output |
| `status` | Show the plan, candidates, policy and verification result |
| `demo` | Run an offline demo with original fixtures |
| `serve` | Run the read-only MCP server over stdio |

Exit codes: `0` success, `2` input/policy/access error, `3` verification drift, `4` discovery returned no candidates, `130` user interruption. Partial failures appear in `errors`; global rate/budget limits stop further requests and set `stopped_early`.

## Workspace layout and portability

```text
my-agent/
├── .stratagent/
│   ├── manifest.json          # Request, tasks, candidates, findings and scores
│   ├── policy.json            # Explicit local repository allowlist
│   ├── cache/<digest>.json    # Inert source text stored as JSON/base64
│   ├── lock.json              # Sources, hashes, licenses and approval records
│   ├── task-plan.json         # Task graph and approved resource assignments
│   ├── portable/skills/       # Generic Agent Skills output
│   └── notices/               # Notices for adapted definitions
├── .agents/skills/            # Codex skills and text references
└── .claude/
    ├── skills/               # Claude Code skills and text references
    └── agents/               # Read-only Claude Code sub-agent definitions
```

Skill adapters emit only `name` and `description` metadata and preserve relative text references and license/notice files. Original source content remains in the evidence cache. Claude sub-agents use `Read, Grep, Glob` and `permissionMode: plan`; the parent environment's permission settings also apply. Codex roles are represented as portable skills, not native multi-agent runtime configuration.

Stratagent does not change user-authored `AGENTS.md`, `CLAUDE.md`, `.codex/config.toml`, hooks or existing files. Conflicts stop installation. Upgrades and removal are not automated yet.

## Security boundaries

- **Read-only network access.** Fixed-host HTTPS GET requests to GitHub's REST API, no redirects, request budgets and sanitized errors. Tokens are sent only in the API authorization header and never stored in manifests or lockfiles. TLS verification cannot be disabled; configure a trusted `SSL_CERT_FILE` if needed.
- **No external execution.** No Git clone, archive extraction, dependency installation, shell commands or plugin hooks run during discovery/installation. Installing Stratagent itself through `pip` is a separate package installation step.
- **Content integrity.** Sources are pinned to immutable commits. Git blob identities and file SHA-256 hashes are verified. Installation uses the reviewed snapshot, not a fresh download from a moving branch.
- **Separate approval gates.** The repository allowlist starts empty. Repository permission and exact plan-hash approval are both required. MCP cannot grant either permission.
- **Bounded inspection.** Limits are 256 KiB per file, 2 MiB/80 files per bundle, 8 MiB per HTTP response, 100 requests and 20 results per discovery. Truncated repository trees are refused.
- **Conservative file policy.** Symlinks, executables, submodules, traversal, absolute paths, control characters, non-portable paths and oversized/non-text content are refused. Installable bundles contain only `.md`, `.txt`, `.rst` and license/notice text. YAML, JSON, scripts and binaries block a bundle, including otherwise valid skills containing `agents/openai.yaml`.
- **Static risk signals.** Rules flag instruction overrides, remote shell execution, destructive commands, credential access and active permission/hook configuration. Security documentation can trigger false positives. These checks are not proof of safety; review every file before approval.
- **Conservative license matching.** Full supported license bodies are compared with pinned reference texts. Missing, unknown, customized or conflicting licenses are blocked. Supported texts are MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause and ISC. A match does not establish legal compatibility; review the actual notices and obligations.
- **Controlled local writes.** A directory lock serializes mutations. Ordinary failures roll back newly created files. Existing files are never overwritten; identical reinstallation verifies content before returning a no-op. There is no filesystem-wide power-loss transaction guarantee; run `verify` after interruption.

The local user and operating system are trusted. There is no signature/attestation protection against an attacker who can rewrite the manifest, cache and lockfile together, or OS sandbox protection against hostile concurrent replacement of parent directories. Activated skills remain subject to the coding environment's own security boundaries.

For GitHub rate limits, narrow discovery with `--repo`/`--limit` or set `GITHUB_TOKEN` with only the necessary read permissions. Stratagent does not read `.env` files.

## Read-only MCP server

```sh
.venv/bin/stratagent serve --workspace /absolute/path/to/my-agent
```

The server uses newline-delimited JSON-RPC over stdio with MCP protocol version `2025-03-26`. stdout contains protocol messages only. Tools are `stratagent_analyze`, `stratagent_status`, `stratagent_inspect`, `stratagent_preview` and `stratagent_discover`. MCP discovery reads from the network without saving files. The server is bound to one workspace, and tool arguments cannot redirect it elsewhere.

Adapt this example to your MCP client, replacing both paths:

```json
{
  "mcpServers": {
    "stratagent": {
      "command": "/absolute/path/to/stratagent/.venv/bin/stratagent",
      "args": ["serve", "--workspace", "/absolute/path/to/my-agent"]
    }
  }
}
```

This is a generic example; Stratagent does not modify user settings. Automated tests and an installed-CLI subprocess exchange verify stdio behavior. MCP Inspector and actual Claude Code/Codex client interoperability have not been tested.

## Development and verification

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip wheel . --no-deps --wheel-dir /tmp/stratagent-wheels
```

The 52 tests run without network access and cover pinned GitHub fixtures, integrity checks, malicious paths, symlink/executable handling, injection signals, license conflicts, approval scope, collisions, rollback, drift, task assignments, the CLI demo and MCP messages. Separate read-only live GitHub results are documented in [validation.md](docs/validation.md).

See [architecture.md](docs/architecture.md) for implementation boundaries and [community-launch.md](docs/community-launch.md) for a concise project description and launch copy.

## Ecosystem references

Primary sources checked on October 18, 2026:

- [Agent Skills specification](https://agentskills.io/specification)
- [OpenAI local skill locations](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents)
- [GitHub tree API](https://docs.github.com/en/rest/git/trees) and [blob API](https://docs.github.com/en/rest/git/blobs)
- [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [OpenAI skills](https://github.com/openai/skills), [Anthropic skills](https://github.com/anthropics/skills) and [VoltAgent sub-agents](https://github.com/VoltAgent/awesome-claude-code-subagents)
- [SPDX license texts](https://github.com/spdx/license-list-data); pinned reference commits/hashes are in `src/stratagent/data/license_sources.json`.

Stratagent source code is MIT-licensed. Discovered resources retain their own licenses. Earlier prototype workspace state is not automatically migrated: create a new workspace rather than editing approval-bound files by hand.
