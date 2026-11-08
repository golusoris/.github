""".bestpractices.json: the OpenSSF Best Practices answers for project 16160."""

import json
import unittest

import yaml

from .repo_checks import (
    MAX_ANSWER_KEYS,
    ROOT,
    TEST_POLICY_FRAGMENTS,
    check_answers,
    check_required_checks,
    check_test_policy,
)


def ruleset(*contexts):
    """Return a minimal ruleset that requires the given status checks."""
    checks = [{"context": context} for context in contexts]
    return {"rules": [{"type": "required_status_checks", "parameters": {"required_status_checks": checks}}]}


def workflow(on, job="make test"):
    """Return a minimal parsed workflow with one job named job."""
    return {True: on, "jobs": {"test": {"name": job}}}

# Criteria a passing badge needs Met (or N/A where the criterion allows it)
# that this repository answers with its own test suite and policy.
TEST_CRITERIA = ("test", "test_invocation", "test_policy", "tests_are_added")


def load_answers():
    """Return the parsed .bestpractices.json of the repository."""
    return json.loads((ROOT / ".bestpractices.json").read_text(encoding="utf-8"))


class AnswerFileTest(unittest.TestCase):
    def test_repository_answers_pass(self):
        """The repository .bestpractices.json file passes every answer check."""
        self.assertEqual(check_answers(load_answers()), [])

    def test_test_criteria_are_met_and_point_at_the_suite(self):
        """Every test criterion is Met and cites the tests/ directory."""
        answers = load_answers()
        for criterion in TEST_CRITERIA:
            with self.subTest(criterion=criterion):
                self.assertEqual(answers[criterion + "_status"], "Met")
                self.assertIn("tests/", answers[criterion + "_justification"])

    def test_badge_names_this_project(self):
        """README.md contains the OpenSSF badge URL for project 16160."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://www.bestpractices.dev/projects/16160/badge", readme)

    def test_test_invocation_matches_makefile(self):
        """The test invocation justification contains the exact make test command."""
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        recipe = ""
        lines = makefile.splitlines()
        for idx, line in enumerate(lines):
            if line.startswith("test:"):
                recipe = lines[idx + 1].strip()
                break
        prefix = "@$(PYTHON) "
        self.assertTrue(recipe.startswith(prefix), recipe)
        rest = recipe.removeprefix(prefix)
        answers = load_answers()
        self.assertIn("python3 " + rest, answers["test_invocation_justification"])

    def test_ci_and_release_notes_criteria(self):
        """Continuous integration and release notes criteria have valid statuses and justifications."""
        answers = load_answers()
        self.assertEqual(answers["test_continuous_integration_status"], "Met")
        self.assertIn(".github/workflows/test.yml", answers["test_continuous_integration_justification"])
        self.assertIn(answers["release_notes_status"], ("Met", "N/A"))

    def test_required_status_checks_match_workflows(self):
        """Every required status check corresponds to a pull request workflow job."""
        ruleset = json.loads((ROOT / ".github/rulesets/main.json").read_text(encoding="utf-8"))
        workflows = []
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            workflows.append(yaml.safe_load(path.read_text(encoding="utf-8")))
        self.assertEqual(check_required_checks(ruleset, workflows), [])

    def test_readme_declares_test_policy(self):
        """README.md states every commitment of the test policy."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(check_test_policy(readme), [])


