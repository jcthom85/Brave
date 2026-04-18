"""Shared combat action payload helpers for browser combat views."""

from world.content import get_content_registry
from world.combat_atb import get_ability_atb_profile, get_item_atb_profile
from world.enemy_icons import get_enemy_icon_name
from world.data.items import ITEM_TEMPLATES, get_item_use_profile

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
ABILITY_LIBRARY = CHARACTER_CONTENT.ability_library
IMPLEMENTED_ABILITY_KEYS = CHARACTER_CONTENT.implemented_ability_keys
from world.resonance import format_ability_display, get_resource_label, get_stat_label, resolve_ability_query


TARGET_BADGES = {
    "self": "S",
    "enemy": "E",
    "ally": "A",
    "none": "N",
}

REACTION_ABILITY_KEYS = {
    "interrupt": {"shieldbash", "cheapshot", "frostbind", "entanglingroots"},
    "guard": {"intercept", "defend", "brace", "guardingaura", "shieldofdawn"},
    "cleanse": {"cleanse", "renewinglight", "blessing", "livingcurrent"},
}

REACTION_ITEM_EFFECT_TYPES = {
    "guard": "guard",
    "cleanse": "cleanse",
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


def _enemy_display_options(enemies):
    totals = {}
    for enemy in enemies:
        group_key = str(enemy.get("template_key") or enemy.get("key") or enemy.get("id") or "").strip().lower()
        totals[group_key] = totals.get(group_key, 0) + 1

    seen = {}
    options = []
    for enemy in enemies:
        group_key = str(enemy.get("template_key") or enemy.get("key") or enemy.get("id") or "").strip().lower()
        seen[group_key] = seen.get(group_key, 0) + 1
        label = str(enemy.get("key") or "Enemy")
        if totals.get(group_key, 0) > 1 and not label.rsplit(" ", 1)[-1].isdigit():
            label = f"{label} {seen[group_key]}"
        options.append((label, enemy))
    return options


def _enemy_option_icon(enemy):
    enemy = dict(enemy or {})
    template_key = str(enemy.get("template_key") or "").strip().lower()
    return str(enemy.get("icon") or get_enemy_icon_name(template_key, enemy))


def _enemy_picker(title, command_prefix, enemies):
    return {
        "title": title,
        "subtitle": "Choose an enemy.",
        "options": [
            {
                "label": label,
                "command": f"{command_prefix} = {enemy['id']}",
                "icon": _enemy_option_icon(enemy),
                "tone": "danger",
            }
            for label, enemy in _enemy_display_options(enemies)
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


def _reaction_role_for_ability(ability_key):
    normalized = str(ability_key or "").lower()
    for role, keys in REACTION_ABILITY_KEYS.items():
        if normalized in keys:
            return role
    return None


def _reaction_role_for_item(use):
    effect_type = str((use or {}).get("effect_type", "") or "").lower()
    return REACTION_ITEM_EFFECT_TYPES.get(effect_type)


def _timing_tooltip(timing, *, reaction_role=None, summary=None):
    timing = dict(timing or {})
    timing_parts = [
        f"ATB {int(timing.get('gauge_cost', 100) or 100)}",
        f"windup {int(timing.get('windup_ticks', 0) or 0)}",
        f"recovery {int(timing.get('recovery_ticks', 0) or 0)}",
    ]
    cooldown = int(timing.get("cooldown_ticks", 0) or 0)
    if cooldown > 0:
        timing_parts.append(f"cooldown {cooldown}")
    if timing.get("telegraph"):
        timing_parts.append("telegraphed")
    if timing.get("interruptible"):
        timing_parts.append("interruptible")
    if reaction_role:
        timing_parts.append(f"{reaction_role} tool")

    parts = []
    if summary:
        parts.append(summary)
    parts.append("Timing: " + " · ".join(timing_parts))
    return "\n".join(parts)


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
        timing = get_ability_atb_profile(ability_key, ability)
        reaction_role = _reaction_role_for_ability(ability_key)
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
            "timing": timing,
            "reaction_role": reaction_role,
            "tooltip": _timing_tooltip(timing, reaction_role=reaction_role, summary=ability.get("summary")),
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
        timing = get_item_atb_profile(template_id, use)
        reaction_role = _reaction_role_for_item(use)
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
            "timing": timing,
            "reaction_role": reaction_role,
            "tooltip": _timing_tooltip(timing, reaction_role=reaction_role, summary=item.get("summary")),
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
