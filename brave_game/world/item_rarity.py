"""UI helpers for Brave item rarity metadata."""

from world.data.items import (
    get_item_rarity_key,
    get_item_rarity_label,
    get_item_rarity_tone,
)


def build_item_rarity_display(item_or_template):
    """Return standard UI fields for coloring an item name by rarity."""

    if not item_or_template:
        return {}
    return {
        "rarity_key": get_item_rarity_key(item_or_template),
        "rarity_label": get_item_rarity_label(item_or_template),
        "rarity_tone": get_item_rarity_tone(item_or_template),
    }


def build_item_rarity_chip(item_or_template):
    """Return a standard chip for explicit rarity labeling."""

    display = build_item_rarity_display(item_or_template)
    if not display:
        return None
    return {
        "label": display["rarity_label"],
        "icon": "diamond",
        "tone": display["rarity_tone"],
    }
