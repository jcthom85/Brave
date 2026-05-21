"""Preview helpers for Brave creator tooling."""

from __future__ import annotations

from world.content.registry import get_content_registry


def preview_room(room_id, registry=None):
    registry = registry or get_content_registry()
    room = registry.world.get_room(room_id)
    if not room:
        return None

    exits = [dict(exit_data) for exit_data in registry.world.exits if exit_data.get("source") == room_id]
    incoming_exits = [dict(exit_data) for exit_data in registry.world.exits if exit_data.get("destination") == room_id]
    exit_pairs = {
        (exit_data.get("source"), exit_data.get("destination")): exit_data
        for exit_data in registry.world.exits
    }
    for exit_data in exits:
        reverse = exit_pairs.get((exit_data.get("destination"), room_id))
        exit_data["has_reverse_exit"] = bool(reverse)
        exit_data["reverse_exit_id"] = reverse.get("id") if reverse else None
    entities = [dict(entity) for entity in registry.world.entities if entity.get("location") == room_id]
    encounters = [
        {
            "key": encounter.get("key"),
            "title": encounter.get("title"),
            "enemy_count": len(encounter.get("enemies", [])),
        }
        for encounter in registry.encounters.get_room_encounters(room_id)
    ]
    activity_values = room.get("activities", room.get("brave_activities", []))
    if isinstance(activity_values, str):
        activities = [activity_values]
    else:
        activities = list(activity_values or [])
    boss_gates = []
    exit_gate_keys = {
        exit_data.get("boss_gate") or exit_data.get("brave_boss_gate")
        for exit_data in registry.world.exits
        if exit_data.get("source") == room_id or exit_data.get("destination") == room_id
    }
    for gate_key, gate in registry.systems.boss_gates.items():
        gate_rooms = {
            gate.get("trigger_room"),
            gate.get("trigger_room_id"),
            gate.get("entry_room"),
            gate.get("entry_room_id"),
            gate.get("success_room"),
            gate.get("success_room_id"),
            gate.get("failure_room"),
            gate.get("failure_room_id"),
        }
        if room_id in gate_rooms or gate_key in exit_gate_keys:
            boss_gates.append({"gate_key": gate_key, "name": gate.get("name", gate_key), "boss": gate.get("boss_enemy_key") or gate.get("boss") or gate.get("boss_template")})
    quest_links = []
    for quest_key, quest in registry.quests.quests.items():
        objectives = [
            objective
            for objective in quest.get("objectives", [])
            if objective.get("room_id") == room_id
        ]
        if objectives:
            quest_links.append({"quest_key": quest_key, "title": quest.get("title", quest_key), "objective_count": len(objectives)})
    return {
        "room": room,
        "exits": exits,
        "incoming_exits": incoming_exits,
        "entities": entities,
        "encounters": encounters,
        "related": {
            "activities": activities,
            "boss_gates": boss_gates,
            "fishing_spot": registry.systems.fishing_spots.get(room_id),
            "quest_links": quest_links,
        },
    }


def preview_race(race_key, registry=None):
    registry = registry or get_content_registry()
    race = registry.characters.races.get(race_key)
    if not race:
        return None
    bonuses = dict(race.get("bonuses", {}))
    perk_bonuses = dict(race.get("perk_bonuses", {}))
    perk_effects = dict(race.get("perk_effects", {}))
    return {
        "race_key": race_key,
        "race": race,
        "primary_stats": list(registry.characters.primary_stats),
        "starting_race": registry.characters.starting_race,
        "is_starting_race": race_key == registry.characters.starting_race,
        "bonus_summary": [f"{stat}: {value:+g}" for stat, value in sorted(bonuses.items())],
        "perk_effect_summary": [f"{key}: {value:+g}" for key, value in sorted({**perk_bonuses, **perk_effects}.items())],
        "race_tutorial_hint": f"Explain what makes {race.get('name', race_key)} distinct and how its perk changes play.",
    }



