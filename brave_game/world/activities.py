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
from world.screen_text import format_entry, render_screen

CONTENT = get_content_registry()
SYSTEMS_CONTENT = CONTENT.systems
COOKING_RECIPES = SYSTEMS_CONTENT.cooking_recipes
COZY_BONUS = SYSTEMS_CONTENT.cozy_bonus
FISHING_SPOTS = SYSTEMS_CONTENT.fishing_spots
format_ingredient_list = SYSTEMS_CONTENT.format_ingredient_list


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
        lines.append("Best rhythm: |wrest|n, check |wpack|n, |wcook|n if you can, then |weat|n right before you head back out.")

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
        sections=[
            ("Tonight's Menu", ["  No recipes are posted here."] if not recipe_blocks else _stack_recipe_blocks(recipe_blocks)),
            (
                "Road Prep",
                [
                    "  Good rhythm: rest first, cook while you are safe, then eat just before you leave town.",
                    "  Meals restore resources and carry a buff into the next stretch.",
                ],
            ),
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
