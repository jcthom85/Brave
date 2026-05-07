"""Town commerce helpers for configurable Brave shops."""

from world.content import get_content_registry


def _registry():
    return get_content_registry()


def _items():
    return _registry().items.item_templates


def _quests():
    return _registry().quests.quests


def _systems():
    return _registry().systems


def _fallback_outfitters_shop():
    return {
        "name": "Brambleford Outfitters",
        "room_id": _systems().outfitters_room_id,
        "keeper_entity_id": "leda_thornwick",
        "summary": "Leda buys practical finds and pays in clean town silver.",
        "buys_kinds": ["loot", "ingredient", "consumable", "meal", "equipment"],
        "sell_price_multiplier": 1.0,
        "shift_outcomes": [],
        "stock": [],
    }


def _all_shops():
    systems = _systems()
    shops = dict(getattr(systems, "shops", {}) or {})
    if "brambleford_outfitters" not in shops and systems.outfitters_room_id:
        shops["brambleford_outfitters"] = _fallback_outfitters_shop()
    return shops


def get_shop(shop_id):
    """Return a configured shop by id."""

    return _all_shops().get(shop_id)


def get_shop_for_room(room):
    """Return ``(shop_id, shop_data)`` for the character's current room."""

    room_id = getattr(getattr(room, "db", None), "brave_room_id", None) if room else None
    if not room_id:
        return None, None
    for shop_id, shop in _all_shops().items():
        if shop.get("room_id") == room_id:
            return shop_id, shop
    return None, None


def is_shop_room(room):
    """Return whether the given room hosts a configured shop."""

    _shop_id, shop = get_shop_for_room(room)
    return bool(shop)


def is_outfitters_room(room):
    """Return whether the given room is the configured Outfitters shop."""

    shop_id, _shop = get_shop_for_room(room)
    return shop_id == "brambleford_outfitters" if shop_id else False


def get_shop_bonus(character, shop_id=None):
    """Return the current active merchant bonus, if any."""

    return {}


def clear_shop_bonus(character):
    """Clear any current shop bonus."""

    character.db.brave_shop_bonus = {}


def format_shop_bonus(bonus):
    """Return a readable merchant-bonus summary."""

    return "No current merchant bonus."


def get_sale_price(template_id, quantity=1, bonus_pct=0, shop=None):
    """Return the silver payout for an item sale."""

    template = _items().get(template_id, {})
    value = template.get("value", 0)
    if quantity <= 0 or value <= 0:
        return 0
    shop_multiplier = float((shop or {}).get("sell_price_multiplier", 1.0) or 1.0)
    return max(1, int(round(value * quantity * shop_multiplier)))


def _shop_buys_item(shop, template):
    kinds = [str(kind or "").strip().lower() for kind in (shop or {}).get("buys_kinds", [])]
    if not kinds:
        return False
    return str(template.get("kind") or "").strip().lower() in kinds


def get_reserved_quantity(character, template_id):
    """Return how many copies of an item should be kept for active collect quests."""

    reserved = 0
    quest_log = character.db.brave_quests or {}
    for quest_key, state in quest_log.items():
        if state.get("status") != "active":
            continue

        definition = _quests().get(quest_key)
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


def get_sellable_entries(character, shop=None, shop_id=None):
    """Return sellable pack entries with current merchant pricing."""

    if shop is None:
        resolved_id, shop = get_shop_for_room(getattr(character, "location", None))
        shop_id = shop_id or resolved_id
    shop = shop or _fallback_outfitters_shop()
    entries = []

    for entry in character.db.brave_inventory or []:
        template_id = entry.get("template")
        template = _items().get(template_id)
        if not template or template.get("value", 0) <= 0 or not _shop_buys_item(shop, template):
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
                "unit_price": get_sale_price(template_id, quantity=1, shop=shop),
                "total_price": get_sale_price(template_id, quantity=sellable, shop=shop),
            }
        )

    entries.sort(key=lambda entry: entry["name"])
    return entries


