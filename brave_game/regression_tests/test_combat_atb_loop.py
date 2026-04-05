import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
            refreshed=0,
        )

        encounter._actor_atb_key = lambda character=None, enemy=None: BraveEncounter._actor_atb_key(encounter, character=character, enemy=enemy)
        encounter._default_atb_fill_rate = lambda character=None, enemy=None: 100
        encounter._get_actor_atb_state = lambda character=None, enemy=None: BraveEncounter._get_actor_atb_state(encounter, character=character, enemy=enemy)
        encounter._save_actor_atb_state = lambda state, character=None, enemy=None: BraveEncounter._save_actor_atb_state(encounter, state, character=character, enemy=enemy)
        encounter._consume_player_pending_action = lambda character: BraveEncounter._consume_player_pending_action(encounter, character)
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._resolve_player_action = lambda character, action: encounter.resolved.append((character.id, dict(action)))
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: None
        encounter._remaining_combat_turn_lock_ms = lambda now_ms=None: 0

        BraveEncounter._advance_player_atb(encounter, character)

        self.assertEqual([(character.id, {"kind": "attack", "target": None})], encounter.resolved)
        self.assertEqual(0, encounter.refreshed)
        state = encounter.db.atb_states["p:7"]
        self.assertEqual("recovering", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])
        self.assertEqual({}, encounter.db.pending_actions)

    def test_advance_enemy_atb_executes_and_enters_recovery(self):
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}),
            resolved=[],
            refreshed=0,
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
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: None
        encounter._remaining_combat_turn_lock_ms = lambda now_ms=None: 0

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual(["e1"], encounter.resolved)
        self.assertEqual(0, encounter.refreshed)
        state = encounter.db.atb_states["e:e1"]
        self.assertEqual("recovering", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])

    def test_advance_enemy_atb_announces_named_telegraph_for_winding_enemy(self):
        enemy = {"id": "e1", "template_key": "old_greymaw", "key": "Old Greymaw"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(atb_states={}),
            resolved=[],
            messages=[],
            refreshed=0,
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
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual([], encounter.resolved)
        self.assertEqual(1, encounter.refreshed)
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
        encounter._set_combat_turn_lock = lambda duration_ms=450, now_ms=None: None
        encounter._remaining_combat_turn_lock_ms = lambda now_ms=None: 0
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

    def test_at_repeat_freezes_other_atb_states_while_enemy_action_resolves(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "old_greymaw", "key": "Old Greymaw"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                round=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 40, "ready_gauge": 100, "fill_rate": 25},
                    "e:e1": {
                        "phase": "winding",
                        "ticks_remaining": 1,
                        "ready_gauge": 100,
                        "fill_rate": 100,
                        "timing": {"windup_ticks": 1, "recovery_ticks": 1},
                        "current_action": {"kind": "enemy_attack", "enemy_id": "e1", "label": "Brush Pounce"},
                    },
                },
                pending_actions={},
            ),
            resolved=[],
            refreshed=0,
            messages=[],
            obj=SimpleNamespace(msg_contents=lambda text: encounter.messages.append(text)),
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
        encounter._active_atb_actor = lambda participants, enemies: BraveEncounter._active_atb_actor(
            encounter,
            participants,
            enemies,
        )
        encounter._next_atb_actor = lambda participants, enemies: BraveEncounter._next_atb_actor(
            encounter,
            participants,
            enemies,
        )
        encounter._tick_all_atb_states = lambda participants, enemies: BraveEncounter._tick_all_atb_states(
            encounter,
            participants,
            enemies,
        )
        encounter._handle_player_atb_state = lambda character: BraveEncounter._handle_player_atb_state(encounter, character)
        encounter._handle_enemy_atb_state = lambda enemy: BraveEncounter._handle_enemy_atb_state(encounter, enemy)
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_round_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._execute_enemy_turn = lambda enemy: encounter.resolved.append(("enemy", enemy["id"]))

        BraveEncounter.at_repeat(encounter)

        self.assertEqual([("enemy", "e1")], encounter.resolved)
        self.assertEqual(40, encounter.db.atb_states["p:7"]["gauge"])
        self.assertEqual("charging", encounter.db.atb_states["p:7"]["phase"])
        self.assertEqual("resolving", encounter.db.atb_states["e:e1"]["phase"])
        self.assertTrue(encounter.db.atb_states["e:e1"]["current_action"]["executed"])

    def test_at_repeat_breaks_exact_ready_ties_by_fill_rate(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                round=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 0, "ready_gauge": 100, "fill_rate": 100},
                    "e:e1": {"phase": "charging", "gauge": 0, "ready_gauge": 100, "fill_rate": 120},
                },
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
        encounter._active_atb_actor = lambda participants, enemies: BraveEncounter._active_atb_actor(
            encounter,
            participants,
            enemies,
        )
        encounter._next_atb_actor = lambda participants, enemies: BraveEncounter._next_atb_actor(
            encounter,
            participants,
            enemies,
        )
        encounter._tick_all_atb_states = lambda participants, enemies: BraveEncounter._tick_all_atb_states(
            encounter,
            participants,
            enemies,
        )
        encounter._handle_player_atb_state = lambda character: BraveEncounter._handle_player_atb_state(encounter, character)
        encounter._handle_enemy_atb_state = lambda enemy: BraveEncounter._handle_enemy_atb_state(encounter, enemy)
        encounter._consume_player_pending_action = lambda character: BraveEncounter._consume_player_pending_action(
            encounter,
            character,
        )
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._set_combat_turn_lock = lambda duration_ms=450, now_ms=None: None
        encounter._remaining_combat_turn_lock_ms = lambda now_ms=None: 0
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
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

        self.assertEqual([("enemy", "e1")], encounter.resolved)
        self.assertEqual("recovering", encounter.db.atb_states["e:e1"]["phase"])
        self.assertEqual("ready", encounter.db.atb_states["p:7"]["phase"])

    def test_at_repeat_keeps_acting_enemy_resolving_during_turn_lock(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                round=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 35, "ready_gauge": 100, "fill_rate": 25},
                    "e:e1": {"phase": "charging", "gauge": 0, "ready_gauge": 100, "fill_rate": 120},
                },
                pending_actions={},
                atb_turn_lock_until_ms=0,
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
        encounter._handle_player_atb_state = lambda character: BraveEncounter._handle_player_atb_state(encounter, character)
        encounter._handle_enemy_atb_state = lambda enemy: BraveEncounter._handle_enemy_atb_state(encounter, enemy)
        encounter._enemy_action_timing = lambda enemy: BraveEncounter._enemy_action_timing(encounter, enemy)
        encounter._enemy_action_label = lambda enemy: BraveEncounter._enemy_action_label(encounter, enemy)
        encounter._enemy_telegraph_message = lambda enemy: BraveEncounter._enemy_telegraph_message(encounter, enemy)
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
        encounter._combat_turn_locked = lambda now_ms=None: int(now_ms or 0) < int(encounter.db.atb_turn_lock_until_ms or 0)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: setattr(encounter.db, "atb_turn_lock_until_ms", 2200)
        encounter._remaining_combat_turn_lock_ms = lambda now_ms=None: max(0, int(encounter.db.atb_turn_lock_until_ms or 0) - int(now_ms or 0))
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_round_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._execute_enemy_turn = lambda enemy: encounter.resolved.append(("enemy", enemy["id"]))

        with patch("typeclasses.scripts.time.time", return_value=1.0):
            BraveEncounter.at_repeat(encounter)

        self.assertEqual([("enemy", "e1")], encounter.resolved)
        self.assertEqual("charging", encounter.db.atb_states["p:7"]["phase"])
        self.assertEqual(60, encounter.db.atb_states["p:7"]["gauge"])
        self.assertEqual("resolving", encounter.db.atb_states["e:e1"]["phase"])
        self.assertTrue(encounter.db.atb_states["e:e1"]["current_action"]["executed"])

    def test_at_repeat_waits_for_turn_lock_before_next_ready_actor(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                round=0,
                atb_states={
                    "p:7": {
                        "phase": "charging",
                        "gauge": 0,
                        "ready_gauge": 100,
                        "fill_rate": 100,
                        "phase_started_at_ms": 1_000,
                        "phase_duration_ms": 1_000,
                        "phase_start_gauge": 0,
                    },
                    "e:e1": {
                        "phase": "charging",
                        "gauge": 0,
                        "ready_gauge": 100,
                        "fill_rate": 100,
                        "phase_started_at_ms": 1_000,
                        "phase_duration_ms": 1_000,
                        "phase_start_gauge": 0,
                    },
                },
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
                atb_turn_lock_until_ms=0,
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
        encounter._combat_turn_locked = lambda now_ms=None: int(now_ms or 0) < int(encounter.db.atb_turn_lock_until_ms or 0)
        encounter._set_combat_turn_lock = lambda duration_ms=450, now_ms=None: setattr(
            encounter.db,
            "atb_turn_lock_until_ms",
            1450,
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

        with patch("world.combat_atb.time.time", return_value=1.0):
            with patch("typeclasses.scripts.time.time", return_value=1.0):
                BraveEncounter.at_repeat(encounter)
            with patch("typeclasses.scripts.time.time", return_value=1.2):
                BraveEncounter.at_repeat(encounter)
            with patch("typeclasses.scripts.time.time", return_value=2.0):
                BraveEncounter.at_repeat(encounter)

        self.assertEqual(
            [
                ("player", character.id, {"kind": "attack", "target": None}),
                ("enemy", "e1"),
            ],
            encounter.resolved,
        )
        self.assertEqual(2, encounter.db.round)
        self.assertGreater(encounter.db.atb_turn_lock_until_ms, 1000)
        self.assertEqual(4, encounter.refreshed)


if __name__ == "__main__":
    unittest.main()
