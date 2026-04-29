"""Fishing and cooking helpers for Brave's Brambleford hub."""

from collections.abc import Mapping
from random import randint, random, uniform
from time import time
from uuid import uuid4

from evennia.utils import delay

from world.bootstrap import get_entity
from world.content import get_content_registry
from world.data.items import (
    ITEM_TEMPLATES,
    format_bonus_summary,
    get_item_use_profile,
    match_inventory_item,
)
from world.questing import get_completed_quests
from world.race_world_hooks import adjust_fishing_weight, get_fishing_suffix
from world.resonance import get_resource_label, get_stat_label
from world.screen_text import format_entry, render_screen

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
SYSTEMS_CONTENT = CONTENT.systems
COOKING_RECIPES = SYSTEMS_CONTENT.cooking_recipes
COZY_BONUS = SYSTEMS_CONTENT.cozy_bonus
FISHING_SPOTS = SYSTEMS_CONTENT.fishing_spots
FISHING_RODS = SYSTEMS_CONTENT.fishing_rods
FISHING_LURES = SYSTEMS_CONTENT.fishing_lures
FISHING_BEHAVIORS = SYSTEMS_CONTENT.fishing_behaviors
format_ingredient_list = SYSTEMS_CONTENT.format_ingredient_list

STARTER_FISHING_ROOM_ID = "brambleford_hobbyists_wharf"
STARTER_FISHING_ROD = "loaner_pole"
STARTER_FISHING_LURE = "plain_hook"
FISHING_MINIGAME_EXPIRES_SECONDS = 90
DEFAULT_FISHING_BEHAVIOR = {
    "pattern": "sine",
    "base_pull": 0.3,
    "burst_pull": 0.08,
    "stamina": 10,
}


def room_supports_activity(room, activity_name):
    """Return whether the room supports a named Brave activity."""

    if not room:
        return False
    return activity_name in set(getattr(room.db, "brave_activities", []) or [])


def _count_inventory(character):
    totals = {}
    for entry in (character.db.brave_inventory or []):
        template_id = entry.get("template")
        totals[template_id] = totals.get(template_id, 0) + entry.get("quantity", 0)
    return totals


def _normalize_target_token(value):
    """Normalize free-text target queries for fuzzy matching."""

    return "".join(char for char in str(value or "").lower() if char.isalnum())


def _is_targetable_consumable_character(obj):
    """Return whether a room object can be targeted by explore consumables."""

    if not obj:
        return False
    if hasattr(obj, "ensure_brave_character"):
        return True
    is_typeclass = getattr(obj, "is_typeclass", None)
    if callable(is_typeclass):
        try:
            return bool(is_typeclass("typeclasses.characters.Character", exact=False))
        except TypeError:
            return False
    return False


def _is_targetable_social_actor(obj):
    """Return whether a room object can be socially targeted."""

    if not obj:
        return False
    if hasattr(obj, "ensure_brave_character"):
        return True
    return getattr(getattr(obj, "db", None), "brave_entity_kind", None) == "npc"


def get_targetable_social_characters(character, include_self=False):
    """Return nearby Brave social actors that can be targeted by emotes."""

    candidates = []
    room = getattr(character, "location", None)
    if room:
        for obj in list(getattr(room, "contents", []) or []):
            if not _is_targetable_social_actor(obj):
                continue
            if obj == character and not include_self:
                continue
            if obj not in candidates:
                candidates.append(obj)

    if include_self and character not in candidates:
        candidates.insert(0, character)

    def _sort_key(candidate):
        same_party = (
            candidate != character
            and getattr(getattr(candidate, "db", None), "brave_party_id", None)
            and getattr(getattr(candidate, "db", None), "brave_party_id", None)
            == getattr(getattr(character, "db", None), "brave_party_id", None)
        )
        kind = getattr(getattr(candidate, "db", None), "brave_entity_kind", None)
        return (
            0 if candidate == character else 1,
            0 if same_party else 1,
            0 if kind == "npc" else 1,
            str(getattr(candidate, "key", "") or "").lower(),
            getattr(candidate, "id", 0),
        )

    candidates.sort(key=_sort_key)
    return candidates


def match_targetable_social_character(character, query, include_self=False):
    """Find a nearby Brave social actor by fuzzy name for emotes."""

    candidates = get_targetable_social_characters(character, include_self=include_self)
    if not query:
        return None

    query_norm = _normalize_target_token(query)
    exact = []
    partial = []
    for candidate in candidates:
        names = [getattr(candidate, "key", "")]
        aliases = getattr(getattr(candidate, "aliases", None), "all", None)
        if callable(aliases):
            names.extend(alias for alias in aliases())
        tokens = [_normalize_target_token(name) for name in names if name]
        if any(query_norm == token for token in tokens):
            exact.append(candidate)
        elif any(query_norm in token for token in tokens):
            partial.append(candidate)

    if exact:
        return exact[0] if len(exact) == 1 else exact
    if partial:
        return partial[0] if len(partial) == 1 else partial
    return None


def get_targetable_consumable_characters(character, include_self=False):
    """Return nearby Brave characters that can be targeted by explore consumables."""

    candidates = []
    room = getattr(character, "location", None)
    if room:
        for obj in list(getattr(room, "contents", []) or []):
            if not _is_targetable_consumable_character(obj):
                continue
            if obj == character and not include_self:
                continue
            if obj not in candidates:
                candidates.append(obj)

    if include_self and character not in candidates:
        candidates.insert(0, character)

    def _sort_key(candidate):
        same_party = (
            candidate != character
            and getattr(getattr(candidate, "db", None), "brave_party_id", None)
            and getattr(getattr(candidate, "db", None), "brave_party_id", None)
            == getattr(getattr(character, "db", None), "brave_party_id", None)
        )
        return (
            0 if candidate == character else 1,
            0 if same_party else 1,
            str(getattr(candidate, "key", "") or "").lower(),
            getattr(candidate, "id", 0),
        )

    candidates.sort(key=_sort_key)
    return candidates


