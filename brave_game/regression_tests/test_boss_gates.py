import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world import boss_gates


class DummyRoom:
    def __init__(self, room_id):
        self.id = 900
        self.key = room_id
        self.db = SimpleNamespace(brave_room_id=room_id)
        self.ndb = SimpleNamespace()
        self.contents = []
        self.messages = []

    def msg_contents(self, message):
        self.messages.append(message)


class DummyCharacter:
    def __init__(self, char_id, key, room, *, cleared=False, hp=30, race="human", brave_class="warrior"):
        self.id = char_id
        self.key = key
        self.location = room
        self.is_connected = True
        self.db = SimpleNamespace(
            brave_resources={"hp": hp},
            brave_boss_clears={"ruk_fence_cutter": True} if cleared else {},
            brave_race=race,
            brave_class=brave_class,
        )
        self.ndb = SimpleNamespace()
        self.messages = []
        room.contents.append(self)

    def msg(self, message):
        self.messages.append(message)

    def move_to(self, destination, quiet=False, move_type="move"):
        if self.location and self in self.location.contents:
            self.location.contents.remove(self)
        self.location = destination
        if hasattr(destination, "contents"):
            destination.contents.append(self)
        return True

    def get_active_encounter(self):
        return None


class DummyEncounter:
    def __init__(self):
        self.db = SimpleNamespace()
        self.added = []
        self.started = False
        self.configured = None

    def configure(self, room_id, encounter_data, expected_party_size=1):
        self.configured = (room_id, encounter_data, expected_party_size)

    def start(self):
        self.started = True

    def add_participant(self, participant):
        self.added.append(participant)
        return True, None


