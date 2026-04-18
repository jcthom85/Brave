import os
import sys
import types
import unittest
from time import time
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda *args, **kwargs: None
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules.setdefault("world.chargen", chargen_stub)

from typeclasses.characters import Character
from world.activities import reel_line
from world.chapel import get_dawn_bell_bonuses
from world.commerce import run_shop_shift
from world.forging import apply_forge_upgrade, get_forge_entries
from world.interactions import get_entity_response


class DummyAliases:
    def all(self):
        return []


class DummyRoom:
    def __init__(self, room_id, *, activities=None):
        self.db = SimpleNamespace(brave_room_id=room_id, brave_activities=list(activities or []))


class DummyRaceCharacter:
    def __init__(self, *, race_key="human", class_key="warrior", silver=0, inventory=None, equipment=None):
        self.id = 21
        self.key = "Brave"
        self.location = None
        self.aliases = DummyAliases()
        self.db = SimpleNamespace(
            brave_race=race_key,
            brave_class=class_key,
            brave_shop_bonus={},
            brave_silver=silver,
            brave_inventory=list(inventory or []),
            brave_quests={},
            brave_equipment=dict(equipment or {}),
            brave_primary_stats={},
            brave_derived_stats={},
            brave_resources={},
        )
        self.ndb = SimpleNamespace()

    def msg(self, *args, **kwargs):
        return None

    def recalculate_stats(self, restore=False):
        return {}, {}

    def get_inventory_quantity(self, template_id):
        return Character.get_inventory_quantity(self, template_id)

    def add_item_to_inventory(self, template_id, quantity=1, *, count_for_collection=True):
        return Character.add_item_to_inventory(self, template_id, quantity, count_for_collection=count_for_collection)

    def remove_item_from_inventory(self, template_id, quantity=1):
        return Character.remove_item_from_inventory(self, template_id, quantity)


class DummyEntity:
    def __init__(self, entity_id, *, kind="readable"):
        self.db = SimpleNamespace(brave_entity_id=entity_id, brave_entity_kind=kind)


class RaceWorldHookTests(unittest.TestCase):
    def test_human_shift_gets_extra_sale(self):
        character = DummyRaceCharacter(race_key="human")

        with patch("world.commerce.random.choice", return_value={"name": "Counter Rhythm", "bonus_pct": 10, "sales_left": 3, "text": "Shift done."}):
            ok, message = run_shop_shift(character)

        self.assertTrue(ok)
        self.assertEqual(4, character.db.brave_shop_bonus.get("sales_left"))
        self.assertIn("extra favorable sale", message)

    def test_dwarf_gets_forge_discount(self):
        character = DummyRaceCharacter(
            race_key="dwarf",
            silver=20,
            inventory=[{"template": "goblin_knife", "quantity": 2}, {"template": "road_charm", "quantity": 1}],
            equipment={"main_hand": "militia_blade"},
        )

        entries = get_forge_entries(character)
        ok, result = apply_forge_upgrade(character, "militia_blade")

        self.assertEqual(18, entries[0]["silver_cost"])
        self.assertTrue(ok)
        self.assertEqual(2, character.db.brave_silver)
        self.assertEqual(18, result["silver_cost"])

    def test_elf_gets_extra_read_insight(self):
        character = DummyRaceCharacter(race_key="elf")
        entity = DummyEntity("dawn_bell")

        response = get_entity_response(character, entity, "read")

        self.assertIn("LET MORNING FIND US", response)
        self.assertIn("second note", response)

    def test_mosskin_gets_better_fishing_read(self):
        character = DummyRaceCharacter(race_key="mosskin")
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])
        character.ndb.brave_fishing = {
            "phase": "bite",
            "room_id": "brambleford_hobbyists_wharf",
            "expires_at": time() + 100,
            "fish": {"item": "bramble_perch", "hook_chance": 1.0, "weight": (1.0, 1.0)},
        }

        with patch("world.activities._award_catch_record", return_value=None):
            ok, message = reel_line(character)

        self.assertTrue(ok)
        self.assertIn("1.3 lb", message)
        self.assertIn("Fen-born patience", message)
        self.assertEqual(1, character.get_inventory_quantity("bramble_perch"))

    def test_ashborn_gets_stronger_chapel_blessing(self):
        character = DummyRaceCharacter(race_key="ashborn", class_key="warrior")

        bonuses = get_dawn_bell_bonuses(character)

        self.assertEqual(3, bonuses.get("attack_power"))
        self.assertEqual(10, bonuses.get("max_stamina"))


if __name__ == "__main__":
    unittest.main()
