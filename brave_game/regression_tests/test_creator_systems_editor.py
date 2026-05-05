import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_systems_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorSystemsEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_creator_systems_editor_requires_authorization(self):
        request = self.factory.get("/creator/systems/")
        request.user = _DummyUser(authenticated=False)

        response = creator_systems_editor(request)

        self.assertEqual(403, response.status_code)

    def test_creator_systems_editor_renders_for_staff(self):
        request = self.factory.get("/creator/systems/")
        request.user = _DummyUser(staff=True)

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
        self.assertIn("Item Builder", body)
        self.assertIn("World Builder", body)
        self.assertIn("Encounter Builder", body)
        self.assertIn("Boss Composer", body)
        self.assertIn("recipe-materials", body)
        self.assertIn("fish-table", body)
        self.assertIn("boss-trigger", body)
        self.assertIn("portal-status", body)
        self.assertIn("stage:'draft'", body)
        self.assertIn("stage:'draft' })", body)
        self.assertIn("Validate Drafts", body)
        self.assertIn("stage:'draft' })", body)
        self.assertIn("payloadSnippet", body)
        self.assertIn("creator_common.js", body)
        self.assertIn("Draft Workflow", body)


if __name__ == "__main__":
    unittest.main()
