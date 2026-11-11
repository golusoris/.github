"""Dated, file-specific records accompany every Python suppression marker."""

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from . import repo_checks

TODAY = date(2026, 11, 11)
EXPIRES = date(2027, 3, 11)
SOURCE = "tests/example.py"
EXCEPTION = (
    f"# exception | file: {SOURCE} | rule: B404 | category: D | entered: 2026-11-11"
    " | expires: 2027-03-11 | reason: Fixed argv needs a child process."
)
MARKERS = ("nosec B404", "nosemgrep: example.rule", "noqa: I001")


class SuppressionExceptionsTest(unittest.TestCase):
    """Check real sources and planted suppression defects without executing them."""

    def setUp(self):
        """Create an isolated tests directory for bounded source fixtures."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "tests").mkdir()

    def check(self, text, today=TODAY):
        """Write one source fixture and return its suppression diagnostics."""
        (self.root / SOURCE).write_text(text, encoding="utf-8")
        return repo_checks.check_suppression_exceptions(self.root, today)

    def assertRefused(self, text, message, today=TODAY):
        """Require a contextual diagnostic for a planted source defect."""
        errors = self.check(text, today)
        self.assertTrue(errors, text)
        self.assertIn(message, "\n".join(errors))
        # Fixture byte cap bounds the returned diagnostic count.
        self.assertTrue(all(error.startswith(SOURCE + ":") for error in errors))

    def test_real_tree_has_recorded_suppressions(self):
        """All repository Python suppressions have current adjacent records."""
        today = datetime.now(timezone.utc).date()
        self.assertEqual(repo_checks.check_suppression_exceptions(repo_checks.ROOT, today), [])

    def test_valid_marker_pairs_pass(self):
        """All three marker forms accept an indented adjacent exception."""
        # Three supported comment markers, each below MAX_SUPPRESSION_BYTES.
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(self.check(f"  {EXCEPTION}\n  import os  # {marker}\n"), [])

    def test_marker_without_exception_is_refused(self):
        """Each marker requires metadata on the immediately preceding line."""
        # Three marker spellings share the same adjacency rule.
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assertRefused(f"import os  # {marker}\n", "directly follow an exception")

    def test_ordinary_exception_comment_passes(self):
        """The word exceptions does not begin an exception record."""
        self.assertEqual(self.check("# exceptions are logged below\npass\n"), [])

    def test_malformed_exception_prefix_is_refused(self):
        """A colon prefix cannot authorize an adjacent suppression marker."""
        text = EXCEPTION.replace("# exception | ", "# exception: ")
        self.assertRefused(text + f"\n# {MARKERS[0]}\n",
                           "suppression must directly follow an exception line")

    def test_wrong_file_is_refused(self):
        """A record for another source cannot authorize this suppression."""
        text = EXCEPTION.replace(SOURCE, "tests/other.py") + f"\nimport os  # {MARKERS[0]}\n"
        self.assertRefused(text, f"exception file must be {SOURCE}")

    def test_expired_exception_is_refused(self):
        """The day after expiry fails even when the interval is correct."""
        self.assertRefused(EXCEPTION + f"\nimport os  # {MARKERS[0]}\n", "expired on",
                           date(2027, 3, 12))

    def test_expiry_day_is_inclusive(self):
        """A category D record remains valid on its 120th day."""
        self.assertEqual(self.check(EXCEPTION + f"\nimport os  # {MARKERS[0]}\n", EXPIRES), [])

    def test_wrong_interval_is_refused(self):
        """One day below or above the category D interval is invalid."""
        # Two neighboring 120-day interval boundaries.
        for expiry in ("2027-03-10", "2027-03-12"):
            with self.subTest(expiry=expiry):
                text = EXCEPTION.replace("2027-03-11", expiry) + f"\n# {MARKERS[0]}\n"
                self.assertRefused(text, "expires must equal entered + 120 days")

    def test_invalid_date_is_refused(self):
        """Malformed and impossible dates cannot bypass shared date validation."""
        # Two invalid date forms exercise syntax and calendar validation.
        for entered in ("2026-1-11", "2026-02-30"):
            with self.subTest(entered=entered):
                text = EXCEPTION.replace("2026-11-11", entered) + f"\n# {MARKERS[0]}\n"
                self.assertRefused(text, "date")

    def test_unordered_metadata_is_refused(self):
        """Suppression records use the existing ordered metadata grammar."""
        text = EXCEPTION.replace("rule: B404 | category: D", "category: D | rule: B404")
        self.assertRefused(text + f"\n# {MARKERS[0]}\n", "exception keys must be")

    def test_orphan_exception_is_refused(self):
        """EOF, blank lines and ordinary comments leave a record orphaned."""
        # Three non-marker successors, including EOF.
        for following in ("", "\n", "\n# ordinary comment\n"):
            with self.subTest(following=following):
                self.assertRefused(EXCEPTION + following, "no suppression directly below")

    def test_marker_in_string_literal_still_counts(self):
        """The conservative line scan also catches comment forms inside strings."""
        text = f'value = "text # {MARKERS[0]}"\n'
        self.assertRefused(text, "directly follow an exception")
        self.assertEqual(self.check(EXCEPTION + "\n" + text), [])

    def test_non_comment_words_are_ignored(self):
        """Ordinary strings and longer words are outside the marker boundary."""
        # Three exact marker words and their non-marker suffix boundaries.
        for marker in MARKERS:
            word = marker.split()[0].removesuffix(":")
            with self.subTest(word=word):
                self.assertEqual(self.check(f'value = "{word}"  # {word}_example\n'), [])

    def test_source_byte_limit_is_inclusive(self):
        """UTF-8 bytes at the cap pass and one byte above it is refused."""
        with patch.object(repo_checks, "MAX_SUPPRESSION_BYTES", 4):
            self.assertEqual(self.check("éé"), [])
            self.assertRefused("éé ", "more than 4 bytes")

    def test_source_file_limit_is_inclusive(self):
        """The configured number of source files passes; the next one fails."""
        with patch.object(repo_checks, "MAX_SUPPRESSION_FILES", 1):
            self.assertEqual(self.check("pass\n"), [])
            (self.root / "tests/second.py").write_text("pass\n", encoding="utf-8")
            errors = repo_checks.check_suppression_exceptions(self.root, TODAY)
            self.assertIn("more than 1 Python files", "\n".join(errors))

    def test_invalid_utf8_is_refused(self):
        """Unreadable source text produces a contextual error, never a skip."""
        (self.root / SOURCE).write_bytes(b"\xff")
        errors = repo_checks.check_suppression_exceptions(self.root, TODAY)
        self.assertIn(f"cannot read {SOURCE}", "\n".join(errors))
