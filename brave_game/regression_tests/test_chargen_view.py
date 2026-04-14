import os
import sys
import types
import unittest
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.browser_views import build_chargen_view


def _next_step(state):
    if not state.get("name"):
        return "menunode_choose_name"
    if not state.get("race"):
        return "menunode_choose_race"
    if not state.get("class"):
        return "menunode_choose_class"
    return "menunode_confirm"


def _build_view(account, state, **kwargs):
    chargen_stub = types.ModuleType("world.chargen")
    chargen_stub.get_next_chargen_step = _next_step
    with patch.dict(sys.modules, {"world.chargen": chargen_stub}):
        return build_chargen_view(account, state, **kwargs)


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
        view = _build_view(DummyAccount(), {"step": "menunode_choose_name", "name": "Aria"})

        self.assertEqual("chargen", view.get("variant"))
        form = _section(view, "Character Name")
        self.assertEqual("form", form.get("kind"))
        self.assertEqual("character_name", form.get("field_name"))
        self.assertEqual("Aria", form.get("value"))
        self.assertEqual("Save And Continue", form.get("submit_label"))
        self.assertEqual("raw", form.get("submit_mode"))
        action_labels = [action.get("label") for action in view.get("actions", [])]
        self.assertNotIn("Name", action_labels)
        self.assertNotIn("Race", action_labels)
        self.assertNotIn("Class", action_labels)
        self.assertIn("Discard", action_labels)
        self.assertIn("Close", action_labels)

    def test_race_step_renders_selectable_cards_with_traits(self):
        view = _build_view(
            DummyAccount(),
            {"step": "menunode_choose_race", "name": "Aria", "race": "elf"},
        )

        actions = [action.get("label") for action in view.get("actions", [])]
        self.assertIn("Continue", actions)
        self.assertIn("Back", actions)
        self.assertNotIn("Name", actions)
        self.assertNotIn("Race", actions)
        self.assertNotIn("Class", actions)

        races = _section(view, "Choose Race")
        elf = next(entry for entry in races.get("items", []) if entry.get("title") == "Elf")
        self.assertTrue(elf.get("selected"))
        self.assertEqual("forest", elf.get("background_icon"))
        self.assertTrue(any("Primary traits:" in line for line in elf.get("lines", [])))
        self.assertTrue(any("Combat traits:" in line for line in elf.get("lines", [])))

    def test_class_step_renders_review_action_and_starter_details(self):
        view = _build_view(
            DummyAccount(),
            {
                "step": "menunode_choose_class",
                "name": "Aria",
                "race": "elf",
                "class": "warrior",
            },
        )

        review_actions = [action for action in view.get("actions", []) if action.get("label") == "Review"]
        self.assertEqual(1, len(review_actions))
        action_labels = [action.get("label") for action in view.get("actions", [])]
        self.assertIn("Back", action_labels)
        self.assertNotIn("Name", action_labels)
        self.assertNotIn("Race", action_labels)
        self.assertNotIn("Class", action_labels)

        classes = _section(view, "Choose Class")
        warrior = next(entry for entry in classes.get("items", []) if entry.get("title") == "Warrior")
        self.assertTrue(warrior.get("selected"))
        self.assertTrue(any("Starts with:" in line for line in warrior.get("lines", [])))
        self.assertTrue(any("Starter gear:" in line for line in warrior.get("lines", [])))


if __name__ == "__main__":
    unittest.main()
