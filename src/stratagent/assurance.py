"""Operator-only resource assurance, fixed-host refresh and local revocations."""
import base64
import hmac
import json
import re
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request

from .artifacts import MAX_ARCHIVE, audit_archive, audit_tools, strict_json
from .common import StratagentError, canonical, digest, identity, repository
from .github import GitHub
from .registry import PACKAGE, SERVER, VERSION

POLICY = ".stratagent/policy.json"
MANIFEST = ".stratagent/manifest.json"
MAX_AGE = 86400


def subject(value):
    if not isinstance(value, str):
        raise StratagentError("Revocation subject must be a string.")
    if value.startswith("repo:") and value == "repo:" + repository(value[5:]):
        return value
    if re.fullmatch(r"(?:review|artifact):[0-9a-f]{64}", value):
        return value
    if value.startswith("npm:") and "@" in value[4:]:
        name, version = value[4:].rsplit("@", 1)
        if PACKAGE.fullmatch(name) and VERSION.fullmatch(version):
            return value
    if value.startswith("mcp:") and "@" in value[4:]:
        name, version = value[4:].split("@", 1)
        if SERVER.fullmatch(name) and 1 <= len(version) <= 100 and all(33 <= ord(char) <= 126 for char in version):
            return value
    raise StratagentError("Use repo:owner/repo, review:SHA256, artifact:SHA256, npm:PACKAGE@VERSION or mcp:NAME@VERSION.")


def validate_revocations(policy):
    records = policy.get("revocations", [])
    if not isinstance(records, list) or len(records) > 500:
        raise StratagentError("Invalid revocation policy; maximum 500 records.")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {"subject", "reason"} or subject(record["subject"]) in seen:
            raise StratagentError("Invalid or duplicate revocation record.")
        reason = record["reason"]
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500 or any(ord(char) < 32 or ord(char) == 127 for char in reason):
            raise StratagentError("Revocation reason must be 1–500 printable characters.")
        seen.add(record["subject"])
    return records


def subjects(review):
    values = {"review:" + review["review_digest"]} if review.get("review_digest") else set()
    if review.get("repo"):
        values.add("repo:" + review["repo"])
    if review.get("origin") == "official-mcp-registry":
        values.add("mcp:" + review["name"] + "@" + review["version"])
    for option in review.get("options", []):
        if option["type"] == "stdio":
            values.add("npm:" + option["package"] + "@" + option["version"])
    selected = review.get("selected_transport", {})
    if selected.get("type") == "stdio":
        values.add("npm:" + selected["package"] + "@" + selected["version"])
    if review.get("kind") == "npm-artifact":
        values.update({"artifact:" + review["sha256"], "npm:" + review["package"] + "@" + review["version"]})
    return values


def restrictions(review, policy):
    identifiers = subjects(review)
    return [{"severity": "block", "rule": "revoked-resource", **record}
            for record in validate_revocations(policy) if record["subject"] in identifiers]


def observation(checked_at):
    if type(checked_at) is not int or checked_at > int(time.time()) + 300 or checked_at < 0:
        raise StratagentError("Invalid assurance observation time.")
    return {"checked_at": checked_at, "expires_at": checked_at + MAX_AGE,
            "fresh": 0 <= int(time.time()) - checked_at <= MAX_AGE}


def advisory_review(response, checked_at):
    response = strict_json(canonical(response))
    if (not isinstance(response, dict) or set(response) - {"vulns", "next_page_token"} or not isinstance(response.get("vulns", []), list)
            or len(response.get("vulns", [])) > 100 or response.get("next_page_token")):
        raise StratagentError("Incomplete or invalid OSV advisory response.")
    identifiers = []
    for record in response.get("vulns", []):
        if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", record["id"]):
            raise StratagentError("Invalid OSV advisory identity.")
        withdrawn = record.get("withdrawn")
        if withdrawn is not None:
            try:
                observed = datetime.fromisoformat(withdrawn.replace("Z", "+00:00"))
                if observed.tzinfo is None:
                    raise ValueError
            except (AttributeError, ValueError):
                raise StratagentError("Invalid withdrawn advisory timestamp.") from None
        if withdrawn is None or observed.timestamp() > time.time():
            identifiers.append(record["id"])
    return {"provider": "OSV", "scope": "exact root npm package only; transitive dependencies not queried",
            **observation(checked_at), "advisory_ids": sorted(set(identifiers))}


