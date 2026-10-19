"""Grounded architectural decisions and resource bindings, without IO or authority."""
import copy
import json
import re

from .common import StratagentError, canonical, identity
from .planner import DOMAINS, REQUIREMENTS, SPECIALISTS, matches, waves, words

CAPABILITIES = {
    "browser": {"browser", "playwright", "puppeteer", "selenium", "frontend"},
    "database": {"database", "postgres", "postgresql", "sqlite", "sql", "prisma"},
    "data": {"data", "csv", "analytics", "pandas", "analysis"},
    "documentation": {"documentation", "docs", "context7", "reference"},
    "repository": {"git", "github", "gitlab", "repository", "pull", "commit"},
    "security": {"security", "audit", "privacy", "vulnerability"},
}
ROLE_NEEDS = {
    "design": ("documentation",), "frontend": ("browser", "documentation"),
    "api": ("documentation", "database"), "database": ("database",),
    "data": ("data", "database"), "build": ("documentation",),
    "test": ("browser", "data"), "security": ("security",), "release": ("repository",),
}
DECISION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["schema_version", "context_digest", "strategy", "reason", "evidence_refs", "bindings"],
    "properties": {
        "schema_version": {"const": 1}, "context_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "strategy": {"enum": ["focused", "specialist"]}, "reason": {"type": "string", "minLength": 3, "maxLength": 2000},
        "provider_label": {"type": "string", "minLength": 1, "maxLength": 100},
        "evidence_refs": {"type": "array", "minItems": 1, "maxItems": 60, "items": {"type": "string"}},
        "domain_inferences": {"type": "array", "maxItems": 10, "items": {
            "type": "object", "additionalProperties": False, "required": ["domain", "reason", "evidence_refs", "quote"],
            "properties": {"domain": {"enum": list(DOMAINS)}, "reason": {"type": "string", "minLength": 3, "maxLength": 2000},
                           "quote": {"type": "string", "minLength": 3, "maxLength": 500},
                           "evidence_refs": {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "string"}}}}},
        "omitted_roles": {"type": "array", "maxItems": 4, "uniqueItems": True, "items": {"type": "string"}},
        "requirements": {"type": "array", "maxItems": 30, "items": {
            "type": "object", "additionalProperties": False, "required": ["id", "status", "statement", "evidence_refs", "quote"],
            "properties": {"id": {"type": "string", "pattern": "^[a-z][a-z0-9-]{0,63}$"},
                           "status": {"enum": ["required", "excluded", "deferred", "uncertain"]},
                           "scope": {"enum": ["project", "testing"]},
                           "statement": {"type": "string", "minLength": 3, "maxLength": 2000},
                           "quote": {"type": "string", "minLength": 3, "maxLength": 500},
                           "evidence_refs": {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "string"}}}}},
        "bindings": {"type": "array", "maxItems": 9, "items": {
            "type": "object", "additionalProperties": False, "required": ["task_id", "skills", "mcps", "reason"],
            "properties": {"task_id": {"type": "string"}, "reason": {"type": "string", "minLength": 3, "maxLength": 2000},
                           "skills": {"type": "array", "maxItems": 3, "uniqueItems": True, "items": {"type": "string"}},
                           "mcps": {"type": "array", "maxItems": 3, "items": {
                               "type": "object", "additionalProperties": False, "required": ["candidate_id", "option"],
                               "properties": {"candidate_id": {"type": "string"}, "option": {"type": "integer", "minimum": 0, "maximum": 39}}}}}}},
    },
}


def validate_shape(value, schema):
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise StratagentError("Decision schema version must be 1.")
    if "enum" in schema and value not in schema["enum"]:
        raise StratagentError("Decision contains an unsupported choice.")
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict) or set(value) - schema["properties"].keys() or set(schema.get("required", [])) - value.keys():
            raise StratagentError("Decision object has missing or unsupported fields.")
        for name, item in value.items():
            validate_shape(item, schema["properties"][name])
    elif kind == "array":
        if not isinstance(value, list) or not schema.get("minItems", 0) <= len(value) <= schema["maxItems"]:
            raise StratagentError("Decision array exceeds the supported bounds.")
        if schema.get("uniqueItems") and len({identity(item) for item in value}) != len(value):
            raise StratagentError("Decision array contains duplicate values.")
        for item in value:
            validate_shape(item, schema["items"])
    elif kind == "string":
        if (not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 200)
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
                or (schema.get("pattern") and not re.fullmatch(schema["pattern"], value))):
            raise StratagentError("Decision text is invalid or exceeds its bounds.")
    elif kind == "integer":
        if type(value) is not int or not schema["minimum"] <= value <= schema["maximum"]:
            raise StratagentError("Decision transport option is invalid.")


