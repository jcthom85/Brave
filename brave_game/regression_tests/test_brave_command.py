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
