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

from world.browser_views import build_combat_victory_view


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class CombatVictoryViewTests(unittest.TestCase):
    def test_victory_view_highlights_chapter_close_and_next_fronts(self):
        encounter = SimpleNamespace(db=SimpleNamespace(encounter_title="Ruk the Fence-Cutter"))
        character = SimpleNamespace()

        view = build_combat_victory_view(
            encounter,
            character,
            xp_total=120,
            reward_silver=18,
            reward_items=[],
            progress_messages=[
                "Chapter complete: First Hour Chapter",
                "Town reaction: Mira, Sister Maybelle, Joss, and the Trophy Hall all have something new waiting back in Brambleford.",
                "Trophy added to the hall: Ruk the Fence-Cutter",
                "New fronts open: Bridgework for Joss and What Whispers in the Wood.",
                "Choose a focus: Use quests track <quest> to pick your next lead.",
            ],
        )

        chapter_close = _section(view, "Chapter Close")
        trophy_hall = _section(view, "Trophy Hall")
        where_next = _section(view, "Where Next")

        self.assertIn("Chapter complete: First Hour Chapter", chapter_close.get("lines", []))
        self.assertIn(
            "Town reaction: Mira, Sister Maybelle, Joss, and the Trophy Hall all have something new waiting back in Brambleford.",
            chapter_close.get("lines", []),
        )
        self.assertEqual(
            ["Trophy added to the hall: Ruk the Fence-Cutter"],
            trophy_hall.get("lines", []),
        )
        self.assertEqual(
            [
                "New fronts open: Bridgework for Joss and What Whispers in the Wood.",
                "Choose a focus: Use quests track <quest> to pick your next lead.",
            ],
            where_next.get("lines", []),
        )

    def test_victory_view_surfaces_aftermath_and_reward_tips(self):
        encounter = SimpleNamespace(db=SimpleNamespace(encounter_title="Roadside Howls"))
        character = SimpleNamespace()

        view = build_combat_victory_view(
            encounter,
            character,
            xp_total=70,
            reward_silver=10,
            reward_items=[("wharfside_skewers", 1)],
            progress_messages=[
                "Aftermath: You have seen enough of Goblin Road to feel the town walls fall behind you.",
                "Reward tip: The road is paying in real silver now. If your pack is filling up, sell the junk before the next longer push.",
                "Next lead: Thin the goblin cutters still working along Goblin Road.",
            ],
        )

        aftermath = _section(view, "Aftermath")
        reward_tip = _section(view, "Use Your Take")
        where_next = _section(view, "Where Next")

        self.assertEqual(
            ["Aftermath: You have seen enough of Goblin Road to feel the town walls fall behind you."],
            aftermath.get("lines", []),
        )
        self.assertEqual(
            ["Reward tip: The road is paying in real silver now. If your pack is filling up, sell the junk before the next longer push."],
            reward_tip.get("lines", []),
        )
        self.assertEqual(
            ["Next lead: Thin the goblin cutters still working along Goblin Road."],
            where_next.get("lines", []),
        )


if __name__ == "__main__":
    unittest.main()
