"""Validation helpers for Brave content domains.

The current pass validates cross-domain references across registry-backed
character, item, quest, world, and encounter content. This keeps content
migration safe before broader creator tooling is introduced.
"""

from world.ability_icons import ALLOWED_ABILITY_ICON_ROLES, ALLOWED_PASSIVE_ICON_ROLES
from world.content import get_content_registry
from world.genders import VALID_BRAVE_GENDERS, normalize_brave_gender


def validate_content_registry(registry=None):
    registry = registry or get_content_registry()
    errors = []

    _validate_character_content(registry, errors)
    _validate_item_content(registry, errors)
    _validate_quest_content(registry, errors)
    _validate_world_content(registry, errors)
    _validate_encounter_content(registry, errors)
    _validate_dialogue_content(registry, errors)
    _validate_systems_content(registry, errors)

    return errors


def _validate_character_content(registry, errors):
    characters = registry.characters
    items = registry.items

    if characters.starting_race not in characters.races:
        errors.append(f"Unknown starting race: {characters.starting_race}")
    if characters.starting_class not in characters.classes:
        errors.append(f"Unknown starting class: {characters.starting_class}")

    for class_key in characters.vertical_slice_classes:
        if class_key not in characters.classes:
            errors.append(f"Vertical-slice class missing from class catalog: {class_key}")

    for class_key, class_data in characters.classes.items():
        for _level, ability_name in class_data.get("progression", []):
            ability_key = characters.ability_key(ability_name)
            if ability_key in characters.ability_library:
                continue
            if ability_key in characters.passive_ability_bonuses:
                continue
            errors.append(f"Class {class_key} references unknown progression ability: {ability_name}")

    for ability_key, ability_data in characters.ability_library.items():
        icon_role = ability_data.get("icon_role")
        if icon_role and icon_role not in ALLOWED_ABILITY_ICON_ROLES:
            errors.append(
                f"Ability {ability_key} uses unknown icon_role: {icon_role}"
            )

    for passive_key, passive_data in characters.passive_ability_bonuses.items():
        icon_role = passive_data.get("icon_role")
        if icon_role and icon_role not in ALLOWED_PASSIVE_ICON_ROLES:
            errors.append(
                f"Passive {passive_key} uses unknown icon_role: {icon_role}"
            )

    for class_key, loadout in items.starter_loadouts.items():
        if class_key not in characters.classes:
            errors.append(f"Starter loadout references unknown class: {class_key}")
        for slot, template_id in loadout.items():
            if slot not in items.equipment_slots:
                errors.append(f"Starter loadout for {class_key} uses unknown slot: {slot}")
            if template_id not in items.item_templates:
                errors.append(f"Starter loadout for {class_key} references unknown item: {template_id}")


def _validate_item_content(registry, errors):
    items = registry.items

    for template_id, item_data in items.item_templates.items():
        slot = item_data.get("slot")
        if slot and slot not in items.equipment_slots:
            errors.append(f"Item {template_id} uses unknown equipment slot: {slot}")
        use = dict(item_data.get("use") or {})
        if use.get("effect_type") == "unlock_recipe":
            recipe_domain = str(use.get("recipe_domain") or "cooking").lower()
            recipe_key = str(use.get("unlock_recipe") or "").lower()
            if recipe_domain == "cooking":
                if recipe_key not in registry.systems.cooking_recipes:
                    errors.append(f"Item {template_id} unlocks unknown cooking recipe: {recipe_key}")
            elif recipe_domain == "tinkering":
                if recipe_key not in registry.systems.tinkering_recipes:
                    errors.append(f"Item {template_id} unlocks unknown tinkering recipe: {recipe_key}")
            else:
                errors.append(f"Item {template_id} uses unknown recipe domain: {recipe_domain}")

    for template_id, _quantity in items.starter_consumables:
        if template_id not in items.item_templates:
            errors.append(f"Starter consumable references unknown item: {template_id}")


def _validate_quest_content(registry, errors):
    items = registry.items
    quests = registry.quests

    for quest_key in quests.starting_quests:
        if quest_key not in quests.quests:
            errors.append(f"Starting quest missing from quest catalog: {quest_key}")

    for quest_key, definition in quests.quests.items():
        for prereq in definition.get("prerequisites", []):
            if prereq not in quests.quests:
                errors.append(f"Quest {quest_key} has unknown prerequisite: {prereq}")

        for reward in definition.get("rewards", {}).get("items", []):
            template_id = reward.get("item")
            if template_id and template_id not in items.item_templates:
                errors.append(f"Quest {quest_key} rewards unknown item: {template_id}")

        for objective in definition.get("objectives", []):
            if objective.get("type") != "collect_item":
                continue
            template_id = objective.get("item_id")
            if template_id and template_id not in items.item_templates:
                errors.append(f"Quest {quest_key} collects unknown item: {template_id}")


