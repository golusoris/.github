"""Checks for the files this repository publishes to the organisation.

Each check takes parsed data (or text) and returns a list of error strings;
an empty list means the input passes. The test modules run every check
against the real repository files and against planted defects.
"""

import math
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent

# Keys EndBug/label-sync reads from a label entry (src/index.ts at the
# commit .github/workflows/sync-labels.yml pins). Any other key is a typo
# the action would silently ignore, so the check refuses it.
LABEL_KEYS = frozenset({"name", "color", "description", "aliases"})

# The GitHub REST API takes a hexadecimal colour code without the leading
# '#'; label-sync strips one leading '#' before sending it.
LABEL_COLOR = re.compile(r"#?[0-9a-fA-F]{6}")

# GitHub REST API limits: 422 'name is too long (maximum is 50 characters)'
# and 'Description is too long (maximum is 100 characters)'.
LABEL_NAME_MAX = 50
LABEL_DESCRIPTION_MAX = 100

# Bounded collection limits to satisfy HISS-02 scalar loop bounds.
MAX_LABELS = 1000
MAX_ANSWER_KEYS = 2000
MAX_MARKDOWN_BYTES = 1_000_000
MAX_MARKDOWN_FILES = 1000
MAX_REPOSITORIES = 1000
REPOSITORY_FLAGS = ("archived", "fork", "private")
MAX_SVG_BYTES = 1_000_000
MAX_SVG_DEPTH = 100

SVG_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")

# Geometry-affecting attributes must be modeled before accepting them.
BANNER_ATTRIBUTES = {
    "g": frozenset({"fill", "stroke-linecap", "font-family", "font-size", "opacity"}),
    "text": frozenset({
        "x", "y", "font-family", "font-size", "font-weight", "fill", "letter-spacing", "opacity",
    }),
    "tspan": frozenset({"fill", "opacity"}),
    "path": frozenset({
        "d", "stroke", "stroke-width", "stroke-dasharray", "opacity", "fill-opacity",
        "stroke-opacity",
    }),
}
# Elements the clearance model reads or that carry no glyph geometry; any other
# element (use, textPath, image, foreignObject, ...) could place text unmodeled.
BANNER_ELEMENTS = frozenset({
    "svg", "title", "desc", "defs", "lineargradient", "stop", "rect", "g", "text", "tspan",
    "path",
})

# Answer values the bestpractices.dev autofill file accepts per criterion.
STATUS_VALUES = frozenset({"Met", "Unmet", "N/A", "?"})
ANSWER_KEY = re.compile(r"[a-z0-9_]+_(status|justification)")

# Markdown files the organisation renders: the profile, the community health
# files and the decision records.
MARKDOWN_GLOBS = ("*.md", "profile/**/*.md", "docs/**/*.md")
EXTERNAL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*:")


class _LinkHTMLParser(HTMLParser):
    """Extract link href and image src/srcset targets from HTML tokens."""

    def __init__(self):
        """Initialize the parser with an empty target buffer."""
        super().__init__()
        self.drained = []

    def handle_starttag(self, tag, attrs):
        """Collect targets from an HTML start or empty tag."""
        attr_dict = dict(attrs)
        if tag == "a" and "href" in attr_dict:
            href = attr_dict["href"]
            if href:
                self.drained.append((href, False))
        elif tag == "img" and "src" in attr_dict:
            src = attr_dict["src"]
            if src:
                self.drained.append((src, True))
        elif tag == "source" and "srcset" in attr_dict:
            srcset = attr_dict["srcset"]
            if srcset:
                for part in srcset.split(","):
                    candidate = part.strip()
                    if candidate:
                        url = candidate.split()[0]
                        if url:
                            self.drained.append((url, True))

    def drain(self):
        """Return the collected targets and clear the buffer."""
        collected = self.drained
        self.drained = []
        return collected


