import os
import types
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.arcade import (
    build_arcade_result_payload,
    merge_arcade_leaderboard,
    resolve_arcade_game_query,
    submit_arcade_score,
)


class _StubCharacter:
    def __init__(self):
        self.key = "Mina"
        self.db = types.SimpleNamespace(
            brave_arcade_best_scores={},
            brave_arcade_claims={},
        )
        self.received = []

    def add_item_to_inventory(self, template_id, quantity=1):
        self.received.append((template_id, quantity))


class _StubCabinet:
    def __init__(self):
        self.id = 77
        self.key = "Joss's Flashing Cabinet"
        self.db = types.SimpleNamespace(
            brave_entity_id="lantern_rest_arcade_cabinet",
            brave_arcade_scores={},
            brave_arcade_rewards={"maze_runner": {"threshold": 2000, "item": "lantern_pixel_pin"}},
        )


class ArcadeSystemTests(unittest.TestCase):
    def test_game_query_resolves_exact_and_partial_names(self):
        match, options = resolve_arcade_game_query("maze", ["maze_runner"])
        self.assertEqual("maze_runner", match)
        self.assertEqual(["maze_runner"], options)

    def test_merge_leaderboard_keeps_each_players_best_score(self):
        updated, details = merge_arcade_leaderboard(
            [
                {"name": "Mina", "score": 900},
                {"name": "Rowan", "score": 1200},
                {"name": "Mina", "score": 1100},
            ],
            "Mina",
            1400,
        )
        self.assertEqual(
            [
                {"name": "Mina", "score": 1400},
                {"name": "Rowan", "score": 1200},
            ],
            updated,
        )
        self.assertEqual(1, details["rank"])
        self.assertTrue(details["new_top_score"])

    def test_merge_leaderboard_reports_rank_beyond_visible_board(self):
        updated, details = merge_arcade_leaderboard(
            [
                {"name": "Ava", "score": 1600},
                {"name": "Bryn", "score": 1500},
                {"name": "Cato", "score": 1400},
                {"name": "Dara", "score": 1300},
                {"name": "Eli", "score": 1200},
            ],
            "Mina",
            1100,
        )
        self.assertEqual(5, len(updated))
        self.assertEqual(6, details["rank"])
        self.assertEqual("Eli", updated[-1]["name"])

    def test_submit_score_grants_threshold_reward_once(self):
        character = _StubCharacter()
        cabinet = _StubCabinet()

        first = submit_arcade_score(character, cabinet, "maze_runner", 2150)
        second = submit_arcade_score(character, cabinet, "maze_runner", 2300)

        self.assertEqual([("lantern_pixel_pin", 1)], character.received)
        self.assertIsNotNone(first["reward"])
        self.assertIsNone(second["reward"])
        self.assertEqual(2300, second["best_score"])
        self.assertEqual(2300, cabinet.db.brave_arcade_scores["maze_runner"][0]["score"])

    def test_result_payload_includes_leaderboard_summary_and_reward_note(self):
        cabinet = _StubCabinet()
        details = {
            "entries": [{"name": "Mina", "score": 2300}, {"name": "Rowan", "score": 1800}],
            "rank": 1,
            "best_score": 2300,
            "improved_personal_best": True,
            "new_top_score": True,
            "player_name": "Mina",
            "reward": {"item_name": "Lantern Pixel Pin"},
        }

        payload = build_arcade_result_payload(cabinet, "maze_runner", 2300, details)

        self.assertEqual("Joss's Flashing Cabinet", payload["cabinet"])
        self.assertEqual("Maze Runner", payload["title"])
        self.assertEqual("NEW HIGH SCORE", payload["headline"])
        self.assertEqual(
            [
                {"label": "Your Score", "value": "2,300", "accent": "score"},
                {"label": "Your Rank", "value": "#1", "accent": "rank"},
                {"label": "High Score", "value": "2,300", "accent": "high"},
            ],
            payload["summary_stats"],
        )
        self.assertEqual(
            [
                {"rank": 1, "name": "Mina", "score": "2,300", "is_current": True, "is_top": True},
                {"rank": 2, "name": "Rowan", "score": "1,800", "is_current": False, "is_top": False},
            ],
            payload["leaderboard"],
        )
        self.assertIsNone(payload["player_row"])
        self.assertEqual(
            [
                {"tone": "record", "text": "New cabinet record."},
                {"tone": "reward", "text": "Prize drawer opens: Lantern Pixel Pin."},
            ],
            payload["notes"],
        )

    def test_result_payload_surfaces_off_board_standing_row(self):
        cabinet = _StubCabinet()
        details = {
            "entries": [
                {"name": "Ava", "score": 1600},
                {"name": "Bryn", "score": 1500},
                {"name": "Cato", "score": 1400},
                {"name": "Dara", "score": 1300},
                {"name": "Eli", "score": 1200},
            ],
            "rank": 6,
            "best_score": 1100,
            "improved_personal_best": True,
            "player_name": "Mina",
            "reward": None,
        }

        payload = build_arcade_result_payload(cabinet, "maze_runner", 1100, details)

        self.assertEqual("#6", payload["summary_stats"][1]["value"])
        self.assertEqual(
            {"rank": 6, "name": "Mina", "score": "1,100", "is_current": True},
            payload["player_row"],
        )
