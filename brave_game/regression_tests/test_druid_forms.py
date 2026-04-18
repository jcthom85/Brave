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


class DummyDruid:
    def __init__(self, *, class_key="druid", inventory=None):
        self.id = 9
        self.key = "Mira"
        self.location = None
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_race="mosskin",
            brave_level=7,
            brave_xp=250,
            brave_silver=12,
            brave_inventory=list(inventory or []),
            brave_learned_abilities=[],
            brave_primary_stats={"strength": 3, "agility": 5, "intellect": 6, "spirit": 7, "vitality": 5},
            brave_derived_stats={
                "max_hp": 52,
                "max_mana": 32,
                "max_stamina": 24,
                "attack_power": 10,
                "spell_power": 15,
                "armor": 8,
                "accuracy": 13,
                "dodge": 8,
                "precision": 3,
            },
            brave_resources={"hp": 45, "mana": 28, "stamina": 20},
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

    def get_learned_abilities(self):
        return Character.get_learned_abilities(self)

    def get_unlocked_abilities(self):
        return Character.get_unlocked_abilities(self)

    def learn_ability(self, ability_key):
        return Character.learn_ability(self, ability_key)


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DruidFormTests(unittest.TestCase):
    def test_druid_can_study_crow_form(self):
        character = DummyDruid(inventory=[{"template": "crowfeather_rite", "quantity": 1}])

        ok, message, result = use_consumable_template(character, "crowfeather_rite", context="explore")

        self.assertTrue(ok)
        self.assertIn("Crow Form", message)
        self.assertEqual("Crow Form", result.get("learned_ability_name"))
        self.assertIn("crowform", character.db.brave_learned_abilities)
        self.assertEqual(0, character.get_inventory_quantity("crowfeather_rite"))

    def test_non_druid_cannot_study_druid_form(self):
        character = DummyDruid(class_key="mage", inventory=[{"template": "crowfeather_rite", "quantity": 1}])

        ok, message, _result = use_consumable_template(character, "crowfeather_rite", context="explore")

        self.assertFalse(ok)
        self.assertIn("Only a Druid", message)

    def test_sheet_view_shows_learned_primal_forms(self):
        character = DummyDruid()
        character.learn_ability("crowform")
        character.learn_ability("serpentform")

        view = build_sheet_view(character)
        forms = _section(view, "Primal Forms")
        titles = [item.get("title") for item in forms.get("items", [])]

        self.assertIn("Wolf Form", titles)
        self.assertIn("Crow Form", titles)
        self.assertIn("Serpent Form", titles)


if __name__ == "__main__":
    unittest.main()
