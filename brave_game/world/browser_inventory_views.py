"""Inventory, gear, and pack browser view payload builders."""

from world.activities import get_targetable_consumable_characters
from world.browser_context import (
    ABILITY_LIBRARY,
    EQUIPMENT_SLOTS,
    ITEM_TEMPLATES,
    SYSTEMS_CONTENT,
    ability_key,
    get_item_category,
    get_item_use_profile,
)
from world.browser_formatting import (
    _format_context_bonus_summary,
    _format_item_value_text,
    _format_restore_summary,
)
from world.browser_ui import (
    _action,
    _entry,
    _item,
    _make_view,
    _pair,
    _picker,
    _picker_option,
    _reactive_from_character,
    _section,
)
from world.data.items import get_item_rarity_label
from world.item_rarity import build_item_rarity_chip, build_item_rarity_display
from world.resonance import format_ability_display

PACK_KIND_ORDER = ("consumable", "ingredient", "loot", "equipment")

PACK_KIND_LABELS = {
    "consumable": ("Consumables", "restaurant"),
    "ingredient": ("Ingredients", "kitchen"),
    "loot": ("Loot And Materials", "category"),
    "equipment": ("Spare Gear", "shield"),
}

GEAR_SLOT_LABELS = {
    "main_hand": "Main Hand",
    "off_hand": "Off Hand",
    "head": "Head",
    "chest": "Chest",
    "hands": "Hands",
    "legs": "Legs",
    "feet": "Feet",
    "ring": "Ring",
    "trinket": "Trinket",
    "snack": "Snack",
}

GEAR_SLOT_ICONS = {
    "main_hand": "swords",
    "off_hand": "shield",
    "head": "helmet",
    "chest": "checkroom",
    "hands": "back_hand",
    "legs": "airline_seat_legroom_extra",
    "feet": "hiking",
    "ring": "diamond",
    "trinket": "auto_awesome",
    "snack": "lunch_dining",
}

def _sheet_detail_tooltip(title, subtitle=None, lines=None):
    parts = [title] if title else []
    if subtitle:
        parts.append(subtitle)
    parts.extend(line for line in (lines or []) if line)
    return "\n".join(parts)

def _gear_slot_label(slot):
    return GEAR_SLOT_LABELS.get(slot, slot.replace("_", " ").title())

def _format_equipment_effect_lines(item, character):
    lines = []
    bonus_text = _format_context_bonus_summary(item.get("bonuses", {}), character)
    if bonus_text:
        lines.append(bonus_text)

    granted_ability = item.get("granted_ability")
    if granted_ability:
        ability_label = item.get("granted_ability_name") or format_ability_display(granted_ability, character)
        cooldown_turns = int(item.get("cooldown_turns", 0) or 0)
        if cooldown_turns > 0:
            lines.append(f"{ability_label} · {cooldown_turns}-turn cooldown")
        else:
            lines.append(ability_label)
    return lines

