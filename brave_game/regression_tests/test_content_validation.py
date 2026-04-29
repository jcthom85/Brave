import os
import unittest
from dataclasses import replace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content import get_content_registry
from world.content.validation import validate_content_registry


class ContentValidationTests(unittest.TestCase):
    def test_live_registry_validates_cleanly(self):
        errors = validate_content_registry()
        self.assertEqual([], errors)

    def test_validator_reports_cross_domain_reference_errors(self):
        registry = get_content_registry()
        broken_items = replace(
            registry.items,
            starter_consumables=(("missing_item", 1),),
            item_templates={
                **registry.items.item_templates,
                "broken_recipe_note": {
                    "kind": "consumable",
                    "name": "Broken Recipe Note",
                    "use": {"effect_type": "unlock_recipe", "recipe_domain": "cooking", "unlock_recipe": "missing_recipe"},
                },
            },
        )
        broken_quests = replace(
            registry.quests,
            quests={
                **registry.quests.quests,
                "practice_makes_heroes": {
                    **registry.quests.quests["practice_makes_heroes"],
                    "prerequisites": ["missing_quest"],
                    "objectives": [
                        {
                            "type": "collect_item",
                            "item_id": "missing_item",
                            "description": "Collect something impossible.",
                        }
                    ],
                    "rewards": {"items": [{"item": "missing_item", "quantity": 1}]},
                },
            },
        )
        broken_world = replace(
            registry.world,
            exits=[*registry.world.exits, {"id": "broken_exit", "source": "missing_room", "destination": "also_missing", "key": "north"}],
            entities=[*registry.world.entities, {"id": "broken_entity", "location": "missing_room", "key": "Broken", "desc": "Broken."}],
        )
        broken_encounters = replace(
            registry.encounters,
            enemy_templates={
                **registry.encounters.enemy_templates,
                "thorn_rat": {
                    **registry.encounters.enemy_templates["thorn_rat"],
                    "loot": [{"item": "missing_item", "chance": 1.0}],
                },
            },
            room_encounters={
                **registry.encounters.room_encounters,
                "missing_room": [{"key": "broken", "enemies": ["missing_enemy"]}],
            },
            enemy_temperament_overrides={
                **registry.encounters.enemy_temperament_overrides,
                "missing_enemy": "unknown_temperament",
            },
        )
        broken_dialogue = replace(
            registry.dialogue,
            talk_rules={
                **registry.dialogue.talk_rules,
                "town_notice_board": [{"text": "Wrong kind."}],
                "mira_fenleaf": [{"text": "Bad route.", "room_id": "missing_room", "resonance": "void"}],
                "missing_npc": [{"text": "Ghost talk."}],
            },
            static_read_responses={
                **registry.dialogue.static_read_responses,
                "mira_fenleaf": "NPCs should not be static readable.",
                "missing_readable": "Missing entity.",
            },
        )
        broken_systems = replace(
            registry.systems,
            fishing_rods={**registry.systems.fishing_rods, "bad_rod": {"unlock_completed_quests": ["missing_quest"]}},
            fishing_lures={**registry.systems.fishing_lures, "bad_lure": {"attracts": ["missing_item"], "unlock_completed_quests": ["missing_quest"]}},
            fishing_spots={**registry.systems.fishing_spots, "missing_room": {"fish": [{"item": "missing_item"}]},},
            cooking_recipes={**registry.systems.cooking_recipes, "broken_recipe": {"result": "missing_item", "ingredients": {"missing_item": 1}}},
            tinkering_recipes={**registry.systems.tinkering_recipes, "broken_tinker": {"base": "missing_item", "result": "missing_item", "components": {"missing_item": 1}}},
            outfitters_room_id="missing_room",
            forge_room_id="missing_room",
            forge_recipes={**registry.systems.forge_recipes, "missing_source": {"result": "missing_item", "materials": {"missing_item": 1}}},
            portals={**registry.systems.portals, "broken_portal": {"status": "unknown", "entry_room": "missing_room"}},
            trophies={**registry.systems.trophies, "broken_trophy": {"summary": "Missing fields."}},
        )
        broken_registry = replace(registry, items=broken_items, quests=broken_quests, world=broken_world, encounters=broken_encounters, dialogue=broken_dialogue, systems=broken_systems)

        errors = validate_content_registry(broken_registry)

        self.assertTrue(any("Starter consumable references unknown item" in error for error in errors))
        self.assertTrue(any("unlocks unknown cooking recipe" in error for error in errors))
        self.assertTrue(any("has unknown prerequisite" in error for error in errors))
        self.assertTrue(any("collects unknown item" in error for error in errors))
        self.assertTrue(any("rewards unknown item" in error for error in errors))
        self.assertTrue(any("unknown source room" in error for error in errors))
        self.assertTrue(any("unknown location room" in error for error in errors))
        self.assertTrue(any("drops unknown item" in error for error in errors))
        self.assertTrue(any("Encounter table references unknown room" in error for error in errors))
        self.assertTrue(any("references unknown enemy" in error for error in errors))
        self.assertTrue(any("Temperament override references unknown enemy" in error for error in errors))
        self.assertTrue(any("uses unknown temperament" in error for error in errors))
        self.assertTrue(any("Dialogue references unknown talk entity" in error for error in errors))
        self.assertTrue(any("Dialogue talk rules require npc entity kind" in error for error in errors))
        self.assertTrue(any("Dialogue talk rule references unknown room" in error for error in errors))
        self.assertTrue(any("Dialogue talk rule uses unknown resonance" in error for error in errors))
        self.assertTrue(any("Dialogue static read requires readable entity kind" in error for error in errors))
        self.assertTrue(any("Dialogue references unknown readable entity" in error for error in errors))
        self.assertTrue(any("Fishing spot references unknown room" in error for error in errors))
        self.assertTrue(any("references unknown fish item" in error for error in errors))
        self.assertTrue(any("Fishing rod bad_rod is missing a name" in error for error in errors))
        self.assertTrue(any("references unknown unlock quest" in error for error in errors))
        self.assertTrue(any("Fishing lure bad_lure is missing a name" in error for error in errors))
        self.assertTrue(any("references unknown attract item" in error for error in errors))
        self.assertTrue(any("Cooking recipe broken_recipe yields unknown item" in error for error in errors))
        self.assertTrue(any("references unknown ingredient" in error for error in errors))
        self.assertTrue(any("Tinkering recipe broken_tinker yields unknown item" in error for error in errors))
        self.assertTrue(any("references unknown base item" in error for error in errors))
        self.assertTrue(any("references unknown component" in error for error in errors))
        self.assertTrue(any("Commerce references unknown outfitters room" in error for error in errors))
        self.assertTrue(any("Forging references unknown forge room" in error for error in errors))
        self.assertTrue(any("Forge recipe references unknown source item" in error for error in errors))
        self.assertTrue(any("Portal broken_portal uses unknown status" in error for error in errors))
        self.assertTrue(any("Portal broken_portal references unknown entry room" in error for error in errors))
        self.assertTrue(any("Trophy broken_trophy is missing a name" in error for error in errors))
        self.assertTrue(any("Trophy broken_trophy is missing a placeholder" in error for error in errors))

    def test_validator_reports_world_shippability_errors(self):
        registry = get_content_registry()
        broken_world = replace(
            registry.world,
            rooms=[
                *registry.world.rooms,
                {
                    "id": "new_room_0_3",
                    "key": "New Room",
                    "desc": "Test",
                    "map_region": "brambleford",
                    "map_x": 0,
                    "map_y": 3,
                    "safe": False,
                    "zone": "brambleford",
                },
                {
                    "id": "hidden_draft_room",
                    "key": "Hidden Draft Room",
                    "desc": "A finished-sounding room with a valid label that is not connected from the start roots.",
                    "map_region": "brambleford",
                    "map_x": 9,
                    "map_y": 9,
                    "safe": False,
                    "zone": "Brambleford",
                },
                {
                    "id": "hidden_draft_room_exit",
                    "key": "Hidden Draft Exit",
                    "desc": "A second hidden room keeps the draft area from being isolated while remaining unreachable.",
                    "map_region": "brambleford",
                    "map_x": 10,
                    "map_y": 9,
                    "safe": False,
                    "zone": "Brambleford",
                },
                {
                    "id": "waivered_isolated_room",
                    "key": "Waivered Isolated Room",
                    "desc": "A finished isolated room that explicitly opts out of graph shipping checks.",
                    "map_region": "brambleford",
                    "map_x": 11,
                    "map_y": 9,
                    "safe": False,
                    "validation": {"allow_isolated": True},
                    "zone": "Brambleford",
                },
            ],
            exits=[
                *registry.world.exits,
                {
                    "id": "hidden_draft_room_to_exit",
                    "source": "hidden_draft_room",
                    "destination": "hidden_draft_room_exit",
                    "key": "east",
                },
                {
                    "id": "hidden_draft_room_exit_to_room",
                    "source": "hidden_draft_room_exit",
                    "destination": "hidden_draft_room",
                    "key": "west",
                },
            ],
        )
        broken_registry = replace(registry, world=broken_world)

        errors = validate_content_registry(broken_registry)

        self.assertTrue(any("Room new_room_0_3 uses a placeholder id" in error for error in errors))
        self.assertTrue(any("Room new_room_0_3 uses a placeholder key" in error for error in errors))
        self.assertTrue(any("Room new_room_0_3 uses a placeholder or too-short description" in error for error in errors))
        self.assertTrue(any("Room new_room_0_3 is isolated without validation.allow_isolated" in error for error in errors))
        self.assertTrue(any("Room hidden_draft_room is unreachable from live start roots" in error for error in errors))
        self.assertTrue(any("Map region brambleford has inconsistent zone label casing" in error for error in errors))
        self.assertFalse(any("waivered_isolated_room" in error for error in errors))