class MarkdownTooLarge(ValueError):
    """A Markdown file is larger than MAX_MARKDOWN_BYTES."""


def _html_targets(fragment):
    """Return the (target, is_image) pairs of one raw HTML fragment.

    Each fragment gets its own parser, closed at the end, so an unfinished
    tag in one fragment cannot join the text of the next.
    """
    parser = _LinkHTMLParser()
    parser.feed(fragment)
    parser.close()
    return parser.drain()


def check_label(entry, index):
    """Return the errors of one labels.yml entry at position index."""
    if not isinstance(entry, dict):
        return [f"entry {index}: not a mapping"]
    errors = [f"entry {index}: unknown key {key!r}" for key in sorted(set(entry) - LABEL_KEYS)]
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"entry {index}: name must be a non-empty string")
    elif len(name) > LABEL_NAME_MAX:
        errors.append(f"entry {index}: name exceeds {LABEL_NAME_MAX} characters")
    color = entry.get("color")
    if not isinstance(color, str) or not LABEL_COLOR.fullmatch(color):
        errors.append(f"entry {index}: color must be six hexadecimal digits")
    if "description" in entry:
        desc = entry["description"]
        if not isinstance(desc, str):
            errors.append(f"entry {index}: description must be a string")
        elif len(desc) > LABEL_DESCRIPTION_MAX:
            errors.append(f"entry {index}: description exceeds {LABEL_DESCRIPTION_MAX} characters")
    aliases = entry.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(a, str) and a.strip() for a in aliases):
        errors.append(f"entry {index}: aliases must be a list of non-empty strings")
    else:
        for alias in aliases:
            if len(alias) > LABEL_NAME_MAX:
                errors.append(f"entry {index}: alias {alias!r} exceeds {LABEL_NAME_MAX} characters")
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
    if len(data) > MAX_LABELS:
        return [f"labels.yml: more than {MAX_LABELS} entries"]
    errors = []
    seen = {}
    for index, entry in enumerate(data):
        errors.extend(check_label(entry, index))
        for name in label_names(entry):
            if not isinstance(name, str):
                continue
            key = name.strip().casefold()
            if key in seen:
                errors.append(f"entry {index}: {name!r} repeats entry {seen[key]}")
            seen.setdefault(key, index)
    return errors


def check_answers(data):
    """Return the errors of a parsed .bestpractices.json document."""
    if not isinstance(data, dict) or not data:
        return [".bestpractices.json must be a non-empty object"]
    if len(data) > MAX_ANSWER_KEYS:
        return [f".bestpractices.json: more than {MAX_ANSWER_KEYS} keys"]
    errors = [f"{key}: not a <criterion>_status or _justification key" for key in sorted(data) if not ANSWER_KEY.fullmatch(key)]
    statuses = {key[: -len("_status")] for key in data if key.endswith("_status")}
    justified = {key[: -len("_justification")] for key in data if key.endswith("_justification")}
    for criterion in sorted(statuses):
        value = data[criterion + "_status"]
        if not isinstance(value, str) or value not in STATUS_VALUES:
            errors.append(f"{criterion}_status: {value!r} is not one of {sorted(STATUS_VALUES)}")
        text = data.get(criterion + "_justification")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{criterion}: status without a justification")
    errors.extend(f"{criterion}: justification without a status" for criterion in sorted(justified - statuses))
    return errors


def required_contexts(ruleset):
    """Return the status check contexts a parsed ruleset requires."""
    rules = ruleset.get("rules") if isinstance(ruleset, dict) else None
    if not isinstance(rules, list):
        return []
    contexts = []
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
            continue
        parameters = rule.get("parameters")
        checks = parameters.get("required_status_checks") if isinstance(parameters, dict) else None
        for check in checks if isinstance(checks, list) else []:
            if isinstance(check, dict) and isinstance(check.get("context"), str):
                contexts.append(check["context"])
    return contexts