def _build_gear_slot_picker(character, slot, equipped_template_id=None):
    slot_label = _gear_slot_label(slot)
    equipped_item = ITEM_TEMPLATES.get(equipped_template_id or "")
    options = []
    body = []

    if equipped_item:
        body.append(equipped_item.get("summary", ""))
        body.extend(_format_equipment_effect_lines(equipped_item, character))
        options.append(
            _picker_option(
                f"Unequip {equipped_item.get('name', slot_label)}",
                command=f"gear unequip {slot}",
                icon="remove_circle",
                tone="muted",
            )
        )
        subtitle = equipped_item.get("name", slot_label)
    else:
        subtitle = "Empty"

    candidates = []
    for entry in getattr(character, "get_equippable_inventory", lambda **kwargs: [])(slot=slot):
        template_id = entry.get("template")
        quantity = max(0, int(entry.get("quantity", 0) or 0))
        template = ITEM_TEMPLATES.get(template_id, {})
        if quantity <= 0 or template_id == equipped_template_id:
            continue
        candidates.append((template.get("name", template_id.replace("_", " ").title()).lower(), template_id, quantity, template))

    candidates.sort()
    for _name_sort, template_id, quantity, template in candidates:
        option_meta = " · ".join(_format_equipment_effect_lines(template, character)) or "Equip from pack"
        option_meta = f"{get_item_rarity_label(template)} · {option_meta}"
        if quantity > 1:
            option_meta = f"x{quantity} · {option_meta}"
        options.append(
            _picker_option(
                template.get("name", template_id.replace("_", " ").title()),
                command=f"gear equip {slot} {template_id}",
                icon="north_east",
                meta=option_meta,
                tone="accent",
                **build_item_rarity_display(template),
            )
        )

    if not candidates:
        body.append("No compatible gear in your pack.")

    picker_kwargs = {}
    if equipped_item:
        picker_kwargs = {
            **build_item_rarity_display(equipped_item),
            "rarity_target": "subtitle",
            "chips": [build_item_rarity_chip(equipped_item)],
        }
    return _picker(slot_label, subtitle=subtitle, options=options, body=body, **picker_kwargs)

def _build_gear_entry(character, slot, template_id):
    item = ITEM_TEMPLATES.get(template_id, {})
    item_name = item.get("name", template_id.replace("_", " ").title())
    slot_label = _gear_slot_label(slot)
    summary_text = item.get("summary", "")
    detail_lines = _format_equipment_effect_lines(item, character)
    body = [summary_text, *detail_lines]
    tooltip = _sheet_detail_tooltip(item_name, slot_label, body)
    return _entry(
        slot_label,
        meta=item_name,
        lines=detail_lines,
        icon=GEAR_SLOT_ICONS.get(slot, "shield"),
        rarity_target="meta",
        **build_item_rarity_display(item),
        picker=_build_gear_slot_picker(character, slot, equipped_template_id=template_id),
        tooltip=tooltip,
    )

def _build_empty_gear_entry(character, slot):
    slot_label = _gear_slot_label(slot)
    return _entry(
        slot_label,
        meta="Empty",
        lines=[],
        icon=GEAR_SLOT_ICONS.get(slot, "inventory_2"),
        picker=_build_gear_slot_picker(character, slot),
        tooltip=_sheet_detail_tooltip(slot_label, "Empty", []),
    )

def build_gear_view(character, feedback=None):
    """Return a browser-first main view for equipped gear."""

    equipment = character.db.brave_equipment or {}
    slot_entries = [
        _build_gear_entry(character, slot, equipment[slot])
        if equipment.get(slot)
        else _build_empty_gear_entry(character, slot)
        for slot in EQUIPMENT_SLOTS
    ]
    sections = []
    if feedback:
        sections.append(
            _section(
                "Power Feedback",
                "trending_up",
                "lines",
                lines=[feedback],
                span="wide",
            )
        )
    sections.append(
        _section(
            "",
            "shield",
            "entries",
            items=slot_entries,
            hide_label=True,
            span="wide",
            variant="slots",
        )
    )

    return {
        **_make_view(
            "",
            "Gear",
            eyebrow_icon=None,
            title_icon="shield",
            subtitle="",
            chips=[],
            sections=sections,
            back=True,
            reactive=_reactive_from_character(character, scene="equipment"),
        ),
        "variant": "gear",
    }

def _pack_item_icon(item):
    kind = get_item_category(item)
    if item.get("kind") == "equipment":
        return GEAR_SLOT_ICONS.get(item.get("slot"), "shield")
    if item.get("kind") == "meal":
        return "lunch_dining"
    if kind == "consumable":
        return "restaurant"
    if kind == "ingredient":
        return "kitchen"
    if kind == "loot":
        return "category"
    return "backpack"

