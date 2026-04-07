"""Preview helpers for Brave creator tooling."""

from __future__ import annotations

from world.content.registry import get_content_registry


def preview_room(room_id, registry=None):
    registry = registry or get_content_registry()
    room = registry.world.get_room(room_id)
    if not room:
        return None

    exits = [
        {
            "id": exit_data.get("id"),
            "key": exit_data.get("key"),
            "destination": exit_data.get("destination"),
            "destination_name": (registry.world.get_room(exit_data.get("destination")) or {}).get("key"),
        }
        for exit_data in registry.world.exits
        if exit_data.get("source") == room_id
    ]
    entities = [
        {
            "id": entity.get("id"),
            "key": entity.get("key"),
            "kind": entity.get("kind"),
        }
        for entity in registry.world.entities
        if entity.get("location") == room_id
    ]
    encounters = [
        {
            "key": encounter.get("key"),
            "title": encounter.get("title"),
            "enemy_count": len(encounter.get("enemies", [])),
        }
        for encounter in registry.encounters.get_room_encounters(room_id)
    ]
    return {
        "room": room,
        "exits": exits,
        "entities": entities,
        "encounters": encounters,
    }


def preview_race(race_key, registry=None):
    registry = registry or get_content_registry()
    race = registry.characters.races.get(race_key)
    if not race:
        return None
    return {
        "race_key": race_key,
        "race": race,
        "primary_stats": list(registry.characters.primary_stats),
        "starting_race": registry.characters.starting_race,
    }



def preview_class(class_key, registry=None):
    registry = registry or get_content_registry()
    class_data = registry.characters.classes.get(class_key)
    if not class_data:
        return None

    progression = []
    for unlock_level, ability_name in class_data.get("progression", []):
        key = registry.characters.ability_key(ability_name)
        ability = registry.characters.get_ability(key)
        passive = registry.characters.get_passive(key)
        progression.append(
            {
                "level": unlock_level,
                "name": ability_name,
                "ability_key": key,
                "entry_type": "action" if ability else "passive" if passive else "unknown",
                "ability": ability,
                "passive": passive,
            }
        )

    actions, passives, unknown = registry.characters.split_unlocked_abilities(class_key, registry.characters.max_level)
    return {
        "class_key": class_key,
        "class": class_data,
        "progression": progression,
        "max_level_actions": actions,
        "max_level_passives": passives,
        "unknown_progression_entries": unknown,
    }



def preview_character_config(registry=None):
    registry = registry or get_content_registry()
    return {
        "primary_stats": list(registry.characters.primary_stats),
        "starting_race": registry.characters.starting_race,
        "starting_class": registry.characters.starting_class,
        "max_level": registry.characters.max_level,
        "vertical_slice_classes": list(registry.characters.vertical_slice_classes),
        "xp_for_level": dict(registry.characters.xp_for_level),
        "implemented_ability_keys": sorted(registry.characters.implemented_ability_keys),
        "ability_count": len(registry.characters.ability_library),
        "passive_count": len(registry.characters.passive_ability_bonuses),
    }


def preview_item(template_id, registry=None):
    registry = registry or get_content_registry()
    item = registry.items.get(template_id)
    if not item:
        return None

    forge_recipe = registry.systems.forge_recipes.get(template_id)
    quests = []
    for quest_key, quest in registry.quests.quests.items():
        objective_match = any(objective.get("item_id") == template_id for objective in quest.get("objectives", []))
        reward_match = any(reward.get("item") == template_id for reward in quest.get("rewards", {}).get("items", []))
        if objective_match or reward_match:
            quests.append({
                "quest_key": quest_key,
                "title": quest.get("title"),
                "used_in_objectives": objective_match,
                "used_in_rewards": reward_match,
            })

    return {
        "template_id": template_id,
        "item": item,
        "category": registry.items.get_item_category(item),
        "use_profile": registry.items.get_item_use_profile(item),
        "bonus_summary": registry.items.format_bonus_summary(item),
        "forge_recipe": forge_recipe,
        "quest_links": quests,
    }


