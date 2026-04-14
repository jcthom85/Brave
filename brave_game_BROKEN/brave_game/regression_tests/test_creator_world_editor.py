import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_world_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorWorldEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_creator_world_editor_requires_authorization(self):
        request = self.factory.get("/creator/world/")
        request.user = _DummyUser(authenticated=False)

        response = creator_world_editor(request)

        self.assertEqual(403, response.status_code)

    def test_creator_world_editor_rejects_authenticated_non_creator_user(self):
        request = self.factory.get("/creator/world/")
        request.user = _DummyUser(authenticated=True)

        response = creator_world_editor(request)

        self.assertEqual(403, response.status_code)

    def test_creator_world_editor_renders_for_staff(self):
        request = self.factory.get("/creator/world/")
        request.user = _DummyUser(staff=True)

        response = creator_world_editor(request)
        body = response.content.decode("utf-8")

        self.assertEqual(200, response.status_code)
        self.assertIn("World Graph", body)
        self.assertIn("/api/content", body)
        self.assertIn("Write Room", body)
        self.assertIn("Write Exit", body)
        self.assertIn("Write Entity", body)
        self.assertIn("New Exit Draft", body)
        self.assertIn("New Entity Draft", body)
        self.assertIn("Destination Room", body)
        self.assertIn("Entity Kind", body)
        self.assertIn("Sync Exit Form To JSON", body)
        self.assertIn("validation-notes", body)
        self.assertIn("creator_common.js", body)
        self.assertIn("Sync Entity Form To JSON", body)


if __name__ == "__main__":
    unittest.main()
