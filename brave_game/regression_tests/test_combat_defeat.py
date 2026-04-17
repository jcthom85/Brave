import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter


class DummyRoom:
    def __init__(self, key):
        self.key = key


class DummyCharacter:
    def __init__(self):
        self.id = 7
        self.key = "Dad"
        self.location = DummyRoom("Brush Line")
        self.ndb = SimpleNamespace()
        self.db = SimpleNamespace()
        self.messages = []
        self.move_calls = []

    def clear_chapel_blessing(self):
        return None

    def restore_resources(self):
        return None

    def move_to(self, destination, quiet=True, move_type=None):
        self.move_calls.append((destination, quiet, move_type))
        self.location = destination
        return True

    def msg(self, text):
        self.messages.append(text)

    def at_look(self, location):
        return f"LOOK {location.key}"


class CombatDefeatTests(unittest.TestCase):
    @patch("world.browser_panels.send_webclient_event")
    @patch("typeclasses.scripts.delay")
    @patch("typeclasses.scripts.get_tutorial_defeat_room", return_value=None)
    @patch("typeclasses.scripts.get_room")
    def test_defeat_clears_combat_ui_before_recovery_text(
        self,
        get_room,
        _get_tutorial_defeat_room,
        delay_mock,
        send_webclient_event,
    ):
        destination = DummyRoom("Brambleford")
        get_room.return_value = destination
        character = DummyCharacter()
        encounter = SimpleNamespace(
            _emit_defeat_fx=Mock(),
            _mark_defeated_participant=Mock(),
            remove_participant=Mock(),
            _refresh_browser_combat_views=Mock(),
        )

        BraveEncounter._defeat_character(encounter, character)

        encounter.remove_participant.assert_called_once_with(character, refresh=False)
        self.assertEqual([(destination, True, "defeat")], character.move_calls)
        send_webclient_event.assert_called_once_with(character, brave_combat_done={})
        self.assertEqual("LOOK Brambleford", character.messages[0])
        self.assertTrue(any("carried back to Brambleford to recover" in message for message in character.messages))
        delay_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
