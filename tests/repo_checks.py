"""Checks for the files this repository publishes to the organisation.

Each check takes parsed data (or text) and returns a list of error strings;
an empty list means the input passes. The test modules run every check
against the real repository files and against planted defects.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Keys EndBug/label-sync reads from a label entry (src/index.ts at the
# commit .github/workflows/sync-labels.yml pins). Any other key is a typo
# the action would silently ignore, so the check refuses it.
LABEL_KEYS = frozenset({"name", "color", "description", "aliases"})

# The GitHub REST API takes a hexadecimal colour code without the leading
# '#'; label-sync strips one leading '#' before sending it.
LABEL_COLOR = re.compile(r"#?[0-9a-fA-F]{6}")

# Answer values the bestpractices.dev autofill file accepts per criterion.
STATUS_VALUES = frozenset({"Met", "Unmet", "N/A", "?"})
ANSWER_KEY = re.compile(r"[a-z0-9_]+_(status|justification)")

# Markdown files the organisation renders: the profile, the community health
# files and the decision records.
MARKDOWN_GLOBS = ("*.md", "profile/*.md", "docs/**/*.md")
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$", re.MULTILINE)
FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
CODE_SPAN = re.compile(r"`[^`\n]*`")
EXTERNAL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*:")


def check_label(entry, index):
    """Return the errors of one labels.yml entry at position index."""
    if not isinstance(entry, dict):
        return [f"entry {index}: not a mapping"]
    errors = [f"entry {index}: unknown key {key!r}" for key in sorted(set(entry) - LABEL_KEYS)]
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"entry {index}: name must be a non-empty string")
    color = entry.get("color")
    if not isinstance(color, str) or not LABEL_COLOR.fullmatch(color):
        errors.append(f"entry {index}: color must be six hexadecimal digits")
    if "description" in entry and not isinstance(entry["description"], str):
        errors.append(f"entry {index}: description must be a string")
    aliases = entry.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(a, str) and a for a in aliases):
        errors.append(f"entry {index}: aliases must be a list of non-empty strings")
    return errors


def label_names(entry):
    """Return the name and aliases one labels.yml entry claims."""
    if not isinstance(entry, dict):
        return []
    aliases = entry.get("aliases")
    return [entry.get("name")] + (aliases if isinstance(aliases, list) else [])


def check_labels(data):
    """Return the errors of a parsed labels.yml document."""
    if not isinstance(data, list) or not data:
        return ["labels.yml must be a non-empty list"]
    errors = []
    seen = {}
    for index, entry in enumerate(data):
        errors.extend(check_label(entry, index))
        for name in label_names(entry):
            if not isinstance(name, str):
                continue
            key = name.casefold()
            if key in seen:
                errors.append(f"entry {index}: {name!r} repeats entry {seen[key]}")
            seen.setdefault(key, index)
    return errors


def check_answers(data):
    """Return the errors of a parsed .bestpractices.json document."""
    if not isinstance(data, dict) or not data:
        return [".bestpractices.json must be a non-empty object"]
    errors = [f"{key}: not a <criterion>_status or _justification key" for key in sorted(data) if not ANSWER_KEY.fullmatch(key)]
    statuses = {key[: -len("_status")] for key in data if key.endswith("_status")}
    justified = {key[: -len("_justification")] for key in data if key.endswith("_justification")}
    for criterion in sorted(statuses):
        value = data[criterion + "_status"]
        if value not in STATUS_VALUES:
            errors.append(f"{criterion}_status: {value!r} is not one of {sorted(STATUS_VALUES)}")
        text = data.get(criterion + "_justification")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{criterion}: status without a justification")
    errors.extend(f"{criterion}: justification without a status" for criterion in sorted(justified - statuses))
    return errors


def link_targets(text):
    """Return the link and image targets of a Markdown text, code excluded."""
    prose = CODE_SPAN.sub("", FENCE.sub("", text))
    return INLINE_LINK.findall(prose) + REFERENCE_LINK.findall(prose)


def check_links(path, root=ROOT):
    """Return the relative link targets in path that name no file in root."""
    errors = []
    for target in link_targets(path.read_text(encoding="utf-8")):
        if target.startswith("#") or EXTERNAL.match(target):
            continue
        local = target.split("#", 1)[0].split("?", 1)[0]
        base = root if local.startswith("/") else path.parent
        if not (base / local.lstrip("/")).exists():
            errors.append(f"{path.relative_to(root)}: {target} names no file")
    return errors


def markdown_files(root=ROOT):
    """Return the rendered Markdown files under root, sorted."""
    return sorted({path for pattern in MARKDOWN_GLOBS for path in root.glob(pattern) if path.is_file()})
