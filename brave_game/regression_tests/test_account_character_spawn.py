import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.spawning import ensure_newbie_area_on_puppet, place_new_brave_character


class DummyCharacter:
    def __init__(self, location):
        self.location = location
        self.home = None
        self.moves = []
        self.db = SimpleNamespace(
            brave_quests={},
            brave_harl_cellar_job_assigned=True,
            brave_opening_sequence_active=False,
            brave_tracked_quest="rats_in_the_kettle",
            brave_track_suppressed=False,
            brave_tutorial=None,
            brave_tutorial_current_step=None,
            brave_level=1,
            brave_xp=0,
        )

    def move_to(self, destination, quiet=True, move_type=None):
        self.moves.append((destination, quiet, move_type))
        self.location = destination
        return True


class AccountCharacterSpawnTests(unittest.TestCase):
    def test_first_character_spawns_in_tutorial_instead_of_limbo(self):
        account = SimpleNamespace(db=SimpleNamespace(brave_tutorial_completed=False))
        limbo = SimpleNamespace(key="Limbo")
        tutorial_room = SimpleNamespace(key="Wayfarer's Yard")
        character = DummyCharacter(limbo)
        calls = []

        with patch("world.spawning.ensure_brave_world", lambda: calls.append("world")), patch(
            "world.spawning.should_start_tutorial", return_value=True
        ), patch("world.spawning.begin_tutorial", lambda char: calls.append(("tutorial", char))), patch(
            "world.spawning.get_tutorial_start_room", return_value=tutorial_room
        ):
            start_room = place_new_brave_character(account, character)

        self.assertEqual(tutorial_room, start_room)
        self.assertEqual(tutorial_room, character.location)
        self.assertEqual(tutorial_room, character.home)
        self.assertEqual([(tutorial_room, True, "spawn")], character.moves)
        self.assertEqual("world", calls[0])
        self.assertEqual(("tutorial", character), calls[1])

    def test_later_character_still_spawns_in_tutorial(self):
        account = SimpleNamespace(db=SimpleNamespace(brave_tutorial_completed=True))
        limbo = SimpleNamespace(key="Limbo")
        tutorial_room = SimpleNamespace(key="Wayfarer's Yard")
        character = DummyCharacter(limbo)

        with patch("world.spawning.ensure_brave_world", lambda: None), patch(
            "world.spawning.get_tutorial_start_room", return_value=tutorial_room
        ), patch("world.spawning.begin_tutorial", lambda char: setattr(char.db, "brave_tutorial", {"status": "active", "step": "first_steps", "flags": {}})):
            start_room = place_new_brave_character(account, character)

        self.assertEqual(tutorial_room, start_room)
        self.assertEqual(tutorial_room, character.location)
        self.assertEqual(tutorial_room, character.home)
        self.assertEqual([(tutorial_room, True, "spawn")], character.moves)
        self.assertFalse(character.db.brave_harl_cellar_job_assigned)
        self.assertEqual("practice_makes_heroes", character.db.brave_tracked_quest)
        self.assertEqual("active", character.db.brave_quests["practice_makes_heroes"]["status"])
        self.assertNotIn("rats_in_the_kettle", character.db.brave_quests)

    def test_unstarted_existing_character_in_training_yard_repairs_to_tutorial(self):
        account = SimpleNamespace(db=SimpleNamespace(brave_tutorial_completed=True))
        training_yard = SimpleNamespace(key="Training Yard", db=SimpleNamespace(brave_room_id="brambleford_training_yard"))
        tutorial_room = SimpleNamespace(key="Wayfarer's Yard", db=SimpleNamespace(brave_room_id="tutorial_wayfarers_yard"))
        character = DummyCharacter(training_yard)
        character.db.brave_harl_cellar_job_assigned = False

        with patch("world.spawning.ensure_brave_world", lambda: None), patch(
            "world.spawning.get_tutorial_start_room", return_value=tutorial_room
        ):
            repaired = ensure_newbie_area_on_puppet(account, character)

        self.assertTrue(repaired)
        self.assertEqual(tutorial_room, character.location)
        self.assertEqual(tutorial_room, character.home)
        self.assertEqual("active", character.db.brave_tutorial["status"])

    def test_completed_tutorial_character_stays_where_they_are(self):
        account = SimpleNamespace(db=SimpleNamespace(brave_tutorial_completed=True))
        training_yard = SimpleNamespace(key="Training Yard", db=SimpleNamespace(brave_room_id="brambleford_training_yard"))
        tutorial_room = SimpleNamespace(key="Wayfarer's Yard", db=SimpleNamespace(brave_room_id="tutorial_wayfarers_yard"))
        character = DummyCharacter(training_yard)
        character.db.brave_tutorial = {"status": "completed", "step": None, "flags": {}}

        with patch("world.spawning.ensure_brave_world", lambda: None), patch(
            "world.spawning.get_tutorial_start_room", return_value=tutorial_room
        ):
            repaired = ensure_newbie_area_on_puppet(account, character)

        self.assertFalse(repaired)
        self.assertEqual(training_yard, character.location)


if __name__ == "__main__":
    unittest.main()
