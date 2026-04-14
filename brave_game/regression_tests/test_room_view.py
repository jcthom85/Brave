import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda *args, **kwargs: None
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules.setdefault("world.chargen", chargen_stub)

from typeclasses.characters import Character
from typeclasses.rooms import Room, _find_direction_to_room, _format_enter_direction, _should_announce_room_movement
from world.browser_views import WELCOME_PAGES, build_map_view, build_room_view


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
    def __init__(self, room_id=None):
        self.key = "Lantern Rest"
        self.db = SimpleNamespace(
            brave_world="Brave",
            brave_zone="Brambleford",
            brave_safe=True,
            desc="Warm light, steady conversation, and a clean path to the street.",
            brave_room_id=room_id,
        )
        self.ndb = SimpleNamespace(brave_encounter=None)
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


class DummyVisibleCharacter:
    def __init__(self, char_id, key, room):
        self.id = char_id
        self.key = key
        self.location = room
        self.db = SimpleNamespace(
            brave_party_id=None,
        )


class DummyMapRoom:
    def __init__(self):
        self.db = SimpleNamespace(
            brave_zone="Brambleford",
            brave_safe=True,
        )


class DummyMovementRoom:
    def __init__(self, exits=None):
        self.exits = list(exits or [])


class DummyMovementCharacter:
    def __init__(self, connected=True):
        self.is_connected = connected

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


class LightweightCharacter(Character):
    @property
    def key(self):
        return getattr(self, "_test_key", "")

    @key.setter
    def key(self, value):
        self._test_key = value

    @property
    def location(self):
        return getattr(self, "_test_location", None)

    @location.setter
    def location(self, value):
        self._test_location = value


