import os
import sys
import types
import unittest
from pathlib import Path

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda state: (
    "menunode_choose_race"
    if not state.get("race")
    else "menunode_choose_class"
    if not state.get("class")
    else "menunode_choose_name"
    if not state.get("name") or not state.get("gender")
    else "menunode_confirm"
)
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules["world.chargen"] = chargen_stub

from world.browser_views import build_chargen_view
from world.content import get_content_registry

CONTENT = get_content_registry()
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = REPO_ROOT / "brave_game/web/static/webclient/js/plugins/default_out.js"
WEBCLIENT_CSS_PATH = REPO_ROOT / "brave_game/web/static/webclient/css/brave_webclient.css"


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyAccount:
    def get_available_character_slots(self):
        return 3


class ChargenViewTests(unittest.TestCase):
    def test_chargen_hero_places_icon_title_before_logo_and_description(self):
        default_out_source = DEFAULT_OUT_PATH.read_text(encoding="utf-8")
        css_source = WEBCLIENT_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('var titlebarMarkup = ((viewData.title_icon || viewData.title || viewData.back_action)', default_out_source)
        self.assertIn("var wordmarkMarkup = viewData.wordmark ?", default_out_source)
        self.assertIn("var chargenHeroMarkup = titlebarMarkup + wordmarkMarkup + subtitleMarkup;", default_out_source)
        self.assertIn('viewData.variant === "chargen"\n                ? chargenHeroMarkup', default_out_source)
        self.assertIn('icon(viewData.title_icon, "brave-view__title-icon")', default_out_source)
        self.assertIn('body[data-brave-view="chargen"] .brave-view__titlebar', css_source)
        self.assertIn("top: 32px !important;", css_source)

    def test_all_chargen_steps_keep_title_icons(self):
        steps = [
            "menunode_choose_race",
            "menunode_choose_class",
            "menunode_choose_gender",
            "menunode_choose_name",
            "menunode_confirm",
        ]

        for step in steps:
            with self.subTest(step=step):
                view = build_chargen_view(DummyAccount(), {"step": step, "name": "Aria"})
                self.assertTrue(view.get("title"))
                self.assertTrue(view.get("subtitle"))
                self.assertTrue(view.get("title_icon"))

    def test_name_step_renders_inline_form_payload(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_choose_name", "name": "Aria"})

        self.assertEqual("chargen", view.get("variant"))
        form = _section(view, "Identity")
        self.assertEqual("form", form.get("kind"))
        self.assertEqual("character_name", form.get("fields", [])[0].get("field_name"))
        self.assertEqual("Aria", form.get("fields", [])[0].get("value"))
        self.assertEqual("Save And Continue", form.get("submit_label"))
        self.assertEqual("raw", form.get("submit_mode"))
        rules = _section(view, "Rules")
        self.assertEqual("list", rules.get("kind"))

    def test_gender_step_renders_gender_choices(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_choose_gender", "name": "Aria"})

        genders = _section(view, "Gender")
        self.assertEqual({"Male", "Female", "Non-binary"}, {entry.get("title") for entry in genders.get("items", [])})

    def test_class_step_uses_distinct_class_background_icons(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_choose_class", "name": "Aria"})
        classes = _section(view, "Classes")
        entries = classes.get("items", [])
        icons_by_title = {entry.get("title"): entry.get("background_icon") for entry in entries}

        self.assertEqual(
            {
                "Warrior": "heavy-shield",
                "Cleric": "hospital-cross",
                "Ranger": "archer",
                "Mage": "crystal-wand",
                "Rogue": "cloak-and-dagger",
                "Paladin": "bolt-shield",
                "Druid": "sprout-emblem",
            },
            icons_by_title,
        )
        self.assertEqual(len(entries), len({entry.get("background_icon") for entry in entries}))
        self.assertTrue(all(entry.get("hide_icon") for entry in entries))
        ranger_entry = next(entry for entry in entries if entry.get("title") == "Ranger")
        self.assertIn("Companion Bond", [chip.get("label") for chip in ranger_entry.get("chips", [])])

    def test_race_step_uses_distinct_race_background_icons(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_choose_race", "name": "Aria"})
        races = _section(view, "Races")
        entries = races.get("items", [])
        icons_by_title = {entry.get("title"): entry.get("background_icon") for entry in entries}

        self.assertEqual(
            {
                CONTENT.characters.races["human"]["name"]: "player",
                CONTENT.characters.races["elf"]["name"]: "fairy",
                CONTENT.characters.races["dwarf"]["name"]: "anvil",
                CONTENT.characters.races["mosskin"]["name"]: "clover",
                CONTENT.characters.races["ashborn"]["name"]: "horns",
            },
            icons_by_title,
        )
        self.assertEqual(len(entries), len({entry.get("background_icon") for entry in entries}))
        self.assertTrue(all(entry.get("hide_icon") for entry in entries))


if __name__ == "__main__":
    unittest.main()