def preview_class(class_key, registry=None):
    registry = registry or get_content_registry()
    class_data = registry.characters.classes.get(class_key)
    if not class_data:
        return None

    progression = []
    learn_items_by_ability = {}
    for template_id, item in registry.items.item_templates.items():
        use_profile = registry.items.get_item_use_profile(item) or {}
        ability_key = use_profile.get("learn_ability")
        if ability_key:
            learn_items_by_ability.setdefault(ability_key, []).append({"template_id": template_id, "name": item.get("name", template_id)})
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
                "implemented": key in registry.characters.implemented_ability_keys,
                "ability": ability,
                "passive": passive,
                "learn_items": learn_items_by_ability.get(key, []),
            }
        )

    actions, passives, unknown = registry.characters.split_unlocked_abilities(class_key, registry.characters.max_level)
    ability_links = [
        {
            "level": entry["level"],
            "name": entry["name"],
            "ability_key": entry["ability_key"],
            "entry_type": entry["entry_type"],
            "implemented": entry["implemented"],
            "learn_items": entry["learn_items"],
        }
        for entry in progression
    ]
    return {
        "class_key": class_key,
        "class": class_data,
        "progression": progression,
        "ability_links": ability_links,
        "implemented_status": {entry["ability_key"]: entry["implemented"] for entry in progression},
        "missing_progression": [entry for entry in ability_links if entry["entry_type"] == "unknown"],
        "learn_items": [item for entry in ability_links for item in entry["learn_items"]],
        "progression_summary": [
            f"Level {entry['level']}: {entry['name']} ({entry['entry_type']}{', implemented' if entry['implemented'] else ''})"
            for entry in ability_links
        ],
        "max_level_actions": actions,
        "max_level_passives": passives,
        "unknown_progression_entries": unknown,
    }



def preview_character_config(registry=None):
    registry = registry or get_content_registry()
    ability_names = sorted({ability.get("name", ability_key) for ability_key, ability in registry.characters.ability_library.items()})
    passive_names = sorted({passive.get("name", passive_key) for passive_key, passive in registry.characters.passive_ability_bonuses.items()})
    slice_class_links = [
        {"class_key": class_key, "name": (registry.characters.classes.get(class_key) or {}).get("name", class_key)}
        for class_key in registry.characters.vertical_slice_classes
    ]
    missing_slice_classes = [
        class_key
        for class_key in registry.characters.vertical_slice_classes
        if class_key not in registry.characters.classes
    ]
    return {
        "primary_stats": list(registry.characters.primary_stats),
        "starting_race": registry.characters.starting_race,
        "starting_class": registry.characters.starting_class,
        "starting_race_name": (registry.characters.races.get(registry.characters.starting_race) or {}).get("name", registry.characters.starting_race),
        "starting_class_name": (registry.characters.classes.get(registry.characters.starting_class) or {}).get("name", registry.characters.starting_class),
        "max_level": registry.characters.max_level,
        "vertical_slice_classes": list(registry.characters.vertical_slice_classes),
        "slice_class_links": slice_class_links,
        "missing_slice_classes": missing_slice_classes,
        "xp_for_level": dict(registry.characters.xp_for_level),
        "xp_curve_summary": [
            {"level": level, "xp": xp}
            for level, xp in sorted(registry.characters.xp_for_level.items(), key=lambda item: int(item[0]))
        ],
        "implemented_ability_keys": sorted(registry.characters.implemented_ability_keys),
        "ability_library": dict(registry.characters.ability_library),
        "passive_ability_bonuses": dict(registry.characters.passive_ability_bonuses),
        "ability_count": len(registry.characters.ability_library),
        "passive_count": len(registry.characters.passive_ability_bonuses),
        "ability_names": ability_names,
        "passive_names": passive_names,
    }


