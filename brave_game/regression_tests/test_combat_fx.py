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

from typeclasses.scripts import BraveEncounter, _combat_entry_ref


class DummyFxEncounter:
    def __init__(self):
        self.events = []

    def _emit_combat_fx(self, **event):
        self.events.append(event)


class CombatFxTests(unittest.TestCase):
    def test_combat_entry_ref_distinguishes_players_and_enemies(self):
        character = SimpleNamespace(id=17, key="Dad")
        enemy = {"id": "e2", "key": "Bog Wolf"}

        self.assertEqual("p:17", _combat_entry_ref(character))
        self.assertEqual("e:e2", _combat_entry_ref(enemy))

    def test_miss_fx_includes_stable_source_and_target_refs(self):
        encounter = DummyFxEncounter()
        character = SimpleNamespace(id=17, key="Dad")
        enemy = {"id": "e2", "key": "Bog Wolf"}

        BraveEncounter._emit_miss_fx(encounter, character, enemy)

        self.assertEqual(1, len(encounter.events))
        event = encounter.events[0]
        self.assertEqual("Dad", event.get("source"))
        self.assertEqual("p:17", event.get("source_ref"))
        self.assertEqual("Bog Wolf", event.get("target"))
        self.assertEqual("e:e2", event.get("target_ref"))
        self.assertTrue(event.get("lunge"))

    def test_action_announcement_does_not_leak_fx_marker(self):
        messages = []
        events = []
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message: messages.append(message)),
            _emit_combat_fx=lambda **event: events.append(event),
        )
        character = SimpleNamespace(key="Dad")

        BraveEncounter._announce_combat_action(encounter, character, "Strike")

        self.assertEqual(["|cDad uses Strike!|n"], messages)
        self.assertNotIn("BRAVEFX", messages[0])
        self.assertEqual([{"kind": "action", "actor": "Dad", "label": "Strike"}], events)

    def test_lethal_damage_fx_marks_defeat_on_damage_event(self):
        events = []
        attacker = SimpleNamespace(
            id=17,
            key="Dad",
            db=SimpleNamespace(brave_class="warrior"),
        )
        enemy = {
            "id": "e2",
            "key": "Bog Wolf",
            "hp": 5,
            "max_hp": 12,
            "armor": 0,
            "marked_turns": 0,
            "shielded": False,
        }
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda *_args, **_kwargs: None),
            _save_enemy=lambda _enemy: None,
            _add_threat=lambda *_args, **_kwargs: None,
            _record_participant_contribution=lambda *_args, **_kwargs: None,
            _emit_combat_fx=lambda **event: events.append(event),
            _emit_defeat_fx=lambda _target, text="DOWN": None,
            _award_enemy_defeat_credit=lambda _enemy: None,
            get_active_enemies=lambda: [],
            _schedule_victory_sequence=lambda *_args, **_kwargs: None,
        )

        BraveEncounter._damage_enemy(encounter, attacker, enemy, 10)

        self.assertTrue(events[0].get("defeat"))
        self.assertEqual("e:e2", events[0].get("target_ref"))


if __name__ == "__main__":
    unittest.main()