def match_targetable_consumable_character(character, query, include_self=False):
    """Find a nearby Brave character by fuzzy name for explore-time item use."""

    candidates = get_targetable_consumable_characters(character, include_self=include_self)
    if not query:
        return None

    query_norm = _normalize_target_token(query)
    exact = []
    partial = []
    for candidate in candidates:
        names = [getattr(candidate, "key", "")]
        aliases = getattr(getattr(candidate, "aliases", None), "all", None)
        if callable(aliases):
            names.extend(alias for alias in aliases())
        tokens = [_normalize_target_token(name) for name in names if name]
        if any(query_norm == token for token in tokens):
            exact.append(candidate)
        elif any(query_norm in token for token in tokens):
            partial.append(candidate)

    if exact:
        return exact[0] if len(exact) == 1 else exact
    if partial:
        return partial[0] if len(partial) == 1 else partial
    return None


def _clear_fishing_state(character):
    if hasattr(character.ndb, "brave_fishing"):
        del character.ndb.brave_fishing


def _pick_fish(spot_data):
    roll = randint(1, sum(entry["chance"] for entry in spot_data["fish"]))
    running = 0
    for fish_entry in spot_data["fish"]:
        running += fish_entry["chance"]
        if roll <= running:
            return fish_entry
    return spot_data["fish"][-1]


def _is_tackle_unlocked(character, payload):
    required = [str(key).lower() for key in (payload.get("unlock_completed_quests") or []) if key]
    if not required:
        return True
    completed = {str(key).lower() for key in get_completed_quests(character)}
    return all(key in completed for key in required)


def get_available_fishing_rods(character=None, *, include_locked=False):
    """Return all currently available fishing rod payloads."""

    rods = []
    for rod_key, rod in FISHING_RODS.items():
        payload = dict(rod)
        payload["key"] = rod_key
        payload["available"] = _is_tackle_unlocked(character, payload) if character else True
        if not payload["available"] and not include_locked:
            continue
        rods.append(payload)
    rods.sort(key=lambda entry: (0 if entry.get("available", True) else 1, int(entry.get("power", 0) or 0), entry.get("name", "").lower()))
    return rods


def get_available_fishing_lures(character=None, *, include_locked=False):
    """Return all currently available fishing lure payloads."""

    lures = []
    for lure_key, lure in FISHING_LURES.items():
        payload = dict(lure)
        payload["key"] = lure_key
        payload["available"] = _is_tackle_unlocked(character, payload) if character else True
        if not payload["available"] and not include_locked:
            continue
        lures.append(payload)
    lures.sort(key=lambda entry: (0 if entry.get("available", True) else 1, int(entry.get("rarity_bonus", 0) or 0), entry.get("name", "").lower()))
    return lures


def get_selected_fishing_rod(character):
    """Return the active fishing rod payload, falling back to the first defined rod."""

    selected = str(getattr(getattr(character, "db", None), "brave_active_fishing_rod", "") or "").lower()
    if selected in FISHING_RODS:
        payload = dict(FISHING_RODS[selected])
        payload["key"] = selected
        payload["available"] = _is_tackle_unlocked(character, payload)
        if payload["available"]:
            return payload
    rods = get_available_fishing_rods(character)
    return rods[0] if rods else {}


def get_selected_fishing_lure(character):
    """Return the active fishing lure payload, falling back to the first defined lure."""

    selected = str(getattr(getattr(character, "db", None), "brave_active_fishing_lure", "") or "").lower()
    if selected in FISHING_LURES:
        payload = dict(FISHING_LURES[selected])
        payload["key"] = selected
        payload["available"] = _is_tackle_unlocked(character, payload)
        if payload["available"]:
            return payload
    lures = get_available_fishing_lures(character)
    return lures[0] if lures else {}


def can_borrow_fishing_tackle(character):
    """Return whether starter tackle can be borrowed in the current room."""

    room = getattr(character, "location", None)
    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    return room_id == STARTER_FISHING_ROOM_ID


def borrow_fishing_tackle(character, selection="kit"):
    """Issue starter tackle from the Brambleford wharf and select it."""

    if not can_borrow_fishing_tackle(character):
        return False, "You need the Brambleford wharf's loaner rack before anyone will issue tackle."

    choice = str(selection or "kit").strip().lower()
    if choice in {"", "kit", "gear", "all"}:
        character.db.brave_active_fishing_rod = STARTER_FISHING_ROD
        character.db.brave_active_fishing_lure = STARTER_FISHING_LURE
        return True, "You borrow a |wLoaner Pole|n and a |wPlain Hook|n from the wharf rack and set them as your tackle."
    if choice in {"rod", "pole"}:
        character.db.brave_active_fishing_rod = STARTER_FISHING_ROD
        return True, "You borrow a |wLoaner Pole|n from the wharf rack and set it as your active rod."
    if choice in {"lure", "hook", "bait"}:
        character.db.brave_active_fishing_lure = STARTER_FISHING_LURE
        return True, "You borrow a |wPlain Hook|n from the wharf rack and set it as your active lure."
    return False, "Borrow a fishing kit, rod, or lure from the rack to begin."


def set_selected_fishing_rod(character, query):
    """Select one fishing rod by fuzzy name."""

    token = _normalize_target_token(query)
    exact = []
    partial = []
    for rod in get_available_fishing_rods(character):
        values = [rod["key"], rod.get("name", "")]
        normalized = [_normalize_target_token(value) for value in values]
        if any(token == value for value in normalized):
            exact.append(rod)
        elif any(token in value for value in normalized):
            partial.append(rod)
    matches = exact or partial
    if not matches:
        return False, "No fishing rod matches that name."
    if len(matches) > 1:
        return False, "Be more specific. That could mean: " + ", ".join(match["name"] for match in matches)
    character.db.brave_active_fishing_rod = matches[0]["key"]
    return True, f"You set out the |w{matches[0]['name']}|n."


