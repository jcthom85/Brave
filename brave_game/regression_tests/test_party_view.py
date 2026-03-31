import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda *args, **kwargs: None
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules.setdefault("world.chargen", chargen_stub)

from world.browser_views import build_party_view


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyLocation:
    def __init__(self):
        self.contents = []


class DummyCharacter:
    def __init__(self, char_id, key, location):
        self.id = char_id
        self.key = key
        self.location = location
        self.is_connected = True
        self.db = SimpleNamespace(
            brave_party_id=None,
            brave_party_leader_id=None,
            brave_party_invites=[],
            brave_follow_target_id=None,
        )

    def ensure_brave_character(self):
        return None


class PartyViewTests(unittest.TestCase):
    @patch("world.browser_views.get_follow_target", return_value=None)
    @patch("world.browser_views.get_party_leader", return_value=None)
    @patch("world.browser_views.get_party_members", return_value=[])
    def test_party_view_lists_nearby_players_for_invites(self, _members, _leader, _follow):
        room = DummyLocation()
        viewer = DummyCharacter(7, "Dad", room)
        nearby = DummyCharacter(8, "Peep", room)
        room.contents = [viewer, nearby]

        view = build_party_view(viewer)

        status = _section(view, "Status")
        self.assertIn("Invite someone nearby to start one.", status.get("lines", []))

        nearby_players = _section(view, "Nearby Players")
        self.assertEqual("list", nearby_players.get("kind"))
        self.assertEqual("Peep", nearby_players.get("items", [])[0].get("text"))
        self.assertEqual("party invite Peep", nearby_players.get("items", [])[0].get("command"))


if __name__ == "__main__":
    unittest.main()
