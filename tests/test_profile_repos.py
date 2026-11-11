"""Public repository coverage and a mocked, fail-closed gh CLI integration."""

import io
import json
import subprocess
import unittest
from unittest.mock import patch

from . import profile_repos
from .repo_checks import MAX_REPOSITORIES, ROOT, unlisted_repositories

# Public org API measurement, 2026-11-11; .github itself is intentionally skipped.
REPOSITORY_NAMES = ("goenvoy", "golusoris", ".github", "sveltesentio", "template-native-gpu")
REPOSITORIES = [
    {"name": name, "archived": False, "fork": False, "private": False}
    for name in REPOSITORY_NAMES
]
RESPONSE = "\n".join(json.dumps(repository) for repository in REPOSITORIES)


class ProfileRepositoriesTest(unittest.TestCase):
    """Check root links, exclusions, case folding and collection boundaries."""

    def setUp(self):
        """Read the published profile and prepare one public repository."""
        self.profile = (ROOT / "profile/README.md").read_text(encoding="utf-8")
        self.repository = {"name": "project", "archived": False, "fork": False, "private": False}

    def test_real_profile_lists_public_repositories(self):
        """The published profile links every measured public org repository."""
        self.assertEqual(unlisted_repositories(self.profile, "golusoris", REPOSITORIES), [])

    def test_removed_sveltesentio_link_is_refused(self):
        """Removing just the SvelteKit root link produces exactly its error."""
        planted = self.profile.replace("(https://github.com/golusoris/sveltesentio)", "")
        self.assertEqual(unlisted_repositories(planted, "golusoris", REPOSITORIES), [
            "profile/README.md: public repository golusoris/sveltesentio has no link",
        ])

    def test_excluded_repositories_need_no_link(self):
        """Archived, fork, private and the organisation profile repo are skipped."""
        repositories = [
            dict(self.repository, archived=True),
            dict(self.repository, fork=True),
            dict(self.repository, private=True),
            dict(self.repository, name=".github"),
        ]
        self.assertEqual(unlisted_repositories("", "owner", repositories), [])

    def test_trailing_slash_is_accepted(self):
        """One trailing slash on a repository root still counts as listed."""
        self.assertEqual(unlisted_repositories("[p](https://github.com/owner/project/)",
                                              "owner", [self.repository]), [])

    def test_subpath_does_not_count(self):
        """A blob link cannot stand in for the public repository root."""
        self.assertEqual(unlisted_repositories("[p](https://github.com/owner/project/blob/main)",
                                              "owner", [self.repository]), [
            "profile/README.md: public repository owner/project has no link",
        ])

    def test_owner_and_name_are_case_insensitive(self):
        """GitHub owner and repository name comparisons ignore case."""
        self.assertEqual(unlisted_repositories("[p](https://github.com/OWNER/PROJECT)",
                                              "Owner", [self.repository]), [])

    def test_raw_html_root_link_counts(self):
        """HTML anchor links use the existing Markdown target extractor."""
        self.assertEqual(unlisted_repositories('<a href="https://github.com/owner/project">p</a>',
                                              "owner", [self.repository]), [])

    def test_code_link_does_not_count(self):
        """A repository URL inside code is excluded by the shared extractor."""
        self.assertEqual(len(unlisted_repositories("`[p](https://github.com/owner/project)`",
                                                  "owner", [self.repository])), 1)

    def test_errors_are_sorted(self):
        """Missing root links are reported in stable lexical order."""
        repositories = [dict(self.repository, name="z"), dict(self.repository, name="a")]
        self.assertEqual(unlisted_repositories("", "owner", repositories), [
            "profile/README.md: public repository owner/a has no link",
            "profile/README.md: public repository owner/z has no link",
        ])

    def test_collection_limit_is_inclusive(self):
        """Exactly MAX_REPOSITORIES entries remain within the collection bound."""
        self.assertEqual(unlisted_repositories("[p](https://github.com/owner/project)",
                                              "owner", iter([self.repository] * MAX_REPOSITORIES)), [])

    def test_collection_over_limit_is_refused(self):
        """One entry over MAX_REPOSITORIES raises a contextual ValueError."""
        with self.assertRaisesRegex(ValueError, f"more than {MAX_REPOSITORIES} repositories"):
            unlisted_repositories("", "owner", iter([self.repository] * (MAX_REPOSITORIES + 1)))


