import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_encounter_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = username
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorEncounterEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        request.session = {}
        return request

    def test_creator_encounter_editor_requires_authorization(self):
        request = self._get_request("/creator/encounters/")
        response = creator_encounter_editor(request)
        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_encounter_editor_renders_for_staff(self):
        request = self._get_request("/creator/encounters/", user=_DummyUser(staff=True))
        response = creator_encounter_editor(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Encounter Builder", body)
        self.assertIn("combat summary risk buckets", body)
        self.assertIn("Encounter Guide", body)
        self.assertIn("Room Fight", body)
        self.assertIn("Quest Combat", body)
        self.assertIn("Boss Setup", body)
        self.assertIn("Loot Drop Enemy", body)
        self.assertIn("Roaming Patrol", body)
        self.assertIn("Room Encounter List", body)
        self.assertIn("Open World Builder", body)
        self.assertIn("Open Item Builder", body)
        self.assertIn("Open Quest Builder", body)
        self.assertIn("Open Systems Builder", body)
        self.assertIn("Open Boss Composer", body)
        self.assertIn("encounter-link-grid", body)
        self.assertIn("enemy-link-grid", body)
        self.assertIn("party-link-grid", body)
        self.assertIn("Copy Link Payload", body)
        self.assertIn("Send To Builder", body)
        self.assertIn("applyEncounterIncoming", body)
        self.assertIn("registerApplyHandler('enemy-loot'", body)
        self.assertIn("payloadSnippet", body)
        self.assertIn("applyEncounterPreset", body)
        self.assertIn("Add Encounter", body)
        self.assertIn("Remove Encounter", body)
        self.assertIn("New Enemy", body)
        self.assertIn("Roaming Parties", body)
        self.assertIn("stage:'draft'", body)
        self.assertIn("allowErrorPayload", body)
        self.assertIn("Advanced Source", body)
        self.assertIn("Save Room Encounters", body)
        self.assertIn("Save Enemy", body)
        self.assertIn("/api/content", body)


if __name__ == "__main__":
    unittest.main()
