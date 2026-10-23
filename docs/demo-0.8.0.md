# Two-minute offline walkthrough

This real CLI walkthrough uses original synthetic fixtures to demonstrate preview,
explicit application, provenance verification and offline health. It does not
show live model reasoning, external installation or native host loading. No host
or third-party process is activated.

Install using the [README](../README.md#try-it-locally), then use new directories:

```sh
stratagent --version
stratagent demo --workspace ./demo-workspace/preview
stratagent demo --workspace ./demo-workspace/applied --apply
stratagent verify --workspace ./demo-workspace/applied
stratagent doctor --workspace ./demo-workspace/applied --check-files
```

1. Version prints `0.8.0`.
2. Inspect `configuration_preview` and `install_previews` in the first response;
   it reports `applied: false`. Generated outputs are not installed by preview.
3. `--apply` is explicit opt-in for this bundled synthetic demo. Real projects use
   the separate stage/diff/exact-approval procedure.
4. Actual verification recorded October 23, 2026, macOS/Python 3.14.7:

```json
{
  "checked": 46,
  "mismatches": [],
  "ok": true,
  "pending_transaction": null
}
```

5. Selected fields from the actual, longer `doctor` response:

```json
{
  "ok": true,
  "writes": false,
  "network_calls": 0,
  "managed_outputs": {
    "id": "managed-outputs",
    "status": "pass",
    "message": "Managed output hashes/modes match the lock."
  }
}
```

`managed_outputs` above is the matching element extracted from the `checks` array,
not the original top-level schema. Leave generated files in place to inspect them.
Never use an existing user project for the demo; use fresh directories on reruns.

For project-to-blueprint/model behavior, continue with [orchestration](orchestration.md).
Public research and installation have separate approvals; missing/partial resources
remain visible.
