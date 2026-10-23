"""Bounded dependency and local agent evidence; no execution or secret-file scan."""
import json
import os
import re
import stat
import tomllib

from .common import MAX_FILE, StratagentError, digest, identity
from .environment import inspect_environment

MANIFEST_NAMES = ("package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod")
DEPENDENCIES = {
    "react": ("web", "react"), "next": ("web", "nextjs"), "vue": ("web", "vue"),
    "typescript": ("web", "typescript"), "fastapi": ("python", "api", "fastapi"),
    "django": ("python", "api", "django"), "flask": ("python", "api", "flask"),
    "express": ("api", "node"), "hono": ("api", "node"),
    "pandas": ("data", "python"), "numpy": ("data", "python"), "polars": ("data", "python"),
    "sqlalchemy": ("data", "database", "python"), "prisma": ("database",),
    "pg": ("database", "postgresql"), "psycopg": ("database", "postgresql", "python"),
    "psycopg2": ("database", "postgresql", "python"), "pytest": ("testing", "python"),
    "vitest": ("testing", "web"), "@playwright/test": ("testing", "web", "playwright"),
    "playwright": ("testing", "web", "playwright"), "mcp": ("agents", "python"),
    "@modelcontextprotocol/sdk": ("agents", "node"), "tokio": ("rust", "api"),
    "axum": ("rust", "api"), "serde": ("rust",), "github.com/gin-gonic/gin": ("go", "api"),
}


def dependency_names(name, data):
    if name == "package.json":
        parsed = json.loads(data)
        if not isinstance(parsed, dict):
            raise ValueError("Expected object")
        result = []
        for field in ("dependencies", "devDependencies", "peerDependencies"):
            section = parsed.get(field, {})
            if not isinstance(section, dict):
                raise ValueError("Expected dependency object")
            result.extend(section)
        return result
    if name in ("pyproject.toml", "Cargo.toml"):
        parsed = tomllib.loads(data.decode("utf-8"))
        if name == "Cargo.toml":
            return list(parsed.get("dependencies", {})) + list(parsed.get("dev-dependencies", {}))
        project = parsed.get("project", {})
        entries = list(project.get("dependencies", []))
        for group in project.get("optional-dependencies", {}).values():
            entries.extend(group)
        for group in parsed.get("dependency-groups", {}).values():
            entries.extend(item for item in group if isinstance(item, str))
        entries.extend(parsed.get("tool", {}).get("poetry", {}).get("dependencies", {}))
        return [re.split(r"[\s\[<>=!~;]", item, maxsplit=1)[0].lower().replace("_", "-") for item in entries]
    text = data.decode("utf-8")
    if name == "requirements.txt":
        return [re.split(r"[\s\[<>=!~;]", line.strip(), maxsplit=1)[0].lower().replace("_", "-")
                for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("#", "-"))]
    entries = [line.strip().split() for line in text.splitlines() if line.strip()]
    return [fields[1] if fields[0] == "require" and len(fields) > 1 else fields[0] for fields in entries]


def inspect_project(workspace):
    paths, warnings = list(MANIFEST_NAMES), []
    for directory in ("apps", "packages"):
        try:
            parent = workspace.path(directory)
            if not parent.is_dir():
                continue
            children = []
            with os.scandir(parent) as entries:
                for count, entry in enumerate(entries):
                    if count >= 64:
                        warnings.append({"path": directory, "reason": "directory-limit"})
                        break
                    if not entry.is_symlink() and entry.is_dir(follow_symlinks=False):
                        children.append(entry.name)
            for child in sorted(children)[:8]:
                paths.extend(f"{directory}/{child}/{name}" for name in MANIFEST_NAMES)
            if len(children) > 8:
                warnings.append({"path": directory, "reason": "package-limit"})
        except (StratagentError, OSError):
            warnings.append({"path": directory, "reason": "unsafe-or-unreadable-directory"})
    evidence, signals = [], []
    for relative in paths:
        try:
            path = workspace.path(relative)
            if not path.exists():
                continue
            if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > MAX_FILE:
                warnings.append({"path": relative, "reason": "not-small-regular-file"})
                continue
            with path.open("rb") as handle:
                data = handle.read(MAX_FILE + 1)
            if len(data) > MAX_FILE:
                raise ValueError("Manifest grew")
            names = dependency_names(path.name, data)
            recognized = sorted(set(names) & set(DEPENDENCIES))
            domains = {"package.json": [], "pyproject.toml": ["python"], "requirements.txt": ["python"],
                       "Cargo.toml": ["rust"], "go.mod": ["go"]}[path.name]
            signals.extend({"term": term, "source": relative, "evidence": "manifest-format"} for term in domains)
            signals.extend({"term": term, "source": relative, "evidence": dependency}
                           for dependency in recognized for term in DEPENDENCIES[dependency])
            evidence.append({"path": relative, "sha256": digest(data), "dependencies": recognized})
        except StratagentError:
            warnings.append({"path": relative, "reason": "unsafe-path"})
        except (OSError, ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
            warnings.append({"path": relative, "reason": "unreadable-or-invalid-manifest"})
    result = {"method": "bounded-manifests-v1", "files": evidence, "signals": signals, "warnings": warnings,
              "environment": inspect_environment(workspace, include_managed=False)["planning"],
              "limits": {"bytes_per_file": MAX_FILE, "packages_per_directory": 8, "recursive_source_scan": False}}
    return {**result, "fingerprint": identity(result)}
