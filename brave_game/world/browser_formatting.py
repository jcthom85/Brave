"""Shared formatting helpers for browser-view payloads."""

from world.resonance import get_resource_label, get_stat_label

def _format_context_bonus_summary(bonuses, character):
    if not bonuses:
        return ""

    parts = []
    for key, value in bonuses.items():
        label = get_stat_label(key, character)
        sign = "+" if value >= 0 else ""
        parts.append(f"{label} {sign}{value}")
    return ", ".join(parts)

def _format_restore_summary(restore, character):
    parts = []
    for resource_key in ("hp", "mana", "stamina"):
        amount = restore.get(resource_key, 0)
        if amount:
            parts.append(f"{get_resource_label(resource_key, character)} +{amount}")
    return ", ".join(parts)

def _format_item_value_text(item, quantity):
    value = item.get("value", 0)
    if value <= 0:
        return ""
    if quantity > 1:
        return f"{value} silver each · {value * quantity} total"
    return f"{value} silver"
