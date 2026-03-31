import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter


class DummyRoom:
    def __init__(self, key):
        self.key = key


class DummyCharacter:
    def __init__(self, destination):
        self.id = 7
        self.key = "Dad"
        self.location = DummyRoom("Brush Line")
        self.ndb = SimpleNamespace(brave_previous_location=destination)
        self.db = SimpleNamespace(brave_resources={}, brave_derived_stats={})
        self.messages = []
        self.move_calls = []

    def move_to(self, destination, quiet=True, move_type=None):
        self.move_calls.append((destination, quiet, move_type))
        self.location = destination
        return True

    def msg(self, text):
        self.messages.append(text)

    def at_look(self, location):
        return f"LOOK {location.key}"


class DummyEncounter:
    def __init__(self, destination=None):
        self.db = SimpleNamespace(pending_actions={}, round=0)
        self.obj_messages = []
        self.obj = SimpleNamespace(msg_contents=self.obj_messages.append)
        self.destination = destination
        self.refreshed = 0
        self.removed = []
        self.threat_added = []

    def _refresh_browser_combat_views(self):
        self.refreshed += 1

    def _get_flee_destination(self, _character):
        return self.destination

    def _get_flee_chance(self, _character):
        return 100

    def remove_participant(self, character):
        self.removed.append(character.id)

    def _add_threat(self, character, amount):
        self.threat_added.append((character.id, amount))


class CombatFleeTests(unittest.TestCase):
    def test_queue_flee_requires_known_destination(self):
        encounter = DummyEncounter(destination=None)
        character = DummyCharacter(destination=None)

        ok, message = BraveEncounter.queue_flee(encounter, character)

        self.assertFalse(ok)
        self.assertIn("clear route", message.lower())
        self.assertEqual({}, encounter.db.pending_actions)

    def test_queue_flee_records_pending_action(self):
        destination = DummyRoom("Old Stone Path")
        encounter = DummyEncounter(destination=destination)
        character = DummyCharacter(destination=destination)

        ok, message = BraveEncounter.queue_flee(encounter, character)

        self.assertTrue(ok)
        self.assertIn("Old Stone Path", message)
        self.assertEqual(
            {"kind": "flee", "destination_name": "Old Stone Path"},
            encounter.db.pending_actions[str(character.id)],
        )
        self.assertEqual(1, encounter.refreshed)

    def test_execute_flee_moves_character_and_removes_participant(self):
        destination = DummyRoom("Old Stone Path")
        encounter = DummyEncounter(destination=destination)
        character = DummyCharacter(destination=destination)

        with patch("typeclasses.scripts.random.randint", return_value=1):
            BraveEncounter._execute_flee(encounter, character)

        self.assertEqual([(destination, True, "flee")], character.move_calls)
        self.assertEqual([character.id], encounter.removed)
        self.assertTrue(any("falls back to Old Stone Path" in message for message in encounter.obj_messages))
        self.assertTrue(any("break away from the fight" in message for message in character.messages))
        self.assertIn("LOOK Old Stone Path", character.messages)
