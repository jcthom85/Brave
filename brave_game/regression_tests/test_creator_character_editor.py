import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_character_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorCharacterEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_creator_character_editor_requires_authorization(self):
        request = self.factory.get("/creator/characters/")
        request.user = _DummyUser(authenticated=False)
        response = creator_character_editor(request)
        self.assertEqual(403, response.status_code)

    def test_creator_character_editor_renders_for_staff(self):
        request = self.factory.get("/creator/characters/")
        request.user = _DummyUser(staff=True)
        response = creator_character_editor(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Character Builder", body)
        self.assertIn("Class Builder", body)
        self.assertIn("Race Builder", body)
        self.assertIn("Character Config", body)
        self.assertIn("Advanced Source", body)
        self.assertIn("Sync Builder To Source", body)
        self.assertIn("/api/content", body)


if __name__ == "__main__":
    unittest.main()
