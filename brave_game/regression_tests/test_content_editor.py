import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content.editor import ContentEditor


ROOT = Path("/home/jcthom85/Brave/brave_game/world/content/packs/core")


class ContentEditorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pack_paths = {}
        for name in ("characters", "items", "quests", "world", "encounters", "dialogue", "systems"):
            source = ROOT / f"{name}.json"
            target = self.root / f"{name}.json"
            shutil.copyfile(source, target)
            self.pack_paths[name] = target
        self.editor = ContentEditor(pack_paths=self.pack_paths)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_upsert_room_updates_world_payload_without_writing(self):
        mutation = self.editor.upsert_room(
            {
                "id": "creator_test_room",
                "key": "Creator Test Room",
                "desc": "A temporary room for editor coverage.",
                "zone": "Testing",
                "world": "Brave",
            },
            write=False,
        )

        room_ids = [room["id"] for room in mutation.payload["rooms"]]
        self.assertIn("creator_test_room", room_ids)
        self.assertIn("Creator Test Room", mutation.diff)

    def test_upsert_quest_updates_region_and_starting_state(self):
        mutation = self.editor.upsert_quest(
            "creator_test_quest",
            {
                "title": "Creator Test Quest",
                "objectives": [{"type": "visit_room", "room_id": "brambleford_town_green", "count": 1}],
                "rewards": {"items": []},
            },
            region="Testing",
            add_starting=True,
            write=False,
        )

        self.assertEqual("Testing", mutation.payload["quest_regions"]["creator_test_quest"])
        self.assertIn("creator_test_quest", mutation.payload["starting_quests"])

    def test_write_pack_persists_forge_recipe_update(self):
        mutation = self.editor.upsert_forge_recipe(
            "creator_test_blade",
            {
                "result": "ironroot_longblade",
                "silver": 18,
                "materials": {"wolf_fang": 1},
                "text": "A temporary forge recipe for editor tests.",
            },
            write=True,
        )

        persisted = json.loads(self.pack_paths["systems"].read_text(encoding="utf-8"))
        self.assertIn("creator_test_blade", persisted["forging"]["forge_recipes"])
        self.assertIn("creator_test_blade", mutation.diff)
