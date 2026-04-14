import os
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.combat_atb import (
    advance_atb_state_by_ms,
    atb_state_ms_until_ready,
    create_atb_state,
    finish_atb_action,
    get_ability_atb_profile,
    get_item_atb_profile,
    normalize_atb_profile,
    render_atb_state,
    start_atb_action,
    tick_atb_state,
)


class CombatAtbTests(unittest.TestCase):
    def test_normalize_atb_profile_clamps_bad_values(self):
        profile = normalize_atb_profile(
            {
                "gauge_cost": "120",
                "windup_ticks": -4,
                "recovery_ticks": "2",
                "cooldown_ticks": "bad",
                "interruptible": True,
            }
        )

        self.assertEqual(120, profile["gauge_cost"])
        self.assertEqual(0, profile["windup_ticks"])
        self.assertEqual(2, profile["recovery_ticks"])
        self.assertEqual(0, profile["cooldown_ticks"])
        self.assertFalse(profile["interruptible"])

    def test_ability_profile_marks_large_spell_as_telegraphed(self):
        profile = get_ability_atb_profile(
            "meteorsigil",
            {"class": "mage", "resource": "mana", "cost": 18, "target": "enemy"},
        )

        self.assertEqual(2, profile["windup_ticks"])
        self.assertEqual(2, profile["recovery_ticks"])
        self.assertEqual(1, profile["cooldown_ticks"])
        self.assertTrue(profile["interruptible"])
        self.assertTrue(profile["telegraph"])

    def test_ability_profile_makes_fast_self_buff_instant(self):
        profile = get_ability_atb_profile(
            "defend",
            {"class": "warrior", "resource": "stamina", "cost": 6, "target": "self"},
        )

        self.assertEqual(0, profile["windup_ticks"])
        self.assertFalse(profile["interruptible"])
        self.assertFalse(profile["target_locked"])

    def test_item_profile_uses_cooldown_turns_and_enemy_damage_windup(self):
        profile = get_item_atb_profile(
            "spark_charge",
            {"target": "enemy", "damage": {"base": 10}, "cooldown_turns": 3},
        )

        self.assertEqual(1, profile["windup_ticks"])
        self.assertTrue(profile["interruptible"])
        self.assertEqual(3, profile["cooldown_ticks"])

    def test_tick_atb_state_uses_four_hundred_point_ready_gauge_by_default(self):
        state = create_atb_state(fill_rate=120)
        state = tick_atb_state(state)

        self.assertEqual(400, state["ready_gauge"])
        self.assertEqual("charging", state["phase"])
        self.assertEqual(120, state["gauge"])

    def test_start_and_finish_atb_action_walks_through_windup_and_recovery(self):
        state = create_atb_state(phase="ready", gauge=400)
        state = start_atb_action(state, {"kind": "ability"}, {"windup_ticks": 2, "recovery_ticks": 1})
        self.assertEqual("winding", state["phase"])
        self.assertEqual(2, state["ticks_remaining"])

        state = tick_atb_state(state)
        self.assertEqual("winding", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])

        state = tick_atb_state(state)
        self.assertEqual("resolving", state["phase"])

        state = finish_atb_action(state)
        self.assertEqual("recovering", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])

        state = tick_atb_state(state)
        self.assertEqual("charging", state["phase"])
        self.assertEqual(0, state["gauge"])

    def test_advance_atb_state_by_ms_stops_at_first_ready_point(self):
        state = advance_atb_state_by_ms(
            {
                "phase": "charging",
                "gauge": 340,
                "ready_gauge": 400,
                "fill_rate": 100,
            },
            600,
            tick_ms=1000,
            now_ms=1_600,
        )

        self.assertEqual("ready", state["phase"])
        self.assertEqual(400, state["gauge"])
        self.assertEqual(0, state["ticks_remaining"])

    def test_atb_state_ms_until_ready_includes_recovery_and_charge(self):
        ready_ms = atb_state_ms_until_ready(
            {
                "phase": "recovering",
                "ticks_remaining": 1,
                "ready_gauge": 400,
                "fill_rate": 100,
            },
            tick_ms=1000,
        )

        self.assertEqual(5000, ready_ms)

    def test_render_atb_state_caps_charging_just_below_ready_until_server_marks_ready(self):
        state = render_atb_state(
            {
                "phase": "charging",
                "gauge": 300,
                "ready_gauge": 400,
                "phase_start_gauge": 300,
                "phase_started_at_ms": 1_000,
                "phase_duration_ms": 1_000,
            },
            tick_ms=250,
            now_ms=2_500,
        )

        self.assertEqual("charging", state["phase"])
        self.assertEqual(399, state["gauge"])
        self.assertEqual(1, state["ticks_remaining"])


if __name__ == "__main__":
    unittest.main()
