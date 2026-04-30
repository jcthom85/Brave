import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import _get_puppet_session


class _Sessions:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def all(self):
        return list(self._sessions)


class CharacterPuppetSessionTests(unittest.TestCase):
    def test_prefers_evennia_puppet_session_kwarg(self):
        kwarg_session = SimpleNamespace(protocol_key="websocket")
        stale_session = SimpleNamespace(protocol_key="telnet")
        character = SimpleNamespace(sessions=_Sessions([stale_session]))

        self.assertIs(_get_puppet_session(character, {"session": kwarg_session}), kwarg_session)

    def test_falls_back_to_character_sessions(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        character = SimpleNamespace(sessions=_Sessions([web_session]))

        self.assertIs(_get_puppet_session(character, {}), web_session)


if __name__ == "__main__":
    unittest.main()
