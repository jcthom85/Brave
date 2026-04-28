import os
import unittest
from pathlib import Path

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_out.js"
WEBCLIENT_CSS_PATH = REPO_ROOT / "brave_game/web/static/webclient/css/brave_webclient.css"


class QuestPopupTests(unittest.TestCase):
    def test_default_out_wires_new_and_completed_quest_popups(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var renderQuestOverlay = function (payload, options)", default_out_source)
        self.assertIn('renderQuestOverlay(payload, { eyebrow: "Quest Complete", sound: "success" });', default_out_source)
        self.assertIn('renderQuestOverlay(payload, { eyebrow: "New Quest", sound: "select" });', default_out_source)
        self.assertIn('if (cmdname === "brave_quest_started")', default_out_source)
        self.assertIn('overlay.addEventListener("click", dismissOverlay);', default_out_source)
        self.assertIn('if (payload.next_step) rewardItems.push({ label: "Lead", value: payload.next_step });', default_out_source)

    def test_default_out_wires_rest_overlay(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var renderRestOverlay = function (payload)", default_out_source)
        self.assertIn('if (cmdname === "brave_rest")', default_out_source)
        self.assertIn('overlay.className = "brave-rest-overlay";', default_out_source)
        self.assertIn('braveAudio.handleRest(payload);', default_out_source)
        self.assertIn('overlay.addEventListener("click", dismissOverlay);', default_out_source)

    def test_quest_popup_overlay_accepts_clicks_for_dismissal(self):
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".brave-quest-complete-overlay {", css_source)
        self.assertIn("pointer-events: auto;", css_source)
        self.assertIn("cursor: pointer;", css_source)

    def test_rest_overlay_styles_full_screen_animation(self):
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".brave-rest-overlay {", css_source)
        self.assertIn(".brave-rest-overlay__moon", css_source)
        self.assertIn("@keyframes brave-rest-meter-fill", css_source)

    def test_menu_surfaces_stack_above_tutorial_objectives(self):
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("#brave-objectives-sheet {\n    position: fixed;\n    inset: 0;\n    z-index: 5010;", css_source)
        self.assertIn("#brave-picker-sheet {\n    position: fixed;\n    inset: 0;\n    z-index: 5030;", css_source)
        self.assertIn("z-index: 5020;\n        pointer-events: none;", css_source)
        self.assertIn("z-index: 5025;\n        pointer-events: none;", css_source)
        self.assertIn("body.brave-objectives-welcome-active #brave-picker-sheet", css_source)
        self.assertIn("body.brave-objectives-welcome-active #mobile-nav-dock", css_source)
        self.assertIn("body.brave-objectives-welcome-active #mobile-utility-sheet", css_source)

    def test_tutorial_overlay_icons_have_frontend_mappings(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        for snippet in (
            '"help_outline": "help"',
            '"monitor_heart": "hearts"',
            '"my_location": "targeted"',
            '"groups": "double-team"',
        ):
            self.assertIn(snippet, default_out_source)


if __name__ == "__main__":
    unittest.main()
