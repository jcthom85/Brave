import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character


class DummyCharacter:
    def __init__(self, *, race_key, class_key="warrior", level=1):
        self.db = SimpleNamespace(
            brave_race=race_key,
            brave_class=class_key,
            brave_level=level,
            brave_resources={},
        )

    def get_equipment_bonuses(self):
        return {}

    def get_active_meal_bonuses(self):
        return {}

    def get_active_chapel_bonuses(self):
        return {}


class RacePerkTests(unittest.TestCase):
    def test_human_resolve_adds_all_resource_caps_and_accuracy(self):
        character = DummyCharacter(race_key="human")

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(141, derived["max_hp"])
        self.assertEqual(49, derived["max_mana"])
        self.assertEqual(85, derived["max_stamina"])
        self.assertEqual(74, derived["accuracy"])

    def test_elf_keen_senses_adds_accuracy_and_precision(self):
        character = DummyCharacter(race_key="elf", class_key="mage")

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(78, derived["accuracy"])
        self.assertEqual(10, derived["precision"])

    def test_dwarf_stoneblood_adds_hp_and_armor(self):
        character = DummyCharacter(race_key="dwarf")

        _primary, derived = Character.recalculate_stats(character, restore=True)

        self.assertEqual(167, derived["max_hp"])
        self.assertEqual(27, derived["armor"])

    def test_legacy_half_orc_maps_to_ashborn(self):
        self.assertEqual("ashborn", Character._canonicalize_race_key("half_orc"))

    def test_legacy_halfling_maps_to_mosskin(self):
        self.assertEqual("mosskin", Character._canonicalize_race_key("halfling"))


if __name__ == "__main__":
    unittest.main()
