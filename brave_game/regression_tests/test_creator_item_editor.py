import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_item_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = username
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorItemEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        request.session = {}
        return request

    def test_creator_item_editor_requires_authorization(self):
        request = self._get_request("/creator/items/")
        response = creator_item_editor(request)
        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_item_editor_renders_for_staff(self):
        request = self._get_request("/creator/items/", user=_DummyUser(staff=True))
        response = creator_item_editor(request)
        body = response.content.decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("Item Builder", body)
        self.assertIn("Creator Guide", body)
        self.assertIn("Usage & Placement", body)
        self.assertIn("Equipment</strong>", body)
        self.assertIn("Meal</strong>", body)
        self.assertIn("Recipe Unlock</strong>", body)
        self.assertIn("Fish/Catch</strong>", body)
        self.assertIn("Identity & Economy", body)
        self.assertIn("Consumable Effects", body)
        self.assertIn("Equipment Bonuses", body)
        self.assertIn("Restore Effects", body)
        self.assertIn("Use Effect", body)
        self.assertIn("item-rarity", body)
        self.assertIn("item-rarity-warning", body)
        self.assertIn("Act 1 should stay mostly common/uncommon", body)
        self.assertIn("placement-hints", body)
        self.assertIn("item-link-grid", body)
        self.assertIn("Copy Link Payload", body)
        self.assertIn("Send To Builder", body)
        self.assertIn("item-shell", body)
        self.assertIn("applyItemIncoming", body)
        self.assertIn("registerApplyHandler('item-shell'", body)
        self.assertIn("applyPreset", body)
        self.assertIn("payloadSnippet", body)
        self.assertIn("stage: 'draft'", body)
        self.assertIn("Advanced Source", body)
        self.assertIn("Preview Item Change", body)
        self.assertIn("Save Item", body)
        self.assertIn("New Item Draft", body)
        self.assertIn("/api/content", body)


if __name__ == "__main__":
    unittest.main()
