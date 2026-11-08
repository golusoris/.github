"""Relative links in the rendered Markdown files name files that exist."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import repo_checks
from .repo_checks import (
    MAX_MARKDOWN_BYTES,
    ROOT,
    check_links,
    link_targets,
    markdown_files,
    relative_targets,
)


class RepositoryLinkTest(unittest.TestCase):
    def test_profile_and_health_files_are_checked(self):
        """Discovered Markdown files include repository profile and health docs."""
        names = {path.relative_to(ROOT).as_posix() for path in markdown_files()}
        self.assertTrue({"README.md", "CONTRIBUTING.md", "SECURITY.md", "profile/README.md"} <= names, names)

    def test_every_relative_link_resolves(self):
        """Every relative Markdown link across the repository resolves to a file."""
        files = markdown_files()
        self.assertTrue(files)
        total_targets = 0
        for path in files:
            total_targets += len(relative_targets(path))
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertEqual(check_links(path), [])
        self.assertGreater(total_targets, 0)


class LinkDefectTest(unittest.TestCase):
    def setUp(self):
        """Create a temporary repository layout with fixture files."""
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        self.root = Path(workdir.name) / "repo"
        self.root.mkdir()
        (self.root / "profile").mkdir()
        (self.root / "profile" / "banner.svg").write_text("<svg/>", encoding="utf-8")
        (self.root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")

    def check(self, text, name="profile/README.md"):
        """Write text to a file under the temporary root and check its links."""
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return check_links(path, self.root)

    def test_existing_targets_pass(self):
        """Links pointing to existing files, anchors, and reference targets pass."""
        text = "![b](banner.svg) [s](../SECURITY.md#report) [r](/SECURITY.md) [a](#top)\n[ref]: ../SECURITY.md\n"
        self.assertEqual(self.check(text), [])

    def test_missing_inline_target_is_refused(self):
        """An inline link pointing to a nonexistent relative file is flagged."""
        self.assertEqual(self.check("[gone](../CODE_OF_CONDUCT.md)\n"), ["profile/README.md: ../CODE_OF_CONDUCT.md names no file"])

    def test_missing_image_is_refused(self):
        """An image link referencing a missing file produces an error."""
        self.assertEqual(self.check("![logo](logo.png)\n"), ["profile/README.md: logo.png names no file"])

    def test_missing_reference_target_is_refused_once(self):
        """A missing target in a reference link produces exactly one error."""
        self.assertEqual(self.check("[x][ref]\n\n[ref]: missing.md\n"), ["profile/README.md: missing.md names no file"])

    def test_unused_reference_definition_is_checked(self):
        """An unused reference definition pointing to a missing file is flagged."""
        self.assertEqual(self.check("[ref]: missing.md\n"), ["profile/README.md: missing.md names no file"])

    def test_link_in_image_alt_text_is_not_a_target(self):
        """Link syntax inside image alt text is ignored during target extraction."""
        self.assertEqual(link_targets("![a [b](missing.md)](banner.svg)\n"), ["banner.svg"])

    def test_root_relative_target_resolves_from_the_root(self):
        """A leading-slash path resolves relative to the repository root."""
        self.assertEqual(self.check("[s](/profile/SECURITY.md)\n"), ["profile/README.md: /profile/SECURITY.md names no file"])

    def test_nested_image_link_checks_both_targets(self):
        """The link wrapping an image has its destination checked."""
        self.assertEqual(self.check("[![b](banner.svg)](missing.md)\n"), ["profile/README.md: missing.md names no file"])

    def test_angle_bracket_target_with_space(self):
        """Angle-bracketed paths containing spaces resolve to files on disk."""
        self.assertEqual(self.check("[x](<a b.md>)\n"), ["profile/README.md: a%20b.md names no file"])
        (self.root / "profile" / "a b.md").write_text("# A B\n", encoding="utf-8")
        self.assertEqual(self.check("[x](<a b.md>)\n"), [])

    def test_link_titles_in_quotes_or_parentheses_are_refused_when_missing(self):
        """Missing link targets with quoted or parenthesized titles are flagged."""
        self.assertEqual(self.check("[x](missing.md 'title')\n"), ["profile/README.md: missing.md names no file"])
        self.assertEqual(self.check("[x](missing.md (title))\n"), ["profile/README.md: missing.md names no file"])

    def test_reference_definition_with_angle_bracket_space(self):
        """Reference definitions using angle brackets with spaces resolve to disk."""
        (self.root / "profile" / "a b.md").write_text("# A B\n", encoding="utf-8")
        self.assertEqual(self.check("[ref]: <a b.md>\n"), [])

    def test_inline_code_followed_by_real_fence(self):
        """Links outside inline code spans are validated even when fences follow."""
        text = "```code``` and [x](missing.md)\n\n```\nfence\n```\n"
        self.assertEqual(self.check(text), ["profile/README.md: missing.md names no file"])

    def test_target_resolution_and_escape(self):
        """Query, root-anchor and // targets pass; a path out of the repo is refused."""
        (self.root.parent / "outside.md").write_text("# Outside\n", encoding="utf-8")
        self.assertEqual(self.check("[x](?query) [y](/#anchor)\n"), [])
        self.assertEqual(self.check("[p](//example.org/x)\n"), [])
        self.assertEqual(self.check("[u](../../outside.md)\n"), ["profile/README.md: ../../outside.md leaves the repository"])

    def test_url_encoded_target_passes_when_file_exists(self):
        """A URL-encoded path like '%20' resolves to the matching file on disk."""
        (self.root / "profile" / "a b.md").write_text("# A B\n", encoding="utf-8")
        self.assertEqual(self.check("[s](a%20b.md)\n"), [])

    def test_nested_profile_markdown_files_are_checked(self):
        """Nested profile Markdown files are discovered and checked for missing targets."""
        sub_dir = self.root / "profile" / "sub"
        sub_dir.mkdir(parents=True, exist_ok=True)
        doc = sub_dir / "x.md"
        doc.write_text("[x](missing.md)\n", encoding="utf-8")
        discovered = [p.relative_to(self.root).as_posix() for p in markdown_files(self.root)]
        self.assertIn("profile/sub/x.md", discovered)
        self.assertEqual(check_links(doc, self.root), ["profile/sub/x.md: missing.md names no file"])

    def test_image_naming_a_directory_is_refused(self):
        """An image referencing an existing directory is refused as not an image file."""
        self.assertEqual(
            self.check("![b](profile)\n", name="README.md"),
            ["README.md: profile names a directory, not an image file"],
        )

    def test_link_to_directory_passes(self):
        """A plain link pointing to an existing directory produces no error."""
        (self.root / "profile" / "sub").mkdir(exist_ok=True)
        self.assertEqual(self.check("[d](sub/)\n"), [])

    def test_target_used_as_link_and_image_is_treated_as_image(self):
        """A target used as both a link and an image is validated with image constraints."""
        text = "[d](profile) and ![d](profile)\n"
        self.assertEqual(
            self.check(text, name="README.md"),
            ["README.md: profile names a directory, not an image file"],
        )

    def test_html_image_block_missing_target_is_refused(self):
        """An HTML image block pointing to a nonexistent file is refused."""
        self.assertEqual(
            self.check('<img src="gone.svg">\n'),
            ["profile/README.md: gone.svg names no file"],
        )

    def test_inline_html_image_missing_target_is_refused(self):
        """An inline HTML image inside a paragraph pointing to a nonexistent file is refused."""
        self.assertEqual(
            self.check('text <img src="gone.svg"> text\n'),
            ["profile/README.md: gone.svg names no file"],
        )

    def test_html_link_and_inline_image_pass(self):
        """HTML paragraph links and inline images pointing to existing targets pass."""
        text = '<p><a href="../SECURITY.md">s</a></p>\ntext <img src="banner.svg"> text\n'
        self.assertEqual(self.check(text), [])

    def test_html_comments_yield_no_targets(self):
        """Markdown links and HTML tags inside HTML comments are ignored."""
        text = '<!-- [x](missing.md) <img src="gone.svg"> -->\n'
        self.assertEqual(link_targets(text), [])
        self.assertEqual(self.check(text), [])

    def test_external_html_image_is_skipped(self):
        """External HTML images with scheme prefixes produce no relative target errors."""
        self.assertEqual(self.check('<img src="https://example.org/x.svg">\n'), [])


