"""Fishing and cooking helpers for Brave's Brambleford hub."""

from collections.abc import Mapping
from random import randint, random, uniform
from time import time

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
from world.screen_text import format_entry, render_screen

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
SYSTEMS_CONTENT = CONTENT.systems
COOKING_RECIPES = SYSTEMS_CONTENT.cooking_recipes
COZY_BONUS = SYSTEMS_CONTENT.cozy_bonus
FISHING_SPOTS = SYSTEMS_CONTENT.fishing_spots
FISHING_RODS = SYSTEMS_CONTENT.fishing_rods
FISHING_LURES = SYSTEMS_CONTENT.fishing_lures
format_ingredient_list = SYSTEMS_CONTENT.format_ingredient_list

STARTER_FISHING_ROOM_ID = "brambleford_hobbyists_wharf"
STARTER_FISHING_ROD = "loaner_pole"
STARTER_FISHING_LURE = "plain_hook"


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
    return False, "Borrow `fish borrow kit`, `fish borrow rod`, or `fish borrow lure`."


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
    hook_chance = min(0.98, hook_chance + (float(rod.get("stability", 0) or 0) * 0.08))
    if fish_entry.get("item") in set(lure.get("attracts", []) or []):
        hook_chance = min(0.98, hook_chance + 0.04)
    if random() > hook_chance:
        return False, "The line jerks, the hook bites, and then the fish twists free at the last second."

    template_id = fish_entry["item"]
    weight = round(uniform(*fish_entry["weight"]), 1)
    weight = adjust_fishing_weight(character, weight)
    character.add_item_to_inventory(template_id, 1)
    record = _award_catch_record(character, template_id, weight)

    rarity = str(fish_entry.get("rarity") or "common").lower()
    rarity_text = ""
    if rarity in {"rare", "epic"}:
        rarity_text = f" |y({rarity.title()})|n"
    message = f"You land a |w{ITEM_TEMPLATES[template_id]['name']}|n{rarity_text} weighing |w{_format_weight(weight)}|n."
    message += get_fishing_suffix(character)
    if record:
        message += " It is your new best catch on the log."
    return True, message


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
    """Return recipe guidance for the Lantern Rest hearth."""

    lines = [
        "A chalkboard beside the firepot lists a few dependable inn recipes.",
        "",
        "Use |wcook|n to review recipes you can make here and |wcook <recipe>|n to prepare one.",
    ]

    if character:
        lines.append("Use |weat <meal>|n once you are ready to take the buff with you.")

    lines.append("")
    if character:
        for entry in get_cooking_entries(character):
            status = "known" if entry["known"] else "locked"
            lines.append(f"- {entry['name']}: {entry['ingredient_text']} ({status})")
    else:
        for recipe in COOKING_RECIPES.values():
            ingredient_text = format_ingredient_list(recipe["ingredients"], ITEM_TEMPLATES)
            lines.append(f"- {recipe['name']}: {ingredient_text}")

    return "\n".join(lines)


