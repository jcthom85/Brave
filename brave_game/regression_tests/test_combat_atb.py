import os
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.combat_atb import (
    create_atb_state,
    finish_atb_action,
    get_ability_atb_profile,
    get_item_atb_profile,
    normalize_atb_profile,
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

    def test_tick_atb_state_advances_from_charging_to_ready(self):
        state = create_atb_state(fill_rate=120, ready_gauge=100, phase_started_at_ms=1000)
        state = tick_atb_state(state, now_ms=2000)

        self.assertEqual("ready", state["phase"])
        self.assertEqual(100, state["gauge"])

    def test_start_and_finish_atb_action_walks_through_windup_and_recovery(self):
        state = create_atb_state(phase="ready", gauge=100, ready_gauge=100, phase_started_at_ms=1000)
        state = start_atb_action(state, {"kind": "ability"}, {"windup_ticks": 2, "recovery_ticks": 1}, now_ms=1000)
        self.assertEqual("winding", state["phase"])
        self.assertEqual(2, state["ticks_remaining"])

        state = tick_atb_state(state, now_ms=2000)
        self.assertEqual("winding", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])

        state = tick_atb_state(state, now_ms=3000)
        self.assertEqual("resolving", state["phase"])

        state = finish_atb_action(state, now_ms=3000)
        self.assertEqual("recovering", state["phase"])
        self.assertEqual(1, state["ticks_remaining"])

        state = tick_atb_state(state, now_ms=4000)
        self.assertEqual("charging", state["phase"])
        self.assertEqual(0, state["gauge"])


if __name__ == "__main__":
    unittest.main()
