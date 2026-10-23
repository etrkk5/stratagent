"""Model-neutral research proposals; outbound data needs separate user approval."""
import re

from .blueprint import validate_shape
from .common import StratagentError, canonical, identity

TEXT = {"type": "string", "minLength": 3, "maxLength": 500}
EVIDENCE = {"type": "array", "minItems": 1, "maxItems": 10, "uniqueItems": True, "items": {"type": "string", "maxLength": 200}}
GROUNDING = {"reason": TEXT, "quote": {"type": "string", "minLength": 3, "maxLength": 200}, "evidence_refs": EVIDENCE}
RESEARCH_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["schema_version", "context_digest", "reason", "github_queries", "mcp_queries", "budgets"],
    "properties": {
        "schema_version": {"const": 1}, "context_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "reason": TEXT,
        "github_queries": {"type": "array", "maxItems": 8, "items": {
            "type": "object", "additionalProperties": False, "required": ["kind", "terms", *GROUNDING],
            "properties": {"kind": {"enum": ["skills", "subagents", "mcp"]}, **GROUNDING,
                           "terms": {"type": "array", "minItems": 1, "maxItems": 5, "uniqueItems": True,
                                     "items": {"type": "string", "minLength": 2, "maxLength": 60, "pattern": "^[A-Za-z0-9][A-Za-z0-9 ._+\\-]*$"}}}}},
        "mcp_queries": {"type": "array", "maxItems": 6, "items": {
            "type": "object", "additionalProperties": False, "required": ["term", *GROUNDING],
            "properties": {"term": {"type": "string", "minLength": 2, "maxLength": 100, "pattern": "^[A-Za-z0-9][A-Za-z0-9 ._\\-]*$"}, **GROUNDING}}},
        "budgets": {"type": "object", "additionalProperties": False, "required": ["repositories", "definitions", "mcp_results"],
                    "properties": {name: {"type": "integer", "minimum": 1, "maximum": 20} for name in ("repositories", "definitions", "mcp_results")}},
    },
}


def project_context(analysis, targets):
    evidence = [{"id": "request", "text": analysis["prompt"]}]
    evidence.extend({"id": "manifest:" + record["path"], "data": record} for record in (analysis.get("project") or {}).get("files", []))
    evidence.extend({"id": "environment:" + record["path"], "source": "untrusted-local-definition", "data": record}
                    for record in (analysis.get("project") or {}).get("environment", {}).get("files", []))
    result = {"schema_version": 1, "analysis": analysis, "targets": targets, "evidence": evidence}
    return {**result, "context_digest": identity(result)}


def preview(context, plan, workspace):
    if len(canonical(plan)) > 32 * 1024:
        raise StratagentError("Research proposal exceeds 32 KiB.")
    validate_shape(plan, RESEARCH_SCHEMA)
    if plan["context_digest"] != context["context_digest"]:
        raise StratagentError("Research context is stale; request a new runtime research plan.")
    if not plan["github_queries"] and not plan["mcp_queries"]:
        raise StratagentError("Research plan needs at least one query; use --offline for cached-only preparation.")
    references = {item["id"] for item in context["evidence"]}
    for item in [*plan["github_queries"], *plan["mcp_queries"]]:
        if set(item["evidence_refs"]) - references or item["quote"] not in context["analysis"]["prompt"] or "request" not in item["evidence_refs"]:
            raise StratagentError("Research queries must cite and quote actual project request evidence.")
    github = [{"kind": item["kind"], "query": " ".join('"' + term + '"' for term in item["terms"]) + " archived:false fork:false is:public",
               "sort": "stars", "order": "desc"} for item in plan["github_queries"]]
    mcp = [item["term"] for item in plan["mcp_queries"]]
    outbound = [entry["query"] for entry in github] + mcp
    if len({entry["query"] for entry in github}) != len(github) or len(set(mcp)) != len(mcp):
        raise StratagentError("Duplicate research queries waste the approved budget.")
    if any(re.search(r"(?:github_pat_|gh[pousr]_|sk-|AKIA)[A-Za-z0-9_-]{12,}", query) for query in outbound):
        raise StratagentError("Research terms contain a credential-like value; remove it before preview.")
    scope = {"schema_version": 1, "workspace": str(workspace), "context_digest": context["context_digest"],
             "proposal": plan, "github_queries": github, "mcp_queries": mcp,
             "network_destinations": ["https://api.github.com", "https://registry.modelcontextprotocol.io"]}
    return {**scope, "search_approval": identity(scope), "network_executed": False,
            "warning": "Exact query text and budgets are outbound data. Review publicness and privacy before approving; validation/quotes do not prove terms are public. Approval covers research only, never installation, credentials or execution."}
