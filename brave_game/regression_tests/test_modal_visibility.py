from playwright.sync_api import sync_playwright

from regression_tests.live_opening_harness import (
    BASE_URL,
    assert_lanternfall_opening_visible,
    create_fresh_character,
)
from regression_tests.ui_contract_fixtures import build_room_fixture, build_room_scene_fixture, combat_scenarios


def seed_room_view(page):
    room = build_room_fixture(version=1)
    scene = build_room_scene_fixture(version=1)
    page.goto(f"{BASE_URL}/webclient/test", wait_until="networkidle")
    page.wait_for_function("() => !!(window.plugins && window.plugins.defaultout && window.plugin_handler)", timeout=15000)
    page.evaluate(
        """({ room, scene }) => {
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
            window.plugin_handler.onSend = (cmd) => { window.__sent.push(cmd); };
        }""",
        {"room": room, "scene": scene},
    )
    page.wait_for_selector(".brave-view--room", state="visible", timeout=10000)


def seed_combat_view(page):
    combat = combat_scenarios()["solo_regular"]
    page.goto(f"{BASE_URL}/webclient/test", wait_until="networkidle")
    page.wait_for_function("() => !!(window.plugins && window.plugins.defaultout && window.plugin_handler)", timeout=15000)
    page.evaluate(
        """(combat) => {
            const plugin = window.plugins.defaultout;
            plugin.onUnknownCmd("brave_clear_all", [], { brave_clear_all: {} });
            plugin.onUnknownCmd("brave_view", [], { brave_view: combat });
            window.__sent = [];
            window.plugin_handler.onSend = (cmd) => { window.__sent.push(cmd); };
        }""",
        combat,
    )
    page.wait_for_selector(".brave-view--combat", state="visible", timeout=10000)


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


def test_victory_continue_suppresses_raw_return_look_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            seed_combat_view(page)
            victory = {
                "variant": "combat-result",
                "title": "VICTORY!",
                "sections": [{"label": "Rewards", "kind": "lines", "lines": ["XP +1"]}],
                "reactive": {"scene": "victory"},
            }
            page.evaluate(
                """(victory) => {
                    window.plugins.defaultout.onUnknownCmd("brave_view", [], { brave_view: victory });
                }""",
                victory,
            )
            page.wait_for_selector("#brave-victory-transition", state="visible", timeout=10000)
            page.locator("[data-brave-victory-continue]").click()
            page.wait_for_function("() => (window.__sent || []).includes('look')", timeout=10000)
            page.evaluate(
                """() => {
                    const plugin = window.plugins.defaultout;
                    plugin.onText(["look"], { cls: "inp" });
                    plugin.onText(["Yard Commons\\nExits: north"], { cls: "out", type: "look" });
                }"""
            )
            leaked = page.evaluate(
                """() => {
                    const mwin = document.getElementById("messagewindow");
                    return {
                        text: mwin ? mwin.textContent : "",
                        strayCount: mwin ? mwin.querySelectorAll(":scope > .out, :scope > .inp").length : -1,
                    };
                }"""
            )
            assert "Yard Commons" not in leaked["text"]
            assert leaked["strayCount"] == 0
        finally:
            browser.close()


def test_desktop_scene_menu_pulls_down_when_gutter_fits():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1000})
        try:
            seed_room_view(page)
            page.wait_for_function(
                """() => {
                    const rail = document.getElementById("scene-rail")?.getBoundingClientRect();
                    const room = document.querySelector("#messagewindow > .brave-view--room")?.getBoundingClientRect();
                    const menu = document.querySelector(".brave-view__menu-button")?.getBoundingClientRect();
                    if (!rail || !room || !menu) return false;
                    const railGap = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--brave-rail-gap"));
                    return menu.left > room.right && Math.abs((rail.left - menu.right) - railGap) <= 1;
                }""",
                timeout=10000,
            )
            placement = page.evaluate(
                """() => {
                    const rail = document.getElementById("scene-rail").getBoundingClientRect();
                    const room = document.querySelector("#messagewindow > .brave-view--room").getBoundingClientRect();
                    const menu = document.querySelector(".brave-view__menu-button").getBoundingClientRect();
                    return {
                        menuLeft: menu.left,
                        menuRight: menu.right,
                        roomRight: room.right,
                        railLeft: rail.left,
                    };
                }"""
            )
            assert placement["menuLeft"] > placement["roomRight"]
            rail_gap = page.evaluate('parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--brave-rail-gap"))')
            assert abs((placement["railLeft"] - placement["menuRight"]) - rail_gap) <= 1
            page.locator(".brave-view__menu-button").click()
            page.wait_for_selector(
                "#brave-desktop-scene-menu.brave-desktop-scene-menu--open .brave-desktop-scene-menu__panel",
                state="visible",
                timeout=10000,
            )
            assert page.locator("#brave-picker-sheet[aria-hidden='false']").count() == 0
            page.get_by_role("menuitem", name="Gear").click()
            page.wait_for_function("() => (window.__sent || []).includes('gear')", timeout=10000)
        finally:
            browser.close()


