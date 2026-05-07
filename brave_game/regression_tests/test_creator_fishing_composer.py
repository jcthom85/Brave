import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_fishing_composer


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = False
        self.username = username

    def check_permstring(self, permstring):
        return False


class CreatorFishingComposerViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        request.session = {}
        return request

    def test_creator_fishing_composer_requires_authorization(self):
        request = self._get_request("/creator/composers/fishing/")
        response = creator_fishing_composer(request)
        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_fishing_composer_renders_guided_flow_for_staff(self):
        request = self._get_request("/creator/composers/fishing/", user=_DummyUser(staff=True))
        response = creator_fishing_composer(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Fishing Composer", body)
        self.assertIn("Compose Fishing Flow", body)
        self.assertIn("Write Draft Fishing Flow", body)
        self.assertIn("Catch Preview", body)
        self.assertIn("fishing-spot", body)
        self.assertIn("stage:'draft'", body)
        self.assertIn("sendToBuilder", body)
        self.assertIn("room-activity", body)
        self.assertIn("creator_common.js", body)


if __name__ == "__main__":
    unittest.main()
