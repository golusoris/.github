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

    def test_unmodeled_elements_are_refused(self):
        """A use copy or a text path could place glyphs the model never reads."""
        planted = {
            "use": '<use href="#t" x="500"/>',
            "textpath": '<text x="0" font-size="10"><textPath href="#p">abc</textPath></text>',
        }
        for tag, element in planted.items():
            with self.subTest(tag=tag):
                svg = self.svg.replace("</svg>", element + "</svg>", 1)
                self.assertIn(f"{tag}: unsupported element", check_banner_clearance(svg))

    def test_group_transform_is_refused(self):
        """A translated subtitle group cannot silently move text geometry."""
        svg = self.svg.replace('<g font-family=', '<g transform="translate(500 0)" font-family=', 1)
        self.assertEqual(check_banner_clearance(svg), ["g: transform is unsupported"])

    def test_path_transform_is_refused(self):
        """A translated path cannot silently move the wave boundary."""
        svg = self.svg.replace('<path d=', '<path transform="translate(-500 0)" d=', 1)
        self.assertIn("path: transform is unsupported", check_banner_clearance(svg))

    def test_other_element_transforms_are_refused(self):
        """Transforms are refused even on elements outside the allow-list."""
        for tag in ("svg", "defs", "linearGradient", "stop", "rect"):
            with self.subTest(tag=tag):
                svg = self.svg.replace(f"<{tag}", f'<{tag} transform="translate(500 0)"', 1)
                self.assertIn(f"{tag.lower()}: transform is unsupported", check_banner_clearance(svg))

    def test_supported_opacity_attributes_pass(self):
        """Decorative opacity attributes do not change text clearance."""
        svg = ('<svg><g opacity="0.5"><text x="0" font-size="10" opacity="0.5">'
               'a<tspan fill="red" opacity="0.5">bc</tspan></text></g>'
               '<path d="M54 0" fill-opacity="0.5" stroke-opacity="0.5"/></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_text_anchor_is_refused(self):
        """Text anchoring cannot silently shift the estimated right edge."""
        svg = self.svg.replace('<text x=', '<text text-anchor="end" x=', 1)
        self.assertIn("text: unsupported attribute text-anchor", check_banner_clearance(svg))

    def test_tspan_position_is_refused(self):
        """An independently positioned tspan cannot silently move glyphs."""
        svg = self.svg.replace('<tspan fill=', '<tspan x="500" fill=', 1)
        self.assertIn("tspan: unsupported attribute x", check_banner_clearance(svg))

    def test_text_style_is_refused(self):
        """Inline CSS cannot override the font-size used for clearance."""
        svg = self.svg.replace('<text x=', '<text style="font-size:40px" x=', 1)
        self.assertIn("text: unsupported attribute style", check_banner_clearance(svg))

    def test_group_letter_spacing_is_refused(self):
        """Letter-spacing inheritance is refused instead of ignored."""
        svg = self.svg.replace('<g font-family=', '<g letter-spacing="2" font-family=', 1)
        self.assertIn("g: unsupported attribute letter-spacing", check_banner_clearance(svg))

    def test_unsupported_attributes_are_sorted_and_geometry_collected(self):
        """All unsupported attributes and a clearance error are reported."""
        svg = ('<svg><text x="0" font-size="10" textLength="20" dx="2">abc</text>'
               '<path d="M50 0"/></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [
            "text: unsupported attribute dx",
            "text: unsupported attribute textlength",
            "abc: right edge 30.0 within 24 of wave start 50.0",
        ])

    def test_letter_spacing_exact_margin_passes(self):
        """Positive spacing counts once per glyph at the exact margin."""
        svg = '<svg><text x="0" font-size="10" letter-spacing="1">abc</text><path d="M57 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_letter_spacing_one_unit_inside_margin_fails(self):
        """Positive spacing moves the right edge one unit into the margin."""
        svg = '<svg><text x="0" font-size="10" letter-spacing="1">abc</text><path d="M56 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [
            "abc: right edge 33.0 within 24 of wave start 56.0",
        ])

    def test_negative_letter_spacing_passes(self):
        """Negative spacing narrows the text to the exact clearance boundary."""
        svg = '<svg><text x="0" font-size="10" letter-spacing="-1">abc</text><path d="M51 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_invalid_letter_spacing_is_refused(self):
        """Non-numeric and non-finite spacing produce contextual errors."""
        for spacing in ("wide", "nan", "inf", "-inf", "1e999", ""):
            with self.subTest(spacing=spacing):
                svg = (f'<svg><text x="0" font-size="10" letter-spacing="{spacing}">abc</text>'
                       '<path d="M80 0"/></svg>')
                self.assertEqual(check_banner_clearance(svg), ["abc: invalid letter-spacing"])

    def test_valueless_letter_spacing_is_refused(self):
        """A present letter-spacing attribute requires a numeric value."""
        svg = '<svg><text x="0" font-size="10" letter-spacing>abc</text><path d="M80 0"/></svg>'
        self.assertEqual(check_banner_clearance(svg), ["abc: invalid letter-spacing"])

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
