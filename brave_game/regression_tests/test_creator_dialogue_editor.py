import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_dialogue_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = username
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorDialogueEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        request.session = {}
        return request

    def test_creator_dialogue_editor_requires_authorization(self):
        request = self._get_request("/creator/dialogue/")
        response = creator_dialogue_editor(request)
        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_dialogue_editor_renders_for_staff(self):
        request = self._get_request("/creator/dialogue/", user=_DummyUser(staff=True))
        response = creator_dialogue_editor(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Dialogue Builder", body)
        self.assertIn("Dialogue Guide", body)
        self.assertIn("NPC Greeting", body)
        self.assertIn("Quest Giver", body)
        self.assertIn("Quest Turn-In", body)
        self.assertIn("Location Bark", body)
        self.assertIn("Readable Sign/Note", body)
        self.assertIn("Tutorial Hint", body)
        self.assertIn("Draft Workflow", body)
        self.assertIn("data-creator-workflow-host", body)
        self.assertIn("Add Talk Rule", body)
        self.assertIn("Remove Talk Rule", body)
        self.assertIn("Sync Builder To Source", body)
        self.assertIn("Advanced Source", body)
        self.assertIn("Readable Response", body)
        self.assertIn("Linked Content", body)
        self.assertIn("Open World Builder", body)
        self.assertIn("Open Quest Builder", body)
        self.assertIn("Open Systems Builder", body)
        self.assertIn("Copy Payload", body)
        self.assertIn("Send To Builder", body)
        self.assertIn("quest-talk-objective", body)
        self.assertIn("payloadSnippet", body)
        self.assertIn("stage: 'draft'", body)
        self.assertIn("Save Dialogue", body)
        self.assertIn("Save Readable", body)
        self.assertIn("/api/content", body)


if __name__ == "__main__":
    unittest.main()
