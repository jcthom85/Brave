import sys
import time
from playwright.sync_api import sync_playwright

def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("Navigating to webclient...")
            page.goto("http://127.0.0.1:4005/webclient")
            page.wait_for_load_state("networkidle")
            
            print("Attempting login for jctest...")
            page.keyboard.press("Tab")
            page.keyboard.type("jctest")
            page.keyboard.press("Tab")
            page.keyboard.type("Animals5")
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            
            content = page.content()
            if "Username and/or password is incorrect" in content:
                print("FAILED: Login rejected with 'incorrect password' error.")
            elif "jctest" in content and "Create Character" in content:
                print("SUCCESS: Login successful!")
            else:
                print("UNKNOWN: Could not determine login status.")
                print(f"Content snippet: {content[:500]}")

        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_login()
