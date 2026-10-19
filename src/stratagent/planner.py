"""Explainable bilingual requirements and role planning without model execution."""
import re

from .common import StratagentError
from .intent import coordination, mentions, requirement_records


DOMAINS = {
    "python": ("python", "fastapi", "django", "flask"),
    "web": ("web", "frontend", "react", "nextjs", "next.js", "arayüz", "website", "dashboard", "vue"),
    "api": ("api", "backend", "sunucu", "servis", "fastapi", "django", "express"),
    "data": ("data", "veri", "csv", "analiz", "analizi", "analytics", "pandas"),
    "testing": ("test", "tests", "testing", "pytest", "quality", "kalite", "playwright"),
    "security": ("security", "secure", "güven", "güvenlik", "güvenliği", "auth", "authentication", "kimlik"),
    "agents": ("agent", "agents", "ajan", "asistan", "mcp", "skill", "skills"),
    "database": ("database", "postgres", "postgresql", "sqlite", "sql", "veritabanı", "prisma"),
    "rust": ("rust", "cargo", "axum"),
    "go": ("golang", "go"),
}
REQUIREMENTS = {
    "authentication": (("auth", "authentication", "login", "oauth", "kimlik", "giriş"), "Test identity, authorization and rejected access."),
    "privacy": (("privacy", "pii", "gdpr", "kvkk", "personal data", "kişisel veri"), "Minimize personal data, redact logs and define retention."),
    "offline": (("offline", "çevrimdışı", "local only", "yerel"), "Demonstrate the core workflow without network access."),
    "performance": (("performance", "latency", "scale", "performans", "ölçek"), "Define measurable latency and load acceptance thresholds."),
    "payments": (("payment", "payments", "stripe", "ödeme"), "Test payment callbacks, duplicate events and secret handling in a sandbox."),
    "accessibility": (("accessibility", "accessible", "a11y", "erişilebilir"), "Verify keyboard navigation and accessible names."),
}
SPECIALISTS = {
    "web": ("frontend", "frontend-engineer", "Plan the user interface and integration contract", "Define UI states, accessible interaction and API contracts."),
    "api": ("api", "api-engineer", "Plan service interfaces and failure handling", "Define validated requests, error responses and service boundaries."),
    "data": ("data", "data-engineer", "Plan data validation and transformation", "Define schemas, missing-data handling and reproducible fixtures."),
    "database": ("database", "database-engineer", "Plan persistence and migrations", "Define schema migrations, rollback and least-privilege access."),
}


def matches(text, term):
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE) is not None


def waves(tasks):
    pending = {task["id"]: set(task["depends_on"]) for task in tasks}
    if len(pending) != len(tasks) or any(dependencies - pending.keys() for dependencies in pending.values()):
        raise StratagentError("Task graph has duplicate IDs or unknown dependencies.")
    completed, result = set(), []
    while pending:
        ready = [task_id for task_id, dependencies in pending.items() if dependencies <= completed]
        if not ready:
            raise StratagentError("Task graph contains a dependency cycle.")
        result.append(ready)
        completed.update(ready)
        for task_id in ready:
            del pending[task_id]
    return result


