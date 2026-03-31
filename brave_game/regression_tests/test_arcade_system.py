import os
import types
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.arcade import merge_arcade_leaderboard, resolve_arcade_game_query, submit_arcade_score


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
