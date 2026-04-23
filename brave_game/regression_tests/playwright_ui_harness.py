import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from regression_tests.ui_contract_fixtures import (
    build_room_fixture,
    build_room_scene_fixture,
    combat_scenarios,
)


DEFAULT_BASE_URL = "http://127.0.0.1:4001"
DEFAULT_OUTPUT_DIR = Path("/home/jcthom85/Brave/tmp/playwright-screenshots")


class HarnessFailure(Exception):
    pass


def _page_js_call(page, expression, payload=None):
    return page.evaluate(expression, payload)


def reset_client(page):
    _page_js_call(
        page,
        """() => {
            const plugin = window.plugins.defaultout;
            plugin.onUnknownCmd("brave_clear_all", [], { brave_clear_all: {} });
            return true;
        }""",
    )
    page.wait_for_timeout(50)


def emit_oob(page, cmd, payload):
    _page_js_call(
        page,
        """({ cmd, payload }) => {
            const plugin = window.plugins.defaultout;
            const kwargs = {};
            kwargs[cmd] = payload;
            plugin.onUnknownCmd(cmd, [], kwargs);
            return true;
        }""",
        {"cmd": cmd, "payload": payload},
    )


def emit_text(page, text, *, cls="out", kwargs=None):
    _page_js_call(
        page,
        """({ text, cls, kwargs }) => {
            return window.plugins.defaultout.onText([text], Object.assign({ cls }, kwargs || {}));
        }""",
        {"text": text, "cls": cls, "kwargs": kwargs or {}},
    )


def wait_for_view(page, selector):
    page.wait_for_selector(selector, state="visible", timeout=10000)
    page.wait_for_timeout(80)


def render_room(page, room_view, scene=None):
    reset_client(page)
    emit_oob(page, "brave_view", room_view)
    if scene:
        emit_oob(page, "brave_scene", scene)
    wait_for_view(page, ".brave-view--room")


def render_combat(page, combat_view):
    reset_client(page)
    emit_oob(page, "brave_view", combat_view)
    wait_for_view(page, ".brave-view--combat")


def save_shot(page, output_dir, group, name):
    target_dir = output_dir / group
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def assert_true(condition, message):
    if not condition:
        raise HarnessFailure(message)


def normalized_label(value):
    return " ".join(str(value or "").split()).strip().lower()


def collect_card_metrics(page):
    return _page_js_call(
        page,
        """() => {
            const viewportWidth = window.innerWidth;
            const partyEntries = Array.from(document.querySelectorAll(".brave-view--combat .brave-view__section--party .brave-view__entry"));
            const players = Array.from(document.querySelectorAll(".brave-view--combat .brave-view__section--party .brave-view__entry-cluster"));
            const enemies = Array.from(document.querySelectorAll(".brave-view--combat .brave-view__section--targets .brave-view__entry"));
            const partyEntryMetrics = partyEntries.map((node) => {
                const rect = node.getBoundingClientRect();
                return {
                    title: node.querySelector(".brave-view__entry-title")?.textContent?.trim() || "",
                    width: rect.width,
                    height: rect.height,
                    left: rect.left,
                    right: rect.right,
                };
            });
            const enemyMetrics = enemies.map((node) => {
                const rect = node.getBoundingClientRect();
                return {
                    title: node.querySelector(".brave-view__entry-title")?.textContent?.trim() || "",
                    width: rect.width,
                    height: rect.height,
                    left: rect.left,
                    right: rect.right,
                    className: node.className,
                    borderColor: getComputedStyle(node).borderColor,
                    boxShadow: getComputedStyle(node).boxShadow,
                };
            });
            const playerMetrics = players.map((node) => {
                const root = node.querySelector(".brave-view__entry");
                const sidecar = node.querySelector(".brave-view__entry-sidecar");
                return {
                    title: root?.querySelector(".brave-view__entry-title")?.textContent?.trim() || "",
                    clusterWidth: node.getBoundingClientRect().width,
                    cardHeight: root?.getBoundingClientRect().height || 0,
                    sidecarHeight: sidecar?.getBoundingClientRect().height || 0,
                };
            });
            const actionButtons = Array.from(document.querySelectorAll(".brave-view--combat .brave-view__actions .brave-view__action")).map((node) => {
                const rect = node.getBoundingClientRect();
                return { label: node.textContent.trim(), width: rect.width, height: rect.height };
            });
            const meters = Array.from(document.querySelectorAll(".brave-view--combat .brave-view__meter-label")).map((node) => node.textContent.trim());
            const chips = Array.from(document.querySelectorAll(".brave-view--combat .scene-card__chip")).map((node) => node.textContent.trim());
            return { viewportWidth, partyEntryMetrics, playerMetrics, enemyMetrics, actionButtons, meters, chips };
        }""",
    )


