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
from world.browser_views import build_sheet_view
from world.content import get_content_registry
from world.mastery import ABILITY_MASTERY_DATA, get_ability_mastery_bonuses, get_ability_mastery_role, get_next_mastery_text


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyMasteryCharacter:
    def __init__(self):
        self.id = 7
        self.key = "Nyra"
        self.location = None
        self.db = SimpleNamespace(
            brave_class="mage",
            brave_race="human",
            brave_level=5,
            brave_xp=120,
            brave_silver=50,
            brave_ability_mastery={},
            brave_primary_stats={"strength": 2, "agility": 3, "intellect": 8, "spirit": 5, "vitality": 4},
            brave_derived_stats={
                "max_hp": 50,
                "max_mana": 30,
                "max_stamina": 20,
                "attack_power": 8,
                "spell_power": 16,
                "armor": 6,
                "accuracy": 12,
                "dodge": 6,
                "precision": 2,
                "threat": 0,
                "healing_power": 0,
            },
            brave_resources={"hp": 50, "mana": 30, "stamina": 20},
            brave_meal_buff={},
            brave_chapel_blessing={},
            brave_companion_bonds={},
            brave_quests={},
            brave_gender="nonbinary",
        )

    def get_unlocked_combat_abilities(self):
        return ["Firebolt", "Frost Bind", "Arc Spark"]

    def get_unlocked_passive_abilities(self):
        return []

    def get_active_meal_bonuses(self):
        return {}

    def get_active_chapel_bonuses(self):
        return {}

    def get_active_companion(self):
        return {}

    def get_unlocked_companions(self):
        return []

    def get_active_oath(self):
        return {}

    def get_unlocked_oaths(self):
        return []

    def get_brave_gender_label(self):
        return "Non-binary"

    def get_ability_mastery_rank(self, ability_key):
        return Character.get_ability_mastery_rank(self, ability_key)

    def get_ability_mastery_map(self):
        return Character.get_ability_mastery_map(self)

    def get_earned_mastery_points(self):
        return Character.get_earned_mastery_points(self)

    def get_spent_mastery_points(self):
        return Character.get_spent_mastery_points(self)

    def get_available_mastery_points(self):
        return Character.get_available_mastery_points(self)

    def set_ability_mastery_rank(self, ability_key, rank):
        return Character.set_ability_mastery_rank(self, ability_key, rank)

    def train_ability_mastery(self, ability_key):
        return Character.train_ability_mastery(self, ability_key)

    def reset_ability_mastery(self):
        return Character.reset_ability_mastery(self)


class AbilityMasteryTests(unittest.TestCase):
    def test_every_implemented_combat_ability_has_authored_mastery(self):
        registry = get_content_registry()
        implemented = set(registry.characters.implemented_ability_keys)

        self.assertEqual(sorted(implemented), sorted(ABILITY_MASTERY_DATA.keys()))

    def test_defend_uses_guard_mastery_profile(self):
        bonuses = get_ability_mastery_bonuses("defend", 3)

        self.assertEqual("guard", get_ability_mastery_role("defend"))
        self.assertEqual(6, bonuses["guard"])
        self.assertEqual(1, bonuses["turn"])

    def test_authored_mastery_text_is_ability_specific(self):
        self.assertEqual(
            "Trained: the bolt flies truer.",
            get_next_mastery_text("firebolt", 1),
        )
        self.assertEqual(
            "Mastered: your guard holds longer into the next exchange.",
            get_next_mastery_text("defend", 2),
        )

    def test_training_spends_points_and_respec_refunds_focus(self):
        character = DummyMasteryCharacter()

        self.assertEqual(2, character.get_earned_mastery_points())
        self.assertEqual(2, character.get_available_mastery_points())

        ok, _message = character.train_ability_mastery("firebolt")
        self.assertTrue(ok)
        self.assertEqual(2, character.get_ability_mastery_rank("firebolt"))
        self.assertEqual(1, character.get_available_mastery_points())

        ok, _message = character.reset_ability_mastery()
        self.assertTrue(ok)
        self.assertEqual(1, character.get_ability_mastery_rank("firebolt"))
        self.assertEqual(20, character.db.brave_silver)

    def test_sheet_view_shows_roman_mastery_tiers(self):
        character = DummyMasteryCharacter()
        character.set_ability_mastery_rank("firebolt", 2)

        view = build_sheet_view(character)
        abilities = _section(view, "Abilities")

        labels = [item.get("text") for item in abilities.get("items", [])]
        self.assertIn("Firebolt II", labels)


if __name__ == "__main__":
    unittest.main()