class LinkBoundaryTest(unittest.TestCase):
    def test_external_and_anchor_targets_are_skipped(self):
        """External URI schemes and local fragment anchors are extracted as targets."""
        text = "[w](https://example.org/x) [m](mailto:a@example.org) [a](#x)\n"
        self.assertEqual(link_targets(text), ["https://example.org/x", "mailto:a@example.org", "#x"])

    def test_links_inside_code_are_ignored(self):
        """Link syntax inside inline code spans or fenced blocks is ignored."""
        text = "`[x](missing.md)`\n\n```md\n[y](missing.md)\n```\n"
        self.assertEqual(link_targets(text), [])

    def test_link_title_and_angle_brackets_are_stripped(self):
        """Angle brackets and trailing titles are stripped from extracted targets."""
        self.assertEqual(link_targets('[t](<c.md>) [u](d.md "title")\n'), ["c.md", "d.md"])

    def test_not_a_reference_definition(self):
        """Bracketed keys lacking a destination URI are not treated as definitions."""
        self.assertEqual(link_targets("[note]:\nNext paragraph.\n"), [])

    def test_code_fences_and_spans_contain_no_targets(self):
        """Indented and nested fences, double and multi-line spans yield no targets."""
        text = (
            "   ```\n   [x](missing.md)\n   ```\n\n"
            "````\n```\n[y](missing.md)\n```\n````\n\n"
            "`` `[z](missing.md)` ``\n\n"
            "`multi\n[w](missing.md)\nline`\n"
        )
        self.assertEqual(link_targets(text), [])

    def test_markdown_byte_cap_boundary(self):
        """A Markdown file of 1000000 bytes passes while 1000001 bytes is refused."""
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        root = Path(workdir.name) / "repo"
        root.mkdir()
        file_exact = root / "exact.md"
        file_exact.write_text("a" * MAX_MARKDOWN_BYTES, encoding="utf-8")
        self.assertEqual(check_links(file_exact, root), [])
        self.assertEqual(relative_targets(file_exact), [])

        file_over = root / "over.md"
        file_over.write_text("a" * (MAX_MARKDOWN_BYTES + 1), encoding="utf-8")
        with self.assertRaises(ValueError):
            relative_targets(file_over)
        self.assertEqual(
            check_links(file_over, root),
            [f"over.md: more than {MAX_MARKDOWN_BYTES} bytes"],
        )

    def test_markdown_file_cap_boundary(self):
        """Collecting Markdown files stops and raises when the file count exceeds the cap."""
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        root = Path(workdir.name) / "repo"
        root.mkdir()
        (root / "a.md").write_text("# A\n", encoding="utf-8")
        (root / "b.md").write_text("# B\n", encoding="utf-8")
        with patch.object(repo_checks, "MAX_MARKDOWN_FILES", 2):
            self.assertEqual(len(markdown_files(root)), 2)
            (root / "c.md").write_text("# C\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                markdown_files(root)


if __name__ == "__main__":
    unittest.main()
