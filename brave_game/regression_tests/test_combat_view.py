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


class DummyRoom:
    def __init__(self, key="Brush Line"):
        self.key = key
        self.db = SimpleNamespace(
            brave_world="Brave",
            brave_zone="Whispering Woods",
        )


class DummyCharacter:
    def __init__(self, char_id, key, room, class_key, resources, derived, abilities):
        self.id = char_id
        self.key = key
        self.location = room
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_resources=resources,
            brave_derived_stats=derived,
        )
        self._abilities = list(abilities)

    def ensure_brave_character(self):
        return None

    def get_unlocked_abilities(self):
        return list(self._abilities)


class DummyEncounter:
    def __init__(self, room, participants, enemies, *, pending=None, states=None, title="Mire Teeth"):
        self.obj = room
        self.db = SimpleNamespace(round=2, encounter_title=title)
        self._participants = list(participants)
        self._enemies = list(enemies)
        self._pending = dict(pending or {})
        self._states = dict(states or {})

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return list(self._participants)

    def _describe_pending_action(self, character):
        return self._pending.get(character.id, "basic attack")

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
            },
        )


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


def _entry(section, title):
    for entry in section.get("items", []):
        if entry.get("title") == title:
            return entry
    raise AssertionError(f"Missing entry {title}")


def _item(section, prefix):
    for item in section.get("items", []):
        if item.get("text", "").startswith(prefix):
            return item
    raise AssertionError(f"Missing item {prefix}")


class CombatViewTests(unittest.TestCase):
    def test_targeted_ally_ability_uses_picker_targets(self):
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
            pending={7: "heal -> Peep"},
        )

        view = build_combat_view(encounter, healer)
        abilities = _section(view, "Abilities")

        heal_item = _item(abilities, "Heal")
        smite_item = _item(abilities, "Smite")

        self.assertEqual("A", heal_item.get("badge"))
        self.assertIsNone(heal_item.get("prefill"))
        self.assertIsNone(heal_item.get("command"))
        self.assertEqual("Heal Target", heal_item.get("picker", {}).get("title"))
        self.assertEqual(
            [
                {"label": "Dad", "command": "use Heal", "meta": "You"},
                {"label": "Peep", "command": "use Heal = Peep", "meta": "Ally"},
            ],
            [
                {
                    "label": option.get("label"),
                    "command": option.get("command"),
                    "meta": option.get("meta"),
                }
                for option in heal_item.get("picker", {}).get("options", [])
            ],
        )
        self.assertEqual("E", smite_item.get("badge"))
        self.assertEqual("use Smite = e1", smite_item.get("command"))
        self.assertEqual([], view.get("chips", []))
        self.assertEqual("", view.get("subtitle", ""))
        self.assertIn("TARGET", heal_item.get("text", ""))
        self.assertIn("8 MAN", smite_item.get("text", ""))

        party = _section(view, "Party")
        dad_entry = _entry(party, "Dad")
        peep_entry = _entry(party, "Peep")
        self.assertEqual(
            [("HP", "20 / 24"), ("MP", "18 / 20")],
            [(meter.get("label"), meter.get("value")) for meter in dad_entry.get("meters", [])],
        )
        self.assertEqual(
            [("HP", "17 / 26"), ("STA", "9 / 12")],
            [(meter.get("label"), meter.get("value")) for meter in peep_entry.get("meters", [])],
        )

    def test_unaffordable_ability_is_not_clickable(self):
        room = DummyRoom()
        healer = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 20, "mana": 4, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal"],
        )
        encounter = DummyEncounter(
            room,
            [healer],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        view = build_combat_view(encounter, healer)
        abilities = _section(view, "Abilities")
        heal_item = _item(abilities, "Heal")

        self.assertIsNone(heal_item.get("command"))
        self.assertIsNone(heal_item.get("prefill"))
        self.assertIsNone(heal_item.get("picker"))
        self.assertIn("NEED 6", heal_item.get("text", ""))


if __name__ == "__main__":
    unittest.main()