def set_selected_fishing_lure(character, query):
    """Select one fishing lure by fuzzy name."""

    token = _normalize_target_token(query)
    exact = []
    partial = []
    for lure in get_available_fishing_lures(character):
        values = [lure["key"], lure.get("name", "")]
        normalized = [_normalize_target_token(value) for value in values]
        if any(token == value for value in normalized):
            exact.append(lure)
        elif any(token in value for value in normalized):
            partial.append(lure)
    matches = exact or partial
    if not matches:
        return False, "No fishing lure matches that name."
    if len(matches) > 1:
        return False, "Be more specific. That could mean: " + ", ".join(match["name"] for match in matches)
    character.db.brave_active_fishing_lure = matches[0]["key"]
    return True, f"You swap over to |w{matches[0]['name']}|n."


def _fishing_weight_for_entry(room_id, fish_entry, rod, lure):
    rarity_rank = {
        "junk": -1,
        "common": 0,
        "uncommon": 1,
        "rare": 2,
        "epic": 3,
    }.get(str(fish_entry.get("rarity") or "common").lower(), 0)
    weight = max(1, int(fish_entry.get("chance", 1) or 1))
    if rarity_rank > 0:
        weight += int(rod.get("power", 0) or 0) * rarity_rank
        weight += int(lure.get("rarity_bonus", 0) or 0) * rarity_rank
    if fish_entry.get("item") in set(lure.get("attracts", []) or []):
        weight += 6
    weight += int((lure.get("zone_bonus", {}) or {}).get(room_id, 0) or 0)
    return max(1, weight)


def _pick_fish_for_setup(room_id, spot_data, rod, lure):
    weighted_entries = []
    total = 0
    for fish_entry in spot_data.get("fish", []):
        chance = _fishing_weight_for_entry(room_id, fish_entry, rod, lure)
        total += chance
        weighted_entries.append((total, fish_entry))
    if not weighted_entries:
        return None
    roll = randint(1, total)
    for threshold, fish_entry in weighted_entries:
        if roll <= threshold:
            return dict(fish_entry)
    return dict(weighted_entries[-1][1])


def get_fishing_spot_summary(character):
    """Return current fishing setup and likely catches for the active room."""

    room = getattr(character, "location", None)
    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    spot = FISHING_SPOTS.get(room_id, {})
    rod = get_selected_fishing_rod(character)
    lure = get_selected_fishing_lure(character)
    catches = []
    for fish_entry in sorted(
        spot.get("fish", []),
        key=lambda entry: (
            {"junk": 0, "common": 1, "uncommon": 2, "rare": 3, "epic": 4}.get(str(entry.get("rarity") or "common").lower(), 1),
            -int(entry.get("chance", 0) or 0),
        ),
    ):
        catches.append(
            {
                "item": fish_entry.get("item"),
                "name": ITEM_TEMPLATES.get(fish_entry.get("item"), {}).get("name", fish_entry.get("item")),
                "rarity": str(fish_entry.get("rarity") or "common").title(),
                "boosted": fish_entry.get("item") in set(lure.get("attracts", []) or []),
            }
        )
    return {
        "spot": spot,
        "rod": rod,
        "lure": lure,
        "catches": catches,
    }


def _fishing_rod_setup_payload(rod, *, selected=False):
    return {
        "key": rod.get("key"),
        "name": rod.get("name", "Rod"),
        "power": int(rod.get("power", 0) or 0),
        "stability": float(rod.get("stability", 0) or 0),
        "summary": rod.get("summary", ""),
        "available": bool(rod.get("available", True)),
        "selected": bool(selected),
        "unlock_text": rod.get("unlock_text", ""),
    }


def _fishing_lure_setup_payload(lure, *, selected=False, room_id=None):
    favored = [
        ITEM_TEMPLATES[item_id]["name"]
        for item_id in lure.get("attracts", [])
        if item_id in ITEM_TEMPLATES
    ]
    return {
        "key": lure.get("key"),
        "name": lure.get("name", "Lure"),
        "rarity_bonus": int(lure.get("rarity_bonus", 0) or 0),
        "favored": favored,
        "summary": lure.get("summary", ""),
        "zone_bonus": int((lure.get("zone_bonus", {}) or {}).get(room_id, 0) or 0),
        "available": bool(lure.get("available", True)),
        "selected": bool(selected),
        "unlock_text": lure.get("unlock_text", ""),
    }


def build_fishing_setup_payload(character, *, status_message=None, status_tone="muted"):
    """Return a browser overlay payload for fishing setup and tackle selection."""

    summary = get_fishing_spot_summary(character)
    room = getattr(character, "location", None)
    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    spot = summary["spot"] or {}
    current_rod = summary["rod"] or {}
    current_lure = summary["lure"] or {}
    active_rod_key = current_rod.get("key")
    active_lure_key = current_lure.get("key")
    fishing_state = getattr(getattr(character, "ndb", None), "brave_fishing", None) or {}
    fishing_phase = fishing_state.get("phase")

    rods = [
        _fishing_rod_setup_payload(rod, selected=rod.get("key") == active_rod_key)
        for rod in get_available_fishing_rods(character, include_locked=True)
    ]
    lures = [
        _fishing_lure_setup_payload(lure, selected=lure.get("key") == active_lure_key, room_id=room_id)
        for lure in get_available_fishing_lures(character, include_locked=True)
    ]

    return {
        "phase": "setup",
        "spot": spot.get("name", getattr(room, "key", None) or "Fishing Water"),
        "cast_text": spot.get("cast_text", "The water looks workable."),
        "message": status_message or "",
        "message_tone": status_tone or "muted",
        "can_borrow": can_borrow_fishing_tackle(character),
        "can_cast": bool(spot) and fishing_phase not in {"waiting", "bite", "minigame"},
        "active_phase": fishing_phase or "setup",
        "rod": _fishing_rod_setup_payload(current_rod, selected=True) if current_rod else {},
        "lure": _fishing_lure_setup_payload(current_lure, selected=True, room_id=room_id) if current_lure else {},
        "rods": rods,
        "lures": lures,
    }


