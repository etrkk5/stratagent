"""Official MCP Registry discovery. Metadata review never executes a server."""
import ipaddress
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request

from .common import StratagentError, canonical, decode_text, identity, repository
from .github import GitHub
from .hosts import get_adapter, merge_outputs, platforms
from .planner import words
from .security import RULES

REGISTRY = "https://registry.modelcontextprotocol.io"
OFFICIAL = "io.modelcontextprotocol.registry/official"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)?\Z")
PACKAGE = re.compile(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*\Z")
SERVER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}/[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")


def public_https(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 2000 or any(char in value for char in "{}\\%") or any(ord(char) <= 32 or ord(char) >= 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None, 443):
            return False
        if not host or "." not in host or not re.fullmatch(r"[A-Za-z]{2,63}", host.rsplit(".", 1)[-1]) or host.endswith((".local", ".internal", ".localhost", ".")):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            return len(host) <= 253 and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in host.split("."))
    except ValueError:
        return False


class Registry:
    def __init__(self):
        self.opener = GitHub(token="").opener

    def search(self, query, limit=6):
        if not isinstance(query, str) or not 2 <= len(query) <= 100 or not re.fullmatch(r"[\w .-]+", query):
            raise StratagentError("Registry query must be 2–100 letters, digits, spaces, dots or hyphens.")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise StratagentError("Registry discovery limit must be between 1 and 20.")
        url = REGISTRY + "/v0.1/servers?" + urlencode({"search": query, "version": "latest", "limit": limit})
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "StratAgent"})
            with self.opener.open(request, timeout=20) as response:
                data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise StratagentError("Registry response exceeds 2 MiB limit.")
            result = json.loads(data)
            if not isinstance(result, dict) or not isinstance(result.get("servers"), list) or len(result["servers"]) > 100:
                raise StratagentError("Invalid Registry response shape.")
            return result["servers"][:limit]
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise StratagentError(f"MCP Registry HTTP {status}; retry later or narrow the query.") from None
        except (URLError, TimeoutError, OSError):
            raise StratagentError("Cannot reach the MCP Registry securely; cached reviews remain available offline.") from None
        except (ValueError, UnicodeError, RecursionError):
            raise StratagentError("Invalid JSON from the MCP Registry.") from None


def assess_server(envelope, terms=()):
    try:
        decode_text(canonical(envelope))
        server = envelope["server"]
        name, version, description = server["name"], server["version"], server["description"]
        if not isinstance(name, str) or not SERVER.fullmatch(name):
            raise ValueError("Invalid server name")
        if not isinstance(version, str) or not 1 <= len(version) <= 100 or any(ord(char) < 33 or ord(char) > 126 for char in version):
            raise ValueError("Invalid server version")
        if not isinstance(description, str) or not 1 <= len(description) <= 10000:
            raise ValueError("Invalid server description")
        decode_text(description.encode())
        status = envelope.get("_meta", {}).get(OFFICIAL, {}).get("status", "unknown")
        source = server.get("repository", {}).get("url", "")
        repo = None
        if isinstance(source, str) and source.startswith("https://github.com/"):
            repo = repository(source.removeprefix("https://github.com/").removesuffix(".git"))
        packages, remotes = server.get("packages", []), server.get("remotes", [])
        if not isinstance(packages, list) or not isinstance(remotes, list) or len(packages) + len(remotes) > 40:
            raise ValueError("Invalid transports")
        findings = [{"severity": "review", "rule": "metadata-only",
                     "detail": "Registry provenance identifies metadata, not executable integrity, license or tool permissions. Review source and artifacts separately."}]
        if status != "active":
            findings.append({"severity": "block", "rule": "inactive-or-unknown-status"})
        for rule, pattern in RULES:
            if re.search(pattern, description, re.I | re.M):
                findings.append({"severity": "block", "rule": rule})
        options = []
        for package in packages:
            identifier, package_version = package.get("identifier", ""), package.get("version", "")
            supported = (package.get("registryType") == "npm"
                         and package.get("registryBaseUrl", "https://registry.npmjs.org") == "https://registry.npmjs.org"
                         and isinstance(identifier, str) and PACKAGE.fullmatch(identifier)
                         and isinstance(package_version, str) and VERSION.fullmatch(package_version)
                         and package.get("transport", {}).get("type") == "stdio"
                         and package.get("runtimeHint") in (None, "npx")
                         and not any(package.get(field) for field in ("runtimeArguments", "packageArguments", "environmentVariables"))
                         and repo is not None)
            if supported:
                options.append({"type": "stdio", "command": "npx", "args": ["--yes", f"{identifier}@{package_version}"],
                                "package": identifier, "version": package_version,
                                "integrity": "version-pinned; executable artifact digest not verified"})
            else:
                findings.append({"severity": "review", "rule": "unsupported-package", "detail": "Only exact-version npm stdio packages without runtime overrides, arguments or environment are rendered."})
        for remote in remotes:
            if remote.get("type") == "streamable-http" and public_https(remote.get("url")) and not remote.get("headers") and not remote.get("variables"):
                options.append({"type": "http", "url": remote["url"], "integrity": "mutable remote service; metadata digest does not pin server behavior"})
            else:
                findings.append({"severity": "review", "rule": "unsupported-remote", "detail": "Only public HTTPS Streamable HTTP without embedded credentials, headers, variables or query is rendered."})
        if not options:
            findings.append({"severity": "block", "rule": "no-supported-transport"})
        requested = set().union(*(words(term) for term in terms)) if terms else set()
        overlap = sorted(requested & words(name.replace("-", " ") + " " + description))
        result = {"id": identity({"name": name, "version": version})[:16], "name": name, "version": version,
                  "description": description, "repo": repo, "status": status, "source_url": source,
                  "registry_url": REGISTRY + "/v0.1/servers/" + quote(name, safe="") + "/versions/" + quote(version, safe=""),
                  "origin": "official-mcp-registry", "metadata_sha256": identity(envelope), "scanner_version": 1,
                  "findings": findings, "options": options, "eligible": not any(finding["severity"] == "block" for finding in findings),
                  "ranking": {"score": round(100 * len(overlap) / max(1, len(requested)), 2), "matched_terms": overlap,
                              "note": "Metadata relevance only. Registry presence and publisher identity are not a safety endorsement."}}
        result["review_digest"] = identity({key: value for key, value in result.items() if key != "ranking"})
        return result
    except (KeyError, ValueError, TypeError, AttributeError, RecursionError):
        raise StratagentError("Invalid MCP Registry server metadata; no configuration generated.") from None


def render_server(review, option, targets):
    if not isinstance(option, int) or isinstance(option, bool) or not 0 <= option < len(review["options"]):
        raise StratagentError("Select a transport option index from inspect-mcp (starting at 0).")
    selected = review["options"][option]
    name = "sa-" + review["id"]
    root = f".stratagent/proposals/mcp/{review['id']}/{option}"
    result = {}
    for target in platforms(targets):
        adapter = get_adapter(target)
        if adapter.mcp_renderer is not None:
            filename, data = adapter.mcp_renderer(name, selected)
            merge_outputs(result, {root + "/" + filename: data})
    result[root + "/review.json"] = canonical({"review": review, "selected_option": option, "activation": "manual-only"}) + b"\n"
    return result
