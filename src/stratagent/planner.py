"""Deterministic bilingual MVP planning; no model or shell invocation."""
import re

from .common import StratagentError


DOMAINS = {
    "python": ("python", "fastapi", "django"),
    "web": ("web", "frontend", "react", "arayüz", "website", "dashboard"),
    "api": ("api", "backend", "sunucu", "servis"),
    "data": ("data", "veri", "csv", "analiz", "analytics"),
    "testing": ("test", "pytest", "quality", "kalite"),
    "security": ("security", "güven", "auth", "kimlik"),
    "agents": ("agent", "ajan", "asistan", "mcp", "skill"),
}


def analyze(prompt):
    if not isinstance(prompt, str) or not 3 <= len(prompt.strip()) <= 8000:
        raise StratagentError("Describe the project in 3–8000 characters.")
    prompt = prompt.strip()
    lowered = prompt.casefold()
    domains = [name for name, words in DOMAINS.items() if any(w in lowered for w in words)]
    domains = domains or ["agents"]
    terms = list(dict.fromkeys(domains + ["testing", "security"]))
    tasks = [
        {"id": "design", "agent": "architect", "title": "Define interfaces and acceptance criteria", "depends_on": [], "acceptance": ["Document scope, inputs, outputs and trust boundaries."]},
        {"id": "build", "agent": "implementer", "title": "Implement the smallest working vertical slice", "depends_on": ["design"], "acceptance": ["A local example satisfies the project request."]},
        {"id": "test", "agent": "test-reviewer", "title": "Verify behavior and failure paths", "depends_on": ["build"], "acceptance": ["Check successful, invalid-input and offline cases."]},
        {"id": "security", "agent": "security-reviewer", "title": "Review trust boundaries, dependencies and licenses", "depends_on": ["design"], "acceptance": ["Report concrete risks with evidence and remediation."]},
        {"id": "release", "agent": "maintainer", "title": "Integrate reviewed changes and document local use", "depends_on": ["test", "security"], "acceptance": ["Tests pass and README reproduces the demo."]},
    ]
    return {"prompt": prompt, "method": "deterministic-keywords-v1", "domains": domains,
            "search_terms": terms, "tasks": tasks,
            "assumptions": ["Tasks are delegated as configuration; no coding agent is launched.",
                            "Heuristic analysis is not an LLM interpretation; review the plan."]}


def words(value):
    return set(re.findall(r"[\w-]{2,}", value.casefold()))
