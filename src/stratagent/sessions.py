"""Bounded research cohorts and freshness, not an evergreen internal registry."""
import re
import time
import uuid

from .blueprint import validate_shape
from .common import StratagentError, identity

TTL = 900
REFERENCE = {"type": "object", "additionalProperties": False, "required": ["id", "review_digest"],
             "properties": {"id": {"type": "string", "pattern": "^[0-9a-f]{16}$"}, "review_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}}
SESSION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["schema_version", "id", "project_digest", "mode", "created_at", "expires_at", "partial", "skills", "mcps", "search_approval", "digest"],
    "properties": {
        "schema_version": {"const": 1}, "id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
        "project_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "mode": {"enum": ["live", "offline-cache"]},
        "created_at": {"type": "integer", "minimum": 0, "maximum": 4102444800}, "expires_at": {"type": "integer", "minimum": 0, "maximum": 4102444800},
        "partial": {"type": "boolean"}, "search_approval": {"type": "string", "pattern": "^(?:[0-9a-f]{64})?$"},
        "skills": {"type": "array", "maxItems": 400, "uniqueItems": True, "items": REFERENCE},
        "mcps": {"type": "array", "maxItems": 400, "uniqueItems": True, "items": REFERENCE},
        "digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    },
}


def record(service, context, github, registry, errors, offline, search_approval, started_at):
    manifest = service.manifest()
    skills = list(manifest["candidates"].values()) if offline else (github or {}).get("candidates", [])
    mcps = list(manifest.get("mcp_candidates", {}).values()) if offline else [item for result in registry for item in result["candidates"]]
    def references(records):
        return [{"id": candidate_id, "review_digest": digest} for candidate_id, digest in sorted({item["id"]: item["review_digest"] for item in records}.items())]
    created = started_at
    result = {"schema_version": 1, "id": uuid.uuid4().hex, "project_digest": context["context_digest"], "mode": "offline-cache" if offline else "live",
              "created_at": created, "expires_at": created + TTL, "partial": bool(errors) or bool((github or {}).get("stopped_early"))
              or any(item.get("incomplete_results") for item in ((github or {}).get("research") or {}).get("queries", [])),
              "skills": references(skills), "mcps": references(mcps), "search_approval": search_approval or ""}
    result["digest"] = identity(result)
    validate_shape(result, SESSION_SCHEMA)
    with service.ws.mutation():
        path = f".stratagent/runs/{result['id']}.json"
        if service.ws.path(path).exists():
            raise StratagentError("Research run ID already exists; no run was overwritten.")
        service.ws.write(path, result)
    return result


def load(service, run_id, project_digest):
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise StratagentError("Research run ID must be 32 hexadecimal characters.")
    path = f".stratagent/runs/{run_id}.json"
    if not service.ws.path(path).exists():
        raise StratagentError("Unknown research run; prepare the workspace first.")
    result = service.ws.read(path)
    validate_shape(result, SESSION_SCHEMA)
    if result["id"] != run_id or result["digest"] != identity({key: value for key, value in result.items() if key != "digest"}):
        raise StratagentError("Research run evidence changed; prepare again.")
    current = int(time.time())
    if result["expires_at"] != result["created_at"] + TTL or result["created_at"] > current + 5 or current >= result["expires_at"]:
        raise StratagentError("Research run expired or has invalid freshness timestamps; prepare again. Existing installed files remain verifiable.")
    if result["project_digest"] != project_digest:
        raise StratagentError("Project or targets changed since research; prepare again.")
    for kind, records in (("skills", service.manifest()["candidates"]), ("mcps", service.manifest().get("mcp_candidates", {}))):
        if len({item["id"] for item in result[kind]}) != len(result[kind]):
            raise StratagentError("Research run contains duplicate source identities.")
        for item in result[kind]:
            if records.get(item["id"], {}).get("review_digest") != item["review_digest"]:
                raise StratagentError("Research source changed after the run; prepare again.")
    return result