# A pull_request filter that can skip the workflow. A skipped workflow leaves
# its required check pending, which blocks the merge (GitHub Docs, "Skipping
# workflow runs").
SKIPPING_FILTERS = ("paths", "paths-ignore", "branches-ignore")


def runs_on_every_pull_request(workflow):
    """Return whether a parsed workflow runs on every pull request."""
    # PyYAML reads the bare key `on` as the boolean True.
    trigger = workflow.get("on", workflow.get(True))
    if isinstance(trigger, str):
        return trigger == "pull_request"
    if isinstance(trigger, list):
        return "pull_request" in [name for name in trigger if isinstance(name, str)]
    if not isinstance(trigger, dict) or "pull_request" not in trigger:
        return False
    config = trigger["pull_request"]
    return not (isinstance(config, dict) and any(key in config for key in SKIPPING_FILTERS))


def check_required_checks(ruleset, workflows):
    """Return the required status checks no pull request workflow job reports."""
    if not isinstance(ruleset, dict):
        return ["ruleset must be a mapping"]
    reported = set()
    for workflow in workflows:
        if not isinstance(workflow, dict) or not runs_on_every_pull_request(workflow):
            continue
        jobs = workflow.get("jobs")
        for job_id, job in jobs.items() if isinstance(jobs, dict) else []:
            reported.add(job.get("name", job_id) if isinstance(job, dict) else job_id)
    return [
        f"required check {context!r} not found in pull_request workflows"
        for context in required_contexts(ruleset)
        if context not in reported
    ]


# The commitments of the README test policy (README.md, "Test policy").
TEST_POLICY_FRAGMENTS = (
    "Test policy:",
    "adds a test to `tests/` in the same pull request",
    "a passing case",
    "a refused planted defect",
    "the boundary between them",
    "A fix adds a test that fails without it",
)


def check_test_policy(text):
    """Return the test policy commitments a README text does not state.

    Line breaks and runs of spaces count as one space, so rewrapping the
    paragraph does not change the result.
    """
    collapsed = " ".join(text.split())
    return [f"README.md: test policy lacks {fragment!r}" for fragment in TEST_POLICY_FRAGMENTS if fragment not in collapsed]


def _extract_targets(text):
    """Return all targets in document order and the set of image targets."""
    env = {}
    tokens = MarkdownIt("commonmark").enable("table").parse(text, env)
    targets = []
    image_targets = set()
    # Token loops are bounded by MAX_MARKDOWN_BYTES since MarkdownIt parses
    # a finite input string whose length is capped prior to parsing.
    for block in tokens:
        if block.type == "html_block" and block.content:
            for target, is_image in _html_targets(block.content):
                targets.append(target)
                if is_image:
                    image_targets.add(target)
        for token in block.children or []:
            if token.type == "link_open":
                href = token.attrGet("href")
                if href:
                    targets.append(href)
            elif token.type == "image":
                src = token.attrGet("src")
                if src:
                    targets.append(src)
                    image_targets.add(src)
            elif token.type == "html_inline" and token.content:
                for target, is_image in _html_targets(token.content):
                    targets.append(target)
                    if is_image:
                        image_targets.add(target)
    references = env.get("references", {})
    for label in sorted(references):
        href = references[label].get("href")
        if href is not None:
            targets.append(href)
    deduped = [target for target in dict.fromkeys(targets) if target is not None]
    return deduped, image_targets


def link_targets(text):
    """Return the link and image targets of a Markdown text, code excluded.

    Each target appears once, in document order, followed by the targets of
    reference definitions no link uses. Raw HTML a, img, and source tags are
    checked; comments and other tags are ignored.
    """
    targets, _ = _extract_targets(text)
    return targets


def profile_repositories(repositories, self_name=".github"):
    """Return public, original, active repositories within the collection bound."""
    included = []
    for index, repository in enumerate(repositories):
        if index >= MAX_REPOSITORIES:
            raise ValueError(f"more than {MAX_REPOSITORIES} repositories")
        if repository["name"].casefold() == self_name.casefold():
            continue
        if not any(repository[key] for key in REPOSITORY_FLAGS):
            included.append(repository)
    return included