def _format_weight(weight):
    return f"{weight:.1f} lb"


def _award_catch_record(character, template_id, weight):
    board = get_entity("great_catch_log")
    if not board:
        return None

    records = dict(board.db.brave_catch_records or {})
    account_name = character.account.key if character.account else character.key
    previous = records.get(account_name)
    if previous and weight <= previous.get("weight", 0):
        return None

    records[account_name] = {
        "account": account_name,
        "character": character.key,
        "fish": ITEM_TEMPLATES[template_id]["name"],
        "weight": round(weight, 1),
    }
    board.db.brave_catch_records = records
    return records[account_name]


def get_catch_log_entries(limit=None):
    """Return Great Catch log rows sorted from heaviest to lightest."""

    board = get_entity("great_catch_log")
    records = dict(board.db.brave_catch_records or {}) if board else {}
    entries = sorted(records.values(), key=lambda entry: (-float(entry.get("weight", 0) or 0), str(entry.get("account", "")).lower()))
    if limit is not None:
        entries = entries[: max(0, int(limit or 0))]
    return entries


def _fishing_behavior_for_entry(fish_entry):
    behavior_key = str(fish_entry.get("behavior_id") or "").strip().lower()
    behavior = dict(FISHING_BEHAVIORS.get(behavior_key, {}) or DEFAULT_FISHING_BEHAVIOR)
    behavior["key"] = behavior_key or "default"
    behavior["pattern"] = str(behavior.get("pattern") or "sine").lower()
    behavior["base_pull"] = float(behavior.get("base_pull", DEFAULT_FISHING_BEHAVIOR["base_pull"]) or 0)
    behavior["burst_pull"] = float(behavior.get("burst_pull", DEFAULT_FISHING_BEHAVIOR["burst_pull"]) or 0)
    behavior["stamina"] = float(behavior.get("stamina", DEFAULT_FISHING_BEHAVIOR["stamina"]) or 1)
    return behavior


def _award_fishing_catch(character, fish_entry, *, perfect=False):
    template_id = fish_entry["item"]
    weight = round(uniform(*fish_entry["weight"]), 1)
    weight = adjust_fishing_weight(character, weight)
    character.add_item_to_inventory(template_id, 1)
    record = _award_catch_record(character, template_id, weight)

    rarity = str(fish_entry.get("rarity") or "common").lower()
    rarity_text = ""
    if rarity in {"rare", "epic"}:
        rarity_text = f" |y({rarity.title()})|n"
    lead = "Perfect catch! You land" if perfect else "You land"
    message = f"{lead} a |w{ITEM_TEMPLATES[template_id]['name']}|n{rarity_text} weighing |w{_format_weight(weight)}|n."
    message += get_fishing_suffix(character)
    if record:
        message += " It is your new best catch on the log."
    return True, message


def build_fishing_minigame_payload(character, state=None):
    """Return a browser minigame payload for the current fishing encounter."""

    state = state or getattr(getattr(character, "ndb", None), "brave_fishing", None) or {}
    room_id = state.get("room_id")
    spot = FISHING_SPOTS.get(room_id, {})
    fish_entry = dict(state.get("fish") or {})
    rod = FISHING_RODS.get(str(state.get("rod_key") or "").lower(), {})
    lure = FISHING_LURES.get(str(state.get("lure_key") or "").lower(), {})
    behavior = _fishing_behavior_for_entry(fish_entry)
    template_id = fish_entry.get("item")
    item = ITEM_TEMPLATES.get(template_id, {})
    rarity = str(fish_entry.get("rarity") or "common").lower()
    wait_ms = int(state.get("wait_ms") or 1800)
    reaction_window = float(spot.get("reaction_window", 4) or 4)
    hook_ms = max(900, min(2200, int(reaction_window * 350)))
    duration_ms = max(9000, min(24000, int(9000 + (behavior.get("stamina", 10) * 700))))
    lure_attracts = {str(item_id).lower() for item_id in lure.get("attracts", []) or []}
    return {
        "phase": "start",
        "encounter_id": state.get("encounter_id"),
        "spot": spot.get("name", "Fishing Water"),
        "cast_text": spot.get("cast_text", "You cast a line into the water."),
        "wait_ms": wait_ms,
        "hook_ms": hook_ms,
        "duration_ms": duration_ms,
        "fish": {
            "item": template_id,
            "name": item.get("name", template_id or "Fish"),
            "rarity": rarity.title(),
        },
        "rod": {
            "key": state.get("rod_key"),
            "name": rod.get("name", "Rod"),
            "power": float(rod.get("power", 1) or 1),
            "stability": float(rod.get("stability", 1) or 1),
        },
        "lure": {
            "key": state.get("lure_key"),
            "name": lure.get("name", "Lure"),
            "favored": str(template_id or "").lower() in lure_attracts,
        },
        "behavior": behavior,
    }


