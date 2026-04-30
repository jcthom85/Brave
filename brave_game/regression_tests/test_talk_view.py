import os
import sys
import types
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda *args, **kwargs: None
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules.setdefault("world.chargen", chargen_stub)

from world.browser_views import _build_world_interaction_picker


class DummyNPC:
    def __init__(self, key, entity_id="mira", kind="npc"):
        self.key = key
        self.location = SimpleNamespace()
        self.db = SimpleNamespace(brave_entity_id=entity_id, brave_entity_kind=kind)


class DummyCharacter:
    def __init__(self):
        self.location = SimpleNamespace(
            db=SimpleNamespace(brave_world="Brave", brave_zone="Brambleford")
        )
        self.db = SimpleNamespace(
            brave_quests={},
            brave_shop_bonus=None,
            brave_inventory=[],
        )


class TalkViewTests(unittest.TestCase):
    def test_npc_interaction_picker_renders_dialogue_and_options(self):
        character = DummyCharacter()
        target = DummyNPC("Mira", entity_id="mira_fenleaf")
        picker = _build_world_interaction_picker(character, target)

        self.assertEqual("Mira", picker.get("title"))
        self.assertEqual("forum", picker.get("title_icon"))
        self.assertIn("The road's quieter than it was", " ".join(picker.get("body", [])))
        
        options = picker.get("options", [])
        self.assertEqual(["Continue"], [opt.get("label") for opt in options])
        self.assertTrue(options[0].get("close_picker"))

    def test_readable_interaction_picker_renders_text(self):
        character = DummyCharacter()
        target = DummyNPC("Supply Board", entity_id="tutorial_supply_board", kind="readable")
        picker = _build_world_interaction_picker(character, target)

        self.assertEqual("Supply Board", picker.get("title"))
        self.assertEqual("menu_book", picker.get("title_icon"))
        self.assertIn("SOUTH LANTERN OUT", " ".join(picker.get("body", [])))


if __name__ == "__main__":
    unittest.main()