def format_pole_rack_text():
    """Return fishing instructions for the wharf."""

    return (
        "A hand-painted note reads: CHECK YOUR TACKLE WITH `fish tackle`, BORROW STARTER GEAR WITH "
        "`fish borrow kit`, CAST WITH `fish` OR `fish cast`, AND WHEN THE LINE TUGS BACK USE `reel` "
        "BEFORE THE RIVER CHANGES ITS MIND."
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
            ("Ready Tonight", ready_blocks or ["  Nothing is ready from your current pantry."]),
            ("Known Recipes", known_blocks or ["  No other known recipes are close to ready."]),
            ("Locked Recipes", locked_blocks or ["  No locked recipes right now."]),
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


def _consume_item_by_template(character, template_id, *, context="explore", cozy=None, target=None, encounter=None):
    """Consume an item template and apply its current use profile."""

    item = ITEM_TEMPLATES.get(template_id)
    use = get_item_use_profile(item, context=context)
    if not item or not use:
        return False, "That item can't be used that way right now.", None

    effect_type = use.get("effect_type")
    restore = dict(use.get("restore", {}))
    buffs = dict(use.get("buffs", {}))
    cleanse_result = None
    guard_amount = 0
    restore_total = 0
    learned_ability_name = None
    target_type = use.get("target", "self")
    if target_type == "enemy":
        resolved_target = target if isinstance(target, Mapping) else None
    elif target_type in {"ally", "self"}:
        resolved_target = target or character
    else:
        resolved_target = target

    if cozy is None:
        cozy = False
        if effect_type == "meal" and room_supports_activity(character.location, "cooking") and character.db.brave_party_id:
            from world.party import get_present_party_members

            cozy = len(get_present_party_members(character)) >= 2

    if effect_type == "damage" and (not encounter or not isinstance(resolved_target, Mapping)):
        return False, "That item can't be used meaningfully here right now.", None

    if effect_type == "teach_spell":
        required_class = str(use.get("required_class") or "mage").lower()
        if str(getattr(getattr(character, "db", None), "brave_class", "") or "").lower() != required_class:
            return False, f"Only a {required_class.title()} can make sense of that spellbook.", None
        ability_key = CHARACTER_CONTENT.ability_key(use.get("learn_ability"))
        ability = CHARACTER_CONTENT.ability_library.get(ability_key) or {}
        if not ability:
            return False, "The spellbook's notation is incomplete.", None
        learn = getattr(character, "learn_ability", None)
        if callable(learn):
            ok, learn_message = learn(ability_key)
            if not ok:
                return False, learn_message, None
        else:
            learned = [str(key).lower() for key in (getattr(getattr(character, "db", None), "brave_learned_abilities", None) or [])]
            if ability_key in learned:
                return False, f"You already know {ability.get('name', 'that technique')}.", None
            learned.append(ability_key)
            character.db.brave_learned_abilities = learned
        learned_ability_name = ability.get("name", ability_key.replace("_", " ").title())

    if effect_type == "unlock_companion":
        required_class = str(use.get("required_class") or "ranger").lower()
        if str(getattr(getattr(character, "db", None), "brave_class", "") or "").lower() != required_class:
            return False, f"Only a {required_class.title()} can forge that companion bond.", None
        companion_key = str(use.get("unlock_companion") or "").lower()
        unlock = getattr(character, "unlock_companion", None)
        if callable(unlock):
            ok, unlock_message = unlock(companion_key)
            if not ok:
                return False, unlock_message, None
            learned_ability_name = unlock_message
        else:
            return False, "That bond cannot be formed right now.", None

    if effect_type == "unlock_oath":
        required_class = str(use.get("required_class") or "paladin").lower()
        if str(getattr(getattr(character, "db", None), "brave_class", "") or "").lower() != required_class:
            return False, f"Only a {required_class.title()} can swear that oath.", None
        oath_key = str(use.get("unlock_oath") or "").lower()
        unlock = getattr(character, "unlock_oath", None)
        if callable(unlock):
            ok, unlock_message = unlock(oath_key)
            if not ok:
                return False, unlock_message, None
            learned_ability_name = unlock_message
        else:
            return False, "That vow cannot be taken right now.", None

    if effect_type == "unlock_recipe":
        recipe_domain = str(use.get("recipe_domain") or "cooking").lower()
        recipe_key = str(use.get("unlock_recipe") or "").lower()
        if recipe_domain == "cooking":
            unlock = getattr(character, "unlock_cooking_recipe", None)
        elif recipe_domain == "tinkering":
            unlock = getattr(character, "unlock_tinkering_recipe", None)
        else:
            unlock = None
        if callable(unlock):
            ok, unlock_message = unlock(recipe_key)
            if not ok:
                return False, unlock_message, None
            learned_ability_name = unlock_message
        else:
            return False, "That pattern cannot be learned right now.", None

    if target_type == "self" and resolved_target != character:
        return False, "That item can only be used on yourself.", None

    ensure_target = getattr(resolved_target, "ensure_brave_character", None)
    if callable(ensure_target):
        ensure_target()
    if hasattr(resolved_target, "location"):
        if resolved_target != character and getattr(resolved_target, "location", None) != getattr(character, "location", None):
            return False, "That target is not here with you.", None

    if effect_type == "cleanse":
        if not encounter or not hasattr(resolved_target, "db"):
            return False, "That item needs an ally in combat to be useful.", None
        cleanse_result = encounter._clear_one_harmful_effect(resolved_target)
        if not cleanse_result:
            target_name = getattr(resolved_target, "key", character.key)
            return False, f"{target_name} has no harmful effect to clear.", None

    if effect_type == "guard":
        if not encounter or not hasattr(resolved_target, "db"):
            return False, "That item needs an ally in combat to be useful.", None
        guard_amount = max(1, int(use.get("guard", 0) or 0))

    if not character.remove_item_from_inventory(template_id, 1):
        return False, "You can't find that item in your pack anymore.", None

    if effect_type == "meal":
        character.apply_meal_buff(template_id, cozy=bool(cozy))

    if effect_type in {"meal", "restore", "cleanse"} and restore:
        target_character = resolved_target if hasattr(resolved_target, "db") else character
        derived = target_character.db.brave_derived_stats or {}
        resources = dict(target_character.db.brave_resources or {})
        for pool in ("hp", "mana", "stamina"):
            cap = derived.get(f"max_{pool}", 0)
            before = resources.get(pool, 0)
            resources[pool] = min(cap, resources.get(pool, 0) + restore.get(pool, 0))
            restore_total += max(0, resources[pool] - before)
        target_character.db.brave_resources = resources

    if effect_type == "guard":
        state = encounter._get_participant_state(resolved_target)
        state["guard"] = max(int(state.get("guard", 0) or 0), guard_amount)
        encounter._save_participant_state(resolved_target, state)

    if effect_type == "damage":
        damage_spec = dict(use.get("damage", {}))
        base = int(damage_spec.get("base", 0) or 0)
        variance = max(0, int(damage_spec.get("variance", 0) or 0))
        damage = max(1, base + randint(0, variance))
        encounter._damage_enemy(character, resolved_target, damage, extra_text=use.get("extra_text", ""))

    verb = use.get("verb", "use")
    active_bonuses = character.get_active_meal_bonuses() if effect_type == "meal" else buffs
    bonus_text = format_bonus_summary({"bonuses": active_bonuses})
    if verb == "eat":
        player_message = f"You eat the |w{item['name']}|n and feel steadier."
        public_message = f"{character.key} snatches a moment to eat {item['name']}."
    elif verb == "drink":
        player_message = f"You drink the |w{item['name']}|n."
        public_message = f"{character.key} downs {item['name']}."
    elif verb == "apply":
        target_name = getattr(resolved_target, "key", character.key)
        if resolved_target and getattr(resolved_target, "id", None) != character.id:
            player_message = f"You apply the |w{item['name']}|n to {target_name}."
            public_message = f"{character.key} applies {item['name']} to {target_name}."
        else:
            player_message = f"You apply the |w{item['name']}|n."
            public_message = f"{character.key} applies {item['name']}."
    elif verb == "throw":
        target_name = resolved_target.get("key", "the target") if isinstance(resolved_target, Mapping) else "the target"
        player_message = f"You hurl the |w{item['name']}|n at {target_name}."
        public_message = None
    elif verb == "cast":
        target_name = getattr(resolved_target, "key", character.key)
        if resolved_target and getattr(resolved_target, "id", None) != character.id:
            player_message = f"You cast the |w{item['name']}|n over {target_name}."
            public_message = f"{character.key} casts {item['name']} over {target_name}."
        else:
            player_message = f"You cast the |w{item['name']}|n over yourself."
            public_message = f"{character.key} casts {item['name']} over themselves."
    else:
        player_message = f"You use the |w{item['name']}|n."
        public_message = f"{character.key} uses {item['name']}."
    if bonus_text:
        player_message += f" Bonus: {bonus_text}."
    if effect_type in {"unlock_companion", "unlock_oath"}:
        player_message += " " + learned_ability_name
    elif learned_ability_name:
        player_message += f" You commit |w{learned_ability_name}|n to memory."
    if cleanse_result:
        player_message += f" It clears {cleanse_result}."
    if guard_amount:
        player_message += f" Guard rises by {guard_amount}."
    if cozy:
        player_message += " Sharing a warm meal in company leaves you with a lingering |wCozy|n feeling."

    return True, player_message, {
        "template_id": template_id,
        "item": item,
        "use": use,
        "public_message": public_message,
        "cleanse_result": cleanse_result,
        "guard_amount": guard_amount,
        "learned_ability_name": learned_ability_name,
        "restore_total": restore_total,
    }


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
