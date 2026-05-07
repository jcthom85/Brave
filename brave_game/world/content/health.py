"""Creator health/readiness helpers."""

from __future__ import annotations

import json

from world.content.editor import ContentEditor
from world.content.registry import build_content_registry_from_payloads, get_content_registry
from world.content.validation import validate_content_registry


def build_draft_registry(editor=None):
    editor = editor or ContentEditor()
    payloads = {}
    source_paths = {}
    draft_domains = []
    for domain in editor.pack_paths:
        draft_path = editor._path_for(domain, stage="draft")
        live_path = editor._path_for(domain, stage="live")
        source_path = draft_path if draft_path.exists() else live_path
        if draft_path.exists():
            draft_domains.append(domain)
        with source_path.open("r", encoding="utf-8") as handle:
            payloads[domain] = json.load(handle)
        source_paths[domain] = source_path
    return build_content_registry_from_payloads(payloads, source_paths=source_paths), draft_domains


def creator_health_payload(*, stage="draft", registry=None, editor=None):
    editor = editor or ContentEditor()
    if stage == "draft":
        registry, draft_domains = build_draft_registry(editor)
    else:
        registry = registry or get_content_registry()
        draft_domains = [
            domain
            for domain in editor.pack_paths
            if editor._path_for(domain, stage="draft").exists()
        ]
    errors = validate_content_registry(registry)
    readiness = _readiness_sections(registry)
    recommendations = _recommendations(errors, readiness, draft_domains)
    return {
        "ok": not errors,
        "stage": stage,
        "draft_domains": draft_domains,
        "validation_errors": errors,
        "counts": _content_counts(registry),
        "readiness": readiness,
        "recommended_next_actions": recommendations,
    }


def _content_counts(registry):
    return {
        "rooms": len(registry.world.rooms),
        "exits": len(registry.world.exits),
        "entities": len(registry.world.entities),
        "items": len(registry.items.item_templates),
        "quests": len(registry.quests.quests),
        "enemies": len(registry.encounters.enemy_templates),
        "room_encounter_tables": len(registry.encounters.room_encounters),
        "dialogue_entities": len(registry.dialogue.talk_rules),
        "readables": len(registry.dialogue.static_read_responses),
        "cooking_recipes": len(registry.systems.cooking_recipes),
        "tinkering_recipes": len(registry.systems.tinkering_recipes),
        "fishing_spots": len(registry.systems.fishing_spots),
        "boss_gates": len(registry.systems.boss_gates),
        "shops": len(registry.systems.shops),
    }


def _issue(message, href="/creator/"):
    return {"message": message, "href": href}


