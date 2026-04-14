import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content import get_content_registry
from world.questing import ensure_starter_quests, get_tracked_quest

CONTENT = get_content_registry()
QUEST_CONTENT = CONTENT.quests


def _completed_state(quest_key):
    definition = QUEST_CONTENT.quests[quest_key]
    objectives = []
    for objective in definition.get("objectives", []):
        required = objective.get("count", 1)
        objectives.append(
            {
                "description": objective["description"],
                "completed": True,
                "progress": required,
                "required": required,
            }
        )
    return {"status": "completed", "objectives": objectives}


class DummyCharacter:
    def __init__(self, quests=None, tracked=None, suppressed=False):
        self.db = SimpleNamespace(
            brave_quests=quests or {},
            brave_tracked_quest=tracked,
            brave_track_suppressed=suppressed,
            brave_inventory=[],
        )
        self.ndb = SimpleNamespace()


class QuestBranchingTests(unittest.TestCase):
    def test_post_ruk_branch_unlocks_do_not_auto_track_one_path(self):
        character = DummyCharacter(
            quests={
                "practice_makes_heroes": _completed_state("practice_makes_heroes"),
                "rats_in_the_kettle": _completed_state("rats_in_the_kettle"),
                "roadside_howls": _completed_state("roadside_howls"),
                "fencebreakers": _completed_state("fencebreakers"),
                "ruk_the_fence_cutter": _completed_state("ruk_the_fence_cutter"),
            },
            tracked="ruk_the_fence_cutter",
        )

        ensure_starter_quests(character)

        self.assertEqual("active", character.db.brave_quests["bridgework_for_joss"]["status"])
        self.assertEqual("active", character.db.brave_quests["what_whispers_in_the_wood"]["status"])
        self.assertIsNone(get_tracked_quest(character))


if __name__ == "__main__":
    unittest.main()
