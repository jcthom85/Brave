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
    def __init__(self, quests=None, tracked=None, tutorial=None):
        self.db = SimpleNamespace(
            brave_quests=quests or {},
            brave_tracked_quest=tracked,
            brave_tutorial=tutorial,
            brave_tutorial_current_step=None,
        )
        self.location = None


class JournalViewTests(unittest.TestCase):
    def test_journal_view_groups_focus_active_and_archive(self):
        active_key = STARTING_QUESTS[0]
        completed_key = STARTING_QUESTS[1]
        character = DummyCharacter(
            quests={
                active_key: _quest_state(active_key, "active"),
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
        self.assertEqual("Track one quest in detail, scan the active roster, and keep finished work archived below.", view.get("subtitle"))

        focus = _section(view, "Current Focus")
        active = _section(view, "Active Quests")
        archive = _section(view, "Completed Archive")

        self.assertEqual("entries", focus.get("kind"))
        self.assertEqual("list", active.get("kind"))
        self.assertEqual("list", archive.get("kind"))

        focus_titles = [entry.get("title") for entry in focus.get("items", [])]
        self.assertIn(QUESTS[active_key]["title"], focus_titles)
        self.assertIn("First Steps In Brambleford", focus_titles)
        self.assertTrue(any(item.get("text", "").startswith(QUESTS[active_key]["title"]) for item in active.get("items", [])))
        self.assertTrue(any(item.get("text", "").startswith(QUESTS[completed_key]["title"]) for item in archive.get("items", [])))

    def test_journal_view_keeps_empty_focus_and_archive_sections(self):
        character = DummyCharacter(
            quests={},
            tracked=None,
            tutorial={"status": "inactive", "step": None, "flags": {}},
        )

        view = build_quests_view(character)

        focus = _section(view, "Current Focus")
        active = _section(view, "Active Quests")
        archive = _section(view, "Completed Archive")

        self.assertEqual("No tracked quest", focus.get("items", [])[0].get("title"))
        self.assertEqual("No active quests right now.", active.get("items", [])[0].get("text"))
        self.assertEqual("No completed quests yet.", archive.get("items", [])[0].get("text"))


if __name__ == "__main__":
    unittest.main()
