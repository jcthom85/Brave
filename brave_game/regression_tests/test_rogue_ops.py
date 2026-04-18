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

from commands.brave_town import CmdSteal
from typeclasses.characters import Character
from world.browser_views import build_sheet_view
from world.rogue_ops import attempt_theft, get_available_steal_targets


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyEntity:
    def __init__(self, key, entity_id):
        self.key = key
        self.db = SimpleNamespace(brave_entity_id=entity_id)


class DummyRogue:
    def __init__(self, *, class_key="rogue"):
        self.id = 8
        self.key = "Shade"
        self.location = None
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_race="human",
            brave_level=6,
            brave_xp=120,
            brave_silver=10,
            brave_inventory=[],
            brave_rogue_theft_log={},
            brave_primary_stats={"strength": 3, "agility": 8, "intellect": 3, "spirit": 2, "vitality": 4},
            brave_derived_stats={
                "max_hp": 44,
                "max_mana": 20,
                "max_stamina": 31,
                "attack_power": 12,
                "spell_power": 5,
                "armor": 7,
                "accuracy": 14,
                "dodge": 11,
                "precision": 5,
            },
            brave_resources={"hp": 40, "mana": 15, "stamina": 27},
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

    def get_unlocked_abilities(self):
        return ["Stab", "Feint", "Backstab", "Vanish"]

    def get_rogue_theft_log(self):
        return Character.get_rogue_theft_log(self)


class RogueOpsTests(unittest.TestCase):
    def test_rogue_can_work_authored_theft_target_once(self):
        character = DummyRogue()
        target = DummyEntity("Uncle Pib", "uncle_pib_underbough")

        ok, message, result = attempt_theft(character, target)

        self.assertTrue(ok)
        self.assertIn("bandage", message.lower())
        self.assertEqual(14, character.db.brave_silver)
        self.assertEqual(1, character.get_inventory_quantity("field_bandage"))
        self.assertEqual("Uncle Pib", result.get("target_name"))
        self.assertIn("uncle_pib_underbough", character.db.brave_rogue_theft_log)

        ok, message, _result = attempt_theft(character, target)
        self.assertFalse(ok)
        self.assertIn("already worked", message)

    def test_non_rogue_cannot_work_theft_target(self):
        character = DummyRogue(class_key="warrior")
        target = DummyEntity("Torren", "torren_ironroot")

        ok, message, _result = attempt_theft(character, target)

        self.assertFalse(ok)
        self.assertIn("Only a Rogue", message)
        self.assertEqual(10, character.db.brave_silver)

    def test_available_steal_targets_filter_to_authored_marks(self):
        entities = [
            DummyEntity("Uncle Pib", "uncle_pib_underbough"),
            DummyEntity("Captain Rowan", "captain_harl_rowan"),
            DummyEntity("Leda", "leda_thornwick"),
        ]

        marks = get_available_steal_targets(entities)

        self.assertEqual(["Uncle Pib", "Leda"], [entity.key for entity, _ in marks])

    def test_rogue_sheet_view_shows_worked_angles(self):
        character = DummyRogue()
        character.db.brave_rogue_theft_log = {
            "uncle_pib_underbough": {"target": "Uncle Pib", "rewards": ["4 silver"]},
            "leda_thornwick": {"target": "Leda Thornwick", "rewards": ["6 silver"]},
        }

        view = build_sheet_view(character)
        illicit_access = _section(view, "Illicit Access")
        entry = illicit_access.get("items", [])[0]

        self.assertEqual("Worked Angles", entry.get("title"))
        self.assertIn("Worked marks: 2", entry.get("lines", []))
        self.assertIn("Latest lift: Leda Thornwick", entry.get("lines", []))

    def test_steal_command_is_registered_with_expected_key(self):
        self.assertEqual("steal", CmdSteal.key)


if __name__ == "__main__":
    unittest.main()
