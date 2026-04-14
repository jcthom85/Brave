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

from world.activities import (
    get_targetable_consumable_characters,
    match_targetable_consumable_character,
    use_consumable,
    use_consumable_template,
)


class DummyRoom:
    def __init__(self, contents=None):
        self.contents = list(contents or [])


class DummyCharacter:
    def __init__(
        self,
        *,
        char_id,
        key,
        location,
        inventory=None,
        resources=None,
        derived=None,
        party_id=None,
    ):
        self.id = char_id
        self.key = key
        self.location = location
        self.db = SimpleNamespace(
            brave_inventory=list(inventory or []),
            brave_resources=dict(resources or {"hp": 20, "mana": 10, "stamina": 10}),
            brave_derived_stats=dict(derived or {"max_hp": 24, "max_mana": 10, "max_stamina": 10}),
            brave_party_id=party_id,
            brave_meal_buff={},
        )

    def ensure_brave_character(self):
        return None

    def remove_item_from_inventory(self, template_id, quantity=1):
        inventory = list(self.db.brave_inventory or [])
        for entry in inventory:
            if entry.get("template") != template_id:
                continue
            if entry.get("quantity", 0) < quantity:
                return False
            entry["quantity"] -= quantity
            if entry["quantity"] <= 0:
                inventory.remove(entry)
            self.db.brave_inventory = inventory
            return True
        return False

    def apply_meal_buff(self, template_id, cozy=False):
        self.db.brave_meal_buff = {"template": template_id, "cozy": bool(cozy)}
        return self.db.brave_meal_buff

    def get_active_meal_bonuses(self):
        return {}


class DummyRoomCharacter:
    def __init__(self, *, char_id, key, location, party_id=None):
        self.id = char_id
        self.key = key
        self.location = location
        self.db = SimpleNamespace(
            brave_party_id=party_id,
            brave_resources={"hp": 12, "mana": 0, "stamina": 6},
            brave_derived_stats={"max_hp": 20, "max_mana": 0, "max_stamina": 8},
        )

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


class ConsumableUseTests(unittest.TestCase):
    def test_targetable_consumable_characters_prioritize_self_then_party_then_room(self):
        room = DummyRoom()
        character = DummyCharacter(char_id=7, key="Dad", location=room, party_id="party-7")
        ally = DummyCharacter(char_id=8, key="Peep", location=room, party_id="party-7")
        stranger = DummyRoomCharacter(char_id=9, key="Rook", location=room)
        room.contents = [stranger, ally, character]

        targets = get_targetable_consumable_characters(character, include_self=True)

        self.assertEqual(["Dad", "Peep", "Rook"], [target.key for target in targets])

    def test_match_targetable_consumable_character_finds_nearby_party_member(self):
        room = DummyRoom()
        character = DummyCharacter(char_id=7, key="Dad", location=room, party_id="party-7")
        ally = DummyCharacter(char_id=8, key="Peep", location=room, party_id="party-7")
        room.contents = [character, ally]

        match = match_targetable_consumable_character(character, "pee", include_self=True)

        self.assertIs(match, ally)

    def test_use_consumable_template_restores_nearby_ally_outside_combat(self):
        room = DummyRoom()
        character = DummyCharacter(
            char_id=7,
            key="Dad",
            location=room,
            inventory=[{"template": "field_bandage", "quantity": 1}],
            party_id="party-7",
        )
        ally = DummyCharacter(
            char_id=8,
            key="Peep",
            location=room,
            resources={"hp": 5, "mana": 0, "stamina": 8},
            derived={"max_hp": 24, "max_mana": 0, "max_stamina": 10},
            party_id="party-7",
        )
        room.contents = [character, ally]

        ok, message, result = use_consumable_template(
            character,
            "field_bandage",
            context="explore",
            target=ally,
        )

        self.assertTrue(ok)
        self.assertIn("Peep", message)
        self.assertEqual("field_bandage", result.get("template_id"))
        self.assertEqual(23, ally.db.brave_resources["hp"])
        self.assertEqual([], character.db.brave_inventory)

    def test_use_consumable_reports_combat_only_items_outside_combat(self):
        room = DummyRoom()
        character = DummyCharacter(
            char_id=7,
            key="Dad",
            location=room,
            inventory=[{"template": "fireflask", "quantity": 1}],
        )
        room.contents = [character]

        ok, message, result = use_consumable(character, "fire flask", context="explore")

        self.assertFalse(ok)
        self.assertIn("can only be used in combat", message)
        self.assertIsNone(result)
        self.assertEqual(1, character.db.brave_inventory[0]["quantity"])


if __name__ == "__main__":
    unittest.main()
