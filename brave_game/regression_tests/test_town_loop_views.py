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

from world.activities import format_kitchen_hearth_text
from world.browser_views import build_cook_view, build_forge_view, build_shop_view


def _entry(template_id, quantity):
    return {"template": template_id, "quantity": quantity}


class DummyCharacter:
    def __init__(self):
        self.db = SimpleNamespace(
            brave_inventory=[],
            brave_silver=24,
            brave_shop_bonus={},
            brave_party_id=None,
            brave_equipment={"main_hand": "militia_blade", "chest": "field_leathers"},
            brave_quests={},
        )
        self.location = SimpleNamespace(db=SimpleNamespace(brave_room_id="brambleford_lantern_rest_inn"))

    def get_inventory_quantity(self, template_id):
        return sum(entry["quantity"] for entry in self.db.brave_inventory if entry["template"] == template_id)


class TownLoopViewTests(unittest.TestCase):
    def test_shop_view_includes_loop_notes(self):
        character = DummyCharacter()
        character.db.brave_inventory = [_entry("wolf_pelt", 2)]
        view = build_shop_view(character)

        section = next(section for section in view["sections"] if section.get("label") == "Loop Notes")
        lines = [item.get("text") for item in section.get("items", [])]
        self.assertTrue(any("Clear excess loot here" in line for line in lines))
        self.assertTrue(any("Work Shift is best" in line for line in lines))

    def test_forge_view_includes_loop_notes(self):
        character = DummyCharacter()
        character.db.brave_inventory = [_entry("goblin_chain_link", 2), _entry("tower_watch_token", 1)]
        view = build_forge_view(character)

        section = next(section for section in view["sections"] if section.get("label") == "Loop Notes")
        lines = [item.get("text") for item in section.get("items", [])]
        self.assertTrue(any("recover, sell what you do not need, then forge" in line for line in lines))

    def test_cook_view_and_hearth_text_frame_road_prep(self):
        character = DummyCharacter()
        character.db.brave_inventory = [_entry("river_perch", 2)]
        view = build_cook_view(character)
        road_prep = next(section for section in view["sections"] if section.get("label") == "Road Prep")
        lines = [item.get("text") for item in road_prep.get("items", [])]
        hearth_text = format_kitchen_hearth_text(character)

        self.assertTrue(any("eat just before you leave town" in line for line in lines))
        self.assertIn("Best rhythm: |wrest|n, check |wpack|n, |wcook|n if you can, then |weat|n right before you head back out.", hearth_text)


if __name__ == "__main__":
    unittest.main()