def _pack_item_subtitle(item):
    use = get_item_use_profile(item)
    if (use or {}).get("effect_type") == "teach_spell":
        return "Spellbook"
    if (use or {}).get("effect_type") == "unlock_recipe":
        return "Recipe Note"
    if (use or {}).get("effect_type") == "unlock_companion":
        return "Bond Item"
    if (use or {}).get("effect_type") == "unlock_oath":
        return "Oath Relic"
    if item.get("kind") == "equipment":
        return _gear_slot_label(item.get("slot"))
    if item.get("kind") == "meal":
        return "Meal"
    kind = get_item_category(item)
    return {
        "consumable": "Consumable",
        "ingredient": "Ingredient",
        "loot": "Loot And Material",
    }.get(kind, "Pack Item")

def _pack_item_body(character, item, quantity):
    body = []
    summary_text = item.get("summary", "")
    if summary_text:
        body.append(summary_text)

    if item.get("kind") == "equipment":
        body.extend(_format_equipment_effect_lines(item, character))
    elif get_item_category(item) == "consumable":
        use = get_item_use_profile(item) or {}
        restore_text = _format_restore_summary(use.get("restore", {}), character)
        if restore_text:
            body.append("Restore: " + restore_text)
        buff_text = _format_context_bonus_summary(use.get("buffs", {}), character)
        if buff_text:
            body.append("Buff: " + buff_text)
        damage_spec = dict(use.get("damage", {}))
        if damage_spec.get("base"):
            low = int(damage_spec.get("base", 0) or 0)
            high = low + max(0, int(damage_spec.get("variance", 0) or 0))
            body.append(f"Damage: {low}-{high}" if high > low else f"Damage: {low}")
        if use.get("effect_type") == "cleanse":
            body.append("Effect: Clear 1 harmful effect")
        if use.get("effect_type") == "guard":
            body.append(f"Effect: Guard {int(use.get('guard', 0) or 0)}")
        if use.get("effect_type") == "teach_spell":
            ability = ABILITY_LIBRARY.get(ability_key(use.get("learn_ability")))
            if ability:
                body.append("Teaches: " + ability.get("name", "Unknown Spell"))
            required_class = use.get("required_class")
            if required_class:
                body.append("Study: " + str(required_class).title() + " only")
        if use.get("effect_type") == "unlock_recipe":
            recipe_key = str(use.get("unlock_recipe", "")).lower()
            domain = str(use.get("recipe_domain", "cooking")).lower()
            if domain == "cooking":
                recipe = SYSTEMS_CONTENT.cooking_recipes.get(recipe_key) or {}
            elif domain == "tinkering":
                recipe = SYSTEMS_CONTENT.tinkering_recipes.get(recipe_key) or {}
            else:
                recipe = {}
            if recipe:
                body.append("Teaches: " + recipe.get("name", recipe_key.replace("_", " ").title()))
            body.append("Pattern: " + domain.title())
        if use.get("effect_type") == "unlock_companion":
            body.append("Unlocks: " + str(use.get("unlock_companion", "")).replace("_", " ").title())
            required_class = use.get("required_class")
            if required_class:
                body.append("Bond: " + str(required_class).title() + " only")
        if use.get("effect_type") == "unlock_oath":
            body.append("Unlocks: " + str(use.get("unlock_oath", "")).replace("_", " ").title())
            required_class = use.get("required_class")
            if required_class:
                body.append("Vow: " + str(required_class).title() + " only")
        contexts = [str(context).title() for context in (use.get("contexts") or [])]
        if contexts:
            body.append("Use: " + ", ".join(contexts))

    value_text = _format_item_value_text(item, quantity)
    if value_text:
        body.append("Value: " + value_text)

    if not body:
        body.append("A kept item in your pack.")
    return body

def _pack_target_meta(character, target):
    if target == character:
        return "You"

    character_party = getattr(getattr(character, "db", None), "brave_party_id", None)
    target_party = getattr(getattr(target, "db", None), "brave_party_id", None)
    if character_party and character_party == target_party:
        return "Party"
    return "Nearby"

