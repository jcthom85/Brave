import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from scripts import creator_codex
from world.content.agent_runs import AgentRunStore


class CreatorCodexCliTests(unittest.TestCase):
    def test_plan_payload_returns_review_scaffold(self):
        payload = creator_codex.plan_payload(json.dumps({"instructions": "Build a starter quest.", "scope": {"domains": ["quests"]}}))

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["plan"]["write"])
        self.assertTrue(payload["plan"]["required_review"])
        self.assertEqual(["quests"], payload["plan"]["scope"]["domains"])
        self.assertIn("quest", payload["capabilities"]["mutation_kinds"])

    def test_drift_payload_returns_domain_summary(self):
        payload = creator_codex.drift_payload()

        self.assertTrue(payload["ok"])
        self.assertIn("domains", payload)
        self.assertIn("summary", payload)
        self.assertTrue(any(entry["domain"] == "world" for entry in payload["domains"]))

    def test_recipes_payload_returns_all_and_single_recipe(self):
        payload = creator_codex.recipes_payload()
        self.assertTrue(payload["ok"])
        self.assertIn("quest", payload["recipes"])
        self.assertEqual(["title"], payload["recipes"]["quest"]["required_fields"])

        single = creator_codex.recipes_payload("item")
        self.assertEqual(["item"], list(single["recipes"]))
        self.assertEqual("object", single["recipes"]["item"]["payload_type"])

    def test_validate_payload_returns_touched_domains_and_previews(self):
        source = json.dumps({"mutations": [{"kind": "quest", "target": "codex_cli_test", "payload": {"title": "Codex CLI Test"}}]})
        payload = creator_codex.validate_payload(source)

        self.assertTrue(payload["ok"])
        self.assertEqual(["quests"], payload["touched_domains"])
        self.assertEqual([{"kind": "quest", "args": ["codex_cli_test"]}], payload["suggested_previews"])

    def test_validate_payload_rejects_missing_required_field(self):
        source = json.dumps({"mutations": [{"kind": "item", "target": "codex_cli_item", "payload": {"kind": "loot"}}]})

        with self.assertRaises(ValueError) as raised:
            creator_codex.validate_payload(source)

        self.assertIn("missing required fields: name", str(raised.exception))

    def test_apply_payload_dry_run_uses_draft_without_health(self):
        fake_mutation = type("Mutation", (), {"domain": "quests", "path": "/tmp/quests.json", "stage": "draft", "diff": "diff", "entry_id": "entry-1", "history_path": "/tmp/history.json"})()
        source = json.dumps({"mutations": [{"kind": "quest", "target": "codex_cli_test", "payload": {"title": "Codex CLI Test"}}]})

        with patch("commands.brave_creator.mutate_content", return_value=fake_mutation) as mutate_mock, patch("world.content.health.creator_health_payload") as health_mock:
            payload = creator_codex.apply_payload(source, dry_run=True)

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["write"])
        self.assertIsNone(payload["health"])
        self.assertEqual("quests", payload["applied"][0]["domain"])
        self.assertEqual(["quests"], payload["touched_domains"])
        self.assertEqual("missing_preview", payload["recipe_warnings"][0]["kind"])
        self.assertEqual("draft", mutate_mock.call_args.kwargs["stage"])
        self.assertEqual("codex-cli", mutate_mock.call_args.kwargs["author"])
        self.assertFalse(mutate_mock.call_args.kwargs["write"])
        health_mock.assert_not_called()

    def test_apply_payload_validates_before_mutating(self):
        source = json.dumps({"mutations": [{"kind": "item", "target": "codex_cli_item", "payload": {"kind": "loot"}}]})

        with patch("commands.brave_creator.mutate_content") as mutate_mock, self.assertRaises(SystemExit) as raised:
            creator_codex.apply_payload(source, dry_run=True)

        self.assertIn("missing required fields: name", str(raised.exception))
        mutate_mock.assert_not_called()

    def test_apply_payload_write_returns_health(self):
        fake_mutation = type("Mutation", (), {"domain": "items", "path": "/tmp/items.json", "stage": "draft", "diff": "diff", "entry_id": "entry-2", "history_path": "/tmp/history.json"})()
        source = json.dumps({"mutations": [{"kind": "item", "target": "codex_cli_item", "payload": {"name": "Codex CLI Item"}}]})

        with patch("commands.brave_creator.mutate_content", return_value=fake_mutation) as mutate_mock, patch("world.content.health.creator_health_payload", return_value={"ok": True}) as health_mock:
            payload = creator_codex.apply_payload(source)

        self.assertTrue(payload["write"])
        self.assertEqual({"ok": True}, payload["health"])
        self.assertEqual("draft", mutate_mock.call_args.kwargs["stage"])
        self.assertTrue(mutate_mock.call_args.kwargs["write"])
        health_mock.assert_called_once_with(stage="draft")

    def test_verify_payload_returns_health_and_previews(self):
        source = json.dumps({"previews": [{"kind": "quest", "args": ["practice_makes_heroes"]}]})

        with patch("commands.brave_creator.preview_content", return_value={"quest": {"title": "Practice Makes Heroes"}}), patch("world.content.health.creator_health_payload", return_value={"ok": True, "validation_errors": []}):
            payload = creator_codex.verify_payload(source)

        self.assertTrue(payload["ok"])
        self.assertEqual("draft", payload["stage"])
        self.assertTrue(payload["previews"][0]["found"])

    def test_run_create_list_show_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            source = json.dumps({
                "instructions": "Build a CLI run quest.",
                "scope": {"domains": ["quests"]},
                "mutations": [{"kind": "quest", "target": "cli_run_quest", "payload": {"title": "CLI Run Quest"}}],
            })

            with patch("scripts.creator_codex._run_store", return_value=store):
                created = creator_codex.run_create_payload(source)
                run_id = created["run"]["run_id"]
                listed = creator_codex.run_list_payload()
                shown = creator_codex.run_show_payload(run_id)
                validated = creator_codex.run_validate_payload(run_id)

            self.assertEqual(run_id, listed["runs"][0]["run_id"])
            self.assertEqual("Build a CLI run quest.", shown["run"]["instructions"])
            self.assertEqual("validated", validated["run"]["status"])
            self.assertEqual(["quests"], validated["run"]["validation"]["touched_domains"])

    def test_run_dry_run_apply_verify_and_review(self):
        fake_mutation = type("Mutation", (), {"domain": "quests", "path": "/tmp/quests.json", "stage": "draft", "diff": "diff", "entry_id": "entry-1", "history_path": "/tmp/history.json"})()
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(
                instructions="Run a full CLI flow.",
                mutations=[{"kind": "quest", "target": "cli_run_full", "payload": {"title": "CLI Run Full"}}],
            )

            with (
                patch("scripts.creator_codex._run_store", return_value=store),
                patch("commands.brave_creator.mutate_content", return_value=fake_mutation) as mutate_mock,
                patch("world.content.health.creator_health_payload", return_value={"ok": True, "validation_errors": []}),
                patch("commands.brave_creator.preview_content", return_value={"quest": {"title": "CLI Run Full"}}),
            ):
                dry_run = creator_codex.run_dry_run_payload(run["run_id"])
                applied = creator_codex.run_apply_payload(run["run_id"])
                verified = creator_codex.run_verify_payload(run["run_id"])
                reviewed = creator_codex.run_review_payload(run["run_id"], "Looks ready for Creator review.")

            self.assertEqual("dry_run", dry_run["run"]["status"])
            self.assertFalse(dry_run["run"]["dry_run"]["write"])
            self.assertEqual("applied", applied["run"]["status"])
            self.assertEqual("entry-1", applied["run"]["apply"]["applied"][0]["entry_id"])
            self.assertEqual("verified", verified["run"]["status"])
            self.assertTrue(verified["run"]["verify"]["previews"][0]["found"])
            self.assertEqual("reviewed", reviewed["run"]["status"])
            self.assertEqual("Looks ready for Creator review.", reviewed["run"]["review_notes"][0]["note"])
            self.assertEqual(2, mutate_mock.call_count)


if __name__ == "__main__":
    unittest.main()
