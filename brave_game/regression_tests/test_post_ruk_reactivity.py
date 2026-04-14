import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.interactions import get_entity_response


class DummyEntity:
    def __init__(self, entity_id, kind):
        self.db = SimpleNamespace(brave_entity_id=entity_id, brave_entity_kind=kind)


class DummyCharacter:
    def __init__(self, quest_states):
        self.db = SimpleNamespace(
            brave_quests=quest_states,
            brave_resources={},
            brave_derived_stats={},
            brave_xp=1,
        )
        self.location = SimpleNamespace(db=SimpleNamespace(brave_resonance="fantasy", brave_room_id="brambleford_town_green"))

    def can_customize_build(self):
        return False


def _completed(quest_key):
    return {quest_key: {"status": "completed", "objectives": []}}


class PostRukReactivityTests(unittest.TestCase):
    def test_post_ruk_mentors_offer_distinct_guidance(self):
        character = DummyCharacter(_completed("ruk_the_fence_cutter"))

        mira = get_entity_response(character, DummyEntity("mira_fenleaf", "npc"), "talk")
        maybelle = get_entity_response(character, DummyEntity("sister_maybelle", "npc"), "talk")
        joss = get_entity_response(character, DummyEntity("joss_veller", "npc"), "talk")
        mayor = get_entity_response(character, DummyEntity("mayor_elric_thorne", "npc"), "talk")
        alden = get_entity_response(character, DummyEntity("brother_alden", "npc"), "talk")

        self.assertIn("south trail", mira)
        self.assertIn("woods south of the gate", maybelle)
        self.assertIn("pattern instead of the symptom", joss)
        self.assertIn("west lantern line", mayor)
        self.assertIn("Help Maybelle steady the south trail first", alden)

    def test_notice_board_marks_post_ruk_follow_up(self):
        character = DummyCharacter(_completed("ruk_the_fence_cutter"))
        board = get_entity_response(character, DummyEntity("town_notice_board", "readable"), "read")

        self.assertIn("Ruk is dead. The road might breathe again.", board)
        self.assertIn("Maybelle wants capable hands on the south trail", board)
        self.assertIn("Mayor and observatory both expect the town's next trouble", board)


if __name__ == "__main__":
    unittest.main()
