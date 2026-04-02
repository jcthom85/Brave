import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CMDSETS = ROOT / "commands" / "default_cmdsets.py"


class CommandRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = ast.parse(DEFAULT_CMDSETS.read_text())
        cls.imports = {}
        for node in cls.module.body:
            if isinstance(node, ast.ImportFrom):
                cls.imports[node.module] = {alias.name for alias in node.names}

    def test_extracted_modules_are_imported(self):
        self.assertIn("brave_arcade", self.imports)
        self.assertIn("brave_combat", self.imports)
        self.assertIn("brave_explore", self.imports)
        self.assertIn("brave_party", self.imports)
        self.assertIn("brave_profile", self.imports)
        self.assertIn("brave_town", self.imports)

        self.assertTrue({"CmdArcade", "CmdArcadeSubmit"} <= self.imports["brave_arcade"])
        self.assertTrue({"CmdAttack", "CmdEnemies", "CmdFight", "CmdFlee", "CmdUse"} <= self.imports["brave_combat"])
        self.assertTrue({"CmdCook", "CmdEat", "CmdFish", "CmdItem", "CmdMap", "CmdMore", "CmdReel", "CmdRest", "CmdTravel"} <= self.imports["brave_explore"])
        self.assertIn("CmdParty", self.imports["brave_party"])
        self.assertTrue({"CmdBuild", "CmdClass", "CmdGear", "CmdPack", "CmdQuests", "CmdRace", "CmdSheet"} <= self.imports["brave_profile"])
        self.assertTrue(
            {"CmdForge", "CmdPortals", "CmdPray", "CmdRead", "CmdSell", "CmdShift", "CmdShop", "CmdTalk"}
            <= self.imports["brave_town"]
        )

    def test_character_cmdset_registers_extracted_commands(self):
        add_calls = set()
        for node in self.module.body:
            if isinstance(node, ast.ClassDef) and node.name == "CharacterCmdSet":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "at_cmdset_creation":
                        for statement in ast.walk(item):
                            if (
                                isinstance(statement, ast.Call)
                                and isinstance(statement.func, ast.Attribute)
                                and statement.func.attr == "add"
                                and statement.args
                                and isinstance(statement.args[0], ast.Call)
                                and isinstance(statement.args[0].func, ast.Name)
                            ):
                                add_calls.add(statement.args[0].func.id)

        expected = {
            "CmdFight",
            "CmdEnemies",
            "CmdAttack",
            "CmdUse",
            "CmdFlee",
            "CmdBuild",
            "CmdRace",
            "CmdClass",
            "CmdSheet",
            "CmdGear",
            "CmdPack",
            "CmdQuests",
            "CmdFish",
            "CmdReel",
            "CmdCook",
            "CmdEat",
            "CmdItem",
            "CmdTravel",
            "CmdMap",
            "CmdMore",
            "CmdRest",
            "CmdArcade",
            "CmdArcadeSubmit",
            "CmdParty",
            "CmdShop",
            "CmdSell",
            "CmdShift",
            "CmdForge",
            "CmdPortals",
            "CmdPray",
            "CmdTalk",
            "CmdRead",
        }
        self.assertTrue(expected <= add_calls)
