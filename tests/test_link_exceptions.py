"""External link exceptions expire and continue to name a published link."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import yaml

from . import repo_checks
from .repo_checks import MAX_MARKDOWN_BYTES, ROOT, markdown_files

TODAY = date(2026, 11, 11)
EXPIRES = date(2027, 3, 11)
PATTERN = r"^https://ko-fi\.com/lusoris$"
EXCEPTION = (
    "# exception | file: README.md | rule: link-status | category: D | "
    "entered: 2026-11-11 | expires: 2027-03-11 | reason: funding bot wall"
)
SCORECARD_STEP_COUNT = 6
LINK_STEP_COUNT = 5
SHORT_CATEGORY_EXPIRIES = (("B", "2026-11-14"), ("C", "2026-11-21"))


class PublishedLinkCheckTest(unittest.TestCase):
    """Published workflows and presentation retain their regression defences."""

    def test_scorecard_handles_drafts_and_merge_queue(self):
        """Scorecard fails drafts and passes the merge queue without analysis."""
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/scorecard.yml").read_text(encoding="utf-8")
        )
        self.assertIn("merge_group", workflow.get("on", {}))
        steps = workflow["jobs"]["analysis"]["steps"]
        reference = yaml.safe_load(
            (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")
        )
        self.assertEqual(steps[0], reference["jobs"]["test"]["steps"][0])
        self.assertEqual(workflow["concurrency"], reference["concurrency"])
        self.assertEqual(steps[1]["if"], "github.event_name == 'merge_group'")
        self.assertIn('"$GITHUB_STEP_SUMMARY"', steps[1]["run"])
        for step in steps[2:SCORECARD_STEP_COUNT]:
            self.assertEqual(
                step["if"],
                "github.event.pull_request.draft != true && "
                "github.event_name != 'merge_group'",
            )
        self.assertEqual(len(steps), SCORECARD_STEP_COUNT)

    def test_links_workflow_checks_the_shared_manifest(self):
        """External links run on PRs, main and weekly with a pinned checker."""
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/links.yml").read_text(encoding="utf-8")
        )
        triggers = workflow["on"]
        self.assertEqual(set(triggers), {
            "pull_request", "push", "schedule", "workflow_dispatch"
        })
        self.assertEqual(triggers["push"], {"branches": ["main"]})
        self.assertEqual(triggers["schedule"], [{"cron": "45 6 * * 1"}])
        # Without a paths filter the declared ruleset would require this check.
        self.assertIn("**/*.md", triggers["pull_request"]["paths"])
        self.assertIn(".lycheeignore", triggers["pull_request"]["paths"])
        steps = workflow["jobs"]["links"]["steps"]
        reference = yaml.safe_load(
            (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")
        )
        self.assertEqual(steps[0], reference["jobs"]["test"]["steps"][0])
        self.assertEqual(workflow["concurrency"], reference["concurrency"])
        for step in steps[1:LINK_STEP_COUNT]:
            self.assertEqual(step["if"], "github.event.pull_request.draft != true")
        self.assertEqual(len(steps), LINK_STEP_COUNT)
        self.assertFalse(steps[1]["with"]["persist-credentials"])
        self.assertIn("--require-hashes", steps[2]["run"])
        self.assertIn("-B -m tests.link_inputs", steps[3]["run"])
        self.assertEqual(steps[4]["uses"],
                         "lycheeverse/lychee-action@e7477775783ea5526144ba13e8db5eec57747ce8")
        self.assertEqual(steps[4]["with"]["lycheeVersion"], "v0.24.2")
        self.assertIs(steps[4]["with"]["fail"], True)
        self.assertEqual(steps[4]["with"]["args"],
                         "--no-progress --scheme https --max-retries 2 --timeout 20 "
                         "--files-from ${{ runner.temp }}/markdown-files.txt")

    def test_readme_presentation_is_enabled(self):
        """The README has five styled badges and enables presentation enforcement."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        opening = readme.split("\n\n", 2)[1]
        self.assertEqual(opening.count("style=for-the-badge"), 5)
        config = yaml.safe_load((ROOT / ".standards.yaml").read_text(encoding="utf-8"))
        self.assertIs(config.get("gate", {}).get("readme_presentation"), True)

    def test_repository_exceptions_pass_at_entry(self):
        """The real exclusion file has valid, used exceptions at entry time."""
        text = (ROOT / ".lycheeignore").read_text(encoding="utf-8")
        self.assertEqual(repo_checks.check_link_exceptions(text, TODAY), [])

    def test_repository_exceptions_are_current(self):
        """The live date turns an expired repository exception into a failure."""
        text = (ROOT / ".lycheeignore").read_text(encoding="utf-8")
        self.assertEqual(repo_checks.check_link_exceptions(text, date.today()), [])

    def test_link_inputs_lists_rendered_markdown(self):
        """The CLI prints exactly the existing walker's repository-relative paths."""
        from .link_inputs import main

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(), 0)
        names = output.getvalue().splitlines()
        expected = [path.relative_to(ROOT).as_posix() for path in markdown_files()]
        self.assertEqual(names, expected)
        self.assertIn("README.md", names)
        self.assertIn("profile/README.md", names)


