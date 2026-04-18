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

from commands.brave_profile import CmdOath
from typeclasses.characters import Character
from world.activities import use_consumable_template
from world.browser_views import build_sheet_view
from world.chapel import apply_dawn_bell_blessing, get_active_blessing


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyPaladin:
    def __init__(self, *, class_key="paladin", inventory=None):
        self.id = 10
        self.key = "Alden"
        self.location = None
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_race="human",
            brave_level=6,
            brave_xp=220,
            brave_silver=18,
            brave_inventory=list(inventory or []),
            brave_paladin_oaths=["oath_of_the_bell"] if class_key == "paladin" else [],
            brave_active_oath="oath_of_the_bell" if class_key == "paladin" else "",
            brave_primary_stats={"strength": 5, "agility": 3, "intellect": 3, "spirit": 6, "vitality": 6},
            brave_derived_stats={
                "max_hp": 64,
                "max_mana": 24,
                "max_stamina": 31,
                "attack_power": 14,
                "spell_power": 10,
                "armor": 12,
                "accuracy": 12,
                "dodge": 6,
                "precision": 2,
                "threat": 11,
                "healing_power": 0,
            },
            brave_resources={"hp": 60, "mana": 21, "stamina": 26},
            brave_meal_buff={},
            brave_chapel_blessing={},
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

    def recalculate_stats(self, restore=False):
        return self.db.brave_primary_stats, self.db.brave_derived_stats

    def get_unlocked_abilities(self):
        return ["Holy Strike", "Guarding Aura", "Judgement", "Shield of Dawn"]

    def get_unlocked_oaths(self):
        return Character.get_unlocked_oaths(self)

    def get_active_oath(self):
        return Character.get_active_oath(self)

    def unlock_oath(self, oath_key):
        return Character.unlock_oath(self, oath_key)

    def set_active_oath(self, oath_key):
        return Character.set_active_oath(self, oath_key)


class PaladinOathTests(unittest.TestCase):
    def test_paladin_can_swear_new_oath_from_relic(self):
        character = DummyPaladin(inventory=[{"template": "mercy_votive", "quantity": 1}])

        ok, message, _result = use_consumable_template(character, "mercy_votive", context="explore")

        self.assertTrue(ok)
        self.assertIn("Oath Of Mercy", message)
        self.assertEqual(0, character.get_inventory_quantity("mercy_votive"))
        self.assertEqual("oath_of_mercy", character.db.brave_active_oath)
        self.assertIn("oath_of_mercy", character.db.brave_paladin_oaths)

    def test_non_paladin_cannot_swear_paladin_oath_relic(self):
        character = DummyPaladin(class_key="cleric", inventory=[{"template": "mercy_votive", "quantity": 1}])

        ok, message, _result = use_consumable_template(character, "mercy_votive", context="explore")

        self.assertFalse(ok)
        self.assertIn("Only a Paladin", message)
        self.assertEqual(1, character.get_inventory_quantity("mercy_votive"))

    def test_active_oath_changes_dawn_bell_rite_and_bonuses(self):
        character = DummyPaladin()

        apply_dawn_bell_blessing(character)
        base = get_active_blessing(character)
        self.assertEqual("Oath Of The Bell", (base.get("rite") or {}).get("name"))
        self.assertEqual(5, base.get("bonuses", {}).get("threat"))

        character.unlock_oath("oath_of_mercy")
        blessing = get_active_blessing(character)

        self.assertEqual("Oath Of Mercy", (blessing.get("rite") or {}).get("name"))
        self.assertEqual(4, blessing.get("bonuses", {}).get("healing_power"))
        self.assertEqual(8, blessing.get("bonuses", {}).get("max_mana"))

    def test_sheet_view_shows_active_paladin_oath(self):
        character = DummyPaladin()
        character.unlock_oath("oath_of_cinders")

        view = build_sheet_view(character)
        oath_section = _section(view, "Sacred Oath")
        entry = oath_section.get("items", [])[0]

        self.assertEqual("Oath Of Cinders", entry.get("title"))
        self.assertIn("Sworn oaths: 2", entry.get("lines", []))

    def test_oath_command_is_registered_with_expected_key(self):
        self.assertEqual("oath", CmdOath.key)


if __name__ == "__main__":
    unittest.main()
