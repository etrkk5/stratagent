"""Public search vocabulary and bounded, diversity-preserving repository selection."""
from .common import GitHubLimitError, StratagentError, repository

PUBLIC_TERMS = {"python", "web", "frontend", "react", "nextjs", "vue", "typescript", "api", "backend",
                "node", "fastapi", "django", "flask", "data", "csv", "analytics", "pandas", "database",
                "postgresql", "sqlite", "sql", "rust", "go", "golang", "security", "testing", "playwright"}


def search_queries(terms):
    if not isinstance(terms, (list, tuple)) or len(terms) > 100 or not all(isinstance(term, str) for term in terms):
        raise StratagentError("Discovery requires a bounded list of public project terms.")
    domains = list(dict.fromkeys(term for term in terms if term in PUBLIC_TERMS and term not in ("testing", "security")))[:2]
    queries = [("skills", '"agent skills"'), ("subagents", "subagents"), ("mcp", '"mcp server"')]
    for domain in domains:
        queries.extend((("skills", domain + " skill"), ("subagents", domain + " agent")))
    if domains:
        queries.append(("mcp", domains[0] + " mcp"))
    return [{"kind": kind, "query": query + " archived:false fork:false", "sort": "stars", "order": "desc"}
            for kind, query in queries]


def survey(client, terms, repo_limit, queries=None):
    if type(repo_limit) is not int or not 1 <= repo_limit <= 20:
        raise StratagentError("Repository inspection limit must be between 1 and 20.")
    specifications = search_queries(terms) if queries is None else queries
    if (not isinstance(specifications, list) or not 1 <= len(specifications) <= 8 or any(
            not isinstance(item, dict) or set(item) != {"kind", "query", "sort", "order"}
            or item["kind"] not in ("skills", "subagents", "mcp") or item["sort"] != "stars" or item["order"] != "desc"
            or not isinstance(item["query"], str) or not 1 <= len(item["query"]) <= 500
            or any(ord(char) < 32 or ord(char) == 127 for char in item["query"]) for item in specifications)):
        raise StratagentError("Invalid bounded research query specifications.")
    origin = "public-vocabulary-fallback" if queries is None else "reviewed-runtime-plan"
    queries, candidates, pools, errors = [], {}, [], []
    stopped = False
    for specification in specifications:
        entry = {**specification, "page": 1, "per_page": 10}
        queries.append(entry)
        try:
            result = client.get("/search/repositories", {"q": entry["query"], "sort": "stars", "order": "desc", "per_page": 10, "page": 1})
            if not isinstance(result, dict):
                raise StratagentError("Invalid GitHub repository search response.")
            items = result.get("items")
            if not isinstance(items, list) or len(items) > 100:
                raise StratagentError("Invalid GitHub repository search results.")
            entry.update({"returned": len(items[:10]), "incomplete_results": result.get("incomplete_results") is True,
                          "total_count": result.get("total_count") if type(result.get("total_count")) is int else None})
            names = []
            for item in items[:10]:
                try:
                    name = repository(item["full_name"])
                    stars = item.get("stargazers_count", 0)
                    if type(stars) is not int or not 0 <= stars <= 10_000_000:
                        raise ValueError("Invalid popularity metadata")
                    if any(type(item[field]) is not bool for field in ("private", "archived", "disabled", "fork") if field in item):
                        raise ValueError("Invalid repository metadata")
                    if any(item.get(field, False) for field in ("private", "archived", "disabled", "fork")):
                        continue
                except (StratagentError, KeyError, TypeError, ValueError):
                    errors.append({"repo": "repository-search", "query": entry["query"], "error": "Invalid repository metadata was skipped."})
                    continue
                record = candidates.setdefault(name, {"repo": name, "stars": stars, "queries": [], "kinds": []})
                record["stars"] = max(stars, record["stars"])
                if entry["query"] not in record["queries"]:
                    record["queries"].append(entry["query"])
                if entry["kind"] not in record["kinds"]:
                    record["kinds"].append(entry["kind"])
                if name not in names:
                    names.append(name)
            pools.append(sorted(names, key=lambda name: (-candidates[name]["stars"], name)))
        except StratagentError as error:
            entry["error"] = str(error)
            errors.append({"repo": "repository-search", "query": entry["query"], "error": str(error)})
            if isinstance(error, GitHubLimitError):
                stopped = True
                break
    selected = []
    for rank in range(10):
        for pool in pools:
            if rank < len(pool) and pool[rank] not in selected and len(selected) < repo_limit:
                selected.append(pool[rank])
    return {"queries": queries, "repositories": sorted(candidates.values(), key=lambda item: (-item["stars"], item["repo"])),
            "query_origin": origin,
            "selected_repositories": selected, "errors": errors, "stopped_early": stopped,
            "limits": {"queries": 8, "results_per_query": 10, "repositories_to_inspect": repo_limit},
            "selection": "Round-robin across star-sorted query results preserves skill, agent and MCP discovery diversity.",
            "note": "Public metadata is a discovery signal, not source review or a safety endorsement. Search is bounded and not exhaustive; queries originate from the disclosed public vocabulary or a separately approved runtime plan."}
