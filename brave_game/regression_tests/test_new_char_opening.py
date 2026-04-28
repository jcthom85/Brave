from playwright.sync_api import sync_playwright

from regression_tests.live_opening_harness import (
    assert_lanternfall_opening_visible,
    create_fresh_character,
)


def test_new_character_opening():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        try:
            identity = create_fresh_character(page)
            assert_lanternfall_opening_visible(page, screenshot_name="desktop_new_character_opening.png")
            assert identity["character"] in page.content()
        finally:
            browser.close()


if __name__ == "__main__":
    test_new_character_opening()