def decision_context(analysis, skills, mcps, targets):
    evidence = [{"id": "request", "source": "user-request", "text": analysis["prompt"]}]
    evidence.extend({"id": "domain:" + entry["domain"], "source": "domain-evidence", "data": entry["evidence"]} for entry in analysis["domain_evidence"])
    evidence.extend({"id": "requirement:" + entry["id"], "source": "scope-evidence", "data": entry} for entry in analysis["requirements"])
    evidence.extend({"id": "manifest:" + entry["path"], "source": "dependency-manifest", "data": entry} for entry in (analysis.get("project") or {}).get("files", []))
    evidence.extend({"id": "skill:" + entry["id"], "source": "untrusted-reviewed-metadata", "review_digest": entry["review_digest"]} for entry in skills)
    evidence.extend({"id": "mcp:" + entry["id"], "source": "untrusted-registry-metadata", "review_digest": entry["review_digest"]} for entry in mcps)
    context = {"schema_version": 1, "analysis": analysis, "skills": sorted(skills, key=lambda entry: entry["id"]),
               "mcps": sorted(mcps, key=lambda entry: entry["id"]), "targets": targets, "evidence": evidence}
    return {**context, "context_digest": identity(context)}


def selected_analysis(analysis, strategy, omitted=()):
    result = copy.deepcopy(analysis)
    core = [task for task in result["tasks"] if task["id"] not in {"frontend", "api", "data", "database"}]
    specialists = [task for task in result["role_options"] if task["id"] not in omitted] if strategy == "specialist" else []
    next(task for task in core if task["id"] == "build")["depends_on"] = [task["id"] for task in specialists] or ["design"]
    result["tasks"] = [core[0], *specialists, *core[1:]]
    for task in result["tasks"]:
        task.setdefault("rationale", f"The {task['id']} work area has project evidence and is retained by the specialist decision.")
    result["coordination"]["selected"] = strategy
    result["architecture"]["parallel_waves"] = waves(result["tasks"])
    return result


def infer_capabilities(candidate):
    tokens = words((candidate["name"] + " " + candidate["description"]).replace("-", " ").replace("/", " "))
    return {name: sorted(tokens & terms) for name, terms in CAPABILITIES.items() if tokens & terms}


def offline_required(analysis, task_id=None):
    return any(item["id"] == "offline" and item["status"] == "required" and (item.get("scope", "project") != "testing" or task_id == "test")
               for item in analysis["requirements"])


def scope_conflicts(candidate, analysis):
    name = candidate["name"].replace("-", " ").replace("/", " ")
    return [item["id"] for item in analysis["requirements"]
            if item["status"] in ("excluded", "deferred") and item["id"] in REQUIREMENTS
            and any(matches(name, term) for term in REQUIREMENTS[item["id"]][0])]


def proposed_bindings(analysis, skills, mcps):
    proposals = []
    active = set(analysis["active_domains"])
    for task in analysis["tasks"]:
        terms = set().union(*(words(term.replace("-", " ")) for term in task["search_terms"]))
        skill_matches = []
        for candidate in skills:
            overlap = terms & words((candidate["name"] + " " + candidate["description"]).replace("-", " "))
            if candidate["eligible"] and overlap and not scope_conflicts(candidate, analysis):
                skill_matches.append({"candidate_id": candidate["id"], "score": len(overlap) * 10 + candidate["ranking"]["score"] / 10,
                                      "matched_terms": sorted(overlap)})
        skill_matches.sort(key=lambda match: (-match["score"], match["candidate_id"]))
        needs = list(ROLE_NEEDS[task["id"]])
        if "web" not in active:
            needs = [need for need in needs if need != "browser"]
        if "data" not in active:
            needs = [need for need in needs if need != "data"]
        if "database" not in active:
            needs = [need for need in needs if need != "database"]
        mcp_matches = []
        for candidate in mcps:
            capabilities = infer_capabilities(candidate)
            overlap = sorted(set(needs) & capabilities.keys())
            if candidate["eligible"] and overlap and not scope_conflicts(candidate, analysis) and not offline_required(analysis, task["id"]):
                mcp_matches.append({"candidate_id": candidate["id"], "option": 0, "matched_capabilities": overlap,
                                    "metadata_evidence": {need: capabilities[need] for need in overlap}, "score": len(overlap)})
        mcp_matches.sort(key=lambda match: (-match["score"], match["candidate_id"]))
        proposals.append({"task_id": task["id"], "agent": task["agent"], "needs": needs,
                          "skill_alternatives": skill_matches[:3], "mcp_alternatives": mcp_matches[:3],
                          "skills": [match["candidate_id"] for match in skill_matches[:1]],
                          "mcps": [{"candidate_id": match["candidate_id"], "option": match["option"]} for match in mcp_matches[:1]],
                          "reason": task["rationale"], "evidence_refs": ["request"],
                          "limitations": ["Metadata matches are suggestions, not verified tool capabilities or proof of architecture quality."]})
    return proposals


