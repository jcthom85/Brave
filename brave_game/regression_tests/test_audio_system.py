import json
from pathlib import Path
import unittest


REPO_ROOT = Path("/home/jcthom85/Brave")
AUDIO_ROOT = REPO_ROOT / "brave_game/web/static/webclient/audio"
MANIFEST_PATH = AUDIO_ROOT / "manifest.json"
AUDIO_JS_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/brave_audio.js"
WEBCLIENT_TEMPLATE_PATH = REPO_ROOT / "brave_game/web/templates/webclient/webclient.html"
WEBCLIENT_BASE_TEMPLATE_PATH = REPO_ROOT / "brave_game/web/templates/webclient/base.html"
DEFAULT_OUT_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_out.js"
DEFAULT_IN_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_in.js"
ATTRIBUTION_PATH = AUDIO_ROOT / "ATTRIBUTION.md"
ELEVENLABS_PLAN_PATH = AUDIO_ROOT / "elevenlabs_plan.json"


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
            "sfx.ui.journal_tab",
            "sfx.inventory.equip",
            "sfx.inventory.unequip",
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

    def test_elevenlabs_generation_plan_targets_known_cues(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        plan = json.loads(ELEVENLABS_PLAN_PATH.read_text(encoding="utf-8"))
        known_cues = set(manifest.get("cues", {}))

        allowed_kinds = {"ambience", "sfx", "music_theme"}
        allowed_batches = {
            "activities",
            "classes",
            "combat_core",
            "enemies",
            "first_hour",
            "music_themes",
            "regional_ambience",
            "ui_feedback",
        }

        self.assertGreaterEqual(plan.get("version", 0), 1)
        self.assertEqual("ElevenLabs", plan.get("provider"))
        self.assertGreaterEqual(len(plan.get("assets", [])), 100)

        asset_ids = set()
        for asset in plan.get("assets", []):
            self.assertNotIn(asset.get("id"), asset_ids)
            asset_ids.add(asset.get("id"))
            self.assertIn(asset.get("kind"), allowed_kinds)
            self.assertIn(asset.get("batch"), allowed_batches)
            self.assertTrue(asset.get("target_cue") or asset.get("proposed_cue"))
            if asset.get("target_cue"):
                self.assertIn(asset.get("target_cue"), known_cues)
            self.assertTrue(asset.get("prompt"))
            self.assertNotIn("in the style of", asset["prompt"].lower())

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
            "play: playCue",
            "setSetting: setSetting",
            "function loadAudioBuffer(assetPath)",
            "function playFileCue(cue, cueId, options)",
            "function chooseAvailableCue(cueIds)",
            "function playFirstCue(cueIds, options)",
            'return chooseAvailableCue(["music.title"]);',
        ):
            self.assertIn(snippet, source)

    def test_webclient_template_and_menu_wire_audio_ui(self):
        template_source = WEBCLIENT_TEMPLATE_PATH.read_text(encoding="utf-8")
        base_template_source = WEBCLIENT_BASE_TEMPLATE_PATH.read_text(encoding="utf-8")
        audio_source = AUDIO_JS_PATH.read_text(encoding="utf-8")
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")
        default_in_source = DEFAULT_IN_PATH.read_text(encoding="utf-8")

        self.assertIn('brave_static_v="20260430x"', base_template_source)
        self.assertIn("BRAVE_AUDIO_MANIFEST_URL", base_template_source)
        self.assertIn("webclient/js/brave_audio.js", base_template_source)
        self.assertLess(
            base_template_source.index("webclient/js/brave_audio.js"),
            base_template_source.index("webclient/js/plugins/default_in.js"),
        )
        self.assertLess(
            base_template_source.index("webclient/js/brave_audio.js"),
            base_template_source.index("webclient/js/plugins/default_out.js"),
        )
        self.assertIn("var getUiSoundForCommand = function (command) {", default_out_source)
        self.assertIn("var playUiSound = function (kind) {", default_out_source)
        self.assertIn('return "";', default_out_source)
        self.assertIn('normalized.indexOf("gear equip ") === 0', default_out_source)
        self.assertIn('normalized.indexOf("gear unequip ") === 0', default_out_source)
        self.assertIn('normalized === "quests active"', default_out_source)
        self.assertIn(' ? "journal_tab"', default_out_source)
        self.assertIn('playUiSound("close");', default_out_source)
        self.assertIn('playUiSound("select");', default_out_source)
        self.assertIn('playUiSound("select");', default_in_source)
        self.assertIn("brave-intro-veil", template_source)
        self.assertIn("clearIntroVeil", template_source)
        self.assertIn("buildSettingsPicker", default_out_source)
        self.assertIn("buildVideoSettingsPicker", default_out_source)
        self.assertIn("buildAudioSettingsPicker", default_out_source)
        self.assertIn('{ label: "Settings", icon: "settings", picker: buildSettingsPicker() }', default_out_source)
        self.assertIn('{ label: "Video", icon: "tv", picker: buildVideoSettingsPicker() }', default_out_source)
        self.assertIn('{ label: "Audio", icon: "graphic_eq", picker: buildAudioSettingsPicker() }', default_out_source)
        self.assertIn('cmdname === "brave_audio_cue"', default_out_source)
        self.assertIn("braveAudioCue.play(audioCueId", default_out_source)
        self.assertIn('transitionReactive.scene = "combat";', default_out_source)
        self.assertIn("isTitleExperienceScene(currentReactiveState", audio_source)

    def test_browser_reactive_state_uses_authored_room_id_for_audio(self):
        import sys
        import types
        from types import SimpleNamespace

        game_root = str(REPO_ROOT / "brave_game")
        if game_root not in sys.path:
            sys.path.insert(0, game_root)

        fake_context = types.ModuleType("world.browser_context")
        fake_context.ENEMY_TEMPLATES = {}
        fake_enemy_icons = types.ModuleType("world.enemy_icons")
        fake_enemy_icons.get_enemy_icon_name = lambda template_key, template: "warning"
        sys.modules.setdefault("world.browser_context", fake_context)
        sys.modules.setdefault("world.enemy_icons", fake_enemy_icons)

        from world.browser_ui import _reactive_view

        room = SimpleNamespace(id=123, db=SimpleNamespace(brave_room_id="brambleford_east_gate"))
        self.assertEqual("brambleford_east_gate", _reactive_view(room, scene="explore")["source_id"])

    def test_east_gate_resolves_to_brambleford_tone_for_music(self):
        import sys
        from types import SimpleNamespace

        game_root = str(REPO_ROOT / "brave_game")
        if game_root not in sys.path:
            sys.path.insert(0, game_root)

        from world.data.world_tones import get_world_tone_key

        east_gate = SimpleNamespace(
            key="East Gate",
            db=SimpleNamespace(
                brave_world="Brave",
                brave_zone="Brambleford",
                brave_map_region="brambleford",
                brave_room_id="brambleford_east_gate",
                brave_portal_hub=False,
            ),
        )
        goblin_road = SimpleNamespace(
            key="Old Fence Line",
            db=SimpleNamespace(
                brave_world="Brave",
                brave_zone="Goblin Road",
                brave_map_region="goblin_road",
                brave_room_id="goblin_road_old_fence_line",
                brave_portal_hub=False,
            ),
        )

        self.assertEqual("brambleford", get_world_tone_key(east_gate))
        self.assertEqual("goblinroad", get_world_tone_key(goblin_road))

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
