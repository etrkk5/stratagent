"""Read-only OSV check of the four declared runtime/build pins; no upgrades.

Only these public package names and versions leave the machine. This is not an
inventory/audit of native libraries, vendored code or downloaded agent resources.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tomllib
from urllib.request import Request, build_opener, HTTPRedirectHandler

ALLOWED = {"pyyaml", "setuptools", "wheel", "packaging"}
LIMIT = 1024 * 1024


class AuditError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AuditError("OSV redirects are not accepted.")


def pins(source):
    project = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = list(project["project"]["dependencies"])
    for line in (source / "requirements-build.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            match = re.fullmatch(r"([A-Za-z0-9._-]+==[0-9]+(?:\.[0-9]+){1,2}) --hash=sha256:[0-9a-f]{64}", line)
            if not match:
                raise AuditError("Build dependency must retain an exact reviewed hash/version pin.")
            requirements.append(match[1])
    result = []
    for requirement in requirements:
        match = re.fullmatch(r"([A-Za-z0-9._-]+)==([0-9]+(?:\.[0-9]+){1,2})", requirement)
        if not match or match[1].lower() not in ALLOWED:
            raise AuditError("Unexpected dependency; review the public-query allowlist first.")
        result.append({"name": match[1].lower(), "version": match[2]})
    if len(result) != 4 or {p["name"] for p in result} != ALLOWED:
        raise AuditError("Expected the complete four-package direct dependency set.")
    return sorted(result, key=lambda p: p["name"])


def audit(source):
    dependencies = pins(source)
    body = {"queries": [{"package": {"ecosystem": "PyPI", "name": p["name"]}, "version": p["version"]} for p in dependencies]}
    request = Request("https://api.osv.dev/v1/querybatch", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "StratAgent-declared-dependency-audit/1"})
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise AuditError("OSV response exceeds the audit budget.")
    results = json.loads(data)["results"]
    if not isinstance(results, list) or len(results) != len(dependencies):
        raise AuditError("Incomplete OSV response; absence is not a clean result.")
    for dependency, result in zip(dependencies, results):
        if not isinstance(result, dict) or set(result) - {"vulns"}:
            raise AuditError("Unexpected OSV result.")
        records = result.get("vulns", [])
        if not isinstance(records, list) or len(records) > 1000:
            raise AuditError("Invalid OSV advisory list.")
        ids = [record.get("id") for record in records if isinstance(record, dict)]
        if len(ids) != len(records) or any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", value) for value in ids):
            raise AuditError("Invalid OSV advisory identifier.")
        dependency["advisory_ids"] = sorted(set(ids))
    return {"ok": not any(d["advisory_ids"] for d in dependencies), "checked_at": datetime.now(timezone.utc).isoformat(),
            "provider": "https://api.osv.dev/v1/querybatch", "dependencies": dependencies,
            "scope": "Four declared PyPI runtime/build pins only; excludes native/vendored/transitive content and external resources.",
            "automatic_changes": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = audit(args.source)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    except Exception:
        print(json.dumps({"ok": False, "error": "Dependency audit unavailable or incomplete; no clean result asserted.", "automatic_changes": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