def preview_item(template_id, registry=None):
    registry = registry or get_content_registry()
    item = registry.items.get(template_id)
    if not item:
        return None

    forge_recipe = registry.systems.forge_recipes.get(template_id)
    cooking_recipes = [
        {"recipe_key": key, "name": recipe.get("name"), "role": "result" if recipe.get("result") == template_id else "ingredient"}
        for key, recipe in registry.systems.cooking_recipes.items()
        if recipe.get("result") == template_id or template_id in recipe.get("ingredients", {})
    ]
    tinkering_recipes = [
        {
            "recipe_key": key,
            "name": recipe.get("name"),
            "role": "result" if recipe.get("result") == template_id else "base" if recipe.get("base") == template_id else "component",
        }
        for key, recipe in registry.systems.tinkering_recipes.items()
        if recipe.get("result") == template_id or recipe.get("base") == template_id or template_id in recipe.get("components", {})
    ]
    fishing_spots = [
        {"room_id": room_id, "name": spot.get("name"), "chance": fish.get("chance"), "rarity": fish.get("rarity")}
        for room_id, spot in registry.systems.fishing_spots.items()
        for fish in spot.get("fish", [])
        if fish.get("item") == template_id
    ]
    lures = [
        {"lure_key": lure_key, "name": lure.get("name")}
        for lure_key, lure in registry.systems.fishing_lures.items()
        if template_id in lure.get("attracts", [])
    ]
    enemy_loot = [
        {
            "template_key": enemy_key,
            "name": enemy.get("name", enemy_key),
            "chance": loot.get("chance"),
            "quantity": loot.get("quantity", 1),
        }
        for enemy_key, enemy in registry.encounters.enemy_templates.items()
        for loot in enemy.get("loot", [])
        if loot.get("item") == template_id
    ]
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
    unlock_links = []
    use_profile = registry.items.get_item_use_profile(item) or {}
    if use_profile.get("effect_type") == "unlock_recipe":
        domain = use_profile.get("recipe_domain") or "cooking"
        recipe_key = use_profile.get("unlock_recipe")
        unlock_links.append({"kind": "recipe", "domain": domain, "key": recipe_key})
    if use_profile.get("learn_ability"):
        unlock_links.append({"kind": "ability", "key": use_profile.get("learn_ability")})
    if use_profile.get("unlock_companion"):
        unlock_links.append({"kind": "companion", "key": use_profile.get("unlock_companion")})
    if use_profile.get("unlock_oath"):
        unlock_links.append({"kind": "oath", "key": use_profile.get("unlock_oath")})

    placement_hints = []
    if not enemy_loot and item.get("kind") in {"loot", "ingredient"}:
        placement_hints.append("No enemy loot drops reference this item.")
    if not quests:
        placement_hints.append("No quest objective or reward references this item.")
    if item.get("kind") in {"ingredient", "meal"} and not cooking_recipes and not tinkering_recipes:
        placement_hints.append("No cooking or tinkering recipe references this item.")
    if item.get("kind") == "ingredient" and not fishing_spots:
        placement_hints.append("No fishing spot catches this item.")
    links = {
        "quests": quests,
        "enemy_loot": enemy_loot,
        "forge": forge_recipe,
        "cooking": cooking_recipes,
        "tinkering": tinkering_recipes,
        "fishing": fishing_spots,
        "lures": lures,
        "unlocks": unlock_links,
    }

    return {
        "template_id": template_id,
        "item": item,
        "category": registry.items.get_item_category(item),
        "use_profile": use_profile,
        "bonus_summary": registry.items.format_bonus_summary(item),
        "forge_recipe": forge_recipe,
        "cooking_links": cooking_recipes,
        "tinkering_links": tinkering_recipes,
        "fishing_links": fishing_spots,
        "lure_links": lures,
        "enemy_loot_links": enemy_loot,
        "quest_links": quests,
        "unlock_links": unlock_links,
        "placement_hints": placement_hints,
        "links": links,
    }


