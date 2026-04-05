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
    def test_advance_player_atb_consumes_pending_action_and_enters_recovery(self):
        character = DummyCharacter()
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}, pending_actions={str(character.id): {"kind": "attack", "target": None}}),
            resolved=[],
        )

        encounter._actor_atb_key = lambda character=None, enemy=None: BraveEncounter._actor_atb_key(encounter, character=character, enemy=enemy)
        encounter._default_atb_fill_rate = lambda character=None, enemy=None: 100
        encounter._get_actor_atb_state = lambda character=None, enemy=None: BraveEncounter._get_actor_atb_state(encounter, character=character, enemy=enemy)
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None: BraveEncounter._save_actor_atb_state(encounter, state, character=character, enemy=enemy)
        encounter._consume_player_pending_action = lambda character: BraveEncounter._consume_player_pending_action(encounter, character)
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._resolve_player_action = lambda character, action: encounter.resolved.append((character.id, dict(action)))

        BraveEncounter._advance_player_atb(encounter, character)

        self.assertEqual([(character.id, {"kind": "attack", "target": None})], encounter.resolved)
        state = encounter.db.atb_states["p:7"]
        self.assertEqual("recovering", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])
        self.assertEqual({}, encounter.db.pending_actions)

    def test_advance_enemy_atb_executes_and_enters_recovery(self):
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}),
            resolved=[],
        )

        encounter._actor_atb_key = lambda character=None, enemy=None: BraveEncounter._actor_atb_key(encounter, character=character, enemy=enemy)
        encounter._default_atb_fill_rate = lambda character=None, enemy=None: 100
        encounter._get_actor_atb_state = lambda character=None, enemy=None: BraveEncounter._get_actor_atb_state(encounter, character=character, enemy=enemy)
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None: BraveEncounter._save_actor_atb_state(encounter, state, character=character, enemy=enemy)
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
        encounter.obj = SimpleNamespace(msg_contents=lambda _text: None)
        encounter._execute_enemy_turn = lambda enemy: encounter.resolved.append(enemy["id"])

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual(["e1"], encounter.resolved)
        state = encounter.db.atb_states["e:e1"]
        self.assertEqual("recovering", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])

    def test_advance_enemy_atb_announces_named_telegraph_for_winding_enemy(self):
        enemy = {"id": "e1", "template_key": "old_greymaw", "key": "Old Greymaw"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}),
            resolved=[],
            messages=[],
            obj=SimpleNamespace(msg_contents=lambda text: encounter.messages.append(text)),
        )

        encounter._actor_atb_key = lambda character=None, enemy=None: BraveEncounter._actor_atb_key(encounter, character=character, enemy=enemy)
        encounter._default_atb_fill_rate = lambda character=None, enemy=None: 100
        encounter._get_actor_atb_state = lambda character=None, enemy=None: BraveEncounter._get_actor_atb_state(encounter, character=character, enemy=enemy)
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None: BraveEncounter._save_actor_atb_state(encounter, state, character=character, enemy=enemy)
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
        encounter._execute_enemy_turn = lambda enemy: encounter.resolved.append(enemy["id"])

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual([], encounter.resolved)
        state = encounter.db.atb_states["e:e1"]
        self.assertEqual("winding", state["phase"])
        self.assertEqual("Brush Pounce", state["current_action"]["label"])
        self.assertTrue(any("Brush Pounce" in message for message in encounter.messages))


if __name__ == "__main__":
    unittest.main()
