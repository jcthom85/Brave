import os
import unittest

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.creator import creator_world_editor


class _DummyUser:
    def __init__(self, *, authenticated=True, staff=False, superuser=False, developer=False, username="testuser"):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = username
        self._developer = developer

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorWorldEditorViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, path, user=None):
        request = self.factory.get(path)
        request.user = user or _DummyUser(authenticated=False)
        request.session = {}
        return request

    def test_creator_world_editor_requires_authorization(self):
        request = self._get_request("/creator/world/")

        response = creator_world_editor(request)

        self.assertEqual(302, response.status_code)
        self.assertIn("/creator/login/", response.url)

    def test_creator_world_editor_rejects_authenticated_non_creator_user(self):
        request = self._get_request("/creator/world/", user=_DummyUser(authenticated=True))

        response = creator_world_editor(request)

        self.assertEqual(403, response.status_code)

    def test_creator_world_editor_renders_for_staff(self):
        request = self._get_request("/creator/world/", user=_DummyUser(staff=True))

        response = creator_world_editor(request)
        body = response.content.decode("utf-8")

        self.assertEqual(200, response.status_code)
        self.assertIn("Rooms", body)
        self.assertIn("Room Map", body)
        self.assertIn("Inspector", body)
        self.assertIn("/api/content", body)
        self.assertIn("Room Details", body)
        self.assertIn("New Room", body)
        self.assertIn("Save Room", body)
        self.assertIn("Save Exit", body)
        self.assertIn("Save Entity", body)
        self.assertIn("Advanced Source", body)
        self.assertIn("Create Path", body)
        self.assertIn("Write Position", body)
        self.assertIn("Path Tool", body)
        self.assertIn("Two-way", body)
        self.assertIn("Reverse Exit", body)
        self.assertIn("Path Summary", body)
        self.assertIn("Related Content", body)
        self.assertIn("Validate Drafts", body)
        self.assertIn("region-filter", body)
        self.assertIn("world-graph", body)
        self.assertIn("New Exit Draft", body)
        self.assertIn("exit-direction", body)
        self.assertIn("exit-aliases", body)
        self.assertIn("exit-required-quest", body)
        self.assertIn("exit-lock-message", body)
        self.assertIn("exit-boss-gate", body)
        self.assertIn("New Entity Draft", body)
        self.assertIn("Destination Room", body)
        self.assertIn("Entity Kind", body)
        self.assertIn("Aliases", body)
        self.assertIn("Entity Description", body)
        self.assertIn("data-editor-tab=\"room\"", body)
        self.assertIn("validation-notes", body)
        self.assertIn("creator_common.js", body)
        self.assertIn("applyWorldIncoming", body)
        self.assertIn("registerApplyHandler(\"room-activity\"", body)
        self.assertIn("registerApplyHandler(\"boss-exit\"", body)
        self.assertIn("registerApplyHandler(\"world-readable\"", body)
        self.assertIn("Drafted exit", body)
        self.assertIn("buildTwoWayExitDraft", body)
        self.assertIn("buildReverseExitDraft", body)
        self.assertIn("stagePathDraft", body)
        self.assertIn("writePathDraft", body)
        self.assertIn("allowErrorPayload", body)
        self.assertIn("Save this room before adding exits", body)
        self.assertNotIn("mutateExit(true);", body)


if __name__ == "__main__":
    unittest.main()
