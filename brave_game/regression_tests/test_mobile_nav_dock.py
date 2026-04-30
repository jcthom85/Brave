import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_out.js"


class MobileNavDockTests(unittest.TestCase):
    def test_mobile_movement_pad_defaults_expanded(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var mobileNavDockExpanded = true;", default_out_source)
        self.assertNotIn("mobileNavDockExpanded = false;\n            if (typeof clearMobileNavDock", default_out_source)


if __name__ == "__main__":
    unittest.main()