def preview_quest(quest_key, registry=None):
    registry = registry or get_content_registry()
    quest = registry.quests.get(quest_key)
    if not quest:
        return None

    def _resolve_enemy_tag(tag):
        token = str(tag or "").strip().lower()
        if not token:
            return None
        for template_id, template in registry.encounters.enemy_templates.items():
            tags = {str(entry or "").strip().lower() for entry in template.get("tags", [])}
            if token == template_id.lower() or token in tags:
                return template
        return None

    objectives = []
    linked_rooms = []
    linked_items = []
    linked_enemies = []
    linked_entities = []
    linked_readables = []
    for objective in quest.get("objectives", []):
        entry = dict(objective)
        item_id = objective.get("item_id")
        if item_id:
            entry["item_name"] = (registry.items.get(item_id) or {}).get("name")
            linked_items.append({"template_id": item_id, "name": entry.get("item_name"), "role": "objective"})
        room_id = objective.get("room_id")
        if room_id:
            entry["room_name"] = (registry.world.get_room(room_id) or {}).get("key")
            linked_rooms.append({"room_id": room_id, "name": entry.get("room_name"), "role": "objective"})
        enemy_tag = objective.get("enemy_tag")
        if enemy_tag:
            enemy = _resolve_enemy_tag(enemy_tag) or {}
            entry["enemy_name"] = enemy.get("name")
            linked_enemies.append({"enemy_tag": enemy_tag, "name": entry.get("enemy_name"), "role": "objective"})
        npc_id = objective.get("npc_id")
        if npc_id:
            entity = next((entity for entity in registry.world.entities if entity.get("id") == npc_id), {})
            entry["npc_name"] = entity.get("key")
            linked_entities.append({"entity_id": npc_id, "name": entry.get("npc_name"), "role": "objective", "room_id": entity.get("location")})
        readable_id = objective.get("readable_id")
        if readable_id:
            entity = registry.world.get_entity(readable_id) or {}
            entry["readable_name"] = entity.get("key")
            linked_readables.append({"entity_id": readable_id, "name": entry.get("readable_name"), "role": "objective", "room_id": entity.get("location")})
        objectives.append(entry)

    rewards = []
    for reward in quest.get("rewards", {}).get("items", []):
        reward_entry = dict(reward)
        item_id = reward.get("item")
        if item_id:
            reward_entry["item_name"] = (registry.items.get(item_id) or {}).get("name")
            linked_items.append({"template_id": item_id, "name": reward_entry.get("item_name"), "role": "reward"})
        rewards.append(reward_entry)
    prerequisites = [
        {"quest_key": prereq, "title": (registry.quests.get(prereq) or {}).get("title", prereq)}
        for prereq in quest.get("prerequisites", [])
    ]
    route = []
    for index, objective in enumerate(objectives, start=1):
        target_name = objective.get("room_name") or objective.get("item_name") or objective.get("enemy_name") or objective.get("npc_name") or objective.get("readable_name") or objective.get("room_id") or objective.get("item_id") or objective.get("enemy_tag") or objective.get("npc_id") or objective.get("readable_id") or "No target"
        route.append({"step": index, "type": objective.get("type"), "description": objective.get("description"), "target": target_name})

    return {
        "quest": quest,
        "region": registry.quests.get_quest_region(quest_key),
        "is_starting": quest_key in set(registry.quests.starting_quests),
        "prerequisites": list(quest.get("prerequisites", [])),
        "prerequisite_links": prerequisites,
        "objectives": objectives,
        "reward_items": rewards,
        "route": route,
        "linked_content": {
            "rooms": linked_rooms,
            "items": linked_items,
            "enemies": linked_enemies,
            "entities": linked_entities,
            "readables": linked_readables,
            "prerequisites": prerequisites,
        },
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
        "recipe": recipe,
        "source_name": source_item.get("name", source_template_id),
        "result_template_id": recipe.get("result"),
        "result_name": result_item.get("name", recipe.get("result")),
        "silver_cost": recipe.get("silver", 0),
        "materials": materials,
        "text": recipe.get("text", ""),
    }


