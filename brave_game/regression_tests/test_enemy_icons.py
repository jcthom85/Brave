import os
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content import get_content_registry
from world.enemy_icons import get_enemy_icon_name


class EnemyIconTests(unittest.TestCase):
    def test_every_enemy_template_gets_a_real_icon(self):
        content = get_content_registry()
        enemy_templates = content.encounters.enemy_templates

        for key, template in sorted(enemy_templates.items()):
            with self.subTest(key=key):
                icon = get_enemy_icon_name(key, template)
                self.assertTrue(icon)
                self.assertNotEqual("warning", icon)

    def test_known_templates_map_to_expected_icons(self):
        content = get_content_registry()
        enemy_templates = content.encounters.enemy_templates

        expectations = {
            "road_wolf": "wolf-head",
            "goblin_sneak": "daggers",
            "goblin_hexer": "crystal-wand",
            "captain_varn_blackreed": "knight-helmet",
            "hollow_lantern": "lantern-flame",
            "salvage_drone": "robot-arm",
            "skeletal_soldier": "crossed-bones",
            "thorn_rat": "tooth",
        }

        for key, expected in expectations.items():
            with self.subTest(key=key):
                self.assertEqual(expected, get_enemy_icon_name(key, enemy_templates[key]))
