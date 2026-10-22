# First live coding-client pilot

For the later two-stage 0.4 existing-host orchestration test, see [orchestration.md](orchestration.md#observed-existing-host-test--october-22-2026). The results below describe the earlier 0.3.0 pilot.

Recorded October 20, 2026, on macOS with Python 3.14.3, StratAgent 0.3.0 and Codex CLI 0.163.0-alpha.10.2. This is a locally observed integration result, not a safety attestation, architecture-quality benchmark or production-readiness certification.

## What was exercised

The target was the original, working [inventory CSV reviewer](../examples/projects/inventory-review), copied to a disposable directory outside the repository. It processes local CSV, reports duplicate SKU values and invalid quantities, and has no external dependencies, network calls, web UI or payment integration. It is a realistic test project, not a customer's production repository or a claimed paying customer.

The exact project request was:

> Build a small Python CSV inventory reviewer. Identify duplicate SKU values and invalid quantities. Keep processing offline. No web UI and no payments.

1. Initialized that workspace for `codex`, without importing skills or discovering servers. No extra resource is necessary for this small offline project.
2. Started an actual Codex CLI model session using its existing ChatGPT authentication, `--ignore-user-config`, `--ephemeral`, a read-only sandbox and a required local StratAgent stdio server supplied by temporary command-line configuration. Persistent host settings were not edited. The procedure follows the official [non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode) and [MCP](https://learn.chatgpt.com/docs/extend/mcp) documentation, checked on the validation date.
3. Observed successful `stratagent_decision_request` and `stratagent_blueprint` tool calls in client JSON events. The model supplied a fresh structured decision with focused coordination, five core responsibilities, explicit empty skill/MCP bindings and grounded offline/web/payment scope. This was a real model roundtrip, not a manually fabricated MCP reply or an unchanged draft labeled as model reasoning. One successful decision does not establish general reasoning quality.
4. Inspected the returned JSON and exact seven output files, then applied its complete approval hash through the local service. Outputs were five portable role skills, `.stratagent/task-plan.json` and `.stratagent/blueprint.json`. Verification passed, the approved context remained current and repeat application was a no-op. No third-party package, skill or server was installed or executed.
5. Started a second read-only Codex session explicitly requesting `$sa-test-reviewer`. Client events record a successful read of `.agents/skills/sa-test-reviewer/SKILL.md`, followed by reads of the original implementation, examples and approved plan, and a successful local `stratagent_status` call. The model produced a static review reporting no findings and disclosing that it had not executed tests. This verifies portable skill access/use in this CLI scenario, not native subagent orchestration or universal host permission enforcement.
6. Confirmed all original input/source files were unchanged and all seven approved outputs still matched the lockfile after the client exited. Both client processes exited 0. Observed runtimes were approximately 31 seconds for decision/preview and 47 seconds for the role review; these are individual observations, not performance guarantees.

CLI event logs and model output remain local temporary artifacts and are not committed. They may contain host context; do not publish raw session logs without inspecting them. No production repository or secret was intentionally supplied to the model. The host's normal authentication and model context remain its responsibility.

## Reproduce safely

From the source checkout after installing StratAgent:

```sh
PILOT=$(mktemp -d)
cp examples/projects/inventory-review/inventory.py \
  examples/projects/inventory-review/valid.csv \
  examples/projects/inventory-review/invalid.csv \
  examples/projects/inventory-review/README.md "$PILOT/"
STRATAGENT_PYTHON="$(pwd)/.venv/bin/python"
.venv/bin/stratagent init "Build a small Python CSV inventory reviewer. Identify duplicate SKU values and invalid quantities. Keep processing offline. No web UI and no payments." \
  --workspace "$PILOT" --platforms codex
```

Connect only the local read-only server for the test run:

```sh
codex exec --ignore-user-config --ephemeral --sandbox read-only \
  --skip-git-repo-check -C "$PILOT" \
  -c "mcp_servers.stratagent.command=\"$STRATAGENT_PYTHON\"" \
  -c "mcp_servers.stratagent.args=[\"-m\",\"stratagent\",\"serve\",\"--workspace\",\"$PILOT\"]" \
  -c 'mcp_servers.stratagent.required=true' \
  -o "$PILOT/decision.json" \
  'Call stratagent_decision_request. Review its evidence and schema, make a grounded architectural decision, then validate it with stratagent_blueprint. Do not install, execute project code, write files, discover remote sources or grant permissions. Return only the validated decision JSON, not Markdown.'
```

Inspect the proposal and every generated file with `blueprint --decisions decision.json --content --workspace "$PILOT"`. Resolve blockers before applying with that preview's full `--approve` hash; never copy the recorded pilot's hash into another destination. Run `verify`, repeat the exact proposal to confirm no-op behavior, and explicitly delegate the generated role for a read-only code review. The model output may fail validation; investigate the actual error instead of bypassing scope or approval checks.

Separately run `python3 "$PILOT/inventory.py" "$PILOT/valid.csv"` and the invalid example (expected exit 1). The automated suite checks success/failure exits, UTF-8/BOM, SKU/quantity rules, diagnostic redaction, CSV errors, limits, preservation of input files and combined four-target blueprint approval/repeatability. Automated tests never launch Codex, require model credentials or make network calls.

## Live Registry result

The previously timed-out official Registry endpoint responded successfully on October 20. Actual `Registry.search`/`assess_server` calls reviewed three `playwright` results and two `context7` results. All five sampled records were active but had no transport eligible under the current conservative policy. Unsupported remote/package findings remained visible; none was force-enabled or contacted. The first query completed in approximately 2.3 seconds. This establishes live search/envelope compatibility for these responses, not package/server safety, useful coverage of every catalog entry, or a successful third-party MCP connection. Supported proposal rendering remains independently tested using fixtures.

## Release boundary

- Verified here: a real client/model → local MCP context → model decision → preview → local approval → portable role file → client read-only review flow.
- Still pending: actual Claude Code and Antigravity runtime sessions; those executables were not found on PATH. Their generated layouts remain covered by automated tests only.
- Still pending: user onboarding without developer help, diverse project/model decision evaluation, third-party artifact/tool audits, upgrades/removal and operational experience beyond this original pilot.
- No automatic agent launch, native Codex subagent runtime configuration, external installer backend, payment collection or production release was added. Platform/model neutrality does not imply every host/model combination has been validated.

The appropriate release label remains **developer preview**. A broader release should follow independently reproducible pilots and actual user feedback, not just additional generated features or stronger marketing claims.
