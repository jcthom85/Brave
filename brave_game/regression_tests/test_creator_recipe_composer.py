import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_recipe_composer


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = False

    def check_permstring(self, permstring):
        return False


class CreatorRecipeComposerViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_creator_recipe_composer_requires_authorization(self):
        request = self.factory.get("/creator/composers/recipe/")
        request.user = _DummyUser(authenticated=False)
        response = creator_recipe_composer(request)
        self.assertEqual(403, response.status_code)

    def test_creator_recipe_composer_renders_guided_flow_for_staff(self):
        request = self.factory.get("/creator/composers/recipe/")
        request.user = _DummyUser(staff=True)
        response = creator_recipe_composer(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Recipe Composer", body)
        self.assertIn("Compose Recipe Flow", body)
        self.assertIn("Write Draft Recipe Flow", body)
        self.assertIn("cooking-recipe", body)
        self.assertIn("tinkering-recipe", body)
        self.assertIn("kind:'item'", body)
        self.assertIn("stage:'draft'", body)
        self.assertIn("sendToBuilder", body)
        self.assertIn("creator_common.js", body)


if __name__ == "__main__":
    unittest.main()