def test_desktop_scene_menu_falls_back_to_picker_when_gutter_is_tight():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1180, "height": 900})
        try:
            seed_room_view(page)
            page.locator(".brave-view__menu-button").click()
            page.wait_for_selector("#brave-picker-sheet[aria-hidden='false']", state="visible", timeout=10000)
            assert page.locator("#brave-desktop-scene-menu.brave-desktop-scene-menu--open").count() == 0
        finally:
            browser.close()


def test_desktop_scene_menu_hides_behind_readable_picker():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1000})
        try:
            seed_room_view(page)
            page.wait_for_selector("#brave-desktop-scene-menu[aria-hidden='false']", state="visible", timeout=10000)
            before = page.evaluate(
                """() => {
                    const menu = document.getElementById("brave-desktop-scene-menu");
                    return {
                        left: menu ? menu.style.left : null,
                        top: menu ? menu.style.top : null,
                    };
                }"""
            )
            assert before["left"]
            assert before["top"]
            page.evaluate(
                """() => {
                    const readable = Array.from(document.querySelectorAll("[data-brave-picker]"))
                        .find((node) => (node.getAttribute("data-brave-picker") || "").includes("Kitchen Hearth"));
                    if (!readable) throw new Error("Readable picker target not found");
                    readable.click();
                }"""
            )
            page.wait_for_selector("#brave-picker-sheet[aria-hidden='false']", state="visible", timeout=10000)
            state = page.evaluate(
                """() => {
                    const menu = document.getElementById("brave-desktop-scene-menu");
                    const picker = document.getElementById("brave-picker-sheet");
                    return {
                        menuAriaHidden: menu ? menu.getAttribute("aria-hidden") : null,
                        menuDisplay: menu ? getComputedStyle(menu).display : null,
                        menuLeft: menu ? menu.style.left : null,
                        menuTop: menu ? menu.style.top : null,
                        menuHit: document.elementFromPoint(
                            menu.getBoundingClientRect().left + 4,
                            menu.getBoundingClientRect().top + 4
                        )?.closest("#brave-desktop-scene-menu") !== null,
                        pickerDisplay: picker ? getComputedStyle(picker).display : null,
                    };
                }"""
            )
            assert state["pickerDisplay"] == "block"
            assert state["menuAriaHidden"] == "true"
            assert state["menuDisplay"] == "none"
            assert state["menuLeft"] == before["left"]
            assert state["menuTop"] == before["top"]
            assert state["menuHit"] is False
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

            overlay_state = page.evaluate(
                """() => ({
                    scene: document.body.getAttribute("data-brave-scene"),
                    sceneCardText: document.getElementById("scene-card")?.innerText || "",
                    packPanelText: document.getElementById("scene-pack-panel")?.innerText || "",
                    roomStillMounted: !!document.querySelector("#messagewindow .brave-view--room"),
                    menuAriaHidden: document.getElementById("brave-desktop-scene-menu")?.getAttribute("aria-hidden") || null,
                    menuDisplay: document.getElementById("brave-desktop-scene-menu")
                        ? getComputedStyle(document.getElementById("brave-desktop-scene-menu")).display
                        : null,
                    menuObstructed: (() => {
                        const menu = document.getElementById("brave-desktop-scene-menu");
                        if (!menu) return false;
                        const rect = menu.getBoundingClientRect();
                        return document.elementFromPoint(
                            rect.left + Math.min(8, Math.max(1, rect.width / 2)),
                            rect.top + Math.min(8, Math.max(1, rect.height / 2))
                        )?.closest("#brave-menu-view-overlay") !== null;
                    })(),
                })"""
            )
            assert overlay_state["scene"] == "explore"
            assert overlay_state["roomStillMounted"] is True
            assert "First Watch" in overlay_state["sceneCardText"]
            assert "Innkeeper's Fish Pie" in overlay_state["packPanelText"]
            assert overlay_state["menuAriaHidden"] == "false"
            assert overlay_state["menuDisplay"] != "none"
            assert overlay_state["menuObstructed"] is True

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
