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

    def test_at_repeat_resolves_one_ready_actor_per_repeat(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                round=0,
                atb_states={},
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
            ),
            resolved=[],
            refreshed=0,
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        encounter._actor_atb_key = lambda character=None, enemy=None: BraveEncounter._actor_atb_key(
            encounter,
            character=character,
            enemy=enemy,
        )
        encounter._default_atb_fill_rate = lambda character=None, enemy=None: 100
        encounter._get_actor_atb_state = lambda character=None, enemy=None: BraveEncounter._get_actor_atb_state(
            encounter,
            character=character,
            enemy=enemy,
        )
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None: BraveEncounter._save_actor_atb_state(
            encounter,
            state,
            character=character,
            enemy=enemy,
        )
        encounter._consume_player_pending_action = lambda character: BraveEncounter._consume_player_pending_action(
            encounter,
            character,
        )
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
        encounter._handle_player_atb_state = lambda character: BraveEncounter._handle_player_atb_state(encounter, character)
        encounter._handle_enemy_atb_state = lambda enemy: BraveEncounter._handle_enemy_atb_state(encounter, enemy)
        encounter._tick_all_atb_states = lambda participants, enemies: BraveEncounter._tick_all_atb_states(
            encounter,
            participants,
            enemies,
        )
        encounter._next_atb_actor = lambda participants, enemies: BraveEncounter._next_atb_actor(
            encounter,
            participants,
            enemies,
        )
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_round_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._resolve_player_action = lambda character, action: encounter.resolved.append(
            ("player", character.id, dict(action))
        )
        encounter._execute_enemy_turn = lambda enemy: encounter.resolved.append(("enemy", enemy["id"]))

        BraveEncounter.at_repeat(encounter)

        self.assertEqual(1, encounter.db.round)
        self.assertEqual([("player", character.id, {"kind": "attack", "target": None})], encounter.resolved)
        self.assertEqual("recovering", encounter.db.atb_states["p:7"]["phase"])
        self.assertEqual("ready", encounter.db.atb_states["e:e1"]["phase"])
        self.assertEqual(1, encounter.refreshed)

        BraveEncounter.at_repeat(encounter)

        self.assertEqual(
            [
                ("player", character.id, {"kind": "attack", "target": None}),
                ("enemy", "e1"),
            ],
            encounter.resolved,
        )
        self.assertEqual("recovering", encounter.db.atb_states["e:e1"]["phase"])
        self.assertEqual(2, encounter.refreshed)


if __name__ == "__main__":
    unittest.main()
