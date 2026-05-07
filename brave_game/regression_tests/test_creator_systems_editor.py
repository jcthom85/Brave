import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_systems_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = username
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorSystemsEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        request.session = {}
        return request

    def test_creator_systems_editor_requires_authorization(self):
        request = self._get_request("/creator/systems/")

        response = creator_systems_editor(request)

        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_systems_editor_renders_for_staff(self):
        request = self._get_request("/creator/systems/", user=_DummyUser(staff=True))

        response = creator_systems_editor(request)
        body = response.content.decode("utf-8")

        self.assertEqual(200, response.status_code)
        self.assertIn("Systems Builder", body)
        self.assertIn("Systems Guide", body)
        self.assertIn("Cooking", body)
        self.assertIn("Tinkering", body)
        self.assertIn("Cooking Recipe", body)
        self.assertIn("Tinkering Pattern", body)
        self.assertIn("Fishing Spots", body)
        self.assertIn("Fishing Tackle", body)
        self.assertIn("Boss Gates", body)
        self.assertIn("Forge Upgrade", body)
        self.assertIn("Portal", body)
        self.assertIn("Trophies", body)
        self.assertIn("Structured System Entry", body)
        self.assertIn("Linked Content", body)
        self.assertIn("Copy Payload", body)
        self.assertIn("Send To Builder", body)
        self.assertIn("room-activity", body)
        self.assertIn("boss-exit", body)
        self.assertIn("Item Builder", body)
        self.assertIn("World Builder", body)
        self.assertIn("Encounter Builder", body)
        self.assertIn("Boss Composer", body)
        self.assertIn("recipe-material-list", body)
        self.assertIn("Add Ingredient", body)
        self.assertIn("recipe-materials", body)
        self.assertIn("fish-table-list", body)
        self.assertIn("Add Fish Entry", body)
        self.assertIn("fish-table", body)
        self.assertIn("boss-trigger", body)
        self.assertIn("portal-status", body)
        self.assertIn("materialRowsToObject", body)
        self.assertIn("fishRowsToArray", body)
        self.assertIn("fish-behaviors", body)
        self.assertNotIn("Ingredients / Components JSON", body)
        self.assertNotIn("Fish Table JSON", body)
        self.assertNotIn("<details open><summary>Advanced Source</summary>", body)
        self.assertIn("stage:'draft'", body)
        self.assertIn("stage:'draft' })", body)
        self.assertIn("Validate Drafts", body)
        self.assertIn("stage:'draft' })", body)
        self.assertIn("payloadSnippet", body)
        self.assertIn("creator_common.js", body)
        self.assertIn("Draft Workflow", body)


if __name__ == "__main__":
    unittest.main()
