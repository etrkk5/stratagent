"""Conservative, non-fetching review of explicit documentation references."""
import html
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from .common import StratagentError, digest, safe_path

INLINE = re.compile(r"!?\[[^\]\n]{0,300}\]\([ \t]*(<[^>\n]{1,2000}>|[^\s()]{1,2000})(?:[ \t]+(?:\"[^\"\n)]{0,300}\"|'[^'\n)]{0,300}'))?[ \t]*\)")
INLINE_START = re.compile(r"!?\[[^\]\n]{0,300}\]\(")
DEFINITION = re.compile(r"^ {0,3}\[([^\]\n]{1,300})\]:\s*(<[^>\n]{1,2000}>|\S{1,2000})", re.M)
INDIRECT = re.compile(r"!?\[([^\]\n]{1,300})\]\[([^\]\n]{0,300})\]")
PATH_LITERAL = re.compile(r"(?<![\w/])(?:scripts|references|assets)/(?:[^\s`\[\]<>\"'()]{1,500})")
HTML_LINK = re.compile(r"\b(?:href|src)\s*=\s*([\"'])([^\n]{1,2000}?)\1", re.I)


def review_references(files, entry, kind, notice_names):
    root = PurePosixPath(entry).parent
    records, findings, seen = [], [], set()
    observations = 0

    def budget():
        nonlocal observations
        observations += 1
        if observations > 512:
            raise StratagentError("Reference review exceeds 512 parser observations.")

    def record(path, target, offset, text):
        target = html.unescape(target.removeprefix("<").removesuffix(">"))
        key = (path, target)
        if key in seen:
            return
        seen.add(key)
        if len(seen) > 256:
            raise StratagentError("Reference review exceeds 256 distinct file/target pairs.")
        item = {"path": path, "target": target, "line": text[:offset].count("\n") + 1}
        try:
            if len(target) > 2000 or not target or any(ord(char) <= 32 or ord(char) == 127 for char in target) or "\\" in target:
                raise ValueError
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or "\\" in parsed.netloc:
                    raise ValueError
                item.update({"kind": "external", "verified": False, "fetched": False})
                findings.append({"severity": "review", "rule": "external-reference-not-fetched", **item})
            elif target.startswith("#"):
                item.update({"kind": "anchor", "verified": False})
            else:
                decoded = unquote(parsed.path, errors="strict")
                if parsed.query or "%" in decoded or any(char in decoded for char in "?#"):
                    raise ValueError
                if decoded.startswith("./"):
                    decoded = decoded[2:]
                relative = safe_path(decoded)
                resolved = str(PurePosixPath(path).parent / relative)
                safe_path(resolved)
                if kind != "skill" or root not in PurePosixPath(resolved).parents:
                    raise ValueError
                if resolved not in files:
                    item.update({"kind": "local", "resolved_path": resolved, "verified": False})
                    findings.append({"severity": "block", "rule": "missing-local-reference", **item})
                else:
                    item.update({"kind": "local", "resolved_path": resolved, "verified": True,
                                 "sha256": digest(files[resolved])})
        except (ValueError, UnicodeError, StratagentError):
            item.update({"kind": "unsupported", "verified": False})
            findings.append({"severity": "block", "rule": "unsafe-or-unsupported-reference", **item})
        records.append(item)

    try:
        for path, data in sorted(files.items()):
            source = PurePosixPath(path)
            if source.name.lower() in notice_names or source.suffix.lower() not in (".md", ".rst", ".txt"):
                continue
            text = data.decode("utf-8")
            definitions = {}
            for match in DEFINITION.finditer(text):
                budget()
                label = " ".join(match[1].split()).casefold()
                if label in definitions and definitions[label] != match[2]:
                    findings.append({"severity": "block", "rule": "ambiguous-reference-label", "path": path,
                                     "line": text[:match.start()].count("\n") + 1})
                definitions[label] = match[2]
                record(path, match[2], match.start(), text)
            inline_starts = set()
            for match in INLINE.finditer(text):
                budget()
                inline_starts.add(match.start())
                record(path, match[1], match.start(), text)
            for match in INLINE_START.finditer(text):
                budget()
                if match.start() not in inline_starts:
                    findings.append({"severity": "block", "rule": "unsupported-inline-reference", "path": path,
                                     "line": text[:match.start()].count("\n") + 1})
            for match in INDIRECT.finditer(text):
                budget()
                label = " ".join((match[2] or match[1]).split()).casefold()
                if label not in definitions:
                    findings.append({"severity": "block", "rule": "missing-reference-label", "path": path,
                                     "line": text[:match.start()].count("\n") + 1})
                else:
                    record(path, definitions[label], match.start(), text)
            for match in HTML_LINK.finditer(text):
                budget()
                record(path, match[2], match.start(), text)
            for match in PATH_LITERAL.finditer(text):
                budget()
                record(path, match[0].rstrip(".,;:"), match.start(), text)
    except StratagentError:
        findings.append({"severity": "block", "rule": "reference-limit", "path": entry})
    return {"references": records, "findings": findings,
            "scope": "Explicit inline/defined Markdown links, quoted HTML href/src and scripts/references/assets paths; not a full Markdown, HTML or code parser. Nothing is fetched."}