def interpret(context, decisions=None):
    analysis = context["analysis"]
    skills = {entry["id"]: entry for entry in context["skills"]}
    mcps = {entry["id"]: entry for entry in context["mcps"]}
    provenance = {"engine": "local-constraint-rules", "review_required": True}
    if decisions is not None:
        if len(canonical(decisions)) > 64 * 1024:
            raise StratagentError("Decision proposal exceeds 64 KiB.")
        validate_shape(decisions, DECISION_SCHEMA)
        if decisions["context_digest"] != context["context_digest"]:
            raise StratagentError("Decision context is stale; obtain a new decision-request and review again.")
        references = {entry["id"] for entry in context["evidence"]}
        groups = [decisions["evidence_refs"], *(item["evidence_refs"] for item in decisions.get("requirements", [])),
                  *(item["evidence_refs"] for item in decisions.get("domain_inferences", []))]
        if any(set(group) - references for group in groups):
            raise StratagentError("Decision references unknown evidence.")
        analysis = copy.deepcopy(analysis)
        inferred = set()
        for inference in decisions.get("domain_inferences", []):
            domain = inference["domain"]
            project_refs = [entry for entry in context["evidence"] if entry["id"] in inference["evidence_refs"] and entry["source"] not in ("untrusted-reviewed-metadata", "untrusted-registry-metadata")]
            if not any(inference["quote"] in (entry.get("text", "") or json.dumps(entry.get("data", {}), ensure_ascii=False)) for entry in project_refs):
                raise StratagentError("Domain inference must quote actual user/project evidence, not available tool metadata.")
            if domain in inferred or domain in {item["id"] for item in analysis["domain_exclusions"]}:
                raise StratagentError("Decision repeats a domain or contradicts an explicit domain exclusion.")
            inferred.add(domain)
            if domain not in analysis["active_domains"]:
                analysis["active_domains"].append(domain)
                if domain not in analysis["domains"]:
                    analysis["domains"].append(domain)
                analysis["search_terms"].append(domain)
                analysis["domain_evidence"].append({"domain": domain, "evidence": [{"source": "external-proposal", **inference}]})
                if domain in SPECIALISTS:
                    task_id, agent, title, acceptance = SPECIALISTS[domain]
                    analysis["role_options"].append({"id": task_id, "agent": agent, "title": title, "depends_on": ["design"],
                                                     "acceptance": [acceptance], "search_terms": [domain, *DOMAINS[domain][:4]], "mode": "read-only"})
        omitted = decisions.get("omitted_roles", [])
        if len(set(omitted)) != len(omitted) or set(omitted) - {task["id"] for task in analysis["role_options"]}:
            raise StratagentError("Only evidenced optional specialist roles may be omitted; core review responsibilities remain required.")
        analysis = selected_analysis(analysis, decisions["strategy"], omitted)
        requirements = {item["id"]: item for item in analysis["requirements"]}
        seen = set()
        for requirement in decisions.get("requirements", []):
            if requirement["quote"] not in analysis["prompt"] or not any(reference == "request" or reference.startswith("requirement:") for reference in requirement["evidence_refs"]):
                raise StratagentError("A decision requirement must quote the actual user request; an evidence ID alone does not ground a new requirement.")
            if requirement["id"] in seen:
                raise StratagentError("Duplicate decision requirement ID.")
            seen.add(requirement["id"])
            previous = requirements.get(requirement["id"])
            if previous and previous["status"] in ("required", "excluded") and previous["status"] != requirement["status"]:
                raise StratagentError("Decision contradicts an explicit requirement; revise the project request rather than overriding its scope.")
            if previous and previous["id"] == "offline" and previous["status"] == "required" and previous.get("scope", "project") == "project" and requirement.get("scope", "project") != "project":
                raise StratagentError("Decision cannot weaken an explicit project-wide offline scope.")
            requirements[requirement["id"]] = {**(previous or {}), **requirement, "interpretation": "external proposal; semantic correctness requires human review"}
        analysis["requirements"] = list(requirements.values())
        test_task = next(task for task in analysis["tasks"] if task["id"] == "test")
        for requirement in decisions.get("requirements", []):
            if requirement["status"] == "required":
                criterion = f"Validate reviewed requirement {requirement['id']} against its evidence in .stratagent/blueprint.json."
                test_task["acceptance"].append(criterion)
        analysis["open_questions"] = [question for question in analysis["open_questions"] if not question.startswith("Resolve ")]
        analysis["open_questions"].extend(f"Resolve {item['id']} scope: {item['status']}." for item in analysis["requirements"] if item["status"] in ("conflicting", "uncertain", "deferred"))
        bindings = decisions["bindings"]
        task_ids = {task["id"] for task in analysis["tasks"]}
        if {item["task_id"] for item in bindings} != task_ids or len(bindings) != len(task_ids):
            raise StratagentError("Decision must bind every selected task exactly once, with explicit empty arrays when no resource is needed.")
        defaults = {item["task_id"]: item for item in proposed_bindings(analysis, list(skills.values()), list(mcps.values()))}
        proposals = [{**defaults[item["task_id"]], **item, "evidence_refs": decisions["evidence_refs"]} for item in bindings]
        provenance = {"engine": "external-structured-proposal", "provider_label": decisions.get("provider_label", "unspecified-unverified"),
                      "proposal_sha256": identity(decisions), "review_required": True,
                      "note": "Provider label and rationale are untrusted claims, not authenticated model provenance."}
        reason = decisions["reason"]
    else:
        analysis = selected_analysis(analysis, analysis["coordination"]["selected"])
        proposals = proposed_bindings(analysis, list(skills.values()), list(mcps.values()))
        reason = next(item for item in analysis["coordination"]["alternatives"] if item["id"] == analysis["coordination"]["selected"])["reasons"][0]
    for proposal in proposals:
        for candidate_id in proposal["skills"]:
            if candidate_id not in skills or not skills[candidate_id]["eligible"] or scope_conflicts(skills[candidate_id], analysis):
                raise StratagentError("Decision selects an unknown or policy-blocked skill.")
            if decisions is not None and "skill:" + candidate_id not in decisions["evidence_refs"]:
                raise StratagentError("Decision must cite the reviewed evidence for every selected skill.")
        selected_mcps = set()
        for selection in proposal["mcps"]:
            candidate_id, option = selection["candidate_id"], selection["option"]
            if candidate_id not in mcps or not mcps[candidate_id]["eligible"] or scope_conflicts(mcps[candidate_id], analysis) or not 0 <= option < len(mcps[candidate_id]["options"]):
                raise StratagentError("Decision selects an unknown, blocked or unsupported MCP transport.")
            if (candidate_id, option) in selected_mcps:
                raise StratagentError("Duplicate MCP selection within a role.")
            if decisions is not None and "mcp:" + candidate_id not in decisions["evidence_refs"]:
                raise StratagentError("Decision must cite the reviewed evidence for every selected MCP server.")
            selected_mcps.add((candidate_id, option))
            if offline_required(analysis, proposal["task_id"]):
                raise StratagentError("An offline requirement cannot select unverified Registry MCP services; offline availability needs a separately reviewed workflow.")
    blockers = [{"rule": "unresolved-scope", "requirement_id": item["id"], "detail": "Resolve contradictory or uncertain scope before applying the blueprint."}
                for item in analysis["requirements"] if item["status"] in ("conflicting", "uncertain")]
    roles = []
    for task in analysis["tasks"]:
        binding = next(item for item in proposals if item["task_id"] == task["id"])
        permissions = [{"kind": "workspace-read", "scope": "project evidence and approved resources", "granted": False}]
        if task["mode"] == "manual-approval":
            permissions.append({"kind": "workspace-write", "scope": "manually delegated implementation/integration", "granted": False})
        for selection in binding["mcps"]:
            transport = mcps[selection["candidate_id"]]["options"][selection["option"]]
            permissions.append({"kind": "network" if transport["type"] == "http" else "package-execution",
                                "scope": transport.get("url", transport.get("package")), "granted": False,
                                "note": "Proposal only; source/tool permissions and activation require human review."})
        roles.append({**task, "binding": binding, "permissions": permissions})
    return {"schema_version": 1, "context_digest": context["context_digest"], "analysis": analysis,
            "decision": {"strategy": analysis["coordination"]["selected"], "reason": reason,
                         "alternatives": analysis["coordination"]["alternatives"], "provenance": provenance},
            "roles": roles, "blockers": blockers, "open_questions": analysis["open_questions"],
            "omitted_roles": [{"task_id": task["id"], "reason": "Extra specialist omitted by the selected coordination strategy or explicit reviewed proposal."}
                              for task in analysis["role_options"] if task["id"] not in {role["id"] for role in roles}],
            "execution": "manual-delegation-only", "approval_required": True,
            "limitations": ["Rule-based fallback is not semantic model reasoning; an external structured proposal can supply model/human judgment.",
                            "Evidence IDs bind inputs but do not prove that a model's interpretation is correct.",
                            "MCP capabilities are inferred from metadata, not verified tool manifests; settings stay inert."]}
