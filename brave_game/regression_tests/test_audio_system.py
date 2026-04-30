import json
from pathlib import Path
import unittest


REPO_ROOT = Path("/home/jcthom85/Brave")
AUDIO_ROOT = REPO_ROOT / "brave_game/web/static/webclient/audio"
MANIFEST_PATH = AUDIO_ROOT / "manifest.json"
AUDIO_JS_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/brave_audio.js"
WEBCLIENT_TEMPLATE_PATH = REPO_ROOT / "brave_game/web/templates/webclient/webclient.html"
DEFAULT_OUT_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_out.js"
ATTRIBUTION_PATH = AUDIO_ROOT / "ATTRIBUTION.md"


class AudioSystemFilesTests(unittest.TestCase):
    def test_manifest_defines_required_buses_and_core_cues(self):
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(1, payload.get("version"))
        self.assertEqual(
            {"master", "ambience", "music", "sfx"},
            set(payload.get("buses", {}).keys()),
        )

        cues = payload.get("cues", {})
        for cue_id in (
            "ambience.brambleford",
            "music.explore.safe",
            "music.title",
            "music.rest",
            "music.combat.standard",
            "music.combat.boss",
            "sfx.ui.click",
            "sfx.combat.hit.melee",
            "sfx.combat.heal",
            "sfx.portal.warp",
        ):
            self.assertIn(cue_id, cues)

    def test_manifest_file_backed_assets_exist(self):
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertTrue(ATTRIBUTION_PATH.exists())

        for cue_id, cue in payload.get("cues", {}).items():
            for relative_path in cue.get("files", []):
                asset_path = AUDIO_ROOT / relative_path
                self.assertTrue(
                    asset_path.exists(),
                    f"{cue_id} references missing asset {relative_path}",
                )

    def test_audio_runtime_exports_director_api(self):
        source = AUDIO_JS_PATH.read_text(encoding="utf-8")

        for snippet in (
            "window.BraveAudio = {",
            "init: init",
            "unlock: unlock",
            "setReactiveState: setReactiveState",
            "handleCombatFx: handleCombatFx",
            "handleNotice: handleNotice",
            "handleRest: handleRest",
            "handleRoomActivity: handleRoomActivity",
            "setSetting: setSetting",
            "function loadAudioBuffer(assetPath)",
            "function playFileCue(cue, cueId, options)",
            'return "music.title";',
        ):
            self.assertIn(snippet, source)

    def test_webclient_template_and_menu_wire_audio_ui(self):
        template_source = WEBCLIENT_TEMPLATE_PATH.read_text(encoding="utf-8")
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("BRAVE_AUDIO_MANIFEST_URL", template_source)
        self.assertIn("webclient/js/brave_audio.js", template_source)
        self.assertIn("?v=20260429a", template_source)
        self.assertIn("brave-intro-veil", template_source)
        self.assertIn("clearIntroVeil", template_source)
        self.assertIn("buildSettingsPicker", default_out_source)
        self.assertIn("buildVideoSettingsPicker", default_out_source)
        self.assertIn("buildAudioSettingsPicker", default_out_source)
        self.assertIn('{ label: "Settings", icon: "settings", picker: buildSettingsPicker() }', default_out_source)
        self.assertIn('{ label: "Video", icon: "tv", picker: buildVideoSettingsPicker() }', default_out_source)
        self.assertIn('{ label: "Audio", icon: "graphic_eq", picker: buildAudioSettingsPicker() }', default_out_source)

    def test_default_out_wires_desktop_movement_hotkeys(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        for snippet in (
            "var getDesktopMovementCommands = function () {",
            "var handleDesktopMovementHotkey = function (event) {",
            'if (key === "arrowup" || key === "w") {',
            'command = commands.up || "";',
            'command = commands.down || "";',
            'document.addEventListener("keydown", function (event) {',
        ):
            self.assertIn(snippet, default_out_source)

    def test_default_out_wires_video_settings_controls(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        for snippet in (
            "var DEFAULT_VIDEO_SETTINGS = {",
            "var applyVideoSettings = function (settings, options) {",
            "var renderVideoSettingsPickerMarkup = function (pickerData, panelClass, backdropClass, panelStyle) {",
            "data-brave-video-action='fullscreen'",
            "data-brave-video-toggle='reduced_motion'",
            "data-brave-video-setting='ui_scale'",
            'pickerData.picker_kind === "video-settings"',
        ):
            self.assertIn(snippet, default_out_source)


if __name__ == "__main__":
    unittest.main()
