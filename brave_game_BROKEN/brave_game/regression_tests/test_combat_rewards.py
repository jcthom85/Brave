import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter, COMBAT_FINISH_FX_DELAY


class DummyRewardCharacter:
    def __init__(self, char_id, key, *, brave_class="warrior"):
        self.id = char_id
        self.key = key
        self.db = SimpleNamespace(
            brave_class=brave_class,
            brave_silver=0,
            brave_resources={"hp": 30},
        )
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
        encounter._participant_reward_weight = lambda character, max_turn, top_impact: BraveEncounter._participant_reward_weight(
            encounter,
            character,
            max_turn=max_turn,
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

    @patch("world.browser_panels.send_webclient_event")
    @patch("world.browser_views.build_combat_victory_view", return_value={"view": "victory"})
    @patch("typeclasses.scripts.pop_recent_quest_updates", return_value=[])
    @patch("typeclasses.scripts.record_encounter_victory")
    @patch("typeclasses.scripts.roll_enemy_rewards", return_value={"silver": 30, "items": [("wolf_fang", 1), ("greymaw_pelt", 1)]})
    def test_reward_victory_scales_late_joiners_and_blocks_idle_leech(
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
                turn_count=4,
                enemies=[{"template_key": "old_greymaw", "xp": 120, "tags": ["boss"]}],
                participant_contributions={
                    "1": {
                        "joined_turn": 0,
                        "meaningful_actions": 3,
                        "damage_done": 60,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 1,
                        "hits_taken": 2,
                        "boss_credit_eligible": True,
                    },
                    "2": {
                        "joined_turn": 2,
                        "meaningful_actions": 1,
                        "damage_done": 12,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": True,
                    },
                    "3": {
                        "joined_turn": 2,
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
        self.assertGreater(starter.xp_awards[0], late.xp_awards[0])
        self.assertEqual([], idle.xp_awards)
        self.assertGreater(starter.db.brave_silver, late.db.brave_silver)
        self.assertEqual(0, idle.db.brave_silver)
        self.assertEqual(2, len(starter.items) + len(late.items))
        self.assertEqual([], idle.items)
        self.assertEqual({starter, late}, {call.args[0] for call in record_encounter_victory.call_args_list})
        self.assertTrue(any("Victory passes you by" in message for message in idle.messages))

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
                        "joined_turn": 0,
                        "meaningful_actions": 1,
                        "damage_done": 0,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": True,
                    },
                    "2": {
                        "joined_turn": 2,
                        "meaningful_actions": 1,
                        "damage_done": 0,
                        "healing_done": 0,
                        "damage_prevented": 0,
                        "utility_points": 0,
                        "hits_taken": 0,
                        "boss_credit_eligible": False,
                    },
                    "3": {
                        "joined_turn": 0,
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
            get_registered_participants=lambda: [starter, late, idle],
        )
        self._bind_reward_helpers(encounter)

        BraveEncounter._damage_enemy(encounter, starter, enemy, 12)

        self.assertEqual([starter], [call.args[0] for call in advance_enemy_defeat.call_args_list])

    @patch("typeclasses.scripts.delay")
    def test_at_repeat_schedules_victory_after_finish_fx_window(self, delay_mock):
        winner = DummyRewardCharacter(1, "Starter")
        reward_mock = Mock(return_value=[winner])
        stop_mock = Mock()
        refresh_mock = Mock()
        encounter = SimpleNamespace(
            db=SimpleNamespace(turn_count=0),
            ndb=SimpleNamespace(brave_victory_pending=False),
            obj=SimpleNamespace(msg_contents=lambda _message, **_kwargs: None),
            get_active_participants=lambda: [winner],
            get_active_enemies=lambda: [],
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

        self.assertEqual(0, encounter.db.turn_count)
        reward_mock.assert_not_called()
        stop_mock.assert_not_called()
        refresh_mock.assert_called_once_with()
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
        reward_mock.assert_called_once_with()
        msg_mock.assert_called_once_with("victory message", exclude=[winner])
        stop_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