def get_reserved_entries(character):
    """Return pack entries currently being held for active quests."""

    entries = []
    for entry in character.db.brave_inventory or []:
        template_id = entry.get("template")
        template = _items().get(template_id)
        if not template:
            continue
        reserved = min(entry.get("quantity", 0), get_reserved_quantity(character, template_id))
        if reserved <= 0:
            continue
        entries.append({"template_id": template_id, "name": template["name"], "reserved": reserved})

    entries.sort(key=lambda entry: entry["name"])
    return entries


def get_buyable_entries(character, shop=None):
    """Return stock entries the character can buy at the current shop."""

    if shop is None:
        _shop_id, shop = get_shop_for_room(getattr(character, "location", None))
    if not shop:
        return []
    completed = {
        quest_key
        for quest_key, state in (character.db.brave_quests or {}).items()
        if state.get("status") == "completed"
    }
    entries = []
    for stock in shop.get("stock", []) or []:
        template_id = stock.get("item")
        template = _items().get(template_id)
        if not template:
            continue
        unlocks = [quest_key for quest_key in stock.get("unlock_completed_quests", []) or [] if quest_key]
        locked = any(quest_key not in completed for quest_key in unlocks)
        price = int(stock.get("price", 0) or 0)
        if price <= 0:
            continue
        entries.append(
            {
                "template_id": template_id,
                "name": stock.get("label") or template.get("name", template_id),
                "summary": template.get("summary"),
                "price": price,
                "locked": locked,
                "unlock_completed_quests": unlocks,
                "kind": template.get("kind"),
            }
        )
    entries.sort(key=lambda entry: (entry["locked"], entry["name"]))
    return entries


def run_shop_shift(character):
    """Return that shop counter work is not currently a supported activity."""

    shop_id, shop = get_shop_for_room(getattr(character, "location", None))
    if not shop:
        shop_id, shop = "brambleford_outfitters", get_shop("brambleford_outfitters") or _fallback_outfitters_shop()
    clear_shop_bonus(character)
    return False, f"{shop.get('name', 'This shop')} is not taking counter help right now."


def sell_inventory_item(character, template_id, quantity):
    """Sell a quantity of one pack item for silver."""

    shop_id, shop = get_shop_for_room(getattr(character, "location", None))
    if not shop:
        return False, "You need to be at a shop to sell anything."
    template = _items().get(template_id)
    if not template or template.get("value", 0) <= 0 or not _shop_buys_item(shop, template):
        return False, f"That item is not something {shop.get('name', 'this shop')} will buy."

    owned = character.get_inventory_quantity(template_id)
    reserved = min(owned, get_reserved_quantity(character, template_id))
    sellable = owned - reserved
    if sellable <= 0:
        return False, "You should keep that for an active quest."
    if quantity <= 0:
        return False, "Sell how many?"
    if quantity > sellable:
        return False, f"You can only sell {sellable} right now."

    silver = get_sale_price(template_id, quantity=quantity, shop=shop)
    if not character.remove_item_from_inventory(template_id, quantity):
        return False, "You can't seem to find that many in your pack anymore."

    character.db.brave_silver = (character.db.brave_silver or 0) + silver

    clear_shop_bonus(character)

    result = {
        "item_name": template["name"],
        "quantity": quantity,
        "silver": silver,
        "expired_bonus": False,
        "remaining_bonus": {},
    }
    return True, result


def buy_shop_item(character, template_id, quantity=1):
    """Buy a quantity of one infinite-stock shop item."""

    _shop_id, shop = get_shop_for_room(getattr(character, "location", None))
    if not shop:
        return False, "You need to be at a shop to buy anything."
    if quantity <= 0:
        return False, "Buy how many?"
    entries = {entry["template_id"]: entry for entry in get_buyable_entries(character, shop=shop)}
    entry = entries.get(template_id)
    if not entry:
        return False, f"{shop.get('name', 'This shop')} does not stock that."
    if entry.get("locked"):
        return False, "That stock is not available to you yet."
    total = entry["price"] * quantity
    if (character.db.brave_silver or 0) < total:
        return False, f"You need {total} silver."
    character.db.brave_silver = max(0, (character.db.brave_silver or 0) - total)
    character.add_item_to_inventory(template_id, quantity, count_for_collection=False)
    return True, {"item_name": entry["name"], "quantity": quantity, "silver": total}
