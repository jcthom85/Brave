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
    def __init__(self, completed=None):
        completed = completed or ()
        self.db = SimpleNamespace(
            brave_quests={quest_key: {"status": "completed", "objectives": []} for quest_key in completed},
            brave_resources={},
            brave_derived_stats={},
            brave_xp=5,
            brave_inventory=[],
        )
        self.location = SimpleNamespace(db=SimpleNamespace(brave_resonance="fantasy", brave_room_id="brambleford_town_green"))

    def can_customize_build(self):
        return False


class MidchapterTownReactivityTests(unittest.TestCase):
    def test_mayors_ledger_accumulates_campaign_state(self):
        character = DummyCharacter(
            completed=("greymaws_trail", "the_knight_without_rest", "captain_varn_blackreed", "the_pot_kings_feast")
        )
        ledger = get_entity_response(character, DummyEntity("mayors_ledger", "readable"), "read")

        self.assertIn("Greymaw culled", ledger)
        self.assertIn("Sir Edric laid to rest", ledger)
        self.assertIn("Blackreed removed", ledger)
        self.assertIn("Goblin crown broken", ledger)

    def test_town_trade_surfaces_shift_after_major_victories(self):
        character = DummyCharacter(completed=("greymaws_trail", "captain_varn_blackreed", "the_hollow_lantern"))

        chalkboard = get_entity_response(character, DummyEntity("outfitters_chalkboard", "readable"), "read")
        forge_board = get_entity_response(character, DummyEntity("forge_order_board", "readable"), "read")
        leda = get_entity_response(character, DummyEntity("leda_thornwick", "npc"), "talk")
        torren = get_entity_response(character, DummyEntity("torren_ironroot", "npc"), "talk")

        self.assertIn("WOODS PELTS WANTED AGAIN", chalkboard)
        self.assertIn("RIDGE TRADE ADDENDUM", chalkboard)
        self.assertIn("MARSH COLUMN REOPENED", chalkboard)
        self.assertIn("SOUTH WEIR BRASS", forge_board)
        self.assertIn("drowned lights", leda)
        self.assertIn("drowned line brass", torren)


if __name__ == "__main__":
    unittest.main()