def preview_portal(portal_key, registry=None):
    registry = registry or get_content_registry()
    portal = registry.systems.get_portal(portal_key)
    if not portal:
        return None
    entry_room_id = portal.get("entry_room")
    entry_room = registry.world.get_room(entry_room_id) if entry_room_id else None
    return {
        "portal": portal,
        "status_label": registry.systems.get_portal_status_label(portal.get("status")),
        "entry_room_name": entry_room.get("key") if entry_room else None,
    }


def preview_dialogue(entity_id, registry=None):
    registry = registry or get_content_registry()
    entity = registry.world.get_entity(entity_id)
    if not entity:
        return None
    room_id = entity.get("location")
    room = registry.world.get_room(room_id) if room_id else None
    quest_links = []
    for quest_key, quest in registry.quests.quests.items():
        objectives = [
            dict(objective)
            for objective in quest.get("objectives", [])
            if objective.get("npc_id") == entity_id
        ]
        if objectives:
            quest_links.append(
                {
                    "quest_key": quest_key,
                    "title": quest.get("title", quest_key),
                    "region": registry.quests.get_quest_region(quest_key),
                    "objective_count": len(objectives),
                    "objectives": objectives,
                }
            )
    return {
        "entity": entity,
        "room": room,
        "talk_rules": list(registry.dialogue.get_talk_rules(entity_id)),
        "quest_links": quest_links,
        "readable_text": registry.dialogue.get_static_read_response(entity_id),
        "linked_content": {
            "room": {"room_id": room_id, "name": room.get("key")} if room else None,
            "quests": quest_links,
            "has_readable": bool(registry.dialogue.get_static_read_response(entity_id)),
        },
    }


def preview_readable(entity_id, registry=None):
    registry = registry or get_content_registry()
    entity = registry.world.get_entity(entity_id)
    if not entity:
        return None
    room_id = entity.get("location")
    room = registry.world.get_room(room_id) if room_id else None
    quest_links = []
    for quest_key, quest in registry.quests.quests.items():
        objectives = [
            dict(objective)
            for objective in quest.get("objectives", [])
            if objective.get("readable_id") == entity_id
        ]
        if objectives:
            quest_links.append(
                {
                    "quest_key": quest_key,
                    "title": quest.get("title", quest_key),
                    "region": registry.quests.get_quest_region(quest_key),
                    "objective_count": len(objectives),
                    "objectives": objectives,
                }
            )
    return {
        "entity": entity,
        "room": room,
        "text": registry.dialogue.get_static_read_response(entity_id),
        "quest_links": quest_links,
        "linked_content": {
            "room": {"room_id": room_id, "name": room.get("key")} if room else None,
            "entity_kind": entity.get("kind"),
            "quests": quest_links,
        },
    }


def preview_room_encounters(room_id, registry=None):
    registry = registry or get_content_registry()
    room = registry.world.get_room(room_id)
    if not room:
        return None
    quest_links = []
    encounters = []
    for encounter in registry.encounters.get_room_encounters(room_id):
        entry = dict(encounter)
        enemies = []
        total_xp = 0
        encounter_tags = set()
        for template_key in encounter.get("enemies", []):
            template = registry.encounters.get_enemy_template(template_key) or {}
            xp = int(template.get("xp", 0) or 0)
            total_xp += xp
            encounter_tags.update(str(tag or "").strip().lower() for tag in template.get("tags", []))
            encounter_tags.add(template_key.lower())
            enemies.append({
                "template_key": template_key,
                "name": template.get("name", template_key),
                "xp": xp,
                "rank": registry.encounters.get_enemy_rank(template_key, template) if template else None,
                "temperament": registry.encounters.get_enemy_temperament(template_key, template) if template else None,
            })
        entry["enemy_details"] = enemies
        entry["total_xp"] = total_xp
        entry["boss_gates"] = [
            {"gate_key": gate_key, "name": gate.get("name", gate_key), "boss_enemy_key": gate.get("boss_enemy_key")}
            for gate_key, gate in registry.systems.boss_gates.items()
            if gate.get("trigger_room_id") == room_id and gate.get("encounter_key") == encounter.get("key")
        ]
        entry["quest_links"] = []
        for quest_key, quest in registry.quests.quests.items():
            for objective in quest.get("objectives", []):
                enemy_tag = str(objective.get("enemy_tag") or "").strip().lower()
                if objective.get("type") == "defeat_enemy" and enemy_tag and enemy_tag in encounter_tags:
                    link = {"quest_key": quest_key, "title": quest.get("title", quest_key), "enemy_tag": enemy_tag}
                    entry["quest_links"].append(link)
                    quest_links.append(link)
        encounters.append(entry)
    return {"room": room, "encounters": encounters, "quest_links": quest_links}


