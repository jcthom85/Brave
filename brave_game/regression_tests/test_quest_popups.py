import os
import unittest
from pathlib import Path

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_out.js"
WEBCLIENT_CSS_PATH = REPO_ROOT / "brave_game/web/static/webclient/css/brave_webclient.css"
AUDIO_JS_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/brave_audio.js"


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

    def test_default_out_opens_server_sent_picker_payloads(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn('if (cmdname === "brave_picker")', default_out_source)
        self.assertIn('openPickerSheet(getOobPayload(args, kwargs, "brave_picker", {}) || {});', default_out_source)
        self.assertIn("var interactive = !!(item && (item.command || item.picker || item.prefill || item.connection_screen));", default_out_source)
        self.assertIn("var attrs = interactive ? commandAttrs(item, false) : \"\";", default_out_source)
        self.assertIn('var directPointerPicker = !!(directTarget && directTarget.hasAttribute("data-brave-picker"));', default_out_source)
        self.assertIn('&& !(event.pointerType === "mouse" && directPointerPicker)', default_out_source)
        self.assertIn('var pickerTarget = event.target.closest("[data-brave-picker]");', default_out_source)
        self.assertIn('openPickerFromTarget(pickerTarget);', default_out_source)
        self.assertIn("var renderPickerChip = function (entry)", default_out_source)
        self.assertIn("pickerChips.map(renderPickerChip).join(\"\")", default_out_source)

    def test_welcome_popup_clears_intro_veil(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var introVeilFailsafeTimer = null;", default_out_source)
        self.assertIn("introVeilFailsafeTimer = window.setTimeout(finishGameIntroVeil, 8000);", default_out_source)
        self.assertIn(
            "var renderWelcomePage = function () {\n"
            "        var host = document.getElementById(\"brave-objectives-sheet\");\n"
            "        if (!host || !currentWelcomePages.length) {\n"
            "            return;\n"
            "        }\n"
            "        finishGameIntroVeil();",
            default_out_source,
        )

    def test_room_activity_speech_does_not_spawn_mobile_voice_toast(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "var shouldToastActivity = function (entry) {\n"
            "        return false;\n"
            "    };",
            default_out_source,
        )
        self.assertNotIn('return "Voices";', default_out_source)
        self.assertIn(
            "if (!braveGameLoaded && isRoomLikeView(viewData)) {\n"
            "                braveGameLoaded = true;\n"
            "                finishGameIntroVeil();",
            default_out_source,
        )

    def test_character_load_veil_holds_intermediate_account_views(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var isCharacterLoadHoldingView = function (viewData)", default_out_source)
        self.assertIn("viewData.variant === \"account\"", default_out_source)
        self.assertIn("viewData.variant === \"character-select\"", default_out_source)
        self.assertIn(
            "if (isCharacterLoadHoldingView(viewData)) {\n"
            "            return;\n"
            "        }",
            default_out_source,
        )

    def test_quest_popup_overlay_accepts_clicks_for_dismissal(self):
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".brave-quest-complete-overlay {", css_source)
        self.assertIn("pointer-events: auto;", css_source)
        self.assertIn("cursor: pointer;", css_source)

    def test_intro_veil_does_not_block_early_audio_interactions(self):
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")
        audio_source = AUDIO_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("#brave-intro-veil.brave-intro-veil--active {", css_source)
        self.assertIn("pointer-events: none;", css_source)
        self.assertIn("playback blocked pending unlock", audio_source)
        self.assertIn("playCueInternal(cueId, cue, options);", audio_source)

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

    def test_mobile_vicinity_inline_actions_are_icon_only(self):
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("@media screen and (max-width: 640px)", css_source)
        self.assertIn(".brave-view--room .brave-view__section--vicinity .brave-view__mini-action span:not(.brave-view__mini-action-icon):not(.brave-icon)", css_source)
        self.assertIn("min-width: 2.35rem;", css_source)

    def test_tutorial_close_button_uses_short_label_and_accent_colors(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('icon("close", "brave-objectives-sheet__close-icon")\n            + "<span>Close</span>"', default_out_source)
        self.assertNotIn("Close Guide", default_out_source)
        self.assertIn("background: rgba(var(--brave-obj-accent-rgb), 0.08);", css_source)
        self.assertIn("border: 1px solid rgba(var(--brave-obj-accent-rgb), 0.22);", css_source)
        self.assertIn("color: color-mix(in srgb, var(--brave-obj-accent) 74%, var(--brave-text-soft));", css_source)
        self.assertIn(".brave-objectives-sheet__close-icon {\n    color: inherit;\n}", css_source)


if __name__ == "__main__":
    unittest.main()
