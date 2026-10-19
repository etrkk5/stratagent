"""Read-only GitHub REST client. No git clone, archives, redirects, or execution."""
import base64
import json
import os
import ssl
import sys
from pathlib import Path
from pathlib import PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from . import __version__
from .common import StratagentError, MAX_BUNDLE, MAX_FILE, MAX_FILES, SHA, git_blob, repository, safe_path
from .security import NOTICE_NAMES

SEEDS = ("openai/skills", "anthropics/skills", "voltagent/awesome-claude-code-subagents")


class GitHubLimitError(StratagentError):
    """Stop discovery rather than repeating requests after a global limit."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise StratagentError("HTTPS API redirect refused; use the canonical source.")


class GitHub:
    def __init__(self, token=None, request_limit=100):
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        if self.token and any(ord(c) < 33 or ord(c) > 126 for c in self.token):
            raise StratagentError("GITHUB_TOKEN contains invalid characters.")
        self.remaining = request_limit
        self.halted = None
        context = ssl.create_default_context()
        # python.org macOS builds may ship without their optional CA bundle.
        # Use the OS CA file when available; TLS verification is never disabled.
        if sys.platform == "darwin" and not ssl.get_default_verify_paths().cafile and not os.environ.get("SSL_CERT_FILE"):
            os_ca = Path("/etc/ssl/cert.pem")
            if os_ca.is_file():
                context.load_verify_locations(cafile=str(os_ca))
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=context))
        self.cache = {}

    def get(self, endpoint, params=None):
        if not endpoint.startswith(("/repos/", "/search/repositories")) or ".." in endpoint or ":" in endpoint:
            raise StratagentError("Disallowed GitHub API endpoint.")
        url = "https://api.github.com" + endpoint
        if params:
            url += "?" + urlencode(params)
        if url in self.cache:
            return self.cache[url]
        if self.halted:
            raise GitHubLimitError(self.halted)
        if self.remaining <= 0:
            self.halted = "GitHub request budget exhausted; narrow discovery with --repo/--limit."
            raise GitHubLimitError(self.halted)
        self.remaining -= 1
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "StratAgent/" + __version__,
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            with self.opener.open(Request(url, headers=headers), timeout=20) as response:
                data = response.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024:
                    raise StratagentError("GitHub response exceeds 8 MiB limit.")
            result = json.loads(data)
            if not isinstance(result, dict):
                raise StratagentError("Invalid GitHub response shape.")
        except HTTPError as exc:
            status = exc.code
            exc.close()
            if status in (403, 429):
                self.halted = "GitHub access/rate limit reached. Retry later or set a read-only GITHUB_TOKEN."
                raise GitHubLimitError(self.halted) from None
            if status == 404:
                raise StratagentError("GitHub repository/ref not found or not accessible.") from None
            raise StratagentError(f"GitHub HTTP {status}; request failed.") from None
        except URLError as exc:
            if isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise StratagentError("GitHub TLS certificate verification failed. Configure a trusted SSL_CERT_FILE; verification cannot be disabled.") from None
            raise StratagentError("Cannot reach GitHub securely. Check network access; use the offline demo to work locally.") from None
        except (TimeoutError, OSError):
            raise StratagentError("Cannot reach GitHub securely. Check network access; use the offline demo to work locally.") from None
        except (ValueError, UnicodeError):
            raise StratagentError("Invalid JSON from GitHub.") from None
        self.cache[url] = result
        return result

    def search(self, terms, limit=4):
        query = " ".join(terms[:2]) + " agent skills"
        result = self.get("/search/repositories", {"q": query, "per_page": limit, "sort": "stars"})
        return [repository(item["full_name"]) for item in result.get("items", [])[:limit]]

    def tree(self, repo):
        repo = repository(repo)
        info = self.get(f"/repos/{repo}")
        branch = quote(info["default_branch"], safe="")
        revision = self.get(f"/repos/{repo}/commits/{branch}")
        commit = revision["sha"]
        tree_sha = revision["commit"]["tree"]["sha"]
        if not SHA.fullmatch(commit) or not SHA.fullmatch(tree_sha):
            raise StratagentError("GitHub did not return immutable commit/tree identities.")
        tree = self.get(f"/repos/{repo}/git/trees/{tree_sha}", {"recursive": "1"})
        if tree.get("truncated"):
            raise StratagentError("GitHub tree is truncated; cannot safely inspect this repository.")
        records = tree.get("tree", [])
        if len(records) > 40_000:
            raise StratagentError("Repository tree exceeds MVP limit.")
        seen = set()
        for record in records:
            path = safe_path(record["path"])
            if path.casefold() in seen:
                raise StratagentError("Repository contains case-colliding paths.")
            seen.add(path.casefold())
        return {"repo": repo, "commit": commit, "stars": info.get("stargazers_count", 0),
                "records": records, "url": f"https://github.com/{repo}/tree/{commit}"}

    def definitions(self, tree, terms=()):
        entries = []
        for record in tree["records"]:
            path = PurePosixPath(record["path"])
            if record["type"] == "blob" and path.name == "SKILL.md":
                entries.append((str(path), "skill"))
            elif record["type"] == "blob" and path.suffix == ".md" and any(p in ("agents", "subagents", "categories") for p in path.parts[:-1]) and path.stem.lower() not in ("readme", "agents", "changelog"):
                entries.append((str(path), "subagent"))
        return sorted(entries, key=lambda x: (-sum(t.casefold() in x[0].casefold() for t in terms), x[0]))

    def snapshot(self, tree, entry, kind):
        entry_path = PurePosixPath(entry)
        records = []
        for record in tree["records"]:
            p = PurePosixPath(record["path"])
            in_bundle = (p == entry_path if kind == "subagent" else entry_path.parent in p.parents)
            license_file = p.name.lower() in NOTICE_NAMES and p.parent in (entry_path.parent, *entry_path.parent.parents)
            if (in_bundle and record["type"] != "tree") or license_file:
                records.append(record)
        if not 1 <= len(records) <= MAX_FILES:
            raise StratagentError("Bundle exceeds the 80-file limit or is empty.")
        total = 0
        for record in records:
            if record["type"] != "blob" or record["mode"] != "100644":
                raise StratagentError("Bundle contains symlinks, executables or submodules.")
            size = record.get("size", MAX_FILE + 1)
            if size > MAX_FILE or size < 0:
                raise StratagentError("Bundle file exceeds 256 KiB limit.")
            total += size
            if total > MAX_BUNDLE:
                raise StratagentError("Bundle exceeds 2 MiB limit.")
        files = []
        for record in sorted(records, key=lambda r: r["path"]):
            sha = record["sha"]
            if not SHA.fullmatch(sha):
                raise StratagentError("Invalid Git blob identity.")
            blob = self.get(f"/repos/{tree['repo']}/git/blobs/{sha}")
            if blob.get("encoding") != "base64":
                raise StratagentError("GitHub blob is not base64 encoded.")
            try:
                data = base64.b64decode("".join(blob["content"].split()), validate=True)
            except (ValueError, TypeError):
                raise StratagentError("Invalid GitHub blob encoding.") from None
            if git_blob(data) != sha or len(data) != record["size"]:
                raise StratagentError("GitHub content does not match the pinned tree.")
            files.append({"path": record["path"], "git_sha": sha, "mode": record["mode"],
                          "data": base64.b64encode(data).decode("ascii")})
        return {"schema_version": 1, "repo": tree["repo"], "commit": tree["commit"],
                "stars": tree["stars"], "entry": entry, "kind": kind, "files": files,
                "origin": "github-api"}
