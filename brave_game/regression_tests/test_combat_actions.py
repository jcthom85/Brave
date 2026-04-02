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


class CombatActionPayloadTests(unittest.TestCase):
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
        abilities = _section(view, "Abilities")
        items = _section(view, "Items")
        heal_action = _action(payload.get("abilities", []), "heal")
        bandage_action = _action(payload.get("items", []), "field_bandage")
        heal_item = _item(abilities, "Heal")
        bandage_item = _item(items, "Field Bandage")

        self.assertEqual(heal_action.get("text"), heal_item.get("text"))
        self.assertEqual(bandage_action.get("text"), bandage_item.get("text"))
        self.assertEqual(bandage_action.get("command"), bandage_item.get("command"))


if __name__ == "__main__":
    unittest.main()
