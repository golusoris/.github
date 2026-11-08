"""Relative links in the rendered Markdown files name files that exist."""

import tempfile
import unittest
from pathlib import Path

from repo_checks import ROOT, check_links, link_targets, markdown_files


class RepositoryLinkTest(unittest.TestCase):
    def test_profile_and_health_files_are_checked(self):
        names = {path.relative_to(ROOT).as_posix() for path in markdown_files()}
        self.assertTrue({"README.md", "CONTRIBUTING.md", "SECURITY.md", "profile/README.md"} <= names, names)

    def test_every_relative_link_resolves(self):
        for path in markdown_files():
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertEqual(check_links(path), [])


class LinkDefectTest(unittest.TestCase):
    def setUp(self):
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        self.root = Path(workdir.name)
        (self.root / "profile").mkdir()
        (self.root / "profile" / "banner.svg").write_text("<svg/>", encoding="utf-8")
        (self.root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")

    def check(self, text, name="profile/README.md"):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return check_links(path, self.root)

    def test_existing_targets_pass(self):
        text = "![b](banner.svg) [s](../SECURITY.md#report) [r](/SECURITY.md) [a](#top)\n[ref]: ../SECURITY.md\n"
        self.assertEqual(self.check(text), [])

    def test_missing_inline_target_is_refused(self):
        self.assertEqual(self.check("[gone](../CODE_OF_CONDUCT.md)\n"), ["profile/README.md: ../CODE_OF_CONDUCT.md names no file"])

    def test_missing_image_is_refused(self):
        self.assertEqual(self.check("![logo](logo.png)\n"), ["profile/README.md: logo.png names no file"])

    def test_missing_reference_target_is_refused(self):
        self.assertEqual(self.check("[x][ref]\n\n[ref]: missing.md\n"), ["profile/README.md: missing.md names no file"])

    def test_root_relative_target_resolves_from_the_root(self):
        self.assertEqual(self.check("[s](/profile/SECURITY.md)\n"), ["profile/README.md: /profile/SECURITY.md names no file"])


class LinkBoundaryTest(unittest.TestCase):
    def test_external_and_anchor_targets_are_skipped(self):
        text = "[w](https://example.org/x) [m](mailto:a@example.org) [a](#x)\n"
        self.assertEqual(link_targets(text), ["https://example.org/x", "mailto:a@example.org", "#x"])

    def test_links_inside_code_are_ignored(self):
        text = "`[x](missing.md)`\n\n```md\n[y](missing.md)\n```\n"
        self.assertEqual(link_targets(text), [])

    def test_link_title_and_angle_brackets_are_stripped(self):
        self.assertEqual(link_targets('[t](<c.md>) [u](d.md "title")\n'), ["c.md", "d.md"])


if __name__ == "__main__":
    unittest.main()
