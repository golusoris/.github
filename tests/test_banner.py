"""Banner text stays clear of the decorative waves, including planted defects."""

import unittest

from .repo_checks import MAX_SVG_BYTES, MAX_SVG_DEPTH, ROOT, check_banner_clearance


class BannerClearanceTest(unittest.TestCase):
    """Exercise real banner geometry and the clearance boundary."""

    def setUp(self):
        """Read the real banner for positive and planted negative checks."""
        self.svg = (ROOT / "profile/golusoris-readme-banner.svg").read_text(encoding="utf-8")

    def test_real_banner_has_clearance(self):
        """Every text element in the published banner clears the wave."""
        self.assertEqual(check_banner_clearance(self.svg), [])

    def test_original_wave_start_overlaps_subtitles(self):
        """Moving the waves back to x=700 flags both monospace subtitles."""
        errors = check_banner_clearance(self.svg.replace("M800", "M700"))
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(errors[0].startswith("Foundational Go libraries"), errors)
        self.assertTrue(errors[1].startswith("Composable fx modules"), errors)

    def test_exact_margin_passes(self):
        """A right edge exactly margin units before the path passes."""
        svg = '<svg><text x="0" font-size="10">abc</text><path d="M54 0 L80 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_one_unit_inside_margin_fails(self):
        """A right edge one unit beyond the clearance boundary is refused."""
        svg = '<svg><text x="1" font-size="10">abc</text><path d="M54 0 L80 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [
            "abc: right edge 31.0 within 24 of wave start 54.0",
        ])

    def test_nearest_group_supplies_font_size(self):
        """Nested groups inherit the nearest font-size, including tspan text."""
        svg = ('<svg><g font-size="100"><g font-size="10"><g>'
               '<text x="0">a<tspan>b</tspan>c</text></g></g></g>'
               '<path d="M54 0 L80 0"/></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_text_font_size_overrides_group(self):
        """A text element's font-size overrides the enclosing group."""
        svg = ('<svg><g font-size="100"><text x="0" font-size="10">abc</text>'
               '</g><path d="M54 0"/></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_relative_commands_are_refused(self):
        """Relative m and c path commands cannot be treated as absolute x."""
        svg = '<svg><text x="0" font-size="10">a</text><path d="m80 0 c1 2 3 4 5 6"/></svg>'
        self.assertIn("only absolute M, C, S and L commands", " ".join(check_banner_clearance(svg)))

    def test_other_absolute_commands_are_refused(self):
        """An absolute H command lacks paired x/y coordinates and is refused."""
        svg = '<svg><text x="0" font-size="10">a</text><path d="M80 0 H90"/></svg>'
        self.assertIn("only absolute M, C, S and L commands", " ".join(check_banner_clearance(svg)))

    def test_no_text_is_refused(self):
        """A banner without text cannot silently pass geometry validation."""
        self.assertEqual(check_banner_clearance('<svg><path d="M80 0"/></svg>'), ["SVG: no text elements"])

    def test_no_paths_is_refused(self):
        """A banner without wave paths cannot establish clearance."""
        self.assertEqual(check_banner_clearance('<svg><text x="0" font-size="10">a</text></svg>'),
                         ["SVG: no wave paths"])

    def test_missing_x_is_refused(self):
        """Missing text x produces a contextual geometry error."""
        svg = '<svg><text font-size="10">a</text><path d="M80 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg), ["a: missing or invalid x or font-size"])

    def test_missing_font_size_is_refused(self):
        """Missing text and group font-size produces a contextual error."""
        svg = '<svg><text x="0">a</text><path d="M80 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg), ["a: missing or invalid x or font-size"])

    def test_path_control_points_contribute_to_minimum(self):
        """A curve control point left of the move point constrains clearance."""
        svg = '<svg><text x="0" font-size="10">abc</text><path d="M80 0 C53 0 90 0 100 0"/></svg>'
        self.assertEqual(len(check_banner_clearance(svg, advance=1)), 1)

    def test_text_content_is_stripped(self):
        """Outer whitespace does not add to the estimated text width."""
        svg = '<svg><text x="0" font-size="10"> abc </text><path d="M54 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_oversized_svg_is_refused(self):
        """Input larger than the scalar byte bound is refused before parsing."""
        self.assertEqual(check_banner_clearance(" " * (MAX_SVG_BYTES + 1)),
                         [f"SVG: more than {MAX_SVG_BYTES} bytes"])

    def test_group_nesting_is_bounded(self):
        """Group inheritance refuses nesting beyond the scalar depth limit."""
        self.assertIn("group nesting exceeds", " ".join(check_banner_clearance("<g>" * (MAX_SVG_DEPTH + 1))))
