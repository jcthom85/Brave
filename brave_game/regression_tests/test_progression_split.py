import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character
from typeclasses.scripts import BraveEncounter
from world.browser_views import build_combat_view
from world.data.character_options import (
    ABILITY_LIBRARY,
    CLASSES,
    PASSIVE_ABILITY_BONUSES,
    ability_key,
    split_unlocked_abilities,
)


class DummyCharacter:
    def __init__(self, class_key="warrior", level=9):
        self.db = SimpleNamespace(
            brave_race="human",
            brave_class=class_key,
            brave_level=level,
            brave_resources={},
        )

    def get_equipment_bonuses(self):
        return {}

    def get_active_meal_bonuses(self):
        return {}

    def get_active_chapel_bonuses(self):
        return {}


class DummyCombatCharacter:
    def __init__(self, char_id, key, class_key, abilities, *, stamina=20, mana=20):
        self.id = char_id
        self.key = key
        self.location = None
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_level=10,
            brave_resources={"hp": 30, "mana": mana, "stamina": stamina},
            brave_derived_stats={"max_hp": 30, "max_mana": 20, "max_stamina": 20},
        )
        self._abilities = list(abilities)

    def get_unlocked_abilities(self):
        return list(self._abilities)

    def ensure_brave_character(self):
        return None


class DummyEncounterForQueue:
    def __init__(self):
        self.db = SimpleNamespace(pending_actions={})
        self.enemy = {"id": "e1", "key": "Bog Wolf", "hp": 14}
        self.refreshed = 0

    def find_enemy(self, _query=None):
        return self.enemy

    def find_participant(self, _query, default=None):
        return default

    def _refresh_browser_combat_views(self):
        self.refreshed += 1


class DummyRoom:
    def __init__(self):
        self.key = "Brush Line"
        self.db = SimpleNamespace(brave_world="Brave", brave_zone="Whispering Woods")


class DummyEncounterForView:
    def __init__(self, participant):
        self.obj = DummyRoom()
        self.db = SimpleNamespace(round=2, encounter_title="Bog Ambush")
        self._participant = participant

    def get_active_enemies(self):
        return [{"id": "e1", "key": "Bog Wolf", "hp": 14, "max_hp": 18}]

    def get_active_participants(self):
        return [self._participant]

    def _describe_pending_action(self, _character):
        return "battle cry"

    def _get_participant_state(self, _character):
        return {
            "guard": 0,
            "bleed_turns": 0,
            "poison_turns": 0,
            "curse_turns": 0,
            "snare_turns": 0,
            "feint_turns": 0,
            "stealth_turns": 0,
        }


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


def _item(section, prefix):
    for item in section.get("items", []):
        if item.get("text", "").startswith(prefix):
            return item
    raise AssertionError(f"Missing item {prefix}")