class LinkExceptionTest(unittest.TestCase):
    """Fixtures exercise positive, planted negative and boundary cases."""

    def setUp(self):
        """Create one Markdown fixture under an isolated repository root."""
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        self.root = Path(workdir.name)
        (self.root / "README.md").write_text(
            "[funding](https://ko-fi.com/lusoris)\n", encoding="utf-8"
        )

    def check(self, metadata=EXCEPTION, pattern=PATTERN, today=TODAY):
        """Check one exception against the temporary Markdown fixture."""
        return repo_checks.check_link_exceptions(
            metadata + "\n" + pattern + "\n", today, self.root
        )

    def assertRefused(self, errors, fragment):
        """Require a contextual diagnostic containing the expected fragment."""
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_valid_exception_passes(self):
        """A dated category D exception matching a Markdown link passes."""
        self.assertEqual(self.check(), [])

    def test_expiry_boundary(self):
        """The expiry date passes and the next day gives exactly one error."""
        self.assertEqual(self.check(today=EXPIRES), [])
        self.assertEqual(self.check(today=EXPIRES + timedelta(days=1)),
                         ["line 2: exception expired on 2027-03-11"])

    def test_pattern_without_metadata_is_refused(self):
        """An exclusion regex cannot silently omit exception metadata."""
        self.assertRefused(self.check(metadata="# ordinary comment"), "exception line")

    def test_metadata_without_pattern_is_refused(self):
        """An exception comment with no adjacent pattern is refused."""
        self.assertRefused(self.check(pattern=""), "no pattern")

    def test_blank_line_breaks_adjacency(self):
        """A blank line between metadata and its pattern is refused."""
        self.assertRefused(self.check(metadata=EXCEPTION + "\n"), "exception line")

    def test_missing_key_is_refused(self):
        """Every metadata field is mandatory."""
        self.assertRefused(self.check(EXCEPTION.replace(" | rule: link-status", "")), "keys")

    def test_unknown_key_is_refused(self):
        """A field outside the metadata allow-list is refused."""
        self.assertRefused(self.check(EXCEPTION.replace("rule:", "unknown:")), "keys")

    def test_duplicate_key_is_refused(self):
        """Repeated fields cannot overwrite metadata silently."""
        self.assertRefused(self.check(EXCEPTION.replace("rule:", "file:")), "keys")

    def test_reordered_keys_are_refused(self):
        """The metadata fields follow the documented order."""
        changed = EXCEPTION.replace("file: README.md | rule: link-status",
                                    "rule: link-status | file: README.md")
        self.assertRefused(self.check(changed), "keys")

    def test_blank_reason_is_refused(self):
        """An empty reason cannot justify an exclusion."""
        self.assertRefused(self.check(EXCEPTION.replace("funding bot wall", "")), "non-empty")

    def test_unknown_category_is_refused(self):
        """Only categories A, B, C and D are accepted."""
        self.assertRefused(self.check(EXCEPTION.replace("category: D", "category: E")), "category")

    def test_category_a_requires_interval(self):
        """Category A must state its interval directly after the category."""
        self.assertRefused(self.check(EXCEPTION.replace("category: D", "category: A")), "interval")

    def test_category_a_interval_passes(self):
        """A stated 30-day category A interval matches its expiry."""
        changed = EXCEPTION.replace("category: D", "category: A | interval: 30d")
        self.assertEqual(self.check(changed.replace("2027-03-11", "2026-12-11")), [])

    def test_short_categories_pass(self):
        """Categories B and C expire three and ten days after entry."""
        for category, expiry in SHORT_CATEGORY_EXPIRIES:
            changed = EXCEPTION.replace("category: D", "category: " + category)
            with self.subTest(category=category):
                self.assertEqual(self.check(changed.replace("2027-03-11", expiry)), [])

    def test_category_d_cannot_override_interval(self):
        """Fixed categories refuse an extra interval field."""
        self.assertRefused(self.check(EXCEPTION.replace("category: D",
                                                       "category: D | interval: 30d")), "keys")

    def test_bad_interval_is_refused(self):
        """Category A intervals must be positive whole days."""
        changed = EXCEPTION.replace("category: D", "category: A | interval: 0d")
        self.assertRefused(self.check(changed), "interval")

    def test_wrong_expiry_is_refused(self):
        """Expiry must equal entry plus the category's interval."""
        self.assertRefused(self.check(EXCEPTION.replace("2027-03-11", "2027-03-12")), "must equal")

    def test_bad_date_is_refused(self):
        """An impossible calendar date is refused with context."""
        self.assertRefused(self.check(EXCEPTION.replace("2026-11-11", "2026-02-30")), "date")

    def test_compact_date_is_refused(self):
        """Dates use the explicit ISO calendar YYYY-MM-DD form."""
        self.assertRefused(self.check(EXCEPTION.replace("2026-11-11", "20261111")), "date")

    def test_overflowing_interval_is_refused(self):
        """An interval beyond the calendar range returns an error."""
        changed = EXCEPTION.replace("category: D", "category: A | interval: 999999999999d")
        self.assertRefused(self.check(changed), "date or interval")

    def test_pattern_whitespace_is_refused(self):
        """Leading whitespace on a regex is refused rather than trimmed."""
        self.assertRefused(self.check(pattern=" " + PATTERN), "whitespace")

    def test_trailing_whitespace_is_refused(self):
        """A trailing tab on a regex is refused rather than trimmed."""
        self.assertRefused(self.check(pattern=PATTERN + "\t"), "whitespace")

    def test_whitespace_only_line_is_a_pattern(self):
        """Whitespace-only lines are patterns under lychee's reader rules."""
        self.assertRefused(self.check(pattern=" "), "whitespace")

    def test_invalid_pattern_is_refused(self):
        """A regex that does not compile is refused with context."""
        self.assertRefused(self.check(pattern="["), "invalid pattern")

    def test_missing_file_is_refused(self):
        """An exception must name an existing Markdown file."""
        self.assertRefused(self.check(EXCEPTION.replace("README.md", "gone.md")), "cannot read gone.md")

    def test_stale_pattern_is_refused(self):
        """An exclusion that matches no target in its named file is stale."""
        self.assertRefused(self.check(pattern="^https://example.org/$"),
                           "matches no link in README.md (stale exception)")

    def test_file_outside_root_is_refused(self):
        """An exception cannot read a file outside its repository root."""
        self.assertRefused(self.check(EXCEPTION.replace("README.md", "../README.md")), "leaves")

    def test_symlink_outside_root_is_refused(self):
        """A symlink cannot redirect an exception outside its root."""
        (self.root / "outside.md").symlink_to(self.root.parent / "outside.md")
        self.assertRefused(self.check(EXCEPTION.replace("README.md", "outside.md")), "leaves")

    def test_file_size_boundary(self):
        """The byte cap permits its boundary and rejects the next byte."""
        path = self.root / "README.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text + " " * (MAX_MARKDOWN_BYTES - len(text)), encoding="utf-8")
        self.assertEqual(self.check(), [])
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        self.assertRefused(self.check(), "more than")

    def test_invalid_file_encoding_is_refused(self):
        """Non-UTF-8 Markdown produces a contextual read error."""
        (self.root / "README.md").write_bytes(b"\xff")
        self.assertRefused(self.check(), "cannot read README.md")

    def test_exception_count_boundary(self):
        """The pattern cap passes at its limit and refuses one extra pattern."""
        text = EXCEPTION + "\n" + PATTERN + "\n"
        with patch.object(repo_checks, "MAX_LINK_EXCEPTIONS", 2):
            self.assertEqual(repo_checks.check_link_exceptions(text * 2, TODAY, self.root), [])
            self.assertRefused(repo_checks.check_link_exceptions(text * 3, TODAY, self.root),
                               "more than 2 patterns")

    def test_comments_and_empty_lines_are_skipped(self):
        """Empty lines and indented ordinary comments add no patterns."""
        text = "\n  # ordinary comment\n" + EXCEPTION + "\n" + PATTERN + "\n"
        self.assertEqual(repo_checks.check_link_exceptions(text, TODAY, self.root), [])

    def test_crlf_lines_pass(self):
        """CRLF terminators do not add whitespace to valid patterns."""
        text = EXCEPTION + "\r\n" + PATTERN + "\r\n"
        self.assertEqual(repo_checks.check_link_exceptions(text, TODAY, self.root), [])

    def test_unterminated_carriage_return_is_refused(self):
        """A final bare CR remains regex whitespace, as in Rust lines."""
        text = EXCEPTION + "\n" + PATTERN + "\r"
        self.assertRefused(repo_checks.check_link_exceptions(text, TODAY, self.root), "whitespace")

    def test_ignore_file_size_cap(self):
        """Exception input above the shared byte cap is refused before parsing."""
        text = "#" + " " * MAX_MARKDOWN_BYTES
        self.assertRefused(repo_checks.check_link_exceptions(text, TODAY, self.root), "more than")


if __name__ == "__main__":
    unittest.main()
