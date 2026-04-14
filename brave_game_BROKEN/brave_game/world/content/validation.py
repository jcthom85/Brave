"""Validation helpers for Brave content domains.

The current pass validates cross-domain references across registry-backed
character, item, quest, world, and encounter content. This keeps content
migration safe before broader creator tooling is introduced.
"""

from world.content import get_content_registry


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
        if not str(class_data.get("icon") or "").strip():
            errors.append(f"Class {class_key} is missing a material icon")
        for _level, ability_name in class_data.get("progression", []):
            ability_key = characters.ability_key(ability_name)
            if ability_key in characters.ability_library:
                continue
            if ability_key in characters.passive_ability_bonuses:
                continue
            errors.append(f"Class {class_key} references unknown progression ability: {ability_name}")

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


def _validate_dialogue_content(registry, errors):
    world = registry.world
    dialogue = registry.dialogue
    entity_by_id = {entity.get("id"): entity for entity in world.entities}
    known_resonances = {"fantasy", "tech"}

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
    world = registry.world
    systems = registry.systems
    room_ids = {room.get("id") for room in world.rooms}

    for room_id, spot in systems.fishing_spots.items():
        if room_id not in room_ids:
            errors.append(f"Fishing spot references unknown room: {room_id}")
        for fish in spot.get("fish", []):
            item_id = fish.get("item")
            if item_id and item_id not in items.item_templates:
                errors.append(f"Fishing spot {room_id} references unknown fish item: {item_id}")

    for recipe_key, recipe in systems.cooking_recipes.items():
        result_id = recipe.get("result")
        if result_id and result_id not in items.item_templates:
            errors.append(f"Cooking recipe {recipe_key} yields unknown item: {result_id}")
        for item_id in recipe.get("ingredients", {}):
            if item_id not in items.item_templates:
                errors.append(f"Cooking recipe {recipe_key} references unknown ingredient: {item_id}")

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
