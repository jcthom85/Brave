"""Codex-facing Creator contract helpers."""

from __future__ import annotations


REFERENCE_DOMAINS = (
    "rooms",
    "exits",
    "entities",
    "items",
    "classes",
    "races",
    "quests",
    "enemies",
    "enemy-tags",
    "roaming-parties",
    "portals",
    "forge",
    "cooking-recipes",
    "tinkering-recipes",
    "fishing-spots",
    "fishing-rods",
    "fishing-lures",
    "fish-behaviors",
    "boss-gates",
    "trophies",
    "shops",
)


MUTATION_RECIPES = {
    "room": {
        "kind": "room",
        "domain": "world",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["key", "desc"],
        "optional_fields": ["zone", "world", "map_region", "map_x", "map_y", "activities"],
        "reference_hints": ["rooms", "exits"],
        "preview": {"kind": "room", "args": ["target"]},
        "example": {"kind": "room", "target": "new_room_id", "payload": {"key": "New Room", "desc": "A useful playable room.", "zone": "Brambleford", "world": "Brave"}},
    },
    "exit": {
        "kind": "exit",
        "domain": "world",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["key", "source", "destination"],
        "optional_fields": ["aliases", "desc"],
        "reference_hints": ["rooms", "exits"],
        "preview": {"kind": "room", "args": ["source"]},
        "example": {"kind": "exit", "target": "new_exit_id", "payload": {"key": "east", "source": "source_room", "destination": "destination_room"}},
    },
    "entity": {
        "kind": "entity",
        "domain": "world",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["key", "kind", "location"],
        "optional_fields": ["desc", "aliases"],
        "reference_hints": ["rooms", "entities"],
        "preview": {"kind": "room", "args": ["location"]},
        "example": {"kind": "entity", "target": "new_npc", "payload": {"key": "New NPC", "kind": "npc", "location": "brambleford_town_green", "desc": "A grounded character."}},
    },
    "item": {
        "kind": "item",
        "domain": "items",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["kind", "category", "desc", "value", "slot", "stats"],
        "reference_hints": ["items"],
        "preview": {"kind": "item", "args": ["target"]},
        "example": {"kind": "item", "target": "new_item", "payload": {"name": "New Item", "kind": "loot", "desc": "A useful reward."}},
    },
    "race": {
        "kind": "race",
        "domain": "characters",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["desc", "perk", "stat_mods"],
        "reference_hints": ["races"],
        "preview": {"kind": "race", "args": ["target"]},
        "example": {"kind": "race", "target": "new_race", "payload": {"name": "New Race", "desc": "A playable ancestry."}},
    },
    "class": {
        "kind": "class",
        "domain": "characters",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["role", "desc", "progression"],
        "reference_hints": ["classes"],
        "preview": {"kind": "class", "args": ["target"]},
        "example": {"kind": "class", "target": "new_class", "payload": {"name": "New Class", "role": "support", "desc": "A playable class."}},
    },
    "character-config": {
        "kind": "character-config",
        "domain": "characters",
        "target_required": False,
        "payload_type": "object",
        "required_fields": [],
        "optional_fields": ["default_race", "default_class", "starting_items"],
        "reference_hints": ["classes", "races", "items"],
        "preview": {"kind": "character-config", "args": []},
        "example": {"kind": "character-config", "target": "", "payload": {"starting_items": []}},
    },
    "quest": {
        "kind": "quest",
        "domain": "quests",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["title"],
        "optional_fields": ["summary", "region", "objectives", "rewards", "next_step", "quest", "add_starting"],
        "reference_hints": ["quests", "rooms", "entities", "items", "enemies"],
        "preview": {"kind": "quest", "args": ["target"]},
        "example": {"kind": "quest", "target": "new_quest", "payload": {"title": "New Quest", "summary": "A concise quest hook.", "objectives": [], "rewards": {"items": []}}},
    },
    "dialogue": {
        "kind": "dialogue",
        "domain": "dialogue",
        "target_required": True,
        "payload_type": "list",
        "required_fields": [],
        "optional_fields": ["list of dialogue rule objects"],
        "reference_hints": ["entities", "quests"],
        "preview": {"kind": "dialogue", "args": ["target"]},
        "example": {"kind": "dialogue", "target": "npc_id", "payload": [{"id": "greeting", "text": "A short grounded line."}]},
    },
    "read": {
        "kind": "read",
        "domain": "dialogue",
        "target_required": True,
        "payload_type": "string",
        "required_fields": [],
        "optional_fields": [],
        "reference_hints": ["entities"],
        "preview": {"kind": "readable", "args": ["target"]},
        "example": {"kind": "read", "target": "readable_entity_id", "payload": "A short readable passage."},
    },
    "enemy": {
        "kind": "enemy",
        "domain": "encounters",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["hp", "xp", "tags", "attacks", "loot"],
        "reference_hints": ["enemies", "items", "enemy-tags"],
        "preview": {"kind": "enemy", "args": ["target"]},
        "example": {"kind": "enemy", "target": "new_enemy", "payload": {"name": "New Enemy", "hp": 10, "xp": 5, "attacks": []}},
    },
    "encounters": {
        "kind": "encounters",
        "domain": "encounters",
        "target_required": True,
        "payload_type": "list",
        "required_fields": [],
        "optional_fields": ["list of room encounter objects"],
        "reference_hints": ["rooms", "enemies"],
        "preview": {"kind": "encounters", "args": ["target"]},
        "example": {"kind": "encounters", "target": "room_id", "payload": [{"key": "new_encounter", "title": "New Encounter", "enemies": ["new_enemy"]}]},
    },
    "roaming-party": {
        "kind": "roaming-party",
        "domain": "encounters",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["region", "start_room", "encounter"],
        "optional_fields": ["interval", "respawn_delay", "avoid_safe"],
        "reference_hints": ["rooms", "enemies", "roaming-parties"],
        "preview": {"kind": "roaming-party", "args": ["target"]},
        "example": {"kind": "roaming-party", "target": "new_patrol", "payload": {"region": "brambleford", "start_room": "brambleford_town_green", "encounter": {"key": "new_patrol", "title": "New Patrol", "enemies": []}}},
    },
    "portal": {
        "kind": "portal",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["status", "room_id", "destination"],
        "reference_hints": ["rooms", "portals"],
        "preview": {"kind": "portal", "args": ["target"]},
        "example": {"kind": "portal", "target": "new_portal", "payload": {"name": "New Portal", "status": "inactive"}},
    },
    "forge": {
        "kind": "forge",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["result"],
        "optional_fields": ["materials", "skill"],
        "reference_hints": ["items", "forge"],
        "preview": {"kind": "forge", "args": ["target"]},
        "example": {"kind": "forge", "target": "source_item", "payload": {"result": "crafted_item", "materials": {}}},
    },
    "cooking-recipe": {
        "kind": "cooking-recipe",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name", "result"],
        "optional_fields": ["ingredients", "station"],
        "reference_hints": ["items", "cooking-recipes"],
        "preview": {"kind": "cooking-recipe", "args": ["target"]},
        "example": {"kind": "cooking-recipe", "target": "new_recipe", "payload": {"name": "New Recipe", "result": "new_meal", "ingredients": {}}},
    },
    "tinkering-recipe": {
        "kind": "tinkering-recipe",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name", "result"],
        "optional_fields": ["base", "components", "station"],
        "reference_hints": ["items", "tinkering-recipes"],
        "preview": {"kind": "tinkering-recipe", "args": ["target"]},
        "example": {"kind": "tinkering-recipe", "target": "new_tinker", "payload": {"name": "New Tinker", "result": "new_device", "components": {}}},
    },
    "fishing-spot": {
        "kind": "fishing-spot",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["fish", "difficulty"],
        "reference_hints": ["rooms", "fishing-spots"],
        "preview": {"kind": "fishing-spot", "args": ["target"]},
        "example": {"kind": "fishing-spot", "target": "room_id", "payload": {"name": "New Fishing Spot", "fish": []}},
    },
    "fishing-rod": {
        "kind": "fishing-rod",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["power", "stability", "summary"],
        "reference_hints": ["fishing-rods"],
        "preview": {"kind": "fishing-rod", "args": ["target"]},
        "example": {"kind": "fishing-rod", "target": "new_rod", "payload": {"name": "New Rod", "power": 1, "stability": 1}},
    },
    "fishing-lure": {
        "kind": "fishing-lure",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["attracts", "summary"],
        "reference_hints": ["fishing-lures", "fish-behaviors"],
        "preview": {"kind": "fishing-lure", "args": ["target"]},
        "example": {"kind": "fishing-lure", "target": "new_lure", "payload": {"name": "New Lure", "attracts": []}},
    },
    "fish-behavior": {
        "kind": "fish-behavior",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["pattern"],
        "optional_fields": ["difficulty", "summary"],
        "reference_hints": ["fish-behaviors"],
        "preview": {"kind": "fish-behavior", "args": ["target"]},
        "example": {"kind": "fish-behavior", "target": "new_behavior", "payload": {"pattern": "steady"}},
    },
    "boss-gate": {
        "kind": "boss-gate",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["trigger_room_id", "boss_enemy", "summary", "reward"],
        "reference_hints": ["rooms", "enemies", "boss-gates", "items"],
        "preview": {"kind": "boss-gate", "args": ["target"]},
        "example": {"kind": "boss-gate", "target": "new_boss_gate", "payload": {"name": "New Boss Gate", "summary": "A decisive boss fight."}},
    },
    "trophy": {
        "kind": "trophy",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name"],
        "optional_fields": ["world", "desc", "criteria"],
        "reference_hints": ["trophies"],
        "preview": {"kind": "trophy", "args": ["target"]},
        "example": {"kind": "trophy", "target": "new_trophy", "payload": {"name": "New Trophy", "world": "Brave"}},
    },
    "shop": {
        "kind": "shop",
        "domain": "systems",
        "target_required": True,
        "payload_type": "object",
        "required_fields": ["name", "room_id"],
        "optional_fields": ["keeper_entity_id", "summary", "buys_kinds", "sell_price_multiplier", "shift_outcomes", "stock"],
        "reference_hints": ["shops", "rooms", "entities", "items", "quests"],
        "preview": {"kind": "shop", "args": ["target"]},
        "example": {"kind": "shop", "target": "new_shop", "payload": {"name": "New Shop", "room_id": "room_id", "stock": []}},
    },
}


