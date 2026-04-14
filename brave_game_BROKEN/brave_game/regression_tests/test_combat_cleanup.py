import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter


class CombatCleanupTests(unittest.TestCase):
    @patch("world.browser_panels.send_webclient_event")
    def test_prune_inactive_room_encounters_deletes_leaks_and_clears_client_state(self, send_webclient_event):
        participant = SimpleNamespace(ndb=SimpleNamespace(brave_encounter="stale"))
        inactive = SimpleNamespace(
            is_active=False,
            get_participants=lambda: [participant],
            delete=Mock(),
        )
        active = SimpleNamespace(is_active=True)
        room = SimpleNamespace(scripts=SimpleNamespace(get=lambda _key: [inactive, active]))

        matches = BraveEncounter._prune_inactive_room_encounters(room)

        self.assertEqual([active], matches)
        self.assertIsNone(participant.ndb.brave_encounter)
        inactive.delete.assert_called_once_with()
        send_webclient_event.assert_called_once_with(participant, brave_combat_done={})

    def test_get_for_room_prunes_inactive_rows_before_returning_none(self):
        cached = SimpleNamespace(id=7, is_active=False)
        room = SimpleNamespace(ndb=SimpleNamespace(brave_encounter=cached))

        with patch.object(BraveEncounter, "_prune_inactive_room_encounters", return_value=[]) as prune:
            encounter = BraveEncounter.get_for_room(room)

        self.assertIsNone(encounter)
        self.assertIsNone(room.ndb.brave_encounter)
        prune.assert_called_once_with(room)
