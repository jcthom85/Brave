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
    def _bind_common_helpers(self, encounter):
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

    def _bind_loop_helpers(self, encounter):
        self._bind_common_helpers(encounter)
        encounter._active_atb_actor = lambda participants, enemies: BraveEncounter._active_atb_actor(
            encounter,
            participants,
            enemies,
        )
        encounter._advance_idle_atb_states = lambda participants, enemies: BraveEncounter._advance_idle_atb_states(
            encounter,
            participants,
            enemies,
        )
        encounter._next_atb_actor = lambda participants, enemies: BraveEncounter._next_atb_actor(
            encounter,
            participants,
            enemies,
        )
        encounter._handle_player_atb_state = lambda character: BraveEncounter._handle_player_atb_state(encounter, character)
        encounter._handle_enemy_atb_state = lambda enemy: BraveEncounter._handle_enemy_atb_state(encounter, enemy)

    def test_advance_player_atb_starts_windup_then_resolves_default_attack(self):
        character = DummyCharacter()
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                atb_states={
                    "p:7": {"phase": "ready", "gauge": 400, "ready_gauge": 400, "fill_rate": 100}
                },
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
            ),
            resolved=[],
            refreshed=0,
        )

        self._bind_common_helpers(encounter)
        encounter._consume_player_pending_action = lambda actor: BraveEncounter._consume_player_pending_action(encounter, actor)
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._resolve_player_action = lambda actor, action: encounter.resolved.append((actor.id, dict(action)))
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: None

        BraveEncounter._advance_player_atb(encounter, character)

        self.assertEqual([], encounter.resolved)
        self.assertEqual(1, encounter.refreshed)
        self.assertEqual({}, encounter.db.pending_actions)
        self.assertEqual("winding", encounter.db.atb_states["p:7"]["phase"])

        BraveEncounter._advance_player_atb(encounter, character)

        self.assertEqual([(character.id, {"kind": "attack", "target": None})], encounter.resolved)
        state = encounter.db.atb_states["p:7"]
        self.assertEqual("charging", state["phase"])
        self.assertEqual(0, state["gauge"])
        self.assertEqual(2, encounter.refreshed)

    def test_advance_enemy_atb_starts_windup_then_resolves_default_attack(self):
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                atb_states={
                    "e:e1": {"phase": "ready", "gauge": 400, "ready_gauge": 400, "fill_rate": 100}
                }
            ),
            resolved=[],
            refreshed=0,
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        self._bind_common_helpers(encounter)
        encounter._enemy_action_timing = lambda actor: BraveEncounter._enemy_action_timing(encounter, actor)
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(actor["id"])
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: None

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual([], encounter.resolved)
        self.assertEqual(1, encounter.refreshed)
        self.assertEqual("winding", encounter.db.atb_states["e:e1"]["phase"])

        BraveEncounter._advance_enemy_atb(encounter, enemy)

        self.assertEqual(["e1"], encounter.resolved)
        state = encounter.db.atb_states["e:e1"]
        self.assertEqual("charging", state["phase"])
        self.assertEqual(0, state["gauge"])
        self.assertEqual(2, encounter.refreshed)

    def test_advance_enemy_atb_announces_named_telegraph_for_winding_enemy(self):
        enemy = {"id": "e1", "template_key": "old_greymaw", "key": "Old Greymaw"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                atb_states={
                    "e:e1": {"phase": "ready", "gauge": 400, "ready_gauge": 400, "fill_rate": 100}
                }
            ),
            resolved=[],
            messages=[],
            refreshed=0,
            obj=SimpleNamespace(msg_contents=lambda text: encounter.messages.append(text)),
        )

        self._bind_common_helpers(encounter)
        encounter._enemy_action_timing = lambda actor: BraveEncounter._enemy_action_timing(encounter, actor)
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(actor["id"])
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
                turn_count=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 300, "ready_gauge": 400, "fill_rate": 100},
                    "e:e1": {"phase": "charging", "gauge": 300, "ready_gauge": 400, "fill_rate": 100},
                },
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
            ),
            resolved=[],
            refreshed=0,
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        self._bind_loop_helpers(encounter)
        encounter._consume_player_pending_action = lambda actor: BraveEncounter._consume_player_pending_action(encounter, actor)
        encounter._player_action_timing = lambda _action: {"windup_ticks": 0, "recovery_ticks": 0}
        encounter._enemy_action_timing = lambda _enemy: {"windup_ticks": 0, "recovery_ticks": 0}
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: None
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_turn_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._resolve_player_action = lambda actor, action: encounter.resolved.append(("player", actor.id, dict(action)))
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(("enemy", actor["id"]))

        BraveEncounter.at_repeat(encounter)

        self.assertEqual(1, encounter.db.turn_count)
        self.assertEqual([("player", character.id, {"kind": "attack", "target": None})], encounter.resolved)
        self.assertEqual("charging", encounter.db.atb_states["p:7"]["phase"])
        self.assertEqual("ready", encounter.db.atb_states["e:e1"]["phase"])

        BraveEncounter.at_repeat(encounter)

        self.assertEqual(
            [
                ("player", character.id, {"kind": "attack", "target": None}),
                ("enemy", "e1"),
            ],
            encounter.resolved,
        )
        self.assertEqual("charging", encounter.db.atb_states["e:e1"]["phase"])

    def test_at_repeat_stops_other_gauges_when_first_actor_becomes_ready(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                turn_count=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 340, "ready_gauge": 400, "fill_rate": 100},
                    "e:e1": {"phase": "charging", "gauge": 100, "ready_gauge": 400, "fill_rate": 200},
                },
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
            ),
            resolved=[],
            refreshed=0,
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        self._bind_loop_helpers(encounter)
        encounter._consume_player_pending_action = lambda actor: BraveEncounter._consume_player_pending_action(encounter, actor)
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._enemy_action_timing = lambda actor: BraveEncounter._enemy_action_timing(encounter, actor)
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_turn_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._resolve_player_action = lambda actor, action: encounter.resolved.append(("player", actor.id, dict(action)))
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(("enemy", actor["id"]))

        BraveEncounter.at_repeat(encounter)

        self.assertEqual([], encounter.resolved)
        self.assertEqual("winding", encounter.db.atb_states["p:7"]["phase"])
        self.assertEqual(220, encounter.db.atb_states["e:e1"]["gauge"])
        self.assertEqual("charging", encounter.db.atb_states["e:e1"]["phase"])

    def test_at_repeat_skips_full_refresh_on_idle_charge_only_tick(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                turn_count=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 0, "ready_gauge": 400, "fill_rate": 100},
                    "e:e1": {"phase": "charging", "gauge": 0, "ready_gauge": 400, "fill_rate": 100},
                },
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
            ),
            resolved=[],
            refreshed=0,
            cleared_turn_states=0,
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        self._bind_loop_helpers(encounter)
        encounter._consume_player_pending_action = lambda actor: BraveEncounter._consume_player_pending_action(encounter, actor)
        encounter._player_action_timing = lambda action: BraveEncounter._player_action_timing(encounter, action)
        encounter._enemy_action_timing = lambda actor: BraveEncounter._enemy_action_timing(encounter, actor)
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_turn_states = lambda: setattr(encounter, "cleared_turn_states", encounter.cleared_turn_states + 1)
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._resolve_player_action = lambda actor, action: encounter.resolved.append(("player", actor.id, dict(action)))
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(("enemy", actor["id"]))

        BraveEncounter.at_repeat(encounter)

        self.assertEqual([], encounter.resolved)
        self.assertEqual(0, encounter.refreshed)
        self.assertEqual(0, encounter.cleared_turn_states)
        self.assertEqual(100, encounter.db.atb_states["p:7"]["gauge"])
        self.assertEqual(100, encounter.db.atb_states["e:e1"]["gauge"])

    def test_advance_idle_atb_states_keeps_phase_timestamps_continuous(self):
        character = DummyCharacter()
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                atb_states={
                    "p:7": {
                        "phase": "charging",
                        "gauge": 0,
                        "ready_gauge": 400,
                        "fill_rate": 100,
                        "phase_start_gauge": 0,
                        "phase_started_at_ms": 1_000,
                        "phase_duration_ms": 4_000,
                    }
                }
            ),
        )

        self._bind_common_helpers(encounter)

        advanced_ms = BraveEncounter._advance_idle_atb_states(encounter, [character], [])

        state = encounter.db.atb_states["p:7"]
        self.assertEqual(1_000, advanced_ms)
        self.assertEqual("charging", state["phase"])
        self.assertEqual(100, state["gauge"])
        self.assertEqual(100, state["phase_start_gauge"])
        self.assertEqual(2_000, state["phase_started_at_ms"])
        self.assertEqual(3_000, state["phase_duration_ms"])

    def test_at_repeat_breaks_exact_ready_ties_by_fill_rate(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                turn_count=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 300, "ready_gauge": 400, "fill_rate": 100},
                    "e:e1": {"phase": "charging", "gauge": 280, "ready_gauge": 400, "fill_rate": 120},
                },
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
            ),
            resolved=[],
            refreshed=0,
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        self._bind_loop_helpers(encounter)
        encounter._consume_player_pending_action = lambda actor: BraveEncounter._consume_player_pending_action(encounter, actor)
        encounter._player_action_timing = lambda _action: {"windup_ticks": 0, "recovery_ticks": 0}
        encounter._enemy_action_timing = lambda _enemy: {"windup_ticks": 0, "recovery_ticks": 0}
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: None
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_turn_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._resolve_player_action = lambda actor, action: encounter.resolved.append(("player", actor.id, dict(action)))
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(("enemy", actor["id"]))

        BraveEncounter.at_repeat(encounter)

        self.assertEqual([("enemy", "e1")], encounter.resolved)
        self.assertEqual("charging", encounter.db.atb_states["e:e1"]["phase"])
        self.assertEqual("ready", encounter.db.atb_states["p:7"]["phase"])

    def test_enemy_action_pause_shifts_other_actor_charge_timing(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "old_greymaw", "key": "Old Greymaw"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                atb_states={
                    "p:7": {
                        "phase": "charging",
                        "gauge": 200,
                        "ready_gauge": 400,
                        "fill_rate": 100,
                        "phase_start_gauge": 200,
                        "phase_started_at_ms": 1_000,
                        "phase_duration_ms": 2_000,
                    },
                    "e:e1": {"phase": "ready", "gauge": 400, "ready_gauge": 400, "fill_rate": 100},
                }
            ),
            refreshed=0,
            resolved=[],
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        self._bind_common_helpers(encounter)
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._enemy_action_timing = lambda actor: BraveEncounter._enemy_action_timing(encounter, actor)
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(actor["id"])
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: None

        with patch("typeclasses.scripts.time.time", return_value=1.2):
            BraveEncounter._advance_enemy_atb(encounter, enemy)

        paused_state = encounter.db.atb_states["p:7"]
        self.assertEqual("winding", encounter.db.atb_states["e:e1"]["phase"])
        self.assertEqual(220, paused_state["gauge"])
        self.assertEqual(2_200, paused_state["phase_started_at_ms"])
        self.assertEqual(1_800, paused_state["phase_duration_ms"])
        self.assertEqual(220, paused_state["phase_start_gauge"])

        with patch("typeclasses.scripts.time.time", return_value=2.0):
            BraveEncounter._advance_enemy_atb(encounter, enemy)

        paused_state = encounter.db.atb_states["p:7"]
        self.assertEqual(["e1"], encounter.resolved)
        self.assertEqual(220, paused_state["gauge"])
        self.assertEqual(3_400, paused_state["phase_started_at_ms"])
        self.assertEqual(1_800, paused_state["phase_duration_ms"])
        self.assertEqual(220, paused_state["phase_start_gauge"])

    def test_at_repeat_freezes_other_atb_states_while_enemy_action_resolves(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "old_greymaw", "key": "Old Greymaw"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                turn_count=0,
                atb_states={
                    "p:7": {"phase": "charging", "gauge": 160, "ready_gauge": 400, "fill_rate": 25},
                    "e:e1": {
                        "phase": "winding",
                        "gauge": 0,
                        "ticks_remaining": 1,
                        "ready_gauge": 400,
                        "fill_rate": 100,
                        "timing": {"windup_ticks": 1, "recovery_ticks": 1, "telegraph": True},
                        "current_action": {"kind": "enemy_attack", "enemy_id": "e1", "label": "Brush Pounce"},
                    },
                },
                pending_actions={},
            ),
            resolved=[],
            messages=[],
            obj=SimpleNamespace(msg_contents=lambda text: encounter.messages.append(text)),
        )

        self._bind_loop_helpers(encounter)
        encounter._enemy_action_timing = lambda actor: BraveEncounter._enemy_action_timing(encounter, actor)
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_turn_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: None
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(("enemy", actor["id"]))

        BraveEncounter.at_repeat(encounter)

        self.assertEqual([("enemy", "e1")], encounter.resolved)
        self.assertEqual(160, encounter.db.atb_states["p:7"]["gauge"])
        self.assertEqual("charging", encounter.db.atb_states["p:7"]["phase"])
        self.assertEqual("recovering", encounter.db.atb_states["e:e1"]["phase"])

    def test_at_repeat_waits_for_turn_lock_before_next_ready_actor(self):
        character = DummyCharacter()
        enemy = {"id": "e1", "template_key": "bog_creeper", "key": "Bog Creeper"}
        encounter = SimpleNamespace(
            interval=1,
            db=SimpleNamespace(
                turn_count=0,
                atb_states={
                    "p:7": {"phase": "ready", "gauge": 400, "ready_gauge": 400, "fill_rate": 100},
                    "e:e1": {"phase": "ready", "gauge": 400, "ready_gauge": 400, "fill_rate": 100},
                },
                pending_actions={str(character.id): {"kind": "attack", "target": None}},
                atb_turn_lock_until_ms=0,
            ),
            resolved=[],
            refreshed=0,
            obj=SimpleNamespace(msg_contents=lambda _text: None),
        )

        self._bind_loop_helpers(encounter)
        encounter._consume_player_pending_action = lambda actor: BraveEncounter._consume_player_pending_action(encounter, actor)
        encounter._player_action_timing = lambda _action: {"windup_ticks": 0, "recovery_ticks": 0}
        encounter._enemy_action_timing = lambda _enemy: {"windup_ticks": 0, "recovery_ticks": 0}
        encounter._enemy_action_label = lambda actor: BraveEncounter._enemy_action_label(encounter, actor)
        encounter._enemy_telegraph_message = lambda actor: BraveEncounter._enemy_telegraph_message(encounter, actor)
        encounter._combat_turn_locked = lambda now_ms=None: int(now_ms or 0) < int(encounter.db.atb_turn_lock_until_ms or 0)
        encounter._set_combat_turn_lock = lambda duration_ms=1200, now_ms=None: setattr(encounter.db, "atb_turn_lock_until_ms", 1450)
        encounter.get_active_participants = lambda: [character]
        encounter.get_active_enemies = lambda: [enemy]
        encounter._apply_participant_effects = lambda: None
        encounter._apply_enemy_effects = lambda: None
        encounter._clear_turn_states = lambda: None
        encounter._refresh_browser_combat_views = lambda: setattr(encounter, "refreshed", encounter.refreshed + 1)
        encounter.stop = lambda: None
        encounter._schedule_victory_sequence = lambda _message, *, exclude_rewarded=True: None
        encounter._resolve_player_action = lambda actor, action: encounter.resolved.append(("player", actor.id, dict(action)))
        encounter._execute_enemy_turn = lambda actor: encounter.resolved.append(("enemy", actor["id"]))

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
        self.assertEqual(2, encounter.db.turn_count)
        self.assertGreater(encounter.db.atb_turn_lock_until_ms, 1000)


if __name__ == "__main__":
    unittest.main()
