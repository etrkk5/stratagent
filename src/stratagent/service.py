"""Shared application services for CLI and a read-only MCP surface."""
import hmac
from datetime import datetime, timezone

from . import __version__
from .adapters import platforms, render_bundle, render_tasks
from .common import StratagentError, digest, identity, repository
from .github import GitHub, GitHubLimitError, SEEDS
from .planner import analyze
from .planner import words
from .security import assess, unpack
from .workspace import Workspace

MANIFEST = ".stratagent/manifest.json"
LOCK = ".stratagent/lock.json"
POLICY = ".stratagent/policy.json"


def now():
    return datetime.now(timezone.utc).isoformat()


class Stratagent:
    def __init__(self, root, github=None):
        self.ws = Workspace(root)
        self.github = github

    def manifest(self):
        value = self.ws.read(MANIFEST)
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise StratagentError("Unsupported manifest schema; expected version 1.")
        platforms(value.get("platforms"))
        if not isinstance(value.get("candidates"), dict) or not isinstance(value.get("analysis"), dict):
            raise StratagentError("Invalid manifest structure.")
        return value

    def init(self, prompt, targets):
        result = {"schema_version": 1, "name": "Stratagent workspace", "created_at": now(),
                  "platforms": platforms(targets), "analysis": analyze(prompt), "candidates": {}}
        with self.ws.mutation():
            if self.ws.path(MANIFEST).exists():
                raise StratagentError("Workspace already initialized; refusing to replace the manifest.")
            self.ws.write(POLICY, {"schema_version": 1, "allow_repositories": []})
            self.ws.write(LOCK, {"schema_version": 1, "generator_version": __version__, "installations": {}})
            self.ws.write(MANIFEST, result)
        return result

    def _save(self, snapshots, reviews):
        with self.ws.mutation():
            manifest = self.manifest()
            for snapshot, review in zip(snapshots, reviews):
                self.ws.write(f".stratagent/cache/{review['review_digest']}.json", snapshot)
                manifest["candidates"][review["id"]] = review
            self.ws.write(MANIFEST, manifest)

    def discover(self, repos=None, limit=6, save=True):
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise StratagentError("Discovery limit must be between 1 and 20.")
        manifest = self.manifest()
        terms = manifest["analysis"]["search_terms"]
        client = self.github or GitHub()
        errors = []
        if repos:
            sources = list(dict.fromkeys(repository(r) for r in repos))
        else:
            try:
                sources = client.search(terms, limit=3)
            except GitHubLimitError as exc:
                return {"candidates": [], "errors": [{"repo": "repository-search", "error": str(exc)}],
                        "saved": False, "stopped_early": True}
            except StratagentError as exc:
                errors.append({"repo": "repository-search", "error": str(exc)})
                sources = []
            sources = list(dict.fromkeys([*sources, *SEEDS]))
        if len(sources) > 8:
            raise StratagentError("At most eight repositories may be inspected per discovery.")
        snapshots, reviews = [], []
        # Select across repositories before filling the requested total limit.
        pools = []
        for repo in sources:
            try:
                tree = client.tree(repo)
                pools.append((tree, iter(client.definitions(tree, terms))))
            except GitHubLimitError as exc:
                return {"candidates": [], "errors": [*errors, {"repo": repo, "error": str(exc)}],
                        "saved": False, "stopped_early": True}
            except StratagentError as exc:
                errors.append({"repo": repo, "error": str(exc)})
        attempts = 0
        stopped = False
        while pools and len(reviews) < limit and attempts < 40:
            remaining = []
            for tree, entries in pools:
                if len(reviews) >= limit:
                    break
                try:
                    entry, kind = next(entries)
                except StopIteration:
                    continue
                remaining.append((tree, entries))
                attempts += 1
                try:
                    snapshot = client.snapshot(tree, entry, kind)
                    review = assess(snapshot, terms)
                    snapshots.append(snapshot)
                    reviews.append(review)
                except GitHubLimitError as exc:
                    errors.append({"repo": tree["repo"], "entry": entry, "error": str(exc)})
                    stopped = True
                    break
                except StratagentError as exc:
                    errors.append({"repo": tree["repo"], "entry": entry, "error": str(exc)})
            pools = remaining
            if stopped:
                break
        if save and snapshots:
            self._save(snapshots, reviews)
        reviews.sort(key=lambda r: (r["eligible"], r["ranking"]["score"]), reverse=True)
        return {"candidates": reviews, "errors": errors, "saved": save and bool(snapshots), "stopped_early": stopped,
                "note": "Discovery is bounded, not exhaustive. No repository is automatically trusted."}

    def import_snapshot(self, snapshot):
        """Offline evidence is useful for demos, but must never impersonate GitHub."""
        review = assess(snapshot, self.manifest()["analysis"]["search_terms"])
        # This is intentionally not a public import command. The demo can only use
        # the bundled example and has a separate origin shown in approval/provenance.
        self._save([snapshot], [review])
        return review

    def inspect(self, candidate_id, content=False):
        manifest = self.manifest()
        if candidate_id not in manifest["candidates"]:
            raise StratagentError("Unknown candidate ID; run discover or demo first.")
        saved = manifest["candidates"][candidate_id]
        review_digest = saved.get("review_digest", "")
        if not isinstance(review_digest, str) or len(review_digest) != 64 or any(c not in "0123456789abcdef" for c in review_digest):
            raise StratagentError("Invalid review digest in manifest.")
        snapshot = self.ws.read(f".stratagent/cache/{review_digest}.json")
        actual = assess(snapshot, manifest["analysis"]["search_terms"])
        if not hmac.compare_digest(actual["review_digest"], review_digest) or actual["id"] != candidate_id:
            raise StratagentError("Cached evidence changed; discover and review again.")
        result = {**actual, "origin": snapshot.get("origin", "unknown"),
                  "source_url": f"https://github.com/{actual['repo']}/blob/{actual['commit']}/{actual['entry']}"}
        if content:
            result["untrusted_file_contents"] = {p: d.decode() for p, d in unpack(snapshot).items()}
        return result, snapshot

    def allow(self, repo):
        repo = repository(repo)
        with self.ws.mutation():
            self.manifest()
            policy = self.ws.read(POLICY)
            allowed = set(policy["allow_repositories"])
            allowed.add(repo)
            policy["allow_repositories"] = sorted(allowed)
            self.ws.write(POLICY, policy)
        return policy

    def recommend(self):
        manifest = self.manifest()
        candidates = [self.inspect(candidate_id)[0] for candidate_id in manifest["candidates"]]
        proposals = []
        for task in manifest["analysis"]["tasks"]:
            role_terms = {
                "design": {"architect", "architecture", "design", "interfaces"},
                "build": set(manifest["analysis"]["domains"]) | {"implement", "implementation", "developer"},
                "test": {"test", "testing", "tests", "qa", "regression"},
                "security": {"security", "secure", "audit", "privacy", "license"},
                "release": {"documentation", "release", "maintainer", "readme"},
            }[task["id"]]
            matches = []
            for candidate in candidates:
                overlap = role_terms & words(candidate["name"].replace("-", " ") + " " + candidate["description"])
                if candidate["eligible"] and overlap:
                    matches.append({"candidate_id": candidate["id"], "name": candidate["name"],
                                    "role_matches": sorted(overlap), "score": round(len(overlap) * 10 + candidate["ranking"]["score"] / 10, 2),
                                    "review_digest": candidate["review_digest"]})
            matches.sort(key=lambda m: (-m["score"], m["candidate_id"]))
            proposals.append({"task_id": task["id"], "agent": task["agent"], "candidates": matches[:3]})
        return {"method": "role-keywords-v1", "proposals": proposals,
                "note": "Suggestions are not approvals. Only explicitly installed resources enter generated task configuration."}

    def _plan(self, files, source, origin, review_digest):
        outputs = [{"path": p, "sha256": digest(d), "size": len(d)} for p, d in sorted(files.items())]
        payload = {"schema_version": 1, "workspace": str(self.ws.root), "generator_version": __version__,
                   "source": source, "origin": origin, "review_digest": review_digest, "outputs": outputs}
        return {**payload, "approval": identity(payload)}

    def preview(self, candidate_id):
        manifest = self.manifest()
        review, snapshot = self.inspect(candidate_id)
        if not review["eligible"]:
            raise StratagentError("Candidate is blocked by policy. Inspect findings; there is no force-install option.")
        files = render_bundle(review, unpack(snapshot), manifest["platforms"])
        plan = self._plan(files, {"candidate_id": candidate_id, "repo": review["repo"],
                                 "commit": review["commit"], "entry": review["entry"],
                                 "license": review["license"], "source_files": review["files"]},
                          review["origin"], review["review_digest"])
        policy = self.ws.read(POLICY)
        plan["repository_allowed"] = review["repo"] in policy["allow_repositories"]
        plan["dry_run"] = True
        return plan, files

    def preview_config(self):
        manifest = self.manifest()
        # Validate locally editable task data instead of trusting arbitrary paths.
        expected = analyze(manifest["analysis"]["prompt"])
        lock = self.ws.read(LOCK)
        if not self.verify()["ok"]:
            raise StratagentError("Installed files have drift; resolve verification before configuring tasks.")
        assignments = []
        recommendations = self.recommend()
        for proposal in recommendations["proposals"]:
            resources = []
            for match in proposal["candidates"]:
                installed = lock["installations"].get("candidate:" + match["candidate_id"])
                if installed and installed["review_digest"] == match["review_digest"]:
                    paths = [f["path"] for f in installed["outputs"] if f["path"].endswith("/SKILL.md") or f["path"].startswith(".claude/agents/")]
                    resources.append({"candidate_id": match["candidate_id"], "paths": paths,
                                      "review_digest": match["review_digest"]})
            assignments.append({"task_id": proposal["task_id"], "agent": proposal["agent"], "resources": resources})
        task_config = {"schema_version": 1, "analysis": expected, "assignments": assignments,
                       "execution": "manual-delegation-only"}
        files = render_tasks(task_config, manifest["platforms"])
        from .common import canonical
        files[".stratagent/task-plan.json"] = canonical(task_config) + b"\n"
        plan = self._plan(files, {"kind": "task-configuration", "task_plan": task_config}, "generated-local", identity(task_config))
        plan["dry_run"] = True
        return plan, files

    def _apply(self, plan, files, approval, key):
        if not isinstance(approval, str) or not hmac.compare_digest(approval, plan["approval"]):
            raise StratagentError("Approval digest does not match this exact plan. Run dry-run, review, and approve that digest.")
        lock = self.ws.read(LOCK)
        if lock.get("schema_version") != 1 or not isinstance(lock.get("installations"), dict):
            raise StratagentError("Invalid lockfile schema.")
        if key in lock["installations"]:
            previous = lock["installations"][key]
            if previous.get("approval") == approval:
                mismatches = self.verify()["mismatches"]
                if mismatches:
                    raise StratagentError("Installed files changed; verify reports drift. Refusing to overwrite.")
                return {"applied": False, "already_installed": True, "approval": approval}
            raise StratagentError("An older installation exists; automatic upgrades are not supported in this MVP.")
        created = self.ws.create_files(files)
        try:
            lock["installations"][key] = {**plan, "dry_run": False, "installed_at": now(),
                                         "provenance": {"tool": "Stratagent", "version": __version__, "execution": "none"}}
            self.ws.write(LOCK, lock)
        except BaseException:
            for path in reversed(created):
                self.ws.path(path).unlink()
            raise
        return {"applied": True, "approval": approval, "written": created, "lockfile": LOCK}

    def install(self, candidate_id, approval=None, apply=False):
        if not apply:
            return self.preview(candidate_id)[0]
        with self.ws.mutation():
            plan, files = self.preview(candidate_id)
            if not plan["repository_allowed"]:
                raise StratagentError("Repository is not allowed. Review it, then run allow owner/repo.")
            return self._apply(plan, files, approval, "candidate:" + candidate_id)

    def configure(self, approval=None, apply=False):
        if not apply:
            return self.preview_config()[0]
        with self.ws.mutation():
            plan, files = self.preview_config()
            return self._apply(plan, files, approval, "task-configuration")

    def verify(self):
        self.manifest()
        lock = self.ws.read(LOCK)
        if lock.get("schema_version") != 1 or not isinstance(lock.get("installations"), dict):
            raise StratagentError("Invalid lockfile schema.")
        mismatches, checked = [], 0
        for installation in lock["installations"].values():
            for output in installation["outputs"]:
                checked += 1
                path = self.ws.path(output["path"])
                if not path.is_file():
                    mismatches.append({"path": output["path"], "reason": "missing"})
                elif path.stat().st_size != output["size"] or digest(path.read_bytes()) != output["sha256"]:
                    mismatches.append({"path": output["path"], "reason": "content-drift"})
        return {"ok": not mismatches, "checked": checked, "mismatches": mismatches}

    def status(self):
        manifest = self.manifest()
        return {"schema_version": 1, "workspace": str(self.ws.root), "platforms": manifest["platforms"],
                "analysis": manifest["analysis"], "candidates": list(manifest["candidates"].values()),
                "policy": self.ws.read(POLICY), "verification": self.verify()}
