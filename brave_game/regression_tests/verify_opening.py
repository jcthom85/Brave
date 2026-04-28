from playwright.sync_api import sync_playwright

from regression_tests.live_opening_harness import (
    assert_lanternfall_opening_visible,
    create_fresh_character,
)


def verify_opening():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        try:
            create_fresh_character(page)
            assert_lanternfall_opening_visible(page, screenshot_name="verify_opening.png")
            print("Verification SUCCESSFUL!")
        finally:
            browser.close()


if __name__ == "__main__":
    verify_opening()
