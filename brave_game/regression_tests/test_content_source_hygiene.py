import re
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContentSourceHygieneTests(unittest.TestCase):
    def test_legacy_authored_python_content_dumps_are_not_present(self):
        checked_paths = [
            ROOT / "world/data/quests.py",
            ROOT / "world/data/items.py",
            ROOT / "world/forging.py",
            ROOT / "world/commerce.py",
            ROOT / "world/trophies.py",
        ]
        forbidden_patterns = [
            re.compile(r"^QUESTS\s*=\s*\{", re.MULTILINE),
            re.compile(r"^ITEM_TEMPLATES\s*=\s*\{", re.MULTILINE),
            re.compile(r"^ITEM_CLASS_REQUIREMENTS\s*=\s*\{", re.MULTILINE),
            re.compile(r"^_UNUSED_", re.MULTILINE),
        ]

        for path in checked_paths:
            source = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertIsNone(pattern.search(source), msg=f"{path.relative_to(ROOT)} contains {pattern.pattern}")

    def test_orphaned_authored_content_modules_are_removed(self):
        removed_paths = [
            ROOT / "world/data/activities.py",
            ROOT / "world/data/entity_dialogue.py",
            ROOT / "world/data/portals.py",
            ROOT / "world/data/starting_world.py",
            ROOT / "world/data/encounters.py",
        ]

        for path in removed_paths:
            self.assertFalse(path.exists(), msg=f"{path.relative_to(ROOT)} should not exist")

    def test_core_json_packs_parse_without_trailing_data(self):
        pack_paths = sorted((ROOT / "world/content/packs/core").glob("*.json"))

        for path in pack_paths:
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_retired_portal_worlds_are_not_authored_content(self):
        checked_paths = [
            ROOT / "world/content/packs/core/world.json",
            ROOT / "world/content/packs/core/quests.json",
            ROOT / "world/content/packs/core/dialogue.json",
            ROOT / "world/content/packs/core/encounters.json",
            ROOT / "world/content/packs/core/systems.json",
        ]
        forbidden = ("Junk-Yard", "junkyard", "training_island", "Training Island", "Nexus", "nexus")

        for path in checked_paths:
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, source, msg=f"{path.relative_to(ROOT)} still contains {token}")


if __name__ == "__main__":
    unittest.main()
