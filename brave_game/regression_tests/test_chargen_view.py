import os
import sys
import types
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda state: "menunode_choose_name"
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules["world.chargen"] = chargen_stub

from world.browser_views import build_chargen_view


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyAccount:
    def get_available_character_slots(self):
        return 3


class ChargenViewTests(unittest.TestCase):
    def test_name_step_renders_inline_form_payload(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_choose_name", "name": "Aria"})

        self.assertEqual("chargen", view.get("variant"))
        form = _section(view, "Character Name")
        self.assertEqual("form", form.get("kind"))
        self.assertEqual("character_name", form.get("field_name"))
        self.assertEqual("Aria", form.get("value"))
        self.assertEqual("Save And Continue", form.get("submit_label"))
        self.assertEqual("raw", form.get("submit_mode"))


if __name__ == "__main__":
    unittest.main()
