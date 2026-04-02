"""Shared combat action payload helpers for browser combat views."""

from world.data.character_options import ABILITY_LIBRARY, IMPLEMENTED_ABILITY_KEYS
from world.data.items import ITEM_TEMPLATES, get_item_use_profile
from world.resonance import format_ability_display, get_resource_label, get_stat_label, resolve_ability_query


TARGET_BADGES = {
    "self": "S",
    "enemy": "E",
    "ally": "A",
    "none": "N",
}

RESOURCE_SHORT_LABELS = {
    "mana": "MP",
    "stamina": "STA",
}


def _ordered_participants(encounter, character):
    participants = encounter.get_active_participants()
    return sorted(
        participants,
        key=lambda participant: (0 if participant.id == character.id else 1, participant.key.lower()),
    )


def _short_resource_label(resource_key, character):
    return RESOURCE_SHORT_LABELS.get(resource_key, get_resource_label(resource_key, character)[:3].upper())


def _enemy_picker(title, command_prefix, enemies):
    return {
        "title": title,
        "subtitle": "Choose an enemy.",
        "options": [
            {
                "label": enemy["key"],
                "command": f"{command_prefix} = {enemy['id']}",
                "icon": "warning",
                "meta": enemy["id"].upper(),
                "tone": "danger",
            }
            for enemy in enemies
        ],
    }


def _ally_picker(title, command_prefix, ordered_participants, character):
    return {
        "title": title,
        "subtitle": "Choose an ally.",
        "options": [
            {
                "label": participant.key,
                "command": command_prefix if participant.id == character.id else f"{command_prefix} = {participant.key}",
                "icon": "person",
                "meta": "You" if participant.id == character.id else "Ally",
                "tone": "accent" if participant.id == character.id else "good",
            }
            for participant in ordered_participants
        ],
    }


def _finalize_action(action):
    has_inline_picker = any(entry.get("picker") for entry in (action.get("actions") or []))
    action["enabled"] = bool(action.get("command") or action.get("picker") or action.get("actions"))
    if (action.get("picker") or has_inline_picker) and action.get("command"):
        action["selection_mode"] = "command+picker"
    elif action.get("picker"):
        action["selection_mode"] = "picker"
    elif has_inline_picker:
        action["selection_mode"] = "picker"
    elif action.get("command"):
        action["selection_mode"] = "command"
    else:
        action["selection_mode"] = "disabled"
    return action


def build_combat_ability_actions(encounter, character):
    """Return normalized browser payloads for combat abilities."""

    enemies = encounter.get_active_enemies()
    ordered_participants = _ordered_participants(encounter, character)
    ability_actions = []

    for unlocked_name in character.get_unlocked_abilities():
        ability_key = resolve_ability_query(character, unlocked_name)
        if isinstance(ability_key, list) or not ability_key:
            continue
        if ability_key not in IMPLEMENTED_ABILITY_KEYS:
            continue
        ability = ABILITY_LIBRARY.get(ability_key)
        if not ability:
            continue

        target_mode = ability["target"]
        resource_key = ability["resource"]
        resource_current = (character.db.brave_resources or {}).get(resource_key, 0)
        command_prefix = f"use {unlocked_name}"
        display_name = format_ability_display(unlocked_name, character)
        text = f"{display_name} · {ability['cost']} {_short_resource_label(resource_key, character)}"
        action = {
            "id": f"ability:{ability_key}",
            "kind": "ability",
            "key": ability_key,
            "label": display_name,
            "source_label": unlocked_name,
            "text": text,
            "badge": TARGET_BADGES.get(target_mode, "?"),
            "target_mode": target_mode,
            "resource_key": resource_key,
            "resource_cost": ability["cost"],
            "resource_current": resource_current,
            "command": None,
            "picker": None,
            "actions": None,
            "disabled_reason": None,
        }

        if resource_current < ability["cost"]:
            action["text"] += f" · NEED {ability['cost'] - resource_current}"
            action["disabled_reason"] = "Insufficient resources."
            ability_actions.append(_finalize_action(action))
            continue

        if target_mode == "enemy":
            if not enemies:
                action["text"] += " · NO FOE"
                action["disabled_reason"] = "No foes available."
            elif len(enemies) == 1:
                action["command"] = f"{command_prefix} = {enemies[0]['id']}"
            else:
                action["picker"] = _enemy_picker(f"{display_name} Target", command_prefix, enemies)
        elif target_mode == "ally":
            if not ordered_participants:
                action["text"] += " · NO ALLY"
                action["disabled_reason"] = "No allies available."
            elif len(ordered_participants) == 1:
                action["command"] = command_prefix
            else:
                action["picker"] = _ally_picker(f"{display_name} Target", command_prefix, ordered_participants, character)
        else:
            action["command"] = command_prefix

        ability_actions.append(_finalize_action(action))

    return ability_actions


