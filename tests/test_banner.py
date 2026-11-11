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

START_TAG_ERROR = "start tag must use exact attribute names with double-quoted values"


class BannerClearanceTest(unittest.TestCase):
    """Exercise real banner geometry and the clearance boundary."""

    def setUp(self):
        """Read the real banner for positive and planted negative checks."""
        self.svg = (ROOT / "profile/golusoris-readme-banner.svg").read_text(encoding="utf-8")

    def test_real_banner_has_clearance(self):
        """Every text element in the published banner clears the wave."""
        self.assertEqual(check_banner_clearance(self.svg), [])

    def test_non_svg_letter_spacing_is_refused(self):
        """Python numeric extensions cannot hide an overlapping subtitle."""
        subtitle = "Composable fx modules \u00b7 Zero-dependency clients"
        # Four invalid spellings; each fixture stays below MAX_SVG_BYTES.
        for spacing in ("-2_0", "-\uff12\uff10", " -20", "-20px"):
            with self.subTest(spacing=spacing):
                svg = self.svg.replace('<text x="350" y="76"',
                                       f'<text x="560" y="76" letter-spacing="{spacing}"')
                self.assertIn(f"{subtitle}: invalid letter-spacing", check_banner_clearance(svg))

    def test_non_svg_font_size_is_refused(self):
        """Underscores and Unicode digits cannot supply the title font size."""
        # Two invalid spellings; each fixture stays below MAX_SVG_BYTES.
        for size in ("5_6", "\uff15\uff16"):
            with self.subTest(size=size):
                svg = self.svg.replace('font-size="56"', f'font-size="{size}"')
                self.assertIn("golusoris.: missing or invalid x or font-size",
                              check_banner_clearance(svg))

    def test_non_svg_x_is_refused(self):
        """Underscores, Unicode digits and trailing dots cannot position text."""
        # Three invalid spellings; each fixture stays below MAX_SVG_BYTES.
        for x in ("3_50", "\uff13\uff15\uff10", "800."):
            with self.subTest(x=x):
                svg = self.svg.replace('x="44"', f'x="{x}"', 1)
                self.assertIn("golusoris.: missing or invalid x or font-size",
                              check_banner_clearance(svg))

    def test_unicode_stroke_width_is_refused(self):
        """A fullwidth digit cannot supply a wave's stroke width."""
        svg = self.svg.replace('stroke-width="14"', 'stroke-width="\uff12"', 1)
        self.assertIn("path: stroke-width must be a finite nonnegative plain number",
                      check_banner_clearance(svg))

    def test_non_svg_path_numbers_are_refused(self):
        """A single fullwidth digit or trailing dot invalidates a wave path."""
        # Two invalid spellings; each fixture stays below MAX_SVG_BYTES.
        for number in ("\uff1800", "800."):
            with self.subTest(number=number):
                svg = self.svg.replace("M800", f"M{number}", 1)
                self.assertIn("wave path: only absolute M, C, S and L commands supported",
                              check_banner_clearance(svg))

    def test_plain_svg_text_numbers_pass(self):
        """Signed, exponent and decimal text numbers preserve clear geometry."""
        # Six valid spellings across the three text geometry attributes.
        for original, replacement in (
            ('x="44"', 'x="+350"'), ('x="44"', 'x="3.5e2"'),
            ('font-size="56"', 'font-size="56.0"'),
            ('font-size="56"', 'font-size="5.6e1"'),
            ('letter-spacing="-1"', 'letter-spacing="-.5"'),
            ('letter-spacing="-1"', 'letter-spacing=".5"'),
        ):
            with self.subTest(replacement=replacement):
                self.assertEqual(check_banner_clearance(
                    self.svg.replace(original, replacement, 1)), [])

    def test_plain_svg_wave_numbers_pass(self):
        """Signed, exponent and decimal wave numbers keep the banner clear."""
        # Seven valid spellings across path coordinates and stroke widths.
        for original, replacement in (
            ("M800", "M+800"), ("M800", "M8e2"), ("M800", "M800.0"),
            ("M800", "M.8e3"), ('stroke-width="14"', 'stroke-width="0"'),
            ('stroke-width="14"', 'stroke-width="+2"'),
            ('stroke-width="14"', 'stroke-width="2.5e0"'),
        ):
            with self.subTest(replacement=replacement):
                self.assertEqual(check_banner_clearance(
                    self.svg.replace(original, replacement, 1)), [])

    def test_shadowed_uppercase_x_is_refused(self):
        """XML x cannot be hidden behind HTMLParser's case-folded X value."""
        svg = self.svg.replace('<text x="44"', '<text x="800" X="44"', 1)
        self.assertIn("text: start tag must use exact attribute names with double-quoted values",
                      check_banner_clearance(svg))

    def test_mixed_case_stroke_join_is_refused(self):
        """An XML-ignored join attribute cannot authorize the round envelope."""
        svg = self.svg.replace('stroke-linejoin="round"', 'Stroke-linejoin="round"', 1)
        self.assertIn("g: start tag must use exact attribute names with double-quoted values",
                      check_banner_clearance(svg))

    def test_noncanonical_element_case_is_refused(self):
        """Every allowed element requires its canonical SVG spelling."""
        # Two element-name boundaries: ordinary lowercase and canonical camelCase.
        for original, planted, tag in (("text", "Text", "text"),
                                       ("linearGradient", "lineargradient", "lineargradient")):
            with self.subTest(planted=planted):
                svg = self.svg.replace(f"<{original}", f"<{planted}", 1)
                self.assertIn(
                    f"{tag}: start tag must use exact attribute names with double-quoted values",
                    check_banner_clearance(svg),
                )

    def test_lowercase_viewbox_is_refused(self):
        """HTMLParser's lowercase viewbox spelling is not a valid SVG viewBox."""
        svg = self.svg.replace("viewBox=", "viewbox=", 1)
        self.assertIn("svg: start tag must use exact attribute names with double-quoted values",
                      check_banner_clearance(svg))

    def test_non_double_quoted_values_are_refused(self):
        """Single-quoted and bare values cannot enter the exact start-tag grammar."""
        # Two alternate quoting forms; each fixture remains below MAX_SVG_BYTES.
        for attribute in ("x='44'", "x=44"):
            with self.subTest(attribute=attribute):
                svg = self.svg.replace('x="44"', attribute, 1)
                self.assertIn(
                    "text: start tag must use exact attribute names with double-quoted values",
                    check_banner_clearance(svg),
                )

    def test_duplicate_attribute_is_refused(self):
        """XML rejects a repeated x even when both values agree."""
        svg = self.svg.replace('<text x="44"', '<text x="44" x="44"', 1)
        self.assertEqual(check_banner_clearance(svg), ["text: duplicate attribute x"])

    def test_canonical_start_tag_whitespace_passes(self):
        """Canonical names accept multiline spacing and both empty-tag forms."""
        svg = self.svg.replace(' x="44"', '\n\t x="44"', 1).replace('/>', ' />')
        self.assertEqual(check_banner_clearance(svg), [])

    def test_start_tag_grammar_variants_are_refused(self):
        """Namespaces, unknown names and malformed values fail the exact grammar."""
        attributes = ('xmlns:extra="urn:example"', 'xml:space="preserve"',
                      'unknown="value"', 'fill="<red"', 'x ="44"', 'x= "44"')
        # len(attributes) bounds the grammar matrix below MAX_SVG_BYTES.
        for attribute in attributes:
            with self.subTest(attribute=attribute):
                svg = self.svg.replace('<text x="44"', f'<text {attribute}', 1)
                self.assertIn(f"text: {START_TAG_ERROR}", check_banner_clearance(svg))

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
        self.assertEqual(check_banner_clearance(svg),
                         [f"g: {START_TAG_ERROR}", "g: transform is unsupported"])

    def test_path_transform_is_refused(self):
        """A translated path cannot silently move the wave boundary."""
        svg = self.svg.replace('<path d=', '<path transform="translate(-500 0)" d=', 1)
        self.assertIn("path: transform is unsupported", check_banner_clearance(svg))

    def test_other_element_transforms_are_refused(self):
        """Transforms are refused even on elements outside the allow-list."""
        for tag in ("svg", "defs", "linearGradient", "stop", "rect"):
            with self.subTest(tag=tag):
                svg = self.svg.replace(f"<{tag}", f'<{tag} transform="translate(500 0)"', 1)
                self.assertEqual(check_banner_clearance(svg),
                                 [f"{tag.lower()}: {START_TAG_ERROR}",
                                  f"{tag.lower()}: transform is unsupported"])

    def test_root_inherited_geometry_is_refused(self):
        """Root CSS and inherited font metrics cannot evade attribute checks."""
        # Three planted attributes; each input remains below MAX_SVG_BYTES.
        for attribute in ('style="letter-spacing:20px"', 'font-size="40"',
                          'letter-spacing="20"'):
            with self.subTest(attribute=attribute):
                svg = self.svg.replace('<svg ', f'<svg {attribute} ', 1)
                name = attribute.split("=", 1)[0]
                self.assertEqual(check_banner_clearance(svg),
                                 [f"svg: {START_TAG_ERROR}", f"svg: unsupported attribute {name}"])

    def test_decorative_element_attributes_are_refused(self):
        """Every non-text element refuses an attribute outside its exact set."""
        # Six allowed tags, including the zero-attribute title/desc boundary.
        for tag in ("defs", "linearGradient", "stop", "rect", "title", "desc"):
            with self.subTest(tag=tag):
                svg = self.svg.replace("</svg>", f'<{tag} style="font-size:40px"/></svg>')
                self.assertEqual(check_banner_clearance(svg),
                                 [f"{tag.lower()}: {START_TAG_ERROR}",
                                  f"{tag.lower()}: unsupported attribute style"])

    def test_attribute_free_title_and_description_pass(self):
        """Zero attributes remain valid for descriptive SVG elements."""
        svg = self.svg.replace("</svg>", "<title>Banner</title><desc>Waves</desc></svg>")
        self.assertEqual(check_banner_clearance(svg), [])

    def test_supported_opacity_attributes_pass(self):
        """Decorative opacity attributes do not change text clearance."""
        svg = ('<svg><g opacity="0.5"><text x="0" font-size="10" opacity="0.5">'
               'a<tspan fill="red" opacity="0.5">bc</tspan></text></g>'
               '<g stroke-linejoin="round"><path stroke-width="0" d="M54 0" fill-opacity="0.5" stroke-opacity="0.5"/></g></svg>')
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
               '<g stroke-linejoin="round"><path stroke-width="0" d="M50 0"/></g></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [
            f"text: {START_TAG_ERROR}",
            "text: unsupported attribute dx",
            "text: unsupported attribute textlength",
            "abc: right edge 30.0 within 24 of wave start 50.0",
        ])

    def test_letter_spacing_exact_margin_passes(self):
        """Positive spacing counts once per glyph at the exact margin."""
        svg = '<svg><text x="0" font-size="10" letter-spacing="1">abc</text><g stroke-linejoin="round"><path stroke-width="0" d="M57 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_letter_spacing_one_unit_inside_margin_fails(self):
        """Positive spacing moves the right edge one unit into the margin."""
        svg = '<svg><text x="0" font-size="10" letter-spacing="1">abc</text><g stroke-linejoin="round"><path stroke-width="0" d="M56 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [
            "abc: right edge 33.0 within 24 of wave start 56.0",
        ])

    def test_negative_letter_spacing_passes(self):
        """Negative spacing narrows the text to the exact clearance boundary."""
        svg = '<svg><text x="0" font-size="10" letter-spacing="-1">abc</text><g stroke-linejoin="round"><path stroke-width="0" d="M52 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_invalid_letter_spacing_is_refused(self):
        """Non-numeric and non-finite spacing produce contextual errors."""
        for spacing in ("wide", "nan", "inf", "-inf", "1e999", ""):
            with self.subTest(spacing=spacing):
                svg = (f'<svg><text x="0" font-size="10" letter-spacing="{spacing}">abc</text>'
                       '<g stroke-linejoin="round"><path stroke-width="0" d="M80 0"/></g></svg>')
                self.assertEqual(check_banner_clearance(svg), ["abc: invalid letter-spacing"])

    def test_valueless_letter_spacing_is_refused(self):
        """A present letter-spacing attribute requires a numeric value."""
        svg = '<svg><text x="0" font-size="10" letter-spacing>abc</text><g stroke-linejoin="round"><path stroke-width="0" d="M80 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg),
                         [f"text: {START_TAG_ERROR}", "abc: invalid letter-spacing"])

    def test_original_wave_start_overlaps_subtitles(self):
        """Moving the waves back to x=700 flags both monospace subtitles."""
        errors = check_banner_clearance(self.svg.replace("M800", "M700"))
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(errors[0].startswith("Foundational Go libraries"), errors)
        self.assertTrue(errors[1].startswith("Composable fx modules"), errors)

    def test_exact_margin_passes(self):
        """A right edge exactly margin units before the path passes."""
        svg = '<svg><text x="0" font-size="10">abc</text><g stroke-linejoin="round"><path stroke-width="0" d="M54 0 L80 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_one_unit_inside_margin_fails(self):
        """A right edge one unit beyond the clearance boundary is refused."""
        svg = '<svg><text x="1" font-size="10">abc</text><g stroke-linejoin="round"><path stroke-width="0" d="M54 0 L80 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [
            "abc: right edge 31.0 within 24 of wave start 54.0",
        ])

    def test_nearest_group_supplies_font_size(self):
        """Nested groups inherit the nearest font-size, including tspan text."""
        svg = ('<svg><g font-size="100"><g font-size="10"><g>'
               '<text x="0">a<tspan>b</tspan>c</text></g></g></g>'
               '<g stroke-linejoin="round"><path stroke-width="0" d="M54 0 L80 0"/></g></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_text_font_size_overrides_group(self):
        """A text element's font-size overrides the enclosing group."""
        svg = ('<svg><g font-size="100"><text x="0" font-size="10">abc</text>'
               '</g><g stroke-linejoin="round"><path stroke-width="0" d="M54 0"/></g></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_relative_commands_are_refused(self):
        """Relative m and c path commands cannot be treated as absolute x."""
        svg = '<svg><text x="0" font-size="10">a</text><g stroke-linejoin="round"><path stroke-width="0" d="m80 0 c1 2 3 4 5 6"/></g></svg>'
        self.assertIn("only absolute M, C, S and L commands", " ".join(check_banner_clearance(svg)))

    def test_other_absolute_commands_are_refused(self):
        """An absolute H command lacks paired x/y coordinates and is refused."""
        svg = '<svg><text x="0" font-size="10">a</text><g stroke-linejoin="round"><path stroke-width="0" d="M80 0 H90"/></g></svg>'
        self.assertIn("only absolute M, C, S and L commands", " ".join(check_banner_clearance(svg)))

    def test_no_text_is_refused(self):
        """A banner without text cannot silently pass geometry validation."""
        self.assertEqual(check_banner_clearance('<svg><g stroke-linejoin="round"><path stroke-width="0" d="M80 0"/></g></svg>'), ["SVG: no text elements"])

    def test_no_paths_is_refused(self):
        """A banner without wave paths cannot establish clearance."""
        self.assertEqual(check_banner_clearance('<svg><text x="0" font-size="10">a</text></svg>'),
                         ["SVG: no wave paths"])

    def test_missing_x_is_refused(self):
        """Missing text x produces a contextual geometry error."""
        svg = '<svg><text font-size="10">a</text><g stroke-linejoin="round"><path stroke-width="0" d="M80 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg), ["a: missing or invalid x or font-size"])

    def test_missing_font_size_is_refused(self):
        """Missing text and group font-size produces a contextual error."""
        svg = '<svg><text x="0">a</text><g stroke-linejoin="round"><path stroke-width="0" d="M80 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg), ["a: missing or invalid x or font-size"])

    def test_path_control_points_contribute_to_minimum(self):
        """A curve control point left of the move point constrains clearance."""
        svg = '<svg><text x="0" font-size="10">abc</text><g stroke-linejoin="round"><path stroke-width="0" d="M80 0 C53 0 90 0 100 0"/></g></svg>'
        self.assertEqual(len(check_banner_clearance(svg, advance=1)), 1)

    def test_smooth_reflected_control_bounds_wave(self):
        """A smooth cubic includes its implicit reflected first control point."""
        path = "M800 76 C800 76 1200 76 800 76 S800 76 800 76"
        self.assertEqual(_wave_start(path), 400)

    def test_smooth_reflection_refuses_subtitle_overlap(self):
        """A reflected point left of explicit coordinates constrains subtitles."""
        svg = ('<svg><text x="350" font-size="14">Subtitle</text>'
               '<g stroke-linejoin="round"><path stroke-width="0" d="M800 76 C800 76 1200 76 800 76 S800 76 800 76"/></g></svg>')
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
        """Outer XML whitespace does not add to the estimated text width."""
        svg = '<svg><text x="0" font-size="10"> abc </text><g stroke-linejoin="round"><path stroke-width="0" d="M54 0"/></g></svg>'
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_oversized_svg_is_refused(self):
        """Input larger than the scalar byte bound is refused before parsing."""
        self.assertEqual(check_banner_clearance(" " * (MAX_SVG_BYTES + 1)),
                         [f"SVG: more than {MAX_SVG_BYTES} bytes"])

    def test_group_nesting_is_bounded(self):
        """Group inheritance refuses nesting beyond the scalar depth limit."""
        self.assertIn("group nesting exceeds", " ".join(check_banner_clearance("<g>" * (MAX_SVG_DEPTH + 1))))

    def test_wide_real_banner_stroke_is_refused(self):
        """The real wave's half-width contributes to its occupied envelope."""
        svg = self.svg.replace('stroke-width="14"', 'stroke-width="140"')
        errors = check_banner_clearance(svg)
        # Diagnostic count is bounded by MAX_SVG_BYTES before parsing.
        self.assertTrue(any("wave start 730.0" in error for error in errors), errors)

    def test_stroke_envelope_boundary(self):
        """A half-width envelope passes at equality and refuses one unit less."""
        svg = ('<svg><text x="0" font-size="10">abc</text>'
               '<g stroke-linejoin="round"><path d="M55 0" stroke-width="2"/></g></svg>')
        self.assertIn("abc: right edge 30.0 within 24 of wave start 53.0",
                      check_banner_clearance(svg.replace("M55", "M54"), advance=1))
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_default_stroke_width_boundary(self):
        """An absent stroke-width defaults to one, including its half-unit edge."""
        svg = ('<svg><text x="0" font-size="10">abc</text>'
               '<g stroke-linejoin="bevel"><path d="M54.5 0"/></g></svg>')
        self.assertIn("abc: right edge 30.0 within 24 of wave start 53.0",
                      check_banner_clearance(svg.replace("M54.5", "M53.5"), advance=1))
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_missing_linejoin_is_refused(self):
        """The default miter join cannot be bounded by a half stroke width."""
        svg = self.svg.replace(' stroke-linejoin="round"', '')
        self.assertIn("path: stroke-linejoin must be round or bevel",
                      check_banner_clearance(svg))

    def test_unbounded_linejoins_are_refused(self):
        """Explicit miter and unknown joins cannot bypass the envelope check."""
        # Two unsupported joins, both below MAX_SVG_BYTES.
        for join in ("miter", "unknown"):
            with self.subTest(join=join):
                svg = self.svg.replace('stroke-linejoin="round"', f'stroke-linejoin="{join}"')
                self.assertIn("path: stroke-linejoin must be round or bevel",
                              check_banner_clearance(svg))

    def test_square_linecap_is_refused(self):
        """A square cap can extend farther than half a stroke width."""
        svg = self.svg.replace('stroke-linecap="round"', 'stroke-linecap="square"')
        self.assertIn("path: stroke-linecap must be absent, butt or round",
                      check_banner_clearance(svg))

    def test_supported_stroke_inheritance_passes(self):
        """Nested groups inherit nearest joins and restore the parent on exit."""
        svg = ('<svg><text x="0" font-size="10">abc</text>'
               '<g stroke-linejoin="round" stroke-linecap="round">'
               '<g stroke-linejoin="bevel" stroke-linecap="butt"><g>'
               '<path d="M55 0" stroke-width="2"/></g></g>'
               '<path d="M55 0" stroke-width="2"/></g></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_nearest_stroke_group_override_is_refused(self):
        """A nested square cap overrides an otherwise supported parent cap."""
        svg = ('<svg><text x="0" font-size="10">abc</text>'
               '<g stroke-linejoin="round" stroke-linecap="round">'
               '<g stroke-linecap="square"><path d="M80 0"/></g></g></svg>')
        self.assertIn("path: stroke-linecap must be absent, butt or round",
                      check_banner_clearance(svg))

    def test_invalid_stroke_width_is_refused(self):
        """Only finite nonnegative plain numbers can bound a stroke."""
        # Seven spellings; diagnostic iterations are bounded by MAX_SVG_BYTES.
        for width in ("wide", "nan", "-1", "1px", "1e999", "", None):
            with self.subTest(width=width):
                attribute = "stroke-width" if width is None else f'stroke-width="{width}"'
                svg = ('<svg><text x="0" font-size="10">abc</text>'
                       f'<g stroke-linejoin="round"><path d="M80 0" {attribute}/></g></svg>')
                self.assertTrue(any("path: stroke-width" in error
                                    for error in check_banner_clearance(svg)))

    def test_cdata_subtitles_are_refused(self):
        """CDATA cannot hide subtitle glyphs where the waves overlap."""
        svg = self.svg.replace("M800", "M700")
        svg = re.sub(r'(<text x="350"[^>]*>)([^<]*)(</text>)',
                     r'\1<![CDATA[\2]]>\3', svg)
        self.assertEqual(check_banner_clearance(svg),
                         ["SVG: CDATA section unsupported"] * 2)

    def test_doctype_entity_is_refused(self):
        """A DOCTYPE cannot introduce text through a declared entity."""
        svg = '<!DOCTYPE svg [<!ENTITY subtitle "Wide subtitle">]>' + self.svg
        svg = svg.replace("Foundational Go libraries", "&subtitle;")
        self.assertIn("SVG: declaration unsupported", check_banner_clearance(svg))

    def test_stylesheet_instruction_is_refused(self):
        """A processing instruction cannot restyle the bounded geometry."""
        svg = '<?xml-stylesheet href="banner.css" type="text/css"?>' + self.svg
        self.assertEqual(check_banner_clearance(svg),
                         ["SVG: processing instruction unsupported"])

    def test_reversed_letter_spacing_is_refused(self):
        """Negative glyph steps leave the first glyph as the rightmost one."""
        svg = ('<svg><text x="800" font-size="14" letter-spacing="-20">abc</text>'
               '<g stroke-linejoin="round"><path d="M800 0" stroke-width="0"/></g></svg>')
        self.assertIn("abc: right edge 808.7 within 24 of wave start 800.0",
                      check_banner_clearance(svg))

    def test_negative_spacing_one_unit_inside_margin_fails(self):
        """The final glyph still occupies its full advance with negative spacing."""
        svg = ('<svg><text x="0" font-size="10" letter-spacing="-1">abc</text>'
               '<g stroke-linejoin="round"><path d="M51 0" stroke-width="0"/></g></svg>')
        self.assertIn("abc: right edge 28.0 within 24 of wave start 51.0",
                      check_banner_clearance(svg, advance=1))

    def test_non_xml_spaces_are_counted(self):
        """Leading and trailing nonbreaking spaces remain occupied advances."""
        # Two Unicode whitespace variants and both text-edge positions.
        for space in ("\u00a0", "\u2003"):
            for text in (space * 3 + "abc", "abc" + space * 3):
                with self.subTest(text=text):
                    svg = (f'<svg><text x="0" font-size="10">{text}</text>'
                           '<g stroke-linejoin="round"><path d="M54 0" stroke-width="0"/></g></svg>')
                    self.assertIn(f"{text}: right edge 60.0 within 24 of wave start 54.0",
                                  check_banner_clearance(svg, advance=1))

    def test_wide_glyph_boundary(self):
        """Wide and fullwidth glyphs occupy two advances, unlike ASCII twins."""
        svg = ('<svg><text x="0" font-size="10">abc</text>'
               '<g stroke-linejoin="round"><path d="M54 0" stroke-width="0"/></g></svg>')
        # W and F width classes each contain three glyphs.
        for text in ("界界界", "\uff41\uff42\uff43"):
            with self.subTest(text=text):
                wide = svg.replace("abc", text)
                self.assertIn(f"{text}: right edge 60.0 within 24 of wave start 54.0",
                              check_banner_clearance(wide, advance=1))
                self.assertEqual(check_banner_clearance(wide.replace("M54", "M84"),
                                                        advance=1), [])
        self.assertEqual(check_banner_clearance(svg, advance=1), [])

    def test_zero_step_spacing_boundary(self):
        """Coincident glyph origins still occupy one complete glyph advance."""
        svg = ('<svg><text x="0" font-size="10" letter-spacing="-10">abc</text>'
               '<g stroke-linejoin="round"><path d="M33 0" stroke-width="0"/></g></svg>')
        self.assertIn("abc: right edge 10.0 within 24 of wave start 33.0",
                      check_banner_clearance(svg, advance=1))
        self.assertEqual(check_banner_clearance(svg.replace("M33", "M34"), advance=1), [])

    def test_wide_negative_spacing_boundary(self):
        """Reversed spacing cannot shrink a single fullwidth glyph's own width."""
        svg = ('<svg><text x="0" font-size="10" letter-spacing="-20">\uff41</text>'
               '<g stroke-linejoin="round"><path d="M43 0" stroke-width="0"/></g></svg>')
        self.assertIn("\uff41: right edge 20.0 within 24 of wave start 43.0",
                      check_banner_clearance(svg, advance=1))
        self.assertEqual(check_banner_clearance(svg.replace("M43", "M44"), advance=1), [])

    def test_empty_text_edge_is_x(self):
        """Empty text has no occupied advance even with positive spacing."""
        svg = ('<svg><text x="0" font-size="10" letter-spacing="20"> \t\n\r</text>'
               '<g stroke-linejoin="round"><path d="M24 0" stroke-width="0"/></g></svg>')
        self.assertEqual(check_banner_clearance(svg, advance=1), [])
