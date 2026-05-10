import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content.editor import ContentEditor, ContentPublishValidationError


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
                "atmosphere": "chapel_lamplight",
            },
            write=False,
        )

        room_ids = [room["id"] for room in mutation.payload["rooms"]]
        self.assertIn("creator_test_room", room_ids)
        room = next(room for room in mutation.payload["rooms"] if room["id"] == "creator_test_room")
        self.assertEqual("chapel_lamplight", room["atmosphere"])
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

    def test_write_pack_persists_system_portal_update(self):
        mutation = self.editor.upsert_portal(
            "creator_test_portal",
            {
                "name": "Creator Test Portal",
                "status": "stable",
                "resonance": "fantasy",
                "summary": "A temporary portal for editor tests.",
                "travel_hint": "north",
                "entry_room": "brambleford_town_green",
            },
            write=True,
        )

        persisted = json.loads(self.pack_paths["systems"].read_text(encoding="utf-8"))
        self.assertIn("creator_test_portal", persisted["portals"]["portals"])
        self.assertIn("Creator Test Portal", mutation.diff)

    def test_system_activity_upserts_and_deletes_use_draft_pack(self):
        self.editor.upsert_cooking_recipe(
            "creator_test_stew",
            {"name": "Creator Test Stew", "ingredients": {"bramble_perch": 1}, "result": "innkeepers_fishpie", "summary": "Draft recipe."},
            write=True,
            stage="draft",
        )
        self.editor.upsert_fishing_rod(
            "creator_test_rod",
            {"name": "Creator Test Rod", "power": 1, "stability": 1, "summary": "Draft rod."},
            write=True,
            stage="draft",
        )
        self.editor.delete_fishing_rod("creator_test_rod", write=True, stage="draft")

        live_payload = json.loads(self.pack_paths["systems"].read_text(encoding="utf-8"))
        draft_payload = json.loads((self.pack_paths["systems"].parent / "drafts" / "systems.json").read_text(encoding="utf-8"))
        self.assertNotIn("creator_test_stew", live_payload["activities"]["cooking_recipes"])
        self.assertIn("creator_test_stew", draft_payload["activities"]["cooking_recipes"])
        self.assertNotIn("creator_test_rod", draft_payload["activities"]["fishing_rods"])

    def test_system_boss_gate_and_trophy_upserts(self):
        gate = self.editor.upsert_boss_gate(
            "creator_test_gate",
            {"name": "Creator Test Gate", "trigger_room_id": "brambleford_town_green", "boss_enemy_key": "training_dummy", "encounter_key": "training_dummy", "max_participants": 1},
            write=False,
        )
        trophy = self.editor.upsert_trophy(
            "creator_test_trophy",
            {"name": "Creator Test Trophy", "placeholder": "Empty hook.", "summary": "A test trophy.", "world": "Brave"},
            write=False,
        )

        self.assertIn("creator_test_gate", gate.payload["boss_gates"]["boss_gates"])
        self.assertIn("creator_test_trophy", trophy.payload["trophies"]["trophies"])

    def test_publish_rejects_bad_world_graph_without_touching_live(self):
        before = self.pack_paths["world"].read_text(encoding="utf-8")
        self.editor.upsert_room(
            {
                "id": "new_creator_publish_room",
                "key": "New Room",
                "desc": "Test",
                "zone": "Brambleford",
                "map_region": "brambleford",
                "world": "Brave",
            },
            write=True,
            stage="draft",
        )

        with self.assertRaises(ContentPublishValidationError) as raised:
            self.editor.publish_stage("world", author="publisher")

        self.assertTrue(any("placeholder id" in error for error in raised.exception.errors))
        self.assertEqual(before, self.pack_paths["world"].read_text(encoding="utf-8"))
        self.assertEqual([], self.editor.list_history(domain="world", stage="live"))

    def test_publish_rejects_bad_reference_without_touching_live(self):
        before = self.pack_paths["encounters"].read_text(encoding="utf-8")
        self.editor.upsert_room_encounters(
            "missing_creator_room",
            [{"key": "bad_table", "title": "Bad Table", "intro": "Invalid reference.", "enemies": ["training_dummy"]}],
            write=True,
            stage="draft",
        )

        with self.assertRaises(ContentPublishValidationError) as raised:
            self.editor.publish_stage("encounters", author="publisher")

        self.assertTrue(any("Encounter table references unknown room" in error for error in raised.exception.errors))
        self.assertEqual(before, self.pack_paths["encounters"].read_text(encoding="utf-8"))
        self.assertEqual([], self.editor.list_history(domain="encounters", stage="live"))

    def test_publish_all_blocks_valid_domain_when_cross_domain_validation_fails(self):
        items_before = self.pack_paths["items"].read_text(encoding="utf-8")
        quests_before = self.pack_paths["quests"].read_text(encoding="utf-8")
        self.editor.upsert_item(
            "creator_valid_publish_item",
            {"name": "Creator Valid Publish Item", "kind": "loot", "summary": "Valid by itself."},
            write=True,
            stage="draft",
        )
        self.editor.upsert_quest(
            "creator_bad_publish_quest",
            {
                "title": "Creator Bad Publish Quest",
                "summary": "Invalid cross-domain quest for publish rollback.",
                "objectives": [{"type": "collect_item", "item_id": "missing_creator_item", "description": "Collect a missing thing."}],
                "rewards": {"items": [{"item": "missing_creator_item", "quantity": 1}]},
            },
            region="Testing",
            write=True,
            stage="draft",
        )

        with self.assertRaises(ContentPublishValidationError) as raised:
            self.editor.publish_stage(author="publisher")

        self.assertTrue(any("collects unknown item" in error for error in raised.exception.errors))
        self.assertTrue(any("rewards unknown item" in error for error in raised.exception.errors))
        self.assertEqual(items_before, self.pack_paths["items"].read_text(encoding="utf-8"))
        self.assertEqual(quests_before, self.pack_paths["quests"].read_text(encoding="utf-8"))
        self.assertEqual([], self.editor.list_history(stage="live"))

    def test_publish_all_validates_cross_domain_drafts_together(self):
        self.editor.upsert_item(
            "creator_cross_domain_item",
            {"name": "Creator Cross-Domain Item", "kind": "loot", "summary": "Draft item referenced by a draft quest."},
            write=True,
            stage="draft",
        )
        self.editor.upsert_quest(
            "creator_cross_domain_quest",
            {
                "title": "Creator Cross-Domain Quest",
                "summary": "Valid cross-domain publish coverage.",
                "objectives": [{"type": "collect_item", "item_id": "creator_cross_domain_item", "description": "Collect the draft item."}],
                "rewards": {"items": [{"item": "creator_cross_domain_item", "quantity": 1}]},
            },
            region="Testing",
            write=True,
            stage="draft",
        )

        mutations = self.editor.publish_stage(author="publisher")

        self.assertEqual(["items", "quests"], [mutation.domain for mutation in mutations])
        items_payload = json.loads(self.pack_paths["items"].read_text(encoding="utf-8"))
        quests_payload = json.loads(self.pack_paths["quests"].read_text(encoding="utf-8"))
        self.assertIn("creator_cross_domain_item", items_payload["item_templates"])
        self.assertIn("creator_cross_domain_quest", quests_payload["quests"])

    def test_publish_domain_list_validates_selected_cross_domain_drafts_together(self):
        self.editor.upsert_item(
            "creator_selected_domain_item",
            {"name": "Creator Selected Domain Item", "kind": "loot", "summary": "Draft item referenced by a selected draft quest."},
            write=True,
            stage="draft",
        )
        self.editor.upsert_quest(
            "creator_selected_domain_quest",
            {
                "title": "Creator Selected Domain Quest",
                "summary": "Selected publish coverage.",
                "objectives": [{"type": "collect_item", "item_id": "creator_selected_domain_item", "description": "Collect the draft item."}],
                "rewards": {"items": [{"item": "creator_selected_domain_item", "quantity": 1}]},
            },
            region="Testing",
            write=True,
            stage="draft",
        )

        mutations = self.editor.publish_stage(["quests", "items"], author="publisher")

        self.assertEqual(["quests", "items"], [mutation.domain for mutation in mutations])
        items_payload = json.loads(self.pack_paths["items"].read_text(encoding="utf-8"))
        quests_payload = json.loads(self.pack_paths["quests"].read_text(encoding="utf-8"))
        self.assertIn("creator_selected_domain_item", items_payload["item_templates"])
        self.assertIn("creator_selected_domain_quest", quests_payload["quests"])
