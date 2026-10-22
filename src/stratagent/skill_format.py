"""Bounded Agent Skills frontmatter parsing using PyYAML's safe loader."""
import math

import yaml

from .common import NAME, StratagentError, decode_text

FIELDS = frozenset({"name", "description", "license", "compatibility", "metadata", "allowed-tools"})


class UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key == "<<" or key in result:
                raise StratagentError("Duplicate or non-string metadata field; YAML merges are unsupported.")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def bounded_yaml(header):
    if len(header.encode("utf-8")) > 16 * 1024:
        raise StratagentError("Frontmatter exceeds 16 KiB limit.")
    try:
        depth = 0
        for count, event in enumerate(yaml.parse(header, Loader=yaml.SafeLoader), 1):
            if count > 512:
                raise StratagentError("Frontmatter exceeds 512 YAML events.")
            if isinstance(event, yaml.events.AliasEvent) or getattr(event, "anchor", None) is not None or getattr(event, "tag", None) is not None:
                raise StratagentError("YAML aliases, anchors and explicit tags are unsupported.")
            if isinstance(event, (yaml.events.MappingStartEvent, yaml.events.SequenceStartEvent)):
                depth += 1
                if depth > 6:
                    raise StratagentError("Frontmatter exceeds six collection levels.")
            elif isinstance(event, (yaml.events.MappingEndEvent, yaml.events.SequenceEndEvent)):
                depth -= 1
        value = yaml.load(header, Loader=UniqueSafeLoader)
    except (yaml.YAMLError, ValueError, RecursionError):
        raise StratagentError("Invalid YAML frontmatter; review its syntax and scalar types.") from None

    def validate(item):
        if isinstance(item, dict):
            if len(item) > 64 or any(not isinstance(key, str) or not 1 <= len(key) <= 128 for key in item):
                raise StratagentError("Metadata mappings require bounded string keys.")
            for key in item:
                validate(key)
            for child in item.values():
                validate(child)
        elif isinstance(item, list):
            for child in item:
                validate(child)
        elif isinstance(item, str):
            try:
                decode_text(item.encode("utf-8"))
            except UnicodeError:
                raise StratagentError("Metadata strings must be valid UTF-8 text.") from None
        elif item is not None and not isinstance(item, (bool, int, float)):
            raise StratagentError("Unsupported metadata scalar type; quote textual values.")
        elif isinstance(item, float) and not math.isfinite(item):
            raise StratagentError("Non-finite metadata numbers are unsupported.")

    validate(value)
    if not isinstance(value, dict):
        raise StratagentError("Frontmatter must be a string-keyed mapping.")
    return value


def metadata(text):
    decode_text(text.encode("utf-8"))
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise StratagentError("Definition requires YAML frontmatter.")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise StratagentError("Unclosed frontmatter.") from None
    result = bounded_yaml("\n".join(lines[1:end]))
    name = result.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 64:
        raise StratagentError("Name must be a 1–64 character lowercase slug.")
    for field, limit, required in (("description", 1024, True), ("license", 1024, False),
                                   ("compatibility", 500, False), ("allowed-tools", 1024, False)):
        if required or field in result:
            value = result.get(field)
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
                raise StratagentError(f"{field} must be a nonempty string of at most {limit} characters.")
            result[field] = value.strip()
    if "metadata" in result:
        extra = result["metadata"]
        if not isinstance(extra, dict) or len(extra) > 32 or any(not isinstance(value, str) or len(value) > 1024 for value in extra.values()):
            raise StratagentError("metadata must map at most 32 string keys to string values of at most 1024 characters.")
    body = "\n".join(lines[end + 1:]).strip()
    if not body:
        raise StratagentError("Definition body is empty.")
    return result, body + "\n"
