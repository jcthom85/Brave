import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.race_perks import (
    adjust_effect_damage,
    adjust_effect_penalty,
    adjust_effect_turns,
    get_atb_fill_rate_bonus,
    get_flee_chance_bonus,
    get_incoming_damage_reduction,
    get_interrupt_recovery_bonus,
    get_wounded_atb_fill_rate_bonus,
    get_wounded_damage_bonus,
)


class DummyCharacter:
    def __init__(self, race_key, *, hp=20, max_hp=40):
        self.db = SimpleNamespace(
            brave_race=race_key,
            brave_resources={"hp": hp},
            brave_derived_stats={"max_hp": max_hp},
        )


class RacePerkEffectTests(unittest.TestCase):
    def test_elf_gets_atb_fill_rate_bonus(self):
        self.assertEqual(6, get_atb_fill_rate_bonus(DummyCharacter("elf")))

    def test_elf_gets_interrupt_recovery_bonus(self):
        self.assertEqual(1, get_interrupt_recovery_bonus(DummyCharacter("elf")))

    def test_mosskin_gets_higher_atb_fill_rate_bonus(self):
        self.assertEqual(8, get_atb_fill_rate_bonus(DummyCharacter("mosskin")))

    def test_dwarf_reduces_poison_turns_and_damage(self):
        dwarf = DummyCharacter("dwarf")

        self.assertEqual(1, adjust_effect_turns(dwarf, "poison", 2))
        self.assertEqual(3, adjust_effect_damage(dwarf, "poison", 4))
        self.assertEqual(1, get_incoming_damage_reduction(dwarf))

    def test_mosskin_reduces_snare_turns(self):
        mosskin = DummyCharacter("mosskin")

        self.assertEqual(1, adjust_effect_turns(mosskin, "snare", 2))
        self.assertEqual(4, adjust_effect_penalty(mosskin, "snare", "accuracy_penalty", 6))
        self.assertEqual(4, adjust_effect_penalty(mosskin, "snare", "dodge_penalty", 6))
        self.assertEqual(3, adjust_effect_penalty(mosskin, "poison", "accuracy_penalty", 5))

    def test_ashborn_gets_damage_bonus_while_wounded(self):
        ashborn = DummyCharacter("ashborn", hp=18, max_hp=40)
        healthy = DummyCharacter("ashborn", hp=30, max_hp=40)
        threshold_edge = DummyCharacter("ashborn", hp=24, max_hp=40)

        self.assertEqual(4, get_wounded_damage_bonus(ashborn))
        self.assertEqual(0, get_wounded_damage_bonus(healthy))
        self.assertEqual(4, get_wounded_damage_bonus(threshold_edge))
        self.assertEqual(10, get_wounded_atb_fill_rate_bonus(ashborn))
        self.assertEqual(0, get_wounded_atb_fill_rate_bonus(healthy))

    def test_human_gets_broad_status_and_flee_support(self):
        human = DummyCharacter("human")

        self.assertEqual(1, adjust_effect_turns(human, "curse", 2))
        self.assertEqual(6, get_flee_chance_bonus(human))


if __name__ == "__main__":
    unittest.main()
