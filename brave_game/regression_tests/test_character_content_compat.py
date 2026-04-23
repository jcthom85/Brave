import os
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content import get_content_registry
from world.data import character_options


class CharacterContentCompatTests(unittest.TestCase):
    def test_legacy_character_options_refs_live_registry(self):
        registry = get_content_registry().characters

        self.assertIs(character_options.RACES, registry.races)
        self.assertIs(character_options.CLASSES, registry.classes)
        self.assertIs(character_options.ABILITY_LIBRARY, registry.ability_library)
        self.assertIs(character_options.PASSIVE_ABILITY_BONUSES, registry.passive_ability_bonuses)
        self.assertEqual(character_options.VERTICAL_SLICE_CLASSES, registry.vertical_slice_classes)

    def test_druid_progression_matches_live_pack(self):
        actions, passives, unknown = character_options.split_unlocked_abilities("druid", 10)

        self.assertIn("Wolf Form", actions)
        self.assertIn("Bear Form", actions)
        self.assertNotIn("Wild Grace", actions)
        self.assertEqual(
            ["Wild Grace", "Groveheart", "Nature's Memory"],
            passives,
        )
        self.assertEqual([], unknown)


if __name__ == "__main__":
    unittest.main()
