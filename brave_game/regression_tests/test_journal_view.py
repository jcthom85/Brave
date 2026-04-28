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

from world.browser_views import build_quests_view
from world.data.quests import QUESTS, STARTING_QUESTS


def _quest_state(quest_key, status):
    definition = QUESTS[quest_key]
    objectives = []
    for objective in definition.get("objectives", []):
        required = objective.get("count", 1)
        completed = status == "completed"
        objectives.append(
            {
                "description": objective["description"],
                "completed": completed,
                "progress": required if completed else 0,
                "required": required,
            }
        )
    return {"status": status, "objectives": objectives}


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyCharacter:
    def __init__(self, quests=None, tracked=None, tutorial=None, journal_tab="active"):
        self.db = SimpleNamespace(
            brave_quests=quests or {},
            brave_tracked_quest=tracked,
            brave_journal_tab=journal_tab,
            brave_tutorial=tutorial,
            brave_tutorial_current_step=None,
        )
        self.location = None


class JournalViewTests(unittest.TestCase):
    def test_journal_view_shows_tracked_then_active_regions(self):
        active_key = STARTING_QUESTS[0]
        second_active_key = STARTING_QUESTS[2]
        completed_key = "bridgework_for_joss"
        character = DummyCharacter(
            quests={
                active_key: _quest_state(active_key, "active"),
                second_active_key: _quest_state(second_active_key, "active"),
                completed_key: _quest_state(completed_key, "completed"),
            },
            tracked=active_key,
            tutorial={
                "status": "active",
                "step": "first_steps",
                "flags": {},
            },
        )

        view = build_quests_view(character)

        self.assertEqual("journal", view.get("variant"))
        self.assertEqual("", view.get("eyebrow"))
        self.assertEqual("", view.get("subtitle"))
        self.assertEqual([], view.get("chips"))
        self.assertEqual("Close", view.get("back_action", {}).get("label"))
        self.assertEqual([], view.get("actions", []))
        switcher = view.get("sections", [])[0]
        self.assertEqual("actions", switcher.get("kind"))
        self.assertEqual("switcher", switcher.get("variant"))
        self.assertEqual(["Active", "Completed"], [item.get("label") for item in switcher.get("items", [])])

        tracked = view.get("sections", [])[1]
        goblin_road = _section(view, "Goblin Road")

        self.assertEqual("entries", tracked.get("kind"))
        self.assertEqual("tracked", tracked.get("variant"))
        self.assertTrue(tracked.get("hide_label"))
        self.assertEqual("Lanternfall", tracked.get("items", [])[0].get("title"))
        tutorial_lines = tracked.get("items", [])[0].get("lines", [])
        self.assertIn("check_box_outline_blank", [line.get("icon") for line in tutorial_lines if isinstance(line, dict)])
        self.assertFalse(any(isinstance(line, str) and line.startswith("[") for line in tutorial_lines))
        self.assertEqual("entries", goblin_road.get("kind"))
        self.assertEqual([QUESTS[second_active_key]["title"]], [item.get("title") for item in goblin_road.get("items", [])])
        self.assertEqual([f"Next: {QUESTS[second_active_key]['objectives'][0]['description']}"], goblin_road.get("items", [])[0].get("lines"))

        labels = [section.get("label") for section in view.get("sections", [])]
        self.assertNotIn("Tutorial", labels)
        self.assertNotIn("Completed Quests", labels)

    def test_journal_view_switches_to_completed_regions(self):
        completed_key = STARTING_QUESTS[1]
        later_completed_key = "bridgework_for_joss"
        character = DummyCharacter(
            quests={
                completed_key: _quest_state(completed_key, "completed"),
                later_completed_key: _quest_state(later_completed_key, "completed"),
            },
            tracked=None,
            tutorial={"status": "inactive", "step": None, "flags": {}},
            journal_tab="completed",
        )

        view = build_quests_view(character)

        self.assertEqual("Close", view.get("back_action", {}).get("label"))
        self.assertEqual([], view.get("actions", []))
        self.assertEqual(["Active", "Completed"], [item.get("label") for item in view.get("sections", [])[0].get("items", [])])
        labels = [section.get("label") for section in view.get("sections", [])]
        self.assertEqual(["", "Brambleford", "Junk-Yard Planet"], labels)
        self.assertEqual("entries", view.get("sections", [])[1].get("kind"))

    def test_journal_view_keeps_empty_states(self):
        character = DummyCharacter(
            quests={},
            tracked=None,
            tutorial={"status": "inactive", "step": None, "flags": {}},
        )

        view = build_quests_view(character)

        active = _section(view, "Active Quests")
        self.assertEqual("No active quests right now.", active.get("items", [])[0].get("title"))

        character.db.brave_journal_tab = "completed"
        completed = _section(build_quests_view(character), "Completed Quests")
        self.assertEqual("No completed quests yet.", completed.get("items", [])[0].get("title"))


if __name__ == "__main__":
    unittest.main()
