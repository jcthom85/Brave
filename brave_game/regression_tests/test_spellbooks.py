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

from typeclasses.characters import Character
from world.activities import use_consumable_template
from world.combat_actions import build_combat_action_payload


class DummyMage:
    def __init__(self, *, class_key="mage", inventory=None):
        self.id = 7
        self.key = "Dad"
        self.location = None
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_level=5,
            brave_inventory=list(inventory or []),
            brave_learned_abilities=[],
            brave_quests={},
            brave_resources={"hp": 20, "mana": 30, "stamina": 12},
            brave_derived_stats={"max_hp": 24, "max_mana": 30, "max_stamina": 12},
        )
        self.ndb = SimpleNamespace()

    def msg(self, *args, **kwargs):
        return None

    def ensure_brave_character(self):
        return None

    def get_inventory_quantity(self, template_id):
        return Character.get_inventory_quantity(self, template_id)

    def add_item_to_inventory(self, template_id, quantity=1, *, count_for_collection=True):
        return Character.add_item_to_inventory(self, template_id, quantity, count_for_collection=count_for_collection)

    def remove_item_from_inventory(self, template_id, quantity=1):
        return Character.remove_item_from_inventory(self, template_id, quantity)

    def get_learned_abilities(self):
        return Character.get_learned_abilities(self)

    def get_unlocked_abilities(self):
        return Character.get_unlocked_abilities(self)

    def learn_ability(self, ability_key):
        return Character.learn_ability(self, ability_key)


class DummyEncounter:
    def __init__(self, participant):
        self._participant = participant
        self._enemies = [{"id": "e1", "key": "Bog Wolf", "hp": 18, "max_hp": 18, "armor": 2, "dodge": 5}]

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return [self._participant]


def _action(actions, key):
    for action in actions:
        if action.get("key") == key:
            return action
    raise AssertionError(f"Missing action {key}")


class SpellbookTests(unittest.TestCase):
    def test_mage_can_study_spellbook_and_learn_spell(self):
        character = DummyMage(inventory=[{"template": "mirror_veil_primer", "quantity": 1}])

        ok, message, result = use_consumable_template(character, "mirror_veil_primer", context="explore")

        self.assertTrue(ok)
        self.assertIn("Mirror Veil", message)
        self.assertEqual("Mirror Veil", result.get("learned_ability_name"))
        self.assertEqual(0, character.get_inventory_quantity("mirror_veil_primer"))
        self.assertIn("mirrorveil", character.db.brave_learned_abilities)
        self.assertIn("Mirror Veil", character.get_unlocked_abilities())

    def test_non_mage_cannot_study_mage_spellbook(self):
        character = DummyMage(class_key="warrior", inventory=[{"template": "mirror_veil_primer", "quantity": 1}])

        ok, message, _result = use_consumable_template(character, "mirror_veil_primer", context="explore")

        self.assertFalse(ok)
        self.assertIn("Only a Mage", message)
        self.assertEqual(1, character.get_inventory_quantity("mirror_veil_primer"))
        self.assertEqual([], character.db.brave_learned_abilities)

    def test_learned_spell_appears_in_combat_actions(self):
        character = DummyMage(inventory=[])
        character.learn_ability("stormlance")
        encounter = DummyEncounter(character)

        payload = build_combat_action_payload(encounter, character)
        stormlance = _action(payload["abilities"], "stormlance")

        self.assertEqual("Stormlance", stormlance.get("label"))
        self.assertIn("disciplined bolt", stormlance.get("tooltip", ""))


if __name__ == "__main__":
    unittest.main()
