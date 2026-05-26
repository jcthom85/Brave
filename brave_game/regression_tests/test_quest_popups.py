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
BRAVE_PROFILE_PATH = REPO_ROOT / "brave_game/commands/brave_profile.py"


class QuestPopupTests(unittest.TestCase):
    def test_default_out_wires_new_and_completed_quest_popups(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var renderQuestOverlay = function (payload, options)", default_out_source)
        self.assertIn("var pendingQuestOverlayQueue = [];", default_out_source)
        self.assertIn("var currentQuestOverlay = null;", default_out_source)
        self.assertIn("var isQuestOverlayQueueReady = function ()", default_out_source)
        self.assertIn("var processQuestOverlayQueue = function ()", default_out_source)
        self.assertIn("pendingQuestOverlayQueue.push({ payload: payload, options: options || {} });", default_out_source)
        self.assertIn("body.getAttribute(\"data-brave-scene\") === \"explore\"", default_out_source)
        self.assertIn("&& !body.classList.contains(\"brave-picker-active\")", default_out_source)
        self.assertIn("&& !body.classList.contains(\"brave-combat-return-active\")", default_out_source)
        self.assertIn("&& !body.classList.contains(\"brave-activity-active\")", default_out_source)
        self.assertIn("&& !body.classList.contains(\"brave-fishing-active\")", default_out_source)
        self.assertIn("&& !body.classList.contains(\"brave-movie-active\")", default_out_source)
        self.assertIn("&& !currentQuestOverlay", default_out_source)
        self.assertIn("&& !document.querySelector(\".brave-quest-complete-overlay\")", default_out_source)
        self.assertIn('renderQuestOverlay(payload, { eyebrow: "Quest Complete", sound: "success" });', default_out_source)
        self.assertIn('renderQuestOverlay(payload, { eyebrow: "New Quest", sound: "select" });', default_out_source)
        self.assertIn('if (cmdname === "brave_quest_started")', default_out_source)
        self.assertIn('overlay.addEventListener("click", dismissOverlay);', default_out_source)
        self.assertIn('if (payload.next_step) rewardItems.push({ label: "Lead", value: payload.next_step });', default_out_source)
        self.assertIn("scheduleQuestOverlayQueueCheck(80);", default_out_source)

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
        self.assertIn(".brave-view__entry[data-brave-picker]", default_out_source)
        self.assertIn(".brave-view__action[data-brave-picker]", default_out_source)
        self.assertIn(".brave-view__action[data-brave-command]", default_out_source)
        self.assertIn("var handleBrowserInteractionEvent = function (event)", default_out_source)
        self.assertIn("claimBrowserInteractionEvent(event);", default_out_source)
        self.assertIn("[data-brave-command], [data-brave-prefill], [data-brave-picker], [data-brave-connection-screen], [data-brave-combat-tab]", default_out_source)
        self.assertIn('var pickerTarget = closestFromEventTarget(event, "[data-brave-picker]");', default_out_source)
        self.assertIn('openPickerFromTarget(pickerTarget);', default_out_source)
        self.assertIn("var renderPickerChip = function (entry)", default_out_source)
        self.assertIn("pickerChips.map(renderPickerChip).join(\"\")", default_out_source)
        self.assertIn("var renderPickerQuantityControl = function (control)", default_out_source)
        self.assertIn("var titleItemRarityClass = pickerData && pickerData.rarity_tone && pickerData.rarity_target === \"title_item\"", default_out_source)
        self.assertIn("var titleMarkup = pickerData && pickerData.title_item", default_out_source)
        self.assertIn('data-brave-picker-quantity-adjust', default_out_source)
        self.assertIn('data-brave-picker-quantity-confirm', default_out_source)
        self.assertIn('sendBrowserCommand(quantityConfirmTarget.getAttribute("data-brave-picker-quantity-command"));', default_out_source)

        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")
        self.assertIn(".brave-picker-quantity__stepper", css_source)
        self.assertIn(".brave-picker-quantity__confirm", css_source)

    def test_welcome_popup_clears_intro_veil(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var introVeilFailsafeTimer = null;", default_out_source)
        self.assertIn("introVeilFailsafeTimer = window.setTimeout(function () {", default_out_source)
        self.assertIn("finishGameIntroVeil();", default_out_source)
        self.assertIn(
            "var renderWelcomePage = function () {\n"
            "        var host = document.getElementById(\"brave-objectives-sheet\");\n"
            "        if (!host || !currentWelcomePages.length) {\n"
            "            return;\n"
            "        }\n"
            "        finishGameIntroVeil();",
            default_out_source,
        )
        self.assertIn('var ctaLabel = isLast ? (page.cta_label || "Begin Adventure") : "Next";', default_out_source)
        self.assertIn("+ escapeHtml(ctaLabel)", default_out_source)
        self.assertIn("var shouldRenderGuidanceAfterWelcome = !active && currentWelcomePages.length > 0;", default_out_source)
        self.assertIn("renderObjectives(currentViewData);", default_out_source)

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

    def test_tutorial_objectives_overlay_has_no_manual_close_button(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertNotIn("aria-label='Close objectives'", default_out_source)
        self.assertNotIn("brave-objectives-sheet__close-mark", default_out_source)
        self.assertNotIn("brave-objectives-sheet__close-label", default_out_source)
        self.assertNotIn("Close Guide", default_out_source)

    def test_combat_without_guidance_preserves_visible_tutorial_overlay(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("viewData.variant === \"combat\"", default_out_source)
        self.assertIn("host.classList.contains(\"brave-objectives-sheet--tutorial\")", default_out_source)
        self.assertIn("document.body.classList.contains(\"brave-objectives-active\")", default_out_source)
        self.assertIn("host.setAttribute(\"aria-hidden\", \"false\");", default_out_source)

    def test_tutorial_overlay_does_not_steal_combat_action_clicks(self):
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "body[data-brave-scene=\"combat\"] #brave-objectives-sheet.brave-objectives-sheet--tutorial .brave-objectives-sheet__panel",
            css_source,
        )
        self.assertIn("pointer-events: none;", css_source)

    def test_tutorial_shimmer_targets_vicinity_name_and_inline_action_not_whole_card(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'var shimmerClass = entry && checkCommandShimmer(entry.command) ? " brave-shimmer" : "";',
            default_out_source,
        )
        self.assertIn(
            'if (shouldShimmer && !hasInlineActions) {\n'
            '                        rowClass += " brave-shimmer";\n'
            '                    }',
            default_out_source,
        )
        self.assertIn(
            'var primaryClass = "brave-view__list-primary brave-click brave-click--row" + (shouldShimmer ? " brave-shimmer" : "");',
            default_out_source,
        )

    def test_tutorial_menu_shimmer_does_not_light_scene_rail_cards(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'if (element.closest("#scene-card, #scene-pack-panel")) {\n'
            '                element.classList.remove("brave-shimmer");\n'
            '                return;\n'
            '            }\n'
            '            if (element.closest("#scene-vicinity-panel") && !element.classList.contains("brave-room-actions__button")) {\n'
            '                element.classList.remove("brave-shimmer");\n'
            '                return;\n'
            '            }',
            default_out_source,
        )
        self.assertIn('button.classList.toggle("brave-shimmer", hasShimmeringMenuOption);', default_out_source)
        self.assertIn('var shimmerClass = (option && option.command && checkCommandShimmer(option.command)) ? " brave-shimmer" : "";', default_out_source)

    def test_tutorial_shimmer_lights_room_action_buttons_in_vicinity_rail(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var shouldShimmer = checkCommandShimmer(action.command);", default_out_source)
        self.assertIn(
            'var buttonClass = "brave-room-actions__button brave-click" + (shouldShimmer ? " brave-shimmer" : "");',
            default_out_source,
        )

    def test_desktop_menu_gap_matches_scene_rail_column_gap(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn('getPropertyValue("--brave-rail-gap")', default_out_source)
        self.assertIn("var center = railRect.left - railGapValue - buttonWidth;", default_out_source)

    def test_journal_popup_refreshes_when_quest_state_changes(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn('if (cmdname === "brave_journal_update")', default_out_source)
        self.assertIn('currentMenuViewOverlayData && String(currentMenuViewOverlayData.variant || "") === "journal"', default_out_source)
        self.assertIn("renderMainView(journalView || {});", default_out_source)
        self.assertIn('var menuViewAttr = (entry && isMenuViewCommand(entry.command)) ? " data-brave-menu-view-command=\'1\'" : "";', default_out_source)

    def test_picker_options_honor_explicit_tutorial_shimmer_payloads(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'var shimmerClass = ((option && option.shimmer) || (option && option.command && checkCommandShimmer(option.command))) ? " brave-shimmer" : "";',
            default_out_source,
        )

    def test_tutorial_objective_refresh_updates_tracked_card_while_menu_overlay_is_open(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "|| (currentMenuViewOverlayData && currentRoomViewData && isRoomLikeView(currentRoomViewData))",
            default_out_source,
        )
        self.assertIn('if (menuViewOverlaySceneRailSnapshot) {', default_out_source)
        self.assertIn('menuViewOverlaySceneRailSnapshot["scene-card"] = {', default_out_source)

    def test_pack_and_gear_mark_tutorial_progress_before_rendering_views(self):
        source = BRAVE_PROFILE_PATH.read_text(encoding="utf-8")

        gear_method = source[source.index("    def _render_gear"):source.index("    def _resolve_slot")]
        self.assertLess(
            gear_method.index('record_command_event(character, "gear")'),
            gear_method.index("build_gear_view(character"),
        )

        pack_method = source[source.index("class CmdPack"):source.index("class CmdCompanion")]
        self.assertLess(
            pack_method.index('record_command_event(character, "pack")'),
            pack_method.index("build_pack_view(character)"),
        )


if __name__ == "__main__":
    unittest.main()
