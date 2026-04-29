import json
import shutil
import tempfile
import unittest
from pathlib import Path

from world.content.build import run_content_build
from world.content.editor import ContentEditor, ContentPublishValidationError
from world.content.registry import get_content_registry
from world.content.validation import validate_content_registry


CORE_PACK_ROOT = Path(__file__).resolve().parents[2] / "world/content/packs/core"
PACK_DOMAINS = ("characters", "items", "quests", "world", "encounters", "dialogue", "systems")


class FastContentTests(unittest.TestCase):
    def test_live_content_build_passes(self):
        result = run_content_build()

        self.assertTrue(result.ok, msg="\n".join(result.errors))

    def test_registry_exposes_pack_backed_content_without_django(self):
        registry = get_content_registry()

        self.assertEqual([], validate_content_registry(registry))
        self.assertIn("warrior", registry.characters.classes)
        self.assertIn("militia_blade", registry.items.item_templates)
        self.assertIn("practice_makes_heroes", registry.quests.quests)
        self.assertTrue(registry.world.get_room("brambleford_town_green"))
        self.assertIn("thorn_rat", registry.encounters.enemy_templates)


class FastContentEditorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pack_paths = {}
        for domain in PACK_DOMAINS:
            source = CORE_PACK_ROOT / f"{domain}.json"
            target = self.root / f"{domain}.json"
            shutil.copyfile(source, target)
            self.pack_paths[domain] = target
        self.editor = ContentEditor(pack_paths=self.pack_paths, history_root=self.root / "history")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_editor_mutates_draft_without_touching_live_pack(self):
        live_before = self.pack_paths["items"].read_text(encoding="utf-8")

        mutation = self.editor.upsert_item(
            "fast_lane_item",
            {"name": "Fast Lane Item", "kind": "loot", "summary": "A temporary fast-lane item."},
            write=True,
            stage="draft",
        )

        self.assertIn("fast_lane_item", mutation.payload["item_templates"])
        self.assertEqual(live_before, self.pack_paths["items"].read_text(encoding="utf-8"))
        draft_payload = json.loads(self.editor._path_for("items", stage="draft").read_text(encoding="utf-8"))
        self.assertIn("fast_lane_item", draft_payload["item_templates"])

    def test_publish_validation_failure_rolls_back_live_pack(self):
        live_before = self.pack_paths["world"].read_text(encoding="utf-8")
        self.editor.upsert_room(
            {
                "id": "new_fast_lane_room",
                "key": "New Room",
                "desc": "TODO",
                "zone": "Brambleford",
                "map_region": "brambleford",
                "world": "Brave",
            },
            write=True,
            stage="draft",
        )

        with self.assertRaises(ContentPublishValidationError) as raised:
            self.editor.publish_stage("world", author="fast-lane")

        self.assertTrue(any("placeholder" in error.lower() for error in raised.exception.errors))
        self.assertEqual(live_before, self.pack_paths["world"].read_text(encoding="utf-8"))
        self.assertEqual([], self.editor.list_history(domain="world", stage="live"))


if __name__ == "__main__":
    unittest.main()
