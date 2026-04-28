import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_index


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorIndexViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_creator_index_requires_authorization(self):
        request = self.factory.get("/creator/")
        request.user = _DummyUser(authenticated=False)
        response = creator_index(request)
        self.assertEqual(403, response.status_code)

    def test_creator_index_rejects_authenticated_non_creator_user(self):
        request = self.factory.get("/creator/")
        request.user = _DummyUser(authenticated=True)
        response = creator_index(request)
        self.assertEqual(403, response.status_code)

    def test_creator_index_renders_links_for_staff(self):
        request = self.factory.get("/creator/")
        request.user = _DummyUser(staff=True)
        response = creator_index(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Brave Creator", body)
        self.assertIn("builder tooling", body)
        self.assertIn("/creator/world/", body)
        self.assertIn("staff, superuser, or Developer-authorized account", body)
        self.assertIn("/creator/items/", body)
        self.assertIn("/creator/characters/", body)
        self.assertIn("Open Character Builder", body)


if __name__ == "__main__":
    unittest.main()
