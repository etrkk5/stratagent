"""Conservative text-bundle assessment, not a sandbox or malware proof."""
import base64
import math
import re
import json
from functools import lru_cache
from importlib.resources import files as resource_files
from pathlib import PurePosixPath

from .common import (StratagentError, MAX_BUNDLE, MAX_FILES, SHA, decode_text,
                     digest, git_blob, identity, repository, safe_path)
from .planner import words
from .skill_format import FIELDS, metadata
from .references import review_references

SCANNER_VERSION = 2
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.md", "copying.txt"}
NOTICE_NAMES = LICENSE_NAMES | {"notice", "notice.md", "notice.txt", "copyright", "copyright.md", "copyright.txt"}
PERMITTED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC"}
RULES = [
    ("instruction-override", r"(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|safety)\s+(?:instructions|prompts|rules)"),
    ("remote-execution", r"(?:curl|wget)[^\n]{0,300}\|\s*(?:ba)?sh\b"),
    ("destructive-command", r"\brm\s+-[a-z]*r[a-z]*f\b|\brm\s+-[a-z]*f[a-z]*r\b"),
    ("permission-bypass", r"bypassPermissions|dangerously-skip-permissions|approval_policy\s*[=:]\s*[\"']?never"),
    ("credential-access", r"(?:~\/\.ssh|\/\.aws\/credentials|id_rsa|(?:send|upload|exfiltrate)[^\n]{0,80}(?:secrets?|tokens?|credentials?))"),
    ("active-configuration", r"^\s*(?:hooks|mcpServers|permissionMode|allowed-tools|disable-model-invocation)\s*:"),
]


@lru_cache(maxsize=1)
def license_references():
    return json.loads(resource_files("stratagent").joinpath("data/license_texts.json").read_text(encoding="utf-8"))


def normalized_license(text):
    return " ".join(text.lower().replace("\\'", "'").split())


def license_id(text):
    """Match complete normative bodies; custom additions fail closed.

    This deliberately recognizes fewer variants than SPDX's full matching rules.
    Copyright notices vary; license terms must match the bundled pinned reference.
    """
    anchors = {"MIT": "Permission is hereby granted", "BSD-3-Clause": "Redistribution and use",
               "BSD-2-Clause": "Redistribution and use", "ISC": "Permission to use, copy"}
    for name, reference in license_references().items():
        if name == "Apache-2.0":
            if normalized_license(text) == normalized_license(reference):
                return name
            continue
        anchor = anchors[name]
        position = text.lower().find(anchor.lower())
        if position < 0:
            continue
        reference_position = reference.lower().find(anchor.lower())
        titles = {"mit license", "the mit license (mit)", "bsd 2-clause license", "bsd 3-clause license", "isc license", "all rights reserved."}
        prefix_lines = [line.strip().lower() for line in text[:position].splitlines() if line.strip()]
        if not all(line in titles or line.startswith("copyright ") or line.startswith("copyright (") for line in prefix_lines):
            continue
        if normalized_license(text[position:]) == normalized_license(reference[reference_position:]):
            return name
    return "UNKNOWN"


