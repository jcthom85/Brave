import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.brave import BraveCharacterCommand


class _DummySessions:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def get(self):
        return list(self._sessions)


class BraveCharacterCommandTests(unittest.TestCase):
    def test_send_room_emote_uses_gendered_head_phrase(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        character = SimpleNamespace(key="Jackson", location=room, db=SimpleNamespace(brave_gender="male"))
        character.ensure_brave_character = lambda: character
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        recorded = []
        from world import browser_panels
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None: recorded.append((location, line, exclude, cls))
        try:
            ok = command.send_room_emote("shake head")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertEqual("Jackson shakes his head.", recorded[0][1])
        self.assertEqual(("You shake your head.",), sent[0]["args"])

    def test_send_room_emote_uses_their_for_nonbinary_character(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        character = SimpleNamespace(key="Ash", location=room, db=SimpleNamespace(brave_gender="nonbinary"))
        character.ensure_brave_character = lambda: character
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        from world import browser_panels
        recorded = []
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None: recorded.append((location, line, exclude, cls))
        try:
            ok = command.send_room_emote("shrug")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertEqual("Ash shrugs their shoulders.", recorded[0][1])
        self.assertEqual(("You shrug.",), sent[0]["args"])

    def test_send_room_emote_targets_present_npc(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        npc = SimpleNamespace(
            key="Uncle Pib Underbough",
            db=SimpleNamespace(brave_entity_kind="npc", brave_entity_id="uncle_pib_underbough"),
        )
        character = SimpleNamespace(key="Ash", location=room, db=SimpleNamespace(brave_gender="nonbinary"))
        character.ensure_brave_character = lambda: character
        character.location = SimpleNamespace(contents=[character, npc])
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        from world import browser_panels

        recorded = []
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None, category=None: recorded.append((location, line, exclude, cls, category))
        try:
            ok = command.send_room_emote("smiles at Uncle Pib Underbough")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertTrue(any("Ash smiles at Uncle Pib Underbough." == line for _location, line, _exclude, _cls, _category in recorded))
        self.assertEqual(("You smile at Uncle Pib Underbough.",), sent[0]["args"])

    def test_send_room_emote_can_target_enemy_in_combat(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        enemy = {"id": "e1", "key": "Bandit Raider", "template_key": "bandit_raider", "hp": 12, "max_hp": 12}
        encounter = SimpleNamespace(
            is_participant=lambda _character: True,
            get_active_enemies=lambda: [enemy],
            react_to_emote=lambda _character, _enemy, _text: "The bandit raider spits back a dirty glare.",
        )
        character = SimpleNamespace(key="Ash", location=room, db=SimpleNamespace(brave_gender="nonbinary"))
        character.ensure_brave_character = lambda: character
        character.get_active_encounter = lambda: encounter
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        from world import browser_panels

        recorded = []
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None, category=None: recorded.append((location, line, exclude, cls, category))
        try:
            ok = command.send_room_emote("taunts the Bandit Raider")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertTrue(any("The bandit raider spits back a dirty glare." == line for _location, line, _exclude, _cls, _category in recorded))
        self.assertTrue(any("Ash taunts the Bandit Raider." == line for _location, line, _exclude, _cls, _category in recorded))
        self.assertEqual(("You taunt the Bandit Raider.",), sent[0]["args"])

    def test_scene_msg_skips_browser_clear_when_view_is_present(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        other_session = SimpleNamespace(protocol_key="telnet")
        command = object.__new__(BraveCharacterCommand)
        command.session = web_session
        command.caller = SimpleNamespace(sessions=_DummySessions([web_session, other_session]))

        sent = []

        def _record(*args, **kwargs):
            sent.append({"args": args, "kwargs": kwargs})

        command.msg = _record

        view = {"variant": "combat", "sticky": True}
        command.scene_msg("snapshot", view=view)

        self.assertFalse(any("brave_clear" in event["kwargs"] for event in sent))
        self.assertEqual(
            [event["kwargs"].get("brave_view") for event in sent if "brave_view" in event["kwargs"]],
            [view],
        )
        self.assertEqual(
            [event["kwargs"].get("session") for event in sent if event["args"] == ("snapshot",)],
            [[other_session]],
        )
