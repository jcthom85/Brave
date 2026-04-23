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

from world.browser_views import build_combat_view
from world.combat_actions import build_combat_action_payload


class DummyRoom:
    def __init__(self, key="Brush Line"):
        self.key = key
        self.db = SimpleNamespace(
            brave_world="Brave",
            brave_zone="Whispering Woods",
        )


class DummyCharacter:
    def __init__(self, char_id, key, room, class_key, resources, derived, abilities, inventory=None):
        self.id = char_id
        self.key = key
        self.location = room
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_resources=resources,
            brave_derived_stats=derived,
            brave_inventory=list(inventory or []),
        )
        self._abilities = list(abilities)

    def ensure_brave_character(self):
        return None

    def get_unlocked_abilities(self):
        return list(self._abilities)


class DummyEncounter:
    def __init__(self, room, participants, enemies, *, pending=None, states=None, title="Mire Teeth"):
        self.obj = room
        self.db = SimpleNamespace(round=2, encounter_title=title, pending_actions=dict(pending or {}))
        self._participants = list(participants)
        self._enemies = list(enemies)
        self._states = dict(states or {})

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return list(self._participants)

    def _describe_pending_action(self, character):
        pending = self.db.pending_actions.get(str(character.id), {})
        return pending.get("label", "basic attack")

    def _get_participant_state(self, character):
        return self._states.get(
            character.id,
            {
                "guard": 0,
                "bleed_turns": 0,
                "poison_turns": 0,
                "curse_turns": 0,
                "snare_turns": 0,
                "feint_turns": 0,
                "stealth_turns": 0,
            },
        )


def _action(actions, key):
    for action in actions:
        if action.get("key") == key:
            return action
    raise AssertionError(f"Missing action {key}")


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