def _validate_world_content(registry, errors):
    world = registry.world
    room_ids = {room.get("id") for room in world.rooms}

    for exit_data in world.exits:
        if exit_data.get("source") not in room_ids:
            errors.append(f"Exit {exit_data.get('id')} has unknown source room: {exit_data.get('source')}")
        if exit_data.get("destination") not in room_ids:
            errors.append(f"Exit {exit_data.get('id')} has unknown destination room: {exit_data.get('destination')}")

    for entity_data in world.entities:
        if entity_data.get("location") not in room_ids:
            errors.append(f"Entity {entity_data.get('id')} has unknown location room: {entity_data.get('location')}")


def _validate_encounter_content(registry, errors):
    items = registry.items
    world = registry.world
    encounters = registry.encounters
    room_ids = {room.get("id") for room in world.rooms}

    for template_key, template in encounters.enemy_templates.items():
        if template.get("gender") and normalize_brave_gender(template.get("gender")) not in VALID_BRAVE_GENDERS:
            errors.append(f"Enemy {template_key} uses an invalid gender: {template.get('gender')}")
        for drop in template.get("loot", []):
            item_id = drop.get("item")
            if item_id and item_id not in items.item_templates:
                errors.append(f"Enemy {template_key} drops unknown item: {item_id}")

    for room_id, encounter_list in encounters.room_encounters.items():
        if room_id not in room_ids:
            errors.append(f"Encounter table references unknown room: {room_id}")
        for encounter in encounter_list:
            encounter_key = encounter.get("key") or "unknown"
            for template_key in encounter.get("enemies", []):
                if template_key not in encounters.enemy_templates:
                    errors.append(f"Encounter {room_id}/{encounter_key} references unknown enemy: {template_key}")

    for template_key, temperament in encounters.enemy_temperament_overrides.items():
        if template_key not in encounters.enemy_templates:
            errors.append(f"Temperament override references unknown enemy: {template_key}")
        if temperament not in encounters.temperament_labels:
            errors.append(f"Temperament override for {template_key} uses unknown temperament: {temperament}")

    for party_key, party in encounters.roaming_parties.items():
        region = party.get("region")
        start_room = party.get("start_room")
        encounter = party.get("encounter") or {}
        enemies = list(encounter.get("enemies") or [])

        if not region:
            errors.append(f"Roaming party {party_key} is missing a region")
        if not start_room:
            errors.append(f"Roaming party {party_key} is missing a start room")
        if start_room and start_room not in room_ids:
            errors.append(f"Roaming party {party_key} references unknown start room: {start_room}")
        if start_room and start_room in room_ids:
            room = world.get_room(start_room)
            if room and room.get("map_region") != region:
                errors.append(f"Roaming party {party_key} start room is outside its region: {start_room} -> {region}")
        if int(party.get("interval", 0) or 0) <= 0:
            errors.append(f"Roaming party {party_key} must have a positive interval")
        if int(party.get("respawn_delay", 0) or 0) < 0:
            errors.append(f"Roaming party {party_key} uses a negative respawn delay")
        if not encounter.get("title"):
            errors.append(f"Roaming party {party_key} is missing an encounter title")
        if not enemies:
            errors.append(f"Roaming party {party_key} has no enemies")
        for template_key in enemies:
            if template_key not in encounters.enemy_templates:
                errors.append(f"Roaming party {party_key} references unknown enemy: {template_key}")


def _validate_dialogue_content(registry, errors):
    world = registry.world
    dialogue = registry.dialogue
    entity_by_id = {entity.get("id"): entity for entity in world.entities}
    known_resonances = {"fantasy", "tech"}

    for entity in world.entities:
        if entity.get("kind") != "npc":
            continue
        gender = normalize_brave_gender(entity.get("gender"))
        if gender not in VALID_BRAVE_GENDERS:
            errors.append(f"NPC entity is missing a valid gender: {entity.get('id')}")

    for entity_id, rules in dialogue.talk_rules.items():
        entity = entity_by_id.get(entity_id)
        if not entity:
            errors.append(f"Dialogue references unknown talk entity: {entity_id}")
            continue
        if entity.get("kind") != "npc":
            errors.append(f"Dialogue talk rules require npc entity kind: {entity_id}")

        for index, rule in enumerate(rules, start=1):
            if "text" not in rule or not rule.get("text"):
                errors.append(f"Dialogue talk rule missing text: {entity_id}#{index}")
            room_id = rule.get("room_id")
            if room_id and not registry.world.get_room(room_id):
                errors.append(f"Dialogue talk rule references unknown room: {entity_id}#{index} -> {room_id}")
            resonance = rule.get("resonance")
            if resonance and resonance not in known_resonances:
                errors.append(f"Dialogue talk rule uses unknown resonance: {entity_id}#{index} -> {resonance}")

    for entity_id in dialogue.static_read_responses:
        entity = entity_by_id.get(entity_id)
        if not entity:
            errors.append(f"Dialogue references unknown readable entity: {entity_id}")
            continue
        if entity.get("kind") != "readable":
            errors.append(f"Dialogue static read requires readable entity kind: {entity_id}")


