import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter, COMBAT_FINISH_FX_DELAY
from world.browser_views import build_combat_victory_view


class DummyRewardCharacter:
    def __init__(self, char_id, key, *, brave_class="warrior"):
        self.id = char_id
        self.key = key
        self.db = SimpleNamespace(
            brave_class=brave_class,
            brave_silver=0,
            brave_resources={"hp": 30},
        )
        self.ndb = SimpleNamespace()
        self.messages = []
        self.xp_awards = []
        self.items = []

    def msg(self, text):
        self.messages.append(text)

    def grant_xp(self, amount):
        self.xp_awards.append(amount)
        return [f"+{amount} XP"]

    def add_item_to_inventory(self, template_id, quantity):
        self.items.append((template_id, quantity))

    def clear_chapel_blessing(self):
        return None


class CombatRewardTests(unittest.TestCase):
    def _bind_reward_helpers(self, encounter):
        encounter._get_participant_contribution = lambda character: BraveEncounter._get_participant_contribution(encounter, character)
        encounter._save_participant_contribution = lambda character, contribution: BraveEncounter._save_participant_contribution(encounter, character, contribution)
        encounter._record_participant_contribution = lambda character, **kwargs: BraveEncounter._record_participant_contribution(encounter, character, **kwargs)
        encounter._participant_reward_eligible = lambda character: BraveEncounter._participant_reward_eligible(encounter, character)
        encounter._participant_impact_score = lambda character: BraveEncounter._participant_impact_score(encounter, character)
        encounter._participant_reward_weight = lambda character, max_round, top_impact: BraveEncounter._participant_reward_weight(
            encounter,
            character,
            max_round=max_round,
            top_impact=top_impact,
        )
        encounter._allocate_weighted_pool = lambda total, weighted_entries, minimum=0: BraveEncounter._allocate_weighted_pool(
            total,
            weighted_entries,
            minimum=minimum,
        )
        encounter._distribute_reward_items = lambda reward_items, weighted_entries: BraveEncounter._distribute_reward_items(
            reward_items,
            weighted_entries,
        )
        encounter._participant_eligible_for_enemy_credit = lambda character, enemy: BraveEncounter._participant_eligible_for_enemy_credit(
            encounter,
            character,
            enemy,
        )
        encounter._award_enemy_defeat_credit = lambda enemy: BraveEncounter._award_enemy_defeat_credit(encounter, enemy)
        encounter._award_companion_bond_progress = lambda: BraveEncounter._award_companion_bond_progress(encounter)

    @patch("world.browser_panels.send_webclient_event")
    @patch("world.browser_views.build_combat_victory_view", return_value={"view": "victory"})
    @patch("typeclasses.scripts.pop_recent_quest_updates", return_value=[])
    @patch("typeclasses.scripts.record_encounter_victory")
    @patch("typeclasses.scripts.roll_enemy_rewards", return_value={"silver": 30, "items": [("wolf_fang", 1), ("greymaw_pelt", 1)]})
    def test_reward_victory_splits_eligible_rewards_evenly_and_blocks_idle_leech(
        self,
        _roll_enemy_rewards,
        record_encounter_victory,
        _pop_recent_quest_updates,
        _build_combat_victory_view,
        _send_webclient_event,
    ):
        starter = DummyRewardCharacter(1, "Starter")
        late = DummyRewardCharacter(2, "Late")
        idle = DummyRewardCharacter(3, "Idle")
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                round=4,
                enemies=[{"template_key": "old_greymaw", "xp": 120, "tags": ["boss"]}],
                participant_contributions={
                    "1": {
                        "joined_round": 0,
                        "meaningful_actions": 3,
                        "damage_done": 60,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 1,
                        "hits_taken": 2,
                        "boss_credit_eligible": True,
                    },
                    "2": {
                        "joined_round": 2,
                        "meaningful_actions": 1,
                        "damage_done": 12,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": True,
                    },
                    "3": {
                        "joined_round": 2,
                        "meaningful_actions": 0,
                        "damage_done": 0,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": False,
                    },
                },
            ),
            obj=SimpleNamespace(),
            _get_scaling_profile=lambda: {"xp": 1.0},
            get_active_participants=lambda: [starter, late, idle],
            get_registered_participants=lambda: [starter, late, idle],
        )
        self._bind_reward_helpers(encounter)

        rewarded = BraveEncounter._reward_victory(encounter)

        self.assertEqual([starter, late, idle], rewarded)
        self.assertEqual([60], starter.xp_awards)
        self.assertEqual([60], late.xp_awards)
        self.assertEqual([], idle.xp_awards)
        self.assertEqual(15, starter.db.brave_silver)
        self.assertEqual(15, late.db.brave_silver)
        self.assertEqual(0, idle.db.brave_silver)
        self.assertEqual(2, len(starter.items) + len(late.items))
        self.assertEqual([], idle.items)
        self.assertEqual({starter, late}, {call.args[0] for call in record_encounter_victory.call_args_list})
        self.assertTrue(any("Victory passes you by" in message for message in idle.messages))
        self.assertTrue(starter.ndb.brave_showing_combat_result)
        self.assertTrue(late.ndb.brave_showing_combat_result)
        self.assertTrue(idle.ndb.brave_showing_combat_result)
        victory_kwargs_by_character = {
            call.args[1]: call.kwargs
            for call in _build_combat_victory_view.call_args_list
        }
        self.assertEqual(60, victory_kwargs_by_character[starter]["xp_total"])
        self.assertEqual(15, victory_kwargs_by_character[starter]["reward_silver"])
        self.assertEqual(starter.items, victory_kwargs_by_character[starter]["reward_items"])
        self.assertEqual(60, victory_kwargs_by_character[late]["xp_total"])
        self.assertEqual(15, victory_kwargs_by_character[late]["reward_silver"])
        self.assertEqual(late.items, victory_kwargs_by_character[late]["reward_items"])
        self.assertEqual(0, victory_kwargs_by_character[idle]["xp_total"])
        self.assertEqual(0, victory_kwargs_by_character[idle]["reward_silver"])
        self.assertEqual([], victory_kwargs_by_character[idle]["reward_items"])

    @patch("world.browser_panels.send_webclient_event")
    @patch("world.browser_views.build_combat_victory_view", return_value={"view": "victory"})
    @patch("typeclasses.scripts.pop_recent_quest_updates", return_value=[])
    @patch("typeclasses.scripts.record_encounter_victory")
    @patch("typeclasses.scripts.roll_enemy_rewards", return_value={"silver": 12, "items": [("wolf_fang", 1)]})
    def test_knocked_out_meaningful_party_member_still_receives_victory_share(
        self,
        _roll_enemy_rewards,
        record_encounter_victory,
        _pop_recent_quest_updates,
        _build_combat_victory_view,
        _send_webclient_event,
    ):
        standing = DummyRewardCharacter(1, "Standing")
        knocked_out = DummyRewardCharacter(2, "KnockedOut")
        knocked_out.db.brave_resources = {"hp": 0}
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                round=3,
                enemies=[{"template_key": "ruk_the_fence_cutter", "xp": 60, "tags": ["ruk", "boss"]}],
                participant_contributions={
                    "1": {
                        "joined_round": 0,
                        "meaningful_actions": 2,
                        "damage_done": 40,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 1,
                        "boss_credit_eligible": True,
                    },
                    "2": {
                        "joined_round": 0,
                        "meaningful_actions": 1,
                        "damage_done": 12,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 2,
                        "boss_credit_eligible": True,
                    },
                },
            ),
            obj=SimpleNamespace(),
            _get_scaling_profile=lambda: {"xp": 1.0},
            get_active_participants=lambda: [standing],
            get_registered_participants=lambda: [standing, knocked_out],
        )
        self._bind_reward_helpers(encounter)

        BraveEncounter._reward_victory(encounter)

        self.assertTrue(knocked_out.xp_awards)
        self.assertTrue(any("victory still holds" in message.lower() for message in knocked_out.messages))
        self.assertIn(knocked_out, [call.args[0] for call in record_encounter_victory.call_args_list])

    def test_victory_view_moves_quest_rewards_out_of_progress(self):
        encounter = SimpleNamespace(db=SimpleNamespace(encounter_title="Roadside Fight"), obj=SimpleNamespace())
        view = build_combat_victory_view(
            encounter,
            DummyRewardCharacter(1, "Starter"),
            xp_total=36,
            reward_silver=1,
            reward_items=[("thorn_rat_tail", 3)],
            progress_messages=[
                "Quest complete: Rats in the Kettle",
                "New quest: Roadside Howls",
                "You gain 35 XP.",
                "You receive 8 silver.",
                "You receive Innkeeper's Fish Pie.",
                "Lead: Follow the cut fences east.",
            ],
        )

        sections = {section["label"]: section for section in view["sections"]}
        reward_pairs = sections["Rewards"]["items"]
        self.assertEqual("71", reward_pairs[0]["value"])
        self.assertEqual("9", reward_pairs[1]["value"])

        loot_labels = [item["text"] for item in sections["Recovered Loot"]["items"]]
        self.assertIn("Thorn Rat Tail x3", loot_labels)
        self.assertIn("Innkeeper's Fish Pie", loot_labels)

        progress_text = str(sections["Progress"])
        self.assertIn("Rats in the Kettle", progress_text)
        self.assertIn("Roadside Howls", progress_text)
        self.assertNotIn("You gain 35 XP", progress_text)
        self.assertNotIn("You receive 8 silver", progress_text)
        self.assertNotIn("Innkeeper's Fish Pie", progress_text)
        self.assertNotIn("Follow the cut fences", progress_text)

    @patch("typeclasses.scripts.advance_enemy_defeat")
    def test_boss_defeat_credit_requires_meaningful_action_and_cutoff_eligibility(self, advance_enemy_defeat):
        starter = DummyRewardCharacter(1, "Starter")
        late = DummyRewardCharacter(2, "Late")
        idle = DummyRewardCharacter(3, "Idle")
        enemy = {
            "id": "e1",
            "key": "Old Greymaw",
            "template_key": "old_greymaw",
            "hp": 10,
            "marked_turns": 0,
            "shielded": False,
            "tags": ["wolf", "boss"],
        }
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                participant_contributions={
                    "1": {
                        "joined_round": 0,
                        "meaningful_actions": 1,
                        "damage_done": 0,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": True,
                    },
                    "2": {
                        "joined_round": 2,
                        "meaningful_actions": 1,
                        "damage_done": 0,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": False,
                    },
                    "3": {
                        "joined_round": 0,
                        "meaningful_actions": 0,
                        "damage_done": 0,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": True,
                    },
                }
            ),
            obj=SimpleNamespace(msg_contents=lambda _message, **_kwargs: None),
            _save_enemy=lambda _enemy: None,
            _add_threat=lambda _attacker, _amount: None,
            _emit_combat_fx=lambda **_kwargs: None,
            _emit_defeat_fx=lambda _target, text="DOWN": None,
            get_active_enemies=lambda: [],
            _schedule_victory_sequence=Mock(),
            get_registered_participants=lambda: [starter, late, idle],
        )
        self._bind_reward_helpers(encounter)

        BraveEncounter._damage_enemy(encounter, starter, enemy, 12)

        self.assertEqual([starter], [call.args[0] for call in advance_enemy_defeat.call_args_list])
        encounter._schedule_victory_sequence.assert_called_once_with("|gThe encounter is over. The road is clear for now.|n")

    @patch("typeclasses.scripts.delay")
    def test_at_repeat_schedules_victory_after_finish_fx_window(self, delay_mock):
        winner = DummyRewardCharacter(1, "Starter")
        reward_mock = Mock(return_value=[winner])
        stop_mock = Mock()
        refresh_mock = Mock()
        encounter = SimpleNamespace(
            db=SimpleNamespace(round=0),
            ndb=SimpleNamespace(brave_victory_pending=False),
            obj=SimpleNamespace(msg_contents=lambda _message, **_kwargs: None),
            get_active_participants=lambda: [winner],
            get_active_player_participants=lambda: [winner],
            get_active_companions=lambda: [],
            get_active_enemies=lambda: [],
            _apply_participant_effects=lambda: None,
            _apply_enemy_effects=lambda: None,
            _advance_player_atb=lambda participant: None,
            _advance_companion_atb=lambda companion: None,
            _advance_enemy_atb=lambda enemy: None,
            _clear_round_states=lambda: None,
            _reward_victory=reward_mock,
            _refresh_browser_combat_views=refresh_mock,
            stop=stop_mock,
        )
        encounter._finish_victory_sequence = lambda room_message, *, exclude_rewarded=True: BraveEncounter._finish_victory_sequence(
            encounter,
            room_message,
            exclude_rewarded=exclude_rewarded,
        )
        encounter._schedule_victory_sequence = lambda room_message, *, exclude_rewarded=True: BraveEncounter._schedule_victory_sequence(
            encounter,
            room_message,
            exclude_rewarded=exclude_rewarded,
        )

        BraveEncounter.at_repeat(encounter)

        self.assertEqual(1, encounter.db.round)
        reward_mock.assert_not_called()
        stop_mock.assert_not_called()
        refresh_mock.assert_not_called()
        self.assertTrue(encounter.ndb.brave_victory_pending)
        self.assertEqual(COMBAT_FINISH_FX_DELAY, delay_mock.call_args.args[0])
        self.assertEqual("|gThe last of them falls. The way is clear for now.|n", delay_mock.call_args.args[2])
        self.assertIs(delay_mock.call_args.kwargs["persistent"], False)

    def test_finish_victory_sequence_rewards_then_stops(self):
        winner = DummyRewardCharacter(1, "Starter")
        reward_mock = Mock(return_value=[winner])
        stop_mock = Mock()
        msg_mock = Mock()
        encounter = SimpleNamespace(
            ndb=SimpleNamespace(brave_victory_pending=True),
            obj=SimpleNamespace(msg_contents=msg_mock),
            _reward_victory=reward_mock,
            stop=stop_mock,
        )

        BraveEncounter._finish_victory_sequence(encounter, "victory message")

        self.assertFalse(encounter.ndb.brave_victory_pending)
        self.assertTrue(encounter.ndb.brave_skip_combat_done)
        reward_mock.assert_called_once_with()
        msg_mock.assert_called_once_with("victory message", exclude=[winner])
        stop_mock.assert_called_once_with()

    @patch("world.browser_panels.send_webclient_event")
    def test_clear_browser_combat_views_skips_after_victory_view(self, send_webclient_event_mock):
        winner = DummyRewardCharacter(1, "Starter")
        encounter = SimpleNamespace(
            ndb=SimpleNamespace(brave_skip_combat_done=True),
            get_participants=lambda: [winner],
        )

        BraveEncounter._clear_browser_combat_views(encounter)

        send_webclient_event_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
