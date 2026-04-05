import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content.preview import (
    preview_character_config,
    preview_class,
    preview_encounter,
    preview_forge_recipe,
    preview_item,
    preview_portal,
    preview_quest,
    preview_race,
    preview_room,
)


class ContentPreviewTests(unittest.TestCase):
    def test_preview_room_includes_entities_and_exits(self):
        preview = preview_room("brambleford_town_green")

        self.assertEqual("brambleford_town_green", preview["room"]["id"])
        self.assertTrue(any(entity["id"] == "town_notice_board" for entity in preview["entities"]))
        self.assertTrue(preview["exits"])

    def test_preview_quest_resolves_region_and_objectives(self):
        preview = preview_quest("practice_makes_heroes")

        self.assertEqual("Brambleford", preview["region"])
        self.assertEqual("Practice Makes Heroes", preview["quest"]["title"])
        self.assertTrue(preview["objectives"])

    def test_preview_item_resolves_derived_metadata(self):
        preview = preview_item("innkeepers_fishpie")

        self.assertEqual("innkeepers_fishpie", preview["template_id"])
        self.assertEqual("consumable", preview["category"])
        self.assertEqual("eat", preview["use_profile"]["verb"])
        self.assertTrue(preview["quest_links"])

    def test_preview_class_resolves_progression_entries(self):
        preview = preview_class("warrior")

        self.assertEqual("warrior", preview["class_key"])
        self.assertTrue(preview["progression"])
        self.assertIn("Iron Will", preview["max_level_passives"])
        self.assertIn("Shield Bash", preview["max_level_actions"])

    def test_preview_race_includes_defaults(self):
        preview = preview_race("human")

        self.assertEqual("human", preview["race_key"])
        self.assertEqual("human", preview["starting_race"])
        self.assertIn("strength", preview["primary_stats"])

    def test_preview_character_config_includes_xp_curve(self):
        preview = preview_character_config()

        self.assertEqual("human", preview["starting_race"])
        self.assertEqual("warrior", preview["starting_class"])
        self.assertEqual(10, preview["max_level"])
        self.assertIn("2", [str(key) for key in preview["xp_for_level"].keys()])

    def test_preview_encounter_summarizes_enemy_stack(self):
        preview = preview_encounter("goblin_road_wolf_turn", "wolf_turn_pack")

        self.assertEqual("wolf_turn_pack", preview["encounter"]["key"])
        self.assertEqual(2, len(preview["enemies"]))
        self.assertGreater(preview["total_xp"], 0)

    def test_preview_forge_recipe_resolves_material_names(self):
        preview = preview_forge_recipe("militia_blade")

        self.assertEqual("Militia Blade", preview["source_name"])
        self.assertEqual("Ironroot Longblade", preview["result_name"])
        self.assertTrue(preview["materials"])

    def test_preview_portal_resolves_status_label(self):
        preview = preview_portal("junkyard_planet")

        self.assertEqual("Stable", preview["status_label"])
        self.assertEqual("Junk-Yard Planet", preview["portal"]["name"])
