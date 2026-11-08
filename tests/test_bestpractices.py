""".bestpractices.json: the OpenSSF Best Practices answers for project 16160."""

import json
import unittest

from .repo_checks import ROOT, check_answers

# Criteria a passing badge needs Met (or N/A where the criterion allows it)
# that this repository answers with its own test suite and policy.
TEST_CRITERIA = ("test", "test_invocation", "test_policy", "tests_are_added")


def load_answers():
    return json.loads((ROOT / ".bestpractices.json").read_text(encoding="utf-8"))


class AnswerFileTest(unittest.TestCase):
    def test_repository_answers_pass(self):
        self.assertEqual(check_answers(load_answers()), [])

    def test_test_criteria_are_met_and_point_at_the_suite(self):
        answers = load_answers()
        for criterion in TEST_CRITERIA:
            with self.subTest(criterion=criterion):
                self.assertEqual(answers[criterion + "_status"], "Met")
                self.assertIn("tests/", answers[criterion + "_justification"])

    def test_badge_names_this_project(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://www.bestpractices.dev/projects/16160/badge", readme)


class AnswerDefectTest(unittest.TestCase):
    def assertRefused(self, data, fragment):
        errors = check_answers(data)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_empty_document_is_refused(self):
        self.assertRefused({}, "non-empty object")
        self.assertRefused([], "non-empty object")

    def test_unknown_status_value_is_refused(self):
        self.assertRefused({"test_status": "Passing", "test_justification": "x"}, "'Passing' is not one of")

    def test_lower_case_status_value_is_refused(self):
        self.assertRefused({"test_status": "met", "test_justification": "x"}, "is not one of")

    def test_status_without_justification_is_refused(self):
        self.assertRefused({"test_status": "Met"}, "status without a justification")

    def test_blank_justification_is_refused(self):
        self.assertRefused({"test_status": "Met", "test_justification": " "}, "status without a justification")

    def test_justification_without_status_is_refused(self):
        self.assertRefused({"test_justification": "x"}, "justification without a status")

    def test_stray_key_is_refused(self):
        self.assertRefused({"test_status": "Met", "test_justification": "x", "test_url": "y"}, "test_url")


class AnswerBoundaryTest(unittest.TestCase):
    def test_every_accepted_status_value_passes(self):
        for value in ("Met", "Unmet", "N/A", "?"):
            with self.subTest(value=value):
                self.assertEqual(check_answers({"test_status": value, "test_justification": "x"}), [])


if __name__ == "__main__":
    unittest.main()