class LightweightRoom(Room):
    @property
    def key(self):
        return getattr(self, "_test_key", "")

    @key.setter
    def key(self, value):
        self._test_key = value

    @property
    def exits(self):
        return getattr(self, "_test_exits", [])

    @exits.setter
    def exits(self, value):
        self._test_exits = value


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
        character.db.brave_tutorial = {"status": "active", "step": "first_steps", "flags": {}}

        view = build_room_view(DummyRoom(room_id="tutorial_wayfarers_yard"), character)

        self.assertGreater(len(view.get("guidance", [])), 1)
        self.assertEqual(WELCOME_PAGES, view.get("welcome_pages"))
        self.assertFalse(character.db.brave_welcome_shown)
        self.assertNotIn("Current Lesson", [section.get("label") for section in view.get("sections", [])])
        self.assertIsNone(view.get("tutorial_notice"))
        self.assertEqual(WELCOME_PAGES, view.get("tutorial_carousel", {}).get("pages"))
        self.assertEqual("talk Sergeant Tamsin Vale", view.get("tutorial_carousel", {}).get("final_action", {}).get("command"))
        self.assertEqual("First Steps In Brambleford", view.get("tutorial_quest", {}).get("title"))
        self.assertIn(
            {"text": "Speak with Sergeant Tamsin Vale.", "completed": False},
            view.get("tutorial_quest", {}).get("objectives", []),
        )
        tracked_quest = view.get("reactive", {}).get("tracked_quest", {})
        self.assertEqual("First Steps In Brambleford", tracked_quest.get("title"))
        self.assertIn(
            {"text": "Speak with Sergeant Tamsin Vale.", "completed": False},
            tracked_quest.get("objectives", []),
        )

    def test_room_view_tracks_tutorial_quest_after_vermin_fight(self):
        character = DummyCharacter()
        character.db.brave_tutorial = {
            "status": "active",
            "step": "through_the_gate",
            "flags": {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "returned_to_wayfarers_yard": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": True,
                "talked_brask": True,
                "won_vermin_fight": True,
            },
        }

        view = build_room_view(DummyRoom(room_id="tutorial_vermin_pens"), character)

        self.assertIsNone(view.get("tutorial_notice"))
        self.assertEqual("Through The Gate", view.get("tutorial_quest", {}).get("title"))
        self.assertEqual(
            [{"text": "Report to Captain Harl Rowan in the Training Yard.", "completed": False}],
            view.get("tutorial_quest", {}).get("objectives", []),
        )
        self.assertEqual("Through The Gate", view.get("reactive", {}).get("tracked_quest", {}).get("title"))

    def test_room_view_gate_walk_keeps_tutorial_in_quest_payload(self):
        character = DummyCharacter()
        character.db.brave_tutorial = {
            "status": "active",
            "step": "through_the_gate",
            "flags": {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "returned_to_wayfarers_yard": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": True,
                "talked_brask": True,
                "won_vermin_fight": True,
            },
        }

        view = build_room_view(DummyRoom(room_id="tutorial_gate_walk"), character)

        self.assertIsNone(view.get("tutorial_notice"))
        self.assertEqual("tutorial", view.get("tutorial_quest", {}).get("source"))
        self.assertIn(
            {"text": "Report to Captain Harl Rowan in the Training Yard.", "completed": False},
            view.get("tutorial_quest", {}).get("objectives", []),
        )

    def test_room_view_renders_compact_grouped_threat_card(self):
        room = DummyRoom()
        room.db.brave_safe = False

        view = build_room_view(
            room,
            DummyCharacter(),
            visible_threats=[
                {
                    "key": "Red Wyrm Retinue",
                    "detail": "dragon, soldier, wolf",
                    "badge": "3",
                    "marker_icon": "skull",
                    "command": "fight",
                    "tooltip": "3 hostiles · deadly threat",
                }
            ],
        )

        vicinity = _section(view, "The Vicinity")
        threat_item = vicinity.get("items", [])[0]

        self.assertEqual("Red Wyrm Retinue", threat_item.get("text"))
        self.assertEqual("dragon, soldier, wolf", threat_item.get("detail"))
        self.assertEqual("3", threat_item.get("badge"))
        self.assertEqual("skull", threat_item.get("marker_icon"))
        self.assertEqual("fight", threat_item.get("command"))

    def test_room_view_marks_engaged_threats_and_characters(self):
        room = DummyRoom()
        room.db.brave_safe = False
        room.ndb.brave_encounter = SimpleNamespace(db=SimpleNamespace(participants=[21]))
        viewer = DummyCharacter()
        viewer.location = room
        ally = DummyVisibleCharacter(21, "Peep", room)

        view = build_room_view(
            room,
            viewer,
            visible_threats=[
                {
                    "key": "Grave Crow Flight",
                    "detail": "Engaged · crows",
                    "badge": "2",
                    "marker_icon": "swords",
                    "command": "fight",
                    "tooltip": "2 hostiles · fight underway",
                }
            ],
            visible_chars=[ally],
        )

        vicinity = _section(view, "The Vicinity")
        items = vicinity.get("items", [])
        self.assertEqual("swords", items[0].get("marker_icon"))
        self.assertEqual("Engaged · crows", items[0].get("detail"))
        self.assertEqual("Peep", items[1].get("text"))
        self.assertEqual("Engaged", items[1].get("detail"))
        self.assertEqual("swords", items[1].get("marker_icon"))


    def test_map_view_uses_map_icon_and_region_card_label(self):
        character = DummyCharacter()
        room = DummyMapRoom()

        with patch(
            "world.browser_views.build_map_snapshot",
            return_value={
                "room": room,
                "region": "Fallback Region",
                "map_text": "map-text",
                "map_tiles": {"columns": 1, "rows": [[{"kind": "room", "symbol": "place", "tone": "room"}]]},
                "legend": [{"label": "You", "icon": "@", "symbol": "person_pin_circle"}],
                "party": [],
            },
        ):
            view = build_map_view(room, character)

        self.assertEqual("map", view.get("variant"))
        self.assertEqual("Map", view.get("title"))
        self.assertEqual("map", view.get("title_icon"))
        self.assertEqual("", view.get("subtitle"))
        self.assertEqual("", view.get("back_action", {}).get("label"))

        map_section = view.get("sections", [])[0]
        self.assertEqual("pre", map_section.get("kind"))
        self.assertEqual("Brambleford", map_section.get("label"))
        self.assertEqual(1, map_section.get("grid", {}).get("columns"))

    def test_room_activity_movement_helpers_format_directional_copy(self):
        source = DummyMovementRoom()
        destination = DummyMovementRoom(
            exits=[
                DummyExit("east", "Kitchen", direction="east", label="Kitchen"),
                DummyExit("north", "Square", direction="north", label="Square"),
            ]
        )
        destination.exits[0].destination = source

        self.assertEqual("east", _find_direction_to_room(destination, source))
        self.assertEqual(" from the east", _format_enter_direction("east"))
        self.assertEqual(" from in", _format_enter_direction("in"))

    def test_room_activity_movement_announcements_skip_non_player_cases(self):
        self.assertTrue(_should_announce_room_movement(DummyMovementCharacter(), "move"))
        self.assertFalse(_should_announce_room_movement(DummyMovementCharacter(connected=False), "move"))
        self.assertFalse(_should_announce_room_movement(DummyMovementCharacter(), "flee"))
        self.assertFalse(_should_announce_room_movement(None, "move"))

    def test_character_speech_emits_activity_for_self_and_room(self):
        room = SimpleNamespace()
        speaker = LightweightCharacter.__new__(LightweightCharacter)
        speaker.key = "Dad"
        speaker.location = room

        with patch("typeclasses.characters.DefaultCharacter.at_say", return_value=None) as parent_at_say, patch(
            "typeclasses.characters._send_webclient_event"
        ) as send_event, patch("typeclasses.characters._broadcast_webclient_activity") as broadcast_activity:
            Character.at_say(speaker, "Hello there.")

        parent_at_say.assert_called_once()
        send_event.assert_called_once_with(speaker, brave_activity={"text": 'You say, "Hello there."'})
        broadcast_activity.assert_called_once_with(
            speaker.location,
            'Dad says, "Hello there."',
            exclude=[speaker],
        )

    def test_room_receive_refreshes_vicinity_view(self):
        source = LightweightRoom.__new__(LightweightRoom)
        source.key = "Source Room"
        source.exits = []
        source.msg_contents = Mock()
        destination = LightweightRoom.__new__(LightweightRoom)
        destination.key = "Destination Room"
        destination.exits = []
        destination.msg_contents = Mock()
        mover = SimpleNamespace(
            id=321,
            key="Dad",
            is_connected=True,
            location=destination,
            msg=Mock(),
        )
        mover.is_typeclass = lambda path, exact=False: path == "typeclasses.characters.Character"

        with patch("typeclasses.rooms.DefaultRoom.at_object_receive", return_value=None), patch(
            "typeclasses.rooms._should_announce_room_movement",
            return_value=True,
        ), patch("typeclasses.rooms._find_direction_to_room", side_effect=["west", "east"]), patch(
            "typeclasses.rooms._broadcast_webclient_activity"
        ), patch(
            "typeclasses.rooms._refresh_room_webclient_views"
        ) as refresh_room_views:
            Room.at_object_receive(destination, mover, source)

        refresh_room_views.assert_called_once_with(destination)

    def test_room_leave_refreshes_vicinity_view(self):
        source = LightweightRoom.__new__(LightweightRoom)
        source.key = "Source Room"
        source.exits = []
        source.msg_contents = Mock()
        destination = LightweightRoom.__new__(LightweightRoom)
        destination.key = "Destination Room"
        destination.exits = []
        destination.msg_contents = Mock()
        mover = SimpleNamespace(
            id=654,
            key="Dad",
            is_connected=True,
            location=destination,
            msg=Mock(),
        )
        mover.is_typeclass = lambda path, exact=False: path == "typeclasses.characters.Character"

        with patch("typeclasses.rooms.DefaultRoom.at_object_leave", return_value=None), patch(
            "typeclasses.rooms._should_announce_room_movement",
            return_value=True,
        ), patch("typeclasses.rooms._find_direction_to_room", return_value="east"), patch(
            "typeclasses.rooms._broadcast_webclient_activity"
        ), patch(
            "typeclasses.rooms._refresh_room_webclient_views"
        ) as refresh_room_views:
            Room.at_object_leave(source, mover, destination)

        refresh_room_views.assert_called_once_with(source)


if __name__ == "__main__":
    unittest.main()
