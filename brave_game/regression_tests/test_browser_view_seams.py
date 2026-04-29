import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BrowserViewSeamTests(unittest.TestCase):
    def test_extracted_browser_view_modules_do_not_import_facade(self):
        extracted_modules = [
            "world/browser_character_views.py",
            "world/browser_combat_views.py",
            "world/browser_inventory_views.py",
            "world/browser_journal_views.py",
            "world/browser_mobile_views.py",
            "world/browser_party_views.py",
            "world/browser_room_helpers.py",
            "world/browser_room_views.py",
            "world/browser_service_views.py",
        ]

        for module_path in extracted_modules:
            source = (ROOT / module_path).read_text(encoding="utf-8")
            self.assertNotIn("world.browser_views", source, msg=module_path)

    def test_enemy_turns_do_not_import_combat_script_class(self):
        source = (ROOT / "world/combat_enemy_turns.py").read_text(encoding="utf-8")

        self.assertNotIn("typeclasses.scripts", source)


if __name__ == "__main__":
    unittest.main()