class ProfileRepositoriesCLITest(unittest.TestCase):
    """Exercise the CLI with subprocess fully mocked and without a live login."""

    def run_cli(self, stdout=RESPONSE, returncode=0, side_effect=None, argv=None):
        """Capture CLI output and assert the exact bounded gh invocation."""
        output, errors = io.StringIO(), io.StringIO()
        result = subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="API failed")
        with patch.object(profile_repos.subprocess, "run", return_value=result, side_effect=side_effect) as run:
            with patch("sys.stdout", output), patch("sys.stderr", errors):
                code = profile_repos.main(["--repository", "golusoris/.github"] if argv is None else argv)
        run.assert_called_once_with(
            ["gh", "api", "--paginate", "orgs/golusoris/repos?type=public&per_page=100", "--jq",
             ".[] | {name, archived, fork, private}"],
            capture_output=True, text=True, timeout=60, check=False,
        )
        return code, output.getvalue(), errors.getvalue()

    def test_success_returns_zero(self):
        """All four public repositories linked yields success and a count."""
        self.assertEqual(self.run_cli(), (0, "profile/README.md: 4 public repositories linked\n", ""))

    def test_unlisted_returns_one(self):
        """A public repository absent from the profile returns a coverage failure."""
        repository = dict(REPOSITORIES[0], name="unlisted")
        code, output, errors = self.run_cli(stdout=json.dumps(repository))
        self.assertEqual(code, 1)
        self.assertEqual(output, "profile/README.md: public repository golusoris/unlisted has no link\n")
        self.assertEqual(errors, "")

    def test_gh_nonzero_returns_two(self):
        """A failed gh request returns 2 and includes gh stderr."""
        code, _, errors = self.run_cli(returncode=1)
        self.assertEqual(code, 2)
        self.assertIn("gh api exited 1: API failed", errors)

    def test_timeout_returns_two(self):
        """The gh subprocess timeout fails closed with deadline context."""
        code, _, errors = self.run_cli(side_effect=subprocess.TimeoutExpired("gh", 60))
        self.assertEqual(code, 2)
        self.assertIn("gh api timed out after 60 seconds", errors)

    def test_missing_gh_returns_two(self):
        """A missing gh executable returns 2 with an actionable message."""
        code, _, errors = self.run_cli(side_effect=FileNotFoundError())
        self.assertEqual(code, 2)
        self.assertIn("gh executable not found", errors)

    def test_malformed_line_returns_two(self):
        """A malformed JSON line refuses the whole response with line context."""
        code, _, errors = self.run_cli(stdout=RESPONSE + "\nnot JSON")
        self.assertEqual(code, 2)
        self.assertIn("gh output line 6: malformed JSON", errors)

    def test_missing_key_returns_two(self):
        """Incomplete repository data cannot silently exclude a public repo."""
        code, _, errors = self.run_cli(stdout='{"name": "partial"}')
        self.assertEqual(code, 2)
        self.assertIn("gh output line 1: missing repository key", errors)

    def test_blank_lines_are_ignored(self):
        """Blank lines between valid JSON objects do not alter the count."""
        self.assertEqual(self.run_cli(stdout="\n" + RESPONSE + "\n\n")[0], 0)

    def test_nonobject_line_returns_two(self):
        """A JSON array in place of an object fails closed."""
        code, _, errors = self.run_cli(stdout="[]")
        self.assertEqual(code, 2)
        self.assertIn("expected a JSON object", errors)

    def test_invalid_flag_type_returns_two(self):
        """A string flag cannot hide a repository through truthiness."""
        code, _, errors = self.run_cli(stdout=json.dumps(dict(REPOSITORIES[0], private="false")))
        self.assertEqual(code, 2)
        self.assertIn("must be booleans", errors)

    def test_repository_environment_default(self):
        """The CLI uses GITHUB_REPOSITORY when no argument overrides it."""
        with patch.object(profile_repos, "os") as operating_system:
            operating_system.environ = {"GITHUB_REPOSITORY": "golusoris/.github"}
            self.assertEqual(self.run_cli(argv=[])[0], 0)

    def test_repository_fallback(self):
        """Absent GITHUB_REPOSITORY uses the specified public organisation default."""
        with patch.object(profile_repos, "os") as operating_system:
            operating_system.environ = {}
            self.assertEqual(self.run_cli(argv=[])[0], 0)

    def test_repository_argument_overrides_environment(self):
        """An explicit repository takes precedence over GITHUB_REPOSITORY."""
        with patch.object(profile_repos, "os") as operating_system:
            operating_system.environ = {"GITHUB_REPOSITORY": "elsewhere/.github"}
            self.assertEqual(self.run_cli()[0], 0)
