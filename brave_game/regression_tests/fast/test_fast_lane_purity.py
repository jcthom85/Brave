import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FAST_ROOT = Path(__file__).resolve().parent


class FastLanePurityTests(unittest.TestCase):
    def test_fast_tests_do_not_import_django_or_evennia(self):
        forbidden_roots = {"django", "evennia"}

        for path in FAST_ROOT.glob("test_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = {alias.name.split(".")[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    imported = {str(node.module or "").split(".")[0]}
                else:
                    continue
                self.assertFalse(
                    imported & forbidden_roots,
                    msg=f"{path.relative_to(ROOT)} imports {sorted(imported & forbidden_roots)}",
                )

    def test_fast_lane_modules_stay_free_of_django_and_evennia_imports(self):
        checked_paths = [
            ROOT / "world/content/build.py",
            ROOT / "world/content/editor.py",
            ROOT / "world/content/registry.py",
            ROOT / "world/content/validation.py",
            ROOT / "world/browser_context.py",
            ROOT / "world/browser_formatting.py",
            ROOT / "world/browser_ui.py",
            ROOT / "world/combat_actor_utils.py",
        ]
        forbidden = ("import django", "from django", "import evennia", "from evennia")

        for path in checked_paths:
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, source, msg=f"{path.relative_to(ROOT)} contains {token}")


if __name__ == "__main__":
    unittest.main()
