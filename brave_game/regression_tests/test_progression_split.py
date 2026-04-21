import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character
from typeclasses.scripts import BraveEncounter
from world.browser_views import build_combat_view
from world.content import get_content_registry

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
ABILITY_LIBRARY = CHARACTER_CONTENT.ability_library
CLASSES = CHARACTER_CONTENT.classes
PASSIVE_ABILITY_BONUSES = CHARACTER_CONTENT.passive_ability_bonuses
ability_key = CHARACTER_CONTENT.ability_key
split_unlocked_abilities = CHARACTER_CONTENT.split_unlocked_abilities


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
    def __init__(self, char_id, key, class_key, abilities, *, stamina=20, mana=20, inventory=None):
        self.id = char_id
        self.key = key
        self.location = None
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_level=10,
            brave_resources={"hp": 30, "mana": mana, "stamina": stamina},
            brave_derived_stats={"max_hp": 30, "max_mana": 20, "max_stamina": 20},
            brave_inventory=list(inventory or []),
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

    def find_consumable(self, character, query, *, context="combat", verb=None):
        return BraveEncounter.find_consumable(self, character, query, context=context, verb=verb)

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


def _view_action(view, label):
    for action in view.get("actions", []):
        if action.get("label") == label:
            return action
    raise AssertionError(f"Missing action {label}")


def _picker_option(picker, label, *, meta=None):
    for option in picker.get("options", []):
        if option.get("label") != label:
            continue
        if meta is not None and option.get("meta") != meta:
            continue
        return option
    raise AssertionError(f"Missing picker option {label} / {meta}")


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
        self.assertIn("Wolf Form", actions)
        self.assertIn("Bear Form", actions)
        self.assertIn("Wrath of the Grove", actions)
        self.assertIn("Wild Grace", passives)
        self.assertIn("Groveheart", passives)
        self.assertIn("Nature's Memory", passives)
        self.assertEqual([], unknown)

    def test_cleric_passives_keep_solo_offense_reliable(self):
        character = DummyCharacter(class_key="cleric", level=10)

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(85, derived["accuracy"])

    def test_rogue_passives_keep_solo_pressure_reliable(self):
        character = DummyCharacter(class_key="rogue", level=10)

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(95, derived["accuracy"])

    def test_druid_passives_now_apply_during_stat_recalculation(self):
        character = DummyCharacter(class_key="druid", level=10)

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(203, derived["max_hp"])
        self.assertEqual(87, derived["accuracy"])
        self.assertEqual(14, derived["dodge"])
        self.assertEqual(137, derived["max_mana"])
        self.assertEqual(41, derived["spell_power"])
        self.assertEqual(2, derived["healing_power"])

    def test_passive_bonuses_apply_during_stat_recalculation(self):
        character = DummyCharacter(class_key="warrior", level=9)

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(229, derived["max_hp"])
        self.assertEqual(35, derived["armor"])
        self.assertEqual(21, derived["threat"])

    def test_queue_passive_trait_reports_it_is_always_active(self):
        encounter = DummyEncounterForQueue()
        warrior = DummyCombatCharacter(7, "Dad", "warrior", ["Strike", "Defend", "Shield Bash", "Iron Will"], stamina=20, mana=0)

        ok, message = BraveEncounter.queue_ability(encounter, warrior, "Iron Will", None)

        self.assertFalse(ok)
        self.assertIn("always active", message)

    def test_queue_item_accepts_combat_consumable(self):
        encounter = DummyEncounterForQueue()
        cleric = DummyCombatCharacter(
            7,
            "Dad",
            "cleric",
            ["Heal"],
            inventory=[{"template": "riverlight_chowder", "quantity": 1}],
        )

        ok, message = BraveEncounter.queue_item(encounter, cleric, "Riverlight Chowder")

        self.assertTrue(ok)
        self.assertIn("Riverlight Chowder", message)
        self.assertEqual("item", encounter.db.pending_actions["7"]["kind"])
        self.assertEqual("riverlight_chowder", encounter.db.pending_actions["7"]["item"])
        self.assertEqual(1, encounter.refreshed)

    def test_queue_item_accepts_ally_target_consumable(self):
        encounter = DummyEncounterForQueue()
        cleric = DummyCombatCharacter(
            7,
            "Dad",
            "cleric",
            ["Heal"],
            inventory=[{"template": "purity_salts", "quantity": 1}],
        )
        ally = DummyCombatCharacter(
            8,
            "Peep",
            "warrior",
            ["Strike"],
            stamina=20,
            mana=0,
        )
        encounter.find_participant = lambda query, default=None: ally if query == "Peep" else default

        ok, message = BraveEncounter.queue_item(encounter, cleric, "Purity Salts", "Peep")

        self.assertTrue(ok)
        self.assertIn("Peep", message)
        self.assertEqual("item", encounter.db.pending_actions["7"]["kind"])
        self.assertEqual("purity_salts", encounter.db.pending_actions["7"]["item"])
        self.assertEqual(8, encounter.db.pending_actions["7"]["target"])

    def test_queue_item_accepts_guard_consumable(self):
        encounter = DummyEncounterForQueue()
        cleric = DummyCombatCharacter(
            7,
            "Dad",
            "cleric",
            ["Heal"],
            inventory=[{"template": "ward_dust", "quantity": 1}],
        )
        ally = DummyCombatCharacter(
            8,
            "Peep",
            "warrior",
            ["Strike"],
            stamina=20,
            mana=0,
        )
        encounter.find_participant = lambda query, default=None: ally if query == "Peep" else default

        ok, message = BraveEncounter.queue_item(encounter, cleric, "Ward Dust", "Peep")

        self.assertTrue(ok)
        self.assertIn("Peep", message)
        self.assertEqual("item", encounter.db.pending_actions["7"]["kind"])
        self.assertEqual("ward_dust", encounter.db.pending_actions["7"]["item"])
        self.assertEqual(8, encounter.db.pending_actions["7"]["target"])



