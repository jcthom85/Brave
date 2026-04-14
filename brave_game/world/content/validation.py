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
    _validate_journey_content(registry, errors)

    return errors


def _build_reachable_room_ids(world):
    """Return room ids reachable from the first authored room via exits."""

    room_ids = [room.get("id") for room in world.rooms if room.get("id")]
    if not room_ids:
        return set()

    adjacency = {room_id: set() for room_id in room_ids}
    for exit_data in world.exits:
        source = exit_data.get("source")
        destination = exit_data.get("destination")
        if source in adjacency and destination in adjacency:
            adjacency[source].add(destination)

    start_room_id = room_ids[0]
    for candidate in ("tutorial_wayfarers_yard", "brambleford_town_green"):
        if candidate in adjacency:
            start_room_id = candidate
            break
    reachable = {start_room_id}
    frontier = [start_room_id]
    while frontier:
        room_id = frontier.pop()
        for destination in adjacency.get(room_id, ()):
            if destination in reachable:
                continue
            reachable.add(destination)
            frontier.append(destination)
    return reachable


def _collect_item_sources(registry):
    """Return item ids that can plausibly enter player inventory."""

    items = set()
    items.update(template_id for template_id, _quantity in registry.items.starter_consumables)

    for loadout in registry.items.starter_loadouts.values():
        items.update(loadout.values())

    for quest in registry.quests.quests.values():
        for reward in quest.get("rewards", {}).get("items", []):
            item_id = reward.get("item")
            if item_id:
                items.add(item_id)

    for template in registry.encounters.enemy_templates.values():
        for drop in template.get("loot", []):
            item_id = drop.get("item")
            if item_id:
                items.add(item_id)

    for spot in registry.systems.fishing_spots.values():
        for fish in spot.get("fish", []):
            item_id = fish.get("item")
            if item_id:
                items.add(item_id)

    for recipe in registry.systems.cooking_recipes.values():
        result_id = recipe.get("result")
        if result_id:
            items.add(result_id)

    for recipe in registry.systems.forge_recipes.values():
        result_id = recipe.get("result")
        if result_id:
            items.add(result_id)

    return items


def _encounter_enemy_tags_by_room(registry):
    """Return encounter-supported enemy tags, both globally and by room."""

    global_tags = set()
    room_tags = {}
    encounters = registry.encounters
    for room_id, encounter_list in encounters.room_encounters.items():
        tags = set()
        for encounter in encounter_list:
            for template_key in encounter.get("enemies", []):
                template = encounters.enemy_templates.get(template_key) or {}
                template_tags = set(template.get("tags") or [])
                tags.update(template_tags)
                global_tags.update(template_tags)
        room_tags[room_id] = tags
    return global_tags, room_tags


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
    known_zones = set()

    for room in world.rooms:
        room_id = room.get("id") or "unknown"
        zone = str(room.get("zone", "") or "").strip()
        if not zone:
            errors.append(f"Room {room_id} is missing a zone")
        else:
            known_zones.add(zone)
        if "safe" not in room:
            errors.append(f"Room {room_id} is missing a safe flag")

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
    known_zones = {str(room.get("zone", "") or "").strip() for room in world.rooms if str(room.get("zone", "") or "").strip()}

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
            roam_radius = encounter.get("roam_radius")
            if roam_radius is not None and int(roam_radius) < 0:
                errors.append(f"Encounter {room_id}/{encounter_key} has negative roam_radius: {roam_radius}")
            for zone in encounter.get("allowed_zones", []):
                if zone not in known_zones:
                    errors.append(f"Encounter {room_id}/{encounter_key} uses unknown allowed zone: {zone}")
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

    for trophy_key, trophy in systems.trophies.items():
        if not trophy.get("name"):
            errors.append(f"Trophy {trophy_key} is missing a name")
        if not trophy.get("placeholder"):
            errors.append(f"Trophy {trophy_key} is missing a placeholder")


def _validate_journey_content(registry, errors):
    world = registry.world
    quests = registry.quests

    room_ids = {room.get("id") for room in world.rooms}
    reachable_room_ids = _build_reachable_room_ids(world)
    item_sources = _collect_item_sources(registry)
    enemy_tags, enemy_tags_by_room = _encounter_enemy_tags_by_room(registry)
    entity_ids = {entity.get("id") for entity in world.entities}

    seen_quest_keys = set()
    for quest_key in quests.starting_quests:
        if quest_key in seen_quest_keys:
            errors.append(f"Starting quest list contains duplicate quest: {quest_key}")
        seen_quest_keys.add(quest_key)

    for room_id in sorted(room_ids - reachable_room_ids):
        errors.append(f"Room {room_id} is not reachable from the authored start room")

    for room_id in sorted(set(registry.encounters.room_encounters) - reachable_room_ids):
        errors.append(f"Encounter table is on unreachable room: {room_id}")

    for quest_key, definition in quests.quests.items():
        if quest_key not in quests.starting_quests:
            errors.append(f"Quest {quest_key} is not listed in starting_quests")

        if quest_key not in quests.quest_regions:
            errors.append(f"Quest {quest_key} is missing a quest region")

        for index, objective in enumerate(definition.get("objectives", []), start=1):
            objective_type = objective.get("type")

            if objective_type == "visit_room":
                room_id = objective.get("room_id")
                if room_id and room_id in room_ids and room_id not in reachable_room_ids:
                    errors.append(f"Quest {quest_key} objective {index} visits unreachable room: {room_id}")
                continue

            if objective_type == "defeat_enemy":
                enemy_tag = objective.get("enemy_tag")
                if enemy_tag and enemy_tag not in enemy_tags:
                    errors.append(f"Quest {quest_key} objective {index} has no encounter enemy with tag: {enemy_tag}")
                    continue
                if enemy_tag and not any(
                    enemy_tag in tags and room_id in reachable_room_ids
                    for room_id, tags in enemy_tags_by_room.items()
                ):
                    errors.append(f"Quest {quest_key} objective {index} has no reachable encounter enemy with tag: {enemy_tag}")
                continue

            if objective_type == "collect_item":
                item_id = objective.get("item_id")
                if item_id and item_id in registry.items.item_templates and item_id not in item_sources:
                    errors.append(f"Quest {quest_key} objective {index} collects item with no acquisition source: {item_id}")
                continue

            if objective_type == "talk_entity":
                entity_id = objective.get("entity_id")
                if entity_id and entity_id not in entity_ids:
                    errors.append(f"Quest {quest_key} objective {index} talks to unknown entity: {entity_id}")
                continue

            errors.append(f"Quest {quest_key} objective {index} uses unsupported objective type: {objective_type}")