def preview_enemy(template_key, registry=None):
    registry = registry or get_content_registry()
    template = registry.encounters.get_enemy_template(template_key)
    if not template:
        return None
    room_encounters = [
        {"room_id": room_id, "encounter_key": encounter.get("key"), "title": encounter.get("title")}
        for room_id, encounters in registry.encounters.room_encounters.items()
        for encounter in encounters
        if template_key in encounter.get("enemies", [])
    ]
    roaming_parties = [
        {"party_key": party_key, "title": (party.get("encounter") or {}).get("title")}
        for party_key, party in registry.encounters.roaming_parties.items()
        if template_key in (party.get("encounter") or {}).get("enemies", [])
    ]
    boss_gates = [
        {"gate_key": gate_key, "name": gate.get("name")}
        for gate_key, gate in registry.systems.boss_gates.items()
        if gate.get("boss_enemy_key") == template_key
    ]
    loot_links = [
        {
            "item": drop.get("item"),
            "item_name": (registry.items.get(drop.get("item")) or {}).get("name", drop.get("item")),
            "chance": drop.get("chance"),
            "quantity": drop.get("quantity", 1),
        }
        for drop in template.get("loot", [])
    ]
    enemy_tags = {template_key.lower(), *(str(tag or "").strip().lower() for tag in template.get("tags", []))}
    quest_links = [
        {"quest_key": quest_key, "title": quest.get("title", quest_key), "enemy_tag": str(objective.get("enemy_tag") or "").strip().lower()}
        for quest_key, quest in registry.quests.quests.items()
        for objective in quest.get("objectives", [])
        if objective.get("type") == "defeat_enemy" and str(objective.get("enemy_tag") or "").strip().lower() in enemy_tags
    ]
    return {
        "template_key": template_key,
        "enemy": template,
        "temperament": registry.encounters.get_enemy_temperament(template_key, template),
        "rank": registry.encounters.get_enemy_rank(template_key, template),
        "loot_links": loot_links,
        "quest_links": quest_links,
        "room_encounters": room_encounters,
        "roaming_parties": roaming_parties,
        "boss_gates": boss_gates,
    }


def preview_roaming_party(party_key, registry=None):
    registry = registry or get_content_registry()
    party = registry.encounters.get_roaming_party(party_key)
    if not party:
        return None
    room = registry.world.get_room(party.get("start_room")) if party.get("start_room") else None
    encounter = party.get("encounter") or {}
    enemies = []
    total_xp = 0
    for template_key in encounter.get("enemies", []):
        template = registry.encounters.get_enemy_template(template_key) or {}
        xp = int(template.get("xp", 0) or 0)
        total_xp += xp
        enemies.append({
            "template_key": template_key,
            "name": template.get("name", template_key),
            "xp": xp,
            "rank": registry.encounters.get_enemy_rank(template_key, template) if template else None,
            "temperament": registry.encounters.get_enemy_temperament(template_key, template) if template else None,
        })
    return {
        "party_key": party_key,
        "party": party,
        "start_room_name": room.get("key") if room else None,
        "start_room_region": room.get("map_region") or room.get("zone") if room else None,
        "region_matches_start": bool(room and (room.get("map_region") or room.get("zone")) == party.get("region")),
        "enemies": enemies,
        "total_xp": total_xp,
    }


