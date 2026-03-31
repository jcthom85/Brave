"""Loot helpers for Brave's first combat slice."""

from random import randint, random

from world.data.encounters import ENEMY_TEMPLATES
from world.data.items import ITEM_TEMPLATES


def roll_enemy_rewards(enemy):
    """Roll silver and personal loot for a defeated enemy."""

    template = ENEMY_TEMPLATES[enemy["template_key"]]
    min_silver, max_silver = template.get("silver", (0, 0))
    silver = randint(min_silver, max_silver) if max_silver else 0
    items = []

    for drop in template.get("loot", []):
        if random() > drop.get("chance", 0):
            continue
        quantity = randint(drop.get("min", 1), drop.get("max", 1))
        if quantity > 0:
            items.append((drop["item"], quantity))

    return {"silver": silver, "items": items}


def merge_reward_entries(entries):
    """Combine duplicate loot entries into a stable list."""

    totals = {}
    for template_id, quantity in entries:
        totals[template_id] = totals.get(template_id, 0) + quantity

    return [
        (template_id, totals[template_id])
        for template_id in sorted(totals, key=lambda item_id: ITEM_TEMPLATES[item_id]["name"])
    ]


def format_reward_summary(reward_data):
    """Return a readable summary of a reward bundle."""

    parts = []
    if reward_data.get("silver"):
        parts.append(f"{reward_data['silver']} silver")

    for template_id, quantity in reward_data.get("items", []):
        item_name = ITEM_TEMPLATES[template_id]["name"]
        if quantity == 1:
            parts.append(item_name)
        else:
            parts.append(f"{item_name} x{quantity}")

    return ", ".join(parts)
