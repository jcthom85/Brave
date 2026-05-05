import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content.preview import (
    preview_boss_gate,
    preview_character_config,
    preview_class,
    preview_cooking_recipe,
    preview_dialogue,
    preview_encounter,
    preview_forge_recipe,
    preview_item,
    preview_portal,
    preview_quest,
    preview_race,
    preview_readable,
    preview_room,
    preview_room_encounters,
    preview_enemy,
    preview_roaming_party,
)


class ContentPreviewTests(unittest.TestCase):
    def test_preview_room_includes_entities_and_exits(self):
        preview = preview_room("brambleford_town_green")

        self.assertEqual("brambleford_town_green", preview["room"]["id"])
        self.assertTrue(any(entity["id"] == "town_notice_board" for entity in preview["entities"]))
        self.assertTrue(preview["exits"])
        self.assertTrue(any("aliases" in exit_data for exit_data in preview["exits"]))
        self.assertIn("incoming_exits", preview)
        self.assertIn("related", preview)
        self.assertTrue(any("has_reverse_exit" in exit_data for exit_data in preview["exits"]))
        self.assertIn("activities", preview["related"])
        self.assertIn("boss_gates", preview["related"])
        self.assertIn("fishing_spot", preview["related"])
        self.assertIn("quest_links", preview["related"])
        notice_board = next(entity for entity in preview["entities"] if entity["id"] == "town_notice_board")
        self.assertIn("aliases", notice_board)
        self.assertIn("desc", notice_board)

    def test_preview_dialogue_resolves_room_and_quest_links(self):
        preview = preview_dialogue("captain_harl_rowan")

        self.assertEqual("captain_harl_rowan", preview["entity"]["id"])
        self.assertIn("room", preview)
        self.assertEqual("brambleford_training_yard", preview["room"]["id"])
        self.assertTrue(preview["quest_links"])
        self.assertTrue(any(link["quest_key"] == "practice_makes_heroes" for link in preview["quest_links"]))
        self.assertEqual("brambleford_training_yard", preview["linked_content"]["room"]["room_id"])

    def test_preview_readable_resolves_room_context(self):
        preview = preview_readable("barrow_marker_stone")

        self.assertEqual("barrow_marker_stone", preview["entity"]["id"])
        self.assertIn("text", preview)
        self.assertIn("room", preview)
        self.assertEqual("readable", preview["linked_content"]["entity_kind"])

    def test_preview_quest_resolves_region_and_objectives(self):
        preview = preview_quest("practice_makes_heroes")

        self.assertEqual("Brambleford", preview["region"])
        self.assertEqual("Practice Makes Heroes", preview["quest"]["title"])
        self.assertTrue(preview["objectives"])
        self.assertEqual("talk_to_npc", preview["objectives"][0]["type"])
        self.assertEqual("Captain Harl Rowan", preview["objectives"][0]["npc_name"])
        self.assertTrue(preview["route"])
        self.assertIn("linked_content", preview)
        self.assertTrue(preview["linked_content"]["entities"])
        self.assertIn("prerequisite_links", preview)

    def test_preview_item_resolves_derived_metadata(self):
        preview = preview_item("innkeepers_fishpie")

        self.assertEqual("innkeepers_fishpie", preview["template_id"])
        self.assertEqual("consumable", preview["category"])
        self.assertEqual("eat", preview["use_profile"]["verb"])
        self.assertTrue(preview["quest_links"])
        self.assertIn("cooking_links", preview)
        self.assertIn("tinkering_links", preview)
        self.assertIn("fishing_links", preview)
        self.assertIn("links", preview)
        self.assertIn("placement_hints", preview)

    def test_preview_item_reports_enemy_loot_backlinks(self):
        preview = preview_item("bandit_mark")

        self.assertTrue(preview["enemy_loot_links"])
        self.assertTrue(any(link["template_key"] == "bandit_raider" for link in preview["enemy_loot_links"]))
        self.assertIn("enemy_loot", preview["links"])

    def test_preview_class_resolves_progression_entries(self):
        preview = preview_class("warrior")

        self.assertEqual("warrior", preview["class_key"])
        self.assertTrue(preview["progression"])
        self.assertIn("Iron Will", preview["max_level_passives"])
        self.assertIn("Shield Bash", preview["max_level_actions"])
        self.assertIn("ability_links", preview)
        self.assertIn("implemented_status", preview)
        self.assertIn("missing_progression", preview)
        self.assertIn("progression_summary", preview)

    def test_preview_race_includes_defaults(self):
        preview = preview_race("human")

        self.assertEqual("human", preview["race_key"])
        self.assertEqual("human", preview["starting_race"])
        self.assertTrue(preview["is_starting_race"])
        self.assertIn("strength", preview["primary_stats"])
        self.assertIn("bonus_summary", preview)
        self.assertIn("perk_effect_summary", preview)
        self.assertIn("race_tutorial_hint", preview)

    def test_preview_character_config_includes_xp_curve(self):
        preview = preview_character_config()

        self.assertEqual("human", preview["starting_race"])
        self.assertEqual("warrior", preview["starting_class"])
        self.assertEqual("Warrior", preview["starting_class_name"])
        self.assertEqual("Human", preview["starting_race_name"])
        self.assertEqual(10, preview["max_level"])
        self.assertIn("2", [str(key) for key in preview["xp_for_level"].keys()])
        self.assertIn("slice_class_links", preview)
        self.assertIn("xp_curve_summary", preview)
        self.assertIn("missing_slice_classes", preview)

    def test_preview_encounter_summarizes_enemy_stack(self):
        preview = preview_encounter("goblin_road_wolf_turn", "wolf_turn_pack")

        self.assertEqual("wolf_turn_pack", preview["encounter"]["key"])
        self.assertEqual(2, len(preview["enemies"]))
        self.assertGreater(preview["total_xp"], 0)

    def test_preview_room_encounters_includes_combat_context(self):
        preview = preview_room_encounters("goblin_road_wolf_turn")

        self.assertTrue(preview["encounters"])
        entry = preview["encounters"][0]
        self.assertIn("total_xp", entry)
        self.assertIn("rank", entry["enemy_details"][0])
        self.assertIn("quest_links", entry)
        self.assertIn("boss_gates", entry)

    def test_preview_enemy_includes_loot_and_usage_links(self):
        preview = preview_enemy("bandit_raider")

        self.assertTrue(preview["loot_links"])
        self.assertIn("quest_links", preview)
        self.assertIn("room_encounters", preview)

    def test_preview_roaming_party_resolves_start_room_context(self):
        preview = preview_roaming_party("blackreed_patrol")

        self.assertEqual("blackreed_patrol", preview["party_key"])
        self.assertTrue(preview["start_room_name"])
        self.assertIn("region_matches_start", preview)
        self.assertTrue(preview["enemies"])

    def test_preview_forge_recipe_resolves_material_names(self):
        preview = preview_forge_recipe("militia_blade")

        self.assertEqual("Militia Blade", preview["source_name"])
        self.assertEqual("Ironroot Longblade", preview["result_name"])
        self.assertTrue(preview["materials"])

    def test_preview_portal_reports_missing_live_portal(self):
        self.assertIsNone(preview_portal("lower_lanternworks"))

    def test_preview_systems_resolve_cross_links(self):
        cooking = preview_cooking_recipe("crisped_perch_plate")
        gate = preview_boss_gate("ruk_fence_cutter")

        self.assertEqual("crisped_perch_plate", cooking["recipe_key"])
        self.assertTrue(cooking["ingredients"])
        self.assertEqual("crisped_perch_plate", cooking["result_template_id"])
        self.assertIn("unlock_items", cooking)
        self.assertEqual("ruk_fence_cutter", gate["gate_key"])
        self.assertEqual("ruk_fence_cutter", gate["boss_enemy_key"])
        self.assertIn("encounter", gate)
        self.assertTrue(gate["linked_exits"])

    def test_preview_fishing_spot_resolves_tackle_and_behaviors(self):
        from world.content.preview import preview_fishing_spot

        preview = preview_fishing_spot("blackfen_approach_reedflats")

        self.assertEqual("blackfen_approach_reedflats", preview["room"]["id"])
        self.assertTrue(preview["fish"])
        self.assertIn("item_name", preview["fish"][0])
        self.assertIn("behavior", preview["fish"][0])
        self.assertIn("recommended_rods", preview)
        self.assertIn("recommended_lures", preview)