def _ingredient_details(ingredients, registry):
    return [
        {"template_id": template_id, "name": (registry.items.get(template_id) or {}).get("name", template_id), "quantity": quantity}
        for template_id, quantity in (ingredients or {}).items()
    ]


def preview_cooking_recipe(recipe_key, registry=None):
    registry = registry or get_content_registry()
    recipe = registry.systems.cooking_recipes.get(recipe_key)
    if not recipe:
        return None
    result_id = recipe.get("result")
    unlock_items = [
        {"template_id": template_id, "name": item.get("name", template_id)}
        for template_id, item in registry.items.item_templates.items()
        if (item.get("use") or {}).get("effect_type") == "unlock_recipe"
        and (item.get("use") or {}).get("recipe_domain", "cooking") == "cooking"
        and (item.get("use") or {}).get("unlock_recipe") == recipe_key
    ]
    return {
        "recipe_key": recipe_key,
        "recipe": recipe,
        "result_template_id": result_id,
        "result_name": (registry.items.get(result_id) or {}).get("name", result_id),
        "ingredients": _ingredient_details(recipe.get("ingredients"), registry),
        "cooking_rooms": [room for room in registry.world.rooms if "cooking" in (room.get("activities") or [])],
        "unlock_items": unlock_items,
    }


def preview_tinkering_recipe(recipe_key, registry=None):
    registry = registry or get_content_registry()
    recipe = registry.systems.tinkering_recipes.get(recipe_key)
    if not recipe:
        return None
    result_id = recipe.get("result")
    base_id = recipe.get("base")
    station = recipe.get("station")
    unlock_items = [
        {"template_id": template_id, "name": item.get("name", template_id)}
        for template_id, item in registry.items.item_templates.items()
        if (item.get("use") or {}).get("effect_type") == "unlock_recipe"
        and (item.get("use") or {}).get("recipe_domain") == "tinkering"
        and (item.get("use") or {}).get("unlock_recipe") == recipe_key
    ]
    return {
        "recipe_key": recipe_key,
        "recipe": recipe,
        "base_template_id": base_id,
        "base_name": (registry.items.get(base_id) or {}).get("name", base_id),
        "result_template_id": result_id,
        "result_name": (registry.items.get(result_id) or {}).get("name", result_id),
        "components": _ingredient_details(recipe.get("components"), registry),
        "station_room": registry.world.get_room(station) if station else None,
        "tinkering_rooms": [room for room in registry.world.rooms if "tinkering" in (room.get("activities") or [])],
        "unlock_items": unlock_items,
    }


def preview_fishing_spot(room_id, registry=None):
    registry = registry or get_content_registry()
    spot = registry.systems.fishing_spots.get(room_id)
    if not spot:
        return None
    fish = []
    for entry in spot.get("fish", []):
        item_id = entry.get("item")
        behavior_id = entry.get("behavior_id")
        fish.append({**entry, "item_name": (registry.items.get(item_id) or {}).get("name", item_id), "behavior": registry.systems.fishing_behaviors.get(behavior_id)})
    return {
        "room": registry.world.get_room(room_id),
        "spot": spot,
        "fish": fish,
        "recommended_rods": [{"rod_key": rod_id, "name": (registry.systems.fishing_rods.get(rod_id) or {}).get("name", rod_id)} for rod_id in spot.get("recommended_rods", [])],
        "recommended_lures": [{"lure_key": lure_id, "name": (registry.systems.fishing_lures.get(lure_id) or {}).get("name", lure_id)} for lure_id in spot.get("recommended_lures", [])],
    }