MUTATION_KINDS = tuple(MUTATION_RECIPES)


def codex_recipes(kind=None):
    if kind:
        normalized = normalize_kind(kind)
        recipe = MUTATION_RECIPES.get(normalized)
        if not recipe:
            raise ValueError(f"Unknown mutation kind: {kind}")
        return {normalized: recipe}
    return {recipe_kind: MUTATION_RECIPES[recipe_kind] for recipe_kind in MUTATION_KINDS}


def codex_capabilities():
    return {
        "mutation_kinds": list(MUTATION_KINDS),
        "reference_domains": list(REFERENCE_DOMAINS),
        "stages": ["draft"],
        "write_policy": "Codex apply writes to draft packs only. Publish remains a separate Creator action.",
        "mutation_shape": {"kind": "quest", "target": "quest_key", "payload": {}, "note": "payload shape follows the existing /api/content/mutate kind."},
        "recipes": codex_recipes(),
    }


def normalize_kind(kind):
    return str(kind or "").strip().lower()


def expected_python_type(payload_type):
    if payload_type == "object":
        return dict
    if payload_type == "list":
        return list
    if payload_type == "string":
        return str
    raise ValueError(f"Unknown payload type: {payload_type}")


def validate_codex_mutations(mutations):
    if not isinstance(mutations, list) or not mutations:
        raise ValueError("Codex apply requires a non-empty mutations list.")
    normalized_entries = []
    for index, entry in enumerate(mutations, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Mutation {index} must be an object.")
        kind = normalize_kind(entry.get("kind"))
        recipe = MUTATION_RECIPES.get(kind)
        if not recipe:
            raise ValueError(f"Mutation {index} uses unknown kind: {entry.get('kind')}")
        target = str(entry.get("target") or "").strip()
        if recipe["target_required"] and not target:
            raise ValueError(f"Mutation {index} ({kind}) requires target.")
        if "payload" not in entry:
            raise ValueError(f"Mutation {index} ({kind}) requires payload.")
        payload = entry.get("payload")
        expected_type = expected_python_type(recipe["payload_type"])
        if not isinstance(payload, expected_type):
            raise ValueError(f"Mutation {index} ({kind}) payload must be a JSON {recipe['payload_type']}.")
        if isinstance(payload, dict):
            missing = [field for field in recipe["required_fields"] if field not in payload and not (kind == "quest" and isinstance(payload.get("quest"), dict) and field in payload["quest"])]
            if missing:
                raise ValueError(f"Mutation {index} ({kind}) payload missing required fields: {', '.join(missing)}.")
        normalized = dict(entry)
        normalized["kind"] = kind
        normalized["target"] = target
        normalized_entries.append(normalized)
    return normalized_entries


def suggested_previews_for_mutations(mutations):
    previews = []
    seen = set()
    for entry in mutations or []:
        recipe = MUTATION_RECIPES.get(normalize_kind(entry.get("kind")))
        if not recipe:
            continue
        preview = recipe.get("preview") or {}
        kind = preview.get("kind")
        args = []
        for token in preview.get("args") or []:
            if token == "target":
                args.append(str(entry.get("target") or ""))
            else:
                payload = entry.get("payload")
                args.append(str(payload.get(token) if isinstance(payload, dict) else ""))
        args = [arg for arg in args if arg]
        key = (kind, tuple(args))
        if kind and key not in seen:
            previews.append({"kind": kind, "args": args})
            seen.add(key)
    return previews


def touched_domains_for_mutations(mutations):
    domains = []
    seen = set()
    for entry in mutations or []:
        recipe = MUTATION_RECIPES.get(normalize_kind(entry.get("kind")))
        domain = recipe.get("domain") if recipe else None
        if domain and domain not in seen:
            domains.append(domain)
            seen.add(domain)
    return domains


def codex_recipe_warnings(mutations, requested_previews=None):
    requested = {
        (entry.get("kind"), tuple(entry.get("args") or []))
        for entry in (requested_previews or [])
        if isinstance(entry, dict)
    }
    warnings = []
    for preview in suggested_previews_for_mutations(mutations):
        key = (preview["kind"], tuple(preview["args"]))
        if key not in requested:
            warnings.append({"kind": "missing_preview", "message": f"Verify preview {preview['kind']} {' '.join(preview['args'])} before publishing.", "preview": preview})
    return warnings