def unlisted_repositories(profile_text, owner, repositories, self_name=".github"):
    """Return sorted errors for public repositories without an exact root link."""
    if len(profile_text) > MAX_MARKDOWN_BYTES:
        raise ValueError(f"profile/README.md: more than {MAX_MARKDOWN_BYTES} characters")
    # Target count is bounded by MAX_MARKDOWN_BYTES before Markdown parsing.
    targets = {target.removesuffix("/").casefold() for target in link_targets(profile_text)}
    included = profile_repositories(repositories, self_name)
    return sorted(
        f"profile/README.md: public repository {owner}/{repository['name']} has no link"
        for repository in included
        if f"https://github.com/{owner}/{repository['name']}".casefold() not in targets
    )


def _wave_start(path):
    """Return the minimum absolute path x, refusing unsupported SVG commands."""
    if re.search(r"[^MCSL\s,]", SVG_NUMBER.sub("", path)):
        raise ValueError("wave path: only absolute M, C, S and L commands supported")
    # Matches and coordinates are bounded by MAX_SVG_BYTES in the caller.
    numbers = [float(number) for number in SVG_NUMBER.findall(path)]
    if not numbers or len(numbers) % 2:
        raise ValueError("wave path: missing or unpaired coordinates")
    if not all(math.isfinite(number) for number in numbers):
        raise ValueError("wave path: coordinates must be finite")
    return min(numbers[::2])


def _attribute_errors(tag, attributes):
    """Return unsupported elements, transforms and attributes in deterministic order."""
    errors = []
    if tag not in BANNER_ELEMENTS:
        errors.append(f"{tag}: unsupported element")
    if "transform" in attributes:
        errors.append(f"{tag}: transform is unsupported")
    if tag in BANNER_ATTRIBUTES:
        # Attribute lists are bounded by MAX_SVG_BYTES before parsing; a
        # transform is reported once, above.
        errors.extend(
            f"{tag}: unsupported attribute {name}"
            for name in sorted(set(attributes) - BANNER_ATTRIBUTES[tag] - {"transform"})
        )
    return errors


class _BannerParser(HTMLParser):
    """Collect SVG text geometry and absolute paths with bounded group nesting."""

    def __init__(self):
        """Initialize text, path, error and inherited font-size buffers."""
        super().__init__()
        self.groups = []
        self.active_text = None
        self.texts = []
        self.paths = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        """Collect geometry and inherit font-size from the nearest group."""
        attributes = dict(attrs)
        self.errors.extend(_attribute_errors(tag, attributes))
        inherited = self.groups[-1] if self.groups else None
        if tag == "g":
            if len(self.groups) >= MAX_SVG_DEPTH:
                raise ValueError(f"SVG: group nesting exceeds {MAX_SVG_DEPTH}")
            self.groups.append(attributes.get("font-size", inherited))
        elif tag == "text":
            if self.active_text is not None:
                raise ValueError("SVG: nested text elements unsupported")
            self.active_text = (
                attributes.get("x"), attributes.get("font-size", inherited), [],
                attributes.get("letter-spacing", 0),
            )
        elif tag == "path":
            try:
                self.paths.append(_wave_start(attributes.get("d") or ""))
            except ValueError as error:
                self.errors.append(str(error))

    def handle_data(self, data):
        """Keep text content, including content inside tspan elements."""
        if self.active_text is not None:
            self.active_text[2].append(data)

    def handle_endtag(self, tag):
        """Finish text records or pop one enclosing group."""
        if tag == "g" and self.groups:
            self.groups.pop()
        elif tag == "text" and self.active_text is not None:
            x, font_size, fragments, letter_spacing = self.active_text
            self.texts.append(("".join(fragments).strip(), x, font_size, letter_spacing))
            self.active_text = None


