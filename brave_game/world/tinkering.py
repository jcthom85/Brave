"""Workbench-style tinkering helpers for Brave."""

from world.content import get_content_registry
from world.data.items import ITEM_TEMPLATES, format_bonus_summary

CONTENT = get_content_registry()
SYSTEMS_CONTENT = CONTENT.systems
TINKERING_RECIPES = SYSTEMS_CONTENT.tinkering_recipes


def _normalize_token(value):
    return "".join(char for char in str(value or "").lower() if char.isalnum())


def is_tinkering_room(room):
    """Return whether the room supports workbench tinkering."""

    if not room:
        return False
    return "tinkering" in set(getattr(room.db, "brave_activities", []) or [])


def _is_recipe_known(character, recipe_key, recipe):
    unlock_type = str(recipe.get("unlock_type") or "auto").lower()
    if unlock_type in {"", "auto", "none"}:
        return True
    known = {str(key).lower() for key in (getattr(getattr(character, "db", None), "brave_known_tinkering_recipes", None) or [])}
    if recipe_key in known:
        return True
    return False


def get_tinkering_entries(character):
    """Return normalized tinkering recipe entries for one character."""

    inventory = {
        entry.get("template"): int(entry.get("quantity", 0) or 0)
        for entry in (character.db.brave_inventory or [])
    }
    entries = []
    for recipe_key, recipe in TINKERING_RECIPES.items():
        base_id = recipe.get("base")
        components = dict(recipe.get("components", {}))
        known = _is_recipe_known(character, recipe_key, recipe)
        missing = []
        base_have = inventory.get(base_id, 0)
        if base_id and base_have < 1:
            missing.append(f"{ITEM_TEMPLATES.get(base_id, {}).get('name', base_id)} {base_have}/1")
        component_rows = []
        for template_id, quantity in components.items():
            owned = inventory.get(template_id, 0)
            component_rows.append(
                {
                    "template_id": template_id,
                    "name": ITEM_TEMPLATES.get(template_id, {}).get("name", template_id),
                    "required": int(quantity or 0),
                    "owned": owned,
                }
            )
            if owned < quantity:
                missing.append(f"{ITEM_TEMPLATES.get(template_id, {}).get('name', template_id)} {owned}/{quantity}")

        result_id = recipe.get("result")
        result_item = ITEM_TEMPLATES.get(result_id, {})
        ready = known and not missing and (character.db.brave_silver or 0) >= int(recipe.get("silver_cost", 0) or 0)
        entries.append(
            {
                "key": recipe_key,
                "name": recipe.get("name", recipe_key.replace("_", " ").title()),
                "summary": recipe.get("summary", ""),
                "known": known,
                "ready": ready,
                "missing": missing,
                "base_id": base_id,
                "base_name": ITEM_TEMPLATES.get(base_id, {}).get("name", base_id) if base_id else "",
                "base_owned": base_have,
                "components": component_rows,
                "result_id": result_id,
                "result_name": result_item.get("name", result_id),
                "result_summary": result_item.get("summary", ""),
                "result_quantity": max(1, int(recipe.get("result_quantity", 1) or 1)),
                "result_bonuses": format_bonus_summary(result_item),
                "silver_cost": max(0, int(recipe.get("silver_cost", 0) or 0)),
                "unlock_text": recipe.get("unlock_text", ""),
            }
        )
    entries.sort(key=lambda entry: (0 if entry["ready"] else 1, 0 if entry["known"] else 1, entry["name"].lower()))
    return entries


def match_tinkering_recipe(query):
    """Resolve one tinkering recipe by fuzzy token."""

    token = _normalize_token(query)
    if not token:
        return None
    exact = []
    partial = []
    for recipe_key, recipe in TINKERING_RECIPES.items():
        names = [recipe_key, recipe.get("name", ""), recipe.get("result", "")]
        normalized = [_normalize_token(name) for name in names if name]
        if any(token == name for name in normalized):
            exact.append(recipe_key)
        elif any(token in name for name in normalized):
            partial.append(recipe_key)
    matches = exact or partial
    if not matches:
        return None
    return matches[0] if len(matches) == 1 else matches


