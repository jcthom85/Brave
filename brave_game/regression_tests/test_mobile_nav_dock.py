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
        self.assertIn("brave-objectives-sheet__backdrop brave-objectives-sheet__backdrop--welcome'></div>", default_out_source)
        self.assertNotIn("brave-objectives-sheet__backdrop--welcome' data-brave-objectives-toggle", default_out_source)
        self.assertNotIn('host.classList.add("brave-objectives-sheet--tutorial", "brave-objectives-sheet--welcome");', default_out_source)
        self.assertIn(".brave-objectives-sheet--mobile-collapsed", css_source)
        self.assertIn("#brave-objectives-sheet.brave-objectives-sheet--tutorial {\n    z-index: 5040;", css_source)
        self.assertNotIn("body.brave-objectives-active #mobile-nav-dock", css_source)
        self.assertIn("#brave-objectives-sheet[aria-hidden=\"true\"]", css_source)

    def test_tutorial_objective_updates_refresh_menu_shimmer(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")
        css_source = CSS_PATH.read_text(encoding="utf-8")
        room_card_start = default_out_source.index("var heroSceneMarkup =")
        room_card_end = default_out_source.index("var viewMarkup =", room_card_start)
        room_card_markup = default_out_source[room_card_start:room_card_end]

        self.assertIn("var refreshTutorialShimmerControls = function ()", default_out_source)
        self.assertIn('document.querySelectorAll(".brave-view__menu-button")', default_out_source)
        self.assertIn("button.classList.toggle(\"brave-shimmer\", hasShimmeringMenuOption);", default_out_source)
        self.assertIn("refreshTutorialShimmerControls();", default_out_source)
        self.assertIn("var renderDesktopSceneMenu = function ()", default_out_source)
        self.assertIn("buildDesktopMenuButtonMarkup();", default_out_source)
        self.assertIn("data-brave-desktop-scene-menu-toggle='1'", default_out_source)
        self.assertIn("var openDesktopSceneMenuPanel = function ()", default_out_source)
        self.assertIn(".brave-desktop-scene-menu--open .brave-desktop-scene-menu__panel", css_source)
        self.assertNotIn("renderDesktopMenuAction()", room_card_markup)

    def test_menu_view_commands_open_large_overlay(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")
        css_source = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("var currentMenuViewOverlayData = null;", default_out_source)
        self.assertIn("var MENU_VIEW_COMMANDS = {", default_out_source)
        self.assertIn("data-brave-menu-view-command='1'", default_out_source)
        self.assertIn("var menuViewAttr = (option && isMenuViewCommand(option.command))", default_out_source)
        self.assertIn("pendingMenuViewCommandUntil = Date.now() + 10000;", default_out_source)
        self.assertIn("var shouldRenderMenuViewOverlay = function (viewData)", default_out_source)
        self.assertIn("renderMenuViewOverlay(viewData, viewMarkup);", default_out_source)
        self.assertIn("target.closest(\"#brave-menu-view-overlay\")", default_out_source)
        self.assertIn("var closeMenuViewOverlayFromTarget = function (target)", default_out_source)
        self.assertIn("var captureMenuViewOverlaySceneRail = function ()", default_out_source)
        self.assertIn("var restoreMenuViewOverlaySceneRail = function ()", default_out_source)
        self.assertIn("if (isMenuViewOverlayOpeningOrActive())", default_out_source)
        self.assertIn("isMenuViewOverlayOpeningOrActive() && !isCombatPanelData(panelPayload || {})", default_out_source)
        self.assertIn("clearMenuViewOverlay();", default_out_source)
        self.assertIn("picker_id: \"quit-menu\"", default_out_source)
        self.assertIn("large: true", default_out_source)
        self.assertIn(".brave-menu-view-overlay", css_source)
        self.assertIn(".brave-menu-view-overlay__panel > .brave-view", css_source)
        self.assertIn("body.brave-menu-view-overlay-active #brave-picker-sheet", css_source)
        self.assertIn(".brave-picker-sheet__panel--large-menu", css_source)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", css_source)

    def test_first_room_discovery_paints_room_text_without_region_transition(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")
        css_source = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("var shouldAnimateFirstRoomDiscoverySceneCard = !!(", default_out_source)
        self.assertIn("viewData.first_room_discovery", default_out_source)
        self.assertIn("!shouldAnimateRegionSceneCard", default_out_source)
        self.assertIn('brave-view__room-scene-card--first-room-discovery', default_out_source)
        self.assertIn("@keyframes brave-room-first-room-title-paint", css_source)
        self.assertIn("@keyframes brave-room-first-room-copy-paint", css_source)

    def test_mobile_room_navigation_suppresses_parent_scroll_jumps(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn("var node = target && target.nodeType === 9 ? target.scrollingElement : target;", default_out_source)
        self.assertIn("node === document.scrollingElement", default_out_source)
        self.assertIn("node === document.documentElement", default_out_source)
        self.assertIn("node === document.body", default_out_source)
        self.assertIn('node.classList.contains("brave-gl-main-item")', default_out_source)
        self.assertIn('node.classList.contains("lm_content")', default_out_source)
        self.assertIn('node.classList.contains("content")', default_out_source)

    def test_tutorial_overlay_preserves_mobile_viewport_scroll(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "var scrollSnapshots = typeof captureMainScrollPositions === \"function\" ? captureMainScrollPositions() : null;\n"
            "        if (isMobileViewport()) {\n"
            "            blurActiveUiControl();\n"
            "            suppressMobileNonInputFocus(900);\n"
            "        }",
            default_out_source,
        )
        self.assertIn("window: true,", default_out_source)
        self.assertIn("top: window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0,", default_out_source)
        self.assertIn("window.scrollTo(entry.left || 0, entry.top || 0);", default_out_source)


if __name__ == "__main__":
    unittest.main()
