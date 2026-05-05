import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.navigation import get_exit_block_message, is_exit_available, visible_exits


class DummyExit:
    def __init__(self, key, label, *, required_quest=None, lock_message=None):
        self.key = key
        self.destination = SimpleNamespace(key=label)
        self.db = SimpleNamespace(
            brave_direction=key,
            brave_exit_label=label,
            brave_required_quest=required_quest,
            brave_lock_message=lock_message,
        )


class DummyRoom:
    def __init__(self, exits):
        self.exits = exits


class DummyCharacter:
    def __init__(self, quests=None):
        self.db = SimpleNamespace(brave_quests=quests or {})


class LanternworksRouteTests(unittest.TestCase):
    def test_lower_lanternworks_route_is_plain_local_room(self):
        town_exit = DummyExit("west", "Town Green")
        lanternworks_exit = DummyExit("east", "Lower Lanternworks")
        room = DummyRoom([lanternworks_exit, town_exit])
        character = DummyCharacter()

        self.assertTrue(is_exit_available(lanternworks_exit, character))
        self.assertEqual([lanternworks_exit, town_exit], visible_exits(room, character))
        self.assertEqual("That route is not ready for you yet.", get_exit_block_message(lanternworks_exit))

    def test_authored_quest_locks_still_work_for_other_routes(self):
        locked_exit = DummyExit("east", "Old Worksite", required_quest="bridgework_for_joss")
        room = DummyRoom([locked_exit])
        character = DummyCharacter({"bridgework_for_joss": {"status": "active"}})

        self.assertTrue(is_exit_available(locked_exit, character))
        self.assertEqual([locked_exit], visible_exits(room, character))


if __name__ == "__main__":
    unittest.main()
