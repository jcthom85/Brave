"""Fishing and cooking helpers for Brave's Brambleford hub."""

from random import randint, random, uniform
from time import time

from evennia.utils import delay

from world.bootstrap import get_entity
from world.data.activities import COOKING_RECIPES, COZY_BONUS, FISHING_SPOTS, format_ingredient_list
from world.data.items import ITEM_TEMPLATES, format_bonus_summary
from world.screen_text import format_entry, render_screen


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

    fish_entry = _pick_fish(spot)
    character.ndb.brave_fishing = {
        "phase": "waiting",
        "room_id": room_id,
        "started_at": time(),
        "fish": fish_entry,
    }
    bite_delay = randint(*spot["bite_delay"])
    delay(bite_delay, _trigger_bite, character, persistent=False)
    return True, spot["cast_text"]


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
    character.msg("|yA sharp tug runs through the line.|n Use |wreel|n before the fish gets away.")
    delay(spot["reaction_window"], _expire_bite, character, persistent=False)


def _expire_bite(character):
    state = getattr(character.ndb, "brave_fishing", None)
    if not state or state.get("phase") != "bite":
        return
    if time() <= state.get("expires_at", 0):
        return
    _clear_fishing_state(character)
    character.msg("The water settles. Whatever was there slips free before you can set the hook.")


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

    if random() > fish_entry.get("hook_chance", 1.0):
        return False, "The line jerks, the hook bites, and then the fish twists free at the last second."

    template_id = fish_entry["item"]
    weight = round(uniform(*fish_entry["weight"]), 1)
    character.add_item_to_inventory(template_id, 1)
    record = _award_catch_record(character, template_id, weight)

    message = (
        f"You land a |w{ITEM_TEMPLATES[template_id]['name']}|n weighing |w{_format_weight(weight)}|n."
    )
    if record:
        message += " It is your new best catch on the log."
    return True, message


def format_catch_log():
    """Return the current shared Great Catch log text."""

    board = get_entity("great_catch_log")
    records = dict(board.db.brave_catch_records or {}) if board else {}
    lines = [
        "The ledger pages are crowded with fish stories, half-legible boasting, and weights Uncle Pib insists are honest.",
        "",
    ]

    if not records:
        lines.append("No one has posted a proper river triumph yet. The first name is still waiting.")
        return "\n".join(lines)

    overall = max(records.values(), key=lambda entry: entry.get("weight", 0))
    lines.append(
        "Town best: "
        f"{overall['fish']} at {_format_weight(overall['weight'])} by {overall['account']} ({overall['character']})."
    )
    lines.append("")
    lines.append("Family catches:")

    for account_name in sorted(records):
        entry = records[account_name]
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
    for recipe in COOKING_RECIPES.values():
        ingredient_text = format_ingredient_list(recipe["ingredients"], ITEM_TEMPLATES)
        lines.append(f"- {recipe['name']}: {ingredient_text}")

    return "\n".join(lines)


def format_pole_rack_text():
    """Return fishing instructions for the wharf."""

    return (
        "A hand-painted note reads: TAKE A POLE, MIND THE HOOKS, AND USE `fish` WHEN THE RIVER LOOKS "
        "LIKE IT MIGHT BE FEELING GENEROUS. WHEN IT TUGS, USE `reel`."
    )


def format_recipe_list(character):
    """Return a readable recipe list showing what the player can make."""

    inventory = _count_inventory(character)
    recipe_blocks = []
    ready_count = 0

    for recipe_key, recipe in COOKING_RECIPES.items():
        ingredient_text = format_ingredient_list(recipe["ingredients"], ITEM_TEMPLATES)
        missing = []
        for template_id, quantity in recipe["ingredients"].items():
            have = inventory.get(template_id, 0)
            if have < quantity:
                missing.append(f"{ITEM_TEMPLATES[template_id]['name']} {have}/{quantity}")
        if not missing:
            ready_count += 1
        status = "Ready to cook" if not missing else "Missing: " + ", ".join(missing)
        recipe_blocks.append(
            format_entry(
                recipe["name"],
                details=[ingredient_text, status],
                summary=recipe["summary"],
            )
        )

    return render_screen(
        "Kitchen Hearth",
        subtitle="Simple inn recipes you can turn out without wasting the room or the pan.",
        meta=[f"{ready_count} ready recipes", f"{len(COOKING_RECIPES)} total recipes"],
        sections=[("Tonight's Menu", ["  No recipes are posted here."] if not recipe_blocks else _stack_recipe_blocks(recipe_blocks))],
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


def _match_meal(character, query):
    token = "".join(char for char in (query or "").lower() if char.isalnum())
    matches = []
    for entry in (character.db.brave_inventory or []):
        template_id = entry.get("template")
        template = ITEM_TEMPLATES.get(template_id)
        if not template or template.get("kind") != "meal":
            continue
        names = [template_id, template["name"]]
        tokens = ["".join(char for char in name.lower() if char.isalnum()) for name in names]
        if any(token == candidate or token in candidate for candidate in tokens):
            matches.append(template_id)
    if not matches:
        return None
    return matches[0] if len(matches) == 1 else matches


def eat_meal(character, query):
    """Consume a prepared meal and apply its buff."""

    match = _match_meal(character, query)
    if isinstance(match, list):
        return False, "Be more specific. That could mean: " + ", ".join(ITEM_TEMPLATES[key]["name"] for key in match)
    if not match:
        return False, "You do not have that meal. Use |wpack|n to check your carried food."

    meal = ITEM_TEMPLATES[match]
    cozy = False
    if room_supports_activity(character.location, "cooking") and character.db.brave_party_id:
        from world.party import get_present_party_members

        cozy = len(get_present_party_members(character)) >= 2

    if not character.remove_item_from_inventory(match, 1):
        return False, "You cannot find that meal in your pack anymore."

    character.apply_meal_buff(match, cozy=cozy)

    restore = meal.get("restore", {})
    derived = character.db.brave_derived_stats or {}
    resources = dict(character.db.brave_resources or {})
    for pool in ("hp", "mana", "stamina"):
        cap = derived.get(f"max_{pool}", 0)
        resources[pool] = min(cap, resources.get(pool, 0) + restore.get(pool, 0))
    character.db.brave_resources = resources

    bonus_text = format_bonus_summary({"bonuses": character.get_active_meal_bonuses()})
    message = f"You eat the |w{meal['name']}|n and feel steadier."
    if bonus_text:
        message += f" Meal bonus: {bonus_text}."
    if cozy:
        message += " Sharing a warm meal in company leaves you with a lingering |wCozy|n feeling."
    return True, message
