"""labels.yml: the label set every golusoris repository syncs."""

import unittest

import yaml

from .repo_checks import ROOT, check_labels


def label(name="type:feat", color="0e8a16", **extra):
    entry = {"name": name, "color": color, "description": "New user-facing feature"}
    entry.update(extra)
    return entry


class LabelFileTest(unittest.TestCase):
    def test_repository_label_set_passes(self):
        data = yaml.safe_load((ROOT / "labels.yml").read_text(encoding="utf-8"))
        self.assertEqual(check_labels(data), [])

    def test_valid_entry_passes(self):
        self.assertEqual(check_labels([label(), label("type:fix", "#D73A4A", aliases=["bug"])]), [])


class LabelDefectTest(unittest.TestCase):
    def assertRefused(self, data, fragment):
        errors = check_labels(data)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_empty_document_is_refused(self):
        self.assertRefused([], "non-empty list")
        self.assertRefused(None, "non-empty list")

    def test_non_mapping_entry_is_refused(self):
        self.assertRefused(["type:feat"], "not a mapping")

    def test_misspelt_key_is_refused(self):
        self.assertRefused([label(colour="0e8a16")], "unknown key 'colour'")

    def test_blank_name_is_refused(self):
        self.assertRefused([label(name="  ")], "name must be")

    def test_missing_color_is_refused(self):
        entry = label()
        del entry["color"]
        self.assertRefused([entry], "color must be")

    def test_non_string_description_is_refused(self):
        self.assertRefused([label(description=7)], "description must be")

    def test_string_aliases_are_refused(self):
        self.assertRefused([label(aliases="bug")], "aliases must be")

    def test_blank_alias_is_refused(self):
        self.assertRefused([label(aliases=["   "])], "aliases must be")

    def test_duplicate_name_ignores_case(self):
        self.assertRefused([label("Type:Feat"), label("type:feat")], "repeats entry 0")

    def test_duplicate_name_with_trailing_whitespace_is_refused(self):
        self.assertRefused([label("a "), label("a")], "repeats entry 0")

    def test_alias_colliding_with_a_name_is_refused(self):
        self.assertRefused([label("type:fix"), label("type:bug", aliases=["TYPE:FIX"])], "repeats entry 0")


class LabelColorBoundaryTest(unittest.TestCase):
    def test_six_digits_with_or_without_hash_pass(self):
        for color in ("000000", "FFFFFF", "#a1b2c3"):
            with self.subTest(color=color):
                self.assertEqual(check_labels([label(color=color)]), [])

    def test_wrong_length_or_digit_is_refused(self):
        for color in ("", "fff", "12345", "1234567", "##123456", "12345g", 123456):
            with self.subTest(color=color):
                self.assertNotEqual(check_labels([label(color=color)]), [])


if __name__ == "__main__":
    unittest.main()