def preview_quest(quest_key, registry=None):
    registry = registry or get_content_registry()
    quest = registry.quests.get(quest_key)
    if not quest:
        return None

    objectives = []
    for objective in quest.get("objectives", []):
        entry = dict(objective)
        item_id = objective.get("item_id")
        if item_id:
            entry["item_name"] = (registry.items.get(item_id) or {}).get("name")
        room_id = objective.get("room_id")
        if room_id:
            entry["room_name"] = (registry.world.get_room(room_id) or {}).get("key")
        objectives.append(entry)

    rewards = []
    for reward in quest.get("rewards", {}).get("items", []):
        reward_entry = dict(reward)
        item_id = reward.get("item")
        if item_id:
            reward_entry["item_name"] = (registry.items.get(item_id) or {}).get("name")
        rewards.append(reward_entry)

    return {
        "quest": quest,
        "region": registry.quests.get_quest_region(quest_key),
        "prerequisites": list(quest.get("prerequisites", [])),
        "objectives": objectives,
        "reward_items": rewards,
    }


def preview_encounter(room_id, encounter_key, registry=None):
    registry = registry or get_content_registry()
    for encounter in registry.encounters.get_room_encounters(room_id):
        if encounter.get("key") != encounter_key:
            continue
        enemies = []
        total_xp = 0
        for template_key in encounter.get("enemies", []):
            template = registry.encounters.get_enemy_template(template_key) or {}
            xp = int(template.get("xp", 0) or 0)
            total_xp += xp
            enemies.append(
                {
                    "template_key": template_key,
                    "name": template.get("name", template_key),
                    "xp": xp,
                    "rank": registry.encounters.get_enemy_rank(template_key, template) if template else None,
                    "temperament": registry.encounters.get_enemy_temperament(template_key, template) if template else None,
                }
            )
        return {
            "room_id": room_id,
            "encounter": encounter,
            "enemies": enemies,
            "total_xp": total_xp,
        }
    return None


def preview_forge_recipe(source_template_id, registry=None):
    registry = registry or get_content_registry()
    recipe = registry.systems.forge_recipes.get(source_template_id)
    if not recipe:
        return None

    source_item = registry.items.get(source_template_id) or {}
    result_item = registry.items.get(recipe.get("result")) or {}
    materials = []
    for template_id, quantity in recipe.get("materials", {}).items():
        materials.append(
            {
                "template_id": template_id,
                "name": (registry.items.get(template_id) or {}).get("name", template_id),
                "quantity": quantity,
            }
        )
    return {
        "source_template_id": source_template_id,
        "source_name": source_item.get("name", source_template_id),
        "result_template_id": recipe.get("result"),
        "result_name": result_item.get("name", recipe.get("result")),
        "silver_cost": recipe.get("silver", 0),
        "materials": materials,
        "text": recipe.get("text", ""),
    }


def preview_dialogue(entity_id, registry=None):
    registry = registry or get_content_registry()
    entity = registry.world.get_entity(entity_id)
    if not entity:
        return None
    return {
        "entity": entity,
        "talk_rules": list(registry.dialogue.get_talk_rules(entity_id)),
    }


def preview_readable(entity_id, registry=None):
    registry = registry or get_content_registry()
    entity = registry.world.get_entity(entity_id)
    if not entity:
        return None
    return {
        "entity": entity,
        "text": registry.dialogue.get_static_read_response(entity_id),
    }


def preview_room_encounters(room_id, registry=None):
    registry = registry or get_content_registry()
    room = registry.world.get_room(room_id)
    if not room:
        return None
    encounters = []
    for encounter in registry.encounters.get_room_encounters(room_id):
        entry = dict(encounter)
        enemies = []
        for template_key in encounter.get("enemies", []):
            template = registry.encounters.get_enemy_template(template_key) or {}
            enemies.append({
                "template_key": template_key,
                "name": template.get("name", template_key),
                "xp": template.get("xp", 0),
            })
        entry["enemy_details"] = enemies
        encounters.append(entry)
    return {"room": room, "encounters": encounters}


def preview_enemy(template_key, registry=None):
    registry = registry or get_content_registry()
    template = registry.encounters.get_enemy_template(template_key)
    if not template:
        return None
    return {
        "template_key": template_key,
        "enemy": template,
        "temperament": registry.encounters.get_enemy_temperament(template_key, template),
        "rank": registry.encounters.get_enemy_rank(template_key, template),
    }
