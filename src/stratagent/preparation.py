"""Idea-to-review orchestration; caches evidence but never installs or executes it."""
import hmac
import time

from .common import StratagentError
from .hosts import DEFAULT_TARGETS, platforms
from .planner import analyze
from .sessions import record as record_session

MCP_QUERIES = {"web": "playwright", "api": "openapi", "database": "postgres", "data": "data", "python": "python", "agents": "mcp"}


def prepare(service, prompt, targets, existing, limit, repo_limit, mcp_limit, offline, research_plan=None, approve_search=None):
    for name, value, maximum in (("Candidate", limit, 20), ("Repository", repo_limit, 20), ("MCP result", mcp_limit, 20)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise StratagentError(f"{name} limit must be between 1 and {maximum}.")
    if type(offline) is not bool:
        raise StratagentError("Offline preparation must be true or false.")
    normalized_prompt = analyze(prompt)["prompt"]
    selected_targets = platforms(targets if targets is not None else (existing["platforms"] if existing else list(DEFAULT_TARGETS)))
    if existing:
        if normalized_prompt != existing["analysis"]["prompt"] or selected_targets != platforms(existing["platforms"]):
            raise StratagentError("Existing workspace has a different request or targets. Separately review stratagent revise first; prepare never resets state.")
    research_context = service.research_context(normalized_prompt, selected_targets)
    started_at = int(time.time())
    search_preview = None
    if research_plan is not None:
        if offline:
            raise StratagentError("A runtime network research plan cannot be combined with --offline.")
        search_preview = service.preview_research(research_plan, normalized_prompt, selected_targets)
        if not isinstance(approve_search, str) or not hmac.compare_digest(search_preview["search_approval"], approve_search):
            raise StratagentError("Outbound search approval must match the exact research preview; no network or initialization performed.")
        budgets = research_plan["budgets"]
        limit, repo_limit, mcp_limit = budgets["definitions"], budgets["repositories"], budgets["mcp_results"]
    elif approve_search is not None:
        raise StratagentError("Search approval requires a research plan.")
    if not existing:
        service.init(normalized_prompt, selected_targets)
    analysis = service.analysis()
    github, registry, errors = None, [], []
    project_offline = any(item["id"] == "offline" and item["status"] == "required" and item.get("scope", "project") == "project" for item in analysis["requirements"])
    if not offline:
        if search_preview is None or search_preview["github_queries"]:
            try:
                github = service.discover(limit=limit, repo_limit=repo_limit, query_plan=search_preview["github_queries"] if search_preview else None)
                errors.extend({"stage": "github", **error} for error in github["errors"])
            except StratagentError as error:
                errors.append({"stage": "github", "error": str(error)})
        queries = [] if project_offline else (search_preview["mcp_queries"] if search_preview else [MCP_QUERIES[domain] for domain in ("database", "web", "api", "data", "python", "agents") if domain in analysis["active_domains"]][:3])
        if not queries and not project_offline and search_preview is None:
            queries = ["documentation"]
        for query in queries:
            try:
                result = service.discover_mcp(query, mcp_limit)
                registry.append(result)
                errors.extend({"stage": "mcp-registry", "query": query, **error} for error in result["errors"])
            except StratagentError as error:
                errors.append({"stage": "mcp-registry", "query": query, "error": str(error)})
    session = record_session(service, research_context, github, registry, errors, offline, approve_search, started_at)
    request = service.decision_request(session["id"])
    blueprint = service.blueprint(run_id=session["id"])
    context = request["context"]
    return {"schema_version": 1, "status": "review-required", "environment_applied": False, "offline": offline,
            "research_run": session,
            "discovery_skips": (["Network discovery disabled by --offline."] if offline else (["Registry discovery omitted for explicit project-wide offline scope."] if project_offline else [])),
            "github_discovery": github, "mcp_discovery": registry, "errors": errors,
            "available_resources": {"skills_or_roles": len(context["skills"]), "eligible_skills_or_roles": sum(item["eligible"] for item in context["skills"]),
                                    "mcp_servers": len(context["mcps"]), "eligible_mcp_servers": sum(item["eligible"] for item in context["mcps"])},
            "blueprint": blueprint, "decision_request": request,
            "unassisted_roles": [role["id"] for role in blueprint["source"]["blueprint"]["roles"] if not role["binding"]["skills"] and not role["binding"]["mcps"]],
            "note": "Preparation initializes project state and caches bounded research. It does not grant trust, install skills, launch agents or enable MCP. Empty resources are visible, not invented. Review the source findings and model/rule decision, resolve blockers, then explicitly approve the current blueprint. Local rules are a fallback, not semantic model judgment."}
