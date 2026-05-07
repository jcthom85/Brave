import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_index


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = username
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorIndexViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        # Mock session to satisfy Evennia's general_context processor
        request.session = {}
        return request

    def test_creator_index_requires_authorization(self):
        request = self._get_request("/creator/")
        response = creator_index(request)
        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_index_rejects_authenticated_non_creator_user(self):
        request = self._get_request("/creator/", user=_DummyUser(authenticated=True))
        response = creator_index(request)
        self.assertEqual(403, response.status_code)
        self.assertIn("Access Denied", response.content.decode("utf-8"))

    def test_creator_index_renders_links_for_staff(self):
        request = self._get_request("/creator/", user=_DummyUser(staff=True))
        response = creator_index(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Brave Creator Mission Control", body)
        self.assertIn("Composers", body)
        self.assertIn("/creator/world/", body)
        self.assertIn("staff, superuser, or Developer-authorized account", body)
        self.assertIn("/creator/items/", body)
        self.assertIn("/creator/characters/", body)
        self.assertIn("Open Character Builder", body)
        self.assertIn("/creator/systems/", body)
        self.assertIn("Open Systems Builder", body)
        self.assertIn("/creator/composers/boss/", body)
        self.assertIn("Open Boss Composer", body)
        self.assertIn("/creator/composers/recipe/", body)
        self.assertIn("Open Recipe Composer", body)
        self.assertIn("/creator/composers/fishing/", body)
        self.assertIn("Open Fishing Composer", body)
        self.assertNotIn("Quest Chain", body)
        self.assertNotIn("Tutorial Moment", body)
        self.assertNotIn("New Zone", body)
        self.assertIn("Creator Health", body)
        self.assertIn("data-creator-agent-runs-host", body)
        self.assertIn("creator_common.js", body)


if __name__ == "__main__":
    unittest.main()
