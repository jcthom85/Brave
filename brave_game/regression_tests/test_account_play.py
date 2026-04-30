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
chargen_stub.clear_chargen_state = lambda *args, **kwargs: None
chargen_stub.get_chargen_state = lambda *args, **kwargs: {}
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
chargen_stub.start_brave_chargen = lambda *args, **kwargs: None
sys.modules.setdefault("world.chargen", chargen_stub)
evmenu_stub = types.ModuleType("evennia.utils.evmenu")
evmenu_stub.get_input = lambda *args, **kwargs: None
sys.modules.setdefault("evennia.utils.evmenu", evmenu_stub)

from commands.account import CmdBravePlay, _release_existing_puppets_for_play
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


class AccountPlayTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