def unpack(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
        raise StratagentError("Unsupported snapshot schema.")
    repository(snapshot.get("repo"))
    if not SHA.fullmatch(str(snapshot.get("commit", ""))):
        raise StratagentError("An immutable 40-character commit SHA is required.")
    safe_path(snapshot.get("entry"))
    if snapshot.get("kind") not in ("skill", "subagent"):
        raise StratagentError("Unsupported definition kind.")
    records = snapshot.get("files", [])
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_FILES:
        raise StratagentError("Bundle file count exceeds limit or is empty.")
    files, names, total = {}, set(), 0
    entry = PurePosixPath(snapshot["entry"])
    for record in records:
        path = safe_path(record["path"])
        p = PurePosixPath(path)
        # A subagent is one definition. Skills include only their own directory.
        in_bundle = (p == entry if snapshot["kind"] == "subagent" else entry.parent in p.parents)
        ancestor_license = p.name.lower() in NOTICE_NAMES and p.parent in (entry.parent, *entry.parent.parents)
        if not in_bundle and not ancestor_license:
            raise StratagentError("File lies outside the definition bundle.")
        if path.casefold() in names:
            raise StratagentError("Duplicate or case-colliding bundle path.")
        names.add(path.casefold())
        if record.get("mode") != "100644":
            raise StratagentError("Symlinks, executables and submodules are forbidden.")
        try:
            encoded = record["data"]
            if not isinstance(encoded, str) or len(encoded) > 4 * 256 * 1024 // 3 + 8:
                raise StratagentError("Encoded file exceeds limit.")
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise StratagentError("Invalid bundle base64.") from exc
        decode_text(data)
        total += len(data)
        if total > MAX_BUNDLE:
            raise StratagentError("Bundle exceeds 2 MiB limit.")
        if git_blob(data) != record.get("git_sha"):
            raise StratagentError("Git blob hash mismatch.")
        files[path] = data
    if snapshot["entry"] not in files:
        raise StratagentError("Definition file is missing.")
    return files


def assess(snapshot, terms=()):
    files = unpack(snapshot)
    entry = snapshot["entry"]
    findings = []
    try:
        meta, body = metadata(decode_text(files[entry]))
        expected = PurePosixPath(entry).parent.name if snapshot["kind"] == "skill" else PurePosixPath(entry).stem
        if meta["name"] != expected:
            findings.append({"severity": "block", "rule": "name-path-mismatch", "path": entry})
    except StratagentError as exc:
        meta, body = {"name": "invalid", "description": "Invalid metadata"}, ""
        findings.append({"severity": "block", "rule": "invalid-metadata", "path": entry, "detail": str(exc)})
    extensions = sorted(set(meta) - FIELDS)
    for field in extensions:
        if snapshot["kind"] == "subagent" and field == "tools" and isinstance(meta[field], str) and set(meta[field].replace(",", " ").split()) <= {"Read", "Grep", "Glob"}:
            findings.append({"severity": "review", "rule": "source-tools-not-granted", "path": entry,
                             "detail": "Source read-only tool hints are stripped; only trusted adapter permissions are emitted."})
        else:
            findings.append({"severity": "block", "rule": "unsupported-metadata-field", "path": entry, "field": field})
    if "allowed-tools" in meta:
        findings.append({"severity": "block", "rule": "source-tool-grant", "path": entry,
                         "detail": "Experimental pre-approved source tools are not authorized by a file review."})
    if meta.get("compatibility"):
        findings.append({"severity": "review", "rule": "compatibility-not-verified", "path": entry,
                         "detail": "Declared environment requirements are untrusted and not automatically installed or verified."})

    def strings(value):
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [text for key, child in value.items() for text in [key, *strings(child)]]
        if isinstance(value, list):
            return [text for child in value for text in strings(child)]
        return []

    decoded_metadata = "\n".join(strings(meta))
    for rule, pattern in RULES:
        if re.search(pattern, decoded_metadata, re.I | re.M):
            findings.append({"severity": "block", "rule": rule, "path": entry, "location": "decoded-metadata"})
    for path, data in files.items():
        p = PurePosixPath(path)
        if p.suffix.lower() not in (".md", ".txt", ".rst") and p.name.lower() not in NOTICE_NAMES:
            findings.append({"severity": "block", "rule": "non-document-file", "path": path})
        if p.name == "SKILL.md" and path != entry:
            findings.append({"severity": "block", "rule": "nested-skill-definition", "path": path})
        for rule, pattern in RULES:
            match = re.search(pattern, decode_text(data), re.I | re.M)
            if match:
                findings.append({"severity": "block", "rule": rule, "path": path,
                                 "line": decode_text(data)[:match.start()].count("\n") + 1})
    references = review_references(files, entry, snapshot["kind"], NOTICE_NAMES)
    findings.extend(references.pop("findings"))
    ancestors = (PurePosixPath(entry).parent, *PurePosixPath(entry).parent.parents)
    license_paths = [p for p in files if PurePosixPath(p).name.lower() in LICENSE_NAMES and PurePosixPath(p).parent in ancestors]
    nearest = sorted(license_paths, key=lambda p: (-len(PurePosixPath(p).parts), p))
    license_value = license_id(decode_text(files[nearest[0]])) if nearest else "UNKNOWN"
    if nearest:
        depth = len(PurePosixPath(nearest[0]).parts)
        if any(license_id(decode_text(files[p])) != license_value for p in nearest if len(PurePosixPath(p).parts) == depth):
            license_value = "UNKNOWN"
    declared = meta.get("license")
    if declared and declared != license_value and declared not in {PurePosixPath(p).name for p in nearest}:
        license_value = "UNKNOWN"
    for path in files:
        if PurePosixPath(path).name.lower() in LICENSE_NAMES and path not in license_paths and license_id(decode_text(files[path])) != license_value:
            findings.append({"severity": "block", "rule": "nested-license-conflict", "path": path})
    if license_value not in PERMITTED_LICENSES:
        findings.append({"severity": "block", "rule": "unapproved-license", "path": entry})
    findings.append({"severity": "review", "rule": "untrusted-instructions", "path": entry,
                     "detail": "Static rules cannot establish safety. Read every file before approval."})
    if snapshot.get("origin") not in ("github-api", "demo-offline"):
        raise StratagentError("Snapshot origin must be github-api or demo-offline.")
    source = {"repo": repository(snapshot["repo"]), "commit": snapshot["commit"], "entry": entry, "origin": snapshot["origin"],
              "kind": snapshot["kind"], "files": [{"path": p, "sha256": digest(d), "git_sha": git_blob(d), "size": len(d)} for p, d in sorted(files.items())]}
    review = {**source, "name": meta["name"], "description": meta["description"], "license": license_value,
              "metadata": meta, "reference_review": references,
              "assurance": {"level": "static-text-only", "artifact_execution": "never", "malware_safety": "not-proven",
                            "vulnerability_status": "not-checked", "tool_behavior": "not-audited",
                            "installable_scope": "UTF-8 documentation only; code, archives and host-specific metadata fail closed"},
              "findings": findings, "eligible": not any(f["severity"] == "block" for f in findings), "scanner_version": SCANNER_VERSION}
    body_words = len(body.split())
    sections = len(re.findall(r"^(?:#{1,6}\s|[-*]\s|\d+\.\s)", body, re.M))
    review["quality"] = {"metadata_valid": meta["name"] != "invalid", "body_words": body_words,
                         "structured_sections": sections,
                         "supporting_documents": sum(p != entry and PurePosixPath(p).name.lower() not in NOTICE_NAMES for p in files),
                         "note": "Documentation structure signals only; correctness has not been executed or proven."}
    review["review_digest"] = identity(review)
    review["id"] = identity({"repo": source["repo"], "entry": entry})[:16]
    haystack = words(meta["name"] + " " + meta["description"] + " " + body[:5000])
    requested = set().union(*(words(t) for t in terms)) if terms else set()
    overlap = len(requested & haystack) / max(1, len(requested))
    try:
        stars = max(0, min(int(snapshot.get("stars", 0)), 10_000_000))
    except (ValueError, TypeError):
        stars = 0
    structure = (5 if meta["name"] != "invalid" else 0) + (5 if body_words >= 50 else 0) + (5 if sections >= 2 else 0)
    components = {"relevance": round(overlap * 45, 2), "structure": structure,
                  "license": 15 if license_value in PERMITTED_LICENSES else 0,
                  "static_policy": 20 if review["eligible"] else 0,
                  "popularity": round(min(5, math.log10(stars + 1)), 2)}
    review["ranking"] = {"score": round(sum(components.values()), 2), "components": components,
                         "matched_terms": sorted(requested & haystack), "note": "Heuristic ranking; popularity is not a trust signal."}
    return review
