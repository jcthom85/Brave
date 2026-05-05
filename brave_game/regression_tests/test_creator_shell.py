from pathlib import Path
import unittest


CREATOR_COMMON_PATH = Path(__file__).resolve().parents[1] / "web" / "static" / "website" / "js" / "creator_common.js"


class CreatorShellTests(unittest.TestCase):
    def test_shared_creator_shell_contains_navigation_and_flow(self):
        source = CREATOR_COMMON_PATH.read_text(encoding="utf-8")

        self.assertIn("CREATOR_LINKS", source)
        self.assertIn("attachCreatorShell", source)
        self.assertIn("Boss Composer", source)
        self.assertIn("Authoring flow: World", source)
        self.assertIn("/creator/composers/boss/", source)


if __name__ == "__main__":
    unittest.main()
