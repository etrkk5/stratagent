# Inventory review pilot

An original, working Python standard-library example for validating StratAgent's project-to-workspace flow. It is not a third-party skill, a production inventory system or evidence of a paying customer.

```sh
python3 inventory.py valid.csv
python3 inventory.py invalid.csv
```

The first command returns `ok: true` and exits 0. The second reports a duplicate SKU, two invalid quantities and an invalid SKU, and exits 1. Unreadable, oversized, non-UTF-8, malformed CSV or invalid headers exit 2 with a JSON error on stderr. Input files are not modified; no network or dependency installation is used.

Headers must be exactly `sku,quantity`. SKUs are case-sensitive, stripped of surrounding whitespace and limited to 1–64 ASCII letters, digits, dots, underscores or hyphens, starting with a letter or digit. Quantities are stripped of surrounding whitespace and must be 1–9 ASCII digits; zero is valid. Empty physical records are ignored. Diagnostic `record` values count CSV records including the header, not physical line numbers. Diagnostics contain rules and record numbers, not field contents. Input is limited to 256 KiB and 1000 nonempty data records.

To use it as a disposable StratAgent target, copy this directory outside the source checkout, initialize that copy for your selected host, and inspect a blueprint:

```sh
stratagent init "Build a small Python CSV inventory reviewer. Identify duplicate SKU values and invalid quantities. Keep processing offline. No web UI and no payments." --workspace /absolute/path/to/pilot-copy --platforms codex
stratagent decision-request --workspace /absolute/path/to/pilot-copy
stratagent blueprint --workspace /absolute/path/to/pilot-copy --content
```

Have your current model/human review the decision context, or use the disclosed rule fallback. If supplying a decision, save its JSON inside the pilot copy and use `--decisions decision.json` consistently for preview and application. Review the exact output and approve its complete hash before applying. Then verify and explicitly ask your coding environment to use the generated test-reviewer role for a read-only review of this code. Do not enable unrelated MCP servers or run discovered third-party content as part of this pilot.

The source is intentionally small and has no dependency manifest. StratAgent's bounded manifest scanner does not inspect this Python implementation; source review is a separate, explicit task for the coding environment. See [pilot validation](../../../docs/pilot-validation.md) for recorded evidence and remaining limits.
