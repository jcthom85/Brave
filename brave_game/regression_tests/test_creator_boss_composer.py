import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_boss_composer


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = username
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorBossComposerViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        request.session = {}
        return request

    def test_creator_boss_composer_requires_authorization(self):
        request = self._get_request("/creator/composers/boss/")

        response = creator_boss_composer(request)

        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_boss_composer_renders_guided_flow_for_staff(self):
        request = self._get_request("/creator/composers/boss/", user=_DummyUser(staff=True))

        response = creator_boss_composer(request)
        body = response.content.decode("utf-8")

        self.assertEqual(200, response.status_code)
        self.assertIn("Boss Composer", body)
        self.assertIn("Compose The Flow", body)
        self.assertIn("Gate Exit Command", body)
        self.assertIn("Write Draft Boss Flow", body)
        self.assertIn("Send Exit To World Builder", body)
        self.assertIn("/creator/world/", body)
        self.assertIn("/creator/encounters/", body)
        self.assertIn("/creator/systems/", body)
        self.assertIn("kind: 'exit'", body)
        self.assertIn("kind: 'boss-gate'", body)
        self.assertIn("stage:'draft'", body)
        self.assertIn("boss-exit", body)
        self.assertIn("creator_common.js", body)


if __name__ == "__main__":
    unittest.main()
