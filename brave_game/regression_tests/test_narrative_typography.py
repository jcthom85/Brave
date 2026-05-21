from pathlib import Path
import unittest


CSS_PATH = Path(__file__).resolve().parents[1] / "web/static/webclient/css/brave_webclient.css"
DEFAULT_OUT_PATH = Path(__file__).resolve().parents[1] / "web/static/webclient/js/plugins/default_out.js"


def _css_block(source, selector):
    start = source.index(selector + " {")
    body_start = source.index("{", start) + 1
    body_end = source.index("}", body_start)
    return source[body_start:body_end]


class NarrativeTypographyTests(unittest.TestCase):
    def test_narrative_typography_uses_readable_font_channel(self):
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("--brave-narrative-font-family:", css)
        self.assertIn("--brave-narrative-letter-spacing:", css)
        self.assertIn('--brave-narrative-font-family: Georgia, "Times New Roman", serif;', css)

        picker_body = _css_block(css, ".brave-picker-sheet__bodyline")
        self.assertIn("font-family: var(--brave-narrative-font-family);", picker_body)
        self.assertIn("letter-spacing: var(--brave-narrative-letter-spacing);", picker_body)
        self.assertIn("font-size: calc(1.14rem * var(--brave-text-scale) * var(--brave-font-size-scale));", picker_body)
        self.assertIn("line-height: 1.58;", picker_body)

        room_description = _css_block(css, ".brave-view--room .brave-view__subtitle")
        self.assertIn("font-size: calc(1.16rem * var(--brave-text-scale) * var(--brave-font-size-scale));", room_description)
        self.assertIn("line-height: 1.62;", room_description)

        mobile_intro = _css_block(css, ".brave-mobile-sheet__empty--intro")
        self.assertIn("font-family: var(--brave-narrative-font-family);", mobile_intro)
        self.assertIn("font-size: calc(0.98rem * var(--brave-text-scale) * var(--brave-font-size-scale));", mobile_intro)
        self.assertIn("line-height: 1.55;", mobile_intro)

    def test_body_text_pickers_do_not_render_as_compact_popovers(self):
        source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("&& currentPickerAnchorRect\n            && !pickerBody.length", source)


if __name__ == "__main__":
    unittest.main()
