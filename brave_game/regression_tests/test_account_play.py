import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = sys.modules.setdefault("world.chargen", types.ModuleType("world.chargen"))
chargen_stub.clear_chargen_state = lambda *args, **kwargs: None
chargen_stub.get_chargen_state = lambda *args, **kwargs: {}
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
chargen_stub.start_brave_chargen = lambda *args, **kwargs: None
evmenu_stub = types.ModuleType("evennia.utils.evmenu")
evmenu_stub.get_input = lambda *args, **kwargs: None
sys.modules.setdefault("evennia.utils.evmenu", evmenu_stub)

from commands.account import (
    CmdBraveLogout,
    CmdBravePlay,
    _refresh_web_session_after_play,
    _release_existing_puppets_for_play,
)
from evennia.commands.default import account as default_account


class _Characters:
    def __init__(self, characters):
        self._characters = list(characters)

    def all(self):
        return list(self._characters)


class _Account:
    def __init__(self, characters, puppets=None):
        self.characters = _Characters(characters)
        self.db = SimpleNamespace(_last_puppet=None)
        self._puppets = list(puppets or [])
        self.unpuppet_count = 0

    def get_all_puppets(self):
        return list(self._puppets)

    def unpuppet_all(self):
        self.unpuppet_count += 1
        self._puppets = []


class _SessionHandler:
    def __init__(self):
        self.partial_syncs = []

    def session_portal_partial_sync(self, payload):
        self.partial_syncs.append(payload)


class _Cmdset:
    def __init__(self):
        self.update_calls = []

    def update(self, **kwargs):
        self.update_calls.append(kwargs)


class AccountPlayTests(unittest.TestCase):
    def test_web_logout_clears_evennia_and_browser_login_state(self):
        messages = []
        session_handler = _SessionHandler()
        session = SimpleNamespace(
            protocol_key="websocket",
            account=SimpleNamespace(key="Tester"),
            uid=7,
            uname="Tester",
            puid=14,
            puppet=SimpleNamespace(key="Hero"),
            logged_in=True,
            cmdset_storage="old",
            cmdset=_Cmdset(),
            sessid=99,
            sessionhandler=session_handler,
        )
        session.msg = lambda **kwargs: messages.append(kwargs)
        command = object.__new__(CmdBraveLogout)
        command.session = session
        command.account = session.account

        command.func()

        self.assertIsNone(session.account)
        self.assertIsNone(session.uid)
        self.assertEqual("", session.uname)
        self.assertIsNone(session.puid)
        self.assertIsNone(session.puppet)
        self.assertFalse(session.logged_in)
        self.assertEqual([{"init_mode": True}], session.cmdset.update_calls)
        self.assertEqual([{99: {"logged_in": False, "uid": None}}], session_handler.partial_syncs)
        logout_events = [message.get("brave_logout") for message in messages if message.get("brave_logout")]
        self.assertEqual("menu", logout_events[-1].get("screen"))
        signin_views = [
            message.get("brave_view")
            for message in messages
            if message.get("brave_view", {}).get("variant") == "connection"
        ]
        self.assertEqual(["Enter Brave"], [section.get("label") for section in signin_views[-1].get("sections", [])])

    def test_release_existing_puppets_unpuppets_different_character(self):
        old_character = SimpleNamespace(key="Old")
        new_character = SimpleNamespace(key="New")
        account = _Account([old_character, new_character], puppets=[old_character])
        session = SimpleNamespace(puppet=old_character)

        _release_existing_puppets_for_play(account, session, new_character)

        self.assertEqual(1, account.unpuppet_count)

    def test_play_command_releases_existing_puppet_before_delegating_to_evennia(self):
        old_character = SimpleNamespace(key="Old")
        new_character = SimpleNamespace(key="New")
        account = _Account([old_character, new_character], puppets=[old_character])
        session = SimpleNamespace(puppet=old_character)
        command = object.__new__(CmdBravePlay)
        command.account = account
        command.session = session
        command.args = "New"
        command.msg = lambda *_args, **_kwargs: None

        calls = []

        def _record_super(cmd):
            calls.append(("super", cmd.args, account.unpuppet_count))

        with patch.object(default_account.CmdIC, "func", _record_super):
            command.func()

        self.assertEqual([("super", "New", 1)], calls)

    def test_play_command_refreshes_web_room_after_puppet(self):
        calls = []
        location = SimpleNamespace(return_appearance=lambda character: calls.append(("look", character.key)))
        character = SimpleNamespace(key="New", location=location, ndb=SimpleNamespace())
        account = _Account([character])
        session = SimpleNamespace(protocol_key="websocket", puppet=None)
        command = object.__new__(CmdBravePlay)
        command.account = account
        command.session = session
        command.args = "New"
        command.msg = lambda *_args, **_kwargs: None

        def _record_super(cmd):
            session.puppet = character
            calls.append(("super", cmd.args))

        with patch.object(default_account.CmdIC, "func", _record_super):
            command.func()

        # We no longer expect an explicit 'look' call from CmdBravePlay.func,
        # as it is handled by the at_post_puppet hook within the super().func() call chain.
        self.assertEqual([("super", "New")], calls)

    def test_refresh_web_session_after_play_ignores_stale_puppet(self):
        calls = []
        character = SimpleNamespace(
            key="New",
            location=SimpleNamespace(return_appearance=lambda _character: calls.append("look")),
            ndb=SimpleNamespace(),
        )
        session = SimpleNamespace(protocol_key="websocket", puppet=SimpleNamespace(key="Old"))

        _refresh_web_session_after_play(session, character)

        self.assertEqual([], calls)

    def test_refresh_web_session_after_play_skips_view_already_sent_by_puppet_hook(self):
        calls = []
        character = SimpleNamespace(
            key="New",
            location=SimpleNamespace(return_appearance=lambda _character: calls.append("look")),
            ndb=SimpleNamespace(brave_post_puppet_room_view_sent=True),
        )
        session = SimpleNamespace(protocol_key="websocket", puppet=character)

        _refresh_web_session_after_play(session, character)

        self.assertEqual([], calls)


if __name__ == "__main__":
    unittest.main()
