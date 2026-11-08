"""labels.yml: the label set every golusoris repository syncs."""

import unittest

import yaml

from .repo_checks import ROOT, check_labels


def label(name="type:feat", color="0e8a16", **extra):
    """Construct a sample label mapping with valid defaults."""
    entry = {"name": name, "color": color, "description": "New user-facing feature"}
    entry.update(extra)
    return entry


class LabelFileTest(unittest.TestCase):
    def test_repository_label_set_passes(self):
        """The repository labels.yml file passes all validation checks."""
        data = yaml.safe_load((ROOT / "labels.yml").read_text(encoding="utf-8"))
        self.assertEqual(check_labels(data), [])

    def test_valid_entry_passes(self):
        """Valid label entries with standard colors and aliases produce no errors."""
        self.assertEqual(check_labels([label(), label("type:fix", "#D73A4A", aliases=["bug"])]), [])


class LabelDefectTest(unittest.TestCase):
    def assertRefused(self, data, fragment):
        """Assert check_labels reports an error containing the expected fragment."""
        errors = check_labels(data)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_empty_document_is_refused(self):
        """An empty list or empty YAML document is refused."""
        self.assertRefused([], "non-empty list")
        self.assertRefused(None, "non-empty list")

    def test_non_mapping_entry_is_refused(self):
        """A list entry that is not a dictionary is refused."""
        self.assertRefused(["type:feat"], "not a mapping")

    def test_misspelt_key_is_refused(self):
        """An unrecognized key such as 'colour' is refused."""
        self.assertRefused([label(colour="0e8a16")], "unknown key 'colour'")

    def test_blank_name_is_refused(self):
        """A label name consisting only of whitespace is refused."""
        self.assertRefused([label(name="  ")], "name must be")

    def test_missing_color_is_refused(self):
        """A label entry missing the required color field is refused."""
        entry = label()
        del entry["color"]
        self.assertRefused([entry], "color must be")

    def test_non_string_description_is_refused(self):
        """A description that is not a string is refused."""
        self.assertRefused([label(description=7)], "description must be")

    def test_string_aliases_are_refused(self):
        """An aliases value that is a string instead of a list is refused."""
        self.assertRefused([label(aliases="bug")], "aliases must be")

    def test_blank_alias_is_refused(self):
        """A label alias of only spaces is refused."""
        self.assertRefused([label(aliases=["   "])], "aliases must be")

    def test_duplicate_name_ignores_case(self):
        """Label names differing only in case are detected as duplicates."""
        self.assertRefused([label("Type:Feat"), label("type:feat")], "repeats entry 0")

    def test_duplicate_name_with_trailing_whitespace_is_refused(self):
        """Label names differing only in trailing whitespace are refused."""
        self.assertRefused([label("a "), label("a")], "repeats entry 0")

    def test_alias_colliding_with_a_name_is_refused(self):
        """An alias matching an existing label name is refused as a collision."""
        self.assertRefused([label("type:fix"), label("type:bug", aliases=["TYPE:FIX"])], "repeats entry 0")


class LabelColorBoundaryTest(unittest.TestCase):
    def test_six_digits_with_or_without_hash_pass(self):
        """Six-character hexadecimal color strings pass with or without a hash."""
        for color in ("000000", "FFFFFF", "#a1b2c3"):
            with self.subTest(color=color):
                self.assertEqual(check_labels([label(color=color)]), [])

    def test_wrong_length_or_digit_is_refused(self):
        """Bad lengths, a doubled hash, non-hex or non-string colors are refused."""
        for color in ("", "fff", "12345", "1234567", "##123456", "12345g", 123456):
            with self.subTest(color=color):
                self.assertNotEqual(check_labels([label(color=color)]), [])


if __name__ == "__main__":
    unittest.main()