class PublicAuditSource:
    def __init__(self):
        self.opener = GitHub(token="").opener
        self.deadline = time.monotonic() + 90
        self.remaining = 3

    def request(self, url, limit, body=None):
        if not (url.startswith("https://registry.npmjs.org/") or url == "https://api.osv.dev/v1/query"):
            raise StratagentError("Disallowed artifact audit endpoint.")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or self.remaining <= 0:
            raise StratagentError("Artifact audit exceeded its 90-second request budget.")
        self.remaining -= 1
        try:
            request = Request(url, data=canonical(body) if body is not None else None,
                              headers={"User-Agent": "StratAgent", "Accept": "application/json", "Content-Type": "application/json"})
            with self.opener.open(request, timeout=min(20, remaining)) as response:
                data = response.read(limit + 1)
            if len(data) > limit:
                raise StratagentError("Artifact audit response exceeds its byte limit.")
            return data
        except HTTPError as error:
            status = error.code
            error.close()
            raise StratagentError(f"Artifact audit provider HTTP {status}; no fresh review recorded.") from None
        except (URLError, OSError, TimeoutError):
            raise StratagentError("Artifact audit provider unavailable; no fresh review recorded.") from None

    def fetch(self, package, version):
        if not isinstance(package, str) or not PACKAGE.fullmatch(package) or not isinstance(version, str) or not VERSION.fullmatch(version):
            raise StratagentError("Artifact audit requires an exact public npm package/version.")
        metadata = strict_json(self.request("https://registry.npmjs.org/" + quote(package, safe="") + "/" + version, 256 * 1024))
        if not isinstance(metadata, dict) or metadata.get("name") != package or metadata.get("version") != version:
            raise StratagentError("npm registry returned a different package identity.")
        tarball = "https://registry.npmjs.org/" + package + "/-/" + package.rsplit("/", 1)[-1] + "-" + version + ".tgz"
        dist = metadata.get("dist", {})
        if not isinstance(dist, dict) or dist.get("tarball") != tarball:
            raise StratagentError("Noncanonical npm artifact endpoint refused.")
        data = self.request(tarball, MAX_ARCHIVE)
        response = strict_json(self.request("https://api.osv.dev/v1/query", 256 * 1024,
                                           {"package": {"name": package, "ecosystem": "npm"}, "version": version}))
        return metadata, data, response