def describe_tinkering_recipe(character, query):
    """Return a readable breakdown for one tinkering design."""

    match = match_tinkering_recipe(query)
    if isinstance(match, list):
        return False, "Be more specific. That could mean: " + ", ".join(TINKERING_RECIPES[key]["name"] for key in match)
    if not match:
        return False, "Unknown design. Use |wtinker|n to review the current workbench ledger."

    recipe = TINKERING_RECIPES[match]
    result_item = ITEM_TEMPLATES.get(recipe.get("result"), {})
    known = _is_recipe_known(character, match, recipe)
    parts = []
    base_id = recipe.get("base")
    if base_id:
        have = character.get_inventory_quantity(base_id)
        parts.append(f"Base: {ITEM_TEMPLATES.get(base_id, {}).get('name', base_id)} {have}/1")
    missing = []
    for template_id, quantity in dict(recipe.get("components", {})).items():
        have = character.get_inventory_quantity(template_id)
        parts.append(f"Part: {ITEM_TEMPLATES.get(template_id, {}).get('name', template_id)} {have}/{quantity}")
        if have < quantity:
            missing.append(f"{ITEM_TEMPLATES.get(template_id, {}).get('name', template_id)} {have}/{quantity}")
    silver_cost = max(0, int(recipe.get("silver_cost", 0) or 0))
    if silver_cost:
        parts.append(f"Silver: {silver_cost}")

    status = "Ready to build"
    if not known:
        status = "Locked design"
    elif missing:
        status = "Missing: " + ", ".join(missing)
    elif (character.db.brave_silver or 0) < silver_cost:
        status = f"Missing silver: {character.db.brave_silver or 0}/{silver_cost}"

    lines = [
        f"|w{recipe.get('name', match.replace('_', ' ').title())}|n",
        f"Status: {status}",
    ]
    lines.extend(parts)
    if recipe.get("summary"):
        lines.append(recipe["summary"])
    if not known and recipe.get("unlock_text"):
        lines.append(recipe["unlock_text"])
    if result_item.get("summary"):
        lines.append("Result: " + result_item["summary"])
    bonus_text = format_bonus_summary(result_item)
    if bonus_text:
        lines.append("Result bonus: " + bonus_text)
    return True, "\n".join(lines)


def perform_tinkering(character, query):
    """Consume materials and create one tinkered result."""

    if not is_tinkering_room(character.location):
        return False, "You need a proper workbench before you can tinker anything worth carrying."
    encounter = character.get_active_encounter()
    if encounter and encounter.is_participant(character):
        return False, "This is not the right moment to spread your kit across a bench."

    match = match_tinkering_recipe(query)
    if isinstance(match, list):
        return False, "Be more specific. That could mean: " + ", ".join(TINKERING_RECIPES[key]["name"] for key in match)
    if not match:
        return False, "Unknown design. Use |wtinker|n to review the current workbench ledger."

    recipe = TINKERING_RECIPES[match]
    if not _is_recipe_known(character, match, recipe):
        return False, recipe.get("unlock_text") or "You do not know that design yet."

    base_id = recipe.get("base")
    if base_id and character.get_inventory_quantity(base_id) < 1:
        return False, f"You need {ITEM_TEMPLATES.get(base_id, {}).get('name', base_id)} before you can start that design."
    for template_id, quantity in dict(recipe.get("components", {})).items():
        if character.get_inventory_quantity(template_id) < quantity:
            return False, f"You do not have enough {ITEM_TEMPLATES.get(template_id, {}).get('name', template_id)}."

    silver_cost = max(0, int(recipe.get("silver_cost", 0) or 0))
    if (character.db.brave_silver or 0) < silver_cost:
        return False, f"You need {silver_cost} silver to finish that work cleanly."

    if base_id:
        character.remove_item_from_inventory(base_id, 1)
    for template_id, quantity in dict(recipe.get("components", {})).items():
        character.remove_item_from_inventory(template_id, quantity)
    if silver_cost:
        character.db.brave_silver = max(0, int(character.db.brave_silver or 0) - silver_cost)

    result_id = recipe.get("result")
    result_quantity = max(1, int(recipe.get("result_quantity", 1) or 1))
    character.add_item_to_inventory(result_id, result_quantity)
    result_item = ITEM_TEMPLATES.get(result_id, {})
    suffix = f" x{result_quantity}" if result_quantity > 1 else ""
    return True, (
        recipe.get("success_text")
        or f"You spread the parts across the bench, work them into shape, and finish |w{result_item.get('name', result_id)}|n{suffix}."
    )
