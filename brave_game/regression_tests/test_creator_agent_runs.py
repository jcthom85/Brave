import tempfile
import time
import unittest
from pathlib import Path

from world.content.agent_runs import AgentRunStore, run_summary


class CreatorAgentRunStoreTests(unittest.TestCase):
    def test_create_list_get_and_update_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(
                instructions="Build a small test quest.",
                scope={"domains": ["quests"]},
                mutations=[{"kind": "quest", "target": "run_test", "payload": {"title": "Run Test"}}],
            )

            self.assertEqual("planned", run["status"])
            self.assertTrue(run["run_id"])
            self.assertEqual(run["run_id"], store.get(run["run_id"])["run_id"])
            self.assertEqual([run["run_id"]], [entry["run_id"] for entry in store.list(limit=5)])

            updated = store.update(run["run_id"], status="validated", validation={"ok": True, "touched_domains": ["quests"]})
            self.assertEqual("validated", updated["status"])
            self.assertEqual(["quests"], run_summary(updated)["touched_domains"])

    def test_status_transition_updates_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))
            run = store.create(instructions="Timestamp run.")
            created_updated_at = run["updated_at"]
            time.sleep(0.001)

            updated = store.update(run["run_id"], status="failed")

            self.assertNotEqual(created_updated_at, updated["updated_at"])

    def test_get_unknown_run_raises_key_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentRunStore(root=Path(tmp))

            with self.assertRaises(KeyError):
                store.get("missing-run")


if __name__ == "__main__":
    unittest.main()
