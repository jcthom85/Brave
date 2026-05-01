import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.roaming import (
    BraveRoamingPartyManager,
    _party_is_stationary,
    _refresh_room_views,
    _room_has_static_stationary_boss,
)


class DummyCharacter:
    def __init__(self, key, *, showing_result=False):
        self.key = key
        self.is_connected = True
        self.ndb = SimpleNamespace(brave_showing_combat_result=showing_result)

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


class DummyRoom:
    def __init__(self, contents=None, *, room_id=None, safe=False):
        self.db = SimpleNamespace(brave_room_id=room_id, brave_safe=safe)
        self.contents = list(contents or [])
        self.exits = []
        self.return_appearance = Mock()


class RoamingRefreshTests(unittest.TestCase):
    @patch("world.roaming.sort_exits", return_value=[])
    def test_refresh_room_views_skips_characters_holding_combat_result(self, _sort_exits):
        winner = DummyCharacter("Winner", showing_result=True)
        watcher = DummyCharacter("Watcher", showing_result=False)
        room = DummyRoom([winner, watcher])

        with patch("world.roaming.get_room", return_value=room):
            _refresh_room_views({"brush_line"})

        self.assertEqual([(watcher,)], [call.args for call in room.return_appearance.call_args_list])


class RoamingMovementTests(unittest.TestCase):
    def test_ruk_template_makes_any_roaming_state_stationary(self):
        party = {
            "key": "stale_ruk_state",
            "encounter": {"title": "Ruk the Fence-Cutter", "enemies": ["ruk_fence_cutter"]},
        }

        self.assertTrue(_party_is_stationary(party))

    def test_stationary_enemy_party_does_not_select_destination(self):
        class DummyManager:
            _advance_parties = BraveRoamingPartyManager._advance_parties

            def _select_destination(self, party, parties):
                raise AssertionError("stationary parties must not select destinations")

        manager = DummyManager()
        party = {
            "key": "stale_ruk_state",
            "room_id": "goblin_road_fencebreaker_camp",
            "start_room_id": "goblin_road_fencebreaker_camp",
            "interval": 18,
            "next_move_at": 0,
            "respawn_at": 0,
            "engaged": False,
            "encounter": {"title": "Ruk the Fence-Cutter", "enemies": ["ruk_fence_cutter"]},
        }

        changed_rooms = manager._advance_parties({"stale_ruk_state": party})

        self.assertEqual(set(), changed_rooms)
        self.assertEqual("goblin_road_fencebreaker_camp", party["room_id"])
        self.assertGreater(party["next_move_at"], time.time())

    def test_static_stationary_boss_room_blocks_roaming_parties(self):
        room = DummyRoom(room_id="goblin_road_fencebreaker_camp")
        manager = BraveRoamingPartyManager()

        self.assertTrue(_room_has_static_stationary_boss(room))
        self.assertTrue(manager._room_is_blocked(room))


if __name__ == "__main__":
    unittest.main()