def analyze(prompt, project=None):
    if not isinstance(prompt, str) or not 3 <= len(prompt.strip()) <= 8000:
        raise StratagentError("Describe the project in 3–8000 characters.")
    prompt = prompt.strip()
    if any((ord(char) < 32 and char not in "\n\t\r") or ord(char) == 127 for char in prompt):
        raise StratagentError("Project request contains control characters.")
    signals = project["signals"] if project else []
    evidence, domain_exclusions = [], []
    for domain, keywords in DOMAINS.items():
        occurrences = mentions(prompt, keywords)
        found = [item for item in occurrences if item["status"] == "required"]
        if occurrences and all(item["status"] == "excluded" for item in occurrences):
            domain_exclusions.append({"id": domain, "evidence": occurrences})
        found.extend({"source": signal["source"], "term": signal["evidence"]}
                     for signal in signals if signal["term"] == domain)
        if found:
            evidence.append({"domain": domain, "evidence": found})
    domains = [entry["domain"] for entry in evidence]
    active_domains = [domain for domain in domains if domain not in {entry["id"] for entry in domain_exclusions}]
    requirements = requirement_records(prompt, REQUIREMENTS)
    required = [item for item in requirements if item["status"] == "required"]
    decision = coordination(prompt, active_domains, project)
    terms = list(dict.fromkeys(active_domains + [signal["term"] for signal in signals if signal["term"] not in {entry["id"] for entry in domain_exclusions}] + ["testing", "security"]))
    tasks = [
        {"id": "design", "agent": "architect", "title": "Define interfaces and acceptance criteria", "depends_on": [], "acceptance": ["Document scope, inputs, outputs and trust boundaries."]},
        {"id": "build", "agent": "implementer", "title": "Implement the smallest working vertical slice", "depends_on": ["design"], "acceptance": ["A local example satisfies the project request."]},
        {"id": "test", "agent": "test-reviewer", "title": "Verify behavior and failure paths", "depends_on": ["build"], "acceptance": ["Check successful, invalid-input and offline cases."]},
        {"id": "security", "agent": "security-reviewer", "title": "Review implemented trust boundaries, dependencies and licenses", "depends_on": ["build"], "acceptance": ["Report concrete risks with evidence and remediation."]},
        {"id": "release", "agent": "maintainer", "title": "Integrate reviewed changes and document local use", "depends_on": ["test", "security"], "acceptance": ["Tests pass and README reproduces the demo."]},
    ]
    role_terms = {"design": ["architect", "architecture", "design", "interfaces"],
                  "build": active_domains + ["implement", "implementation", "developer"],
                  "test": ["test", "testing", "tests", "qa", "regression"],
                  "security": ["security", "secure", "audit", "privacy", "license"],
                  "release": ["documentation", "release", "maintainer", "readme"]}
    for task in tasks:
        task["search_terms"] = role_terms[task["id"]]
        task["mode"] = "manual-approval" if task["id"] in ("build", "release") else "read-only"
    specialist_tasks = []
    for domain, (task_id, agent, title, acceptance) in SPECIALISTS.items():
        if domain in active_domains:
            specialist_tasks.append({"id": task_id, "agent": agent, "title": title, "depends_on": ["design"],
                                     "acceptance": [acceptance], "search_terms": [domain, *DOMAINS[domain][:4]], "mode": "read-only"})
    selected_specialists = specialist_tasks if decision["selected"] == "specialist" else []
    if selected_specialists:
        tasks[1]["depends_on"] = [task["id"] for task in selected_specialists]
    tasks[2]["acceptance"].extend(item["acceptance"] for item in required)
    tasks[3]["acceptance"].extend(item["acceptance"] for item in required if item["id"] in ("privacy", "authentication", "payments"))
    tasks = [tasks[0], *selected_specialists, *tasks[1:]]
    for task in tasks:
        task["rationale"] = (f"The active {task['id']} work area needs a specialist interface review under the selected strategy."
                             if task["id"] in {item["id"] for item in specialist_tasks}
                             else "Core responsibility for explicit scope, implementation, independent verification or release review; no process is launched.")
    questions = []
    if not domains:
        questions.append("Which language, framework and primary workflow should this project use?")
    if any(item["id"] in ("authentication", "privacy", "payments") for item in required):
        questions.append("What data, user roles and credential scopes are permitted?")
    if "database" in domains:
        questions.append("Which database and migration/backup requirements are in scope?")
    questions.extend(f"Resolve {item['id']} scope: {item['status']}." for item in requirements if item["status"] in ("conflicting", "uncertain", "deferred"))
    return {"prompt": prompt, "method": "constraint-evidence-v3", "domains": domains, "active_domains": active_domains,
            "domain_evidence": evidence, "domain_exclusions": domain_exclusions, "requirements": requirements, "search_terms": terms, "tasks": tasks,
            "role_options": specialist_tasks, "coordination": decision,
            "architecture": {"coordinator": "architect", "execution": "manual-delegation-only", "parallel_waves": waves(tasks),
                             "handoff": "Report artifacts, evidence, unresolved risks and acceptance results to the coordinator.",
                             "write_policy": "Manually approve implementer/maintainer work; serialize overlapping writes."},
            "open_questions": questions, "project": project,
            "assumptions": ["No agent is launched. Adapter capabilities determine native role definitions or portable skills.",
                            "Deterministic evidence matching is not semantic interpretation; negation and ambiguous scope require review.",
                            "Dependencies indicate context, not permission to run scripts or install content."]}


def words(value):
    return set(re.findall(r"[\w-]{2,}", value.casefold()))
