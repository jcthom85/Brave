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


def _entry(section, title):
    for entry in section.get("items", []):
        if entry.get("title") == title:
            return entry
    raise AssertionError(f"Missing entry {title}")


def _pair(section, label):
    for item in section.get("items", []):
        if item.get("label") == label:
            return item
    raise AssertionError(f"Missing pair {label}")


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

    def test_choose_class_step_uses_class_background_icons(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_choose_class", "name": "Aria", "race": "human", "class": "mage"})

        summary = _section(view, "Draft")
        classes = _section(view, "Classes")
        mage_entry = _entry(classes, "Mage")

        self.assertEqual("auto_awesome", _pair(summary, "Class").get("icon"))
        self.assertEqual("class-catalog", classes.get("variant"))
        self.assertEqual("auto_awesome", mage_entry.get("background_icon"))
        self.assertIsNone(mage_entry.get("icon"))
        self.assertIn("Current", [chip.get("label") for chip in mage_entry.get("chips", [])])
        self.assertIn("Starts with: Firebolt, Frost Bind", mage_entry.get("lines", []))
        self.assertIn("First unlock: Arc Spark", mage_entry.get("lines", []))

    def test_choose_race_step_shows_bonus_summary(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_choose_race", "name": "Aria", "race": "elf", "class": "mage"})

        races = _section(view, "Races")
        elf_entry = _entry(races, "Elf")

        self.assertIn("Bonuses: +2 Agility, +1 Intellect, +1 Spirit", elf_entry.get("lines", []))


if __name__ == "__main__":
    unittest.main()
