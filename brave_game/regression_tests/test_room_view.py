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

from world.browser_views import WELCOME_PAGES, build_map_view, build_room_view
from world.navigation import build_map_snapshot, build_minimap_snapshot
from typeclasses.scripts import BraveEncounter


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
            brave_room_id="lantern_rest",
            brave_activities=[],
            desc="Warm light, steady conversation, and a clean path to the street.",
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
        self.ndb = SimpleNamespace()

    def get_active_encounter(self):
        return None


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


class DummyMappedRoom:
    def __init__(self, room_id, key="Blackreed's Roost", x=0, y=0):
        self.id = 501
        self.key = key
        self.db = SimpleNamespace(
            brave_map_region="Test Ridge",
            brave_map_x=x,
            brave_map_y=y,
            brave_map_icon="R",
            brave_room_id=room_id,
            brave_activities=[],
            brave_portal_hub=False,
        )
        self.exits = []


class RoomViewTests(unittest.TestCase):
    def test_room_view_includes_room_actions_payload_for_valid_room_verbs(self):
        room = DummyRoom()
        room.db.brave_safe = True

        view = build_room_view(room, DummyCharacter())
        room_actions = view.get("room_actions", [])

        self.assertEqual(["rest", None], [item.get("command") for item in room_actions])
        self.assertEqual("Emote", room_actions[-1].get("text"))
        self.assertEqual("sentiment_satisfied", room_actions[-1].get("icon"))
        self.assertIn("picker", room_actions[-1])
        picker = room_actions[-1]["picker"]
        self.assertEqual("Emote", picker.get("title"))
        self.assertEqual("Choose a social emote.", picker.get("subtitle"))
        self.assertEqual(
            ["Smile", "Nod", "Wave", "Shrug", "Laugh", "Frown", "Bow", "Think"],
            [option.get("label") for option in picker.get("options", [])],
        )

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
        mobile_panels = view.get("mobile_panels", {})
        self.assertEqual("Lantern Rest", mobile_panels.get("title"))
        self.assertEqual("Safe", mobile_panels.get("status_label"))
        self.assertEqual(3, mobile_panels.get("route_count"))
        self.assertEqual("Dad", mobile_panels.get("character", {}).get("name"))
        self.assertEqual(18, mobile_panels.get("pack", {}).get("silver"))
        self.assertEqual(0, mobile_panels.get("quests", {}).get("active_count"))
        self.assertFalse(mobile_panels.get("party", {}).get("in_party"))

        ways_forward = view.get("sections", [])[0]
        self.assertTrue(ways_forward.get("hide_label"))
        self.assertEqual("navpad", ways_forward.get("kind"))
        self.assertEqual(["N", "E"], [item.get("badge") for item in ways_forward.get("items", [])])
        self.assertEqual(["U"], [item.get("badge") for item in ways_forward.get("vertical_items", [])])

        vicinity = _section(view, "The Vicinity")
        self.assertEqual("vicinity", vicinity.get("variant"))
        self.assertEqual("list", vicinity.get("kind"))
        self.assertEqual("All is quiet.", vicinity.get("items", [])[0].get("text"))
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

    def test_room_view_renders_compact_grouped_threat_card(self):
        room = DummyRoom()
        room.db.brave_safe = False

        view = build_room_view(
            room,
            DummyCharacter(),
            visible_threats=[
                {
                    "display_name": "Red Wyrm Retinue",
                    "composition": "2 Red Wyrms + 1 Red Wyrm Champion",
                    "count": 3,
                    "detail": "2 Red Wyrms + 1 Red Wyrm Champion",
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
        self.assertIsNone(threat_item.get("detail"))
        self.assertEqual("3", threat_item.get("badge"))
        self.assertEqual("skull", threat_item.get("marker_icon"))
        self.assertEqual("fight", threat_item.get("actions", [])[1].get("command"))
        self.assertEqual("Inspect", threat_item.get("actions", [])[0].get("label"))
        inspect_picker = threat_item.get("actions", [])[0].get("picker", {})
        self.assertEqual("Red Wyrm Retinue", inspect_picker.get("title"))
        self.assertEqual(["2 Red Wyrms + 1 Red Wyrm Champion"], inspect_picker.get("body", []))
        self.assertEqual("fight", inspect_picker.get("options", [])[0].get("command"))

    def test_single_enemy_party_uses_enemy_name_and_no_redundant_composition(self):
        room = DummyRoom()
        room.db.brave_safe = False

        view = build_room_view(
            room,
            DummyCharacter(),
            visible_threats=[
                {
                    "display_name": "Road Wolf",
                    "composition": "Road Wolf",
                    "count": 1,
                    "badge": "1",
                    "command": "fight",
                    "tooltip": "1 hostile · wary threat",
                }
            ],
        )

        threat_item = _section(view, "The Vicinity").get("items", [])[0]
        inspect_picker = threat_item.get("actions", [])[0].get("picker", {})
        self.assertEqual("Road Wolf", threat_item.get("text"))
        self.assertIsNone(threat_item.get("detail"))
        self.assertEqual("Road Wolf", inspect_picker.get("title"))
        self.assertEqual([], inspect_picker.get("body", []))

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
                    "display_name": "Grave Crow Flight",
                    "composition": "2 Grave Crows",
                    "detail": "Engaged",
                    "badge": "2",
                    "marker_icon": "swords",
                    "command": "fight",
                    "tooltip": "2 hostiles · fight underway",
                    "engaged": True,
                }
            ],
            visible_chars=[ally],
        )

        vicinity = _section(view, "The Vicinity")
        items = vicinity.get("items", [])
        self.assertEqual("swords", items[0].get("marker_icon"))
        self.assertEqual("Engaged", items[0].get("detail"))
        self.assertEqual("Peep", items[1].get("text"))
        self.assertEqual("Engaged", items[1].get("detail"))
        self.assertEqual("swords", items[1].get("marker_icon"))

    def test_visible_threats_list_identical_roaming_parties_separately(self):
        room = DummyRoom()
        room.db.brave_safe = False
        room.db.brave_room_id = "wolf_turn"
        viewer = DummyCharacter()
        viewer.location = room

        preview = {
            "room_id": "wolf_turn",
            "roaming_parties": [
                {
                    "key": "road_wolves_a",
                    "room_id": "wolf_turn",
                    "encounter": {
                        "key": "road_wolves",
                        "title": "Road Wolves",
                        "intro": "",
                        "enemies": ["road_wolf", "road_wolf"],
                    },
                },
                {
                    "key": "road_wolves_b",
                    "room_id": "wolf_turn",
                    "encounter": {
                        "key": "road_wolves",
                        "title": "Road Wolves",
                        "intro": "",
                        "enemies": ["road_wolf", "road_wolf"],
                    },
                },
            ],
        }

        with patch.object(BraveEncounter, "get_room_threat_preview", return_value=preview):
            threats = BraveEncounter.get_visible_room_threats(room, viewer)

        self.assertEqual(2, len(threats))
        self.assertEqual(["Road Wolves", "Road Wolves"], [threat.get("key") for threat in threats])
        self.assertEqual(["2", "2"], [threat.get("badge") for threat in threats])
        self.assertEqual(["fight road_wolves_a", "fight road_wolves_b"], [threat.get("command") for threat in threats])

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

    def test_map_snapshot_stacks_full_map_markers_by_priority(self):
        character = DummyCharacter()
        character.db.brave_tracked_quest = "captain_varn_blackreed"
        character.db.brave_quests = {
            "captain_varn_blackreed": {
                "status": "active",
                "objectives": [
                    {"completed": False},
                    {"completed": False},
                ],
            }
        }
        room = DummyMappedRoom("ruined_watchtower_blackreed_roost")

        with patch("world.navigation.get_rooms_in_map_region", return_value=[room]):
            snapshot = build_map_snapshot(room, character=character)

        center_cell = snapshot["map_tiles"]["rows"][1][1]
        self.assertEqual("player", center_cell.get("symbol"))
        self.assertEqual("current", center_cell.get("primary_marker"))
        self.assertEqual(["current", "quest", "boss"], [marker.get("key") for marker in center_cell.get("markers")])
        self.assertIn("Tracked Quest", center_cell.get("title"))
        self.assertIn("Boss", center_cell.get("title"))
        self.assertEqual(
            ["You", "Tracked Quest", "Boss"],
            [entry.get("label") for entry in snapshot.get("legend")],
        )

    def test_minimap_snapshot_uses_simple_symbols_without_marker_stack(self):
        character = DummyCharacter()
        character.db.brave_tracked_quest = "captain_varn_blackreed"
        character.db.brave_quests = {
            "captain_varn_blackreed": {
                "status": "active",
                "objectives": [
                    {"completed": False},
                    {"completed": False},
                ],
            }
        }
        room = DummyMappedRoom("ruined_watchtower_blackreed_roost")

        with patch("world.navigation.get_rooms_in_map_region", return_value=[room]):
            snapshot = build_minimap_snapshot(room, character=character)

        center_cell = snapshot["map_tiles"]["rows"][1][1]
        self.assertEqual("player", center_cell.get("symbol"))
        self.assertEqual([], center_cell.get("markers"))
        self.assertEqual("", center_cell.get("primary_marker"))


if __name__ == "__main__":
    unittest.main()