def preview_fishing_rod(rod_key, registry=None):
    registry = registry or get_content_registry()
    rod = registry.systems.fishing_rods.get(rod_key)
    if not rod:
        return None
    spots = [room_id for room_id, spot in registry.systems.fishing_spots.items() if rod_key in spot.get("recommended_rods", [])]
    return {"rod_key": rod_key, "rod": rod, "recommended_for_spots": spots}


def preview_fishing_lure(lure_key, registry=None):
    registry = registry or get_content_registry()
    lure = registry.systems.fishing_lures.get(lure_key)
    if not lure:
        return None
    attracted_items = [
        {"template_id": item_id, "name": (registry.items.get(item_id) or {}).get("name", item_id)}
        for item_id in lure.get("attracts", [])
    ]
    spots = [room_id for room_id, spot in registry.systems.fishing_spots.items() if lure_key in spot.get("recommended_lures", [])]
    return {"lure_key": lure_key, "lure": lure, "attracted_items": attracted_items, "recommended_for_spots": spots}


def preview_fish_behavior(behavior_key, registry=None):
    registry = registry or get_content_registry()
    behavior = registry.systems.fishing_behaviors.get(behavior_key)
    if not behavior:
        return None
    spots = [
        {"room_id": room_id, "fish_item": fish.get("item")}
        for room_id, spot in registry.systems.fishing_spots.items()
        for fish in spot.get("fish", [])
        if fish.get("behavior_id") == behavior_key
    ]
    return {"behavior_key": behavior_key, "behavior": behavior, "used_by_spots": spots}


def preview_boss_gate(gate_key, registry=None):
    registry = registry or get_content_registry()
    gate = registry.systems.boss_gates.get(gate_key)
    if not gate:
        return None
    boss_key = gate.get("boss_enemy_key")
    exits = [exit_data for exit_data in registry.world.exits if exit_data.get("boss_gate") == gate_key or exit_data.get("brave_boss_gate") == gate_key]
    encounter = None
    for entry in registry.encounters.get_room_encounters(gate.get("trigger_room_id")):
        if entry.get("key") == gate.get("encounter_key"):
            encounter = entry
            break
    return {
        "gate_key": gate_key,
        "gate": gate,
        "boss_enemy": registry.encounters.get_enemy_template(boss_key) if boss_key else None,
        "boss_enemy_key": boss_key,
        "encounter": encounter,
        "trigger_room": registry.world.get_room(gate.get("trigger_room_id")),
        "entry_room": registry.world.get_room(gate.get("entry_room_id")),
        "success_room": registry.world.get_room(gate.get("success_room_id")),
        "failure_room": registry.world.get_room(gate.get("failure_room_id")),
        "linked_exits": exits,
    }


def preview_trophy(trophy_key, registry=None):
    registry = registry or get_content_registry()
    trophy = registry.systems.trophies.get(trophy_key)
    if not trophy:
        return None
    return {"trophy_key": trophy_key, "trophy": trophy}


def preview_shop(shop_key, registry=None):
    registry = registry or get_content_registry()
    shop = registry.systems.shops.get(shop_key)
    if not shop:
        return None
    room_id = shop.get("room_id")
    keeper_id = shop.get("keeper_entity_id")
    room = registry.world.get_room(room_id) if room_id else None
    keeper = registry.world.get_entity(keeper_id) if keeper_id else None
    stock = []
    for entry in shop.get("stock", []) or []:
        item_id = entry.get("item")
        item = registry.items.get(item_id) or {}
        stock.append(
            {
                **entry,
                "item_name": item.get("name", item_id),
                "item_kind": item.get("kind"),
            }
        )
    return {
        "shop_key": shop_key,
        "shop": shop,
        "room": room,
        "keeper": keeper,
        "stock": stock,
        "stock_count": len(stock),
        "buys_kinds": list(shop.get("buys_kinds", []) or []),
        "shift_outcome_count": len(shop.get("shift_outcomes", []) or []),
    }
