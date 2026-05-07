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
from world.content.agent_runs import AgentRunStore
from world.content.editor import ContentEditor, ContentPublishValidationError


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
        self.assertIn("cooking_recipes", payload["domains"]["systems"])
        self.assertIn("boss_gates", payload["domains"]["systems"])

    def test_health_requires_authorization(self):
        request = self.factory.get("/api/content/health")
        request.user = _DummyUser(authenticated=False)
        response = views.content_health(request)
        self.assertEqual(403, response.status_code)

    def test_health_reports_draft_readiness_and_recommendations(self):
        request = self.factory.get("/api/content/health", {"stage": "draft"})
        request.user = self.user
        response = views.content_health(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertIn("draft_domains", payload)
        self.assertIn("validation_errors", payload)
        self.assertIn("readiness", payload)
        self.assertTrue(payload["readiness"])
        self.assertIn("recommended_next_actions", payload)

    def test_reference_search_returns_room_matches(self):
        request = self.factory.get("/api/content/references/rooms", {"q": "green", "limit": 5})
        request.user = self.user
        response = views.content_references(request, "rooms")
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("rooms", payload["domain"])
        match = next(entry for entry in payload["results"] if entry["id"] == "brambleford_town_green")
        self.assertIn("map_region", match)
        self.assertIn("map_x", match)
        self.assertIn("map_y", match)

    def test_reference_search_returns_exit_graph_edges(self):
        request = self.factory.get("/api/content/references/exits", {"q": "brambleford", "limit": 5})
        request.user = self.user
        response = views.content_references(request, "exits")
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("exits", payload["domain"])
        self.assertTrue(payload["results"])
        self.assertIn("source", payload["results"][0])
        self.assertIn("destination", payload["results"][0])

    def test_reference_search_returns_roaming_party_matches(self):
        request = self.factory.get("/api/content/references/roaming-parties", {"limit": 5})
        request.user = self.user
        response = views.content_references(request, "roaming-parties")
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("roaming-parties", payload["domain"])
        self.assertTrue(payload["results"])
        self.assertIn("region", payload["results"][0])
        self.assertIn("start_room", payload["results"][0])

    def test_reference_search_returns_system_matches(self):
        request = self.factory.get("/api/content/references/cooking-recipes", {"limit": 5})
        request.user = self.user
        response = views.content_references(request, "cooking-recipes")
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("cooking-recipes", payload["domain"])
        self.assertTrue(payload["results"])

    def test_preview_returns_room_payload(self):
        request = self.factory.post("/api/content/preview", data=json.dumps({"kind": "room", "args": ["brambleford_town_green"]}), content_type="application/json")
        request.user = self.user
        response = views.content_preview(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("room", payload["kind"])
        self.assertEqual("brambleford_town_green", payload["preview"]["room"]["id"])
        self.assertIn("incoming_exits", payload["preview"])
        self.assertIn("related", payload["preview"])

    def test_preview_returns_quest_payload_with_starting_state(self):
        request = self.factory.post("/api/content/preview", data=json.dumps({"kind": "quest", "args": ["practice_makes_heroes"]}), content_type="application/json")
        request.user = self.user
        response = views.content_preview(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("quest", payload["kind"])
        self.assertIn("is_starting", payload["preview"])
        self.assertIn("objectives", payload["preview"])

    def test_preview_returns_roaming_party_payload(self):
        request = self.factory.post("/api/content/preview", data=json.dumps({"kind": "roaming-party", "args": ["blackreed_patrol"]}), content_type="application/json")
        request.user = self.user
        response = views.content_preview(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("roaming-party", payload["kind"])
        self.assertEqual("blackreed_patrol", payload["preview"]["party_key"])
        self.assertIn("total_xp", payload["preview"])

    def test_preview_returns_system_payload(self):
        request = self.factory.post("/api/content/preview", data=json.dumps({"kind": "boss-gate", "args": ["ruk_fence_cutter"]}), content_type="application/json")
        request.user = self.user
        response = views.content_preview(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("boss-gate", payload["kind"])
        self.assertEqual("ruk_fence_cutter", payload["preview"]["gate_key"])

    def test_preview_returns_dialogue_payload(self):
        request = self.factory.post("/api/content/preview", data=json.dumps({"kind": "dialogue", "args": ["brother_alden"]}), content_type="application/json")
        request.user = self.user
        response = views.content_preview(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("dialogue", payload["kind"])
        self.assertIn("talk_rules", payload["preview"])
        self.assertIn("linked_content", payload["preview"])
        self.assertIn("quest_links", payload["preview"])

    def test_preview_returns_readable_payload(self):
        request = self.factory.post("/api/content/preview", data=json.dumps({"kind": "readable", "args": ["barrow_marker_stone"]}), content_type="application/json")
        request.user = self.user
        response = views.content_preview(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("readable", payload["kind"])
        self.assertIn("text", payload["preview"])
        self.assertIn("linked_content", payload["preview"])

    def test_mutate_dry_run_returns_diff(self):
        request = self.factory.post("/api/content/mutate", data=json.dumps({"kind": "room", "target": "creator_api_room", "payload": {"key": "Creator API Room", "desc": "Dry run through the web creator api.", "zone": "Testing", "world": "Brave"}, "write": False}), content_type="application/json")
        request.user = self.user
        response = views.content_mutate(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["write"])
        self.assertEqual("draft", payload["stage"])
        self.assertIn("creator_api_room", payload["diff"])

    def test_mutate_roaming_party_dry_run_returns_diff(self):
        request = self.factory.post(
            "/api/content/mutate",
            data=json.dumps({
                "kind": "roaming-party",
                "target": "creator_api_patrol",
                "payload": {
                    "key": "creator_api_patrol",
                    "region": "brambleford",
                    "start_room": "brambleford_town_green",
                    "interval": 18,
                    "respawn_delay": 180,
                    "avoid_safe": True,
                    "encounter": {"key": "creator_api_patrol", "title": "Creator API Patrol", "intro": "", "enemies": ["training_dummy"]},
                },
                "write": False,
            }),
            content_type="application/json",
        )
        request.user = self.user
        response = views.content_mutate(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["write"])
        self.assertIn("creator_api_patrol", payload["diff"])

    def test_mutate_system_dry_run_defaults_to_draft(self):
        request = self.factory.post(
            "/api/content/mutate",
            data=json.dumps({
                "kind": "fishing-rod",
                "target": "creator_api_rod",
                "payload": {"name": "Creator API Rod", "power": 1, "stability": 1, "summary": "Dry-run rod."},
                "write": False,
            }),
            content_type="application/json",
        )
        request.user = self.user
        response = views.content_mutate(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("draft", payload["stage"])
        self.assertIn("creator_api_rod", payload["diff"])

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

    def test_publish_endpoint_blocks_invalid_draft_without_reload(self):
        request = self.factory.post("/api/content/publish", data=json.dumps({"domain": "world"}), content_type="application/json")
        request.user = self.user
        error = ContentPublishValidationError(["Room new_bad uses a placeholder id"], domains=["world"])
        with patch("web.api.views.publish_content", side_effect=error), patch("web.api.views.reload_content_registry") as reload_mock:
            response = views.content_publish(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertFalse(payload["ok"])
        self.assertEqual([], payload["published"])
        self.assertEqual(["world"], payload["domains"])
        self.assertEqual(["Room new_bad uses a placeholder id"], payload["validation_errors"])
        reload_mock.assert_not_called()

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

    def test_codex_context_requires_authorization(self):
        request = self.factory.get("/api/content/codex/context")
        request.user = _DummyUser(authenticated=False)
        response = views.codex_context(request)
        self.assertEqual(403, response.status_code)

    def test_codex_context_reports_capabilities(self):
        request = self.factory.get("/api/content/codex/context")
        request.user = self.user
        response = views.codex_context(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertEqual("brave-creator-codex", payload["api"])
        self.assertIn("quest", payload["capabilities"]["mutation_kinds"])
        self.assertEqual(["draft"], payload["capabilities"]["stages"])
        self.assertIn("recipes", payload["capabilities"])
        self.assertEqual(["title"], payload["capabilities"]["recipes"]["quest"]["required_fields"])
        self.assertIn("health", payload)

    def test_codex_plan_returns_review_scaffold_without_writes(self):
        request = self.factory.post(
            "/api/content/codex/plan",
            data=json.dumps({"instructions": "Create a small quest.", "scope": {"domains": ["quests", "items"]}}),
            content_type="application/json",
        )
        request.user = self.user
        response = views.codex_plan(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["plan"]["write"])
        self.assertTrue(payload["plan"]["required_review"])
        self.assertEqual(["quests", "items"], payload["plan"]["scope"]["domains"])

    def test_codex_plan_requires_instructions(self):
        request = self.factory.post(
            "/api/content/codex/plan",
            data=json.dumps({"scope": {"domains": ["quests"]}}),
            content_type="application/json",
        )
        request.user = self.user
        response = views.codex_plan(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertIn("requires instructions", payload["error"])

    def test_codex_apply_writes_draft_mutations_only(self):
        fake_mutation = type("Mutation", (), {"domain": "quests", "path": "/tmp/quests.json", "stage": "draft", "diff": "diff", "entry_id": "entry-1", "history_path": "/tmp/history.json"})()
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"mutations": [{"kind": "quest", "target": "codex_test", "payload": {"title": "Codex Test"}}]}),
            content_type="application/json",
        )
        request.user = self.user
        with patch("web.api.views.mutate_content", return_value=fake_mutation) as mutate_mock, patch("web.api.views.creator_health_payload", return_value={"ok": True}):
            response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["write"])
        self.assertEqual("draft", payload["stage"])
        self.assertEqual("quests", payload["applied"][0]["domain"])
        self.assertEqual(["quests"], payload["touched_domains"])
        self.assertEqual({"kind": "quest", "args": ["codex_test"]}, payload["suggested_previews"][0])
        self.assertEqual("missing_preview", payload["recipe_warnings"][0]["kind"])
        mutate_mock.assert_called_once()
        self.assertEqual("draft", mutate_mock.call_args.kwargs["stage"])
        self.assertTrue(mutate_mock.call_args.kwargs["write"])

    def test_codex_apply_rejects_empty_mutations(self):
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"mutations": []}),
            content_type="application/json",
        )
        request.user = self.user
        response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertIn("non-empty mutations list", payload["error"])

    def test_codex_apply_rejects_unknown_kind_before_mutating(self):
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"mutations": [{"kind": "unknown", "target": "codex_test", "payload": {}}]}),
            content_type="application/json",
        )
        request.user = self.user
        with patch("web.api.views.mutate_content") as mutate_mock:
            response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertIn("unknown kind", payload["error"])
        mutate_mock.assert_not_called()

    def test_codex_apply_rejects_missing_target_before_mutating(self):
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"mutations": [{"kind": "item", "payload": {"name": "Codex Test Item"}}]}),
            content_type="application/json",
        )
        request.user = self.user
        with patch("web.api.views.mutate_content") as mutate_mock:
            response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertIn("requires target", payload["error"])
        mutate_mock.assert_not_called()

    def test_codex_apply_rejects_wrong_payload_type_before_mutating(self):
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"mutations": [{"kind": "dialogue", "target": "npc_id", "payload": {"text": "Not a list."}}]}),
            content_type="application/json",
        )
        request.user = self.user
        with patch("web.api.views.mutate_content") as mutate_mock:
            response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertIn("payload must be a JSON list", payload["error"])
        mutate_mock.assert_not_called()

    def test_codex_apply_rejects_missing_required_fields_before_mutating(self):
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"mutations": [{"kind": "item", "target": "codex_test_item", "payload": {"kind": "loot"}}]}),
            content_type="application/json",
        )
        request.user = self.user
        with patch("web.api.views.mutate_content") as mutate_mock:
            response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertIn("missing required fields: name", payload["error"])
        mutate_mock.assert_not_called()

    def test_codex_apply_rejects_live_stage(self):
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"stage": "live", "mutations": [{"kind": "quest", "target": "codex_test", "payload": {}}]}),
            content_type="application/json",
        )
        request.user = self.user
        response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertIn("draft stage", payload["error"])

    def test_codex_apply_dry_run_does_not_write_or_return_health(self):
        fake_mutation = type("Mutation", (), {"domain": "items", "path": "/tmp/items.json", "stage": "draft", "diff": "diff", "entry_id": "entry-1", "history_path": "/tmp/history.json"})()
        request = self.factory.post(
            "/api/content/codex/apply",
            data=json.dumps({"dry_run": True, "mutations": [{"kind": "item", "target": "codex_test_item", "payload": {"name": "Codex Test Item"}}]}),
            content_type="application/json",
        )
        request.user = self.user
        with patch("web.api.views.mutate_content", return_value=fake_mutation) as mutate_mock, patch("web.api.views.creator_health_payload") as health_mock:
            response = views.codex_apply(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertFalse(payload["write"])
        self.assertIsNone(payload["health"])
        self.assertEqual(["items"], payload["touched_domains"])
        self.assertEqual([{"kind": "item", "args": ["codex_test_item"]}], payload["suggested_previews"])
        self.assertFalse(mutate_mock.call_args.kwargs["write"])
        health_mock.assert_not_called()

    def test_codex_apply_attaches_to_agent_run(self):
        fake_mutation = type("Mutation", (), {"domain": "quests", "path": "/tmp/quests.json", "stage": "draft", "diff": "diff", "entry_id": "entry-1", "history_path": "/tmp/history.json"})()
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="API attached run.", mutations=[{"kind": "quest", "target": "codex_run_test", "payload": {"title": "Codex Run Test"}}])
            request = self.factory.post(
                "/api/content/codex/apply",
                data=json.dumps({"run_id": run["run_id"], "dry_run": True, "mutations": run["mutations"]}),
                content_type="application/json",
            )
            request.user = self.user
            with patch("web.api.views.AgentRunStore", return_value=store), patch("web.api.views.mutate_content", return_value=fake_mutation):
                response = views.codex_apply(request)
            payload = json.loads(response.content)

            stored = store.get(run["run_id"])
        self.assertEqual(200, response.status_code)
        self.assertEqual(run["run_id"], payload["run_id"])
        self.assertEqual("dry_run", stored["status"])
        self.assertFalse(stored["dry_run"]["write"])

    def test_codex_verify_returns_health_and_requested_previews(self):
        request = self.factory.post(
            "/api/content/codex/verify",
            data=json.dumps({"previews": [{"kind": "quest", "args": ["practice_makes_heroes"]}]}),
            content_type="application/json",
        )
        request.user = self.user
        with patch("web.api.views.creator_health_payload", return_value={"ok": True, "validation_errors": []}), patch("web.api.views.preview_content", return_value={"quest": {"title": "Practice Makes Heroes"}}):
            response = views.codex_verify(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["ok"])
        self.assertEqual("draft", payload["stage"])
        self.assertTrue(payload["previews"][0]["found"])

    def test_codex_verify_attaches_to_agent_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="API verify run.")
            request = self.factory.post(
                "/api/content/codex/verify",
                data=json.dumps({"run_id": run["run_id"], "previews": [{"kind": "quest", "args": ["practice_makes_heroes"]}]}),
                content_type="application/json",
            )
            request.user = self.user
            with patch("web.api.views.AgentRunStore", return_value=store), patch("web.api.views.creator_health_payload", return_value={"ok": True, "validation_errors": []}), patch("web.api.views.preview_content", return_value={"quest": {"title": "Practice Makes Heroes"}}):
                response = views.codex_verify(request)
            payload = json.loads(response.content)
            stored = store.get(run["run_id"])

        self.assertEqual(200, response.status_code)
        self.assertEqual(run["run_id"], payload["run_id"])
        self.assertEqual("verified", stored["status"])
        self.assertTrue(stored["verify"]["previews"][0]["found"])

    def test_codex_runs_require_authorization(self):
        request = self.factory.get("/api/content/codex/runs")
        request.user = _DummyUser(authenticated=False)
        response = views.codex_runs(request)
        self.assertEqual(403, response.status_code)

    def test_codex_runs_returns_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="Summarized run.", mutations=[{"kind": "quest", "target": "summary_run", "payload": {"title": "Summary Run"}}])
            store.update(run["run_id"], status="validated", validation={"ok": True, "touched_domains": ["quests"]})
            request = self.factory.get("/api/content/codex/runs", {"limit": 5})
            request.user = self.user
            with patch("web.api.views.AgentRunStore", return_value=store):
                response = views.codex_runs(request)
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual(run["run_id"], payload["runs"][0]["run_id"])
        self.assertEqual(["quests"], payload["runs"][0]["touched_domains"])
        self.assertNotIn("dry_run", payload["runs"][0])

    def test_codex_run_detail_returns_full_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="Detailed run.", mutations=[{"kind": "quest", "target": "detail_run", "payload": {"title": "Detail Run"}}])
            request = self.factory.get(f"/api/content/codex/runs/{run['run_id']}")
            request.user = self.user
            with patch("web.api.views.AgentRunStore", return_value=store):
                response = views.codex_run_detail(request, run["run_id"])
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual(run["run_id"], payload["run"]["run_id"])
        self.assertIn("mutations", payload["run"])

    def test_codex_run_review_appends_note_and_marks_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="Reviewable run.")
            request = self.factory.post(
                f"/api/content/codex/runs/{run['run_id']}/review",
                data=json.dumps({"note": "Reviewed in Mission Control."}),
                content_type="application/json",
            )
            request.user = self.user
            with patch("web.api.views.AgentRunStore", return_value=store):
                response = views.codex_run_review(request, run["run_id"])
            stored = store.get(run["run_id"])
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("reviewed", payload["run"]["status"])
        self.assertEqual("reviewed", stored["status"])
        self.assertEqual("Reviewed in Mission Control.", stored["review_notes"][0]["note"])

    def test_codex_run_publish_promotes_touched_domains_and_marks_published(self):
        fake_mutation = type("Mutation", (), {"domain": "quests", "path": "/tmp/quests.json", "entry_id": "entry-4", "history_path": "/tmp/history/entry-4.json", "diff": "diff"})()
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="Publishable run.")
            store.update(run["run_id"], status="applied", apply={"touched_domains": ["quests", "items"]})
            request = self.factory.post(
                f"/api/content/codex/runs/{run['run_id']}/publish",
                data=json.dumps({}),
                content_type="application/json",
            )
            request.user = self.user
            with (
                patch("web.api.views.AgentRunStore", return_value=store),
                patch("web.api.views.publish_content", return_value=[fake_mutation]) as publish_mock,
                patch("web.api.views.reload_content_registry"),
                patch("web.api.views.validate_content_registry", return_value=[]),
            ):
                response = views.codex_run_publish(request, run["run_id"])
            stored = store.get(run["run_id"])
        payload = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual("published", payload["run"]["status"])
        self.assertEqual("published", stored["status"])
        self.assertEqual(["items", "quests"], stored["publish"]["domains"])
        publish_mock.assert_called_once_with(["items", "quests"], author="tester")

    def test_codex_run_publish_records_validation_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="Blocked run.")
            store.update(run["run_id"], status="reviewed", apply={"touched_domains": ["quests"]})
            request = self.factory.post(
                f"/api/content/codex/runs/{run['run_id']}/publish",
                data=json.dumps({}),
                content_type="application/json",
            )
            request.user = self.user
            error = ContentPublishValidationError(["Quest test rewards unknown item: missing_item"], domains=["quests"])
            with patch("web.api.views.AgentRunStore", return_value=store), patch("web.api.views.publish_content", side_effect=error):
                response = views.codex_run_publish(request, run["run_id"])
            stored = store.get(run["run_id"])
        payload = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertEqual("publish_blocked", payload["run"]["status"])
        self.assertEqual("publish_blocked", stored["status"])
        self.assertEqual(["Quest test rewards unknown item: missing_item"], stored["publish"]["validation_errors"])


if __name__ == "__main__":
    unittest.main()
