import time
from pathlib import Path


BASE_URL = "http://127.0.0.1:4005"
SCREENSHOT_DIR = Path("/home/jcthom85/Brave/tmp/live-opening")


def _safe_stamp():
    return str(int(time.time() * 1000))[-10:]


def _letter_stamp():
    value = int(time.time() * 1000)
    letters = []
    for _index in range(8):
        value, offset = divmod(value, 26)
        letters.append(chr(ord("a") + offset))
    return "".join(reversed(letters)).title()


def send_command(page, command):
    page.evaluate(
        """(command) => {
            if (!window.plugin_handler || typeof window.plugin_handler.onSend !== "function") {
                throw new Error("webclient plugin_handler is not ready");
            }
            window.plugin_handler.onSend(command);
            return true;
        }""",
        command,
    )


def wait_for_plugin(page):
    page.wait_for_function(
        "() => !!(window.plugin_handler && typeof window.plugin_handler.onSend === 'function')",
        timeout=15000,
    )


def wait_for_view(page, variant, timeout=15000):
    page.wait_for_selector(f".brave-view--{variant}", state="visible", timeout=timeout)


def wait_for_scene(page, scene="explore", timeout=20000):
    page.wait_for_function(
        "(scene) => document.body && document.body.getAttribute('data-brave-scene') === scene",
        arg=scene,
        timeout=timeout,
    )


def create_fresh_character(page, *, viewport=None):
    if viewport:
        page.set_viewport_size(viewport)
    character_name = f"Hero{_letter_stamp()}"

    page.goto(f"{BASE_URL}/webclient/test")
    page.wait_for_load_state("networkidle")
    wait_for_plugin(page)
    wait_for_view(page, "account")

    send_command(page, "create discard")
    wait_for_view(page, "account")
    send_command(page, "create")
    wait_for_view(page, "chargen")
    send_command(page, "human")
    wait_for_view(page, "chargen")
    send_command(page, "warrior")
    wait_for_view(page, "chargen")
    send_command(page, "male")
    wait_for_view(page, "chargen")
    send_command(page, character_name)
    wait_for_view(page, "chargen")
    send_command(page, "finish play")
    wait_for_scene(page, "explore")
    page.wait_for_selector("#brave-objectives-sheet", state="attached", timeout=10000)

    return {
        "username": "jctest",
        "character": character_name,
    }


def assert_lanternfall_opening_visible(page, *, screenshot_name="opening.png"):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOT_DIR / screenshot_name), full_page=True)

    sheet = page.locator("#brave-objectives-sheet")
    sheet.wait_for(state="visible", timeout=10000)
    assert sheet.get_attribute("aria-hidden") == "false"
    assert "A New Hero Arrives!" in sheet.inner_text()

    page.locator("[data-brave-welcome-next]").click()
    assert "Lanternfall" in sheet.inner_text()
    assert "south road lantern has gone black" in sheet.inner_text()

    page.locator("[data-brave-welcome-next]").click()
    assert "No Time To Drift" in sheet.inner_text()
    assert "Sergeant Tamsin" in sheet.inner_text()

    return True