def start_fishing_minigame(character):
    """Begin a browser-driven fishing minigame encounter."""

    room = character.location
    if not room or not room_supports_activity(room, "fishing"):
        return False, "You need open water and a proper spot before you can fish.", None

    encounter = character.get_active_encounter()
    if encounter and encounter.is_participant(character):
        return False, "You are a little too busy surviving to fish right now.", None

    room_id = getattr(room.db, "brave_room_id", None)
    spot = FISHING_SPOTS.get(room_id)
    if not spot:
        return False, "This stretch of water is not set up for fishing yet.", None

    state = getattr(character.ndb, "brave_fishing", None)
    if state:
        phase = state.get("phase")
        if phase == "minigame":
            return False, "Your line is already in the water.", build_fishing_minigame_payload(character, state)
        if phase == "waiting":
            return False, "Your line is already in the water. Give it a moment.", None
        if phase == "bite":
            return False, "Something is already biting. Use |wreel|n now.", None

    rod = get_selected_fishing_rod(character)
    lure = get_selected_fishing_lure(character)
    fish_entry = _pick_fish_for_setup(room_id, spot, rod, lure)
    if not fish_entry:
        return False, "The water here looks empty for the moment.", None

    bite_delay = randint(*spot.get("bite_delay", [2, 4]))
    state = {
        "phase": "minigame",
        "room_id": room_id,
        "started_at": time(),
        "expires_at": time() + FISHING_MINIGAME_EXPIRES_SECONDS,
        "encounter_id": uuid4().hex,
        "fish": fish_entry,
        "rod_key": rod.get("key"),
        "lure_key": lure.get("key"),
        "wait_ms": max(900, int(bite_delay * 1000)),
    }
    character.ndb.brave_fishing = state
    payload = build_fishing_minigame_payload(character, state)
    return True, (
        f"{spot['cast_text']} You work with |w{rod.get('name', 'a borrowed rod')}|n and |w{lure.get('name', 'a plain lure')}|n."
    ), payload


def resolve_fishing_minigame(character, encounter_id, result):
    """Resolve a browser-driven fishing minigame encounter."""

    state = getattr(character.ndb, "brave_fishing", None)
    if not state or state.get("phase") != "minigame":
        return False, "You do not have an active fishing run.", {
            "phase": "result",
            "success": False,
            "message": "You do not have an active fishing run.",
        }

    if str(state.get("encounter_id") or "") != str(encounter_id or ""):
        return False, "That fishing run is no longer active.", {
            "phase": "result",
            "success": False,
            "message": "That fishing run is no longer active.",
        }

    room = character.location
    room_id = getattr(room.db, "brave_room_id", None) if room else None
    if room_id != state.get("room_id"):
        _clear_fishing_state(character)
        return False, "You have moved away from the line.", {
            "phase": "result",
            "success": False,
            "message": "You have moved away from the line.",
        }

    if time() > state.get("expires_at", 0):
        _clear_fishing_state(character)
        return False, "The line goes slack. The fish is gone.", {
            "phase": "result",
            "success": False,
            "message": "The line goes slack. The fish is gone.",
        }

    fish_entry = state["fish"]
    _clear_fishing_state(character)
    outcome = str(result or "").strip().lower()
    if outcome not in {"success", "perfect"}:
        message = "The line goes slack before you can land it."
        return False, message, {"phase": "result", "success": False, "message": message}

    ok, message = _award_fishing_catch(character, fish_entry, perfect=outcome == "perfect")
    return ok, message, {"phase": "result", "success": ok, "message": message}


def start_fishing(character):
    """Begin a fishing attempt in a valid fishing room."""

    room = character.location
    if not room or not room_supports_activity(room, "fishing"):
        return False, "You need open water and a proper spot before you can fish."

    encounter = character.get_active_encounter()
    if encounter and encounter.is_participant(character):
        return False, "You are a little too busy surviving to fish right now."

    room_id = getattr(room.db, "brave_room_id", None)
    spot = FISHING_SPOTS.get(room_id)
    if not spot:
        return False, "This stretch of water is not set up for fishing yet."

    state = getattr(character.ndb, "brave_fishing", None)
    if state:
        phase = state.get("phase")
        if phase == "minigame":
            return False, "Your line is already in the water."
        if phase == "waiting":
            return False, "Your line is already in the water. Give it a moment."
        if phase == "bite":
            return False, "Something is already biting. Use |wreel|n now."

    rod = get_selected_fishing_rod(character)
    lure = get_selected_fishing_lure(character)
    fish_entry = _pick_fish_for_setup(room_id, spot, rod, lure)
    if not fish_entry:
        return False, "The water here looks empty for the moment."
    character.ndb.brave_fishing = {
        "phase": "waiting",
        "room_id": room_id,
        "started_at": time(),
        "fish": fish_entry,
        "rod_key": rod.get("key"),
        "lure_key": lure.get("key"),
    }
    bite_delay = randint(*spot["bite_delay"])
    delay(bite_delay, _trigger_bite, character, persistent=False)
    return True, (
        f"{spot['cast_text']} You work with |w{rod.get('name', 'a borrowed rod')}|n and |w{lure.get('name', 'a plain lure')}|n."
    )


def _trigger_bite(character):
    state = getattr(character.ndb, "brave_fishing", None)
    if not state or state.get("phase") != "waiting":
        return

    room = character.location
    room_id = getattr(room.db, "brave_room_id", None) if room else None
    if room_id != state.get("room_id"):
        _clear_fishing_state(character)
        return

    spot = FISHING_SPOTS.get(room_id)
    if not spot:
        _clear_fishing_state(character)
        return

    expires_at = time() + spot["reaction_window"]
    state["phase"] = "bite"
    state["expires_at"] = expires_at
    character.ndb.brave_fishing = state
    try:
        from world.browser_panels import send_browser_notice_event
    except Exception:
        character.msg("|yA sharp tug runs through the line.|n Use |wreel|n before the fish gets away.")
    else:
        send_browser_notice_event(
            character,
            "|yA sharp tug runs through the line.|n Use |wreel|n before the fish gets away.",
            title="Fishing",
            tone="warn",
            icon="phishing",
            duration_ms=3200,
        )
    delay(spot["reaction_window"], _expire_bite, character, persistent=False)


def _expire_bite(character):
    state = getattr(character.ndb, "brave_fishing", None)
    if not state or state.get("phase") != "bite":
        return
    if time() <= state.get("expires_at", 0):
        return
    _clear_fishing_state(character)
    try:
        from world.browser_panels import send_browser_notice_event
    except Exception:
        character.msg("The water settles. Whatever was there slips free before you can set the hook.")
    else:
        send_browser_notice_event(
            character,
            "The water settles. Whatever was there slips free before you can set the hook.",
            title="Fishing",
            tone="muted",
            icon="waves",
            duration_ms=3200,
        )


