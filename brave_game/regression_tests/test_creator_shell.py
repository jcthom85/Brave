from pathlib import Path
import unittest


CREATOR_COMMON_PATH = Path(__file__).resolve().parents[1] / "web" / "static" / "website" / "js" / "creator_common.js"


class CreatorShellTests(unittest.TestCase):
    def test_shared_creator_shell_contains_navigation_and_flow(self):
        source = CREATOR_COMMON_PATH.read_text(encoding="utf-8")

        self.assertIn("CREATOR_LINKS", source)
        self.assertIn("attachCreatorShell", source)
        self.assertIn("Brave Creator Studio", source)
        self.assertIn("creator-shell-has-nav", source)
        self.assertIn("creator-shell-fixed-workspace", source)
        self.assertIn(".quest-row", source)
        self.assertIn("position: fixed", source)
        self.assertIn("calc(100vh - var(--creator-shell-height))", source)
        self.assertIn("window.getComputedStyle(shell).position === 'fixed'", source)
        self.assertIn("Boss Composer", source)
        self.assertIn("Recipe Composer", source)
        self.assertIn("Fishing Composer", source)
        self.assertIn("creator-shell-nav__menu", source)
        self.assertIn("<summary>Composers</summary>", source)
        self.assertIn("/creator/composers/boss/", source)
        self.assertIn("fetchHealth", source)
        self.assertIn("renderHealthPanel", source)
        self.assertIn("Draft Actions", source)
        self.assertIn("data-creator-actions-host", source)
        self.assertIn("Draft Health", source)
        self.assertIn("Recommended Cleanup", source)
        self.assertIn("Readiness Issues", source)
        self.assertIn("Agent Runs", source)
        self.assertIn("Scratch / Test Runs", source)
        self.assertIn("isScratchRun", source)
        self.assertIn("box-shadow:inset 3px 0 0", source)
        self.assertIn("attachAgentRunsPanel", source)
        self.assertIn("Ready To Publish", source)
        self.assertIn("Published History", source)
        self.assertIn("/codex/runs?limit=20", source)
        self.assertIn("/codex/runs/${encodeURIComponent", source)
        self.assertIn("/review", source)
        self.assertIn("Mark Reviewed", source)
        self.assertIn("sendToBuilder", source)
        self.assertIn("normalizeIncomingPayload", source)
        self.assertIn("source_builder", source)
        self.assertIn("target_builder", source)
        self.assertIn("kind", source)
        self.assertIn("consumeIncomingPayload", source)
        self.assertIn("Incoming Payload", source)
        self.assertIn("Apply To Builder", source)
        self.assertIn("registerApplyHandler", source)
        self.assertIn("applyIncomingPayload", source)


if __name__ == "__main__":
    unittest.main()
