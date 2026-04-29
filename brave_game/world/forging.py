"""Equipment upgrade helpers for Ironroot Forge."""

from world.content import get_content_registry
from world.data.items import EQUIPMENT_SLOTS, ITEM_TEMPLATES, format_bonus_summary
from world.race_world_hooks import get_forge_silver_discount

CONTENT = get_content_registry()
SYSTEMS_CONTENT = CONTENT.systems
FORGE_ROOM_ID = SYSTEMS_CONTENT.forge_room_id
FORGE_RECIPES = SYSTEMS_CONTENT.forge_recipes


def _get_slot_for_template(template_id):
    """Return the equipment slot for a given template id."""

    return ITEM_TEMPLATES.get(template_id, {}).get("slot")


def is_forge_room(room):
    """Return whether the given room is Ironroot Forge."""

    return getattr(room.db, "brave_room_id", None) == FORGE_ROOM_ID if room else False


def get_forge_entries(character):
    """Return current forge upgrade options for equipped gear."""

    equipment = dict(character.db.brave_equipment or {})
    entries = []

    for slot in EQUIPMENT_SLOTS:
        template_id = equipment.get(slot)
        recipe = FORGE_RECIPES.get(template_id)
        if not recipe:
            continue

        source_item = ITEM_TEMPLATES.get(template_id, {})
        result_template_id = recipe["result"]
        result_item = ITEM_TEMPLATES.get(result_template_id, {})
        materials = []
        silver_cost = max(0, int(recipe["silver"] or 0) - get_forge_silver_discount(character))
        ready = (character.db.brave_silver or 0) >= silver_cost

        for material_id, required in recipe.get("materials", {}).items():
            owned = character.get_inventory_quantity(material_id)
            materials.append(
                {
                    "template_id": material_id,
                    "name": ITEM_TEMPLATES[material_id]["name"],
                    "required": required,
                    "owned": owned,
                }
            )
            if owned < required:
                ready = False

        entries.append(
            {
                "slot": slot,
                "slot_label": slot.replace("_", " ").title(),
                "source_template_id": template_id,
                "source_name": source_item.get("name", template_id),
                "result_template_id": result_template_id,
                "result_name": result_item.get("name", result_template_id),
                "silver_cost": silver_cost,
                "silver_on_hand": character.db.brave_silver or 0,
                "materials": materials,
                "ready": ready,
                "result_bonuses": format_bonus_summary(result_item),
                "text": recipe.get("text", ""),
            }
        )

    entries.sort(key=lambda entry: EQUIPMENT_SLOTS.index(entry["slot"]))
    return entries


def apply_forge_upgrade(character, source_template_id):
    """Apply one forge recipe to the currently equipped item."""

    recipe = FORGE_RECIPES.get(source_template_id)
    if not recipe:
        return False, "Torren doesn't have a standing upgrade plan for that piece."

    slot = _get_slot_for_template(source_template_id)
    equipped = (character.db.brave_equipment or {}).get(slot)
    if equipped != source_template_id:
        return False, "You need to be wearing the piece you want Torren to rework."

    silver_cost = max(0, int(recipe["silver"] or 0) - get_forge_silver_discount(character))
    if (character.db.brave_silver or 0) < silver_cost:
        return False, f"You need {silver_cost} silver for that rework."

    missing = []
    for material_id, required in recipe.get("materials", {}).items():
        owned = character.get_inventory_quantity(material_id)
        if owned < required:
            missing.append(f"{ITEM_TEMPLATES[material_id]['name']} {owned}/{required}")

    if missing:
        return False, "You are still short on: " + ", ".join(missing)

    for material_id, required in recipe.get("materials", {}).items():
        if not character.remove_item_from_inventory(material_id, required):
            return False, "Torren pauses. Your pack contents no longer match the order."

    character.db.brave_silver = max(0, (character.db.brave_silver or 0) - silver_cost)
    equipment = dict(character.db.brave_equipment or {})
    equipment[slot] = recipe["result"]
    character.db.brave_equipment = equipment
    character.recalculate_stats()

    result_item = ITEM_TEMPLATES[recipe["result"]]
    result = {
        "slot": slot,
        "slot_label": slot.replace("_", " ").title(),
        "item_name": result_item["name"],
        "bonus_summary": format_bonus_summary(result_item),
        "silver_cost": silver_cost,
        "text": recipe.get("text", ""),
    }
    return True, result
