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

from world.browser_views import WELCOME_PAGES, build_room_view


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyExit:
    def __init__(self, key, destination_key, *, direction=None, label=None):
        self.key = key
        self.destination = SimpleNamespace(key=destination_key)
        self.db = SimpleNamespace(
            brave_direction=direction or key,
            brave_exit_label=label,
        )


class DummyRoom:
    def __init__(self):
        self.key = "Lantern Rest"
        self.db = SimpleNamespace(
            brave_world="Brave",
            brave_zone="Brambleford",
            brave_safe=True,
            desc="Warm light, steady conversation, and a clean path to the street.",
        )
        self.exits = [
            DummyExit("north", "Town Green"),
            DummyExit("east", "Kitchen"),
            DummyExit("up", "Guest Loft"),
        ]


class DummyCharacter:
    def __init__(self):
        self.id = 77
        self.key = "Dad"
        self.location = None
        self.db = SimpleNamespace(
            brave_inventory=[
                {"template": "innkeepers_fishpie", "quantity": 2},
                {"template": "lantern_carp", "quantity": 3},
            ],
            brave_silver=18,
            brave_party_id=None,
            brave_party_leader_id=None,
            brave_party_invites=[],
            brave_follow_target_id=None,
            brave_tutorial={},
            brave_welcome_shown=False,
        )


class RoomViewTests(unittest.TestCase):
    def test_room_view_includes_mobile_pack_summary_and_navpad(self):
        view = build_room_view(DummyRoom(), DummyCharacter())

        self.assertEqual("room", view.get("variant"))
        self.assertEqual(
            18,
            view.get("mobile_pack", {}).get("silver"),
        )
        self.assertEqual(2, view.get("mobile_pack", {}).get("item_types"))
        self.assertEqual(2, view.get("mobile_pack", {}).get("consumables"))
        self.assertEqual(3, view.get("mobile_pack", {}).get("ingredients"))
        self.assertEqual(
            [
                {"label": "Innkeeper's Fish Pie", "quantity": 2},
                {"label": "Lantern Carp", "quantity": 3},
            ],
            view.get("mobile_pack", {}).get("preview"),
        )

        ways_forward = _section(view, "Ways Forward")
        self.assertEqual("navpad", ways_forward.get("kind"))
        self.assertEqual(["N", "E"], [item.get("badge") for item in ways_forward.get("items", [])])
        self.assertEqual(["U"], [item.get("badge") for item in ways_forward.get("vertical_items", [])])

        vicinity = _section(view, "The Vicinity")
        self.assertEqual("vicinity", vicinity.get("variant"))
        self.assertEqual("list", vicinity.get("kind"))
        self.assertEqual("The vicinity is quiet.", vicinity.get("items", [])[0].get("text"))
        self.assertEqual([], view.get("guidance", []))
        self.assertEqual([], view.get("welcome_pages", []))

    def test_room_view_includes_tutorial_guidance_and_welcome_pages(self):
        character = DummyCharacter()
        tutorial_state = {"status": "active", "step": "first_steps", "flags": {}}

        with patch("world.browser_views.ensure_tutorial_state", return_value=tutorial_state):
            view = build_room_view(DummyRoom(), character)

        self.assertGreater(len(view.get("guidance", [])), 1)
        self.assertEqual(WELCOME_PAGES, view.get("welcome_pages"))
        self.assertTrue(character.db.brave_welcome_shown)


if __name__ == "__main__":
    unittest.main()
