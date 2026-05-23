from playwright.sync_api import sync_playwright

from regression_tests.live_opening_harness import (
    BASE_URL,
    assert_lanternfall_opening_visible,
    create_fresh_character,
)
from regression_tests.ui_contract_fixtures import build_room_fixture, build_room_scene_fixture


def test_welcome_modal_visibility():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        page = context.new_page()
        try:
            create_fresh_character(page)
            assert_lanternfall_opening_visible(page, screenshot_name="mobile_welcome_modal.png")
        finally:
            browser.close()


def test_menu_overlay_close_preserves_exploration_and_nested_picker_stacks_above():
    room = build_room_fixture(version=1)
    scene = build_room_scene_fixture(version=1)
    gear_view = {
        "variant": "gear",
        "title": "Gear",
        "title_icon": "shield",
        "back_action": {"label": "Close", "command": "look", "icon": "close", "tone": "muted", "aria_label": "Close"},
        "sections": [{
            "label": "",
            "icon": "shield",
            "kind": "entries",
            "hide_label": True,
            "variant": "slots",
            "items": [{
                "title": "Trinket",
                "meta": "Wayfarer Clasp",
                "icon": "diamond",
                "picker": {
                    "picker_id": "gear-trinket",
                    "picker_kind": "gear-slot",
                    "title": "Trinket",
                    "subtitle": "Wayfarer Clasp",
                    "options": [{"label": "Unequip Wayfarer Clasp", "icon": "remove_circle", "command": "gear unequip trinket"}],
                },
            }],
        }],
        "reactive": {"scene": "equipment"},
    }
    gear_panel = {"eyebrow": "Gear", "title": "Gear Panel", "sections": [{"label": "Debug", "items": [{"text": "Do not replace scene rail"}]}]}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(f"{BASE_URL}/webclient/test", wait_until="networkidle")
            page.wait_for_function("() => !!(window.plugins && window.plugins.defaultout && window.plugin_handler)", timeout=15000)
            page.evaluate(
                """({ room, scene, gearView, gearPanel }) => {
                    const plugin = window.plugins.defaultout;
                    const emit = (cmd, payload) => {
                        const kwargs = {};
                        kwargs[cmd] = payload;
                        plugin.onUnknownCmd(cmd, [], kwargs);
                    };
                    plugin.onUnknownCmd("brave_clear_all", [], { brave_clear_all: {} });
                    emit("brave_view", room);
                    emit("brave_scene", scene);
                    window.__sent = [];
                    window.plugin_handler.onSend = (cmd) => {
                        window.__sent.push(cmd);
                        if (cmd === "gear") {
                            emit("brave_clear", {});
                            emit("brave_panel", gearPanel);
                            emit("brave_view", gearView);
                        } else if (cmd === "look") {
                            emit("brave_clear", {});
                            emit("brave_view", room);
                            emit("brave_scene", scene);
                        }
                    };
                }""",
                {"room": room, "scene": scene, "gearView": gear_view, "gearPanel": gear_panel},
            )

            page.wait_for_selector(".brave-view--room", state="visible", timeout=10000)
            page.locator(".brave-view__menu-button").click()
            page.get_by_text("Gear", exact=True).click()
            page.wait_for_selector("#brave-menu-view-overlay .brave-view--gear", state="visible", timeout=10000)

            page.locator("#brave-menu-view-overlay .brave-view__entry").first.click()
            page.wait_for_selector("#brave-picker-sheet[aria-hidden='false']", state="visible", timeout=10000)
            top_text = page.evaluate(
                "() => document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2).textContent"
            )
            assert "Unequip Wayfarer Clasp" in top_text

            page.locator("#brave-picker-sheet .brave-picker-sheet__close").click()
            page.locator("#brave-menu-view-overlay .brave-view__back").click()
            page.wait_for_timeout(300)

            state = page.evaluate(
                """() => ({
                    sent: window.__sent || [],
                    scene: document.body.getAttribute("data-brave-scene"),
                    overlayOpen: !!document.getElementById("brave-menu-view-overlay"),
                    mainChildren: Array.from(document.querySelectorAll("#messagewindow > *")).map((node) => node.className || node.id || node.tagName),
                    sceneCardText: document.getElementById("scene-card")?.innerText || "",
                    packPanelText: document.getElementById("scene-pack-panel")?.innerText || "",
                })"""
            )
            assert "look" not in state["sent"]
            assert state["scene"] == "explore"
            assert state["overlayOpen"] is False
            assert state["mainChildren"] == ["brave-view brave-view--room brave-view--tone-safe"]
            assert "First Watch" in state["sceneCardText"]
            assert "Innkeeper's Fish Pie" in state["packPanelText"]
        finally:
            browser.close()


if __name__ == "__main__":
    test_welcome_modal_visibility()
