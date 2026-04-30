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
    build_first_hour_route_report,
    build_progression_runs,
    build_interrupt_opportunity_report,
    build_summary,
    classify_encounter_rank,
    collect_authored_encounters,
    choose_player_action,
    infer_expected_level,
    render_interrupt_opportunity_markdown,
    render_first_hour_route_markdown,
    render_markdown,
    simulate_encounter,
    DummyRoom,
    SimulationEncounter,
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

    def test_progression_level_inference_uses_zone_band(self):
        authored = {
            "room_id": "goblin_warrens_feast_hall",
            "encounter_data": {"key": "hall_press"},
        }

        self.assertEqual(8, infer_expected_level(authored))

    def test_simulation_can_run_at_explicit_progression_level(self):
        authored = collect_authored_encounters()[0]
        scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == "solo_warrior")

        run = simulate_encounter(authored, scenario, base_seed=11, max_rounds=60, level=2)

        self.assertEqual(2, run["character_level"])
        self.assertIn("expected_level", run)

    def test_progression_runs_use_inferred_levels(self):
        runs = build_progression_runs(base_seed=3, max_rounds=20, limit=1)

        self.assertEqual(len(PARTY_SCENARIOS), len(runs))
        self.assertTrue(all(run["character_level"] == run["expected_level"] for run in runs))

    def test_first_hour_route_tracks_xp_level_and_post_ruk_lead(self):
        report = build_first_hour_route_report(scenario_key="solo_warrior", base_seed=7, max_rounds=120)

        self.assertEqual(4, report["final_level"])
        self.assertLess(report["final_xp"], 350)
        self.assertEqual("what_whispers_in_the_wood", report["post_ruk_unlock_order"][0])
        self.assertTrue(all(step.get("outcome", "victory") == "victory" for step in report["steps"]))
        self.assertGreater(report["final_silver_min"], 0)
        self.assertGreaterEqual(report["final_silver_max"], report["final_silver_min"])
        self.assertTrue(report["guaranteed_items"])
        self.assertTrue(report["possible_items"])
        self.assertFalse(any(flag["kind"] in {"missing_next_step", "missing_post_ruk_next_step"} for flag in report["pacing_flags"]))
        self.assertTrue(all(step.get("next_step") for step in report["steps"] if step["kind"] == "quest"))
        ruk_step = next(step for step in report["steps"] if step["key"] == "ruks_stand")
        self.assertGreater(ruk_step["telegraphed_actions"], 0)
        self.assertGreater(ruk_step["telegraphed_unanswered"], 0)
        self.assertTrue(any(lead["next_step"] for lead in report["post_ruk_leads"] if lead["key"] == "what_whispers_in_the_wood"))
        self.assertEqual(
            ("ruk_the_fence_cutter", "what_whispers_in_the_wood"),
            (
                report["tracked_quest_transitions"][-1]["before"],
                report["tracked_quest_transitions"][-1]["after"],
            ),
        )
        markdown = render_first_hour_route_markdown(report)
        self.assertIn("First Hour Route Summary", markdown)
        self.assertIn("Tracked Quest Transitions", markdown)
        self.assertIn("Pacing Flags", markdown)
        self.assertIn("what_whispers_in_the_wood", markdown)

    def test_ranger_companion_scenario_spawns_companion_actor(self):
        authored = collect_authored_encounters()[0]
        scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == "solo_ranger_with_companion")

        run = simulate_encounter(authored, scenario, base_seed=5, max_rounds=60)

        self.assertEqual(1, run["party_size"])
        self.assertEqual(["ranger"], run["party_classes"])
        self.assertTrue(run["companion_enabled"])
        self.assertGreaterEqual(run["companion_count"], 1)

    def test_drowned_weir_solo_scaling_is_targeted(self):
        encounter_data = {
            "key": "lock_surge",
            "title": "Scale Check",
            "intro": "Testing scaling.",
            "enemies": ["hollow_lantern"],
        }
        outlier_data = {
            **encounter_data,
            "key": "the_hollow_lantern",
        }
        solo = SimulationEncounter(
            DummyRoom("drowned_weir_blackwater_lamp_house"),
            encounter_data,
            expected_party_size=1,
            seed=1,
        )
        duo = SimulationEncounter(
            DummyRoom("drowned_weir_blackwater_lamp_house"),
            encounter_data,
            expected_party_size=2,
            seed=1,
        )
        early_solo = SimulationEncounter(
            DummyRoom("goblin_road_trailhead"),
            encounter_data,
            expected_party_size=1,
            seed=1,
        )
        outlier_solo = SimulationEncounter(
            DummyRoom("drowned_weir_blackwater_lamp_house"),
            outlier_data,
            expected_party_size=1,
            seed=1,
        )

        self.assertEqual("Solo Drowned Weir", solo._get_scaling_profile()["label"])
        self.assertLess(solo._get_scaling_profile()["power"], early_solo._get_scaling_profile()["power"])
        self.assertLess(outlier_solo._get_scaling_profile()["power"], solo._get_scaling_profile()["power"])
        self.assertEqual("Duo", duo._get_scaling_profile()["label"])
        self.assertEqual("Solo", early_solo._get_scaling_profile()["label"])

    def test_simulation_trace_emits_tick_snapshots_when_enabled(self):
        authored = collect_authored_encounters()[0]
        scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == "solo_warrior")

        run = simulate_encounter(authored, scenario, base_seed=11, max_rounds=8, trace=True)

        self.assertIsInstance(run["trace"], list)
        self.assertGreaterEqual(len(run["trace"]), 2)
        self.assertIn("players", run["trace"][0])
        self.assertIn("enemies", run["trace"][0])
        self.assertIn("telegraph", run["trace"][0])

    def test_simulation_counts_telegraph_outcomes(self):
        authored = next(
            entry
            for entry in collect_authored_encounters()
            if entry["encounter_data"].get("key") == "greymaws_stand"
        )
        scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == "duo_warrior_cleric")

        run = simulate_encounter(authored, scenario, base_seed=24, max_rounds=40)

        self.assertGreater(run["telegraphed_actions"], 0)
        telegraphed_outcomes = (
            run["telegraphed_interrupts"]
            + run["telegraphed_redirects"]
            + run["telegraphed_mitigations"]
            + run["telegraphed_unanswered"]
        )
        self.assertGreater(telegraphed_outcomes, 0)
        self.assertIn("telegraphed_unanswered", run)

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

    def test_summary_surfaces_risk_and_telegraph_metrics(self):
        base_run = {
            "source": "room:test",
            "source_kind": "room",
            "room_id": "test_room",
            "encounter_key": "test_boss",
            "encounter_title": "Test Boss",
            "enemy_templates": ["old_greymaw"],
            "rank_bucket": "boss",
            "max_rank": 5,
            "scenario_key": "solo_warrior",
            "scenario_label": "Solo Warrior",
            "character_level": 10,
            "expected_level": 10,
            "party_size": 1,
            "party_classes": ["warrior"],
            "companion_enabled": False,
            "seed": 1,
            "outcome": "victory",
            "rounds": 42,
            "player_remaining_hp": 10,
            "player_remaining_hp_ratio": 0.1,
            "enemy_remaining_hp": 0,
            "enemy_remaining_hp_ratio": 0.0,
            "surviving_players": 1,
            "enemy_count": 1,
            "companion_count": 0,
            "damage_done_by_players": 100,
            "damage_done_by_companions": 0,
            "healing_done": 12,
            "mitigation_done": 8,
            "damage_taken": 55,
            "meaningful_actions": 7,
            "telegraphed_actions": 2,
            "telegraphed_interrupts": 0,
            "telegraphed_redirects": 0,
            "telegraphed_mitigations": 0,
            "telegraphed_unanswered": 2,
            "telegraphed_response_actions": 0,
            "held_actions": 0,
            "combat_fx_events": 3,
            "near_wipe": True,
            "trace": None,
        }
        companion_run = {
            **base_run,
            "scenario_key": "solo_ranger_with_companion",
            "scenario_label": "Solo Ranger + Companion",
            "party_classes": ["ranger"],
            "companion_enabled": True,
            "damage_done_by_companions": 25,
            "near_wipe": False,
            "player_remaining_hp_ratio": 0.75,
            "telegraphed_interrupts": 1,
            "telegraphed_unanswered": 1,
        }
        no_companion_run = {
            **base_run,
            "scenario_key": "solo_ranger_no_companion",
            "scenario_label": "Solo Ranger",
            "party_classes": ["ranger"],
            "companion_enabled": False,
            "outcome": "defeat",
            "rounds": 50,
            "player_remaining_hp": 0,
            "player_remaining_hp_ratio": 0.0,
            "near_wipe": False,
            "telegraphed_actions": 0,
            "telegraphed_unanswered": 0,
        }

        summary = build_summary([base_run, companion_run, no_companion_run])
        markdown = render_markdown(summary)

        self.assertEqual(3, summary["totals"]["runs"])
        self.assertEqual(1, summary["totals"]["near_wipes"])
        self.assertIn("encounter_summary", summary)
        self.assertEqual(1, len(summary["telegraph_risks"]))
        self.assertEqual("test_boss", summary["encounter_risks"][0]["encounter_key"])
        self.assertIn("## Encounter Risk List", markdown)
        self.assertIn("## Telegraph Risks", markdown)
        self.assertIn("telegraph answer rate", markdown)

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

    def test_cleric_cleanses_afflicted_ally_outside_telegraph(self):
        warrior = SimulatedCharacter(1, "warrior")
        cleric = SimulatedCharacter(2, "cleric")
        enemy = {"id": "e1", "key": "Bog Wolf", "template_key": "road_wolf", "hp": 40, "dodge": 8, "target_strategy": "highest_threat"}
        states = {
            str(warrior.id): {"stealth_turns": 0, "poison_turns": 2},
            str(cleric.id): {"stealth_turns": 0},
        }
        encounter = SimpleNamespace(
            db=SimpleNamespace(threat={"1": 12, "2": 2}),
            get_active_enemies=lambda: [enemy],
            get_active_participants=lambda: [warrior, cleric],
            get_active_player_participants=lambda: [warrior, cleric],
            _enemy_reaction_state=lambda current_enemy: {"phase": "charging", "telegraphed": False, "interruptible": False},
            _get_participant_state=lambda actor: states.get(str(actor.id), {"stealth_turns": 0}),
        )

        action = choose_player_action(encounter, cleric)

        self.assertEqual("ability", action["kind"])
        self.assertEqual("cleanse", action["ability"])
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
