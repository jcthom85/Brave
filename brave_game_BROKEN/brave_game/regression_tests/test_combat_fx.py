import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter


class DummyAttacker:
    def __init__(self, char_id, key):
        self.id = char_id
        self.key = key
        self.db = SimpleNamespace(brave_class="warrior")


class CombatFxTests(unittest.TestCase):
    @patch("world.browser_panels.send_webclient_event")
    def test_emit_combat_fx_includes_remaining_turn_lock(self, send_event):
        participant = SimpleNamespace(location="room")
        encounter = SimpleNamespace(
            obj="room",
            db=SimpleNamespace(atb_turn_lock_until_ms=2_200),
            get_active_participants=lambda: [participant],
        )

        with patch("typeclasses.scripts.time.time", return_value=2.0):
            BraveEncounter._emit_combat_fx(encounter, kind="damage", source="Dad", target="Bog Wolf")

        self.assertEqual(200, send_event.call_args.kwargs["brave_combat_fx"]["lock_ms"])

    def test_damage_enemy_emits_stable_entry_refs(self):
        events = []
        messages = []
        attacker = DummyAttacker(7, "Dad")
        enemy = {
            "id": "e1",
            "key": "Grave Crow",
            "hp": 12,
            "marked_turns": 0,
            "shielded": False,
            "tags": [],
        }
        encounter = SimpleNamespace(
            _save_enemy=lambda current_enemy: None,
            _add_threat=lambda character, amount: None,
            _record_participant_contribution=lambda character, **kwargs: None,
            _emit_combat_fx=lambda **event: events.append(event),
            _emit_defeat_fx=lambda target, text="DOWN": None,
            _award_enemy_defeat_credit=lambda target: None,
            obj=SimpleNamespace(msg_contents=lambda message, **kwargs: messages.append(message)),
        )

        BraveEncounter._damage_enemy(encounter, attacker, enemy, 5)

        self.assertEqual(1, len(events))
        self.assertEqual("Dad", events[0]["source"])
        self.assertEqual("Grave Crow", events[0]["target"])
        self.assertEqual("p:7", events[0]["source_ref"])
        self.assertEqual("e:e1", events[0]["target_ref"])

    def test_emit_defeat_fx_includes_target_entry_ref(self):
        events = []
        encounter = SimpleNamespace(_emit_combat_fx=lambda **event: events.append(event))

        BraveEncounter._emit_defeat_fx(encounter, {"id": "e2", "key": "Grave Crow"})

        self.assertEqual(
            {
                "kind": "defeat",
                "target": "Grave Crow",
                "target_ref": "e:e2",
                "text": "DOWN",
                "tone": "break",
                "impact": "break",
                "defeat": True,
            },
            events[0],
        )

    def test_heal_enemy_emits_structured_heal_fx(self):
        events = []
        messages = []
        source_enemy = {"id": "e1", "key": "Barrow Wisp", "hp": 12, "max_hp": 12}
        target_enemy = {"id": "e2", "key": "Bog Wolf", "hp": 5, "max_hp": 16}
        encounter = SimpleNamespace(
            _save_enemy=lambda current_enemy: None,
            _emit_combat_fx=lambda **event: events.append(event),
            obj=SimpleNamespace(msg_contents=lambda message, **kwargs: messages.append(message)),
        )

        healed = BraveEncounter._heal_enemy(encounter, source_enemy, target_enemy, 6)

        self.assertTrue(healed)
        self.assertEqual(11, target_enemy["hp"])
        self.assertEqual("Barrow Wisp", events[0]["source"])
        self.assertEqual("Bog Wolf", events[0]["target"])
        self.assertEqual("e:e1", events[0]["source_ref"])
        self.assertEqual("e:e2", events[0]["target_ref"])
        self.assertEqual("heal", events[0]["kind"])
        self.assertTrue(any("mends Bog Wolf for 6 HP" in message for message in messages))

    def test_enemy_bleed_tick_emits_structured_damage_fx(self):
        enemy = {
            "id": "e4",
            "key": "Mire Hound",
            "hp": 10,
            "max_hp": 18,
            "bleed_turns": 1,
            "bleed_damage": 3,
            "poison_turns": 0,
            "poison_damage": 0,
        }
        events = []
        encounter = SimpleNamespace(
            get_active_enemies=lambda: [enemy],
            _save_enemy=lambda current_enemy: None,
            _emit_combat_fx=lambda **event: events.append(event),
            _emit_defeat_fx=Mock(),
            _award_enemy_defeat_credit=Mock(),
            obj=SimpleNamespace(msg_contents=lambda message, **kwargs: None),
        )

        BraveEncounter._apply_enemy_effects(encounter)

        self.assertEqual(7, enemy["hp"])
        self.assertEqual(1, len(events))
        self.assertEqual("damage", events[0]["kind"])
        self.assertEqual("e:e4", events[0]["target_ref"])
        self.assertEqual("bleed", events[0]["element"])

    def test_enemy_dot_kill_uses_defeat_fx_path(self):
        enemy = {
            "id": "e3",
            "key": "Bog Wolf",
            "hp": 2,
            "max_hp": 12,
            "bleed_turns": 0,
            "bleed_damage": 0,
            "poison_turns": 1,
            "poison_damage": 3,
        }
        messages = []
        encounter = SimpleNamespace(
            get_active_enemies=lambda: [enemy],
            _save_enemy=lambda current_enemy: None,
            _emit_combat_fx=lambda **event: None,
            _emit_defeat_fx=Mock(),
            _award_enemy_defeat_credit=Mock(),
            obj=SimpleNamespace(msg_contents=lambda message, **kwargs: messages.append(message)),
        )

        BraveEncounter._apply_enemy_effects(encounter)

        encounter._emit_defeat_fx.assert_called_once_with(enemy)
        encounter._award_enemy_defeat_credit.assert_called_once_with(enemy)
        self.assertTrue(any("Bog Wolf falls." in message for message in messages))


if __name__ == "__main__":
    unittest.main()
