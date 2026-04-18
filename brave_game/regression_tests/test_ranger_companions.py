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
from world.browser_views import build_sheet_view


class DummyRanger:
    def __init__(self, *, class_key="ranger", inventory=None):
        self.id = 5
        self.key = "Kest"
        self.location = None
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_race="human",
            brave_level=6,
            brave_xp=120,
            brave_silver=10,
            brave_inventory=list(inventory or []),
            brave_companions=["marsh_hound"] if class_key == "ranger" else [],
            brave_active_companion="marsh_hound" if class_key == "ranger" else "",
            brave_primary_stats={"strength": 4, "agility": 8, "intellect": 2, "spirit": 2, "vitality": 5},
            brave_derived_stats={
                "max_hp": 50,
                "max_mana": 18,
                "max_stamina": 28,
                "attack_power": 13,
                "spell_power": 4,
                "armor": 8,
                "accuracy": 14,
                "dodge": 9,
                "precision": 4,
            },
            brave_resources={"hp": 45, "mana": 12, "stamina": 22},
            brave_meal_buff={},
            brave_quests={},
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

    def get_unlocked_companions(self):
        return Character.get_unlocked_companions(self)

    def get_active_companion(self):
        return Character.get_active_companion(self)

    def unlock_companion(self, companion_key):
        return Character.unlock_companion(self, companion_key)

    def set_active_companion(self, companion_key):
        return Character.set_active_companion(self, companion_key)

    def get_unlocked_abilities(self):
        return ["Quick Shot", "Mark Prey", "Aimed Shot", "Snare Trap"]


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class RangerCompanionTests(unittest.TestCase):
    def test_ranger_can_unlock_hawk_companion_from_bond_item(self):
        character = DummyRanger(inventory=[{"template": "hawkcaller_whistle", "quantity": 1}])

        ok, message, _result = use_consumable_template(character, "hawkcaller_whistle", context="explore")

        self.assertTrue(ok)
        self.assertIn("Ash Hawk", message)
        self.assertEqual(0, character.get_inventory_quantity("hawkcaller_whistle"))
        self.assertEqual("ash_hawk", character.db.brave_active_companion)
        self.assertIn("ash_hawk", character.db.brave_companions)

    def test_non_ranger_cannot_unlock_companion_from_bond_item(self):
        character = DummyRanger(class_key="mage", inventory=[{"template": "hawkcaller_whistle", "quantity": 1}])

        ok, message, _result = use_consumable_template(character, "hawkcaller_whistle", context="explore")

        self.assertFalse(ok)
        self.assertIn("Only a Ranger", message)

    def test_ranger_can_switch_active_companion(self):
        character = DummyRanger()
        character.unlock_companion("briar_boar")

        ok, message = character.set_active_companion("marsh_hound")

        self.assertTrue(ok)
        self.assertIn("Marsh Hound", message)
        self.assertEqual("marsh_hound", character.db.brave_active_companion)

    def test_sheet_view_shows_active_ranger_companion(self):
        character = DummyRanger()
        character.unlock_companion("ash_hawk")

        view = build_sheet_view(character)
        companion = _section(view, "Companion")

        self.assertEqual("Ash Hawk", companion.get("items", [])[0].get("title"))
        self.assertIn("Unlocked companions: 2", companion.get("items", [])[0].get("lines", []))


if __name__ == "__main__":
    unittest.main()