def reel_line(character):
    """Resolve a fishing attempt after a bite."""

    state = getattr(character.ndb, "brave_fishing", None)
    if not state:
        return False, "You do not have a line in the water. Use |wfish|n first."

    if state.get("phase") == "minigame":
        return False, "Use the fishing popup to work that line."

    if state.get("phase") == "waiting":
        return False, "You tug too soon and only stir up the water. Wait for a real bite."

    room = character.location
    room_id = getattr(room.db, "brave_room_id", None) if room else None
    if room_id != state.get("room_id"):
        _clear_fishing_state(character)
        return False, "You have moved away from the line."

    if time() > state.get("expires_at", 0):
        _clear_fishing_state(character)
        return False, "You are too slow. The fish is gone."

    fish_entry = state["fish"]
    _clear_fishing_state(character)

    rod = FISHING_RODS.get(str(state.get("rod_key") or "").lower(), {})
    lure = FISHING_LURES.get(str(state.get("lure_key") or "").lower(), {})
    hook_chance = float(fish_entry.get("hook_chance", 1.0) or 1.0)
    hook_chance = min(1.0, hook_chance + (float(rod.get("stability", 0) or 0) * 0.08))
    if fish_entry.get("item") in set(lure.get("attracts", []) or []):
        hook_chance = min(1.0, hook_chance + 0.04)
    if random() > hook_chance:
        return False, "The line jerks, the hook bites, and then the fish twists free at the last second."

    return _award_fishing_catch(character, fish_entry)


def format_catch_log():
    """Return the current shared Great Catch log text."""

    entries = get_catch_log_entries()
    lines = [
        "The ledger pages are crowded with fish stories, half-legible boasting, and weights Uncle Pib insists are honest.",
        "",
    ]

    if not entries:
        lines.append("No one has posted a proper river triumph yet. The first name is still waiting.")
        return "\n".join(lines)

    overall = entries[0]
    lines.append(
        "Town best: "
        f"{overall['fish']} at {_format_weight(overall['weight'])} by {overall['account']} ({overall['character']})."
    )
    lines.append("")
    lines.append("Family catches:")

    for entry in sorted(entries, key=lambda current: str(current["account"]).lower()):
        lines.append(
            f"- {entry['account']}: {entry['fish']} at {_format_weight(entry['weight'])} "
            f"({entry['character']})"
        )

    return "\n".join(lines)


def format_kitchen_hearth_text(character=None):
    """Return descriptive text for the Lantern Rest hearth."""

    return "\n".join(
        [
            "The Lantern Rest hearth is a broad brick firepit blackened by years of soup pots, scorched pans, and late-night road meals. Iron hooks hang above the coals, a scarred prep board leans nearby, and the whole corner carries the deep kitchen smell of ash, onion, and river oil worked into old stone. Everything about it looks built for steady inn work rather than show: practical heat, heavy cookware, and just enough room to turn a rough haul into something worth serving.",
        ]
    )


def format_pole_rack_text():
    """Return fishing instructions for the wharf."""

    return (
        "A hand-painted note reads: CHECK YOUR TACKLE, BORROW STARTER GEAR IF YOU NEED IT, "
        "CAST YOUR LINE, AND WHEN IT TUGS BACK, REEL IN BEFORE THE RIVER CHANGES ITS MIND."
    )


def format_fishing_screen(character):
    """Return a readable fishing guide for the active room and tackle."""

    room = getattr(character, "location", None)
    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    spot = FISHING_SPOTS.get(room_id)
    if not spot:
        return "There is no proper place to fish here."

    summary = get_fishing_spot_summary(character)
    rod = summary["rod"]
    lure = summary["lure"]
    catch_lines = []
    for catch in summary["catches"]:
        boosted = " · favored by lure" if catch["boosted"] else ""
        catch_lines.append(f"  {catch['name']} · {catch['rarity']}{boosted}")

    return render_screen(
        "Tackle Roll",
        subtitle=spot.get("name", room.key if room else "Fishing Water"),
        meta=[
            f"Rod: {rod.get('name', 'None selected')}",
            f"Lure: {lure.get('name', 'None selected')}",
        ],
        sections=[
            ("Current Water", [f"  {spot.get('cast_text', '')}"]),
            ("Likely Catches", catch_lines or ["  Nothing obvious is moving here."]),
            (
                "How To Fish",
                [
                    "  Use |wfish|n or |wfish cast|n to put a line in the water.",
                    "  Use |wfish rod <rod>|n or |wfish lure <lure>|n to change your setup.",
                    "  Use |wfish borrow kit|n at the Brambleford wharf for starter tackle.",
                    "  Use |wfish log|n to review the Great Catch ledger.",
                ],
            ),
        ],
    )


def _is_cooking_recipe_known(character, recipe_key, recipe):
    """Return whether one recipe is currently known to the character."""

    unlock_type = str(recipe.get("unlock_type") or "auto").lower()
    if unlock_type in {"", "auto", "none"}:
        return True
    known = {str(key).lower() for key in (getattr(getattr(character, "db", None), "brave_known_cooking_recipes", None) or [])}
    return str(recipe_key).lower() in known


