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


class NexusGateTests(unittest.TestCase):
    def test_nexus_route_hidden_until_bridgework_is_active(self):
        town_exit = DummyExit("west", "Town Green")
        nexus_exit = DummyExit(
            "east",
            "Nexus Gate",
            required_quest="bridgework_for_joss",
            lock_message="Joss has the lower gate chamber chained shut until the bridgework is stable.",
        )
        room = DummyRoom([nexus_exit, town_exit])
        character = DummyCharacter()

        self.assertFalse(is_exit_available(nexus_exit, character))
        self.assertEqual([town_exit], visible_exits(room, character))
        self.assertEqual(
            "Joss has the lower gate chamber chained shut until the bridgework is stable.",
            get_exit_block_message(nexus_exit),
        )

    def test_nexus_route_visible_after_bridgework_unlocks(self):
        nexus_exit = DummyExit("east", "Nexus Gate", required_quest="bridgework_for_joss")
        room = DummyRoom([nexus_exit])
        character = DummyCharacter({"bridgework_for_joss": {"status": "active"}})

        self.assertTrue(is_exit_available(nexus_exit, character))
        self.assertEqual([nexus_exit], visible_exits(room, character))


if __name__ == "__main__":
    unittest.main()