def build_combat_item_actions(encounter, character):
    """Return normalized browser payloads for combat items."""

    enemies = encounter.get_active_enemies()
    ordered_participants = _ordered_participants(encounter, character)
    item_actions = []

    for entry in (character.db.brave_inventory or []):
        template_id = entry.get("template")
        quantity = int(entry.get("quantity", 0) or 0)
        item = ITEM_TEMPLATES.get(template_id, {})
        use = get_item_use_profile(item, context="combat") or {}
        if quantity <= 0 or not use:
            continue

        label = item.get("name", template_id)
        restore_parts = []
        for resource_key, short_label in (("hp", "HP"), ("mana", "MP"), ("stamina", "STA")):
            amount = int((use.get("restore", {}) or {}).get(resource_key, 0) or 0)
            if amount > 0:
                restore_parts.append(f"{short_label}+{amount}")

        text = label
        if restore_parts:
            text += " · " + " · ".join(restore_parts)

        buff_parts = []
        for stat_key, amount in (use.get("buffs", {}) or {}).items():
            if amount:
                buff_parts.append(f"{get_stat_label(stat_key, character)}+{amount}")
        if buff_parts:
            text += " · " + buff_parts[0]
        if use.get("effect_type") == "cleanse":
            text += " · CLEANSE"
        if use.get("effect_type") == "guard":
            text += f" · GUARD {int(use.get('guard', 0) or 0)}"
        damage_spec = dict(use.get("damage", {}))
        if damage_spec.get("base"):
            low = int(damage_spec.get("base", 0) or 0)
            high = low + max(0, int(damage_spec.get("variance", 0) or 0))
            text += f" · DMG {low}-{high}" if high > low else f" · DMG {low}"

        target_mode = use.get("target", "self")
        command_prefix = f"use {label}"
        action = {
            "id": f"item:{template_id}",
            "kind": "item",
            "key": template_id,
            "label": label,
            "text": text,
            "badge": str(quantity),
            "target_mode": target_mode,
            "quantity": quantity,
            "command": None,
            "picker": None,
            "actions": None,
            "disabled_reason": None,
            "effect_type": use.get("effect_type"),
        }

        if target_mode == "enemy":
            if not enemies:
                action["text"] += " · NO FOE"
                action["disabled_reason"] = "No foes available."
            elif len(enemies) == 1:
                action["command"] = f"{command_prefix} = {enemies[0]['id']}"
            else:
                action["picker"] = _enemy_picker(f"{label} Target", command_prefix, enemies)
        elif target_mode == "ally":
            if not ordered_participants:
                action["text"] += " · NO ALLY"
                action["disabled_reason"] = "No allies available."
            else:
                action["command"] = command_prefix
                if len(ordered_participants) > 1:
                    picker = _ally_picker(f"{label} Target", command_prefix, ordered_participants, character)
                    action["actions"] = [{
                        "label": "Target Ally",
                        "icon": "person",
                        "tone": "muted",
                        "picker": picker,
                    }]
        else:
            action["command"] = command_prefix

        item_actions.append(_finalize_action(action))

    return item_actions


def build_combat_action_payload(encounter, character):
    """Return the normalized combat action payload for a browser combat view."""

    return {
        "abilities": build_combat_ability_actions(encounter, character),
        "items": build_combat_item_actions(encounter, character),
    }
