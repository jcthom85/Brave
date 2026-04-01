import os
import sys
import types
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda *args, **kwargs: None
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules.setdefault("world.chargen", chargen_stub)

from world.browser_views import build_talk_list_view, build_talk_view


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyNPC:
    def __init__(self, key, entity_id="mira"):
        self.key = key
        self.location = SimpleNamespace()
        self.db = SimpleNamespace(brave_entity_id=entity_id)


class DummyCharacter:
    def __init__(self):
        self.location = SimpleNamespace(
            db=SimpleNamespace(brave_world="Brave", brave_zone="Brambleford")
        )


class TalkViewTests(unittest.TestCase):
    def test_talk_list_view_renders_browser_picker_entries(self):
        character = DummyCharacter()
        view = build_talk_list_view(character, [DummyNPC("Mira"), DummyNPC("Uncle Pib")])

        self.assertEqual("dialogue-list", view.get("variant"))
        section = _section(view, "Nearby NPCs")
        self.assertEqual("dialogue-list", section.get("variant"))
        self.assertEqual(["Mira", "Uncle Pib"], [item.get("title") for item in section.get("items", [])])
        self.assertEqual(["talk Mira", "talk Uncle Pib"], [item.get("command") for item in section.get("items", [])])

    def test_talk_view_renders_structured_dialogue_actions(self):
        view = build_talk_view(DummyNPC("Leda", entity_id="leda_thornwick"), "Welcome in.\nTake your time.")

        self.assertEqual("dialogue", view.get("variant"))
        self.assertTrue(view.get("preserve_rail"))
        self.assertEqual("NPC", view.get("chips", [])[0].get("label"))
        section = _section(view, "What They Say")
        self.assertEqual("dialogue", section.get("variant"))
        self.assertEqual(["Welcome in.", "Take your time."], section.get("lines"))
        self.assertEqual(["Back", "Open Shop", "Read Nearby Boards"], [item.get("label") for item in view.get("actions", [])])


if __name__ == "__main__":
    unittest.main()