def _banner_text_errors(record, wave_start, margin, advance):
    """Return missing geometry or insufficient clearance errors for one text."""
    text, x, font_size, letter_spacing = record
    try:
        x, font_size = float(x), float(font_size)
    except (TypeError, ValueError):
        return [f"{text}: missing or invalid x or font-size"]
    if not math.isfinite(x) or not math.isfinite(font_size) or font_size <= 0:
        return [f"{text}: x and font-size must be finite; font-size must be positive"]
    try:
        letter_spacing = float(letter_spacing)
    except (TypeError, ValueError):
        return [f"{text}: invalid letter-spacing"]
    if not math.isfinite(letter_spacing):
        return [f"{text}: invalid letter-spacing"]
    edge = x + len(text) * (advance * font_size + letter_spacing)
    if edge > wave_start - margin:
        return [f"{text}: right edge {edge:.1f} within {margin} of wave start {wave_start:.1f}"]
    return []


def check_banner_clearance(svg_text, margin=24, advance=0.62):
    """Return SVG text errors where the estimated right edge crowds a wave."""
    if len(svg_text.encode("utf-8")) > MAX_SVG_BYTES:
        return [f"SVG: more than {MAX_SVG_BYTES} bytes"]
    parser = _BannerParser()
    try:
        parser.feed(svg_text)
        parser.close()
    except ValueError as error:
        return [f"SVG: {error}"]
    errors = parser.errors.copy()
    if not parser.texts:
        errors.append("SVG: no text elements")
    if not parser.paths:
        return errors + ["SVG: no wave paths"]
    wave_start = min(parser.paths)
    # Parser events and text records are bounded by MAX_SVG_BYTES.
    for record in parser.texts:
        errors.extend(_banner_text_errors(record, wave_start, margin, advance))
    return errors


def _relative_targets(path):
    """Return relative targets and the set of image targets for path."""
    if path.stat().st_size > MAX_MARKDOWN_BYTES:
        raise MarkdownTooLarge(f"{path}: more than {MAX_MARKDOWN_BYTES} bytes")
    targets, image_targets = _extract_targets(path.read_text(encoding="utf-8"))
    rel_targets = []
    for target in targets:
        if target.startswith("//") or EXTERNAL.match(target):
            continue
        local = target.split("#", 1)[0].split("?", 1)[0]
        if not local:
            continue
        rel_targets.append(target)
    return rel_targets, image_targets


def relative_targets(path):
    """Return the relative link targets in the Markdown file at path."""
    targets, _ = _relative_targets(path)
    return targets


def check_links(path, root=ROOT):
    """Return the relative link targets in path that name no file in root."""
    rel = path.relative_to(root)
    try:
        targets, image_targets = _relative_targets(path)
    except MarkdownTooLarge:
        return [f"{rel}: more than {MAX_MARKDOWN_BYTES} bytes"]
    errors = []
    for target in targets:
        local = target.split("#", 1)[0].split("?", 1)[0]
        unquoted = unquote(local)
        base = root if unquoted.startswith("/") else path.parent
        target_path = (base / unquoted.lstrip("/")).resolve()
        if not target_path.is_relative_to(root.resolve()):
            errors.append(f"{rel}: {target} leaves the repository")
        elif not target_path.exists():
            errors.append(f"{rel}: {target} names no file")
        elif target in image_targets and not target_path.is_file():
            errors.append(f"{rel}: {target} names a directory, not an image file")
    return errors


def markdown_files(root=ROOT):
    """Return the rendered Markdown files under root, sorted."""
    discovered = set()
    for pattern in MARKDOWN_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                discovered.add(path)
                if len(discovered) > MAX_MARKDOWN_FILES:
                    raise ValueError(f"{root}: more than {MAX_MARKDOWN_FILES} markdown files")
    return sorted(discovered)
