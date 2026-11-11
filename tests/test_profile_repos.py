"""Public repository coverage and a mocked, fail-closed gh CLI integration."""

import io
import json
import sys
import unittest
from unittest.mock import patch

from . import profile_repos
from .repo_checks import MAX_REPOSITORIES, ROOT, link_targets, unlisted_repositories

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

    def test_non_hyperlink_targets_do_not_count(self):
        """Unused definitions and image sources cannot satisfy root coverage."""
        url = "https://github.com/owner/project"
        cases = (f"[unused]: {url}", f"![p]({url})", f'<img src="{url}">',
                 f'<source srcset="{url} 1x, {url} 2x">',
                 f'inline <img src="{url}"> text')
        # Five non-hyperlink forms, bounded by this tuple.
        for markdown in cases:
            with self.subTest(markdown=markdown):
                self.assertEqual(unlisted_repositories(markdown, "owner", [self.repository]), [
                    "profile/README.md: public repository owner/project has no link",
                ])

    def test_used_reference_and_linked_image_count(self):
        """Resolved reference links and an image's enclosing hyperlink count."""
        url = "https://github.com/owner/project"
        cases = (f"[p][r]\n\n[r]: {url}", f"[![i](x.png)]({url})",
                 f'inline <a href="{url}">p</a> text')
        # Three hyperlink forms at the image/reference extraction boundary.
        for markdown in cases:
            with self.subTest(markdown=markdown):
                self.assertEqual(unlisted_repositories(markdown, "owner", [self.repository]), [])

    def test_file_target_extractor_keeps_images_and_definitions(self):
        """Hyperlink filtering leaves general file validation targets intact."""
        text = '![i](image.png)\n\n[unused]: unused.md\n\n<source srcset="a.png 1x, b.png 2x">'
        self.assertEqual(link_targets(text),
                         ["image.png", "a.png", "b.png", "unused.md"])

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
    """Exercise the CLI with its byte collector mocked and without a live login."""

    def run_cli(self, stdout=RESPONSE, returncode=0, side_effect=None, argv=None,
                expected_owner="golusoris"):
        """Capture CLI output and assert the exact bounded gh invocation."""
        output, errors = io.StringIO(), io.StringIO()
        result = profile_repos.Collected(returncode, stdout=stdout, stderr="API failed")
        with (
            patch.object(profile_repos, "_collect_output", return_value=result, side_effect=side_effect) as run,
            patch("sys.stdout", output), patch("sys.stderr", errors),
        ):
            code = profile_repos.main(["--repository", "golusoris/.github"] if argv is None else argv)
        run.assert_called_once_with(
            ["gh", "api", "--paginate", f"orgs/{expected_owner}/repos?type=public&per_page=100", "--jq",
             ".[] | {name, archived, fork, private}"],
            timeout=60, limit=profile_repos.MAX_API_OUTPUT,
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
        code, _, errors = self.run_cli(side_effect=profile_repos.CollectionTimeout(60))
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

    def test_nonobject_parser_raises_type_error(self):
        """Every non-object JSON type keeps its response line in a TypeError."""
        # Five JSON type boundaries after one valid object.
        for value in ([], None, "repository", 1, True):
            with self.subTest(value=value), self.assertRaisesRegex(
                TypeError, "gh output line 2: expected a JSON object"
            ):
                profile_repos._parse_repositories(RESPONSE.splitlines()[0] + "\n" + json.dumps(value))

    def test_invalid_flag_type_returns_two(self):
        """A string flag cannot hide a repository through truthiness."""
        code, _, errors = self.run_cli(stdout=json.dumps(dict(REPOSITORIES[0], private="false")))
        self.assertEqual(code, 2)
        self.assertIn("must be booleans", errors)

    def test_repository_environment_default(self):
        """The CLI uses GITHUB_REPOSITORY when no argument overrides it."""
        with patch.object(profile_repos, "os") as operating_system:
            operating_system.environ = {"GITHUB_REPOSITORY": "elsewhere/.github"}
            self.assertEqual(self.run_cli(argv=[], expected_owner="elsewhere")[0], 1)

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


class APIOutputCollectionTest(unittest.TestCase):
    """Exercise byte bounds and deadlines with offline Python children."""

    def test_exact_output_limit_is_accepted(self):
        """A response of exactly the byte limit is collected successfully."""
        result = profile_repos._collect_output(
            [sys.executable, "-c", "import sys; sys.stdout.write('x' * 64)"],
            timeout=5, limit=64)
        self.assertEqual(result.stdout, "x" * 64)
        self.assertEqual(result.returncode, 0)
        script = "import sys; sys.stdout.buffer.write(bytes([195,169])*32)"
        result = profile_repos._collect_output([sys.executable, "-c", script], timeout=5, limit=64)
        self.assertEqual(result.stdout, "é" * 32)

    def test_empty_output_is_accepted(self):
        """EOF before any bytes is the collection lower boundary."""
        result = profile_repos._collect_output([sys.executable, "-c", "pass"], timeout=5, limit=64)
        self.assertEqual(result.stdout, "")

    def test_collected_result_is_immutable(self):
        """A successful collection cannot have its captured exit status rewritten."""
        result = profile_repos._collect_output([sys.executable, "-c", "pass"], timeout=5, limit=64)
        with self.assertRaises(AttributeError):
            result.returncode = 7

    def test_decode_deadline_is_inclusive(self):
        """Decoding just before the deadline passes; reaching it raises a timeout."""
        # Two deterministic last-clock boundaries, after collection and child exit.
        for now in (0.999, 1.0):
            with self.subTest(now=now), patch.object(
                profile_repos.time, "monotonic", side_effect=(0, 0, 0, 0, now)
            ):
                if now < 1:
                    result = profile_repos._collect_output(
                        [sys.executable, "-c", "pass"], timeout=1, limit=64)
                    self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
                else:
                    with self.assertRaises(profile_repos.CollectionTimeout) as raised:
                        profile_repos._collect_output(
                            [sys.executable, "-c", "pass"], timeout=1, limit=64)
                    self.assertEqual(raised.exception.timeout, 1)

    def fetch_python(self, script, children=None):
        """Run the fetch integration offline while retaining real subprocess I/O."""
        popen = profile_repos.subprocess.Popen

        def start_python(command, **kwargs):
            """Replace only the executable, retaining the collector pipe setup."""
            child = popen([sys.executable, "-c", script], **kwargs)
            if children is not None:
                children.append(child)
            return child

        with (
            patch.object(profile_repos, "MAX_API_OUTPUT", 64),
            patch.object(profile_repos.subprocess, "Popen", side_effect=start_python),
        ):
            return profile_repos._fetch_repositories("owner")

    def test_output_over_limit_kills_child(self):
        """The fetch path stops a live child after limit plus one bytes."""
        children = []
        script = "import sys,time; sys.stdout.write('x'*65); sys.stdout.flush(); time.sleep(10)"
        with self.assertRaisesRegex(ValueError, "gh output exceeds 64"):
            self.fetch_python(script, children)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].returncode)
        self.assertNotEqual(children[0].returncode, 0)
        self.assertIsNotNone(children[0].poll())

    def test_sleeping_child_hits_collection_deadline(self):
        """A silent child cannot block the bounded reader beyond its deadline."""
        with self.assertRaises(profile_repos.CollectionTimeout) as raised:
            profile_repos._collect_output(
                [sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1, limit=64)
        self.assertIn("timed out", str(raised.exception))
        self.assertEqual(raised.exception.timeout, 0.1)

    def test_closed_stdout_does_not_remove_exit_deadline(self):
        """A child that closes stdout must still exit before the same deadline."""
        with self.assertRaises(profile_repos.CollectionTimeout):
            profile_repos._collect_output(
                [sys.executable, "-c", "import os,time; os.close(1); time.sleep(10)"],
                timeout=0.1, limit=64)

    def test_nonzero_exit_keeps_bounded_stderr(self):
        """Large stderr cannot deadlock and only a fixed prefix is retained."""
        script = "import sys; sys.stderr.write('API failed'+'x'*100000); sys.exit(7)"
        result = profile_repos._collect_output([sys.executable, "-c", script], timeout=5, limit=64)
        self.assertEqual(result.returncode, 7)
        self.assertTrue(result.stderr.startswith("API failed"))
        self.assertEqual(len(result.stderr), profile_repos.MAX_API_STDERR)

    def test_invalid_utf8_is_refused_with_context(self):
        """Invalid bytes are reported as a contextual collection ValueError."""
        script = "import sys; sys.stdout.buffer.write(bytes([255]))"
        with self.assertRaisesRegex(ValueError, "gh output.*UTF-8"):
            self.fetch_python(script)

    def test_limit_counts_bytes_before_utf8_decoding(self):
        """Multibyte text consumes its encoded byte length in the reader."""
        script = "import sys; sys.stdout.buffer.write(bytes([195,169])*33)"
        with self.assertRaisesRegex(ValueError, "gh output exceeds 64"):
            self.fetch_python(script)

    def test_parser_retains_independent_output_limit(self):
        """Parsing still refuses excess data if the collector is bypassed."""
        with (
            patch.object(profile_repos, "MAX_API_OUTPUT", 64),
            self.assertRaisesRegex(ValueError, "gh output exceeds 64"),
        ):
            profile_repos._parse_repositories(" " * 65)