class CombatActionPayloadTests(unittest.TestCase):
    def test_ability_tooltip_includes_authored_summary_when_present(self):
        room = DummyRoom()
        mage = DummyCharacter(
            7,
            "Dad",
            room,
            "mage",
            {"hp": 20, "mana": 30, "stamina": 0},
            {"max_hp": 24, "max_mana": 30, "max_stamina": 0},
            ["Firebolt", "Arc Spark"],
        )
        encounter = DummyEncounter(
            room,
            [mage],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        payload = build_combat_action_payload(encounter, mage)
        firebolt = _action(payload["abilities"], "firebolt")

        self.assertIn("reliable burst of fire", firebolt.get("tooltip", ""))
        self.assertIn("Timing:", firebolt.get("tooltip", ""))

    def test_payload_normalizes_multi_target_ability_state(self):
        room = DummyRoom()
        healer = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 20, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal", "Smite"],
        )
        ally = DummyCharacter(
            8,
            "Peep",
            room,
            "warrior",
            {"hp": 17, "mana": 0, "stamina": 9},
            {"max_hp": 26, "max_mana": 0, "max_stamina": 12},
            ["Strike"],
        )
        encounter = DummyEncounter(
            room,
            [healer, ally],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        payload = build_combat_action_payload(encounter, healer)
        heal = _action(payload["abilities"], "heal")
        smite = _action(payload["abilities"], "smite")

        self.assertEqual("ability", heal.get("kind"))
        self.assertEqual("Heal", heal.get("source_label"))
        self.assertEqual("ally", heal.get("target_mode"))
        self.assertEqual("picker", heal.get("selection_mode"))
        self.assertTrue(heal.get("enabled"))
        self.assertIsNone(heal.get("disabled_reason"))
        self.assertEqual("Heal Target", heal.get("picker", {}).get("title"))
        self.assertEqual(
            ["use Heal", "use Heal = Peep"],
            [option.get("command") for option in heal.get("picker", {}).get("options", [])],
        )
        self.assertEqual("enemy", smite.get("target_mode"))
        self.assertEqual("use Smite = e1", smite.get("command"))
        self.assertIn("timing", heal)
        self.assertEqual(432, heal.get("timing", {}).get("gauge_cost"))
        self.assertFalse(heal.get("timing", {}).get("target_locked"))
        self.assertEqual(1, smite.get("timing", {}).get("windup_ticks"))
        self.assertIsNone(heal.get("reaction_role"))
        self.assertIn("Timing:", heal.get("tooltip", ""))

    def test_payload_normalizes_ally_target_item_state(self):
        room = DummyRoom()
        cleric = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 14, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal"],
            inventory=[{"template": "purity_salts", "quantity": 2}],
        )
        ally = DummyCharacter(
            8,
            "Peep",
            room,
            "warrior",
            {"hp": 17, "mana": 0, "stamina": 9},
            {"max_hp": 26, "max_mana": 0, "max_stamina": 12},
            ["Strike"],
        )
        encounter = DummyEncounter(room, [cleric, ally], [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}])

        payload = build_combat_action_payload(encounter, cleric)
        salts = _action(payload["items"], "purity_salts")

        self.assertEqual("item", salts.get("kind"))
        self.assertEqual("ally", salts.get("target_mode"))
        self.assertEqual("command+picker", salts.get("selection_mode"))
        self.assertEqual("use Purity Salts", salts.get("command"))
        self.assertEqual("2", salts.get("badge"))
        self.assertEqual("Target Ally", salts.get("actions", [])[0].get("label"))
        self.assertIn("timing", salts)
        self.assertEqual(0, salts.get("timing", {}).get("windup_ticks"))
        self.assertFalse(salts.get("timing", {}).get("target_locked"))
        self.assertEqual("cleanse", salts.get("reaction_role"))
        self.assertIn("cleanse tool", salts.get("tooltip", ""))
        self.assertEqual(
            ["use Purity Salts", "use Purity Salts = Peep"],
            [option.get("command") for option in salts.get("actions", [])[0].get("picker", {}).get("options", [])],
        )

    def test_view_exposes_raw_combat_actions_and_rendered_items_match(self):
        room = DummyRoom()
        cleric = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 14, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal", "Smite"],
            inventory=[{"template": "field_bandage", "quantity": 2}],
        )
        ally = DummyCharacter(
            8,
            "Peep",
            room,
            "warrior",
            {"hp": 17, "mana": 0, "stamina": 9},
            {"max_hp": 26, "max_mana": 0, "max_stamina": 12},
            ["Strike"],
        )
        encounter = DummyEncounter(room, [cleric, ally], [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}])

        view = build_combat_view(encounter, cleric)
        payload = view.get("combat_actions", {})
        abilities = _view_action(view, "Abilities")
        items = _view_action(view, "Items")
        heal_action = _action(payload.get("abilities", []), "heal")
        bandage_action = _action(payload.get("items", []), "field_bandage")
        heal_item = _picker_option(abilities.get("picker", {}), "Heal", meta="Heal · 10 MP")
        bandage_item = _picker_option(items.get("picker", {}), "Field Bandage", meta="Field Bandage · HP+18")

        self.assertEqual(heal_action.get("text"), heal_item.get("meta"))
        self.assertEqual(bandage_action.get("text"), bandage_item.get("meta"))
        self.assertEqual(bandage_action.get("command"), bandage_item.get("command"))
        self.assertEqual(bandage_action.get("tooltip"), bandage_item.get("tooltip"))

    def test_enemy_target_picker_uses_numbered_enemy_names(self):
        room = DummyRoom()
        rogue = DummyCharacter(
            7,
            "Dad",
            room,
            "rogue",
            {"hp": 16, "mana": 0, "stamina": 12},
            {"max_hp": 20, "max_mana": 0, "max_stamina": 12},
            ["Cheap Shot"],
        )
        encounter = DummyEncounter(
            room,
            [rogue],
            [
                {"id": "e1", "key": "Grave Crow", "hp": 9, "max_hp": 12, "template_key": "grave_crow"},
                {"id": "e2", "key": "Grave Crow", "hp": 9, "max_hp": 12, "template_key": "grave_crow"},
            ],
        )

        payload = build_combat_action_payload(encounter, rogue)
        action = _action(payload["abilities"], "cheapshot")

        self.assertEqual(
            ["Grave Crow 1", "Grave Crow 2"],
            [option.get("label") for option in action.get("picker", {}).get("options", [])],
        )
        self.assertEqual(
            ["use Cheap Shot = e1", "use Cheap Shot = e2"],
            [option.get("command") for option in action.get("picker", {}).get("options", [])],
        )

    def test_emote_action_targets_enemies_in_combat(self):
        room = DummyRoom()
        rogue = DummyCharacter(
            7,
            "Dad",
            room,
            "rogue",
            {"hp": 16, "mana": 0, "stamina": 12},
            {"max_hp": 20, "max_mana": 0, "max_stamina": 12},
            ["Cheap Shot"],
        )
        encounter = DummyEncounter(
            room,
            [rogue],
            [
                {"id": "e1", "key": "Bandit Raider", "hp": 9, "max_hp": 12, "template_key": "bandit_raider"},
                {"id": "e2", "key": "Bandit Raider", "hp": 9, "max_hp": 12, "template_key": "bandit_raider"},
            ],
        )

        payload = build_combat_action_payload(encounter, rogue)
        emote = _action(payload["emotes"], "emote")

        self.assertEqual("social", emote.get("kind"))
        self.assertEqual("Emote", emote.get("label"))
        self.assertEqual("Emote At", emote.get("picker", {}).get("title"))
        self.assertEqual(
            ["Bandit Raider 1", "Bandit Raider 2"],
            [option.get("label") for option in emote.get("picker", {}).get("options", [])],
        )
        self.assertEqual(
            ["emote = e1", "emote = e2"],
            [option.get("command") for option in emote.get("picker", {}).get("options", [])],
        )
        self.assertEqual(
            "Emote At Bandit Raider 1",
            emote.get("picker", {}).get("options", [])[0].get("picker", {}).get("title"),
        )


if __name__ == "__main__":
    unittest.main()