def get_cooking_entries(character):
    """Return normalized cooking entries for one character."""

    inventory = _count_inventory(character)
    entries = []
    for recipe_key, recipe in COOKING_RECIPES.items():
        ingredient_text = format_ingredient_list(recipe["ingredients"], ITEM_TEMPLATES)
        missing = []
        for template_id, quantity in recipe["ingredients"].items():
            have = inventory.get(template_id, 0)
            if have < quantity:
                missing.append(f"{ITEM_TEMPLATES[template_id]['name']} {have}/{quantity}")
        known = _is_cooking_recipe_known(character, recipe_key, recipe)
        entries.append(
            {
                "key": recipe_key,
                "name": recipe["name"],
                "ingredient_text": ingredient_text,
                "summary": recipe.get("summary", ""),
                "known": known,
                "ready": known and not missing,
                "missing": missing,
                "unlock_text": recipe.get("unlock_text", ""),
                "result": recipe.get("result"),
            }
        )
    entries.sort(key=lambda entry: (0 if entry["ready"] else 1, 0 if entry["known"] else 1, entry["name"].lower()))
    return entries


def _format_meal_restore(restore, character):
    """Return browser-friendly restore text for a meal."""

    restore = dict(restore or {})
    bits = [
        f"{get_resource_label(resource, character)} +{amount}"
        for resource, amount in restore.items()
        if amount
    ]
    return ", ".join(bits)


def _format_meal_bonuses(bonuses, character):
    """Return browser-friendly meal bonus text."""

    bonuses = dict(bonuses or {})
    bits = [
        f"{get_stat_label(stat, character)} +{amount}"
        for stat, amount in bonuses.items()
        if amount
    ]
    return ", ".join(bits)


def _build_cooking_recipe_payload(entry, character):
    meal = ITEM_TEMPLATES.get(entry["result"], {})
    if entry["ready"]:
        status = "Ready to cook"
    elif entry["known"]:
        status = "Missing: " + ", ".join(entry["missing"])
    else:
        status = "Locked recipe"

    return {
        "key": entry["key"],
        "name": entry["name"],
        "ingredient_text": entry["ingredient_text"],
        "known": bool(entry["known"]),
        "ready": bool(entry["ready"]),
        "missing": list(entry["missing"]),
        "status": status,
        "summary": entry["summary"] if entry["known"] else (entry["unlock_text"] or "You have not learned this recipe yet."),
        "result": entry["result"],
        "result_name": meal.get("name", entry["result"]),
        "result_summary": meal.get("summary", ""),
        "restore_text": _format_meal_restore(meal.get("restore", {}), character),
        "bonus_text": _format_meal_bonuses(meal.get("meal_bonuses", {}), character),
        "command": f"cook {entry['name']}" if entry["ready"] else "",
    }


def build_cooking_payload(character, *, status_message=None, status_tone="muted"):
    """Return a browser overlay payload for hearth cooking."""

    ready = []
    known = []
    locked = []
    entries = get_cooking_entries(character)
    for entry in entries:
        payload = _build_cooking_recipe_payload(entry, character)
        if not entry["known"]:
            locked.append(payload)
        elif entry["ready"]:
            ready.append(payload)
        else:
            known.append(payload)

    meals = []
    for inventory_entry in (getattr(getattr(character, "db", None), "brave_inventory", None) or []):
        template_id = inventory_entry.get("template")
        item = ITEM_TEMPLATES.get(template_id, {})
        quantity = int(inventory_entry.get("quantity", 0) or 0)
        if quantity <= 0 or item.get("kind") != "meal":
            continue
        meals.append(
            {
                "template": template_id,
                "name": item.get("name", template_id),
                "quantity": quantity,
                "summary": item.get("summary", ""),
                "restore_text": _format_meal_restore(item.get("restore", {}), character),
                "bonus_text": _format_meal_bonuses(item.get("meal_bonuses", {}), character),
                "command": f"eat {item.get('name', template_id)}",
            }
        )
    meals.sort(key=lambda entry: entry["name"].lower())

    room = getattr(character, "location", None)
    return {
        "phase": "setup",
        "title": "Kitchen Hearth",
        "spot": getattr(room, "key", None) or "Kitchen Hearth",
        "message": status_message or "",
        "message_tone": status_tone or "muted",
        "ready": ready,
        "known": known,
        "locked": locked,
        "meals": meals,
        "ready_count": len(ready),
        "total_count": len(entries),
        "meal_count": len(meals),
        "can_cook": room_supports_activity(room, "cooking"),
    }


def format_recipe_list(character):
    """Return a readable recipe list showing what the player can make."""

    ready_blocks = []
    known_blocks = []
    locked_blocks = []
    entries = get_cooking_entries(character)
    for entry in entries:
        status = "Ready to cook" if entry["ready"] else ("Missing: " + ", ".join(entry["missing"]) if entry["known"] else "Locked recipe")
        block = format_entry(
            entry["name"],
            details=[entry["ingredient_text"], status],
            summary=entry["summary"] if entry["known"] else (entry["unlock_text"] or "You have not learned this recipe yet."),
        )
        if not entry["known"]:
            locked_blocks.append(block)
        elif entry["ready"]:
            ready_blocks.append(block)
        else:
            known_blocks.append(block)

    return render_screen(
        "Kitchen Hearth",
        subtitle="Simple inn recipes you can turn out without wasting the room or the pan.",
        meta=[f"{sum(1 for entry in entries if entry['ready'])} ready recipes", f"{len(entries)} total recipes"],
        sections=[
            ("Ready Tonight", _stack_recipe_blocks(ready_blocks) if ready_blocks else ["  Nothing is ready from your current pantry."]),
            ("Known Recipes", _stack_recipe_blocks(known_blocks) if known_blocks else ["  No other known recipes are close to ready."]),
            ("Locked Recipes", _stack_recipe_blocks(locked_blocks) if locked_blocks else ["  No locked recipes right now."]),
        ],
    )


def _stack_recipe_blocks(blocks):
    """Join recipe blocks with one blank line between them."""

    lines = []
    for block in blocks:
        if lines:
            lines.append("")
        lines.extend(block)
    return lines