class Assurance:
    def __init__(self, forge):
        self.forge = forge

    def revoke(self, identifier, reason):
        record = {"subject": subject(identifier), "reason": reason}
        with self.forge.ws.mutation():
            policy = self.forge.policy()
            records = policy.get("revocations", [])
            existing = next((item for item in records if item["subject"] == record["subject"]), None)
            if existing is not None:
                if existing != record:
                    raise StratagentError("Resource already revoked with a different reason; revocation is not silently replaced.")
            else:
                policy["revocations"] = sorted([*records, record], key=lambda item: item["subject"])
                validate_revocations(policy)
                self.forge.ws.write(POLICY, policy)
        return {"revoked": record, "security": self.status(), "execution": "none"}

    def package_request(self, candidate_id, option):
        review, _ = self.forge.inspect_mcp(candidate_id, include_assurance=False)
        if type(option) is not int or not 0 <= option < len(review["options"]) or review["options"][option]["type"] != "stdio":
            raise StratagentError("Package auditing requires an exact npm stdio option from inspect-mcp.")
        selected = review["options"][option]
        if restrictions(review, self.forge.policy()):
            raise StratagentError("Cannot refresh a revoked resource.")
        payload = {"workspace": str(self.forge.ws.root), "candidate_id": candidate_id, "option": option,
                   "metadata_review": review["review_digest"], "package": selected["package"], "version": selected["version"],
                   "repo": review["repo"], "policy": identity(self.forge.policy()),
                   "egress": ["GET exact-version metadata and canonical tarball at https://registry.npmjs.org",
                              "POST root public package name/version to https://api.osv.dev/v1/query"],
                   "limits": {"requests": 3, "seconds": 90, "artifact_bytes": MAX_ARCHIVE}, "execution": "never"}
        return {**payload, "approval": identity(payload), "dry_run": True}

    def package(self, candidate_id, option=0, approval=None, source=None):
        preview = self.package_request(candidate_id, option)
        if approval is None:
            return preview
        if not isinstance(approval, str) or not hmac.compare_digest(approval, preview["approval"]):
            raise StratagentError("Network approval does not match the current package audit request.")
        key = f"{candidate_id}:{option}"
        with self.forge.ws.mutation():
            if self.package_request(candidate_id, option) != preview:
                raise StratagentError("Package audit request changed before refresh.")
            manifest = self.forge.manifest()
            if key not in manifest.get("artifact_audits", {}) and len(manifest.get("artifact_audits", {})) >= 100:
                raise StratagentError("Artifact audit cache index is full; maximum 100 exact options.")
            manifest.setdefault("artifact_audits", {})[key] = {"state": "pending", "request": preview["approval"]}
            self.forge.ws.write(MANIFEST, manifest)
        try:
            metadata, data, osv = (source or PublicAuditSource()).fetch(preview["package"], preview["version"])
            if not isinstance(metadata, dict) or metadata.get("name") != preview["package"] or metadata.get("version") != preview["version"]:
                raise StratagentError("Audit source returned a different package identity.")
            upstream = metadata.get("repository", {})
            upstream = upstream.get("url", "") if isinstance(upstream, dict) else upstream
            expected = "https://github.com/" + preview["repo"]
            if not isinstance(upstream, str) or upstream.removeprefix("git+").removesuffix(".git").lower() != expected:
                raise StratagentError("npm artifact repository differs from reviewed Registry provenance.")
            record = {"schema_version": 1, "candidate_id": candidate_id, "option": option,
                      "metadata_review": preview["metadata_review"], "registry_metadata": metadata,
                      "artifact": base64.b64encode(data).decode("ascii"), "osv": osv, "checked_at": int(time.time())}
            report = self.report_package(record)
        except Exception:
            with self.forge.ws.mutation():
                manifest = self.forge.manifest()
                current = manifest.get("artifact_audits", {}).get(key, {})
                if current.get("request") == preview["approval"]:
                    manifest["artifact_audits"][key] = {"state": "failed", "request": preview["approval"]}
                    self.forge.ws.write(MANIFEST, manifest)
            raise
        with self.forge.ws.mutation():
            manifest = self.forge.manifest()
            if manifest.get("artifact_audits", {}).get(key) != {"state": "pending", "request": preview["approval"]}:
                raise StratagentError("Concurrent audit changed; this refresh cannot replace it.")
            current = self.package_request(candidate_id, option)
            if current != preview:
                raise StratagentError("Source/policy changed during audit; refresh again.")
            self.save(manifest, "artifact_audits", key, record)
        return report

    def save(self, manifest, field, key, record):
        if key not in manifest.get(field, {}) and len(manifest.get(field, {})) >= 100:
            raise StratagentError("Assurance cache index is full; maximum 100 entries.")
        checksum = identity(record)
        self.forge.ws.write(f".stratagent/assurance/{checksum}.json", record)
        manifest.setdefault(field, {})[key] = {"state": "reviewed", "digest": checksum}
        self.forge.ws.write(MANIFEST, manifest)

    def load(self, reference):
        checksum = reference.get("digest")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise StratagentError("Invalid assurance evidence reference.")
        record = self.forge.ws.read(f".stratagent/assurance/{checksum}.json")
        if not isinstance(record, dict) or record.get("schema_version") != 1 or identity(record) != checksum:
            raise StratagentError("Assurance evidence changed; audit again.")
        return record

    def report_package(self, record):
        try:
            if record.get("schema_version") != 1:
                raise ValueError
            metadata = record["registry_metadata"]
            encoded = record["artifact"]
            if not isinstance(encoded, str) or len(encoded) > MAX_ARCHIVE * 4 // 3 + 8:
                raise ValueError
            data = base64.b64decode(encoded, validate=True)
            report = audit_archive(data, metadata["dist"]["integrity"], metadata["name"], metadata["version"])
            report["advisories"] = advisory_review(record["osv"], record["checked_at"])
            report["policy_findings"] = restrictions(report, self.forge.policy())
            if metadata.get("deprecated"):
                report["policy_findings"].append({"severity": "block", "rule": "deprecated-npm-version"})
            if report["advisories"]["advisory_ids"]:
                report["policy_findings"].append({"severity": "block", "rule": "known-package-advisory"})
            if not report["advisories"]["fresh"]:
                report["policy_findings"].append({"severity": "block", "rule": "expired-advisory-review"})
            report["static_policy_passed"] = report["static_policy_passed"] and not report["policy_findings"]
            return report
        except (KeyError, ValueError, TypeError):
            raise StratagentError("Invalid artifact assurance record; refresh again.") from None

    def tools(self, candidate_id, relative):
        with self.forge.ws.mutation():
            review, _ = self.forge.inspect_mcp(candidate_id, include_assurance=False)
            path = self.forge.ws.path(relative)
            if not path.is_file() or path.stat().st_size > 256 * 1024:
                raise StratagentError("Tool manifest must be a regular JSON file of at most 256 KiB.")
            document = strict_json(path.read_bytes())
            record = {"schema_version": 1, "candidate_id": candidate_id, "metadata_review": review["review_digest"],
                      "checked_at": int(time.time()), "document": document}
            report = self.report_tools(record)
            self.save(self.forge.manifest(), "tool_audits", candidate_id, record)
        return report

    def report_tools(self, record):
        report = audit_tools(record["document"])
        report["observation"] = {**observation(record.get("checked_at")), "server_behavior_verified": False}
        report["policy_findings"] = restrictions(report, self.forge.policy())
        if not report["observation"]["fresh"]:
            report["policy_findings"].append({"severity": "block", "rule": "expired-tool-review"})
        report["static_policy_passed"] = report["static_policy_passed"] and not report["policy_findings"]
        return report

    def enrich(self, review):
        result = {**review, "policy_findings": restrictions(review, self.forge.policy()), "resource_assurance": []}
        manifest = self.forge.manifest()
        references = [(key, value, "artifact") for key, value in manifest.get("artifact_audits", {}).items() if key.startswith(review["id"] + ":")]
        reference = manifest.get("tool_audits", {}).get(review["id"])
        if reference:
            references.append((review["id"], reference, "tools"))
        for key, reference, kind in references:
            if reference.get("state") != "reviewed":
                result["policy_findings"].append({"severity": "block", "rule": "assurance-refresh-incomplete", "kind": kind})
                continue
            record = self.load(reference)
            if record.get("candidate_id") != review["id"] or record.get("metadata_review") != review["review_digest"]:
                result["policy_findings"].append({"severity": "block", "rule": "stale-assurance-source", "kind": kind})
                continue
            if kind == "artifact":
                option = record.get("option")
                if type(option) is not int or not 0 <= option < len(review["options"]) or key != f"{review['id']}:{option}":
                    raise StratagentError("Artifact audit option binding changed.")
                selected = review["options"][option]
                metadata = record.get("registry_metadata", {})
                if selected.get("type") != "stdio" or metadata.get("name") != selected["package"] or metadata.get("version") != selected["version"]:
                    raise StratagentError("Artifact audit package binding changed.")
            report = self.report_package(record) if kind == "artifact" else self.report_tools(record)
            result["resource_assurance"].append(report)
            if not report["static_policy_passed"]:
                result["policy_findings"].append({"severity": "block", "rule": "resource-assurance-blocked", "kind": kind})
        result["eligible"] = review["eligible"] and not result["policy_findings"]
        return result

    def status(self):
        findings = []
        policy, manifest = self.forge.policy(), self.forge.manifest()
        for key, installation in self.forge.lock()["installations"].items():
            source = installation.get("source", {})
            reviews = [{**source, "review_digest": installation.get("review_digest")}]
            reviews.extend(item["review"] for item in source.get("reviewed_sources", []))
            for review in reviews:
                findings.extend({"installation": key, **item} for item in restrictions(review, policy))
                candidate_id = review.get("candidate_id", review.get("id"))
                if candidate_id in manifest.get("mcp_candidates", {}):
                    try:
                        current, _ = self.forge.inspect_mcp(candidate_id)
                        findings.extend({"installation": key, **item} for item in current["policy_findings"])
                    except StratagentError:
                        findings.append({"installation": key, "rule": "assurance-unavailable", "severity": "block"})
        return {"ok": not findings, "findings": findings,
                "scope": "Local revocation and recorded audit impact only; file verification is separate. No automatic removal or activation."}
