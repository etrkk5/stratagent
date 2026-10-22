"""Bounded artifact and MCP manifest review. Never extract, import or execute."""
import ast
import base64
import gzip
import hashlib
import io
import json
import math
from pathlib import PurePosixPath
import re
import tarfile

from .common import StratagentError, MAX_FILE, canonical, decode_text, digest, identity, safe_path
from .security import LICENSE_NAMES, PERMITTED_LICENSES, RULES, license_id

MAX_ARCHIVE = 4 * 1024 * 1024
MAX_EXPANDED = 16 * 1024 * 1024


def strict_json(data):
    def mapping(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise StratagentError("Duplicate JSON key in untrusted evidence.")
            result[key] = value
        return result

    try:
        value = json.loads(decode_text(data), object_pairs_hook=mapping,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
        pending, count = [(value, 0)], 0
        while pending:
            child, depth = pending.pop()
            count += 1
            if depth > 16 or count > 10000:
                raise StratagentError("JSON evidence exceeds depth/node limits.")
            if isinstance(child, dict):
                pending.extend((item, depth + 1) for item in child.values())
                pending.extend((key, depth + 1) for key in child)
            elif isinstance(child, list):
                pending.extend((item, depth + 1) for item in child)
            elif isinstance(child, str):
                decode_text(child.encode("utf-8"))
            elif isinstance(child, float) and not math.isfinite(child):
                raise StratagentError("Non-finite JSON evidence is unsupported.")
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise StratagentError("Invalid bounded JSON evidence.") from None


def scan_text(path, data):
    findings = []
    try:
        text = decode_text(data)
    except StratagentError:
        return [{"severity": "block", "rule": "unsupported-binary-content", "path": path}]
    for rule, pattern in RULES:
        match = re.search(pattern, text, re.I | re.M)
        if match:
            findings.append({"severity": "block", "rule": rule, "path": path,
                             "line": text[:match.start()].count("\n") + 1})
    capabilities = (("process-execution", r"\b(?:exec|eval|spawn|subprocess|child_process|os\.system)\b"),
                    ("network-access", r"https?://|\b(?:fetch|requests|urllib|socket)\b"),
                    ("environment-access", r"process\.env|os\.environ|\bgetenv\b"),
                    ("filesystem-write", r"\b(?:writeFile|unlink|rmtree|remove|chmod)\b"))
    for rule, pattern in capabilities:
        if re.search(pattern, text):
            findings.append({"severity": "review", "rule": rule, "path": path})
    if PurePosixPath(path).suffix == ".py":
        try:
            tree = ast.parse(text)
            if sum(1 for _ in ast.walk(tree)) > 10000:
                raise ValueError
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            findings.append({"severity": "block", "rule": "unsupported-python-syntax-or-size", "path": path})
    return findings


def decoded_strings(value):
    pending, result = [value], []
    while pending:
        child = pending.pop()
        if isinstance(child, dict):
            pending.extend(child.keys())
            pending.extend(child.values())
        elif isinstance(child, list):
            pending.extend(child)
        elif isinstance(child, str):
            result.append(child)
    return "\n".join(result).encode("utf-8")


def archive_files(data, integrity):
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_ARCHIVE:
        raise StratagentError("Artifact exceeds the 4 MiB compressed limit or is empty.")
    if not isinstance(integrity, str) or not re.fullmatch(r"sha512-[A-Za-z0-9+/]{86}==", integrity):
        raise StratagentError("Artifact requires one canonical SHA-512 SRI digest.")
    actual = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")
    if actual != integrity:
        raise StratagentError("Artifact SHA-512 integrity mismatch.")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
            raw = compressed.read(MAX_EXPANDED + 1)
        if len(raw) > MAX_EXPANDED:
            raise StratagentError("Artifact exceeds the 16 MiB expanded limit.")
        offset, headers = 0, 0
        if len(raw) % 512:
            raise StratagentError("Artifact tar blocks are truncated.")
        while offset + 512 <= len(raw) and any(raw[offset:offset + 512]):
            header = raw[offset:offset + 512]
            headers += 1
            if headers > 200 or header[156:157] not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
                raise StratagentError("Extended archive headers, links and more than 200 members are unsupported.")
            size = tarfile.nti(header[124:136])
            if not 0 <= size <= MAX_FILE or (header[156:157] == tarfile.DIRTYPE and size):
                raise StratagentError("Invalid or oversized archive member before parsing.")
            offset += 512 + ((size + 511) // 512) * 512
            if offset > len(raw):
                raise StratagentError("Truncated archive member payload.")
        if any(raw[offset:]):
            raise StratagentError("Trailing non-padding artifact content is unsupported.")
        result, modes, seen, components, total = {}, {}, set(), {}, 0
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            for count, member in enumerate(archive, 1):
                if count > 200:
                    raise StratagentError("Artifact exceeds 200 archive members.")
                path = safe_path(member.name.rstrip("/") if member.isdir() else member.name)
                if not path.startswith("package/") and not (path == "package" and member.isdir()):
                    raise StratagentError("npm artifact must stay inside package/.")
                if path.casefold() in seen or member.pax_headers or member.issparse():
                    raise StratagentError("Ambiguous, extended or sparse archive entries are unsupported.")
                for prefix in (PurePosixPath(path), *PurePosixPath(path).parents):
                    spelling = str(prefix)
                    if spelling.casefold() in components and components[spelling.casefold()] != spelling:
                        raise StratagentError("Archive contains case-colliding path components.")
                    components[spelling.casefold()] = spelling
                seen.add(path.casefold())
                if member.isdir():
                    continue
                if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or member.mode & 0o7000:
                    raise StratagentError("Archive links, devices and privileged modes are forbidden.")
                if not 0 <= member.size <= MAX_FILE:
                    raise StratagentError("Artifact member exceeds 256 KiB.")
                total += member.size
                if total > 8 * 1024 * 1024:
                    raise StratagentError("Artifact file payload exceeds 8 MiB.")
                handle = archive.extractfile(member)
                if handle is None:
                    raise StratagentError("Artifact member cannot be read.")
                with handle:
                    content = handle.read(MAX_FILE + 1)
                if len(content) != member.size:
                    raise StratagentError("Truncated artifact member.")
                result[path] = content
                modes[path] = member.mode & 0o777
            if any(raw[archive.offset:]):
                raise StratagentError("Trailing non-padding artifact content is unsupported.")
        if "package/package.json" not in result:
            raise StratagentError("Artifact has no package/package.json.")
        for path in result:
            if any(str(parent).casefold() in {item.casefold() for item in result} for parent in PurePosixPath(path).parents):
                raise StratagentError("Artifact contains file/directory collisions.")
        return result, modes
    except (OSError, EOFError, tarfile.TarError, ValueError, OverflowError):
        raise StratagentError("Invalid or unsupported bounded gzip/tar artifact.") from None


def audit_archive(data, integrity, package, version):
    files, modes = archive_files(data, integrity)
    manifest = strict_json(files["package/package.json"])
    if not isinstance(manifest, dict) or manifest.get("name") != package or manifest.get("version") != version:
        raise StratagentError("Artifact package identity differs from the approved exact version.")
    findings = [item for path, content in sorted(files.items()) for item in scan_text(path, content)]
    for path, mode in modes.items():
        if mode & 0o022:
            findings.append({"severity": "block", "rule": "writable-artifact-permissions", "path": path})
        if mode & 0o111:
            findings.append({"severity": "review", "rule": "executable-artifact-mode", "path": path})
    binaries = manifest.get("bin", {})
    if isinstance(binaries, str):
        binaries = {package.rsplit("/", 1)[-1]: binaries}
    if not isinstance(binaries, dict) or len(binaries) > 20 or any(not isinstance(value, str) for value in binaries.values()):
        raise StratagentError("Invalid or oversized package bin declaration.")
    for name, target in binaries.items():
        path = "package/" + safe_path(target.removeprefix("./"))
        if path not in files:
            findings.append({"severity": "block", "rule": "missing-package-entrypoint", "entrypoint": name})
    scripts = manifest.get("scripts", {})
    findings.extend(scan_text("decoded-package-metadata", decoded_strings(manifest)))
    if not isinstance(scripts, dict) or any(not isinstance(value, str) for value in scripts.values()):
        raise StratagentError("Invalid package scripts declaration.")
    for name in sorted(scripts):
        findings.append({"severity": "block" if name in {"preinstall", "install", "postinstall", "prepare", "prepublish", "prepublishOnly"} else "review",
                         "rule": "package-script", "script": name})
    dependencies = {}
    for field in ("dependencies", "optionalDependencies", "peerDependencies"):
        declared = manifest.get(field, {})
        if not isinstance(declared, dict) or len(declared) > 100 or any(not isinstance(value, str) for value in declared.values()):
            raise StratagentError("Invalid or oversized package dependency declaration.")
        dependencies[field] = declared
    if any(dependencies.values()) or manifest.get("bundledDependencies") or manifest.get("bundleDependencies"):
        findings.append({"severity": "block", "rule": "dependency-closure-unverified"})
    for path in files:
        if PurePosixPath(path).name == "binding.gyp":
            findings.append({"severity": "block", "rule": "implicit-native-install", "path": path})
    licenses = [path for path in files if PurePosixPath(path).parent == PurePosixPath("package") and PurePosixPath(path).name.lower() in LICENSE_NAMES]
    recognized = {license_id(decode_text(files[path])) for path in licenses}
    license_value = next(iter(recognized)) if len(recognized) == 1 else "UNKNOWN"
    if license_value not in PERMITTED_LICENSES or manifest.get("license") != license_value:
        findings.append({"severity": "block", "rule": "unapproved-artifact-license"})
    for path in files:
        if PurePosixPath(path).name.lower() in LICENSE_NAMES and path not in licenses:
            if license_id(decode_text(files[path])) != license_value:
                findings.append({"severity": "block", "rule": "nested-license-conflict", "path": path})
    result = {"schema_version": 1, "kind": "npm-artifact", "package": package, "version": version,
              "sha256": digest(data), "integrity": integrity, "license": license_value,
              "files": [{"path": path, "sha256": digest(content), "size": len(content), "mode": modes[path]} for path, content in sorted(files.items())],
              "entrypoints": binaries, "dependencies": dependencies, "findings": findings, "execution_eligible": False,
              "static_policy_passed": not any(item["severity"] == "block" for item in findings),
              "assurance": "SRI-verified bounded static artifact review, not signature verification, dependency closure or behavioral proof. No extraction or execution."}
    result["review_digest"] = identity(result)
    return result


def audit_tools(document):
    document = strict_json(canonical(document))
    result = document.get("result", document) if isinstance(document, dict) else None
    tools = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(tools, list) or len(tools) > 100:
        raise StratagentError("Tool evidence must contain a tools/list result with at most 100 tools.")
    findings, names, summaries = [], set(), []
    if result.get("nextCursor") is not None:
        findings.append({"severity": "block", "rule": "incomplete-tool-pagination"})
    for tool in tools:
        if (not isinstance(tool, dict) or not isinstance(tool.get("name"), str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", tool["name"]) or tool["name"] in names
                or not isinstance(tool.get("inputSchema"), dict) or tool["inputSchema"].get("type") != "object"):
            raise StratagentError("Invalid, duplicate or unsupported MCP tool definition.")
        names.add(tool["name"])
        annotations = tool.get("annotations", {})
        if not isinstance(annotations, dict) or any(type(annotations[key]) is not bool for key in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint") if key in annotations):
            raise StratagentError("Invalid MCP tool annotations.")
        description = tool.get("description", "")
        if not isinstance(description, str) or len(description) > 8000:
            raise StratagentError("Invalid MCP tool description.")
        findings.extend(scan_text("tool/" + tool["name"] + "/metadata", decoded_strings(tool)))
        pending = [tool]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if "$ref" in value and (not isinstance(value["$ref"], str) or not value["$ref"].startswith("#")):
                    findings.append({"severity": "block", "rule": "external-tool-schema-reference", "tool": tool["name"]})
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        summaries.append({"name": tool["name"], "declared_annotations": annotations,
                          "schema_sha256": identity(tool["inputSchema"]), "permissions_granted": []})
    result = {"schema_version": 1, "kind": "operator-supplied-tools-list", "manifest_sha256": identity(document),
              "tools": summaries, "findings": findings, "execution_eligible": False,
              "static_policy_passed": not any(item["severity"] == "block" for item in findings),
              "assurance": "Annotations and operator/server association are untrusted; schema/description review does not verify implementation or behavior. No server contacted."}
    result["review_digest"] = identity(result)
    return result
