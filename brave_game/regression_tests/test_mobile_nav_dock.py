import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_out.js"
CSS_PATH = REPO_ROOT / "brave_game/web/static/webclient/css/brave_webclient.css"


class MobileNavDockTests(unittest.TestCase):
    def test_mobile_movement_pad_defaults_expanded(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var mobileNavDockExpanded = true;", default_out_source)
        self.assertNotIn("mobileNavDockExpanded = false;\n            if (typeof clearMobileNavDock", default_out_source)

    def test_tutorial_objectives_do_not_hide_mobile_nav_dock(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")
        css_source = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("var mobileObjectivesExpanded = false;", default_out_source)
        self.assertIn('body.classList.contains("brave-objectives-welcome-active")', default_out_source)
        self.assertNotIn('document.body.classList.contains("brave-objectives-active")) {\n            dock.innerHTML = "";', default_out_source)
        self.assertIn("data-brave-objectives-expand='1'", default_out_source)
        self.assertIn('host.classList.add("brave-objectives-sheet--welcome");', default_out_source)
        self.assertNotIn('host.classList.add("brave-objectives-sheet--tutorial", "brave-objectives-sheet--welcome");', default_out_source)
        self.assertIn(".brave-objectives-sheet--mobile-collapsed", css_source)
        self.assertNotIn("body.brave-objectives-active #mobile-nav-dock", css_source)
        self.assertIn("#brave-objectives-sheet[aria-hidden=\"true\"]", css_source)


if __name__ == "__main__":
    unittest.main()
