"""Bounded, explainable scope interpretation; uncertain language stays uncertain."""
import re


NEGATIVE_PREFIX = re.compile(r"\b(?:no|without|exclude|excluding|avoid|don't need|do not need|don't want|do not want|not using|no need for)\b", re.I)
NEGATIVE_SUFFIX = re.compile(r"\b(?:not needed|not required|is excluded|out of scope|istemiyorum|istemiyoruz|gerekmiyor|gerekmez|olmasın|olmayacak|kullanmayacağız|yok|hariç|olmadan|içermesin)\b", re.I)
UNCERTAIN = re.compile(r"\b(?:maybe|perhaps|optional|consider|belki|opsiyonel|isteğe bağlı|gerekir mi|do we need)\b", re.I)
DEFERRED = re.compile(r"\b(?:later|future|eventually|ileride|sonra|sonraki aşama)\b", re.I)
CLAUSES = re.compile(r"[,;!?\n]+|(?<=\.)\s+|\b(?:but|however|ama|ancak|fakat)\b", re.I)


def mentions(prompt, terms):
    result, repeated = [], {}
    position = 0
    for boundary in list(CLAUSES.finditer(prompt)) + [None]:
        end = boundary.start() if boundary else len(prompt)
        clause = prompt[position:end]
        normalized = clause.replace("’", "'")
        for term in terms:
            for occurrence in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", clause, re.I):
                before = normalized[max(0, occurrence.start() - 90):occurrence.start()]
                after = normalized[occurrence.end():occurrence.end() + 65]
                after_scope = re.split(r"\b(?:and|or|ve|veya|with|without|including|for|ile|için)\b", after, maxsplit=1, flags=re.I)[0]
                affirmative = re.search(r"\b(?:required|needed|necessary|gerekli|zorunlu)\b", after_scope, re.I)
                conjunctions = list(re.finditer(r"\b(?:and|or|ve|veya)\b", before, re.I))
                if affirmative and conjunctions:
                    before = before[conjunctions[-1].end():]
                negative = NEGATIVE_PREFIX.search(before) or NEGATIVE_SUFFIX.search(after_scope)
                double_negative = re.search(r"\bnot\s+without\b", before, re.I)
                local_context = before + " " + after_scope
                if double_negative or UNCERTAIN.search(local_context) or (NEGATIVE_SUFFIX.search(after) and not negative and not affirmative):
                    status = "uncertain"
                elif negative:
                    status = "excluded"
                elif DEFERRED.search(local_context):
                    status = "deferred"
                else:
                    status = "required"
                quote = clause[max(0, occurrence.start() - 70):min(len(clause), occurrence.end() + 130)].strip()
                key = (term, status, quote)
                if key in repeated:
                    repeated[key]["occurrences"] += 1
                else:
                    evidence = {"term": term, "status": status, "source": "prompt", "quote": quote,
                                "span": [position + occurrence.start(), position + occurrence.end()], "occurrences": 1}
                    repeated[key] = evidence
                    result.append(evidence)
        position = boundary.end() if boundary else len(prompt)
    return sorted(result, key=lambda item: (item["span"], item["term"]))


def requirement_records(prompt, definitions):
    result = []
    for name, (terms, acceptance) in definitions.items():
        evidence = mentions(prompt, terms)
        if not evidence:
            continue
        statuses = {item["status"] for item in evidence}
        status = next(iter(statuses)) if len(statuses) == 1 else "conflicting"
        result.append({"id": name, "status": status, "matched_terms": sorted({item["term"] for item in evidence}),
                       "acceptance": acceptance, "evidence": evidence,
                       "interpretation": "bounded bilingual scope rules; complex negation and intent require model/human review"})
        if name == "offline":
            testing_only = all(re.search(r"\b(?:offline|çevrimdışı)\s+(?:tests?|testing|testler\w*)\b", item["quote"], re.I) for item in evidence)
            result[-1]["scope"] = "testing" if testing_only else "project"
    return result


def coordination(prompt, domains, project):
    small = [item for item in mentions(prompt, ("small", "simple", "mvp", "prototype", "solo", "küçük", "basit", "prototip", "tek geliştirici")) if item["status"] == "required"]
    parallel = [item for item in mentions(prompt, ("parallel", "independent teams", "paralel", "bağımsız ekipler")) if item["status"] == "required"]
    work_areas = sorted(set(domains) & {"web", "api", "data", "database"})
    components = len(project["files"]) if project else 0
    focused_score = 5 + (4 if small else 0) + (3 if len(work_areas) <= 1 else 0)
    specialist_score = 4 + 2 * max(0, len(work_areas) - 1) + (2 if components > 1 else 0) + (4 if parallel else 0) - (4 if small else 0)
    alternatives = [
        {"id": "focused", "score": focused_score, "role_policy": "Five core responsibilities; no extra domain specialists",
         "reasons": ["Minimizes handoffs and coordination for a focused vertical slice."] + (["The request explicitly limits scope/team size."] if small else []),
         "tradeoffs": ["The implementer owns cross-domain integration; specialist depth may need later review."]},
        {"id": "specialist", "score": specialist_score, "role_policy": "Add only evidenced domain specialists",
         "reasons": [f"Observed active work areas: {', '.join(work_areas) or 'unspecified'}."] + (["Multiple dependency manifests suggest component boundaries, not proven independent services."] if components > 1 else []) + (["The request explicitly asks for parallel responsibilities."] if parallel else []),
         "tradeoffs": ["Extra handoffs cost coordination; separate roles are not automatically separate processes or services."]},
    ]
    selected = max(alternatives, key=lambda alternative: alternative["score"])["id"]
    return {"method": "constraint-tradeoffs-v1", "selected": selected, "alternatives": alternatives,
            "signals": {"small_scope": small, "parallel_work": parallel, "work_areas": work_areas, "manifest_count": components},
            "note": "Scores are transparent rules, not model confidence or proof of the best architecture."}