class AnswerDefectTest(unittest.TestCase):
    def assertRefused(self, data, fragment):
        """Assert check_answers reports an error containing the expected fragment."""
        errors = check_answers(data)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_empty_document_is_refused(self):
        """An empty mapping or list document is refused."""
        self.assertRefused({}, "non-empty object")
        self.assertRefused([], "non-empty object")

    def test_unknown_status_value_is_refused(self):
        """A criterion status outside the accepted set is refused."""
        self.assertRefused({"test_status": "Passing", "test_justification": "x"}, "'Passing' is not one of")

    def test_lower_case_status_value_is_refused(self):
        """A lower-case status value like 'met' is refused."""
        self.assertRefused({"test_status": "met", "test_justification": "x"}, "is not one of")

    def test_list_status_is_refused(self):
        """A list status value is refused as unrecognized without raising."""
        self.assertRefused({"test_status": [], "test_justification": "x"}, "is not one of")

    def test_dict_status_is_refused(self):
        """A dictionary status value is refused as unrecognized without raising."""
        self.assertRefused({"test_status": {}, "test_justification": "x"}, "is not one of")

    def test_status_without_justification_is_refused(self):
        """A status entry missing a justification key is refused."""
        self.assertRefused({"test_status": "Met"}, "status without a justification")

    def test_blank_justification_is_refused(self):
        """A whitespace-only justification string is refused."""
        self.assertRefused({"test_status": "Met", "test_justification": " "}, "status without a justification")

    def test_justification_without_status_is_refused(self):
        """A justification entry missing a status key is refused."""
        self.assertRefused({"test_justification": "x"}, "justification without a status")

    def test_stray_key_is_refused(self):
        """Keys not matching the status or justification pattern are refused."""
        self.assertRefused({"test_status": "Met", "test_justification": "x", "test_url": "y"}, "test_url")

    def test_missing_required_check_is_refused(self):
        """A required status check no workflow job reports is refused."""
        self.assertEqual(
            check_required_checks(ruleset("gone"), [workflow(["pull_request"])]),
            ["required check 'gone' not found in pull_request workflows"],
        )

    def test_required_check_behind_a_path_filter_is_refused(self):
        """A required check from a workflow that path filters can skip is refused."""
        on = {"pull_request": {"paths": ["tests/**"]}}
        self.assertNotEqual(check_required_checks(ruleset("make test"), [workflow(on)]), [])

    def test_required_check_from_a_push_only_workflow_is_refused(self):
        """A required check from a workflow that never runs on pull requests is refused."""
        self.assertNotEqual(check_required_checks(ruleset("make test"), [workflow("push")]), [])

    def test_malformed_ruleset_and_workflows_do_not_raise(self):
        """Rules, parameters and jobs of the wrong type are skipped without an exception."""
        rules = {"rules": [None, {"type": "required_status_checks", "parameters": []}]}
        broken = [None, {True: ["pull_request", {"x": 1}], "jobs": []}]
        self.assertEqual(check_required_checks(rules, broken), [])
        self.assertEqual(check_required_checks({"rules": {}}, broken), [])

    def test_incomplete_test_policy_is_refused(self):
        """A README text without the planted-defect commitment is refused."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        planted = " ".join(readme.split()).replace("a refused planted defect", "a test")
        self.assertEqual(check_test_policy(planted), ["README.md: test policy lacks 'a refused planted defect'"])


class AnswerBoundaryTest(unittest.TestCase):
    def test_every_accepted_status_value_passes(self):
        """Each accepted status value passes when accompanied by justification."""
        for value in ("Met", "Unmet", "N/A", "?"):
            with self.subTest(value=value):
                self.assertEqual(check_answers({"test_status": value, "test_justification": "x"}), [])

    def test_required_check_trigger_forms_pass(self):
        """A pull_request trigger as a string, a list, a mapping or a branch filter passes."""
        for on in ("pull_request", ["push", "pull_request"], {"pull_request": None}, {"pull_request": {"branches": ["main"]}}):
            with self.subTest(on=on):
                self.assertEqual(check_required_checks(ruleset("make test"), [workflow(on)]), [])

    def test_job_context_is_its_name_or_else_its_id(self):
        """A named job reports only its name; a job without a name reports its id."""
        unnamed = {True: "pull_request", "jobs": {"test": {}}}
        self.assertEqual(check_required_checks(ruleset("test"), [unnamed]), [])
        self.assertNotEqual(check_required_checks(ruleset("make test"), [unnamed]), [])
        self.assertNotEqual(check_required_checks(ruleset("test"), [workflow("pull_request")]), [])

    def test_wrapped_test_policy_passes(self):
        """A test policy whose sentences wrap at every space passes."""
        text = "\n".join(fragment.replace(" ", "\n  ") for fragment in TEST_POLICY_FRAGMENTS)
        self.assertEqual(check_test_policy(text), [])

    def test_answer_keys_count_boundary(self):
        """An answers mapping with 2000 keys passes while 2001 keys is refused."""
        answers_2000 = {}
        for i in range(MAX_ANSWER_KEYS // 2):
            answers_2000[f"c{i}_status"] = "Met"
            answers_2000[f"c{i}_justification"] = "x"
        self.assertEqual(check_answers(answers_2000), [])
        answers_2001 = dict(answers_2000)
        answers_2001["c1000_status"] = "Met"
        self.assertEqual(check_answers(answers_2001), [f".bestpractices.json: more than {MAX_ANSWER_KEYS} keys"])


if __name__ == "__main__":
    unittest.main()
