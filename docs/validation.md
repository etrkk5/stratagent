# Validation — October 18–19, 2026

Executed locally on macOS with Python 3.14.7. The CI configuration includes Python 3.11 and 3.14 on Linux and Python 3.14 on macOS; CI itself has not been run on GitHub.

The October 19 naming/language update uses `stratagent-cli`, the `stratagent` command, `.stratagent/` workspace state and `stratagent_*` MCP tool names. Documentation, original demo inputs and generated sample configurations are in English. The complete offline test suite and demo were rerun after the rename.

## Automated checks

- 52 standard-library `unittest` tests pass without network access.
- Editable package installation succeeded in a new virtual environment.
- A standard wheel was built and installed with `--no-index` into another clean environment. The installed console entry point ran the offline demo and verified 31 generated files.
- CLI subprocess tests cover demo, planning, clean error output and a nonzero exit when file hashes drift.
- MCP tests exchange newline-delimited initialize, notification, tools/list and tools/call messages. Invalid JSON, invalid arguments, unknown/mutating tools and initialization ordering are checked.
- Safety tests cover Git blob/hash mismatch, mutable refs, traversal, control characters, duplicate paths, executable/symlink/submodule modes, binary/oversized files, unknown/conflicting/customized licenses, injection signals, exact approval scope, allowlist, no overwrites, rollback, concurrency locking, cache drift and role-resource binding.

## Live, read-only GitHub validation

Repository search was exercised through the actual GitHub API. For the broad `python agent skills` query, results included `langgenius/dify` and `shubhamsaboo/awesome-llm-apps`; this demonstrates the API path and also the limitations of repository-level search. Explicit repositories give more focused discovery.

Discovery inspected immutable commits:

| Repository | Commit | Result |
| --- | --- | --- |
| `openai/skills` | `49f948faa9258a0c61caceaf225e179651397431` | 44 definition paths enumerated; sampled security skills assessed |
| `VoltAgent/awesome-claude-code-subagents` | `408d3c9eee2d0c75c12a3abb5de29e53c2ca6b9e` | API designer and FastAPI developer definitions assessed |

The first live discovery returned four assessed candidates with no errors. MIT-licensed API designer/FastAPI sub-agents were eligible for human review. Security skill bundles with YAML metadata/scripts were blocked by the documentation-only policy. A security reference also triggered the conservative credential rule; this is not a claim that the upstream project is malicious.

After strengthening full license-body comparison, a second live run again recognized the Apache-2.0 skill and MIT sub-agent licenses, and produced an install dry-run for the API designer. The remaining requests encountered GitHub's unauthenticated rate limit. This exposed repeated requests after a global limit; the client now opens a circuit and discovery returns partial evidence after the first limit error. Regression tests confirm this behavior without making further network requests.

No real third-party candidate was installed, executed or launched. The tested install/lockfile/adapter flow uses only original bundled examples. The built-in live review/dry-run remained outside the source tree in a temporary workspace.

## Remaining verification limits

- Actual Claude Code/Codex runtime loading and a real MCP client/Inspector session were not executed.
- Only Python 3.14.7 was executed locally; compatibility with 3.11+ is declared and covered by the prepared CI matrix, pending CI execution.
- Static checks and license text matching are conservative filters, not a proof of safety, correctness or legal compatibility.
- Existing installation upgrades/removal, semantic LLM planning and launching coding-agent processes are outside this MVP.
