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

from typeclasses.scripts import BraveEncounter


class DummyExit:
    def __init__(self, destination):
        self.destination = destination


class DummyRoom:
    def __init__(self, room_id, *, zone="Blackfen", safe=False, blocked=False, x=0, y=0):
        self.db = SimpleNamespace(
            brave_room_id=room_id,
            brave_zone=zone,
            brave_safe=safe,
            brave_enemy_movement_blocked=blocked,
            brave_map_region=zone.lower(),
            brave_map_x=x,
            brave_map_y=y,
            brave_room_threat_preview=None,
            brave_room_threat_previews=[],
            brave_room_threat_ready_at=0,
        )
        self.ndb = SimpleNamespace(brave_encounter=None)
        self.exits = []


class ThreatRoamingTests(unittest.TestCase):
    def test_can_preview_roam_only_within_zone_and_outside_safe_rooms(self):
        source = DummyRoom("source", zone="Blackfen", x=0, y=0)
        allowed = DummyRoom("allowed", zone="Blackfen", x=1, y=0)
        safe = DummyRoom("safe", zone="Blackfen", safe=True, x=0, y=1)
        other_zone = DummyRoom("other", zone="Brambleford", x=1, y=1)
        preview = {
            "preview_id": "p1",
            "origin_room_id": "source",
            "allowed_zone_keys": ["blackfen"],
            "roam_radius": 3,
            "roaming": True,
        }
        rooms = {"source": source}

        with patch("typeclasses.scripts.get_room", side_effect=lambda room_id: rooms.get(room_id)), \
             patch.object(BraveEncounter, "get_for_room", return_value=None):
            self.assertTrue(BraveEncounter._can_preview_roam_to_room(source, allowed, preview))
            self.assertFalse(BraveEncounter._can_preview_roam_to_room(source, safe, preview))
            self.assertFalse(BraveEncounter._can_preview_roam_to_room(source, other_zone, preview))

    def test_advance_roaming_threats_moves_preview_and_sets_respawn_cooldown(self):
        source = DummyRoom("source", zone="Blackfen", x=0, y=0)
        destination = DummyRoom("destination", zone="Blackfen", x=1, y=0)
        source.exits = [DummyExit(destination)]
        destination.exits = [DummyExit(source)]
        source.db.brave_room_threat_preview = {
            "preview_id": "p1",
            "room_id": "source",
            "origin_room_id": "source",
            "zone_key": "blackfen",
            "allowed_zone_keys": ["blackfen"],
            "roam_radius": 3,
            "roaming": True,
            "encounter_key": "bog_pack",
            "encounter_title": "Bog Pack",
            "encounter_intro": "A pack prowls nearby.",
            "encounter_data": {"key": "bog_pack", "title": "Bog Pack", "intro": "A pack prowls nearby.", "enemies": ["fen_wisp"]},
            "enemies": [{"template_key": "fen_wisp", "key": "Fen Wisp", "rank": 1}],
        }
        source.db.brave_room_threat_previews = [dict(source.db.brave_room_threat_preview)]

        with patch.object(BraveEncounter, "_iter_world_rooms", return_value=[source, destination]), \
             patch.object(BraveEncounter, "get_for_room", return_value=None), \
             patch("typeclasses.scripts.random.random", return_value=0.0), \
             patch("typeclasses.scripts.random.choice", side_effect=lambda seq: seq[0]), \
             patch("typeclasses.scripts.time.time", return_value=100.0):
            BraveEncounter.advance_roaming_threats()

        self.assertIsNone(source.db.brave_room_threat_preview)
        self.assertEqual("destination", destination.db.brave_room_threat_preview.get("room_id"))
        self.assertEqual(1, len(destination.db.brave_room_threat_previews))
        self.assertEqual(145.0, source.db.brave_room_threat_ready_at)

    def test_moving_preview_emits_departure_and_arrival_activity(self):
        source = DummyRoom("source", zone="Blackfen", x=0, y=0)
        destination = DummyRoom("destination", zone="Blackfen", x=1, y=0)
        source.exits = [DummyExit(destination)]
        source.exits[0].db = SimpleNamespace(brave_direction="east")
        destination.exits = [DummyExit(source)]
        destination.exits[0].db = SimpleNamespace(brave_direction="west")
        preview = {
            "preview_id": "p1",
            "room_id": "source",
            "origin_room_id": "source",
            "encounter_title": "Bog Pack",
        }

        with patch("typeclasses.scripts._emit_room_activity") as emit_activity:
            BraveEncounter._move_room_threat_preview(source, destination, preview)

        emit_activity.assert_any_call(source, "Bog Pack leaves to the east.")
        emit_activity.assert_any_call(destination, "Bog Pack arrives from the west.")

    def test_moving_preview_refreshes_source_and_destination_views(self):
        source = DummyRoom("source", zone="Blackfen", x=0, y=0)
        destination = DummyRoom("destination", zone="Blackfen", x=1, y=0)
        preview = {
            "preview_id": "p1",
            "room_id": "source",
            "origin_room_id": "source",
            "encounter_title": "Bog Pack",
        }

        with patch("typeclasses.scripts._refresh_room_webclient_views") as refresh_views:
            BraveEncounter._move_room_threat_preview(source, destination, preview)

        refresh_views.assert_any_call(source)
        refresh_views.assert_any_call(destination)

    def test_ensure_roaming_population_seeds_zone_when_empty(self):
        room_a = DummyRoom("a", zone="Blackfen", x=0, y=0)
        room_b = DummyRoom("b", zone="Blackfen", x=1, y=0)
        room_c = DummyRoom("c", zone="Blackfen", x=2, y=0)
        room_d = DummyRoom("d", zone="Blackfen", x=3, y=0)

        with patch.object(BraveEncounter, "_iter_world_rooms", return_value=[room_a, room_b, room_c, room_d]), \
             patch.object(BraveEncounter, "_room_has_encounter_table", return_value=True), \
             patch.object(BraveEncounter, "get_for_room", return_value=None), \
             patch.object(BraveEncounter, "_spawn_room_threat_preview", side_effect=lambda room: room.db.__setattr__("brave_room_threat_preview", {"preview_id": room.db.brave_room_id, "room_id": room.db.brave_room_id}) or room.db.__setattr__("brave_room_threat_previews", [room.db.brave_room_threat_preview]) or room.db.brave_room_threat_preview), \
             patch("typeclasses.scripts.random.shuffle", side_effect=lambda seq: None):
            BraveEncounter.ensure_roaming_threat_population()

        seeded = [room.db.brave_room_threat_preview for room in (room_a, room_b, room_c, room_d) if room.db.brave_room_threat_preview]
        self.assertEqual(2, len(seeded))

    def test_ensure_roaming_population_refreshes_rooms_when_previews_change(self):
        room_a = DummyRoom("a", zone="Blackfen", x=0, y=0)
        room_b = DummyRoom("b", zone="Blackfen", x=1, y=0)
        room_a.db.brave_room_threat_preview = {"preview_id": "keep", "room_id": "a"}
        room_a.db.brave_room_threat_previews = [
            dict(room_a.db.brave_room_threat_preview),
            {"preview_id": "drop", "room_id": "a"},
            {"preview_id": "trim", "room_id": "a"},
        ]

        with patch.object(BraveEncounter, "_iter_world_rooms", return_value=[room_a, room_b]), \
             patch.object(BraveEncounter, "_room_has_encounter_table", return_value=True), \
             patch.object(BraveEncounter, "get_for_room", return_value=None), \
             patch.object(BraveEncounter, "_spawn_room_threat_preview", return_value=None), \
             patch("typeclasses.scripts.random.shuffle", side_effect=lambda seq: None), \
             patch("typeclasses.scripts._refresh_room_webclient_views") as refresh_views:
            BraveEncounter.ensure_roaming_threat_population()

        refresh_views.assert_any_call(room_a)

    def test_move_preview_allows_destination_with_existing_group(self):
        source = DummyRoom("source", zone="Blackfen", x=0, y=0)
        destination = DummyRoom("destination", zone="Blackfen", x=1, y=0)
        preview = {
            "preview_id": "moving",
            "origin_room_id": "source",
            "allowed_zone_keys": ["blackfen"],
            "roam_radius": 3,
            "roaming": True,
        }
        destination.db.brave_room_threat_preview = {"preview_id": "existing", "room_id": "destination"}
        destination.db.brave_room_threat_previews = [dict(destination.db.brave_room_threat_preview)]

        with patch.object(BraveEncounter, "get_for_room", return_value=None), \
             patch("typeclasses.scripts.get_room", return_value=source):
            self.assertTrue(BraveEncounter._can_preview_roam_to_room(source, destination, preview))


if __name__ == "__main__":
    unittest.main()
