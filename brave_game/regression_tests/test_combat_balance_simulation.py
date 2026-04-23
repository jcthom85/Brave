import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from regression_tests.combat_balance_simulation import (
    PARTY_SCENARIOS,
    _planned_telegraph_responses,
    _queue_pending_actions,
    analyze_interrupt_opportunities,
    analyze_trace,
    build_interrupt_opportunity_report,
    classify_encounter_rank,
    collect_authored_encounters,
    choose_player_action,
    render_interrupt_opportunity_markdown,
    simulate_encounter,
    SimulatedCharacter,
)


class CombatBalanceSimulationTests(unittest.TestCase):
    def test_classify_encounter_rank_marks_elite_and_boss(self):
        elite, elite_rank = classify_encounter_rank({"enemies": ["goblin_cutter"]})
        boss, boss_rank = classify_encounter_rank({"enemies": ["old_greymaw"]})

        self.assertEqual("elite", elite)
        self.assertGreaterEqual(elite_rank, 1)
        self.assertEqual("boss", boss)
        self.assertGreaterEqual(boss_rank, elite_rank)

    def test_simulation_is_deterministic_for_same_seed(self):
        authored = collect_authored_encounters()[0]
        scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == "solo_warrior")

        first = simulate_encounter(authored, scenario, base_seed=11, max_rounds=60)
        second = simulate_encounter(authored, scenario, base_seed=11, max_rounds=60)

        self.assertEqual(first["outcome"], second["outcome"])
        self.assertEqual(first["rounds"], second["rounds"])
        self.assertEqual(first["player_remaining_hp_ratio"], second["player_remaining_hp_ratio"])
        self.assertEqual(first["damage_done_by_players"], second["damage_done_by_players"])

    def test_ranger_companion_scenario_spawns_companion_actor(self):
        authored = collect_authored_encounters()[0]
        scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == "solo_ranger_with_companion")

        run = simulate_encounter(authored, scenario, base_seed=5, max_rounds=60)

        self.assertEqual(1, run["party_size"])
        self.assertEqual(["ranger"], run["party_classes"])
        self.assertTrue(run["companion_enabled"])
        self.assertGreaterEqual(run["companion_count"], 1)

    def test_simulation_trace_emits_tick_snapshots_when_enabled(self):
        authored = collect_authored_encounters()[0]
        scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == "solo_warrior")

        run = simulate_encounter(authored, scenario, base_seed=11, max_rounds=8, trace=True)

        self.assertIsInstance(run["trace"], list)
        self.assertGreaterEqual(len(run["trace"]), 2)
        self.assertIn("players", run["trace"][0])
        self.assertIn("enemies", run["trace"][0])
        self.assertIn("telegraph", run["trace"][0])

    def test_trace_analysis_marks_late_interrupt_actor(self):
        trace = [
            {
                "round": 12,
                "telegraph": {
                    "enemy_id": "e1",
                    "enemy_key": "The Hollow Lantern",
                    "phase": "winding",
                    "interruptible": True,
                    "ticks_remaining": 1,
                },
                "players": [
                    {
                        "key": "Warrior 1",
                        "class": "warrior",
                        "phase": "charging",
                        "ticks_remaining": 3,
                        "pending_action": {"kind": "ability", "ability": "shieldbash", "target": "e1"},
                    }
                ],
                "messages_tail": ["|yThe Hollow Lantern swells with drowned light and prepares Blackwater Flare.|n"],
            }
        ]

        analysis = analyze_trace(trace)

        self.assertEqual(1, len(analysis["telegraph_windows"]))
        tick = analysis["telegraph_windows"][0]["ticks"][0]
        self.assertIsNone(tick["interrupt_ready_actor"])
        self.assertEqual("Warrior 1", tick["interrupt_pending_actor"])

    def test_interrupt_opportunity_summary_counts_ready_and_recovering_ticks(self):
        trace = [
            {
                "round": 8,
                "telegraph": {
                    "enemy_id": "e1",
                    "enemy_key": "Boss",
                    "phase": "winding",
                    "interruptible": True,
                    "ticks_remaining": 2,
                },
                "players": [
                    {"key": "Warrior 1", "class": "warrior", "phase": "ready", "ticks_remaining": 0, "pending_action": {}},
                    {"key": "Mage 2", "class": "mage", "phase": "recovering", "ticks_remaining": 1, "pending_action": {}},
                ],
                "messages_tail": [],
            },
            {
                "round": 9,
                "telegraph": {
                    "enemy_id": "e1",
                    "enemy_key": "Boss",
                    "phase": "winding",
                    "interruptible": True,
                    "ticks_remaining": 1,
                },
                "players": [
                    {"key": "Warrior 1", "class": "warrior", "phase": "charging", "ticks_remaining": 0, "pending_action": {"kind": "ability", "ability": "shieldbash", "target": "e1"}},
                ],
                "messages_tail": [],
            },
        ]

        summary = analyze_interrupt_opportunities(trace)

        self.assertEqual(1, summary["telegraph_windows"])
        self.assertEqual(2, summary["telegraph_ticks"])
        self.assertEqual(1, summary["interrupt_ready_ticks"])
        self.assertEqual(1, summary["interrupt_charging_zero_ticks"])
        self.assertEqual(1, summary["interrupt_recovering_ticks"])
        self.assertEqual(1, summary["interrupt_late_pending_ticks"])

    def test_interrupt_opportunity_report_aggregates_traces(self):
        report = build_interrupt_opportunity_report(
            [
                {
                    "encounter_key": "boss_a",
                    "scenario_key": "solo_warrior",
                    "summary": {
                        "telegraph_windows": 2,
                        "telegraph_ticks": 4,
                        "interrupt_ready_ticks": 0,
                        "interrupt_charging_zero_ticks": 1,
                        "interrupt_recovering_ticks": 1,
                        "interrupt_late_pending_ticks": 1,
                    },
                },
                {
                    "encounter_key": "boss_b",
                    "scenario_key": "trio_warrior_cleric_mage",
                    "summary": {
                        "telegraph_windows": 1,
                        "telegraph_ticks": 2,
                        "interrupt_ready_ticks": 1,
                        "interrupt_charging_zero_ticks": 0,
                        "interrupt_recovering_ticks": 0,
                        "interrupt_late_pending_ticks": 0,
                    },
                },
            ]
        )

        self.assertEqual(2, report["totals"]["traces"])
        self.assertEqual(3, report["totals"]["telegraph_windows"])
        self.assertEqual(6, report["totals"]["telegraph_ticks"])
        self.assertEqual(1, report["totals"]["interrupt_ready_ticks"])
        self.assertIn("boss_a__solo_warrior", report["by_trace"])
        markdown = render_interrupt_opportunity_markdown(report)
        self.assertIn("Interrupt Opportunity Summary", markdown)
        self.assertIn("boss_b__trio_warrior_cleric_mage", markdown)

    def test_warrior_prefers_interrupt_on_telegraphed_enemy(self):
        warrior = SimulatedCharacter(1, "warrior")
        warrior.db.brave_resources["stamina"] = 99
        enemy = {"id": "e1", "key": "Old Greymaw", "template_key": "old_greymaw", "hp": 40, "dodge": 8, "target_strategy": "highest_threat"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(threat={"1": 12}),
            get_active_enemies=lambda: [enemy],
            get_active_participants=lambda: [warrior],
            get_active_player_participants=lambda: [warrior],
            _enemy_reaction_state=lambda current_enemy: {"phase": "winding", "telegraphed": True, "interruptible": True},
            _get_participant_state=lambda actor: {"stealth_turns": 0},
        )

        action = choose_player_action(encounter, warrior)

        self.assertEqual("ability", action["kind"])
        self.assertEqual("shieldbash", action["ability"])
        self.assertEqual("e1", action["target"])

    def test_cleric_guards_predicted_target_during_telegraph(self):
        warrior = SimulatedCharacter(1, "warrior")
        cleric = SimulatedCharacter(2, "cleric")
        warrior.db.brave_resources["hp"] = warrior.db.brave_derived_stats["max_hp"] // 2
        enemy = {"id": "e1", "key": "Hollow Lantern", "template_key": "hollow_lantern", "hp": 120, "dodge": 6, "target_strategy": "highest_threat"}
        encounter = SimpleNamespace(
            db=SimpleNamespace(threat={"1": 18, "2": 2}),
            get_active_enemies=lambda: [enemy],
            get_active_participants=lambda: [warrior, cleric],
            get_active_player_participants=lambda: [warrior, cleric],
            _enemy_reaction_state=lambda current_enemy: {"phase": "winding", "telegraphed": True, "interruptible": False},
            _get_participant_state=lambda actor: {"stealth_turns": 0},
        )

        action = choose_player_action(encounter, cleric)

        self.assertEqual("ability", action["kind"])
        self.assertEqual("guardianlight", action["ability"])
        self.assertEqual(warrior.id, action["target"])

    def test_telegraph_planner_only_assigns_response_when_actor_can_resolve_in_time(self):
        warrior = SimulatedCharacter(1, "warrior")
        mage = SimulatedCharacter(2, "mage")
        enemy = {"id": "e1", "key": "Old Greymaw", "template_key": "old_greymaw", "hp": 60, "dodge": 8, "target_strategy": "highest_threat"}
        atb_states = {
            "p:1": {"phase": "charging", "ticks_remaining": 1, "fill_rate": 100, "gauge": 0, "ready_gauge": 400},
            "p:2": {"phase": "charging", "ticks_remaining": 3, "fill_rate": 100, "gauge": 0, "ready_gauge": 400},
            "e:e1": {
                "phase": "winding",
                "ticks_remaining": 2,
                "fill_rate": 100,
                "gauge": 0,
                "ready_gauge": 400,
                "current_action": {"label": "Brush Pounce"},
                "timing": {"telegraph": True, "interruptible": True},
            },
        }
        encounter = SimpleNamespace(
            db=SimpleNamespace(threat={"1": 10, "2": 4}, atb_states=atb_states, pending_actions={}),
            get_active_enemies=lambda: [enemy],
            get_active_participants=lambda: [warrior, mage],
            get_active_player_participants=lambda: [warrior, mage],
            _enemy_reaction_state=lambda current_enemy: {
                "phase": "winding",
                "telegraphed": True,
                "interruptible": True,
                "atb_state": atb_states["e:e1"],
            },
            _get_participant_state=lambda actor: {"stealth_turns": 0},
            _get_actor_atb_state=lambda character=None, enemy=None, companion=None: atb_states["p:1" if character and character.id == 1 else "p:2" if character and character.id == 2 else "e:e1"],
            _player_action_timing=lambda action: {"shieldbash": {"windup_ticks": 1}, "frostbind": {"windup_ticks": 1}}[action["ability"]],
        )

        plans = _planned_telegraph_responses(encounter)

        self.assertEqual({"1": {"kind": "ability", "ability": "shieldbash", "target": "e1"}}, plans)

    def test_ready_interrupt_actor_holds_for_imminent_boss_telegraph(self):
        warrior = SimulatedCharacter(1, "warrior")
        enemy = {"id": "e1", "key": "Old Greymaw", "template_key": "old_greymaw", "tags": ["boss"], "hp": 60, "dodge": 8, "target_strategy": "highest_threat"}
        atb_states = {
            "p:1": {"phase": "ready", "ticks_remaining": 0, "fill_rate": 100, "gauge": 400, "ready_gauge": 400},
            "e:e1": {"phase": "charging", "ticks_remaining": 1, "fill_rate": 100, "gauge": 320, "ready_gauge": 400},
        }
        encounter = SimpleNamespace(
            db=SimpleNamespace(threat={"1": 10}, atb_states=atb_states, pending_actions={}),
            telemetry={"telegraphed_response_actions": 0, "held_actions": 0},
            get_active_enemies=lambda: [enemy],
            get_active_participants=lambda: [warrior],
            get_active_player_participants=lambda: [warrior],
            _enemy_action_timing=lambda current_enemy: {"telegraph": True},
            _enemy_reaction_state=lambda current_enemy: {"phase": "charging", "telegraphed": False, "interruptible": True, "atb_state": atb_states["e:e1"]},
            _get_participant_state=lambda actor: {"stealth_turns": 0},
            _get_actor_atb_state=lambda character=None, enemy=None, companion=None: atb_states["p:1" if character else "e:e1"],
            _player_action_timing=lambda action: {"shieldbash": {"windup_ticks": 1}}[action["ability"]],
        )

        _queue_pending_actions(encounter)

        self.assertEqual({"1": {"kind": "hold"}}, encounter.db.pending_actions)
        self.assertEqual(1, encounter.telemetry["held_actions"])


if __name__ == "__main__":
    unittest.main()
