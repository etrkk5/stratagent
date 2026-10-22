"""Bounded serialization, content identities, and strict portable paths."""
import hashlib
import json
import re
from pathlib import PurePosixPath


class StratagentError(Exception):
    """An actionable, safe-to-display failure."""


class GitHubLimitError(StratagentError):
    """Stop discovery rather than repeating requests after a global limit."""


MAX_FILE = 256 * 1024
MAX_BUNDLE = 2 * 1024 * 1024
MAX_FILES = 80
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(value):
    return digest(canonical(value))


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def repository(value):
    if not isinstance(value, str) or not REPO.fullmatch(value) or any(p in (".", "..") for p in value.split("/")):
        raise StratagentError("Repository must be an exact GitHub owner/repo name.")
    return value.lower()


def safe_path(value):
    if not isinstance(value, str) or not value or len(value) > 500:
        raise StratagentError("Invalid or oversized path.")
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or any(c in value for c in "\\:\0"):
        raise StratagentError("Unsafe path characters.")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise StratagentError("Absolute paths and traversal are forbidden.")
    if any(x.endswith((".", " ")) or x.lower().split(".")[0].rstrip(" ") in {"con", "prn", "aux", "nul", "conin$", "conout$", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))} for x in p.parts):
        raise StratagentError("Non-portable path.")
    return value


def decode_text(data):
    if len(data) > MAX_FILE:
        raise StratagentError("File exceeds 256 KiB limit.")
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise StratagentError("Only UTF-8 text bundles are supported.") from exc
    if any(ord(c) < 32 and c not in "\t\n\r" for c in text) or "\x7f" in text:
        raise StratagentError("Control characters in external content.")
    return text