def _readiness_sections(registry):
    room_ids = {room.get("id") for room in registry.world.rooms}
    entity_by_id = {entity.get("id"): entity for entity in registry.world.entities}
    item_ids = set(registry.items.item_templates)
    sections = {
        "world": [],
        "encounters": [],
        "systems": [],
        "items": [],
        "quests": [],
        "dialogue": [],
        "characters": [],
    }

    exits = registry.world.exits
    exit_pairs = {(exit_data.get("source"), exit_data.get("destination")) for exit_data in exits}
    for exit_data in exits:
        pair = (exit_data.get("destination"), exit_data.get("source"))
        if exit_data.get("source") in room_ids and exit_data.get("destination") in room_ids and pair not in exit_pairs:
            sections["world"].append(_issue(f"Exit {exit_data.get('id')} has no reverse path.", "/creator/world/"))
            if len(sections["world"]) >= 8:
                break

    used_enemies = {
        enemy_key
        for encounters in registry.encounters.room_encounters.values()
        for encounter in encounters
        for enemy_key in encounter.get("enemies", [])
    }
    for enemy_key, enemy in registry.encounters.enemy_templates.items():
        if enemy_key not in used_enemies and "boss" not in {str(tag).lower() for tag in enemy.get("tags", [])}:
            sections["encounters"].append(_issue(f"Enemy {enemy_key} is not used by a room encounter.", "/creator/encounters/"))
            if len(sections["encounters"]) >= 6:
                break

    room_activities = {}
    for room in registry.world.rooms:
        activities = room.get("activities", room.get("brave_activities", [])) or []
        if isinstance(activities, str):
            activities = [activities]
        room_activities[room.get("id")] = set(activities)
    for room_id in registry.systems.fishing_spots:
        if "fishing" not in room_activities.get(room_id, set()):
            sections["systems"].append(_issue(f"Fishing spot {room_id} is missing room activity fishing.", "/creator/systems/"))
    if registry.systems.cooking_recipes and not any("cooking" in values for values in room_activities.values()):
        sections["systems"].append(_issue("Cooking recipes exist but no room advertises cooking activity.", "/creator/world/"))
    if registry.systems.tinkering_recipes and not any("tinkering" in values for values in room_activities.values()):
        sections["systems"].append(_issue("Tinkering recipes exist but no room advertises tinkering activity.", "/creator/world/"))

    referenced_items = set()
    for quest in registry.quests.quests.values():
        referenced_items.update(objective.get("item_id") for objective in quest.get("objectives", []) if objective.get("item_id"))
        referenced_items.update(reward.get("item") for reward in quest.get("rewards", {}).get("items", []) if reward.get("item"))
    for enemy in registry.encounters.enemy_templates.values():
        referenced_items.update(loot.get("item") for loot in enemy.get("loot", []) if loot.get("item"))
    for entity in registry.world.entities:
        for reward in (entity.get("arcade_rewards") or {}).values():
            if isinstance(reward, dict) and reward.get("item"):
                referenced_items.add(reward.get("item"))
    for spot in registry.systems.fishing_spots.values():
        for fish in spot.get("fish", []):
            if fish.get("item"):
                referenced_items.add(fish.get("item"))
    for lure in registry.systems.fishing_lures.values():
        referenced_items.update(lure.get("attracts", []) or [])
    for shop in registry.systems.shops.values():
        for stock in shop.get("stock", []):
            if stock.get("item"):
                referenced_items.add(stock.get("item"))
    for recipe in registry.systems.cooking_recipes.values():
        referenced_items.add(recipe.get("result"))
        referenced_items.update((recipe.get("ingredients") or {}).keys())
    for recipe in registry.systems.tinkering_recipes.values():
        referenced_items.add(recipe.get("base"))
        referenced_items.add(recipe.get("result"))
        referenced_items.update((recipe.get("components") or {}).keys())
    for item_id, item in registry.items.item_templates.items():
        if item.get("kind") in {"loot", "ingredient", "meal"} and item_id not in referenced_items:
            sections["items"].append(_issue(f"Item {item_id} has no quest, loot, or system placement.", "/creator/items/"))
            if len(sections["items"]) >= 8:
                break

    for quest_key, quest in registry.quests.quests.items():
        for objective in quest.get("objectives", []):
            if objective.get("type") == "talk_to_npc" and objective.get("npc_id") not in entity_by_id:
                sections["quests"].append(_issue(f"Quest {quest_key} talks to missing NPC {objective.get('npc_id')}.", "/creator/quests/"))
            if objective.get("type") == "collect_item" and objective.get("item_id") not in item_ids:
                sections["quests"].append(_issue(f"Quest {quest_key} collects missing item {objective.get('item_id')}.", "/creator/quests/"))

    for quest_key, quest in registry.quests.quests.items():
        for objective in quest.get("objectives", []):
            npc_id = objective.get("npc_id")
            if objective.get("type") == "talk_to_npc" and npc_id and not registry.dialogue.get_talk_rules(npc_id):
                sections["dialogue"].append(_issue(f"Quest {quest_key} talks to {npc_id}, but it has no talk rules.", "/creator/dialogue/"))
    for entity in registry.world.entities:
        if entity.get("kind") == "readable" and not registry.dialogue.get_static_read_response(entity.get("id")):
            sections["dialogue"].append(_issue(f"Readable {entity.get('id')} has no readable text.", "/creator/dialogue/"))
            if len(sections["dialogue"]) >= 8:
                break

    for class_key, class_data in registry.characters.classes.items():
        for _level, ability_name in class_data.get("progression", []):
            ability_key = registry.characters.ability_key(ability_name)
            if ability_key not in registry.characters.ability_library and ability_key not in registry.characters.passive_ability_bonuses:
                sections["characters"].append(_issue(f"Class {class_key} references unresolved ability {ability_name}.", "/creator/characters/"))

    return [
        {"key": key, "label": key.replace("_", " ").title(), "issues": issues[:8]}
        for key, issues in sections.items()
    ]


def _recommendations(errors, readiness, draft_domains):
    actions = []
    if errors:
        actions.append({"label": "Fix validation errors before publishing.", "href": "/creator/"})
    if draft_domains:
        actions.append({"label": f"Review draft domains: {', '.join(draft_domains)}.", "href": "/creator/"})
    for section in readiness:
        if section["issues"]:
            actions.append({"label": f"Resolve {section['label']} readiness issues.", "href": section["issues"][0]["href"]})
    if not actions:
        actions.append({"label": "Creator content is ready for a draft publish pass.", "href": "/creator/"})
    return actions[:8]
