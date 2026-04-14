import importlib.util
import os
import sys
import textwrap
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

_ORIGINAL_MODULES = {
    name: sys.modules.get(name)
    for name in (
        "evennia.utils.evmenu",
        "evennia.utils.utils",
        "typeclasses.characters",
        "world.browser_panels",
    )
}

evmenu_stub = types.ModuleType("evennia.utils.evmenu")
evmenu_stub.EvMenu = object
sys.modules["evennia.utils.evmenu"] = evmenu_stub

utils_stub = types.ModuleType("evennia.utils.utils")
utils_stub.dedent = textwrap.dedent
sys.modules["evennia.utils.utils"] = utils_stub

characters_stub = types.ModuleType("typeclasses.characters")
characters_stub.Character = type("Character", (), {"default_description": ""})
sys.modules["typeclasses.characters"] = characters_stub

browser_panels_stub = types.ModuleType("world.browser_panels")
browser_panels_stub.send_webclient_event = lambda *args, **kwargs: None
sys.modules["world.browser_panels"] = browser_panels_stub

CHARGEN_PATH = Path(__file__).resolve().parents[1] / "world" / "chargen.py"
spec = importlib.util.spec_from_file_location("_chargen_under_test", CHARGEN_PATH)
assert spec and spec.loader
chargen_module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(chargen_module)
finally:
    for name, module in _ORIGINAL_MODULES.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


_format_bonus_line = chargen_module._format_bonus_line
_set_class = chargen_module._set_class
_set_race = chargen_module._set_race
get_resume_chargen_step = chargen_module.get_resume_chargen_step


class DummyAccount:
    def __init__(self, state=None):
        self.db = SimpleNamespace(brave_chargen=state or {})


class DummyCaller:
    def __init__(self, account):
        self.account = account


class ChargenFlowTests(unittest.TestCase):
    def test_new_draft_starts_at_name_step(self):
        account = DummyAccount()

        self.assertEqual("menunode_choose_name", get_resume_chargen_step(account))

    def test_race_selection_stays_on_race_step_until_continue(self):
        account = DummyAccount({"name": "Aria", "race": None, "class": None})
        caller = DummyCaller(account)

        next_step = _set_race(caller, race_key="elf")

        self.assertEqual("menunode_choose_race", next_step)
        self.assertEqual("elf", account.db.brave_chargen["race"])

    def test_class_selection_stays_on_class_step_until_review(self):
        account = DummyAccount({"name": "Aria", "race": "elf", "class": None})
        caller = DummyCaller(account)

        next_step = _set_class(caller, class_key="warrior")

        self.assertEqual("menunode_choose_class", next_step)
        self.assertEqual("warrior", account.db.brave_chargen["class"])

    def test_bonus_line_includes_derived_trait_bonuses(self):
        rendered = _format_bonus_line({"armor": 1, "max_hp": 2})

        self.assertIn("+1 Armor", rendered)
        self.assertIn("+2 HP", rendered)


if __name__ == "__main__":
    unittest.main()
