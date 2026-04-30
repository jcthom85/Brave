import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character
from typeclasses.scripts import BraveEncounter


class DummyCharacter:
    def __init__(self, *, class_key, race_key="human", level=1, equipment=None):
        self.db = SimpleNamespace(
            brave_race=race_key,
            brave_class=class_key,
            brave_level=level,
            brave_resources={},
        )
        self._equipment = dict(equipment or {})

    def get_equipment_bonuses(self):
        return dict(self._equipment)

    def get_active_meal_bonuses(self):
        return {}

    def get_active_chapel_bonuses(self):
        return {}


def _stats(class_key, *, race_key="human", level=1, equipment=None):
    character = DummyCharacter(
        class_key=class_key,
        race_key=race_key,
        level=level,
        equipment=equipment,
    )
    _primary, derived = Character.recalculate_stats(character, restore=True)
    atb = BraveEncounter._default_atb_fill_rate(SimpleNamespace(), character=character)
    return derived, atb


class StatBalanceTests(unittest.TestCase):
    def test_rogue_leads_ranger_in_crit_and_speed_across_key_levels(self):
        for race_key in ("human", "elf", "mosskin"):
            for level in (1, 5, 10):
                with self.subTest(race=race_key, level=level):
                    rogue, rogue_atb = _stats("rogue", race_key=race_key, level=level)
                    ranger, ranger_atb = _stats("ranger", race_key=race_key, level=level)

                    self.assertGreater(rogue["crit_chance"], ranger["crit_chance"])
                    self.assertGreater(rogue_atb, ranger_atb)

    def test_human_level_ten_class_envelope_preserves_roles(self):
        rogue, rogue_atb = _stats("rogue", level=10)
        ranger, ranger_atb = _stats("ranger", level=10)
        warrior, warrior_atb = _stats("warrior", level=10)
        mage, mage_atb = _stats("mage", level=10)

        self.assertEqual(18, rogue["crit_chance"])
        self.assertEqual(154, rogue_atb)
        self.assertEqual(14, ranger["crit_chance"])
        self.assertEqual(144, ranger_atb)
        self.assertGreater(warrior["armor"], ranger["armor"])
        self.assertGreater(mage["spell_power"], rogue["spell_power"])
        self.assertLess(warrior_atb, ranger_atb)
        self.assertLess(mage_atb, warrior_atb)

    def test_precision_bonuses_feed_critical_chance(self):
        base, _base_atb = _stats("rogue", level=10)
        precise, _precise_atb = _stats("rogue", level=10, equipment={"precision": 10})

        self.assertEqual(base["precision"] + 10, precise["precision"])
        self.assertEqual(base["crit_chance"] + 2, precise["crit_chance"])

    def test_direct_crit_bonuses_stack_and_clamp(self):
        boosted, _boosted_atb = _stats(
            "rogue",
            race_key="mosskin",
            level=10,
            equipment={"precision": 200, "crit_chance": 100},
        )

        self.assertEqual(50, boosted["crit_chance"])

    def test_mosskin_does_not_erase_rogue_ranger_identity(self):
        rogue, rogue_atb = _stats("rogue", race_key="mosskin", level=10)
        ranger, ranger_atb = _stats("ranger", race_key="mosskin", level=10)

        self.assertEqual(21, rogue["crit_chance"])
        self.assertEqual(17, ranger["crit_chance"])
        self.assertEqual(170, rogue_atb)
        self.assertEqual(160, ranger_atb)


if __name__ == "__main__":
    unittest.main()