def _match_recipe(query):
    if not query:
        return None

    token = "".join(char for char in query.lower() if char.isalnum())
    matches = []
    for recipe_key, recipe in COOKING_RECIPES.items():
        names = [recipe_key, recipe["name"], ITEM_TEMPLATES[recipe["result"]]["name"]]
        tokens = ["".join(char for char in name.lower() if char.isalnum()) for name in names]
        if any(token == candidate or token in candidate for candidate in tokens):
            matches.append(recipe_key)

    if not matches:
        return None
    return matches[0] if len(matches) == 1 else matches


def describe_cooking_recipe(character, query):
    """Return a readable breakdown for one cooking recipe."""

    match = _match_recipe(query)
    if isinstance(match, list):
        return False, "Be more specific. That could mean: " + ", ".join(COOKING_RECIPES[key]["name"] for key in match)
    if not match:
        return False, "Unknown recipe. Use |wcook|n to review the current hearth menu."

    recipe = COOKING_RECIPES[match]
    meal = ITEM_TEMPLATES.get(recipe["result"], {})
    known = _is_cooking_recipe_known(character, match, recipe)
    ingredient_text = format_ingredient_list(recipe["ingredients"], ITEM_TEMPLATES)
    restore = meal.get("restore", {})
    restore_bits = [f"{pool.upper()} +{value}" for pool, value in restore.items() if value]
    bonus_text = format_bonus_summary({"bonuses": meal.get("meal_bonuses", {})})
    status = "Ready to cook"
    missing = []
    for template_id, quantity in recipe["ingredients"].items():
        have = character.get_inventory_quantity(template_id)
        if have < quantity:
            missing.append(f"{ITEM_TEMPLATES[template_id]['name']} {have}/{quantity}")
    if not known:
        status = "Locked recipe"
    elif missing:
        status = "Missing: " + ", ".join(missing)

    lines = [
        f"|w{recipe['name']}|n",
        f"Ingredients: {ingredient_text}",
        f"Status: {status}",
    ]
    if recipe.get("summary"):
        lines.append(recipe["summary"])
    if not known and recipe.get("unlock_text"):
        lines.append(recipe["unlock_text"])
    if restore_bits:
        lines.append("Restore: " + ", ".join(restore_bits))
    if bonus_text:
        lines.append("Meal bonus: " + bonus_text)
    return True, "\n".join(lines)


def cook_recipe(character, query):
    """Cook a meal from ingredients at the Lantern Rest hearth."""

    room = character.location
    if not room or not room_supports_activity(room, "cooking"):
        return False, "You need a proper hearth before you can cook anything worth eating."

    encounter = character.get_active_encounter()
    if encounter and encounter.is_participant(character):
        return False, "This is not the right moment to start a recipe."

    match = _match_recipe(query)
    if isinstance(match, list):
        return False, "Be more specific. That could mean: " + ", ".join(COOKING_RECIPES[key]["name"] for key in match)
    if not match:
        return False, "Unknown recipe. Use |wcook|n to review the current hearth menu."

    recipe = COOKING_RECIPES[match]
    if not _is_cooking_recipe_known(character, match, recipe):
        return False, recipe.get("unlock_text") or "You have not learned that recipe yet."
    for template_id, quantity in recipe["ingredients"].items():
        if character.get_inventory_quantity(template_id) < quantity:
            return False, (
                f"You do not have enough {ITEM_TEMPLATES[template_id]['name']}. "
                "Use |wpack|n to check your ingredients."
            )

    for template_id, quantity in recipe["ingredients"].items():
        character.remove_item_from_inventory(template_id, quantity)
    character.add_item_to_inventory(recipe["result"], 1)

    meal = ITEM_TEMPLATES[recipe["result"]]
    return True, (
        f"You work the hearth for a few quiet minutes and turn the ingredients into |w{meal['name']}|n. "
        "It goes into your pack."
    )


def _resolve_consumable_match(character, query, *, context="explore", verb=None):
    """Resolve a carried consumable item in a specific use context."""

    return match_inventory_item(character, query, context=context, category="consumable", verb=verb)


from world.activity_item_use import _consume_item_by_template


def use_consumable_template(character, template_id, *, context="explore", verb=None, target=None, encounter=None):
    """Consume one carried item by template id in a specific context."""

    item = ITEM_TEMPLATES.get(template_id)
    if not item:
        return False, "That item does not exist.", None

    use = get_item_use_profile(item, context=context)
    if not use:
        return False, "That item can't be used that way right now.", None
    if verb and use.get("verb") != verb:
        return False, "That item can't be used that way right now.", None
    return _consume_item_by_template(
        character,
        template_id,
        context=context,
        target=target,
        encounter=encounter,
    )


def use_consumable(character, query, *, context="explore", verb=None, target=None, encounter=None):
    """Consume a carried consumable item by fuzzy name."""

    match = _resolve_consumable_match(character, query, context=context, verb=verb)
    if isinstance(match, list):
        return False, "Be more specific. That could mean: " + ", ".join(ITEM_TEMPLATES[key]["name"] for key in match), None
    if not match:
        any_match = _resolve_consumable_match(character, query, context=None, verb=verb)
        if isinstance(any_match, list):
            return False, "Be more specific. That could mean: " + ", ".join(ITEM_TEMPLATES[key]["name"] for key in any_match), None
        if any_match:
            item = ITEM_TEMPLATES.get(any_match, {})
            any_use = get_item_use_profile(item) or {}
            contexts = tuple(any_use.get("contexts") or ())
            if context == "explore" and "combat" in contexts and "explore" not in contexts:
                return False, f"{item.get('name', 'That item')} can only be used in combat.", None
            return False, "That item can't be used that way right now.", None
        return False, "You do not have a usable consumable matching that.", None
    return use_consumable_template(
        character,
        match,
        context=context,
        verb=verb,
        target=target,
        encounter=encounter,
    )


def eat_meal(character, query):
    """Consume a prepared meal and apply its buff."""

    ok, message, _result = use_consumable(character, query, context="explore", verb="eat")
    return ok, message
