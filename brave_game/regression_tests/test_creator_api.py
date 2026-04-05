import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import django
from django.test import RequestFactory


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.api import views
from world.content.editor import ContentEditor


class _DummyUser:
    def __init__(self, *, authenticated=True, username="tester", staff=False, superuser=False, developer=False):
        self.is_authenticated = authenticated
        self.username = username
        self.is_staff = staff
        self.is_superuser = superuser
        self._developer = developer

    def get_username(self):
        return self.username

    def check_permstring(self, permstring):
        return self._developer and permstring == "Developer"


class CreatorApiTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = _DummyUser(authenticated=True, staff=True)

    def test_status_requires_authorization(self):
        request = self.factory.get("/api/content/status")
        request.user = _DummyUser(authenticated=False)
        response = views.content_status(request)
        self.assertEqual(403, response.status_code)

    def test_status_rejects_non_creator_authenticated_user(self):
        request = self.factory.get("/api/content/status")
        request.user = _DummyUser(authenticated=True)
        response = views.content_status(request)
        payload = json.loads(response.content)
        self.assertEqual(403, response.status_code)
        self.assertIn("Creator access required", payload["error"])

    def test_status_allows_staff_user(self):
        request = self.factory.get("/api/content/status")
        request.user = self.user
        response = views.content_status(request)
        self.assertEqual(200, response.status_code)

    def test_status_allows_developer_user(self):
        request = self.factory.get("/api/content/status")
        request.user = _DummyUser(authenticated=True, developer=True)
        response = views.content_status(request)
        self.assertEqual(200, response.status_code)

    def test_status_reports_domains(self):
        request = self.factory.get("/api/content/status")
        request.user = self.user
        response = views.content_status(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertIn("quests", payload["domains"])
        self.assertIn("draft", payload["domains"]["world"])

    def test_reference_search_returns_room_matches(self):
        request = self.factory.get("/api/content/references/rooms", {"q": "green", "limit": 5})
        request.user = self.user
        response = views.content_references(request, "rooms")
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("rooms", payload["domain"])
        self.assertTrue(any(entry["id"] == "brambleford_town_green" for entry in payload["results"]))

    def test_preview_returns_room_payload(self):
        request = self.factory.post("/api/content/preview", data=json.dumps({"kind": "room", "args": ["brambleford_town_green"]}), content_type="application/json")
        request.user = self.user
        response = views.content_preview(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("room", payload["kind"])
        self.assertEqual("brambleford_town_green", payload["preview"]["room"]["id"])

    def test_mutate_dry_run_returns_diff(self):
        request = self.factory.post("/api/content/mutate", data=json.dumps({"kind": "room", "target": "creator_api_room", "payload": {"key": "Creator API Room", "desc": "Dry run through the web creator api.", "zone": "Testing", "world": "Brave"}, "write": False}), content_type="application/json")
        request.user = self.user
        response = views.content_mutate(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["write"])
        self.assertIn("creator_api_room", payload["diff"])

    def test_remove_dry_run_returns_diff(self):
        request = self.factory.post("/api/content/remove", data=json.dumps({"kind": "read", "target": "dawn_bell", "write": False}), content_type="application/json")
        request.user = self.user
        response = views.content_remove(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["write"])
        self.assertIn("dawn_bell", payload["diff"])

    def test_history_endpoint_returns_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            editor = ContentEditor(history_root=Path(tmp))
            editor.history.record(domain="world", stage="live", action="upsert", target="test_room", path="/tmp/world.json", diff="diff", before={}, after={}, author="api-user")
            request = self.factory.get("/api/content/history", {"limit": 5})
            request.user = self.user
            with patch("web.api.views.list_content_history", return_value=editor.list_history(limit=5)):
                response = views.content_history(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["entries"])
        self.assertEqual("api-user", payload["entries"][0]["author"])

    def test_revert_endpoint_returns_mutation_metadata(self):
        fake_mutation = {"ok": True}
        request = self.factory.post("/api/content/revert", data=json.dumps({"entry_id": "entry-1", "write": False}), content_type="application/json")
        request.user = self.user
        with patch("web.api.views.revert_content") as revert_mock:
            revert_mock.return_value = type("Mutation", (), {"domain": "items", "path": "/tmp/items.json", "stage": "live", "diff": "diff", "entry_id": "entry-2", "history_path": "/tmp/history/entry-2.json"})()
            response = views.content_revert(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("items", payload["domain"])
        self.assertEqual("entry-2", payload["entry_id"])

    def test_publish_endpoint_returns_published_entries(self):
        request = self.factory.post("/api/content/publish", data=json.dumps({"domain": "items"}), content_type="application/json")
        request.user = self.user
        with patch("web.api.views.publish_content") as publish_mock, patch("web.api.views.reload_content_registry") as reload_mock, patch("web.api.views.validate_content_registry", return_value=[]):
            publish_mock.return_value = [type("Mutation", (), {"domain": "items", "path": "/tmp/items.json", "entry_id": "entry-3", "history_path": "/tmp/history/entry-3.json", "diff": "diff"})()]
            reload_mock.return_value = object()
            response = views.content_publish(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(payload["published"]))
        self.assertEqual("items", payload["published"][0]["domain"])

    def test_validate_returns_ok_payload(self):
        request = self.factory.post("/api/content/validate", data=b"{}", content_type="application/json")
        request.user = self.user
        response = views.content_validate(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertIn("errors", payload)

    def test_reload_returns_sources(self):
        request = self.factory.post("/api/content/reload", data=b"{}", content_type="application/json")
        request.user = self.user
        response = views.content_reload(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertIn("world", payload["sources"])


if __name__ == "__main__":
    unittest.main()