class BossGateTests(unittest.TestCase):
    def setUp(self):
        self.room = DummyRoom("goblin_road_fencebreaker_camp")
        self.initiator = DummyCharacter(1, "Jason", self.room)
        self.non_party_helper = DummyCharacter(2, "Mira", self.room, cleared=True)
        self.unready = DummyCharacter(3, "Rowan", self.room)

    def test_roster_includes_same_room_non_party_helpers(self):
        roster = boss_gates.build_gate_roster_snapshot(self.initiator, "ruk_fence_cutter")

        self.assertEqual(["Jason", "Rowan"], [entry["name"] for entry in roster["needs_clear"]])
        self.assertEqual(["Mira"], [entry["name"] for entry in roster["can_assist"]])

    def test_first_fight_creates_four_slot_run_with_caller_in_slot_one(self):
        ok, _message = boss_gates.start_gate_ready_check(self.initiator, "ruk_fence_cutter")
        self.assertTrue(ok)

        runs = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")
        self.assertEqual(1, len(runs))
        self.assertEqual([self.initiator.id, None, None, None], runs[0]["slot_ids"])

        payload = boss_gates.build_gate_run_payload(self.initiator, runs[0]["run_id"])
        self.assertEqual("run", payload["kind"])
        self.assertEqual(4, len(payload["slots"]))
        self.assertEqual("Jason", payload["slots"][0]["name"])
        self.assertEqual("Human", payload["slots"][0]["race_name"])
        self.assertEqual("Warrior", payload["slots"][0]["class_name"])
        self.assertEqual("heavy-shield", payload["slots"][0]["class_icon"])
        self.assertTrue(payload["slots"][0]["caller"])

    def test_second_fight_shows_waiting_run_choice_instead_of_auto_joining(self):
        ok, _message = boss_gates.start_gate_ready_check(self.initiator, "ruk_fence_cutter")
        self.assertTrue(ok)
        run_id = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")[0]["run_id"]

        ok, _message = boss_gates.start_gate_ready_check(self.non_party_helper, "ruk_fence_cutter")
        self.assertTrue(ok)

        runs = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")
        self.assertEqual(1, len(runs))
        self.assertEqual([self.initiator.id, None, None, None], runs[0]["slot_ids"])
        choice = boss_gates.build_gate_run_choice_payload(self.non_party_helper, "ruk_fence_cutter")
        self.assertEqual("choice", choice["kind"])
        self.assertEqual(run_id, choice["runs"][0]["run_id"])
        self.assertEqual("Jason", choice["runs"][0]["caller"])
        self.assertEqual("1/4 slots", choice["runs"][0]["meta"])

    def test_join_fills_next_slot_and_caller_can_remove_with_run_cooldown(self):
        ok, _message = boss_gates.start_gate_ready_check(self.initiator, "ruk_fence_cutter")
        self.assertTrue(ok)
        run_id = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")[0]["run_id"]
        ok, _message = boss_gates.join_gate_run(self.non_party_helper, run_id)
        self.assertTrue(ok)

        run = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")[0]
        self.assertEqual([self.initiator.id, self.non_party_helper.id, None, None], run["slot_ids"])
        payload = boss_gates.build_gate_run_payload(self.initiator, run_id)
        self.assertTrue(payload["slots"][1]["can_remove"])
        self.assertIn(f"bossgate remove {run_id} {self.non_party_helper.id}", payload["slots"][1]["remove_command"])

        ok, _message = boss_gates.remove_gate_run_member(self.initiator, run_id, self.non_party_helper.id)
        self.assertTrue(ok)
        run = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")[0]
        self.assertEqual([self.initiator.id, None, None, None], run["slot_ids"])

        ok, message = boss_gates.join_gate_run(self.non_party_helper, run_id)
        self.assertFalse(ok)
        self.assertIn("seconds", message)

        ok, new_run_id = boss_gates.create_gate_run(self.non_party_helper, "ruk_fence_cutter")
        self.assertTrue(ok)
        self.assertNotEqual(run_id, new_run_id)

    def test_non_caller_cannot_start_or_remove_from_run(self):
        ok, _message = boss_gates.start_gate_ready_check(self.initiator, "ruk_fence_cutter")
        self.assertTrue(ok)
        run_id = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")[0]["run_id"]
        ok, _message = boss_gates.join_gate_run(self.non_party_helper, run_id)
        self.assertTrue(ok)

        ok, message = boss_gates.launch_gate_run(self.non_party_helper, run_id)
        self.assertFalse(ok)
        self.assertIn("Only the player who started", message)

        ok, message = boss_gates.remove_gate_run_member(self.non_party_helper, run_id, self.initiator.id)
        self.assertFalse(ok)
        self.assertIn("Only the player who started", message)

    def test_fight_caller_controls_launch_roster(self):
        ok, _message = boss_gates.start_gate_ready_check(self.initiator, "ruk_fence_cutter")
        self.assertTrue(ok)
        run_id = boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter")[0]["run_id"]
        ok, _message = boss_gates.join_gate_run(self.non_party_helper, run_id)
        self.assertTrue(ok)
        temp_room = DummyRoom("bossrun:ruk_fence_cutter:test")
        encounter = DummyEncounter()
        encounter_data = {
            "key": "ruks_stand",
            "title": "Ruk the Fence-Cutter",
            "intro": "Ruk rises.",
            "enemies": ["ruk_fence_cutter"],
        }
        with patch("world.boss_gates._resolve_encounter_data", return_value=encounter_data), patch(
            "world.boss_gates.create.create_object", return_value=temp_room
        ), patch("world.boss_gates.create.create_script", return_value=encounter):
            ok, result = boss_gates.launch_gate_run(self.initiator, run_id)

        self.assertTrue(ok)
        self.assertIs(result, encounter)
        self.assertTrue(encounter.started)
        self.assertEqual([self.initiator, self.non_party_helper], encounter.added)
        self.assertEqual(temp_room, self.initiator.location)
        self.assertEqual(temp_room, self.non_party_helper.location)
        self.assertEqual(self.room, self.unready.location)
        self.assertEqual([self.initiator.id], encounter.db.boss_gate_needed_at_start)
        self.assertEqual([], boss_gates.get_waiting_gate_runs(self.room, "ruk_fence_cutter"))

    def test_cleared_room_without_uncleared_players_does_not_stage(self):
        cleared_room = DummyRoom("goblin_road_fencebreaker_camp")
        cleared = DummyCharacter(10, "Tamsin", cleared_room, cleared=True)

        ok, message = boss_gates.start_gate_ready_check(cleared, "ruk_fence_cutter")

        self.assertFalse(ok)
        self.assertIn("no longer blocks", message)
        self.assertEqual({}, getattr(cleared_room.ndb, "brave_boss_gate_runs", {}))

    def test_victory_clear_is_personal_to_needed_eligible_participants(self):
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                boss_gate_key="ruk_fence_cutter",
                boss_gate_needed_at_start=[self.initiator.id],
                boss_gate_success_room_id="goblin_warrens_sinkmouth_cut",
            ),
            obj=self.room,
        )
        encounter._participant_eligible_for_enemy_credit = lambda participant, _enemy: participant is self.initiator
        success_room = DummyRoom("goblin_warrens_sinkmouth_cut")

        with patch("world.boss_gates.get_room", return_value=success_room):
            boss_gates.resolve_gate_victory(encounter, [self.initiator, self.non_party_helper])

        self.assertTrue(self.initiator.db.brave_boss_clears["ruk_fence_cutter"])
        self.assertTrue(self.non_party_helper.db.brave_boss_clears["ruk_fence_cutter"])
        self.assertEqual(success_room, self.initiator.location)
        self.assertEqual(success_room, self.non_party_helper.location)


if __name__ == "__main__":
    unittest.main()
