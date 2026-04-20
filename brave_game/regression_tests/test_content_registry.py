import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content import get_content_registry


class DummyInventoryCharacter:
    def __init__(self, inventory):
        self.db = SimpleNamespace(brave_inventory=list(inventory))


class ContentRegistryTests(unittest.TestCase):
    def test_character_registry_loads_from_pack_file(self):
        registry = get_content_registry()
        pack_path = Path(registry.characters.source_path)
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertIn("human", registry.characters.races)
        self.assertIn("warrior", registry.characters.classes)
        self.assertIn("strike", registry.characters.ability_library)
        self.assertEqual(tuple(payload["primary_stats"]), registry.characters.primary_stats)
        self.assertEqual(payload["races"]["human"]["name"], registry.characters.races["human"]["name"])
        self.assertEqual(payload["classes"]["warrior"]["name"], registry.characters.classes["warrior"]["name"])

    def test_split_unlocked_abilities_matches_existing_progression_shape(self):
        registry = get_content_registry()
        actions, passives, unknown = registry.characters.split_unlocked_abilities("warrior", 9)
        self.assertIn("Shield Bash", actions)
        self.assertIn("Battle Cry", actions)
        self.assertIn("Iron Will", passives)
        self.assertIn("Bulwark", passives)
        self.assertEqual([], unknown)

    def test_passive_bonus_aggregation_runs_through_registry(self):
        registry = get_content_registry()
        bonuses = registry.characters.get_passive_ability_bonuses("mage", 10)
        self.assertEqual(14, bonuses["max_mana"])
        self.assertEqual(5, bonuses["spell_power"])
        self.assertEqual(2, bonuses["accuracy"])

    def test_item_registry_loads_from_pack_file(self):
        registry = get_content_registry()
        pack_path = Path(registry.items.source_path)
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual("Militia Blade", registry.items.get("militia_blade")["name"])
        self.assertEqual(tuple(payload["equipment_slots"]), registry.items.equipment_slots)
        self.assertEqual(payload["item_templates"]["militia_blade"]["name"], registry.items.get("militia_blade")["name"])
        self.assertEqual(payload["bonus_labels"]["armor"], registry.items.bonus_labels["armor"])

    def test_item_registry_helpers_run_against_pack_backed_data(self):
        registry = get_content_registry()
        character = DummyInventoryCharacter([
            {"template": "riverlight_chowder", "quantity": 1},
            {"template": "militia_blade", "quantity": 1},
        ])
        self.assertEqual("equipment", registry.items.get_item_category("militia_blade"))
        self.assertEqual("consumable", registry.items.get_item_category("riverlight_chowder"))
        self.assertEqual("eat", registry.items.get_item_use_profile("riverlight_chowder", context="combat")["verb"])
        self.assertEqual("riverlight_chowder", registry.items.match_inventory_item(character, "chowder", context="combat"))
        self.assertIn("Armor", registry.items.format_bonus_summary({"bonuses": {"armor": 4}}))

    def test_quest_registry_loads_from_pack_file(self):
        registry = get_content_registry()
        pack_path = Path(registry.quests.source_path)
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual("practice_makes_heroes", registry.quests.starting_quests[0])
        self.assertEqual("Brambleford", registry.quests.get_quest_region("practice_makes_heroes"))
        self.assertEqual("Practice Makes Heroes", registry.quests.get("practice_makes_heroes")["title"])
        self.assertEqual(payload["starting_quests"], registry.quests.starting_quests)
        self.assertEqual(payload["quest_regions"], registry.quests.quest_regions)
        self.assertEqual(payload["quests"]["practice_makes_heroes"]["title"], registry.quests.get("practice_makes_heroes")["title"])

    def test_class_progression_rewards_are_anchored_in_live_quest_content(self):
        registry = get_content_registry()
        expected_rewards = {
            "roadside_howls": "hawkcaller_whistle",
            "ruk_the_fence_cutter": "boar_keeper_charm",
            "bridgework_for_joss": "stormlance_codex",
            "herbs_for_sister_maybelle": "crowfeather_rite",
            "lanterns_at_dusk": "mercy_votive",
            "the_knight_without_rest": "cinder_vigil_tablet",
            "miretooths_claim": "serpent_scale_manual",
        }

        for quest_key, item_id in expected_rewards.items():
            rewards = registry.quests.get(quest_key).get("rewards", {}).get("items", [])
            self.assertIn(item_id, [reward.get("item") for reward in rewards], msg=quest_key)

    def test_world_registry_loads_from_pack_file(self):
        registry = get_content_registry()
        pack_path = Path(registry.world.source_path)
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["rooms"][0]["id"], registry.world.rooms[0]["id"])
        self.assertTrue(registry.world.get_room("brambleford_town_green"))
        self.assertTrue(registry.world.get_entity("mayor_elric_thorne"))
        self.assertEqual(payload["entities"][0]["id"], registry.world.entities[0]["id"])

    def test_encounter_registry_loads_from_pack_file(self):
        registry = get_content_registry()
        pack_path = Path(registry.encounters.source_path)
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["enemy_templates"]["thorn_rat"]["name"], registry.encounters.get_enemy_template("thorn_rat")["name"])
        self.assertEqual(payload["room_encounters"]["goblin_road_wolf_turn"][0]["key"], registry.encounters.get_room_encounters("goblin_road_wolf_turn")[0]["key"])
        self.assertEqual("Wary", registry.encounters.get_enemy_temperament_label("wary"))
        self.assertEqual("wary", registry.encounters.get_enemy_temperament("thorn_rat"))
        self.assertGreaterEqual(registry.encounters.get_enemy_rank("captain_varn_blackreed"), 2)
        self.assertEqual("Dangerous", registry.encounters.get_relative_threat_label(2, 2))

    def test_dialogue_registry_loads_from_pack_file(self):
        registry = get_content_registry()
        pack_path = Path(registry.dialogue.source_path)
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["talk_rules"]["mira_fenleaf"][0]["text"], registry.dialogue.get_talk_rules("mira_fenleaf")[0]["text"])
        self.assertEqual(payload["static_read_responses"]["dawn_bell"], registry.dialogue.get_static_read_response("dawn_bell"))
        self.assertEqual((), registry.dialogue.get_talk_rules("missing_entity"))
        self.assertIsNone(registry.dialogue.get_static_read_response("missing_entity"))

    def test_systems_registry_loads_from_pack_file(self):
        registry = get_content_registry()
        pack_path = Path(registry.systems.source_path)
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["activities"]["cozy_bonus"], registry.systems.cozy_bonus)
        self.assertEqual(payload["portals"]["portals"]["junkyard_planet"]["name"], registry.systems.get_portal("junkyard_planet")["name"])
        self.assertEqual("Stable", registry.systems.get_portal_status_label("stable"))
        self.assertIn("brambleford_hobbyists_wharf", registry.systems.fishing_spots)
        self.assertIn("drowned_weir_drowned_causeway", registry.systems.fishing_spots)
        self.assertIn("loaner_pole", registry.systems.fishing_rods)
        self.assertIn("glass_spinner", registry.systems.fishing_lures)
        self.assertIn("plain_hook", registry.systems.fishing_lures)
        self.assertIn("field_bandage_roll", registry.systems.tinkering_recipes)
        self.assertIn("militia_blade", registry.systems.forge_recipes)
        self.assertIn("junkyard_beacon_core", registry.systems.trophies)

    def test_recipe_unlock_items_are_distributed_beyond_fishing(self):
        registry = get_content_registry()
        goblin_hexer_loot = [entry["item"] for entry in registry.encounters.get_enemy_template("goblin_hexer")["loot"]]
        pot_king_loot = [entry["item"] for entry in registry.encounters.get_enemy_template("grubnak_the_pot_king")["loot"]]
        barrow_wisp_loot = [entry["item"] for entry in registry.encounters.get_enemy_template("barrow_wisp")["loot"]]
        goblin_cutter_loot = [entry["item"] for entry in registry.encounters.get_enemy_template("goblin_cutter")["loot"]]
        hollow_wisp_loot = [entry["item"] for entry in registry.encounters.get_enemy_template("hollow_wisp")["loot"]]
        drowned_warder_loot = [entry["item"] for entry in registry.encounters.get_enemy_template("drowned_warder")["loot"]]

        self.assertIn("veskas_pitchfire_pattern", goblin_hexer_loot)
        self.assertIn("grease_stained_supper_note", pot_king_loot)
        self.assertIn("purity_salts_formula", barrow_wisp_loot)
        self.assertIn("latchwire_ward_pattern", goblin_cutter_loot)
        self.assertIn("lockfin_skillet_note", hollow_wisp_loot)
        self.assertIn("fenlight_talisman_pattern", drowned_warder_loot)
