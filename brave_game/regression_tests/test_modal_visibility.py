from playwright.sync_api import sync_playwright

from regression_tests.live_opening_harness import (
    assert_lanternfall_opening_visible,
    create_fresh_character,
)


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


if __name__ == "__main__":
    test_welcome_modal_visibility()