def _build_pack_consumable_action(character, template_id, item):
    use = get_item_use_profile(item, context="explore")
    if not use:
        return None

    item_name = item.get("name", template_id.replace("_", " ").title())
    action_label = (
        "Study"
        if use.get("verb") == "study"
        else "Bond"
        if use.get("verb") == "bond"
        else "Swear"
        if use.get("verb") == "swear"
        else "Use"
    )
    target_type = use.get("target", "self")
    if target_type == "ally":
        targets = get_targetable_consumable_characters(character, include_self=True)
        options = []
        for target in targets:
            command = f"use {item_name}" if target == character else f"use {item_name} = {target.key}"
            options.append(
                _picker_option(
                    target.key,
                    command=command,
                    icon="person",
                    meta=_pack_target_meta(character, target),
                    tone="good" if target == character else None,
                )
            )
        if not options:
            options.append(
                _picker_option(
                    "You",
                    command=f"use {item_name}",
                    icon="person",
                    meta="You",
                    tone="good",
                )
            )
        return _action(
            action_label,
            None,
            None,
            tone="muted",
            picker=_picker(f"{action_label} {item_name}", subtitle="Choose target", options=options),
        )

    if target_type in {"self", "none"}:
        return _action(action_label, f"use {item_name}", None, tone="muted")
    return None

def _build_pack_item(character, template_id, quantity):
    item = ITEM_TEMPLATES.get(template_id, {})
    title = item.get("name", template_id.replace("_", " ").title())
    kind = get_item_category(item)
    subtitle = _pack_item_subtitle(item)
    body = _pack_item_body(character, item, quantity)
    tooltip = _sheet_detail_tooltip(title, subtitle, body)

    entry = _item(
        title,
        badge=str(max(1, int(quantity or 1))),
        picker=_picker(
            title,
            subtitle=subtitle,
            body=body,
            chips=[build_item_rarity_chip(item)],
            **build_item_rarity_display(item),
        ),
        tooltip=tooltip,
        **build_item_rarity_display(item),
    )
    if kind == "consumable":
        action = _build_pack_consumable_action(character, template_id, item)
        if action:
            entry["actions"] = [action]
    return entry

def build_pack_view(character):
    """Return a browser-first main view for the player's pack."""

    inventory = list(character.db.brave_inventory or [])
    inventory.sort(key=lambda entry: ITEM_TEMPLATES.get(entry["template"], {}).get("name", entry["template"]))
    grouped = {kind: [] for kind in PACK_KIND_ORDER}
    other_entries = []

    for entry in inventory:
        template_id = entry["template"]
        quantity = entry.get("quantity", 1)
        item = ITEM_TEMPLATES.get(template_id, {})
        formatted = _build_pack_item(character, template_id, quantity)
        kind = get_item_category(item)
        if kind in grouped:
            grouped[kind].append(formatted)
        else:
            other_entries.append(formatted)

    sections = [
        _section(
            "",
            "savings",
            "pairs",
            items=[_pair("Silver", character.db.brave_silver or 0, "savings")],
            hide_label=True,
            span="wide",
            variant="money",
        )
    ]
    for kind in PACK_KIND_ORDER:
        if grouped[kind]:
            label, icon = PACK_KIND_LABELS[kind]
            sections.append(_section(label, icon, "list", items=grouped[kind], variant="items"))
    if other_entries:
        sections.append(_section("Other", "backpack", "list", items=other_entries, variant="items"))
    if len(sections) == 1:
        sections.append(
            _section(
                "Contents",
                "backpack",
                "list",
                items=[_item("Pack is empty.", icon="info")],
                variant="items",
            )
        )

    return {
        **_make_view(
            "",
            "Pack",
            eyebrow_icon=None,
            title_icon="backpack",
            subtitle="",
            chips=[],
            sections=sections,
            back=True,
            reactive=_reactive_from_character(character, scene="pack"),
        ),
        "variant": "pack",
    }
