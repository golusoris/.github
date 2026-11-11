"""Banner text stays clear of the decorative waves, including planted defects."""

import re
import unittest

from .repo_checks import (
    MAX_SVG_BYTES,
    MAX_SVG_DEPTH,
    ROOT,
    SVG_NUMBER,
    _wave_start,
    check_banner_clearance,
)


class BannerClearanceTest(unittest.TestCase):
    """Exercise real banner geometry and the clearance boundary."""

    def setUp(self):
        """Read the real banner for positive and planted negative checks."""
        self.svg = (ROOT / "profile/golusoris-readme-banner.svg").read_text(encoding="utf-8")

    def test_real_banner_has_clearance(self):
        """Every text element in the published banner clears the wave."""
        self.assertEqual(check_banner_clearance(self.svg), [])

    def test_nested_svg_viewport_is_refused(self):
        """A subtitle viewport cannot shift both lines into the wave unnoticed."""
        svg = self.svg.replace(
            '<g font-family=',
            '<svg viewBox="-500 0 1200 120" width="1200" height="120"><g font-family=', 1,
        ).replace("  </g>\n</svg>", "  </g></svg>\n</svg>")
        self.assertIn("svg: nested or second svg element unsupported", check_banner_clearance(svg))

    def test_second_svg_root_is_refused(self):
        """Closing the root does not permit a second SVG viewport."""
        self.assertIn("svg: nested or second svg element unsupported",
                      check_banner_clearance(self.svg + "<svg/>"))

    def test_non_svg_first_element_is_refused(self):
        """An otherwise supported group cannot precede or replace the SVG root."""
        # Two first-element boundaries, both below MAX_SVG_BYTES.
        for svg in ("<g></g>" + self.svg, self.svg.replace("<svg ", "<g ", 1)):
            with self.subTest(svg=svg[:80]):
                self.assertIn("svg: first element must be svg", check_banner_clearance(svg))

    def test_root_viewbox_scaling_preserves_clearance(self):
        """One root viewport scales waves and text in the same user units."""
        svg = self.svg.replace('viewBox="0 0 1200 120"', 'viewBox="-500 0 2400 240"')
        self.assertEqual(check_banner_clearance("<!-- banner -->\n" + svg), [])

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
                self.assertEqual(check_banner_clearance(svg), [f"{tag.lower()}: transform is unsupported"])

    def test_root_inherited_geometry_is_refused(self):
        """Root CSS and inherited font metrics cannot evade attribute checks."""
        # Three planted attributes; each input remains below MAX_SVG_BYTES.
        for attribute in ('style="letter-spacing:20px"', 'font-size="40"',
                          'letter-spacing="20"'):
            with self.subTest(attribute=attribute):
                svg = self.svg.replace('<svg ', f'<svg {attribute} ', 1)
                name = attribute.split("=", 1)[0]
                self.assertEqual(check_banner_clearance(svg), [f"svg: unsupported attribute {name}"])

    def test_decorative_element_attributes_are_refused(self):
        """Every non-text element refuses an attribute outside its exact set."""
        # Six allowed tags, including the zero-attribute title/desc boundary.
        for tag in ("defs", "linearGradient", "stop", "rect", "title", "desc"):
            with self.subTest(tag=tag):
                svg = self.svg.replace("</svg>", f'<{tag} style="font-size:40px"/></svg>')
                self.assertEqual(check_banner_clearance(svg),
                                 [f"{tag.lower()}: unsupported attribute style"])

    def test_attribute_free_title_and_description_pass(self):
        """Zero attributes remain valid for descriptive SVG elements."""
        svg = self.svg.replace("</svg>", "<title>Banner</title><desc>Waves</desc></svg>")
        self.assertEqual(check_banner_clearance(svg), [])

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

    def test_smooth_reflected_control_bounds_wave(self):
        """A smooth cubic includes its implicit reflected first control point."""
        path = "M800 76 C800 76 1200 76 800 76 S800 76 800 76"
        self.assertEqual(_wave_start(path), 400)

    def test_smooth_reflection_refuses_subtitle_overlap(self):
        """A reflected point left of explicit coordinates constrains subtitles."""
        svg = ('<svg><text x="350" font-size="14">Subtitle</text>'
               '<path d="M800 76 C800 76 1200 76 800 76 S800 76 800 76"/></svg>')
        self.assertEqual(check_banner_clearance(svg), [
            "Subtitle: right edge 419.4 within 24 of wave start 400.0",
        ])

    def test_smooth_without_cubic_uses_current_point(self):
        """M and L reset smooth reflection to the current point."""
        # Two previous-command boundaries.
        for path in ("M800 0 S900 0 1000 0",
                     "M800 0 C800 0 1200 0 800 0 L800 0 S900 0 1000 0"):
            with self.subTest(path=path):
                self.assertEqual(_wave_start(path), 800)

    def test_implicit_path_segments_update_reflection(self):
        """Repeated M, C and S groups obey segment and reflection semantics."""
        cases = {
            "M900 0 800 0 S900 0 1000 0": 800,
            "M800 0 C800 0 800 0 800 0 800 0 1200 0 800 0 S800 0 800 0": 400,
            "M800 0 S1200 0 800 0 800 0 800 0": 400,
        }
        # Three finite command sequences, bounded by their token counts.
        for path, minimum in cases.items():
            with self.subTest(path=path):
                self.assertEqual(_wave_start(path), minimum)

    def test_incomplete_path_segments_are_refused(self):
        """Even coordinate counts cannot hide incomplete cubic segments."""
        # Eight malformed command and numeric boundaries.
        for path in ("M800 0 C900 0", "M800 0 S900 0", "M800 0 C",
                     "800 0", "L800 0", "M800 0 M", "M800", "M1e999 0"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "wave path:"):
                _wave_start(path)

    def test_real_banner_smooth_controls_keep_minimum(self):
        """All three real reflections equal 1042.6 and preserve x=800."""
        paths = re.findall(r'<path d="([^"]+)"', self.svg)
        self.assertEqual(len(paths), 3)
        # Exactly three paths in the published banner.
        for path in paths:
            with self.subTest(path=path):
                segment = path.split("C", 1)[1].split("S", 1)[0]
                # A cubic segment has exactly six explicit coordinates.
                coordinates = [float(number) for number in SVG_NUMBER.findall(segment)]
                self.assertEqual(len(coordinates), 6)
                self.assertAlmostEqual(2 * coordinates[-2] - coordinates[-4], 1042.6)
                self.assertEqual(_wave_start(path), 800)

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
