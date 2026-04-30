import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter


class DummyRoom:
    def __init__(self, key, *, rest_allowed=False):
        self.key = key
        self.db = SimpleNamespace(brave_safe=True, brave_rest_allowed=rest_allowed, brave_room_id="")


class DummyCharacter:
    def __init__(self):
        self.id = 7
        self.key = "Dad"
        self.location = DummyRoom("Brush Line")
        self.ndb = SimpleNamespace()
        self.db = SimpleNamespace(brave_silver=12, brave_resources={})
        self.messages = []
        self.move_calls = []

    def clear_chapel_blessing(self):
        return None

    def restore_resources(self):
        self.db.brave_resources = {"hp": 30, "mana": 20, "stamina": 25}

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
        destination = DummyRoom("Brambleford", rest_allowed=True)
        get_room.return_value = destination
        character = DummyCharacter()
        encounter = SimpleNamespace(
            _emit_defeat_fx=Mock(),
            _mark_defeated_participant=Mock(),
            _mark_defeat_consequence=lambda _character: BraveEncounter._mark_defeat_consequence(encounter, _character),
            _set_defeat_resources=lambda _character: BraveEncounter._set_defeat_resources(encounter, _character),
            remove_participant=Mock(),
            _refresh_browser_combat_views=Mock(),
        )

        BraveEncounter._defeat_character(encounter, character)

        encounter.remove_participant.assert_called_once_with(character, refresh=False)
        self.assertEqual([(destination, True, "defeat")], character.move_calls)
        self.assertEqual(2, send_webclient_event.call_count)
        send_webclient_event.assert_any_call(character, brave_combat_done={})
        defeat_view = send_webclient_event.call_args_list[-1].kwargs["brave_view"]
        self.assertEqual("DEFEATED", defeat_view["title"])
        self.assertEqual("combat-result", defeat_view["variant"])
        self.assertEqual("defeat", defeat_view["reactive"]["scene"])
        self.assertEqual("5", defeat_view["sections"][0]["items"][3]["value"])
        self.assertEqual("rest", defeat_view["actions"][0]["command"])
        self.assertEqual("look", defeat_view["actions"][-1]["command"])
        self.assertEqual("LOOK Brambleford", character.messages[0])
        self.assertTrue(any("carried back to Brambleford, barely standing" in message for message in character.messages))
        self.assertEqual(7, character.db.brave_silver)
        self.assertEqual({"hp": 1, "mana": 1, "stamina": 1}, character.db.brave_resources)
        delay_mock.assert_called_once()

    @patch("world.browser_panels.send_webclient_event")
    @patch("typeclasses.scripts.delay")
    @patch("typeclasses.scripts.get_tutorial_defeat_room")
    @patch("typeclasses.scripts.get_room")
    def test_tutorial_defeat_does_not_charge_silver(
        self,
        get_room,
        get_tutorial_defeat_room,
        _delay_mock,
        _send_webclient_event,
    ):
        destination = DummyRoom("Wayfarer's Yard")
        get_tutorial_defeat_room.return_value = destination
        get_room.return_value = DummyRoom("Brambleford")
        character = DummyCharacter()
        encounter = SimpleNamespace(
            _emit_defeat_fx=Mock(),
            _mark_defeated_participant=Mock(),
            _mark_defeat_consequence=lambda _character: BraveEncounter._mark_defeat_consequence(encounter, _character),
            _set_defeat_resources=lambda _character: BraveEncounter._set_defeat_resources(encounter, _character),
            remove_participant=Mock(),
            _refresh_browser_combat_views=Mock(),
        )

        BraveEncounter._defeat_character(encounter, character)

        self.assertEqual([(destination, True, "defeat")], character.move_calls)
        self.assertEqual(12, character.db.brave_silver)
        self.assertEqual({"hp": 1, "mana": 1, "stamina": 1}, character.db.brave_resources)
        defeat_view = _send_webclient_event.call_args_list[-1].kwargs["brave_view"]
        self.assertEqual("DEFEATED", defeat_view["title"])
        self.assertEqual("0", defeat_view["sections"][0]["items"][3]["value"])

    def test_defeat_silver_loss_is_capped_by_carried_silver(self):
        character = DummyCharacter()
        character.db.brave_silver = 3

        lost = BraveEncounter._mark_defeat_consequence(SimpleNamespace(), character)

        self.assertEqual(3, lost)
        self.assertEqual(0, character.db.brave_silver)

    def test_defeat_resources_leave_character_barely_standing(self):
        character = DummyCharacter()
        character.restore_resources()

        BraveEncounter._set_defeat_resources(SimpleNamespace(), character)

        self.assertEqual({"hp": 1, "mana": 1, "stamina": 1}, character.db.brave_resources)

    @patch("world.browser_panels.send_browser_notice_event")
    def test_party_defeat_sends_explicit_wipe_notice(self, send_browser_notice_event):
        character = DummyCharacter()
        msg_contents = Mock()
        stop = Mock()
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=msg_contents),
            get_defeated_participants=lambda: [character],
            stop=stop,
        )

        BraveEncounter._finish_party_defeat(encounter, "|rThe party is driven back toward town.|n")

        msg_contents.assert_called_once_with("|rThe party is driven back toward town.|n")
        send_browser_notice_event.assert_called_once()
        self.assertEqual(character, send_browser_notice_event.call_args.args[0])
        self.assertEqual("Party Defeated", send_browser_notice_event.call_args.kwargs["title"])
        stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