class ProgressionSplitTests(unittest.TestCase):
    def test_every_progression_ability_is_classified(self):
        missing = []
        for class_data in CLASSES.values():
            for _unlock_level, ability_name in class_data["progression"]:
                key = ability_key(ability_name)
                if key not in ABILITY_LIBRARY and key not in PASSIVE_ABILITY_BONUSES:
                    missing.append(ability_name)
        self.assertEqual([], missing)

    def test_split_unlocked_abilities_separates_actions_and_passives(self):
        actions, passives, unknown = split_unlocked_abilities("warrior", 9)

        self.assertIn("Shield Bash", actions)
        self.assertIn("Battle Cry", actions)
        self.assertIn("Iron Will", passives)
        self.assertIn("Bulwark", passives)
        self.assertEqual([], unknown)

    def test_ranger_progression_actions_are_classified(self):
        actions, passives, unknown = split_unlocked_abilities("ranger", 10)

        self.assertIn("Volley", actions)
        self.assertIn("Rain of Arrows", actions)
        self.assertIn("Trailwise", passives)
        self.assertIn("Deadly Rhythm", passives)
        self.assertEqual([], unknown)

    def test_mage_progression_actions_are_classified(self):
        actions, passives, unknown = split_unlocked_abilities("mage", 10)

        self.assertIn("Arc Spark", actions)
        self.assertIn("Meteor Sigil", actions)
        self.assertIn("Deep Focus", passives)
        self.assertIn("Elemental Attunement", passives)
        self.assertEqual([], unknown)

    def test_rogue_progression_actions_are_classified(self):
        actions, passives, unknown = split_unlocked_abilities("rogue", 10)

        self.assertIn("Backstab", actions)
        self.assertIn("Eviscerate", actions)
        self.assertIn("Light Feet", passives)
        self.assertIn("Killer's Focus", passives)
        self.assertEqual([], unknown)

    def test_paladin_progression_actions_are_classified(self):
        actions, passives, unknown = split_unlocked_abilities("paladin", 10)

        self.assertIn("Judgement", actions)
        self.assertIn("Avenging Light", actions)
        self.assertIn("Steadfast Faith", passives)
        self.assertIn("Beacon Soul", passives)
        self.assertEqual([], unknown)

    def test_druid_progression_actions_are_classified(self):
        actions, passives, unknown = split_unlocked_abilities("druid", 10)

        self.assertIn("Entangling Roots", actions)
        self.assertIn("Wrath of the Grove", actions)
        self.assertIn("Wild Grace", passives)
        self.assertIn("Nature's Memory", passives)
        self.assertEqual([], unknown)

    def test_passive_bonuses_apply_during_stat_recalculation(self):
        character = DummyCharacter(class_key="warrior", level=9)

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(221, derived["max_hp"])
        self.assertEqual(35, derived["armor"])
        self.assertEqual(21, derived["threat"])

    def test_queue_passive_trait_reports_it_is_always_active(self):
        encounter = DummyEncounterForQueue()
        warrior = DummyCombatCharacter(7, "Dad", "warrior", ["Strike", "Defend", "Shield Bash", "Iron Will"], stamina=20, mana=0)

        ok, message = BraveEncounter.queue_ability(encounter, warrior, "Iron Will", None)

        self.assertFalse(ok)
        self.assertIn("always active", message)

    def test_combat_view_renders_none_target_ability_as_direct_command(self):
        warrior = DummyCombatCharacter(7, "Dad", "warrior", ["Strike", "Defend", "Battle Cry"], stamina=20, mana=0)
        encounter = DummyEncounterForView(warrior)

        view = build_combat_view(encounter, warrior)
        abilities = _section(view, "Abilities")
        battle_cry = _item(abilities, "Battle Cry")

        self.assertEqual("N", battle_cry.get("badge"))
        self.assertEqual("use Battle Cry", battle_cry.get("command"))
        self.assertIsNone(battle_cry.get("picker"))

    def test_combat_view_renders_ranger_aoe_ability_as_direct_command(self):
        ranger = DummyCombatCharacter(8, "Scout", "ranger", ["Quick Shot", "Mark Prey", "Volley"], stamina=20, mana=0)
        encounter = DummyEncounterForView(ranger)

        view = build_combat_view(encounter, ranger)
        abilities = _section(view, "Abilities")
        volley = _item(abilities, "Volley")

        self.assertEqual("N", volley.get("badge"))
        self.assertEqual("use Volley", volley.get("command"))
        self.assertIsNone(volley.get("picker"))

    def test_combat_view_renders_mage_aoe_ability_as_direct_command(self):
        mage = DummyCombatCharacter(9, "Hex", "mage", ["Firebolt", "Frost Bind", "Flame Wave"], stamina=0, mana=20)
        encounter = DummyEncounterForView(mage)

        view = build_combat_view(encounter, mage)
        abilities = _section(view, "Abilities")
        flame_wave = _item(abilities, "Flame Wave")

        self.assertEqual("N", flame_wave.get("badge"))
        self.assertEqual("use Flame Wave", flame_wave.get("command"))
        self.assertIsNone(flame_wave.get("picker"))


if __name__ == "__main__":
    unittest.main()
