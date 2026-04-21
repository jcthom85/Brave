import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter


class DummyCharacter:
    def __init__(self, char_id=7, class_key="warrior"):
        self.id = char_id
        self.key = "Dad"
        self.db = SimpleNamespace(brave_class=class_key)


class CombatAtbLoopTests(unittest.TestCase):
    def test_advance_player_atb_starts_charging_before_resolution(self):
        character = DummyCharacter()
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}, pending_actions={str(character.id): {"kind": "attack", "target": None}}),
            resolved=[],
        )

        encounter._actor_atb_key = lambda character=None, enemy=None, companion=None: BraveEncounter._actor_atb_key(encounter, character=character, enemy=enemy, companion=companion)
        encounter._default_atb_fill_rate = lambda character=None, enemy=None, companion=None: 100
        encounter._atb_tick_ms = lambda: 1000
        encounter._get_actor_atb_state = lambda character=None, enemy=None, companion=None: BraveEncounter._get_actor_atb_state(encounter, character=character, enemy=enemy, companion=companion)
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None, companion=None: BraveEncounter._save_actor_atb_state(encounter, state, character=character, enemy=enemy, companion=companion)
        encounter._consume_player_pending_action = lambda character: BraveEncounter._consume_player_pending_action(encounter, character)
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._resolve_player_action = lambda character, action: encounter.resolved.append((character.id, dict(action)))

        BraveEncounter._advance_player_atb(encounter, character)

        self.assertEqual([], encounter.resolved)
        state = encounter.db.atb_states["p:7"]
        self.assertEqual("charging", state["phase"])
        self.assertEqual(4, state["ticks_remaining"])
        self.assertEqual({str(character.id): {"kind": "attack", "target": None}}, encounter.db.pending_actions)

    def test_advance_enemy_atb_starts_charging_before_resolution(self):
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}),
            resolved=[],
        )

        encounter._actor_atb_key = lambda character=None, enemy=None, companion=None: BraveEncounter._actor_atb_key(encounter, character=character, enemy=enemy, companion=companion)
        encounter._default_atb_fill_rate = lambda character=None, enemy=None, companion=None: 100
        encounter._atb_tick_ms = lambda: 1000
        encounter._get_actor_atb_state = lambda character=None, enemy=None, companion=None: BraveEncounter._get_actor_atb_state(encounter, character=character, enemy=enemy, companion=companion)
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None, companion=None: BraveEncounter._save_actor_atb_state(encounter, state, character=character, enemy=enemy, companion=companion)
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
        encounter.obj = SimpleNamespace(msg_contents=lambda _text: None)
        encounter._execute_enemy_turn = lambda enemy: encounter.resolved.append(enemy["id"])

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual([], encounter.resolved)
        state = encounter.db.atb_states["e:e1"]
        self.assertEqual("charging", state["phase"])
        self.assertEqual(4, state["ticks_remaining"])

    def test_advance_enemy_atb_keeps_winding_enemy_in_charging_phase_until_ready(self):
        enemy = {"id": "e1", "template_key": "old_greymaw", "key": "Old Greymaw"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}),
            resolved=[],
            messages=[],
            obj=SimpleNamespace(msg_contents=lambda text: encounter.messages.append(text)),
        )

        encounter._actor_atb_key = lambda character=None, enemy=None, companion=None: BraveEncounter._actor_atb_key(encounter, character=character, enemy=enemy, companion=companion)
        encounter._default_atb_fill_rate = lambda character=None, enemy=None, companion=None: 100
        encounter._atb_tick_ms = lambda: 1000
        encounter._get_actor_atb_state = lambda character=None, enemy=None, companion=None: BraveEncounter._get_actor_atb_state(encounter, character=character, enemy=enemy, companion=companion)
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None, companion=None: BraveEncounter._save_actor_atb_state(encounter, state, character=character, enemy=enemy, companion=companion)
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
        encounter._execute_enemy_turn = lambda enemy: encounter.resolved.append(enemy["id"])

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual([], encounter.resolved)
        state = encounter.db.atb_states["e:e1"]
        self.assertEqual("charging", state["phase"])
        self.assertIsNone(state["current_action"])
        self.assertEqual([], encounter.messages)

    def test_telegraph_uses_enemy_gender_pronouns(self):
        female_enemy = {"id": "e2", "template_key": "sir_edric_restless", "key": "Dame Edric", "gender": "female"}
        nonbinary_enemy = {"id": "e3", "template_key": "captain_varn_blackreed", "key": "Captain Reed", "gender": "non-binary"}
        encounter = SimpleNamespace()
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)

        female_message = BraveEncounter._enemy_telegraph_message(encounter, female_enemy)
        nonbinary_message = BraveEncounter._enemy_telegraph_message(encounter, nonbinary_enemy)

        self.assertIn("raises her blade", female_message)
        self.assertIn("shifts their stance", nonbinary_message)


if __name__ == "__main__":
    unittest.main()