def collect_battle_feed_metrics(page):
    return _page_js_call(
        page,
        """() => {
            const log = document.querySelector(".brave-combat-log");
            const body = document.querySelector(".brave-combat-log__body");
            if (!log || !body) {
                return null;
            }
            const rect = log.getBoundingClientRect();
            return {
                top: rect.top,
                left: rect.left,
                width: rect.width,
                height: rect.height,
                lineCount: body.children.length,
                text: body.innerText,
                scrollTop: body.scrollTop,
                scrollHeight: body.scrollHeight,
                clientHeight: body.clientHeight,
            };
        }""",
    )


def open_mobile_panel(page, trigger_selector, expected_title):
    page.locator(trigger_selector).click()
    page.wait_for_selector("#mobile-utility-sheet .brave-mobile-sheet__panel", state="visible", timeout=5000)
    title = page.locator("#mobile-utility-sheet .brave-mobile-sheet__title").inner_text().strip()
    assert_true(
        normalized_label(title) == normalized_label(expected_title),
        f"Expected mobile panel '{expected_title}', got '{title}'",
    )


def open_mobile_panel_by_key(page, tab_key, expected_title):
    _page_js_call(
        page,
        """({ tabKey }) => {
            const button = document.createElement("button");
            button.type = "button";
            button.setAttribute("data-brave-mobile-panel", tabKey);
            document.body.appendChild(button);
            button.click();
            button.remove();
            return true;
        }""",
        {"tabKey": tab_key},
    )
    page.wait_for_selector("#mobile-utility-sheet .brave-mobile-sheet__panel", state="visible", timeout=5000)
    title = page.locator("#mobile-utility-sheet .brave-mobile-sheet__title").inner_text().strip()
    assert_true(
        normalized_label(title) == normalized_label(expected_title),
        f"Expected mobile panel '{expected_title}', got '{title}'",
    )


def verify_mobile_room_panel_persistence(page, room_v1, room_v2, output_dir, report):
    page.set_viewport_size({"width": 390, "height": 844})
    render_room(page, room_v1, build_room_scene_fixture(version=1))
    panel_checks = [
        ("activity", "[data-brave-mobile-panel='activity']", "Activity"),
        ("nearby", "[data-brave-mobile-panel='nearby']", "Nearby"),
        ("menu", "[data-brave-mobile-panel='menu']", "Menu"),
        ("room", None, "Room"),
        ("character", None, "Character"),
        ("pack", None, "Pack"),
        ("journal", None, "Journal"),
        ("party", None, "Party"),
    ]

    for key, selector, expected_title in panel_checks:
        render_room(page, room_v1, build_room_scene_fixture(version=1))
        if key == "party":
            open_mobile_panel_by_key(page, "party", "Party")
        elif selector is None:
            open_mobile_panel_by_key(page, "quests" if key == "journal" else key, expected_title)
        else:
            open_mobile_panel(page, selector, expected_title)

        emit_oob(page, "brave_scene", build_room_scene_fixture(version=2))
        emit_text(page, "A fresh note reaches the room activity rail.")
        emit_oob(page, "brave_view", room_v2)
        page.wait_for_timeout(120)

        current_title = page.locator("#mobile-utility-sheet .brave-mobile-sheet__title").inner_text().strip()
        assert_true(
            normalized_label(current_title) == normalized_label("Party" if key == "party" else expected_title),
            f"{key} panel did not stay selected after refresh",
        )
        assert_true(page.locator("#mobile-utility-sheet").get_attribute("aria-hidden") == "false", f"{key} sheet collapsed after refresh")
        assert_true(page.locator("#mobile-nav-dock [data-brave-mobile-panel='activity']").count() > 0, "Mobile dock missing after refresh")
        report["screenshots"].append(save_shot(page, output_dir, "mobile-exploration", key))

    render_room(page, room_v1, build_room_scene_fixture(version=1))
    open_mobile_panel(page, "[data-brave-mobile-panel='activity']", "Activity")
    before_count = page.locator("#mobile-utility-sheet .brave-room-log__body--mobile > *").count()
    emit_oob(page, "brave_room_activity", {"text": "Peep checks the doorway.", "cls": "out"})
    emit_oob(page, "brave_view", room_v2)
    page.wait_for_timeout(120)
    after_count = page.locator("#mobile-utility-sheet .brave-room-log__body--mobile > *").count()
    assert_true(after_count > before_count, "Activity panel did not update in place")
    assert_true(
        normalized_label(page.locator("#mobile-utility-sheet .brave-mobile-sheet__title").inner_text()) == "activity",
        "Activity panel dismissed during refresh",
    )

    render_room(page, room_v1, build_room_scene_fixture(version=1))
    open_mobile_panel(page, "[data-brave-mobile-panel='nearby']", "Nearby")
    emit_oob(page, "brave_view", room_v2)
    page.wait_for_timeout(120)
    nearby_text = page.locator("#mobile-utility-sheet").inner_text()
    assert_true("Rook" in nearby_text, "Nearby panel did not refresh in place")
    assert_true(
        normalized_label(page.locator("#mobile-utility-sheet .brave-mobile-sheet__title").inner_text()) == "nearby",
        "Nearby panel dismissed during refresh",
    )