class DummyCmdUse:
    def __init__(self, character, encounter, args):
        self._character = character
        self._encounter = encounter
        self.args = args
        self.lhs = args
        self.rhs = None
        self.last_message = None

    def get_character(self):
        return self._character

    def get_encounter(self, _character, require=True):
        return self._encounter

    def msg(self, message):
        self.last_message = message

    def test_cmd_use_falls_back_to_combat_consumable(self):
        from commands.brave_combat import CmdUse

        encounter = DummyEncounterForQueue()
        cleric = DummyCombatCharacter(
            7,
            "Dad",
            "cleric",
            ["Heal"],
            inventory=[{"template": "field_bandage", "quantity": 1}],
        )
        cmd = DummyCmdUse(cleric, encounter, "Field Bandage")

        CmdUse.func(cmd)

        self.assertIn("Field Bandage", cmd.last_message)
        self.assertEqual("item", encounter.db.pending_actions["7"]["kind"])
        self.assertEqual("field_bandage", encounter.db.pending_actions["7"]["item"])

    def test_combat_view_renders_none_target_ability_as_direct_command(self):
        warrior = DummyCombatCharacter(7, "Dad", "warrior", ["Strike", "Defend", "Battle Cry"], stamina=20, mana=0)
        encounter = DummyEncounterForView(warrior)

        view = build_combat_view(encounter, warrior)
        abilities = _view_action(view, "Abilities")
        battle_cry = _picker_option(abilities.get("picker", {}), "Battle Cry", meta="Battle Cry · 8 STA")

        self.assertEqual("use Battle Cry", battle_cry.get("command"))
        self.assertIsNone(battle_cry.get("picker"))

    def test_combat_view_renders_ranger_aoe_ability_as_direct_command(self):
        ranger = DummyCombatCharacter(8, "Scout", "ranger", ["Quick Shot", "Mark Prey", "Volley"], stamina=20, mana=0)
        encounter = DummyEncounterForView(ranger)

        view = build_combat_view(encounter, ranger)
        abilities = _view_action(view, "Abilities")
        volley = _picker_option(abilities.get("picker", {}), "Volley", meta="Volley · 10 STA")

        self.assertEqual("use Volley", volley.get("command"))
        self.assertIsNone(volley.get("picker"))

    def test_combat_view_renders_mage_aoe_ability_as_direct_command(self):
        mage = DummyCombatCharacter(9, "Hex", "mage", ["Firebolt", "Frost Bind", "Flame Wave"], stamina=0, mana=20)
        encounter = DummyEncounterForView(mage)

        view = build_combat_view(encounter, mage)
        abilities = _view_action(view, "Abilities")
        flame_wave = _picker_option(abilities.get("picker", {}), "Flame Wave", meta="Flame Wave · 14 MP")

        self.assertEqual("use Flame Wave", flame_wave.get("command"))
        self.assertIsNone(flame_wave.get("picker"))

    def test_enemy_targeting_prefers_visible_participants_over_hidden_ones(self):
        hidden = SimpleNamespace(
            id=7,
            key="Dad",
            db=SimpleNamespace(brave_resources={"hp": 30}),
        )
        visible = SimpleNamespace(
            id=8,
            key="Peep",
            db=SimpleNamespace(brave_resources={"hp": 18}),
        )
        encounter = SimpleNamespace(
            db=SimpleNamespace(threat={str(hidden.id): 12, str(visible.id): 3}),
            get_active_participants=lambda: [hidden, visible],
            _get_participant_state=lambda participant: {"stealth_turns": 1} if participant.id == hidden.id else {"stealth_turns": 0},
        )

        target = BraveEncounter._choose_enemy_target(encounter)

        self.assertEqual(visible, target)


if __name__ == "__main__":
    unittest.main()
