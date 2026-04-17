import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.roaming import _refresh_room_views


class DummyCharacter:
    def __init__(self, key, *, showing_result=False):
        self.key = key
        self.is_connected = True
        self.ndb = SimpleNamespace(brave_showing_combat_result=showing_result)

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


class DummyRoom:
    def __init__(self, contents):
        self.contents = list(contents)
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


if __name__ == "__main__":
    unittest.main()