def verify_combat_screens(page, output_dir, report):
    desktop_viewport = {"width": 1440, "height": 1100}
    mobile_viewport = {"width": 390, "height": 844}
    scenarios = combat_scenarios()

    desktop_names = [
        "solo_regular",
        "party_duo",
        "party_trio",
        "party_quad",
        "ranger_companion",
        "elite_enemy",
        "boss_enemy",
        "boss_with_adds",
    ]
    for name in desktop_names:
        page.set_viewport_size(desktop_viewport)
        render_combat(page, scenarios[name])
        report["screenshots"].append(save_shot(page, output_dir, "desktop-combat", name))

    page.set_viewport_size(desktop_viewport)
    render_combat(page, scenarios["solo_regular"])
    before_feed = collect_battle_feed_metrics(page)
    assert_true(before_feed is not None, "Battle feed missing before first action")
    report["screenshots"].append(save_shot(page, output_dir, "desktop-combat", "battle-feed-before-first-action"))
    emit_text(page, "Dad strikes Road Wolf for 7 damage.")
    page.wait_for_timeout(120)
    after_first = collect_battle_feed_metrics(page)
    assert_true(after_first["lineCount"] == before_feed["lineCount"] + 1, "Battle feed did not retain first action")
    assert_true(abs(after_first["top"] - before_feed["top"]) <= 2, "Battle feed jumped after first action")
    report["screenshots"].append(save_shot(page, output_dir, "desktop-combat", "battle-feed-after-first-action"))
    for line in [
        "Road Wolf bites Dad for 3 damage.",
        "Dad uses Strike on Road Wolf.",
        "Road Wolf falls.",
    ]:
        emit_text(page, line)
    page.wait_for_timeout(120)
    after_several = collect_battle_feed_metrics(page)
    assert_true(after_several["lineCount"] >= after_first["lineCount"] + 3, "Battle feed did not persist through several actions")
    report["screenshots"].append(save_shot(page, output_dir, "desktop-combat", "battle-feed-after-several-actions"))

    render_combat(page, scenarios["party_quad"])
    baseline_heights = collect_card_metrics(page)
    party_heights_before = [entry["cardHeight"] for entry in baseline_heights["playerMetrics"]]
    emit_text(page, "Dad strikes Road Wolf for 7 damage.")
    emit_text(page, "Peep casts Bolt.")
    emit_oob(page, "brave_view", scenarios["party_quad"])
    page.wait_for_timeout(160)
    refreshed_heights = collect_card_metrics(page)
    party_heights_after = [entry["cardHeight"] for entry in refreshed_heights["playerMetrics"]]
    assert_true(party_heights_before == party_heights_after, "Combat card sizing changed after action refresh")

    render_combat(page, scenarios["ranger_companion"])
    companion_metrics = collect_card_metrics(page)
    paired = companion_metrics["playerMetrics"][0]
    assert_true(abs(paired["cardHeight"] - paired["sidecarHeight"]) <= 2, "Companion and player card heights drifted apart")

    page.set_viewport_size(mobile_viewport)
    mobile_names = [
        "solo_regular",
        "party_duo",
        "party_trio",
        "party_quad",
        "ranger_companion",
        "elite_enemy",
        "boss_enemy",
        "boss_with_adds",
        "mobile_card_count",
        "elite_vs_regular",
    ]
    for name in mobile_names:
        render_combat(page, scenarios[name])
        report["screenshots"].append(save_shot(page, output_dir, "mobile-combat", name))

    render_combat(page, scenarios["mobile_card_count"])
    mobile_metrics = collect_card_metrics(page)
    assert_true(len(mobile_metrics["partyEntryMetrics"]) == 4, "Expected four player cards on mobile")
    assert_true(len(mobile_metrics["enemyMetrics"]) == 4, "Expected four standard enemy cards on mobile")
    assert_true(
        max(entry["right"] for entry in mobile_metrics["partyEntryMetrics"]) <= mobile_metrics["viewportWidth"] + 2,
        "Four player cards are not visible at once on mobile",
    )
    assert_true(
        max(entry["right"] for entry in mobile_metrics["enemyMetrics"]) <= mobile_metrics["viewportWidth"] + 2,
        "Four standard enemy cards are not visible at once on mobile",
    )

    render_combat(page, scenarios["boss_with_adds"])
    boss_metrics = collect_card_metrics(page)
    boss_entry = next((entry for entry in boss_metrics["enemyMetrics"] if "size-boss" in entry["className"]), None)
    standard_entries = [entry for entry in boss_metrics["enemyMetrics"] if "size-boss" not in entry["className"]]
    assert_true(boss_entry is not None and len(standard_entries) >= 1, "Boss scenario did not render boss and adds")
    standard_width = standard_entries[0]["width"]
    assert_true(boss_entry["width"] >= (standard_width * 1.9), "Boss width is not approximately 2x a standard enemy")
    assert_true(boss_entry["width"] <= boss_metrics["viewportWidth"], "Boss card overflowed the mobile viewport")

    render_combat(page, scenarios["elite_vs_regular"])
    elite_metrics = collect_card_metrics(page)
    elite_entry = next((entry for entry in elite_metrics["enemyMetrics"] if "size-elite" in entry["className"]), None)
    regular_entry = next((entry for entry in elite_metrics["enemyMetrics"] if "size-elite" not in entry["className"]), None)
    assert_true(elite_entry is not None and regular_entry is not None, "Elite comparison scenario did not render both cards")
    assert_true(abs(elite_entry["width"] - regular_entry["width"]) <= 2, "Elite width diverged from standard enemy width")
    assert_true(
        elite_entry["borderColor"] != regular_entry["borderColor"] or elite_entry["boxShadow"] != regular_entry["boxShadow"],
        "Elite card is not visually distinct from a standard enemy",
    )

    render_combat(page, scenarios["party_quad"])
    readability_metrics = collect_card_metrics(page)
    assert_true({"ATB", "HP"} <= set(readability_metrics["meters"]), "Mobile combat cards lost ATB or HP labels")
    assert_true(len(readability_metrics["actionButtons"]) >= 3, "Combat actions are not readable on mobile")
    assert_true(all(button["height"] >= 28 for button in readability_metrics["actionButtons"]), "Combat action affordances are too small on mobile")


def run(base_url, output_dir, headless=True):
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "base_url": base_url,
        "output_dir": str(output_dir),
        "screenshots": [],
        "checks": [],
        "failures": [],
    }
    room_v1 = build_room_fixture(version=1)
    room_v2 = build_room_fixture(version=2)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(f"{base_url}/webclient/test", wait_until="networkidle")
        page.wait_for_function("() => !!(window.plugins && window.plugins.defaultout)", timeout=15000)
        page.wait_for_timeout(1200)

        verify_mobile_room_panel_persistence(page, room_v1, room_v2, output_dir, report)
        report["checks"].append("mobile exploration panel persistence")
        verify_combat_screens(page, output_dir, report)
        report["checks"].append("combat rendering, feed persistence, and rank layout")

        browser.close()

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Run Brave mobile/combat UI screenshot harness.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    try:
        report = run(args.base_url.rstrip("/"), Path(args.output_dir), headless=not args.headed)
    except HarnessFailure as exc:
        raise SystemExit(f"HARNESS FAILURE: {exc}")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