def _validate_systems_content(registry, errors):
    items = registry.items
    quests = registry.quests
    world = registry.world
    systems = registry.systems
    room_ids = {room.get("id") for room in world.rooms}

    for rod_key, rod in systems.fishing_rods.items():
        if not rod.get("name"):
            errors.append(f"Fishing rod {rod_key} is missing a name")
        for quest_key in rod.get("unlock_completed_quests", []) or []:
            if quest_key not in quests.quests:
                errors.append(f"Fishing rod {rod_key} references unknown unlock quest: {quest_key}")

    for lure_key, lure in systems.fishing_lures.items():
        if not lure.get("name"):
            errors.append(f"Fishing lure {lure_key} is missing a name")
        for item_id in lure.get("attracts", []):
            if item_id not in items.item_templates:
                errors.append(f"Fishing lure {lure_key} references unknown attract item: {item_id}")
        for quest_key in lure.get("unlock_completed_quests", []) or []:
            if quest_key not in quests.quests:
                errors.append(f"Fishing lure {lure_key} references unknown unlock quest: {quest_key}")

    for behavior_key, behavior in systems.fishing_behaviors.items():
        if behavior.get("pattern") not in {"sine", "linear", "burst", "dart", "drag", "snag"}:
            errors.append(f"Fish behavior {behavior_key} has an unknown pattern: {behavior.get('pattern')}")

    for room_id, spot in systems.fishing_spots.items():
        if room_id not in room_ids:
            errors.append(f"Fishing spot references unknown room: {room_id}")
        for rod_key in spot.get("recommended_rods", []):
            if rod_key not in systems.fishing_rods:
                errors.append(f"Fishing spot {room_id} references unknown rod: {rod_key}")
        for lure_key in spot.get("recommended_lures", []):
            if lure_key not in systems.fishing_lures:
                errors.append(f"Fishing spot {room_id} references unknown lure: {lure_key}")
        for fish in spot.get("fish", []):
            item_id = fish.get("item")
            if item_id and item_id not in items.item_templates:
                errors.append(f"Fishing spot {room_id} references unknown fish item: {item_id}")
            behavior_id = fish.get("behavior_id")
            if behavior_id and behavior_id not in systems.fishing_behaviors:
                errors.append(f"Fishing spot {room_id} references unknown fish behavior: {behavior_id}")

    for recipe_key, recipe in systems.cooking_recipes.items():
        result_id = recipe.get("result")
        if result_id and result_id not in items.item_templates:
            errors.append(f"Cooking recipe {recipe_key} yields unknown item: {result_id}")
        for item_id in recipe.get("ingredients", {}):
            if item_id not in items.item_templates:
                errors.append(f"Cooking recipe {recipe_key} references unknown ingredient: {item_id}")

    for recipe_key, recipe in systems.tinkering_recipes.items():
        result_id = recipe.get("result")
        if result_id and result_id not in items.item_templates:
            errors.append(f"Tinkering recipe {recipe_key} yields unknown item: {result_id}")
        base_id = recipe.get("base")
        if base_id and base_id not in items.item_templates:
            errors.append(f"Tinkering recipe {recipe_key} references unknown base item: {base_id}")
        for item_id in recipe.get("components", {}):
            if item_id not in items.item_templates:
                errors.append(f"Tinkering recipe {recipe_key} references unknown component: {item_id}")

    if systems.outfitters_room_id and systems.outfitters_room_id not in room_ids:
        errors.append(f"Commerce references unknown outfitters room: {systems.outfitters_room_id}")

    if systems.forge_room_id and systems.forge_room_id not in room_ids:
        errors.append(f"Forging references unknown forge room: {systems.forge_room_id}")

    for source_id, recipe in systems.forge_recipes.items():
        if source_id not in items.item_templates:
            errors.append(f"Forge recipe references unknown source item: {source_id}")
            continue
        result_id = recipe.get("result")
        if result_id not in items.item_templates:
            errors.append(f"Forge recipe {source_id} yields unknown item: {result_id}")
        source_slot = items.item_templates.get(source_id, {}).get("slot")
        result_slot = items.item_templates.get(result_id, {}).get("slot")
        if source_slot and result_slot and source_slot != result_slot:
            errors.append(f"Forge recipe {source_id} changes equipment slot: {source_slot} -> {result_slot}")
        for item_id in recipe.get("materials", {}):
            if item_id not in items.item_templates:
                errors.append(f"Forge recipe {source_id} references unknown material: {item_id}")

    for portal_key, portal in systems.portals.items():
        status = portal.get("status")
        if status not in systems.portal_status_labels:
            errors.append(f"Portal {portal_key} uses unknown status: {status}")
        entry_room = portal.get("entry_room")
        if entry_room and entry_room not in room_ids:
            errors.append(f"Portal {portal_key} references unknown entry room: {entry_room}")

    for trophy_key, trophy in systems.trophies.items():
        if not trophy.get("name"):
            errors.append(f"Trophy {trophy_key} is missing a name")
        if not trophy.get("placeholder"):
            errors.append(f"Trophy {trophy_key} is missing a placeholder")
