"""Town commerce helpers for Brambleford Outfitters."""

import random

from world.content import get_content_registry
from world.data.items import ITEM_TEMPLATES
from world.race_world_hooks import get_shift_sales_bonus

CONTENT = get_content_registry()
QUESTS = CONTENT.quests.quests
SYSTEMS_CONTENT = CONTENT.systems
OUTFITTERS_ROOM_ID = SYSTEMS_CONTENT.outfitters_room_id
SHIFT_OUTCOMES = list(SYSTEMS_CONTENT.shift_outcomes)


def is_outfitters_room(room):
    """Return whether the given room is Brambleford Outfitters."""

    return getattr(room.db, "brave_room_id", None) == OUTFITTERS_ROOM_ID if room else False


def get_shop_bonus(character):
    """Return the current active merchant bonus, if any."""

    bonus = dict(character.db.brave_shop_bonus or {})
    if bonus.get("bonus_pct", 0) <= 0 or bonus.get("sales_left", 0) <= 0:
        return {}
    return bonus


def clear_shop_bonus(character):
    """Clear any current shop bonus."""

    character.db.brave_shop_bonus = {}


def format_shop_bonus(bonus):
    """Return a readable merchant-bonus summary."""

    if not bonus:
        return "No current merchant bonus."
    sales_left = bonus.get("sales_left", 0)
    label = "sale" if sales_left == 1 else "sales"
    return f"{bonus.get('name', 'Merchant Bonus')} (+{bonus['bonus_pct']}% on next {sales_left} {label})"


def get_sale_price(template_id, quantity=1, bonus_pct=0):
    """Return the silver payout for an item sale."""

    template = ITEM_TEMPLATES.get(template_id, {})
    value = template.get("value", 0)
    if quantity <= 0 or value <= 0:
        return 0
    multiplier = (100 + max(0, bonus_pct)) / 100.0
    return max(1, int(round(value * quantity * multiplier)))


def get_reserved_quantity(character, template_id):
    """Return how many copies of an item should be kept for active collect quests."""

    reserved = 0
    quest_log = character.db.brave_quests or {}
    for quest_key, state in quest_log.items():
        if state.get("status") != "active":
            continue

        definition = QUESTS.get(quest_key)
        if not definition:
            continue

        for index, objective in enumerate(definition.get("objectives", [])):
            if objective.get("type") != "collect_item":
                continue
            if objective.get("item_id") != template_id:
                continue

            objectives = state.get("objectives", [])
            if index >= len(objectives):
                continue
            objective_state = objectives[index]
            if objective_state.get("completed"):
                continue

            required = objective_state.get("required", objective.get("count", 1))
            progress = min(required, objective_state.get("progress", 0))
            reserved += max(0, required - progress)

    return reserved


def get_sellable_entries(character):
    """Return sellable pack entries with current merchant pricing."""

    bonus = get_shop_bonus(character)
    bonus_pct = bonus.get("bonus_pct", 0)
    entries = []

    for entry in character.db.brave_inventory or []:
        template_id = entry.get("template")
        template = ITEM_TEMPLATES.get(template_id)
        if not template or template.get("value", 0) <= 0:
            continue

        quantity = entry.get("quantity", 0)
        reserved = min(quantity, get_reserved_quantity(character, template_id))
        sellable = quantity - reserved
        if sellable <= 0:
            continue

        entries.append(
            {
                "template_id": template_id,
                "name": template["name"],
                "quantity": quantity,
                "reserved": reserved,
                "sellable": sellable,
                "unit_price": get_sale_price(template_id, quantity=1, bonus_pct=bonus_pct),
                "total_price": get_sale_price(template_id, quantity=sellable, bonus_pct=bonus_pct),
            }
        )

    entries.sort(key=lambda entry: entry["name"])
    return entries


def get_reserved_entries(character):
    """Return pack entries currently being held for active quests."""

    entries = []
    for entry in character.db.brave_inventory or []:
        template_id = entry.get("template")
        template = ITEM_TEMPLATES.get(template_id)
        if not template:
            continue
        reserved = min(entry.get("quantity", 0), get_reserved_quantity(character, template_id))
        if reserved <= 0:
            continue
        entries.append({"template_id": template_id, "name": template["name"], "reserved": reserved})

    entries.sort(key=lambda entry: entry["name"])
    return entries


def run_shop_shift(character):
    """Grant a temporary merchant bonus from helping at the Outfitters."""

    current = get_shop_bonus(character)
    if current:
        return False, (
            "Leda waves you off for now. You already have |w"
            + format_shop_bonus(current)
            + "|n waiting on the next few sales."
        )

    outcome = random.choice(SHIFT_OUTCOMES)
    sales_left = outcome["sales_left"] + get_shift_sales_bonus(character)
    character.db.brave_shop_bonus = {
        "name": outcome["name"],
        "bonus_pct": outcome["bonus_pct"],
        "sales_left": sales_left,
    }
    message = outcome["text"] + " " + f"You gain |w{format_shop_bonus(character.db.brave_shop_bonus)}|n."
    if get_shift_sales_bonus(character):
        message += " Your practical instincts buy you one extra favorable sale."
    return True, message


def sell_inventory_item(character, template_id, quantity):
    """Sell a quantity of one pack item for silver."""

    template = ITEM_TEMPLATES.get(template_id)
    if not template or template.get("value", 0) <= 0:
        return False, "That item is not something the Outfitters will buy."

    owned = character.get_inventory_quantity(template_id)
    reserved = min(owned, get_reserved_quantity(character, template_id))
    sellable = owned - reserved
    if sellable <= 0:
        return False, "You should keep that for an active quest."
    if quantity <= 0:
        return False, "Sell how many?"
    if quantity > sellable:
        return False, f"You can only sell {sellable} right now."

    bonus = get_shop_bonus(character)
    silver = get_sale_price(template_id, quantity=quantity, bonus_pct=bonus.get("bonus_pct", 0))
    if not character.remove_item_from_inventory(template_id, quantity):
        return False, "You can't seem to find that many in your pack anymore."

    character.db.brave_silver = (character.db.brave_silver or 0) + silver

    expired = False
    if bonus:
        bonus["sales_left"] = max(0, bonus.get("sales_left", 0) - 1)
        if bonus["sales_left"] <= 0:
            expired = True
            clear_shop_bonus(character)
        else:
            character.db.brave_shop_bonus = bonus

    result = {
        "item_name": template["name"],
        "quantity": quantity,
        "silver": silver,
        "expired_bonus": expired,
        "remaining_bonus": get_shop_bonus(character),
    }
    return True, result
