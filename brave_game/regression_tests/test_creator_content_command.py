import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.brave_creator import (
    list_content_history,
    mutate_content,
    preview_content,
    publish_content,
    remove_content,
    revert_content,
)
from world.content.editor import ContentEditor
from world.content.editor import ContentPublishValidationError


ROOT = Path("/home/jcthom85/Brave/brave_game/world/content/packs/core")


class CreatorContentCommandTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pack_paths = {}
        for name in ("characters", "items", "quests", "world", "encounters", "dialogue", "systems"):
            source = ROOT / f"{name}.json"
            target = self.root / f"{name}.json"
            shutil.copyfile(source, target)
            self.pack_paths[name] = target
        self.draft_paths = {name: self.root / "drafts" / f"{name}.json" for name in self.pack_paths}
        self.history_root = self.root / "history"
        self.editor = ContentEditor(pack_paths=self.pack_paths, draft_pack_paths=self.draft_paths, history_root=self.history_root)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_preview_content_room_returns_world_graph(self):
        preview = preview_content("room", ["brambleford_town_green"])
        self.assertEqual("brambleford_town_green", preview["room"]["id"])
        self.assertTrue(preview["exits"])
        self.assertIn("entities", preview)
        self.assertIn("encounters", preview)

    def test_mutate_content_room_sets_target_id(self):
        mutation = mutate_content(
            "room",
            "creator_test_room",
            json.dumps({"key": "Creator Test Room", "desc": "A temporary room injected through the creator command.", "zone": "Testing", "world": "Brave"}),
            editor=self.editor,
        )
        room = next(room for room in mutation.payload["rooms"] if room["id"] == "creator_test_room")
        self.assertEqual("Creator Test Room", room["key"])
        self.assertIn("creator_test_room", mutation.diff)
        self.assertEqual("live", mutation.stage)

    def test_mutate_content_quest_accepts_wrapper_metadata(self):
        mutation = mutate_content(
            "quest",
            "creator_test_quest",
            json.dumps({"quest": {"title": "Creator Test Quest", "summary": "Quest wrapper coverage.", "objectives": [{"type": "visit_room", "room_id": "brambleford_town_green", "count": 1}], "rewards": {"items": []}}, "region": "Testing", "add_starting": True}),
            editor=self.editor,
        )
        self.assertEqual("Testing", mutation.payload["quest_regions"]["creator_test_quest"])
        self.assertIn("creator_test_quest", mutation.payload["starting_quests"])

    def test_mutate_content_portal_write_persists(self):
        mutate_content(
            "portal",
            "creator_test_portal",
            json.dumps({"name": "Creator Test Portal", "status": "stable", "resonance": "fantasy", "summary": "A temporary portal added by command coverage.", "travel_hint": "north", "entry_room": "brambleford_town_green"}),
            write=True,
            editor=self.editor,
            author="tester",
        )
        persisted = json.loads(self.pack_paths["systems"].read_text(encoding="utf-8"))
        self.assertIn("creator_test_portal", persisted["portals"]["portals"])
        self.assertEqual("tester", persisted["_meta"]["last_modified_by"])

    def test_remove_content_readable_dry_run_removes_entry(self):
        mutation = remove_content("read", "dawn_bell", editor=self.editor)
        self.assertNotIn("dawn_bell", mutation.payload["static_read_responses"])
        self.assertIn("dawn_bell", mutation.diff)

    def test_draft_write_creates_draft_pack_without_touching_live(self):
        mutation = mutate_content(
            "item",
            "creator_draft_item",
            json.dumps({"name": "Creator Draft Item", "kind": "loot", "summary": "Draft only."}),
            write=True,
            stage="draft",
            editor=self.editor,
            author="draft-user",
        )
        live_payload = json.loads(self.pack_paths["items"].read_text(encoding="utf-8"))
        draft_payload = json.loads(self.draft_paths["items"].read_text(encoding="utf-8"))
        self.assertNotIn("creator_draft_item", live_payload["item_templates"])
        self.assertIn("creator_draft_item", draft_payload["item_templates"])
        self.assertEqual("draft", mutation.stage)
        self.assertEqual("draft-user", draft_payload["_meta"]["last_modified_by"])

    def test_history_entries_are_recorded_for_writes(self):
        mutation = mutate_content(
            "room",
            "creator_history_room",
            json.dumps({"key": "Creator History Room", "desc": "History coverage.", "zone": "Testing", "world": "Brave"}),
            write=True,
            editor=self.editor,
            author="historian",
        )
        self.assertTrue(mutation.entry_id)
        self.assertTrue((self.history_root / f"{mutation.entry_id}.json").exists())
        entries = list_content_history(editor=self.editor, limit=5)
        self.assertTrue(any(entry["entry_id"] == mutation.entry_id for entry in entries))
        self.assertEqual("historian", entries[0]["author"])

    def test_revert_content_restores_previous_snapshot(self):
        first = mutate_content(
            "item",
            "creator_revert_item",
            json.dumps({"name": "First Name", "kind": "loot", "summary": "First"}),
            write=True,
            editor=self.editor,
            author="author-one",
        )
        mutate_content(
            "item",
            "creator_revert_item",
            json.dumps({"name": "Second Name", "kind": "loot", "summary": "Second"}),
            write=True,
            editor=self.editor,
            author="author-two",
        )
        revert_content(first.entry_id, write=True, editor=self.editor, author="reverter")
        persisted = json.loads(self.pack_paths["items"].read_text(encoding="utf-8"))
        self.assertNotIn("creator_revert_item", persisted["item_templates"])
        self.assertEqual("reverter", persisted["_meta"]["last_modified_by"])

    def test_publish_content_promotes_draft_to_live(self):
        mutate_content(
            "class",
            "creator_publish_class",
            json.dumps({"name": "Creator Publish Class", "role": "tester", "resource": "focus", "summary": "Draft class.", "base_stats": {"might": 2}, "progression": []}),
            write=True,
            stage="draft",
            editor=self.editor,
            author="draft-author",
        )
        mutations = publish_content("characters", editor=self.editor, author="publisher")
        self.assertEqual(1, len(mutations))
        persisted = json.loads(self.pack_paths["characters"].read_text(encoding="utf-8"))
        self.assertIn("creator_publish_class", persisted["classes"])
        self.assertEqual("publisher", persisted["_meta"]["last_modified_by"])

    def test_publish_content_raises_before_live_write_when_draft_is_invalid(self):
        live_before = self.pack_paths["world"].read_text(encoding="utf-8")
        mutate_content(
            "room",
            "placeholder_publish_room",
            json.dumps({"key": "Placeholder", "desc": "TODO", "zone": "Testing", "world": "Brave"}),
            write=True,
            stage="draft",
            editor=self.editor,
            author="draft-author",
        )

        with self.assertRaises(ContentPublishValidationError) as raised:
            publish_content("world", editor=self.editor, author="publisher")

        self.assertTrue(any("placeholder" in error.lower() for error in raised.exception.errors))
        self.assertEqual(live_before, self.pack_paths["world"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
