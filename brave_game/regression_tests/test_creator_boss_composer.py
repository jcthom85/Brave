import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_boss_composer


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorBossComposerViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_creator_boss_composer_requires_authorization(self):
        request = self.factory.get("/creator/composers/boss/")
        request.user = _DummyUser(authenticated=False)

        response = creator_boss_composer(request)

        self.assertEqual(403, response.status_code)

    def test_creator_boss_composer_renders_guided_flow_for_staff(self):
        request = self.factory.get("/creator/composers/boss/")
        request.user = _DummyUser(staff=True)

        response = creator_boss_composer(request)
        body = response.content.decode("utf-8")

        self.assertEqual(200, response.status_code)
        self.assertIn("Boss Composer", body)
        self.assertIn("Compose The Flow", body)
        self.assertIn("Gate Exit Command", body)
        self.assertIn("Write Draft Boss Flow", body)
        self.assertIn("/creator/world/", body)
        self.assertIn("/creator/encounters/", body)
        self.assertIn("/creator/systems/", body)
        self.assertIn("kind: 'exit'", body)
        self.assertIn("kind: 'boss-gate'", body)
        self.assertIn("stage:'draft'", body)
        self.assertIn("creator_common.js", body)


if __name__ == "__main__":
    unittest.main()
