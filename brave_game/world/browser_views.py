"""Browser-only main-pane view payloads for Brave's richer command screens."""

import time

from world.arcade import format_arcade_score, get_personal_best, get_reward_definition, has_arcade_reward
from world.activities import (
    can_borrow_fishing_tackle,
    format_fishing_screen,
    get_cooking_entries,
    get_available_fishing_lures,
    get_available_fishing_rods,
    get_fishing_spot_summary,
    get_targetable_consumable_characters,
    room_supports_activity,
)
from world.combat_atb import render_atb_state
from world.combat_actions import build_combat_action_payload
from world.ability_icons import get_ability_icon_name, get_passive_icon_name
from world.enemy_icons import get_enemy_icon_name
from world.content import get_content_registry
from world.data.arcade import ARCADE_GAMES
from world.commerce import format_shop_bonus, get_reserved_entries, get_sellable_entries, get_shop_bonus
from world.data.themes import THEMES, THEME_BY_KEY, normalize_theme_key
from world.data.world_tones import get_world_tone_key
from world.chapel import get_active_blessing, is_chapel_room
from world.character_icons import get_class_icon, get_race_icon
from world.class_features import get_class_features
from world.druid_forms import get_druid_form
from world.forging import get_forge_entries
from world.genders import BRAVE_GENDER_LABELS, get_brave_gender_label
from world.navigation import (
    build_map_snapshot,
    build_minimap_snapshot,
    format_exit_summary,
    format_route_hint,
    get_exit_direction,
    get_exit_label,
    sort_exits,
)
from world.mastery import format_mastery_name
from world.interactions import get_entity_response
from world.party import get_character_by_id, get_follow_target, get_party_leader, get_party_members
from world.questing import get_tracked_quest
from world.resonance import (
    format_ability_display,
    get_world_label,
    get_resource_label,
    get_resonance_key,
    get_resonance_label,
    get_stat_label,
    resolve_ability_query,
)
from world.tinkering import get_tinkering_entries
from world.tutorial import (
    LANTERNFALL_RECAP_PAGES,
    LANTERNFALL_WELCOME_PAGES,
    TUTORIAL_STEPS,
    ensure_tutorial_state,
    get_tutorial_mechanical_guidance,
    get_tutorial_objective_entries,
    is_tutorial_active,
    should_show_lanternfall_recap,
)
from world.resting import room_allows_rest

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
ITEM_CONTENT = CONTENT.items
QUEST_CONTENT = CONTENT.quests
SYSTEMS_CONTENT = CONTENT.systems

ABILITY_LIBRARY = CHARACTER_CONTENT.ability_library
CLASSES = CHARACTER_CONTENT.classes
PASSIVE_ABILITY_BONUSES = CHARACTER_CONTENT.passive_ability_bonuses
RACES = CHARACTER_CONTENT.races
VERTICAL_SLICE_CLASSES = CHARACTER_CONTENT.vertical_slice_classes
ability_key = CHARACTER_CONTENT.ability_key
split_unlocked_abilities = CHARACTER_CONTENT.split_unlocked_abilities
xp_needed_for_next_level = CHARACTER_CONTENT.xp_needed_for_next_level

EQUIPMENT_SLOTS = ITEM_CONTENT.equipment_slots
ITEM_TEMPLATES = ITEM_CONTENT.item_templates
get_item_category = ITEM_CONTENT.get_item_category
get_item_use_profile = ITEM_CONTENT.get_item_use_profile

QUESTS = QUEST_CONTENT.quests
STARTING_QUESTS = QUEST_CONTENT.starting_quests
get_quest_region = QUEST_CONTENT.get_quest_region
group_quest_keys_by_region = QUEST_CONTENT.group_quest_keys_by_region
ENCOUNTER_CONTENT = CONTENT.encounters
ENEMY_TEMPLATES = ENCOUNTER_CONTENT.enemy_templates
COOKING_RECIPES = SYSTEMS_CONTENT.cooking_recipes
format_ingredient_list = SYSTEMS_CONTENT.format_ingredient_list
PORTALS = SYSTEMS_CONTENT.portals
PORTAL_STATUS_LABELS = SYSTEMS_CONTENT.portal_status_labels


PACK_KIND_ORDER = ("consumable", "ingredient", "loot", "equipment")
PACK_KIND_LABELS = {
    "consumable": ("Consumables", "restaurant"),
    "ingredient": ("Ingredients", "kitchen"),
    "loot": ("Loot And Materials", "category"),
    "equipment": ("Spare Gear", "shield"),
}

ROOM_ENTITY_KIND_ICONS = {
    "npc": "forum",
    "readable": "menu_book",
    "arcade": "videogame_asset",
    "object": "category",
}

ROOM_ENTITY_ID_ICONS = {
    "kitchen_hearth": "soup_kitchen",
}

TUTORIAL_TALK_ENTITY_IDS = {
    "sergeant_tamsin_vale",
    "quartermaster_nella_cobb",
    "courier_peep_marrow",
    "ringhand_brask",
    "captain_harl_rowan",
}

TUTORIAL_READ_ENTITY_IDS = {
    "tutorial_supply_board",
    "family_post_sign",
    "tutorial_damaged_cart",
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


def _display_name(obj):
    display_name = getattr(getattr(obj, "db", None), "brave_display_name", None)
    if display_name:
        return str(display_name)
    key = getattr(obj, "key", "") or ""
    if not key:
        return ""
    return key.title()


def _chip(label, icon, tone="muted"):
    return {"label": label, "icon": icon, "tone": tone}


def _action(label, command, icon, *, tone=None, confirm=None, icon_only=False, aria_label=None, picker=None, no_icon=False):
    action = {"label": label, "icon": icon}
    if command:
        action["command"] = command
    if tone:
        action["tone"] = tone
    if confirm:
        action["confirm"] = confirm
    if icon_only:
        action["icon_only"] = True
    if aria_label:
        action["aria_label"] = aria_label
    if picker:
        action["picker"] = picker
    if no_icon:
        action["no_icon"] = True
    return action


def _item(
    text,
    *,
    icon=None,
    background_icon=None,
    badge=None,
    command=None,
    prefill=None,
    confirm=None,
    actions=None,
    picker=None,
    tooltip=None,
    detail=None,
    marker_icon=None,
    on_open_command=None,
    dismiss_bubble_speaker=None,
):
    item = {"text": text}
    if icon:
        item["icon"] = icon
    if badge:
        item["badge"] = badge
    if command:
        item["command"] = command
    if prefill:
        item["prefill"] = prefill
    if confirm:
        item["confirm"] = confirm
    if actions:
        item["actions"] = actions
    if picker:
        item["picker"] = picker
    if tooltip:
        item["tooltip"] = tooltip
    if detail:
        item["detail"] = detail
    if marker_icon:
        item["marker_icon"] = marker_icon
    if on_open_command:
        item["on_open_command"] = on_open_command
    if dismiss_bubble_speaker:
        item["dismiss_bubble_speaker"] = dismiss_bubble_speaker
    return item


def _line(text, *, icon=None):
    line = {"text": text}
    if icon:
        line["icon"] = icon
    return line


def _pair(label, value, icon=None):
    return {"label": label, "value": str(value), "icon": icon}


def _meter(label, current, maximum, *, tone="accent", meta=None, value=None):
    current_value = max(0, int(current or 0))
    maximum_value = max(1, int(maximum or 0))
    percent = max(0, min(100, int(round((current_value / maximum_value) * 100))))
    meter = {
        "label": label,
        "value": value or f"{current_value} / {maximum_value}",
        "percent": percent,
        "tone": tone,
    }
    if meta:
        meter["meta"] = dict(meta)
    return meter


def _resource_meter_tone(current, maximum):
    maximum_value = max(1, int(maximum or 0))
    current_value = max(0, int(current or 0))
    percent = current_value / maximum_value
    if percent <= 0.25:
        return "danger"
    if percent <= 0.6:
        return "warn"
    return "good"


def _hp_meter_tone(current, maximum):
    maximum_value = max(1, int(maximum or 0))
    current_value = max(0, int(current or 0))
    percent = current_value / maximum_value
    if percent <= 0.25:
        return "danger"
    if percent <= 0.5:
        return "warn"
    return "good"


def _enemy_icon(enemy):
    enemy = dict(enemy or {})
    template_key = str(enemy.get("template_key") or "").strip().lower()
    template = ENEMY_TEMPLATES.get(template_key, {})
    return str(enemy.get("icon") or get_enemy_icon_name(template_key, template))


def _combat_card_size_class(entry=None, *, enemy=False):
    if not enemy:
        return "normal"
    entry = dict(entry or {})
    template_key = str(entry.get("template_key") or "").strip().lower()
    template = ENEMY_TEMPLATES.get(template_key, {})
    tags = {str(tag).lower() for tag in template.get("tags", [])}
    rank = int(entry.get("rank") or 1)
    if "boss" in tags:
        return "boss"
    if rank >= 4 or {"captain", "commander", "elite"} & tags:
        return "elite"
    return "normal"


def _entry(
    title,
    *,
    meta=None,
    lines=None,
    summary=None,
    icon=None,
    background_icon=None,
    badge=None,
    command=None,
    prefill=None,
    confirm=None,
    actions=None,
    picker=None,
    chips=None,
    meters=None,
    size_class=None,
    tooltip=None,
    selected=False,
    combat_state=None,
    entry_ref=None,
    hide_icon=False,
    attachments=None,
    sidecars=None,
    cluster_ref=None,
):
    entry = {
        "title": title,
        "meta": meta,
        "lines": [line for line in (lines or []) if line],
        "summary": summary or "",
        "icon": icon,
        "badge": badge,
    }
    if background_icon:
        entry["background_icon"] = background_icon
    if hide_icon:
        entry["hide_icon"] = True
    if selected:
        entry["selected"] = True
    if combat_state:
        entry["combat_state"] = list(combat_state)
    if entry_ref:
        entry["entry_ref"] = str(entry_ref)
    if command:
        entry["command"] = command
    if prefill:
        entry["prefill"] = prefill
    if confirm:
        entry["confirm"] = confirm
    if actions:
        entry["actions"] = actions
    if picker:
        entry["picker"] = picker
    if chips:
        entry["chips"] = chips
    if meters:
        entry["meters"] = meters
    if tooltip:
        entry["tooltip"] = tooltip
    if size_class:
        entry["size_class"] = size_class
    if attachments:
        entry["attachments"] = list(attachments)
    if sidecars:
        entry["sidecars"] = list(sidecars)
    if cluster_ref:
        entry["cluster_ref"] = str(cluster_ref)
    return entry


def _picker_option(label, *, command=None, prefill=None, icon=None, meta=None, tone=None, picker=None, chat_open=False, chat_prompt=None):
    option = {"label": label}
    if command:
        option["command"] = command
    if prefill:
        option["prefill"] = prefill
    if icon:
        option["icon"] = icon
    if meta:
        option["meta"] = meta
    if tone:
        option["tone"] = tone
    if picker:
        option["picker"] = picker
    if chat_open:
        option["chat_open"] = True
    if chat_prompt:
        option["chat_prompt"] = chat_prompt
    return option


def _picker(title, *, subtitle=None, options=None, body=None, picker_id=None, title_icon=None):
    picker = {
        "title": title,
        "options": [option for option in (options or []) if option],
    }
    if picker_id:
        picker["picker_id"] = picker_id
    if title_icon:
        picker["title_icon"] = title_icon
    if subtitle:
        picker["subtitle"] = subtitle
    if body:
        picker["body"] = [line for line in body if line]
    return picker


def _section(label, icon, kind, items=None, lines=None, span=None, **extra):
    section = {
        "label": label,
        "icon": icon,
        "kind": kind,
        "items": items or [],
        "lines": lines or [],
    }
    if span:
        section["span"] = span
    if extra:
        section.update(extra)
    return section


def _make_view(
    eyebrow,
    title,
    *,
    eyebrow_icon,
    title_icon,
    wordmark=None,
    subtitle=None,
    chips=None,
    sections=None,
    actions=None,
    back=False,
    reactive=None,
    welcome_pages=None,
):
    view_actions = list(actions or [])
    back_action = _action("Close", "look", "close", tone="muted", aria_label="Close") if back else None
    return {
        "eyebrow": eyebrow,
        "eyebrow_icon": eyebrow_icon,
        "title": title,
        "title_icon": title_icon,
        "wordmark": wordmark or "",
        "subtitle": subtitle or "",
        "back_action": back_action,
        "chips": [chip for chip in (chips or []) if chip],
        "sections": sections or [],
        "actions": view_actions,
        "reactive": reactive or {},
        "welcome_pages": welcome_pages or [],
    }


def _reactive_view(source=None, *, scene="system", danger=None, boss=False):
    """Build semantic browser-reactivity metadata for a view."""

    reactive = {
        "scene": scene,
        "world_tone": get_world_tone_key(source),
    }
    source_id = getattr(source, "id", None)
    if source_id is not None:
        reactive["source_id"] = str(source_id)
    if danger:
        reactive["danger"] = danger
    if boss:
        reactive["boss"] = True
    return reactive


def _reactive_from_character(character, *, scene="system", danger=None, boss=False):
    """Convenience wrapper using the character's current room."""

    return _reactive_view(getattr(character, "location", None), scene=scene, danger=danger, boss=boss)


def _format_dialogue_line(line):
    return str(line or "").strip()


def _build_talk_actions(target):
    actions = []
    entity_id = getattr(getattr(target, "db", None), "brave_entity_id", None)

    if entity_id == "leda_thornwick":
        actions.append(_action("Open Shop", "shop", "storefront", tone="accent"))
    elif entity_id == "torren_ironroot":
        actions.append(_action("Open Forge", "forge", "construction", tone="accent"))
    elif entity_id == "mistress_elira_thorne":
        actions.append(_action("Mastery", "mastery", "school", tone="accent"))
    elif entity_id == "mender_veska_flint":
        actions.append(_action("Open Tinkering", "tinker", "handyman", tone="accent"))

    return actions


def _build_world_interaction_picker(viewer, target):
    kind = getattr(getattr(target, "db", None), "brave_entity_kind", None)
    entity_id = getattr(getattr(target, "db", None), "brave_entity_id", None)
    title = _display_name(target) or getattr(target, "key", "Details")

    if kind == "npc":
        response = get_entity_response(viewer, target, "talk")
        body = [line.strip() for line in str(response or "").splitlines() if line.strip()]
        if not body:
            body = ["They have nothing to say right now."]
        options = [
            _picker_option(
                action["label"],
                command=action.get("command"),
                icon=action.get("icon"),
                meta=action.get("confirm"),
                tone=action.get("tone"),
            )
            for action in _build_talk_actions(target)
        ]
        options.append(_picker_option("Emote At", icon="sentiment_satisfied", picker=_build_targeted_room_emote_picker(target.key)))
        return _picker(title, body=body, options=options, title_icon="forum")

    if kind == "readable":
        response = get_entity_response(viewer, target, "read")
        body = [line.strip() for line in str(response or "").splitlines() if line.strip()]
        if not body:
            body = ["There is nothing legible here right now."]
        options = []
        if entity_id == "kitchen_hearth":
            options.append(_picker_option("Cook", command="cook", icon="restaurant", tone="accent"))
        return _picker(title, body=body, options=options, title_icon="menu_book")

    if kind == "arcade":
        description = [line.strip() for line in str(getattr(getattr(target, "db", None), "desc", "") or "").splitlines() if line.strip()]
        if not description:
            description = ["The cabinet hums softly, waiting for a coin and a steady hand."]
        return _picker(
            title,
            body=description,
            title_icon="sports_esports",
            options=[_picker_option("Play", command=f"arcade open {target.key}", icon="sports_esports", tone="accent")],
        )

    return None


def _sheet_detail_tooltip(title, subtitle=None, lines=None):
    parts = [title] if title else []
    if subtitle:
        parts.append(subtitle)
    parts.extend(line for line in (lines or []) if line)
    return "\n".join(parts)


def _build_sheet_ability_item(character, ability_name):
    display_name = format_ability_display(ability_name, character)
    key = ability_key(ability_name)
    rank = getattr(character, "get_ability_mastery_rank", lambda _key: 1)(key)
    display_name = format_mastery_name(display_name, rank)
    ability = ABILITY_LIBRARY.get(key, {})
    target_label = {
        "enemy": "Targets one enemy",
        "ally": "Targets one ally",
        "self": "Targets yourself",
        "none": "No direct target",
    }.get(ability.get("target"), "Combat ability")
    subtitle_parts = []
    if ability.get("cost") and ability.get("resource"):
        subtitle_parts.append(f"Costs {ability['cost']} {get_resource_label(ability['resource'], character)}")
    if target_label:
        subtitle_parts.append(target_label)
    subtitle = " · ".join(subtitle_parts)
    body = [
        ability.get("summary")
        or {
            "enemy": "A combat technique aimed at a single foe.",
            "ally": "A supportive combat technique used on one ally.",
            "self": "A defensive or empowering combat technique you use on yourself.",
            "none": "A battlefield technique that does not require a single target.",
        }.get(ability.get("target"), "A combat technique available to your build."),
    ]
    tooltip = _sheet_detail_tooltip(display_name, subtitle, body)
    return _item(
        display_name,
        icon=get_ability_icon_name(key, ability),
        picker=_picker(display_name, subtitle=subtitle, body=body),
        tooltip=tooltip,
    )


def _build_sheet_passive_item(character, passive_name, *, icon_name="passive", summary_line=None, bonus_map=None):
    display_name = format_ability_display(passive_name, character)
    passive_key = ability_key(passive_name)
    passive = PASSIVE_ABILITY_BONUSES.get(passive_key, {})
    body = []
    if summary_line:
        body.append(summary_line)
    else:
        body.append(passive.get("summary") or "A passive trait that is always active.")
    bonus_text = _format_context_bonus_summary(bonus_map or {}, character)
    if bonus_text:
        body.append("Bonuses: " + bonus_text)
    tooltip = _sheet_detail_tooltip(display_name, "Passive trait", body)
    return _item(
        display_name,
        icon=get_passive_icon_name(passive_key, passive) if icon_name == "passive" else icon_name,
        picker=_picker(display_name, subtitle="Passive trait", body=body),
        tooltip=tooltip,
    )


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
        if quantity > 1:
            option_meta = f"x{quantity} · {option_meta}"
        options.append(
            _picker_option(
                template.get("name", template_id.replace("_", " ").title()),
                command=f"gear equip {slot} {template_id}",
                icon="north_east",
                meta=option_meta,
                tone="accent",
            )
        )

    if not candidates:
        body.append("No compatible gear in your pack.")

    return _picker(slot_label, subtitle=subtitle, options=options, body=body)


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


def _pre_section(label, icon, text, *, span=None, tone=None, hide_label=False, grid=None):
    section = {
        "label": label,
        "icon": icon,
        "kind": "pre",
        "text": text,
    }
    if span:
        section["span"] = span
    if tone:
        section["tone"] = tone
    if hide_label:
        section["hide_label"] = True
    if grid:
        section["grid"] = grid
    return section


def _short_direction(direction):
    token = str(direction or "").strip().lower()
    return {
        "north": "N",
        "east": "E",
        "south": "S",
        "west": "W",
        "up": "U",
        "down": "D",
    }.get(token, token.upper()[:3] or "?")


def _movement_command(direction, fallback):
    token = str(direction or "").strip().lower()
    return {
        "north": "n",
        "east": "e",
        "south": "s",
        "west": "w",
        "up": "u",
        "down": "d",
    }.get(token, fallback)


CHARGEN_STEP_ORDER = (
    "menunode_choose_race",
    "menunode_choose_class",
    "menunode_choose_gender",
    "menunode_choose_name",
    "menunode_confirm",
)

CHARGEN_STEP_META = {
    "menunode_choose_race": {
        "eyebrow": "Ancestry",
        "title": "Choose Your Origin",
        "title_icon": "diversity_3",
        "subtitle": "Your blood carries the weight of history and ancient perks.",
        "step_index": 1,
    },
    "menunode_choose_class": {
        "eyebrow": "Calling",
        "title": "Choose A Class",
        "title_icon": "swords",
        "subtitle": "How do you face the world when it bites back?",
        "step_index": 2,
    },
    "menunode_choose_gender": {
        "eyebrow": "Identity",
        "title": "Choose A Gender",
        "title_icon": "person",
        "subtitle": "Select the gender identity for your character.",
        "step_index": 3,
    },
    "menunode_choose_name": {
        "eyebrow": "Identity",
        "title": "Choose A Name",
        "title_icon": "badge",
        "subtitle": "Set the name this character will carry into the world.",
        "step_index": 4,
    },
    "menunode_confirm": {
        "eyebrow": "Finality",
        "title": "Review And Forge",
        "title_icon": "task_alt",
        "subtitle": "The path is clear. Is this the one who will walk it?",
        "step_index": 5,
    },
}


def build_chargen_view(account, state, *, error=None):
    """Return a browser-native main view for the character creator."""

    from world.chargen import get_next_chargen_step

    step_key = state.get("step") or "menunode_choose_race"
    step_meta = CHARGEN_STEP_META.get(step_key, CHARGEN_STEP_META["menunode_choose_race"])
    slots_left = account.get_available_character_slots()
    slot_text = "Unlimited" if slots_left is None else str(slots_left)
    race_name = RACES.get(state.get("race"), {}).get("name", "Not set")
    class_name = CLASSES.get(state.get("class"), {}).get("name", "Not set")
    gender_label = get_brave_gender_label(state.get("gender"))

    chips = [
        _chip(f"Step {step_meta['step_index']} / 5", "steps", "accent"),
        _chip(f"{slot_text} open", "add_circle", "muted"),
    ]
    if state.get("race"):
        chips.append(_chip(race_name, get_race_icon(state.get("race"), RACES.get(state.get("race"))), "muted"))
    if state.get("class"):
        chips.append(_chip(class_name, get_class_icon(state.get("class"), CLASSES.get(state.get("class"))), "muted"))

    sections = [
        _section(
            "Draft",
            "checklist",
            "pairs",
            items=[
                _pair("Name", state.get("name") or "Not set", "badge"),
                _pair("Gender", gender_label, "person"),
                _pair("Race", race_name, get_race_icon(state.get("race"), RACES.get(state.get("race")))),
                _pair("Class", class_name, get_class_icon(state.get("class"), CLASSES.get(state.get("class")))),
            ],
            span="wide",
        )
    ]

    actions = []

    def _race_feel(race_key, race_data):
        if race_key == "human":
            return ("Steady start", "bolt")
        if race_key == "elf":
            return ("Precision", "visibility")
        if race_key == "dwarf":
            return ("Durable", "shield")
        if race_key == "mosskin":
            return ("Evasive", "footprint")
        if race_key == "ashborn":
            return ("Aggressive", "local_fire_department")
        return (race_data.get("perk", "Trait"), "star")

    def _class_style(class_key, class_data):
        role = (class_data.get("role") or "").lower()
        if class_key == "warrior":
            return ("Low upkeep", "Frontline anchor", "security")
        if class_key == "cleric":
            return ("Medium upkeep", "Recovery and rescue", "healing")
        if class_key == "ranger":
            return ("Medium upkeep", "Mark and pick targets", "ads_click")
        if class_key == "mage":
            return ("High upkeep", "Burst and control", "auto_awesome")
        if class_key == "rogue":
            return ("High upkeep", "Exploit openings", "bolt")
        if class_key == "paladin":
            return ("Medium upkeep", "Guard and support", "shield")
        if class_key == "druid":
            return ("High upkeep", "Control and adapt", "forest")
        if "tank" in role:
            return ("Medium upkeep", "Hold pressure", "shield")
        if "healer" in role or "support" in role:
            return ("Medium upkeep", "Keep allies stable", "healing")
        return ("Medium upkeep", "Flexible pressure", "star")

    if step_key == "menunode_welcome":
        next_step = get_next_chargen_step(state)
        next_step_entry = {
            "menunode_choose_race": _entry(
                "Choose Race",
                meta="Step 1",
                icon="diversity_3",
                command="continue",
            ),
            "menunode_choose_class": _entry(
                "Choose Class",
                meta="Step 2",
                icon="swords",
                command="continue",
            ),
            "menunode_choose_gender": _entry(
                "Choose Gender",
                meta="Step 3",
                icon="person",
                command="continue",
            ),
            "menunode_choose_name": _entry(
                "Choose Name",
                meta="Step 4",
                icon="badge",
                command="continue",
            ),
            "menunode_confirm": _entry(
                "Review Character",
                meta="Step 5",
                icon="task_alt",
                command="continue",
                chips=[_chip("Ready", "check_circle", "good")],
            ),
        }[next_step]
        sections.append(_section("Next Step", "format_list_numbered", "entries", items=[next_step_entry]))
    elif step_key == "menunode_choose_gender":
        sections = []
        if error:
            sections.append(
                _section(
                    "Identity Issue",
                    "trash",
                    "lines",
                    lines=[error.replace("|r", "").replace("|n", "")],
                    span="wide",
                )
            )
        gender_entries = []
        for gender_key, label in BRAVE_GENDER_LABELS.items():
            gender_entries.append(
                _entry(
                    label,
                    meta="Selected" if state.get("gender") == gender_key else None,
                    lines=[],
                    icon="person",
                    command=label.lower(),
                    chips=[_chip("Current", "check_circle", "good")] if state.get("gender") == gender_key else [],
                )
            )
        sections.append(_section("Gender", "person", "entries", items=gender_entries, span="wide"))
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
    elif step_key == "menunode_choose_name":
        sections = []
        if error:
            sections.append(
                _section(
                    "Identity Issue",
                    "trash",
                    "lines",
                    lines=[error.replace("|r", "").replace("|n", "")],
                    span="wide",
                )
            )
        sections.append(
            _section(
                "Identity",
                "badge",
                "form",
                span="wide",
                hide_label=True,
                fields=[
                    {
                        "field_label": "Character Name",
                        "field_name": "character_name",
                        "value": state.get("name") or "",
                        "placeholder": "Type your character name here",
                        "maxlength": 24,
                        "minlength": 2,
                        "autocapitalize": "words",
                        "autocomplete": "off",
                        "spellcheck": False,
                        "enterkeyhint": "done",
                        "autofocus": True,
                    }
                ],
                submit_label="Save And Continue",
                submit_icon="arrow_forward",
                submit_tone="accent",
                submit_mode="raw",
            )
        )
        sections.append(
            _section(
                "Rules",
                "rule",
                "list",
                items=[
                    _item("2 to 24 characters", icon="straighten"),
                    _item("Letters, spaces, apostrophes, and hyphens only", icon="spellcheck"),
                    _item("Must be unique across all characters", icon="shield"),
                ],
            )
        )
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
    elif step_key == "menunode_choose_race":
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
        race_entries = []
        for race_key, race_data in RACES.items():
            feel_label, feel_icon = _race_feel(race_key, race_data)
            race_entries.append(
                _entry(
                    race_data["name"],
                    meta="Selected" if state.get("race") == race_key else "Origin",
                    lines=[
                        race_data["summary"],
                        f"Perk: {race_data['perk']}",
                        f"Feel: {feel_label}",
                    ],
                    background_icon=get_race_icon(race_key, race_data),
                    command=race_key,
                    hide_icon=True,
                    chips=[
                        *([_chip("Current", "check_circle", "good")] if state.get("race") == race_key else []),
                        _chip(feel_label, feel_icon, "muted"),
                    ],
                )
            )
        sections.append(_section("Races", "forest", "entries", items=race_entries, span="wide"))
    elif step_key == "menunode_choose_class":
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
        class_entries = []
        for class_key in VERTICAL_SLICE_CLASSES:
            class_data = CLASSES[class_key]
            features = get_class_features(class_key)
            upkeep_label, style_label, style_icon = _class_style(class_key, class_data)
            class_entries.append(
                _entry(
                    class_data["name"],
                    meta=class_data["role"],
                    lines=[
                        class_data["summary"],
                        f"Approach: {style_label}",
                        *[feature["summary"] for feature in features[:1]],
                    ],
                    background_icon=get_class_icon(class_key, class_data),
                    command=class_key,
                    hide_icon=True,
                    chips=[
                        *([_chip("Current", "check_circle", "good")] if state.get("class") == class_key else []),
                        _chip(upkeep_label, "tune", "muted"),
                        _chip(style_label, style_icon, "muted"),
                        *[_chip(feature["name"], feature.get("icon", "star"), "muted") for feature in features[:2]],
                    ],
                )
            )
        sections.append(_section("Classes", "swords", "entries", items=class_entries, span="wide"))
    elif step_key == "menunode_confirm":
        actions.extend(
            [
                _action("Create And Play", "finish play", "play_arrow", tone="accent"),
                _action("Back", "back", "arrow_back", tone="muted"),
            ]
        )
        race_data = RACES.get(state.get("race"), {})
        class_data = CLASSES.get(state.get("class"), {})
        if error:
            sections.append(
                _section(
                    "Issue",
                    "trash",
                    "lines",
                    lines=[error.replace("|r", "").replace("|n", "")],
                    span="wide",
                )
            )
        sections.append(
            _section(
                "Highlights",
                "star",
                "entries",
                items=[
                    _entry(
                        get_brave_gender_label(state.get("gender")),
                        meta="Identity",
                        lines=["Gender selection locked in for this character."],
                        icon="person",
                    ),
                    _entry(
                        race_data.get("name", "Race"),
                        meta="Race Perk",
                        lines=[race_data.get("perk", "No perk found."), race_data.get("summary", "")],
                        icon=get_race_icon(state.get("race"), race_data),
                    ),
                    _entry(
                        class_data.get("name", "Class"),
                        meta=class_data.get("role", "Role"),
                        lines=[
                            class_data.get("summary", "No class summary found."),
                            f"Approach: {_class_style(state.get('class'), class_data)[1]}",
                        ],
                        icon=get_class_icon(state.get("class"), class_data),
                    ),
                ],
                span="wide",
                variant="grid3",
            )
        )
        sections.append(
            _section(
                "Begin Your Journey",
                "play_arrow",
                "entries",
                items=[
                    _entry(
                        "Create Character",
                        lines=["Create this character and enter the world immediately."],
                        icon="login",
                        command="finish play",
                    ),
                ],
                span="wide",
            )
        )

    return {
        **_make_view(
            step_meta["eyebrow"],
            step_meta["title"],
            eyebrow_icon="person_add",
            title_icon=step_meta["title_icon"],
            wordmark="BRAVE",
            subtitle=step_meta["subtitle"],
            chips=chips,
            sections=sections,
            actions=actions,
            reactive=_reactive_view(scene="account"),
        ),
        "variant": "chargen",
    }


def _local_npc_keys(character):
    if not getattr(character, "location", None):
        return set()
    return {
        obj.key
        for obj in character.location.contents
        if getattr(getattr(obj, "db", None), "brave_entity_kind", None) == "npc"
    }


def _local_player_characters(character):
    if not getattr(character, "location", None):
        return []
    return [
        obj
        for obj in character.location.contents
        if obj != character and hasattr(obj, "ensure_brave_character") and getattr(obj, "is_connected", False)
    ]


def _format_room_threat_items(visible_threats):
    """Format visible hostile threats for the room view."""

    items = []
    for threat in visible_threats or []:
        inspect_lines = []
        display_name = str(threat.get("display_name") or threat.get("key") or "").strip()
        composition = str(threat.get("composition") or threat.get("detail") or "").strip()
        intro = str(threat.get("intro") or "").strip()
        if composition and composition != display_name:
            inspect_lines.append(composition)
        if intro:
            inspect_lines.append(intro)
        inspect_picker = _picker(
            display_name,
            body=inspect_lines,
            options=[
                _picker_option("Fight", command=threat.get("command") or "fight", icon="swords", tone="danger")
            ],
            picker_id=f"room-threat-{str(threat.get('key') or display_name).strip().lower().replace(' ', '-')}",
        )
        items.append(
            _item(
                display_name,
                icon=threat.get("icon") or "monster-skull",
                badge=threat.get("badge") or threat.get("count"),
                picker=inspect_picker,
                detail="Engaged" if threat.get("engaged") else None,
                tooltip=threat.get("tooltip"),
                marker_icon=threat.get("marker_icon"),
                actions=[
                    _action(
                        "Inspect",
                        None,
                        "search",
                        tone="muted",
                        picker=inspect_picker,
                    ),
                    _action(
                        "Fight",
                        threat.get("command") or "fight",
                        "swords",
                        tone="danger",
                    ),
                ],
            )
        )
    return items




def _format_room_entity_items(viewer, visible_entities, visible_chars):
    items = []

    kind_order = {"npc": 0, "readable": 1, "arcade": 2, "object": 3}
    sorted_entities = sorted(
        list(visible_entities or []),
        key=lambda obj: (kind_order.get((getattr(obj.db, "brave_entity_kind", "") or "object"), 3), obj.key.lower()),
    )
    for obj in sorted_entities:
        kind = getattr(obj.db, "brave_entity_kind", "") or "object"
        entity_id = getattr(obj.db, "brave_entity_id", None)
        label = obj.key if kind == "npc" else _display_name(obj)
        command = None
        picker = None
        on_open_command = None
        dismiss_bubble_speaker = None
        if kind == "npc":
            command = f"talk {obj.key}"
            picker = _build_world_interaction_picker(viewer, obj)
            if entity_id in TUTORIAL_TALK_ENTITY_IDS:
                on_open_command = f"_bravepopup talk {obj.key}"
                dismiss_bubble_speaker = obj.key
        elif kind == "readable":
            command = f"read {obj.key}"
            picker = _build_world_interaction_picker(viewer, obj)
            if entity_id in TUTORIAL_READ_ENTITY_IDS:
                on_open_command = f"_bravepopup read {obj.key}"
        elif kind == "arcade":
            command = f"arcade inspect {obj.key}"
            picker = _build_world_interaction_picker(viewer, obj)
        items.append(
            _item(
                label,
                icon=ROOM_ENTITY_ID_ICONS.get(entity_id, ROOM_ENTITY_KIND_ICONS.get(kind, "category")),
                command=command,
                picker=picker,
                on_open_command=on_open_command,
                dismiss_bubble_speaker=dismiss_bubble_speaker,
            )
        )

    viewer_party_id = getattr(getattr(viewer, "db", None), "brave_party_id", None)
    follow_target = get_follow_target(viewer) if viewer and viewer_party_id else None
    party_leader = get_party_leader(viewer) if viewer and viewer_party_id else None
    room = getattr(viewer, "location", None)
    encounter = getattr(getattr(room, "ndb", None), "brave_encounter", None) if room else None
    engaged_participant_ids = set()
    if encounter and getattr(encounter, "db", None):
        engaged_participant_ids = {
            int(participant_id)
            for participant_id in (getattr(encounter.db, "participants", None) or [])
            if participant_id is not None
        }

    char_entries = []
    for obj in list(visible_chars or []):
        party_id = getattr(getattr(obj, "db", None), "brave_party_id", None)
        same_party = bool(viewer_party_id and viewer_party_id == party_id)
        grouped = bool(party_id)
        engaged = bool(getattr(obj, "id", None) in engaged_participant_ids)
        following = bool(follow_target and follow_target.id == getattr(obj, "id", None))
        leader = bool(party_leader and party_leader.id == getattr(obj, "id", None))
        can_invite = bool(
            not party_id
            and (not viewer_party_id or (party_leader and party_leader.id == viewer.id and len(get_party_members(viewer)) < 4))
        )
        can_kick = bool(same_party and party_leader and party_leader.id == viewer.id)

        detail_bits = []
        if engaged:
            detail_bits.append("Engaged")
        elif same_party:
            detail_bits.append("Party")
        elif grouped:
            detail_bits.append("Grouped")
        if leader:
            detail_bits.append("Leader")
        if following:
            detail_bits.append("Following")

        priority = 0
        if engaged:
            priority -= 30
        if same_party:
            priority -= 24
        if leader:
            priority -= 18
        if following:
            priority -= 12
        if grouped:
            priority -= 6

        char_entries.append(
            (
                priority,
                obj.key.lower(),
                _item(
                    obj.key,
                    icon="person",
                    detail=" · ".join(detail_bits) if detail_bits else None,
                    marker_icon="swords" if engaged else None,
                    picker=_build_room_character_picker(
                        viewer,
                        obj,
                        same_party=same_party,
                        engaged=engaged,
                        following=following,
                        leader=leader,
                        can_invite=can_invite,
                        can_kick=can_kick,
                    ),
                ),
            )
        )

    items.extend(entry for _priority, _key, entry in sorted(char_entries, key=lambda value: (value[0], value[1])))

    return items


def _build_targeted_room_emote_picker(target_name):
    return _picker(
        f"Emote At {target_name}",
        subtitle="Choose a quick social emote aimed at this person.",
        title_icon="sentiment_satisfied",
        options=[
            _picker_option("Smile", command=f"emote smiles at {target_name}", icon="sentiment_satisfied"),
            _picker_option("Nod", command=f"emote nods to {target_name}", icon="how_to_reg"),
            _picker_option("Wave", command=f"emote waves at {target_name}", icon="waving_hand"),
            _picker_option("Laugh", command=f"emote laughs with {target_name}", icon="sentiment_very_satisfied"),
            _picker_option("Bow", command=f"emote bows to {target_name}", icon="self_improvement"),
        ],
    )


def _build_room_character_picker(viewer, obj, *, same_party=False, engaged=False, following=False, leader=False, can_invite=False, can_kick=False):
    target_name = obj.key
    subtitle = "Choose how to interact with this person nearby."
    options = [
        _picker_option(
            "Whisper",
            prefill=f"whisper {target_name} = ",
            icon="forum",
            chat_open=True,
            chat_prompt=f"Whisper to {target_name}...",
        ),
        _picker_option(
            "Emote At",
            icon="sentiment_satisfied",
            picker=_build_targeted_room_emote_picker(target_name),
        ),
    ]
    if same_party:
        if following:
            options.append(_picker_option("Stay", command="party stay", icon="do_not_disturb_on", meta="Stop following for now."))
        else:
            options.append(_picker_option("Follow", command=f"party follow {target_name}", icon="directions_walk", meta=f"Keep pace with {target_name}."))
        options.append(_picker_option("Where", command="party where", icon="location_searching", meta="Check your party's current location."))
        if can_kick:
            options.append(
                _picker_option(
                    "Kick",
                    command=f"party kick {target_name}",
                    icon="person_remove",
                    meta=f"Remove {target_name} from your party.",
                    tone="danger",
                )
            )
    elif can_invite:
        options.append(_picker_option("Invite", command=f"party invite {target_name}", icon="person_add"))

    body = []
    if same_party:
        body.append("Party member")
    else:
        body.append("Nearby player")
    if leader:
        body.append("Party leader")
    if following:
        body.append("You are following them")
    if engaged:
        body.append("Already engaged in the current fight")

    return _picker(
        target_name,
        subtitle=subtitle,
        title_icon="person",
        body=body,
        options=options,
    )


def _build_room_social_presence(viewer, visible_chars):
    chars = list(visible_chars or [])
    if not chars:
        return {
            "nearby_total": 0,
            "engaged_total": 0,
            "party_total": 0,
            "group_count": 0,
            "people": [],
        }

    viewer_party_id = getattr(getattr(viewer, "db", None), "brave_party_id", None)
    follow_target = get_follow_target(viewer) if viewer and viewer_party_id else None
    party_leader = get_party_leader(viewer) if viewer and viewer_party_id else None
    room = getattr(viewer, "location", None)
    encounter = getattr(getattr(room, "ndb", None), "brave_encounter", None) if room else None
    engaged_participant_ids = set()
    if encounter and getattr(encounter, "db", None):
        engaged_participant_ids = {
            int(participant_id)
            for participant_id in (getattr(encounter.db, "participants", None) or [])
            if participant_id is not None
        }

    people = []
    grouped_party_ids = set()
    nearby_total = 0
    engaged_total = 0
    party_total = 0

    for obj in chars:
        nearby_total += 1
        party_id = getattr(getattr(obj, "db", None), "brave_party_id", None)
        same_party = bool(viewer_party_id and viewer_party_id == party_id)
        grouped = bool(party_id)
        engaged = bool(getattr(obj, "id", None) in engaged_participant_ids)
        following = bool(follow_target and follow_target.id == getattr(obj, "id", None))
        leader = bool(party_leader and party_leader.id == getattr(obj, "id", None))

        if grouped:
            grouped_party_ids.add(party_id)
        if engaged:
            engaged_total += 1
        if same_party:
            party_total += 1

        lines = []
        if same_party:
            lines.append("Party member")
        elif grouped:
            lines.append("Grouped nearby")
        else:
            lines.append("Nearby player")
        if leader:
            lines.append("Party leader")
        if following:
            lines.append("You are following them")
        if engaged:
            lines.append("Already in the current fight")

        priority = 0
        if same_party:
            priority -= 40
        if leader:
            priority -= 30
        if following:
            priority -= 24
        if engaged:
            priority -= 18
        if grouped:
            priority -= 8

        badge = "Engaged" if engaged else ("Party" if same_party else "")

        can_invite = bool(
            not party_id
            and (not viewer_party_id or (party_leader and party_leader.id == viewer.id and len(get_party_members(viewer)) < 4))
        )
        can_kick = bool(same_party and party_leader and party_leader.id == viewer.id)
        people.append(
            {
                "name": obj.key,
                "summary": lines[0],
                "detail": " · ".join(lines[1:]),
                "badge": badge,
                "badge_tone": "danger" if engaged else ("muted" if same_party else ""),
                "priority": priority,
                "picker": _build_room_character_picker(
                    viewer,
                    obj,
                    same_party=same_party,
                    engaged=engaged,
                    following=following,
                    leader=leader,
                    can_invite=can_invite,
                    can_kick=can_kick,
                ),
            }
        )

    people.sort(key=lambda entry: (entry["priority"], entry["name"].lower()))

    return {
        "nearby_total": nearby_total,
        "engaged_total": engaged_total,
        "party_total": party_total,
        "group_count": len(grouped_party_ids),
        "people": [
            {
                "name": entry["name"],
                "summary": entry["summary"],
                "detail": entry["detail"],
                "badge": entry["badge"],
                "badge_tone": entry["badge_tone"],
                "picker": entry["picker"],
            }
            for entry in people
        ],
    }


def _character_in_combat(character):
    encounter_getter = getattr(character, "get_active_encounter", None)
    if not callable(encounter_getter):
        return False
    encounter = encounter_getter()
    return bool(encounter and encounter.is_participant(character))


def _build_room_emote_picker():
    return _picker(
        "Emote",
        subtitle="Choose a social emote.",
        options=[
            {"label": "Smile", "icon": "sentiment_satisfied", "command": "emote smile"},
            {"label": "Nod", "icon": "how_to_reg", "command": "emote nod"},
            {"label": "Wave", "icon": "waving_hand", "command": "emote wave"},
            {"label": "Shrug", "icon": "air", "command": "emote shrug"},
            {"label": "Laugh", "icon": "sentiment_very_satisfied", "command": "emote laugh"},
            {"label": "Frown", "icon": "sentiment_dissatisfied", "command": "emote frown"},
            {"label": "Bow", "icon": "self_improvement", "command": "emote bow"},
            {"label": "Think", "icon": "psychology", "command": "emote think"},
        ],
    )


def _format_room_context_action_items(room, viewer):
    """Return room-level buttons for core actions that do not belong to one object."""

    if not room or not viewer or _character_in_combat(viewer):
        return []

    local_entities = list(getattr(room, "contents", []) or [])
    local_arcades = [
        obj
        for obj in local_entities
        if getattr(getattr(obj, "db", None), "brave_entity_kind", None) == "arcade"
    ]

    items = []
    if room_allows_rest(room):
        items.append(_item("Rest", icon="campfire", command="rest"))

    if local_arcades:
        items.append(_item("Play", icon="sports_esports", command="arcade"))

    if room_supports_activity(room, "fishing"):
        fishing_state = getattr(getattr(viewer, "ndb", None), "brave_fishing", None) or {}
        if fishing_state.get("phase") == "bite":
            items.append(_item("Reel", icon="phishing", command="reel", detail="Something is biting."))
        elif fishing_state.get("phase") == "waiting":
            items.append(_item("Line in the water", icon="waves", detail="Wait for a bite."))
        else:
            items.append(_item("Fish", icon="fish", command="fish"))
    if room_supports_activity(room, "cooking"):
        items.append(_item("Cook", icon="restaurant", command="cook"))
    if room_supports_activity(room, "tinkering"):
        items.append(_item("Tinker", icon="build", command="tinker"))
    if room_supports_activity(room, "mastery"):
        items.append(_item("Mastery", icon="school", command="mastery"))

    if is_chapel_room(room):
        blessing = get_active_blessing(viewer)
        items.append(
            _item(
                "Pray" if not blessing else "Review Blessing",
                icon="notifications_active",
                command="pray",
                detail=None if not blessing else "Dawn Bell blessing active.",
            )
        )

    items.append(_item("Emote", icon="sentiment_satisfied", picker=_build_room_emote_picker(), tooltip="Choose a social emote."))
    return items


def _build_tutorial_guidance(character):
    """Return raw guidance entries for the tutorial floating sheet (the TUTORIAL overlay)."""

    mechanical = get_tutorial_mechanical_guidance(character)
    if not mechanical:
        return []

    return mechanical["guidance"]


WELCOME_PAGES = LANTERNFALL_WELCOME_PAGES
RECAP_PAGES = LANTERNFALL_RECAP_PAGES


def build_room_view(room, looker, *, visible_threats=None, visible_entities=None, visible_chars=None):
    """Return a browser-first room view for exploration and movement."""

    world_name = getattr(room.db, "brave_world", "Brave") or "Brave"
    region_name = getattr(room.db, "brave_map_region", None) or room.db.brave_zone or world_name
    description = room.db.desc or "A place of mystery and potential."
    primary_exits = {}
    vertical_exits = []
    special_exits = []
    for exit_obj in sort_exits(list(room.exits)):
        direction = get_exit_direction(exit_obj)
        entry = {
            "direction": direction,
            "label": get_exit_label(exit_obj),
            "badge": _short_direction(direction),
            "command": _movement_command(direction, getattr(exit_obj, "key", "")),
        }
        if direction in {"north", "east", "south", "west"}:
            primary_exits[direction] = entry
        elif direction in {"up", "down"}:
            vertical_exits.append(entry)
        else:
            special_exits.append(
                _item(
                    f"{entry['badge']} · {entry['label']}",
                    icon="route",
                    command=entry["command"],
                )
            )

    nav_items = [primary_exits[direction] for direction in ("north", "west", "east", "south") if direction in primary_exits]

    threat_items = _format_room_threat_items(visible_threats)
    visible_items = _format_room_entity_items(looker, visible_entities, visible_chars)
    room_action_items = _format_room_context_action_items(room, looker)
    sections = []
    tutorial_guidance = []
    welcome_pages = []
    
    welcome_shown = getattr(looker.db, "brave_welcome_shown", False)
    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)

    if not welcome_shown:
        if is_tutorial_active(looker):
            welcome_pages = LANTERNFALL_WELCOME_PAGES
        elif room_id == "brambleford_training_yard":
            welcome_pages = LANTERNFALL_RECAP_PAGES
        
        if welcome_pages:
             sessions = getattr(looker, "sessions", None)
             if sessions and sessions.count() > 0:
                 looker.db.brave_welcome_shown = True
                 looker.db.brave_lanternfall_intro_shown = True

    sections.append(
        _section(
            "",
            "route",
            "navpad",
            items=nav_items,
            span="medium",
            vertical_items=vertical_exits,
            extra_items=special_exits,
            variant="routes",
            hide_label=True,
        )
    )

    vicinity_items = []
    has_threats = bool(threat_items)
    for item in (threat_items or []):
        item["tone"] = "danger"
        vicinity_items.append(item)
    vicinity_items.extend(visible_items or [])
    if not vicinity_items:
        vicinity_items.append(_item("All is quiet.", icon="visibility_off"))

    guidance_eyebrow = None
    guidance_title = None
    if is_tutorial_active(looker):
        mechanical = get_tutorial_mechanical_guidance(looker)
        if mechanical:
            tutorial_guidance = mechanical["guidance"]
            guidance_eyebrow = mechanical["eyebrow"]
            guidance_title = mechanical["title"]

    sections.append(
        _section(
            "The Vicinity",
            "groups",
            "list",
            items=vicinity_items,
            variant="vicinity",
        )
    )

    return {
        **_make_view(
            room.db.brave_zone or world_name,
            room.key,
            eyebrow_icon=None,
            title_icon=None,
            subtitle=description,
            sections=sections,
            reactive=_reactive_view(
                room,
                scene="explore",
                danger="safe" if room.db.brave_safe else "danger",
            ),
            welcome_pages=welcome_pages,
        ),
        "layout": "explore",
        "room_id": str(getattr(room, "id", "") or ""),
        "region_name": str(region_name or ""),
        "first_region_discovery": bool(getattr(getattr(looker, "ndb", None), "brave_first_region_discovery", False)),
        "micromap": build_minimap_snapshot(room, radius=2, character=looker),
        "mobile_pack": _build_mobile_pack_payload(looker),
        "mobile_panels": _build_mobile_room_payload(
            room,
            looker,
            nav_items,
            vertical_exits,
            special_exits,
            vicinity_items,
            room_action_items,
        ),
        "variant": "room",
        "tone": "safe" if room.db.brave_safe else "danger",
        "guidance": tutorial_guidance,
        "guidance_eyebrow": guidance_eyebrow,
        "guidance_title": guidance_title,
        "welcome_pages": welcome_pages,
        "room_actions": room_action_items,
        "social_presence": _build_room_social_presence(looker, visible_chars),
    }


def build_map_view(room, character, *, mode="map"):
    """Return a browser-first large map view."""

    radius = None if mode == "map" else 2
    snapshot = build_map_snapshot(room, radius=radius, character=character)
    if not snapshot:
        return _make_view(
            "",
            "Map Unavailable",
            eyebrow_icon=None,
            title_icon="map",
            subtitle="",
            chips=[],
            sections=[_section("Status", "info", "lines", lines=["No regional coordinates are configured for this room."])],
            back=True,
        )

    region_room = snapshot["room"]
    region_label = region_room.db.brave_zone or snapshot["region"] or "Region"

    legend_items = []
    for entry in snapshot["legend"]:
        text = entry["label"]
        if entry.get("suffix"):
            text += f" · {entry['suffix']}"
        legend_items.append({"text": text, "icon": entry.get("symbol") or "place"})

    sections = [
        _pre_section(region_label, "grid_view", snapshot["map_text"], span="mapwide", tone="map", grid=snapshot.get("map_tiles")),
        _section("Legend", "category", "list", items=legend_items),
    ]

    if snapshot["party"]:
        sections.append(
            _section(
                "Party",
                "groups",
                "entries",
                items=[
                    _entry(
                        member["name"],
                        meta=member["status"].title(),
                        lines=[member["location"], member["route"]],
                        icon="person",
                    )
                    for member in snapshot["party"]
                ],
            )
        )

    view = _make_view(
        "",
        "Map" if mode == "map" else "Local Map",
        eyebrow_icon=None,
        title_icon="map",
        subtitle="",
        chips=[],
        sections=sections,
        back=True,
        reactive=_reactive_view(
            region_room,
            scene="map",
            danger="safe" if getattr(region_room.db, "brave_safe", False) else "danger",
        ),
    )
    if view.get("back_action"):
        view["back_action"]["label"] = ""
        view["back_action"]["aria_label"] = "Close"
    return {**view, "variant": "map"}


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


def _format_equipment_totals(character):
    totals = {}
    for template_id in (character.db.brave_equipment or {}).values():
        item = ITEM_TEMPLATES.get(template_id)
        if not item:
            continue
        for key, value in (item.get("bonuses") or {}).items():
            totals[key] = totals.get(key, 0) + value
    return totals


def _inventory_totals(character):
    totals = {}
    for entry in (character.db.brave_inventory or []):
        template_id = entry.get("template")
        if not template_id:
            continue
        totals[template_id] = totals.get(template_id, 0) + entry.get("quantity", 0)
    return totals


def _build_mobile_pack_payload(character):
    inventory = list(character.db.brave_inventory or [])
    inventory.sort(key=lambda entry: ITEM_TEMPLATES.get(entry.get("template"), {}).get("name", entry.get("template", "")))
    item_types = 0
    consumables = 0
    ingredients = 0
    preview = []
    grouped = {kind: [] for kind in PACK_KIND_ORDER}
    other_items = []

    for entry in inventory:
        template_id = entry.get("template")
        if not template_id:
            continue
        item_types += 1
        quantity = max(0, int(entry.get("quantity", 0) or 0))
        template = ITEM_TEMPLATES.get(template_id, {})
        kind = template.get("kind")
        category = get_item_category(template)
        if category == "consumable":
            consumables += quantity
        elif kind == "ingredient":
            ingredients += quantity

        if item_types <= 60:
            if kind == "equipment":
                icon_name = "shield"
            elif kind == "meal":
                icon_name = "lunch_dining"
            elif category == "consumable":
                icon_name = "restaurant"
            elif category == "ingredient":
                icon_name = "kitchen"
            elif category == "loot":
                icon_name = "category"
            else:
                icon_name = "backpack"
            preview.append(
                {
                    "label": template.get("name", template_id.replace("_", " ").title()),
                    "quantity": quantity,
                    "icon": icon_name,
                }
            )
        packed_item = {
            "label": template.get("name", template_id.replace("_", " ").title()),
            "quantity": quantity,
            "icon": icon_name,
            "meta": _pack_item_subtitle(template),
        }
        if category in grouped:
            grouped[category].append(packed_item)
        else:
            other_items.append(packed_item)

    sections = []
    for kind in PACK_KIND_ORDER:
        if grouped[kind]:
            label, icon = PACK_KIND_LABELS[kind]
            sections.append(
                {
                    "label": label,
                    "icon": icon,
                    "count": sum(item["quantity"] for item in grouped[kind]),
                    "items": grouped[kind][:8],
                    "overflow": max(0, len(grouped[kind]) - 8),
                }
            )
    if other_items:
        sections.append(
            {
                "label": "Other",
                "icon": "backpack",
                "count": sum(item["quantity"] for item in other_items),
                "items": other_items[:8],
                "overflow": max(0, len(other_items) - 8),
            }
        )

    return {
        "silver": character.db.brave_silver or 0,
        "item_types": item_types,
        "consumables": consumables,
        "ingredients": ingredients,
        "preview": [{"label": entry["label"], "quantity": entry["quantity"]} for entry in preview[:4]],
        "items": preview,
        "overflow": max(0, item_types - len(preview)),
        "sections": sections,
    }


def _build_mobile_character_payload(character):
    race_key = str(getattr(character.db, "brave_race", "human") or "human").lower()
    class_key = str(getattr(character.db, "brave_class", "warrior") or "warrior").lower()
    race = RACES.get(race_key, RACES["human"])
    class_data = CLASSES.get(class_key, CLASSES["warrior"])
    level = int(getattr(character.db, "brave_level", 1) or 1)
    primary = getattr(character.db, "brave_primary_stats", None) or {}
    derived = getattr(character.db, "brave_derived_stats", None) or {}
    resources = getattr(character.db, "brave_resources", None) or {}
    blessing = get_active_blessing(character)
    features = list(get_class_features(class_key) or [])

    stats = [
        {"label": get_stat_label("attack_power", character), "value": str(derived.get("attack_power", 0))},
        {"label": get_stat_label("armor", character), "value": str(derived.get("armor", 0))},
        {"label": get_stat_label("accuracy", character), "value": str(derived.get("accuracy", 0))},
        {"label": get_stat_label("dodge", character), "value": str(derived.get("dodge", 0))},
    ]
    if derived.get("spell_power", 0):
        stats.insert(1, {"label": get_stat_label("spell_power", character), "value": str(derived.get("spell_power", 0))})

    effects = []
    if blessing:
        effects.append(blessing.get("name", "Blessing"))
    if race.get("perk"):
        effects.append(race["perk"])

    return {
        "name": character.key,
        "identity": f"{race['name']} {class_data['name']} · Level {level}",
        "summary": class_data["summary"],
        "resources": [
            {"label": get_resource_label("hp", character), "value": f"{resources.get('hp', 0)} / {derived.get('max_hp', 0)}"},
            {"label": get_resource_label("mana", character), "value": f"{resources.get('mana', 0)} / {derived.get('max_mana', 0)}"},
            {"label": get_resource_label("stamina", character), "value": f"{resources.get('stamina', 0)} / {derived.get('max_stamina', 0)}"},
        ],
        "attributes": [
            {"label": get_stat_label("strength", character), "value": str(primary.get("strength", 0))},
            {"label": get_stat_label("agility", character), "value": str(primary.get("agility", 0))},
            {"label": get_stat_label("intellect", character), "value": str(primary.get("intellect", 0))},
            {"label": get_stat_label("spirit", character), "value": str(primary.get("spirit", 0))},
            {"label": get_stat_label("vitality", character), "value": str(primary.get("vitality", 0))},
        ],
        "stats": stats,
        "feature": (features[0] if features else {}),
        "effects": effects,
    }


def _build_mobile_quests_payload(character):
    quest_state = getattr(character.db, "brave_quests", None) or {}
    tracked_key = get_tracked_quest(character)
    active_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if quest_state.get(quest_key, {}).get("status") == "active"
    ]
    completed_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if quest_state.get(quest_key, {}).get("status") == "completed"
    ]

    def summarize(quest_key):
        definition = QUESTS.get(quest_key, {})
        state = quest_state.get(quest_key, {})
        objectives = list(state.get("objectives", []))
        remaining = [objective for objective in objectives if not objective.get("completed")]
        next_objective = remaining[0] if remaining else None
        return {
            "title": definition.get("title", quest_key.replace("_", " ").title()),
            "meta": f"{get_quest_region(quest_key)} · {definition.get('giver', '')}".strip(" ·"),
            "line": _format_objective_progress(next_objective) if next_objective else definition.get("summary", ""),
        }

    tracked = summarize(tracked_key) if tracked_key else None
    if tracked:
        tracked["objectives"] = [
            {
                "text": _format_objective_progress(objective),
                "completed": bool(objective.get("completed")),
            }
            for objective in list(quest_state.get(tracked_key, {}).get("objectives", []))[:5]
        ]

    return {
        "tracked": tracked,
        "active_count": len(active_keys),
        "completed_count": len(completed_keys),
        "active": [summarize(quest_key) for quest_key in active_keys[:5]],
        "completed": [summarize(quest_key) for quest_key in completed_keys[:3]],
    }


def _build_mobile_party_payload(character):
    try:
        members = list(get_party_members(character) or [])
        leader = get_party_leader(character)
        follow_target = get_follow_target(character)
        invites = [
            leader_obj
            for leader_obj in (
                get_character_by_id(invite_id) for invite_id in (getattr(character.db, "brave_party_invites", None) or [])
            )
            if leader_obj
        ]
    except Exception:
        members = []
        leader = None
        follow_target = None
        invites = []

    member_entries = []
    for member in members[:5]:
        resources = member.db.brave_resources or {}
        derived = member.db.brave_derived_stats or {}
        member_entries.append(
            {
                "name": member.key,
                "meta": "Leader" if leader and member.id == leader.id else "Member",
                "line": member.location.key if member.location else "Nowhere",
                "resource": f"HP {resources.get('hp', 0)} / {derived.get('max_hp', 0)}",
            }
        )

    return {
        "in_party": bool(members),
        "leader_name": getattr(leader, "key", "") if leader else "",
        "member_count": len(members),
        "follow_target": getattr(follow_target, "key", "") if follow_target else "",
        "members": member_entries,
        "invites": [invite.key for invite in invites[:4]],
    }


def _build_mobile_room_payload(room, looker, nav_items, vertical_exits, special_exits, vicinity_items, room_action_items):
    route_items = []
    for entry in list(nav_items) + list(vertical_exits):
        route_items.append(
            {
                "label": entry.get("label") or entry.get("direction", "").title(),
                "badge": entry.get("badge", ""),
                "command": entry.get("command"),
            }
        )
    for entry in special_exits[:6]:
        route_items.append(
            {
                "label": entry.get("text", ""),
                "badge": entry.get("badge", ""),
                "command": entry.get("command"),
            }
        )

    vicinity = []
    for item in vicinity_items[:8]:
        vicinity.append(
            {
                "text": item.get("text", ""),
                "detail": item.get("detail", ""),
                "badge": item.get("badge", ""),
                "icon": item.get("marker_icon") or item.get("icon") or "chevron_right",
                "command": item.get("command"),
            }
        )

    return {
        "title": room.key,
        "description": room.db.desc or "A place of mystery and potential.",
        "status_label": "Danger" if not room.db.brave_safe else "Safe",
        "status_copy": "Stay ready for a fight." if not room.db.brave_safe else "No immediate threats nearby.",
        "route_count": len(route_items),
        "routes": route_items,
        "vicinity": vicinity,
        "actions": [
            {
                "label": action.get("label", ""),
                "command": action.get("command"),
                "icon": action.get("icon") or "chevron_right",
            }
            for action in room_action_items[:6]
            if action.get("command")
        ],
        "character": _build_mobile_character_payload(looker),
        "pack": _build_mobile_pack_payload(looker),
        "quests": _build_mobile_quests_payload(looker),
        "party": _build_mobile_party_payload(looker),
    }


def _format_quest_reward_text(definition):
    rewards = definition.get("rewards", {})
    parts = []
    if rewards.get("xp"):
        parts.append(f"{rewards['xp']} XP")
    if rewards.get("silver"):
        parts.append(f"{rewards['silver']} silver")
    for item_reward in rewards.get("items", []):
        template_id = item_reward.get("item")
        if not template_id:
            continue
        item_name = ITEM_TEMPLATES.get(template_id, {}).get("name", template_id)
        quantity = item_reward.get("quantity", 1)
        parts.append(item_name + (f" x{quantity}" if quantity > 1 else ""))
    return ", ".join(parts)


def _character_location_label(character):
    return character.location.key if character.location else ""


def build_account_view(account):
    """Return a browser-first main view for the OOC account screen."""

    from world.chargen import has_chargen_progress

    characters = list(account.characters.all())
    last_played = account.db._last_puppet if account.db._last_puppet in characters else None
    available_slots = account.get_available_character_slots()
    pending = dict(account.db.brave_chargen or {})
    has_pending = has_chargen_progress(account)

    roster_entries = []
    can_create = available_slots is None or available_slots > 0 or has_pending
    if can_create:
        create_lines = []
        create_meta = None
        create_icon = "person_add"
        create_chips = []
        create_actions = []
        if has_pending:
            create_meta = None
            create_icon = "edit_note"
            create_chips.append(_chip("Draft", "edit_note", "warn"))
            create_lines = [
                f"Name: {pending.get('name') or '-'}",
                f"Race: {RACES.get(pending.get('race'), {}).get('name', '-')}",
                f"Class: {CLASSES.get(pending.get('class'), {}).get('name', '-')}",
            ]
            create_title = "Resume Character Creation"
            create_actions.append(
                _action(
                    "Discard draft",
                    "create discard",
                    "trash",
                    tone="danger",
                    confirm="Discard this saved character draft?",
                    icon_only=True,
                    aria_label="Discard saved character draft",
                )
            )
        else:
            create_title = "Create Character"

        roster_entries.append(
            _entry(
                create_title,
                meta=create_meta,
                lines=create_lines,
                icon=create_icon,
                command="create",
                chips=create_chips,
                actions=create_actions,
            )
        )

    for index, character in enumerate(characters, start=1):
        character.ensure_brave_character()
        race_name = RACES[character.db.brave_race]["name"]
        class_name = CLASSES[character.db.brave_class]["name"]
        lines = [
            f"{race_name} {class_name} · Level {character.db.brave_level}",
        ]
        if location_label := _character_location_label(character):
            lines.append(location_label)
        entry_chips = []
        if last_played and character.id == last_played.id:
            entry_chips.append(_chip("Last Played", "history", "accent"))
        roster_entries.append(
            _entry(
                character.key,
                meta=None,
                lines=lines,
                icon=get_class_icon(character.db.brave_class, CLASSES.get(character.db.brave_class)),
                badge=str(index),
                command=f"play {index}",
                chips=entry_chips,
                actions=[
                    _action(
                        "Delete",
                        f"delete {index} --force",
                        "trash",
                        tone="danger",
                        confirm=f"Delete {character.key} permanently?",
                        icon_only=True,
                        aria_label=f"Delete {character.key}",
                    )
                ],
            )
        )

    sections = [
        _section(
            "",
            "groups",
            "entries",
            items=roster_entries or [_entry("No characters yet.", lines=["Create your first adventurer to begin."], icon="person_add")],
            hide_label=True,
        ),
    ]

    actions = [_action("Logout", "logout", "logout", tone="muted")]

    return {
        **_make_view(
            account.key,
            "",
            eyebrow_icon="badge",
            title_icon=None,
            wordmark="BRAVE",
            subtitle="",
            chips=[],
            sections=sections,
            actions=actions,
            reactive=_reactive_view(scene="account"),
        ),
        "variant": "account",
    }


def build_connection_view(*, screen="menu", error=None, username="", registration_enabled=True):
    """Return a browser-native login/account-creation view."""

    normalized_screen = (screen or "menu").strip().lower()
    if normalized_screen not in {"menu", "signin", "create"}:
        normalized_screen = "menu"

    chips = []
    if normalized_screen == "create":
        chips.append(_chip("Character creation happens after login", "arrow_forward", "muted"))
    sections = []
    actions = []
    clean_error = (error or "").strip()
    if clean_error:
        sections.append(
            _section(
                "Issue",
                "warning",
                "lines",
                lines=[clean_error],
                span="wide",
            )
        )

    if normalized_screen == "signin":
        actions.append(_action("Back", "", "arrow_back", tone="muted"))
        actions[-1]["connection_screen"] = "menu"
        sections.append(
            _section(
                "Sign In",
                "login",
                "form",
                span="wide",
                fields=[
                    {
                        "field_name": "username",
                        "field_label": "Username",
                        "placeholder": "Username",
                        "value": username,
                        "autocomplete": "username",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "autofocus": True,
                    },
                    {
                        "field_name": "password",
                        "field_label": "Password",
                        "input_type": "password",
                        "placeholder": "Password",
                        "autocomplete": "current-password",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "enterkeyhint": "go",
                    },
                ],
                submit_template="connect {username} {password}",
                submit_label="Sign In",
                submit_icon="login",
                submit_tone="accent",
            )
        )
        sections.append(
            _section(
                "What Happens Next",
                "explore",
                "list",
                items=[
                    _item("Choose a character or resume a draft after login.", icon="groups"),
                    _item("Your last played character will be ready to continue.", icon="history"),
                    _item("If sign-in fails, you stay here with the username preserved.", icon="sync_problem"),
                ],
            )
        )
        eyebrow = "Sign In"
        eyebrow_icon = "login"
        subtitle = ""
    elif normalized_screen == "create":
        actions.append(_action("Back", "", "arrow_back", tone="muted"))
        actions[-1]["connection_screen"] = "menu"
        sections.append(
            _section(
                "Create Account",
                "person_add",
                "form",
                span="wide",
                fields=[
                    {
                        "field_name": "username",
                        "field_label": "Username",
                        "placeholder": "Choose a username",
                        "value": username,
                        "autocomplete": "username",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "autofocus": True,
                    },
                    {
                        "field_name": "password",
                        "field_label": "Password",
                        "input_type": "password",
                        "placeholder": "Choose a password",
                        "autocomplete": "new-password",
                        "autocapitalize": "none",
                        "spellcheck": False,
                    },
                    {
                        "field_name": "password_confirm",
                        "field_label": "Confirm Password",
                        "input_type": "password",
                        "placeholder": "Repeat your password",
                        "autocomplete": "new-password",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "enterkeyhint": "go",
                    },
                ],
                submit_template="create {username} {password} {password_confirm}",
                submit_label="Create Account",
                submit_icon="person_add",
                submit_tone="accent",
            )
        )
        sections.append(
            _section(
                "Account Rules",
                "rule",
                "list",
                items=[
                    _item("Use a stable username you can remember.", icon="badge"),
                    _item("Pick a password you have not reused elsewhere.", icon="shield"),
                    _item(
                        "After the account is created, you will continue into character setup."
                        if registration_enabled
                        else "New account registration is currently disabled.",
                        icon="arrow_forward" if registration_enabled else "block",
                    ),
                    _item("Use the same account for multiple characters instead of creating multiple logins.", icon="groups"),
                ],
            )
        )
        eyebrow = "Create Account"
        eyebrow_icon = "person_add"
        subtitle = "Make an account, then shape your first adventurer."
    else:
        sections.append(
            _section(
                "Enter Brave",
                "key",
                "list",
                items=[
                    _item("Sign In", icon="key"),
                    _item("Create Account", icon="quill"),
                ],
            )
        )
        sections[0]["items"][0]["connection_screen"] = "signin"
        sections[0]["items"][1]["connection_screen"] = "create"
        eyebrow = ""
        eyebrow_icon = None
        subtitle = ""

    return {
        **_make_view(
            eyebrow,
            "",
            eyebrow_icon=eyebrow_icon,
            title_icon=None,
            wordmark="BRAVE",
            subtitle=subtitle,
            chips=chips,
            sections=sections,
            actions=actions,
            reactive=_reactive_view(scene="account"),
        ),
        "variant": "connection",
    }


def build_theme_view(current_theme_key=None):
    """Build the browser-native theme selection screen."""

    current_theme = THEME_BY_KEY.get(normalize_theme_key(current_theme_key))
    current_theme_key = current_theme["key"] if current_theme else normalize_theme_key(current_theme_key)

    entries = []
    default_theme_key = "hearth"
    for theme in THEMES:
        lines = [theme["summary"]]
        chips_for_entry = []
        if theme["key"] == default_theme_key:
            chips_for_entry.append(_chip("Default", "home", "accent"))
        if theme["key"] == current_theme_key:
            chips_for_entry.append(_chip("Current", "check_circle", "good"))

        entry = _entry(
            theme["name"],
            meta=None,
            summary="",
            lines=lines,
            command=f"theme {theme['key']}",
            chips=chips_for_entry,
        )
        entry["preview"] = {
            "theme_key": theme["key"],
            "font_name": theme["font_name"],
            "summary": theme["summary"],
            "current": theme["key"] == current_theme_key,
        }
        entries.append(entry)

    view = _make_view(
        "",
        "Themes",
        eyebrow_icon=None,
        title_icon="snowflake",
        subtitle="",
        chips=[],
        sections=[_section("", "palette", "entries", items=entries, hide_label=True)],
        actions=[],
        back=True,
        reactive=_reactive_view(scene="theme"),
    )
    if view.get("back_action"):
        view["back_action"]["label"] = ""
        view["back_action"]["aria_label"] = "Close"
    return {**view, "variant": "theme"}


def build_prayer_view(character, *, blessing=None, applied=False):
    """Return a browser-first main view for the Chapel blessing."""

    blessing = blessing or get_active_blessing(character)
    blessing_name = blessing.get("name", "Dawn Bell Blessing")
    duration = blessing.get("duration", "Until your next encounter ends.")
    bonus_text = _format_context_bonus_summary(blessing.get("bonuses", {}), character)
    rite = dict(blessing.get("rite") or {})

    chips = [
        _chip(blessing_name, "wb_sunny", "accent"),
        _chip("One encounter", "schedule", "muted"),
    ]
    if rite.get("name"):
        chips.append(_chip(rite["name"], "workspace_premium", "good"))

    sections = [
        _section(
            "Blessing",
            "wb_sunny",
            "lines",
            lines=[
                "The bell's steadier note settles into you and follows you back onto the road.",
                duration,
                "Bonuses: " + bonus_text if bonus_text else "No mechanical bonus recorded.",
            ],
        ),
    ]
    if rite:
        sections.append(
            _section(
                "Class Rite",
                "workspace_premium",
                "lines",
                lines=[rite.get("summary", ""), *(rite.get("lines") or [])],
            )
        )
    sections.append(
        _section(
            "Chapel Notes",
            "church",
            "list",
            items=[
                _item("Brother Alden watches the west-side trouble and the barrow line.", icon="forum"),
                _item("Sister Maybelle tends the hurt and keeps the town practical about what bravery costs.", icon="forum"),
                _item("Return here before a harder run when you want the Dawn Bell at your back.", icon="flag"),
            ],
        )
    )

    subtitle = (
        "The Dawn Bell answers and steadies you for the next hard road."
        if applied
        else "The Dawn Bell's ward still rests on you."
    )

    return _make_view(
        "Chapel Of The Dawn Bell",
        "Dawn Bell",
        eyebrow_icon="church",
        title_icon="wb_sunny",
        subtitle=subtitle,
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="chapel"),
    )


def _build_tutorial_entry(character):
    state = ensure_tutorial_state(character)
    if state.get("status") != "active":
        return None

    step_key = state.get("step") or "first_steps"
    step = TUTORIAL_STEPS[step_key]
    tutorial_objectives = get_tutorial_objective_entries(character) or {}
    lines = [step["summary"]]
    lines.extend(
        _line(
            objective.get("text", "Objective"),
            icon="check_box" if objective.get("completed") else "check_box_outline_blank",
        )
        for objective in tutorial_objectives.get("objectives", [])
    )
    return _entry(step["title"], meta="Tutorial", lines=lines, icon="school")


def _format_objective_progress(objective):
    text = objective.get("description", "Objective")
    required = objective.get("required", 1)
    if required > 1:
        text += f" ({objective.get('progress', 0)}/{required})"
    return text


def _get_journal_mode(character):
    mode = getattr(getattr(character, "db", None), "brave_journal_tab", "active")
    return mode if mode in {"active", "completed"} else "active"


def _get_expanded_completed_quest(character):
    value = getattr(getattr(character, "db", None), "brave_journal_expanded_completed", None)
    return value or None


def _build_journal_quest_picker(character, quest_key, *, tracked_key=None, nearby_npcs=None):
    state = (character.db.brave_quests or {}).get(quest_key, {})
    definition = QUESTS[quest_key]
    all_objectives = list(state.get("objectives", []))
    completed = state.get("status") == "completed"
    options = []

    if completed:
        options.append(_picker_option("Completed", icon="check_circle", tone="good"))
    elif quest_key == tracked_key:
        options.append(_picker_option("Untrack", command="quests untrack", icon="flag", tone="accent"))
    else:
        options.append(_picker_option("Track", command=f"quests track {quest_key}", icon="flag", tone="accent"))

    body = [definition["summary"]]
    body.extend(
        _line(
            _format_objective_progress(objective),
            icon="check_box" if objective.get("completed") else "check_box_outline_blank",
        )
        for objective in all_objectives[:8]
    )

    return _picker(
        definition["title"],
        subtitle=f"{get_quest_region(quest_key)} · {definition['giver']}",
        options=options,
        body=body,
    )


def _build_journal_quest_entry(character, quest_key, *, tracked_key=None, nearby_npcs=None, detailed=False, inline_command=None):
    state = (character.db.brave_quests or {}).get(quest_key, {})
    definition = QUESTS[quest_key]
    completed = state.get("status") == "completed"
    all_objectives = list(state.get("objectives", []))
    remaining_objectives = [
        objective for objective in all_objectives if not objective.get("completed")
    ]
    next_objective = remaining_objectives[0] if remaining_objectives else None
    lines = []
    meta = definition["giver"]

    if detailed:
        lines.append(definition["summary"])
        lines.extend(
            _line(
                _format_objective_progress(objective),
                icon="check_box" if objective.get("completed") else "check_box_outline_blank",
            )
            for objective in all_objectives
        )
        return _entry(
            definition["title"],
            meta=f"{get_quest_region(quest_key)} · {definition['giver']}",
            lines=lines,
            icon=None if completed else "flag",
            hide_icon=completed,
            command=inline_command,
            actions=[] if state.get("status") == "completed" else [
                _action("Untrack", "quests untrack", "flag", tone="accent"),
            ],
        )

    if completed:
        return _entry(
            definition["title"],
            meta=f"{get_quest_region(quest_key)} · {definition['giver']}",
            lines=[],
            icon=None,
            hide_icon=True,
            command=inline_command,
        )

    if next_objective:
        lines.append(f"Next: {_format_objective_progress(next_objective)}")
    else:
        lines.append(definition["summary"])

    return _entry(
        definition["title"],
        meta=meta,
        lines=lines,
        icon=None,
        hide_icon=True,
        command=inline_command,
        picker=None if completed else _build_journal_quest_picker(
            character,
            quest_key,
            tracked_key=tracked_key,
            nearby_npcs=nearby_npcs,
        ),
    )


def _build_journal_region_sections(character, quest_keys, *, tracked_key=None, status="active"):
    nearby_npcs = _local_npc_keys(character)
    sections = []
    expanded_completed_key = _get_expanded_completed_quest(character) if status == "completed" else None
    filtered_keys = [quest_key for quest_key in quest_keys if not (status == "active" and quest_key == tracked_key)]
    for region, region_keys in group_quest_keys_by_region(filtered_keys):
        items = [
            _build_journal_quest_entry(
                character,
                quest_key,
                tracked_key=tracked_key,
                nearby_npcs=nearby_npcs,
                detailed=(status == "completed" and quest_key == expanded_completed_key),
                inline_command=(
                    f"quests collapse {quest_key}"
                    if status == "completed" and quest_key == expanded_completed_key
                    else (f"quests expand {quest_key}" if status == "completed" else None)
                ),
            )
            for quest_key in region_keys
        ]
        kind = "entries"

        sections.append(
            _section(
                region,
                "explore",
                kind,
                items=items,
                variant="active" if status == "active" else "archive",
            )
        )
    return sections


def build_quests_view(character):
    """Return a browser-first main view for the quest journal."""

    journal_mode = _get_journal_mode(character)
    tutorial_entry = _build_tutorial_entry(character)
    tutorial_active = tutorial_entry is not None
    tracked_key = get_tracked_quest(character)
    nearby_npcs = _local_npc_keys(character)
    tracked_entry = _build_journal_quest_entry(
        character,
        tracked_key,
        tracked_key=tracked_key,
        nearby_npcs=nearby_npcs,
        detailed=True,
    ) if tracked_key and not tutorial_active else None
    active_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if (character.db.brave_quests or {}).get(quest_key, {}).get("status") == "active"
    ]
    completed_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if (character.db.brave_quests or {}).get(quest_key, {}).get("status") == "completed"
    ]

    actions = [
        _action(
            "Active",
            "quests active",
            "assignment",
            tone="accent" if journal_mode == "active" else "muted",
        ),
        _action(
            "Completed",
            "quests completed",
            "check_circle",
            tone="accent" if journal_mode == "completed" else "muted",
        ),
    ]

    sections = [
        _section(
            "",
            "assignment",
            "actions",
            items=actions,
            hide_label=True,
            span="wide",
            variant="switcher",
        )
    ]
    if journal_mode == "active":
        effective_tracked_entry = tutorial_entry or tracked_entry
        if effective_tracked_entry:
            sections.append(
                _section(
                    "",
                    "school" if tutorial_entry else "flag",
                    "entries",
                    items=[effective_tracked_entry],
                    variant="tracked",
                    hide_label=True,
                )
            )
        sections.extend(
            _build_journal_region_sections(
                character,
                active_keys,
                tracked_key=tracked_key,
                status="active",
            )
        )
        if len(sections) == 1:
            sections.append(
                _section(
                    "Active Quests",
                    "assignment",
                    "entries",
                    items=[_entry("No active quests right now.", icon="info")],
                    variant="active",
                )
            )
    else:
        sections.extend(
            _build_journal_region_sections(
                character,
                completed_keys,
                status="completed",
            )
        )
        if len(sections) == 1:
            sections.append(
                _section(
                    "Completed Quests",
                    "task_alt",
                    "entries",
                    items=[_entry("No completed quests yet.", icon="info")],
                    variant="archive",
                )
            )

    return {
        **_make_view(
            "",
            "Journal",
            eyebrow_icon=None,
            title_icon="menu_book",
            subtitle="",
            chips=[],
            sections=sections,
            actions=[],
            back=True,
            reactive=_reactive_from_character(character, scene="journal"),
        ),
        "variant": "journal",
    }


def _build_party_member_entry(viewer, member, leader_id, mode="status"):
    member.ensure_brave_character()
    location = member.location.key if member.location else "Nowhere"
    online = "online" if member.is_connected else "offline"
    lines = [f"{'Leader' if member.id == leader_id else 'Member'} · {online}", f"Room: {location}"]
    command = None
    actions = []
    follow_target = get_follow_target(viewer)

    if mode == "status":
        resources = member.db.brave_resources or {}
        derived = member.db.brave_derived_stats or {}
        lines.append(f"HP: {resources.get('hp', 0)}/{derived.get('max_hp', 0)}")
        route = format_route_hint(viewer.location, member.location) if viewer.location else "route unavailable"
        lines.append(f"Route from you: {route}")
        member_follow_target = get_follow_target(member)
        if member_follow_target:
            lines.append(f"Following: {member_follow_target.key}")
    else:
        route = format_route_hint(viewer.location, member.location) if viewer.location else "route unavailable"
        lines.append(f"Route: {route}")

    if member.id != viewer.id:
        if member.location and viewer.location and member.location == viewer.location:
            if follow_target and follow_target.id == member.id:
                command = "party stay"
                actions.append(_action("Stay", "party stay", "do_not_disturb_on", tone="muted"))
            else:
                command = f"party follow {member.key}"
                actions.append(_action("Follow", command, "directions_walk"))
        actions.append(_action("Where", "party where", "location_searching", tone="muted"))
        if leader_id == viewer.id:
            actions.append(
                _action(
                    "Kick",
                    f"party kick {member.key}",
                    "person_remove",
                    tone="danger",
                    confirm=f"Remove {member.key} from the party?",
                )
            )

    return _entry(member.key, lines=lines, icon="person", command=command, actions=actions)


def build_party_view(character, mode="status"):
    """Return a browser-first main view for party screens."""

    members = get_party_members(character)
    leader = get_party_leader(character)
    invites = [
        leader_obj for leader_obj in (
            get_character_by_id(invite_id) for invite_id in (character.db.brave_party_invites or [])
        ) if leader_obj
    ]
    follow_target = get_follow_target(character)
    viewer_party_id = getattr(character.db, "brave_party_id", None)
    party_leader_id = getattr(character.db, "brave_party_leader_id", None)
    party_is_full = len(members) >= 4

    nearby_player_items = []
    for nearby in _local_player_characters(character):
        nearby_party_id = getattr(nearby.db, "brave_party_id", None)
        if viewer_party_id and nearby_party_id == viewer_party_id:
            continue
        if nearby_party_id:
            continue
        if viewer_party_id and party_leader_id != character.id:
            continue
        if party_is_full:
            continue

        nearby_player_items.append(
            _item(
                nearby.key,
                icon="person",
                command=f"party invite {nearby.key}",
            )
        )

    sections = []
    if not members:
        sections.append(
            _section(
                "Status",
                "groups",
                "lines",
                lines=[
                    "You are not currently in a party.",
                    "Invite someone nearby to start one.",
                ],
            )
        )
    else:
        sections.append(
            _section(
                "Members" if mode == "status" else "Party Routes",
                "groups",
                "entries",
                items=[_build_party_member_entry(character, member, character.db.brave_party_leader_id, mode=mode) for member in members],
            )
        )

    if nearby_player_items:
        sections.append(
            _section(
                "Nearby Players",
                "person_add",
                "list",
                items=nearby_player_items,
            )
        )

    if invites:
        sections.append(
            _section(
                "Invites",
                "mail",
                "list",
                items=[
                    _item(
                        invite.key,
                        icon="person_add",
                        command=f"party accept {invite.key}",
                        actions=[_action("Decline", f"party decline {invite.key}", "person_off", tone="danger")],
                    )
                    for invite in invites
                ],
            )
        )

    if members:
        command_items = [_item("Locate your party", icon="location_searching", command="party where")]
        if follow_target:
            command_items.append(_item("Stop following", icon="do_not_disturb_on", command="party stay"))
        command_items.append(_item("Leave party", icon="logout", command="party leave"))
        sections.append(_section("Actions", "terminal", "list", items=command_items))

    view = _make_view(
        "",
        "Party",
        eyebrow_icon=None,
        title_icon="group",
        subtitle="",
        chips=[],
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="party"),
    )
    if view.get("back_action"):
        view["back_action"]["label"] = ""
        view["back_action"]["aria_label"] = "Close"
    return {**view, "variant": "party"}


def build_shop_view(character):
    """Return a browser-first main view for the Outfitters."""

    bonus = get_shop_bonus(character)
    sellables = get_sellable_entries(character)
    reserved = get_reserved_entries(character)

    sellable_entries = []
    for entry in sellables:
        template = ITEM_TEMPLATES.get(entry["template_id"], {})
        lines = [f"{entry['unit_price']} silver each · {entry['total_price']} silver total"]
        if entry["reserved"]:
            lines.append(f"Holding {entry['reserved']} for active quest progress")
        sellable_entries.append(
            _entry(
                f"{entry['name']} x{entry['sellable']}",
                lines=lines,
                summary=template.get("summary"),
                icon="sell",
                command=f"sell {entry['name']}",
                actions=[
                    _action("Sell 1", f"sell {entry['name']}", "sell")
                ] + (
                    [
                        _action(
                            "Sell All",
                            f"sell {entry['name']} = all",
                            "layers",
                            tone="danger",
                            confirm=f"Sell all available {entry['name']}?",
                        )
                    ]
                    if entry["sellable"] > 1
                    else []
                ),
            )
        )

    chips = [
        _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
    ]
    if bonus:
        chips.append(_chip(format_shop_bonus(bonus), "storefront", "good"))

    return _make_view(
        "Town Service",
        "Brambleford Outfitters",
        eyebrow_icon="storefront",
        title_icon="sell",
        subtitle="Leda buys practical finds and pays in clean town silver.",
        chips=chips,
        actions=[] if bonus else [_action("Work Shift", "shift", "front_hand", tone="accent")],
        sections=[
            _section(
                "Sell",
                "sell",
                "entries",
                items=sellable_entries or [_entry("Nothing sellable right now.", icon="inventory_2")],
            ),
            _section(
                "Reserved",
                "assignment",
                "list",
                items=[{"text": f"{entry['name']} x{entry['reserved']}", "icon": "lock"} for entry in reserved]
                or [{"text": "Nothing currently reserved.", "icon": "info"}],
            ),
        ],
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_forge_view(character):
    """Return a browser-first main view for forge orders."""

    entries = get_forge_entries(character)
    ready_entries = []
    pending_entries = []

    for entry in entries:
        material_text = ", ".join(
            f"{material['name']} {material['owned']}/{material['required']}"
            for material in entry["materials"]
        )
        lines = [
            f"{entry['slot_label']} · {entry['silver_cost']} silver",
            "Materials: " + material_text if material_text else "No extra materials needed",
        ]
        if entry["result_bonuses"]:
            lines.append("Result: " + entry["result_bonuses"])
        command = None
        confirm = None
        actions = []
        if entry["ready"]:
            command = f"forge {entry['source_name']}"
            confirm = f"Forge {entry['result_name']} for {entry['silver_cost']} silver?"
            actions.append(_action("Forge", command, "construction", tone="accent", confirm=confirm))
        formatted = _entry(
            f"{entry['source_name']} -> {entry['result_name']}",
            lines=lines,
            summary=entry.get("text", ""),
            icon="construction" if entry["ready"] else "schedule",
            command=command,
            confirm=confirm,
            actions=actions,
        )
        if entry["ready"]:
            ready_entries.append(formatted)
        else:
            pending_entries.append(formatted)

    ready_count = sum(1 for entry in entries if entry["ready"])
    chips = [
        _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
        _chip(f"{ready_count} ready", "task_alt", "good" if ready_count else "muted"),
    ]

    return _make_view(
        "Town Service",
        "Forge",
        eyebrow_icon="construction",
        title_icon="build",
        subtitle="Torren can rework your equipped field kit into sturdier frontier gear.",
        chips=chips,
        sections=[
            _section(
                "Ready",
                "construction",
                "entries",
                items=ready_entries or [_entry("Nothing is fully ready yet.", icon="schedule")],
            ),
            _section(
                "Needs Materials",
                "inventory",
                "entries",
                items=pending_entries or [_entry("No pending orders.", icon="task_alt")],
            ),
        ],
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_cook_view(character, *, status_message=None, status_tone="muted"):
    """Return a browser-first main view for the hearth and meal loop."""

    ready_entries = []
    known_entries = []
    locked_entries = []
    meal_entries = []

    for recipe in get_cooking_entries(character):
        missing = list(recipe["missing"])
        lines = [recipe["ingredient_text"], "Ready to cook" if recipe["ready"] else ("Missing: " + ", ".join(missing) if recipe["known"] else "Locked recipe")]
        formatted = _entry(
            recipe["name"],
            lines=lines,
            summary=recipe["summary"] if recipe["known"] else (recipe["unlock_text"] or "You have not learned this recipe yet."),
            icon="restaurant" if recipe["ready"] else ("kitchen" if recipe["known"] else "lock"),
            command=f"cook {recipe['name']}" if recipe["ready"] else None,
            actions=[_action("Cook", f"cook {recipe['name']}", "restaurant", tone="accent")] if recipe["ready"] else [],
        )
        if not recipe["known"]:
            locked_entries.append(formatted)
        elif recipe["ready"]:
            ready_entries.append(formatted)
        else:
            known_entries.append(formatted)

    for entry in (character.db.brave_inventory or []):
        template_id = entry.get("template")
        quantity = entry.get("quantity", 0)
        item = ITEM_TEMPLATES.get(template_id, {})
        if item.get("kind") != "meal" or quantity <= 0:
            continue

        restore_text = _format_restore_summary(item.get("restore", {}), character)
        bonus_text = _format_context_bonus_summary(item.get("meal_bonuses", {}), character)
        lines = [text for text in (restore_text and "Restore: " + restore_text, bonus_text and "Buff: " + bonus_text) if text]
        meal_entries.append(
            _entry(
                item.get("name", template_id) + (f" x{quantity}" if quantity > 1 else ""),
                lines=lines,
                summary=item.get("summary"),
                icon="lunch_dining",
                command=f"eat {item.get('name', template_id)}",
                actions=[_action("Eat", f"eat {item.get('name', template_id)}", "restaurant", tone="good")],
            )
        )

    chips = [
        _chip(f"{len(ready_entries)} ready", "task_alt", "good" if ready_entries else "muted"),
    ]
    if meal_entries:
        chips.append(_chip(f"{len(meal_entries)} meals packed", "lunch_dining", "accent"))

    sections = []
    if status_message:
        status_icon = "task_alt" if status_tone == "good" else "info"
        sections.append(
            _section(
                "Kitchen Notes",
                status_icon,
                "lines",
                lines=[status_message],
                span="wide",
            )
        )

    sections.extend(
        [
            _section("Ready", "restaurant", "entries", items=ready_entries or [_entry("Nothing is ready from your current ingredients.", icon="schedule")]),
            _section("Known", "grocery", "entries", items=known_entries or [_entry("No other known recipes are waiting on ingredients.", icon="task_alt")]),
            _section("Locked", "lock", "entries", items=locked_entries or [_entry("No locked recipes right now.", icon="task_alt")]),
            _section("Meals", "lunch_dining", "entries", items=meal_entries or [_entry("You are not carrying any prepared meals.", icon="backpack")]),
        ]
    )

    return _make_view(
        "Town Service",
        "Hearth",
        eyebrow_icon="restaurant",
        title_icon="soup_kitchen",
        subtitle="Simple inn recipes you can turn out without wasting the room or the pan.",
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_fishing_view(character, *, status_message=None, status_tone="muted"):
    """Return a browser-first main view for fishing tackle setup."""

    summary = get_fishing_spot_summary(character)
    spot = summary["spot"] or {}
    current_rod = summary["rod"] or {}
    current_lure = summary["lure"] or {}
    room = getattr(character, "location", None)
    fishing_state = getattr(getattr(character, "ndb", None), "brave_fishing", None) or {}
    fishing_phase = fishing_state.get("phase")
    active_rod_key = current_rod.get("key")
    active_lure_key = current_lure.get("key")

    rod_entries = []
    for rod_data in get_available_fishing_rods(character, include_locked=True):
        rod_key = rod_data["key"]
        selected = rod_key == active_rod_key
        rod_entries.append(
            _entry(
                rod_data.get("name", rod_key.replace("_", " ").title()),
                lines=[
                    f"Power {int(rod_data.get('power', 0) or 0)}",
                    f"Stability {rod_data.get('stability', 0)}",
                ],
                summary=rod_data.get("summary") if rod_data.get("available", True) else (rod_data.get("unlock_text") or "Locked until you prove yourself further."),
                icon="straighten",
                command=None if selected or not rod_data.get("available", True) else f"fish rod {rod_data.get('name', rod_key)}",
                actions=[] if selected or not rod_data.get("available", True) else [_action("Select", f"fish rod {rod_data.get('name', rod_key)}", "straighten", tone="accent")],
                badge="Selected" if selected else (None if rod_data.get("available", True) else "Locked"),
                selected=selected,
            )
        )

    lure_entries = []
    for lure_data in get_available_fishing_lures(character, include_locked=True):
        lure_key = lure_data["key"]
        selected = lure_key == active_lure_key
        favored = ", ".join(ITEM_TEMPLATES[item_id]["name"] for item_id in lure_data.get("attracts", []) if item_id in ITEM_TEMPLATES)
        lines = []
        if favored:
            lines.append("Favored: " + favored)
        zone_bonus = (lure_data.get("zone_bonus", {}) or {}).get(getattr(getattr(room, "db", None), "brave_room_id", None), 0)
        if zone_bonus:
            lines.append(f"Water bonus {zone_bonus}")
        lure_entries.append(
            _entry(
                lure_data.get("name", lure_key.replace("_", " ").title()),
                lines=lines,
                summary=lure_data.get("summary") if lure_data.get("available", True) else (lure_data.get("unlock_text") or "Locked until you prove yourself further."),
                icon="tune",
                command=None if selected or not lure_data.get("available", True) else f"fish lure {lure_data.get('name', lure_key)}",
                actions=[] if selected or not lure_data.get("available", True) else [_action("Select", f"fish lure {lure_data.get('name', lure_key)}", "tune", tone="accent")],
                badge="Selected" if selected else (None if lure_data.get("available", True) else "Locked"),
                selected=selected,
            )
        )

    chips = []
    if current_rod:
        chips.append(_chip(current_rod.get("name", "Rod"), "straighten", "accent"))
    if current_lure:
        chips.append(_chip(current_lure.get("name", "Lure"), "tune", "muted"))
    if fishing_phase == "waiting":
        chips.append(_chip("Line In Water", "waves", "good"))
    elif fishing_phase == "bite":
        chips.append(_chip("Bite", "phishing", "warn"))
    elif fishing_phase == "minigame":
        chips.append(_chip("Line Active", "phishing", "good"))

    actions = []
    if can_borrow_fishing_tackle(character):
        actions.append(_action("Borrow Kit", "fish borrow kit", "inventory_2", tone="muted"))
    if fishing_phase == "bite":
        actions.append(_action("Reel", "reel", "phishing", tone="accent"))
    elif fishing_phase not in {"waiting", "minigame"}:
        actions.append(_action("Cast Line", "fish cast", "phishing", tone="accent"))

    water_lines = [spot.get("cast_text", "The water looks workable.")]
    if fishing_phase == "waiting":
        water_lines.append("Your line is in the water. Wait for a real bite.")
    elif fishing_phase == "bite":
        water_lines.append("Something is on the line. Reel now.")
    elif fishing_phase == "minigame":
        water_lines.append("Your line is active. Work the fishing popup to land it.")

    sections = []
    if status_message:
        sections.append(
            _section(
                "River Notes",
                "task_alt" if status_tone == "good" else "info",
                "lines",
                lines=[status_message],
                span="wide",
            )
        )
    sections.append(
        _section(
            "Current Water",
            "waves",
            "entries",
            items=[
                _entry(
                    spot.get("name", room.key if room else "Fishing Water"),
                    lines=water_lines,
                    icon="waves",
                    actions=(
                        ([_action("Borrow Kit", "fish borrow kit", "inventory_2", tone="muted")] if can_borrow_fishing_tackle(character) else [])
                        + ([_action("Reel", "reel", "phishing", tone="accent")] if fishing_phase == "bite" else [])
                        + ([_action("Cast", "fish cast", "phishing", tone="accent")] if fishing_phase not in {"waiting", "bite", "minigame"} else [])
                    ),
                )
            ],
        )
    )
    sections.append(
        _section(
            "Active Tackle",
            "inventory_2",
            "entries",
            items=[
                _entry(
                    current_rod.get("name", "No rod selected"),
                    meta="Rod",
                    lines=[current_rod.get("summary", "")],
                    icon="straighten",
                ),
                _entry(
                    current_lure.get("name", "No lure selected"),
                    meta="Lure",
                    lines=[current_lure.get("summary", "")],
                    icon="tune",
                ),
            ],
        )
    )
    sections.append(_section("Rods", "straighten", "entries", items=rod_entries or [_entry("No rods are available.", icon="block")]))
    sections.append(_section("Lures", "tune", "entries", items=lure_entries or [_entry("No lures are available.", icon="block")]))

    return _make_view(
        "Town Activity",
        "Fishing",
        eyebrow_icon="phishing",
        title_icon="waves",
        subtitle="Cast a line, read the water, and swap tackle when the catch calls for it.",
        chips=chips,
        sections=sections,
        actions=actions,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_tinker_view(character, *, status_message=None, status_tone="muted"):
    """Return a browser-first main view for tinkering recipes."""

    ready_entries = []
    known_entries = []
    locked_entries = []
    for entry in get_tinkering_entries(character):
        lines = []
        if entry["base_name"]:
            lines.append(f"Base: {entry['base_name']} {entry['base_owned']}/1")
        if entry["components"]:
            lines.append(
                "Parts: "
                + ", ".join(f"{row['name']} {row['owned']}/{row['required']}" for row in entry["components"])
            )
        if entry["silver_cost"]:
            lines.append(f"Silver: {entry['silver_cost']}")
        if entry["result_bonuses"]:
            lines.append("Result: " + entry["result_bonuses"])
        payload = _entry(
            entry["name"],
            lines=lines,
            summary=entry["summary"] or entry["result_summary"],
            icon="handyman" if entry["ready"] else "inventory_2",
            command=f"tinker {entry['name']}" if entry["ready"] else None,
            actions=[_action("Build", f"tinker {entry['name']}", "build", tone="accent")] if entry["ready"] else [],
            badge="Ready" if entry["ready"] else ("Known" if entry["known"] else "Locked"),
        )
        if not entry["known"]:
            locked_entries.append(payload)
        elif entry["ready"]:
            ready_entries.append(payload)
        else:
            known_entries.append(payload)

    chips = [_chip(f"{character.db.brave_silver or 0} silver", "payments", "muted")]
    if ready_entries:
        chips.append(_chip(f"{len(ready_entries)} ready", "task_alt", "good"))

    sections = []
    if status_message:
        sections.append(_section("Bench Notes", "task_alt" if status_tone == "good" else "info", "lines", lines=[status_message], span="wide"))
    sections.extend(
        [
            _section("Ready Now", "build", "entries", items=ready_entries or [_entry("Nothing is ready from your current pack.", icon="schedule")]),
            _section("Known Designs", "inventory_2", "entries", items=known_entries or [_entry("No other known designs are close to completion.", icon="construction")]),
            _section("Locked Designs", "lock", "entries", items=locked_entries or [_entry("No locked tinkering designs yet.", icon="task_alt")]),
        ]
    )

    return _make_view(
        "Town Service",
        "Workbench Ledger",
        eyebrow_icon="build",
        title_icon="handyman",
        subtitle="Small frontier repairs, field fixes, and rough bench work that keeps a pack useful.",
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_portals_view(character):
    """Return a browser-first main view for current Nexus gates."""

    sections = []
    for status_key, section_title in (("stable", "Stable"), ("dormant", "Dormant"), ("sealed", "Sealed")):
        items = []
        for portal in PORTALS.values():
            if portal["status"] != status_key:
                continue
            lines = [f"Resonance: {portal['resonance'].replace('_', ' ').title()}"]
            if portal.get("travel_hint"):
                lines.append(f"Entry route: {portal['travel_hint']}")
            command = None
            actions = []
            if portal["status"] == "stable" and portal.get("travel_hint"):
                command = _movement_command(portal["travel_hint"], f"travel {portal['travel_hint']}")
                actions.append(_action("Travel", command, "travel_explore", tone="accent"))
            items.append(
                _entry(
                    portal["name"],
                    meta=PORTAL_STATUS_LABELS.get(portal["status"], portal["status"].title()),
                    lines=lines,
                    summary=portal["summary"],
                    icon="travel_explore",
                    command=command,
                    actions=actions,
                )
            )
        sections.append(_section(section_title, "travel_explore", "entries", items=items or [_entry("None at the moment.", icon="info")]))

    stable_count = sum(1 for portal in PORTALS.values() if portal["status"] == "stable")
    return _make_view(
        "Nexus",
        "Gates",
        eyebrow_icon="travel_explore",
        title_icon="public",
        subtitle="The ring lists what Brambleford can currently reach and what still refuses to answer.",
        chips=[_chip(f"{stable_count} stable", "travel_explore", "accent" if stable_count else "muted")],
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_travel_view(character):
    """Return a browser-first main view for travel fallback."""

    room = getattr(character, "location", None)
    exits = sort_exits(list(room.exits)) if room else []
    route_entries = []
    for exit_obj in exits:
        direction = getattr(exit_obj.db, "brave_direction", exit_obj.key).lower()
        aliases = [alias for alias in exit_obj.aliases.all() if alias.lower() != direction]
        lines = []
        if aliases:
            lines.append("Aliases: " + ", ".join(aliases))
        command = _movement_command(direction, exit_obj.key)
        route_entries.append(
            _entry(
                getattr(exit_obj.destination, "key", None) or exit_obj.key,
                meta=direction.title(),
                lines=lines,
                icon="route",
                badge=_short_direction(direction),
                command=command,
            )
        )

    return _make_view(
        "Travel",
        "Routes",
        eyebrow_icon="explore",
        title_icon="route",
        subtitle=f"Current room: {room.key}" if room else "No current room.",
        chips=[_chip(f"{len(exits)} exits", "move_selection_right", "accent" if exits else "muted")],
        sections=[
            _section("From Here", "route", "entries", items=route_entries or [_entry("No routes available from here.", icon="block")]),
        ],
        back=True,
        reactive=_reactive_from_character(character, scene="travel"),
    )


def build_arcade_detail_view(cabinet):
    """Return a descriptive inspect view for one local arcade cabinet."""

    paragraphs = [line.strip() for line in str(getattr(getattr(cabinet, "db", None), "desc", "") or "").splitlines() if line.strip()]
    if not paragraphs:
        paragraphs = ["The cabinet hums softly, waiting for a coin and a steady hand."]

    return {
        **_make_view(
            "",
            _display_name(cabinet),
            eyebrow_icon=None,
            title_icon="sports_esports",
            subtitle="",
            sections=[
                _section(
                    "",
                    "menu_book",
                    "lines",
                    lines=paragraphs,
                    hide_label=True,
                )
            ],
            actions=[_action("Play", f"arcade open {cabinet.key}", "sports_esports", tone="accent")],
            back=True,
            reactive=_reactive_view(getattr(cabinet, "location", None), scene="read"),
        ),
        "variant": "read",
    }


def build_arcade_play_view(character, cabinet, game_key):
    """Return a browser-first play view for one arcade game."""

    definition = ARCADE_GAMES[game_key]
    reward = get_reward_definition(cabinet, game_key)
    leaderboard = cabinet.get_leaderboard(game_key)
    high_score = 0
    if leaderboard:
        try:
            high_score = max(0, int((leaderboard[0] or {}).get("score", 0) or 0))
        except (TypeError, ValueError):
            high_score = 0
    chips = [
        _chip(f"Best {format_arcade_score(get_personal_best(character, cabinet, game_key))}", "military_tech", "muted"),
    ]
    if reward.get("threshold", 0) and reward.get("item_name"):
        if has_arcade_reward(character, cabinet, game_key):
            chips.append(_chip(f"Prize Claimed: {reward['item_name']}", "workspace_premium", "good"))
        else:
            chips.append(
                _chip(f"Prize {format_arcade_score(reward['threshold'])}: {reward['item_name']}", "workspace_premium", "accent")
            )

    return {
        **_make_view(
            _display_name(cabinet),
            definition["name"],
            eyebrow_icon="sports_esports",
            title_icon="videogame_asset",
            chips=chips,
            sections=[
                _section(
                    "Cabinet Screen",
                    "sports_esports",
                    "arcade",
                    lines=[],
                    span="mapwide",
                    game_key=game_key,
                    high_score=high_score,
                    best_score=get_personal_best(character, cabinet, game_key),
                ),
            ],
            actions=[_action("Quit", "arcade quit", "close", tone="muted")],
            reactive=_reactive_from_character(character, scene="arcade"),
        ),
        "variant": "arcade",
    }


def build_combat_view(encounter, character):
    """Return a browser-first sticky combat view with clickable actions."""

    from typeclasses.scripts import ABILITY_LIBRARY

    condition_telegraph_enemies = {
        "briar_imp",
        "cave_bat_swarm",
        "cave_spider",
        "carrion_hound",
        "drowned_warder",
        "fen_wisp",
        "goblin_hexer",
        "grave_crow",
        "grubnak_the_pot_king",
        "hollow_lantern",
        "hollow_wisp",
        "mire_hound",
        "miretooth",
        "restless_shade",
        "rot_crow",
        "ruk_fence_cutter",
        "sir_edric_restless",
        "sludge_slime",
    }

    timing_scale = max(1, int(round(1 / max(0.1, float(getattr(encounter, "interval", 1) or 1)))))

    def display_atb_ticks(raw_ticks):
        raw_ticks = int(raw_ticks or 0)
        if raw_ticks <= 0:
            return 0
        return max(1, (raw_ticks + timing_scale - 1) // timing_scale)

    render_now_ms = int(round(time.time() * 1000))
    render_tick_ms = max(1, int(round(float(getattr(encounter, "interval", 1) or 1) * 1000)))

    def participant_id(participant):
        return participant.get("id") if isinstance(participant, dict) else participant.id

    def participant_name(participant):
        return str(participant.get("key") if isinstance(participant, dict) else participant.key)

    def participant_resources(participant):
        if isinstance(participant, dict):
            return {"hp": int(participant.get("hp", 0) or 0)}
        return participant.db.brave_resources or {}

    def participant_derived(participant):
        if isinstance(participant, dict):
            return {
                "max_hp": int(participant.get("max_hp", 1) or 1),
                "max_mana": 0,
                "max_stamina": 0,
            }
        return participant.db.brave_derived_stats or {}

    def participant_background_icon(participant):
        if isinstance(participant, dict):
            return participant.get("icon", "pets")
        return get_class_icon(participant.db.brave_class, CLASSES.get(participant.db.brave_class))

    def actor_atb_state(*, participant=None, enemy=None):
        getter = getattr(encounter, "_get_actor_atb_state", None)
        if not callable(getter):
            return {}
        try:
            if participant is not None:
                if isinstance(participant, dict):
                    return render_atb_state(getter(companion=participant) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
                return render_atb_state(getter(character=participant) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
            if enemy is not None:
                return render_atb_state(getter(enemy=enemy) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
        except Exception:
            return {}
        return {}

    def combat_action_item(action):
        return _item(
            action.get("text", action.get("label", "")),
            badge=action.get("badge"),
            command=action.get("command"),
            prefill=action.get("prefill"),
            confirm=action.get("confirm"),
            actions=action.get("actions"),
            picker=action.get("picker"),
            tooltip=action.get("tooltip"),
        )

    def combat_option_icon(action):
        if action.get("kind") == "ability":
            return get_ability_icon_name(action.get("key"))
        if action.get("kind") == "social":
            return "sentiment_satisfied"
        return "lunch_dining"

    def party_has_harmful_condition():
        for participant in participants:
            state = encounter._get_participant_state(participant)
            if any(int(state.get(key, 0) or 0) > 0 for key in ("bleed_turns", "poison_turns", "curse_turns", "snare_turns")):
                return True
        return False

    def build_reaction_window():
        roles = set()
        threats = []
        harmful_condition_active = party_has_harmful_condition()
        for enemy in enemies:
            state = actor_atb_state(enemy=enemy)
            if (state or {}).get("phase") != "winding":
                continue
            timing = dict((state or {}).get("timing") or {})
            action = dict((state or {}).get("current_action") or {})
            threat_roles = {"guard"}
            if timing.get("interruptible"):
                threat_roles.add("interrupt")
            template_key = str(enemy.get("template_key") or "").strip().lower()
            if harmful_condition_active or template_key in condition_telegraph_enemies:
                threat_roles.add("cleanse")
            roles.update(threat_roles)
            threats.append(
                {
                    "enemy_id": enemy.get("id"),
                    "enemy": str(enemy.get("key") or "Enemy"),
                    "label": action.get("label") or enemy.get("telegraph_label") or "Attack",
                    "interruptible": bool(timing.get("interruptible")),
                    "roles": sorted(threat_roles),
                }
            )
        return {"active": bool(threats), "roles": sorted(roles), "threats": threats}

    def mark_reaction_actions(actions, reaction_roles):
        for action in actions:
            role = action.get("reaction_role")
            recommended = bool(role and role in reaction_roles)
            action["reaction_recommended"] = recommended
            if recommended:
                action["reaction_hint"] = f"Reaction window: {role}"
                if action.get("tooltip"):
                    action["tooltip"] = f"{action['tooltip']}\nReaction window: useful now."
                else:
                    action["tooltip"] = "Reaction window: useful now."
        return actions

    def combat_picker_options(action):
        options = []
        reaction_recommended = bool(action.get("reaction_recommended"))
        if action.get("enabled"):
            meta = action.get("text")
            if reaction_recommended:
                meta = f"{meta} · REACTION" if meta else "REACTION"
            primary = {
                "label": action.get("label") or action.get("text") or "",
                "icon": combat_option_icon(action),
                "meta": meta,
                "tone": "good" if reaction_recommended else ("accent" if action.get("kind") == "ability" else "good"),
                "tooltip": action.get("tooltip"),
            }
            if action.get("picker"):
                primary["picker"] = action.get("picker")
            elif action.get("command"):
                primary["command"] = action.get("command")
            if primary.get("command") or primary.get("picker"):
                options.append(primary)
        for inline_action in action.get("actions", []) or []:
            picker = inline_action.get("picker")
            command = inline_action.get("command")
            if not picker and not command:
                continue
            option = {
                "label": action.get("label") or action.get("text") or "",
                "icon": inline_action.get("icon") or combat_option_icon(action),
                "meta": inline_action.get("label"),
                "tone": "good" if reaction_recommended else (inline_action.get("tone") or "muted"),
                "tooltip": action.get("tooltip"),
            }
            if picker:
                option["picker"] = picker
            if command:
                option["command"] = command
            options.append(option)
        return options

    def build_combat_action_picker(title, icon_name, actions, empty_text):
        options = []
        for action in actions:
            options.extend(combat_picker_options(action))
        has_reaction = any(action.get("reaction_recommended") for action in actions)
        return _action(
            title,
            None,
            icon_name,
            tone="good" if has_reaction else ("accent" if options else "muted"),
            picker=_picker(
                title,
                subtitle="Reaction tools are highlighted." if has_reaction else "Choose an action.",
                picker_id=f"combat-{title.strip().lower()}",
                options=options,
                body=[] if options else [empty_text],
            ),
        )

    def atb_chip(state, *, label_ready="Ready", ready_tone="accent"):
        phase = (state or {}).get("phase")
        if phase == "ready":
            return _chip(label_ready, "bolt", ready_tone)
        if phase == "winding":
            ticks = display_atb_ticks((state or {}).get("ticks_remaining", 0))
            return _chip(f"Winding {ticks}", "hourglass_top", "danger")
        if phase == "recovering":
            ticks = display_atb_ticks((state or {}).get("ticks_remaining", 0))
            return _chip(f"Recovering {ticks}", "timer", "muted")
        if phase == "cooldown":
            ticks = display_atb_ticks((state or {}).get("ticks_remaining", 0))
            return _chip(f"Cooldown {ticks}", "timer", "muted")
        return None

    def atb_meter(state, *, enemy=False):
        state = dict(state or {})
        phase = state.get("phase")
        timing = dict(state.get("timing") or {})
        gauge = int(state.get("gauge", 0) or 0)
        ready_gauge = max(1, int(state.get("ready_gauge", 400) or 400))
        ticks_remaining = int(state.get("ticks_remaining", 0) or 0)
        phase_started_at_ms = int(state.get("phase_started_at_ms", 0) or 0)
        phase_duration_ms = int(state.get("phase_duration_ms", 0) or 0)
        elapsed_ms = max(0, render_now_ms - phase_started_at_ms) if phase_started_at_ms > 0 else 0
        phase_remaining_ms = max(0, phase_duration_ms - elapsed_ms) if phase_duration_ms > 0 else 0

        value = gauge
        tone = "atb"
        if phase in {"ready", "resolving", "winding"}:
            value = 100
            tone = "danger" if enemy else "good"
            if phase == "winding":
                tone = "danger" if enemy else "warn"
        elif phase in {"recovering", "cooldown"}:
            value = 0
            tone = "muted"
        else:
            value = max(0, min(100, int(round((gauge / ready_gauge) * 100))))
        meter_meta = {
            "kind": "atb",
            "hide_value": True,
            "phase": phase or "charging",
            "gauge": gauge,
            "phase_start_gauge": int(state.get("phase_start_gauge", gauge) or 0),
            "phase_started_at_ms": phase_started_at_ms,
            "phase_duration_ms": phase_duration_ms,
            "phase_remaining_ms": phase_remaining_ms,
            "ready_gauge": ready_gauge,
            "fill_rate": int(state.get("fill_rate", 100) or 100),
            "tick_ms": render_tick_ms,
            "ticks_remaining": ticks_remaining,
            "windup_ticks": int(timing.get("windup_ticks", 0) or 0),
            "recovery_ticks": int(timing.get("recovery_ticks", 0) or 0),
            "cooldown_ticks": int(timing.get("cooldown_ticks", 0) or 0),
        }
        return _meter("ATB", value, 100, tone=tone, meta=meter_meta)

    def build_participant_status_chips(state):
        chips = []
        if state.get("guard", 0) > 0:
            chips.append(_chip("Guarding", "shield", "good"))
        if state.get("reaction_redirect_to"):
            chips.append(_chip("Intercept", "swap_horiz", "good"))
        elif state.get("reaction_guard", 0) > 0:
            chips.append(_chip("Answer Ready", "shield", "accent"))
        if state.get("bleed_turns", 0) > 0:
            chips.append(_chip(f"Bleeding {state['bleed_turns']}", "water_drop", "danger"))
        if state.get("poison_turns", 0) > 0:
            chips.append(_chip(f"Poisoned {state['poison_turns']}", "warning", "danger"))
        if state.get("curse_turns", 0) > 0:
            chips.append(_chip(f"Cursed {state['curse_turns']}", "warning", "warn"))
        if state.get("snare_turns", 0) > 0:
            chips.append(_chip(f"Snared {state['snare_turns']}", "block", "warn"))
        if state.get("feint_turns", 0) > 0:
            chips.append(_chip("Feint Ready", "bolt", "accent"))
        if state.get("stealth_turns", 0) > 0:
            chips.append(_chip("Hidden", "visibility_off", "muted"))
        return chips

    def build_enemy_status_chips(enemy):
        chips = []
        telegraph_outcome = str(enemy.get("telegraph_outcome") or "").lower()
        telegraph_answer = str(enemy.get("telegraph_answer") or "")
        if telegraph_outcome == "interrupted":
            chips.append(_chip("Interrupted", "block", "good"))
        elif telegraph_outcome == "redirected":
            chips.append(_chip("Redirected", "swap_horiz", "good"))
        elif telegraph_outcome == "mitigated":
            chips.append(_chip("Mitigated", "shield", "good"))
        elif telegraph_outcome == "unanswered":
            chips.append(_chip("Landed Clean", "priority_high", "danger"))
        elif telegraph_outcome == "pending" and telegraph_answer:
            chips.append(_chip(f"Answer: {telegraph_answer}", "shield", "accent"))
        if enemy.get("marked_turns", 0) > 0:
            chips.append(_chip(f"Marked {enemy['marked_turns']}", "my_location", "accent"))
        if enemy.get("bound_turns", 0) > 0:
            chips.append(_chip(f"Bound {enemy['bound_turns']}", "block", "warn"))
        if enemy.get("hidden_turns", 0) > 0:
            chips.append(_chip(f"Hidden {enemy['hidden_turns']}", "visibility_off", "muted"))
        if enemy.get("shielded"):
            chips.append(_chip("Warded", "shield", "good"))
        if enemy.get("bleed_turns", 0) > 0:
            chips.append(_chip(f"Bleeding {enemy['bleed_turns']}", "water_drop", "danger"))
        if enemy.get("poison_turns", 0) > 0:
            chips.append(_chip(f"Poisoned {enemy['poison_turns']}", "warning", "warn"))
        return chips

    def hp_meter(current_hp, max_hp):
        ratio = (current_hp / max_hp) if max_hp else 0
        if ratio <= 0.25:
            tone = "danger"
        elif ratio <= 0.5:
            tone = "warn"
        else:
            tone = "good"
        return _meter("HP", current_hp, max_hp, tone=tone)

    def resource_meter(resource_key, current_value, max_value):
        short_label = {
            "mana": "MP",
            "stamina": "STA",
        }.get(resource_key, get_resource_label(resource_key, character)[:3].upper())
        tone = {
            "mana": "mana",
            "stamina": "stamina",
        }.get(resource_key, "accent")
        return _meter(short_label, current_value, max_value, tone=tone)

    enemies = encounter.get_active_enemies()
    participants = encounter.get_active_participants()
    encounter_title = (getattr(encounter.db, "encounter_title", "") or "").strip() or "Combat"

    ordered_participants = sorted(
        participants,
        key=lambda participant: (
            0 if not isinstance(participant, dict) and participant.id == character.id else 1,
            participant_name(participant).lower(),
        ),
    )
    player_participants = [participant for participant in ordered_participants if not isinstance(participant, dict)]
    companion_participants = [participant for participant in ordered_participants if isinstance(participant, dict)]
    ally_count = len(player_participants)
    companion_count = len(companion_participants)
    companion_by_owner = {}
    default_owner_id = player_participants[0].id if len(player_participants) == 1 else None
    for companion in companion_participants:
        owner_id = companion.get("owner_id")
        if owner_id is None:
            owner_id = default_owner_id
        companion_by_owner.setdefault(owner_id, []).append(companion)
    for owner_companions in companion_by_owner.values():
        owner_companions.sort(key=lambda companion: participant_name(companion).lower())

    foe_count = len(enemies)
    ally_label = "Ally" if ally_count == 1 else "Allies"
    companion_label = "Pet" if companion_count == 1 else "Pets"
    foe_label = "Foe" if foe_count == 1 else "Foes"
    pending_action = dict(getattr(encounter.db, "pending_actions", {}) or {}).get(str(character.id), {}) or {}
    selected_target_id = pending_action.get("target")
    selected_target_kind = None
    if pending_action.get("kind") == "attack":
        selected_target_kind = "enemy"
    elif pending_action.get("kind") == "ability":
        selected_ability = ABILITY_LIBRARY.get(pending_action.get("ability"))
        if selected_ability:
            selected_target_kind = selected_ability.get("target")
    elif pending_action.get("kind") == "item":
        selected_item = ITEM_TEMPLATES.get(pending_action.get("item"))
        selected_use = get_item_use_profile(selected_item, context="combat") or {}
        selected_target_kind = selected_use.get("target")

    reaction_window = build_reaction_window()
    combat_actions = build_combat_action_payload(encounter, character)
    reaction_roles = set(reaction_window.get("roles") or [])
    mark_reaction_actions(combat_actions.get("abilities", []), reaction_roles)
    mark_reaction_actions(combat_actions.get("items", []), reaction_roles)

    def build_companion_sidecar(companion):
        resources = participant_resources(companion)
        derived = participant_derived(companion)
        state = encounter._get_participant_state(companion)
        status_chips = build_participant_status_chips(state)
        atb_state = actor_atb_state(participant=companion)
        atb_status = atb_chip(atb_state)
        if atb_status:
            status_chips = [atb_status] + list(status_chips)
        combat_state = []
        phase = (atb_state or {}).get("phase")
        if phase == "ready":
            combat_state.append("ready")
        if state.get("reaction_guard", 0) > 0 or state.get("reaction_redirect_to"):
            combat_state.append("guarding")
        if selected_target_kind == "ally" and selected_target_id == participant_id(companion):
            status_chips = list(status_chips) + [_chip("Targeted", "my_location", "good")]
            combat_state.append("selected")
        return _entry(
            participant_name(companion),
            meta="Companion",
            icon="pets",
            background_icon=participant_background_icon(companion),
            chips=status_chips[:2],
            meters=[
                atb_meter(atb_state),
                hp_meter(resources.get("hp", 0), derived.get("max_hp", 0)),
            ],
            selected=bool(selected_target_kind == "ally" and selected_target_id == participant_id(companion)),
            combat_state=combat_state,
            entry_ref=f"c:{participant_id(companion)}",
            size_class="compact",
        )

    party_entries = []
    party_count = len(player_participants)
    for participant in player_participants:
        if not isinstance(participant, dict):
            participant.ensure_brave_character()
        resources = participant_resources(participant)
        derived = participant_derived(participant)
        state = encounter._get_participant_state(participant)
        status_chips = build_participant_status_chips(state)
        atb_state = actor_atb_state(participant=participant)
        atb_status = atb_chip(atb_state)
        if atb_status:
            status_chips = [atb_status] + list(status_chips)
        combat_state = []
        phase = (atb_state or {}).get("phase")
        if phase == "ready":
            combat_state.append("ready")
        if state.get("reaction_guard", 0) > 0 or state.get("reaction_redirect_to"):
            combat_state.append("guarding")
        meters = [atb_meter(atb_state), hp_meter(resources.get("hp", 0), derived.get("max_hp", 0))]
        for resource_key in ("stamina", "mana"):
            max_value = derived.get(f"max_{resource_key}", 0)
            if max_value > 0:
                meters.append(resource_meter(resource_key, resources.get(resource_key, 0), max_value))
        if selected_target_kind == "ally" and selected_target_id == participant_id(participant):
            status_chips = list(status_chips) + [_chip("Targeted", "my_location", "good")]
            combat_state.append("selected")

        sidecars = [build_companion_sidecar(companion) for companion in companion_by_owner.get(participant.id, [])[:1]]

        party_entries.append(
            _entry(
                participant_name(participant),
                meta=None,
                icon="person",
                background_icon=participant_background_icon(participant),
                size_class=_combat_card_size_class(participant),
                chips=status_chips,
                meters=meters,
                selected=bool(selected_target_kind == "ally" and selected_target_id == participant_id(participant)),
                combat_state=combat_state,
                entry_ref=f"p:{participant.id}",
                sidecars=sidecars,
                cluster_ref=f"p:{participant.id}",
            )
        )

    enemy_name_totals = {}
    for enemy in enemies:
        group_key = str(enemy.get("template_key") or enemy.get("key") or enemy.get("id") or "").strip().lower()
        enemy_name_totals[group_key] = enemy_name_totals.get(group_key, 0) + 1

    enemy_name_seen = {}
    enemy_entries = []
    for enemy in enemies:
        status_chips = build_enemy_status_chips(enemy)
        atb_state = actor_atb_state(enemy=enemy)
        atb_status = atb_chip(atb_state, label_ready="Acting", ready_tone="danger")
        if atb_status:
            status_chips = [atb_status] + list(status_chips)
        lines = []
        active_action = dict((atb_state or {}).get("current_action") or {})
        if (atb_state or {}).get("phase") == "winding":
            lines.append(active_action.get("label", "Attack"))
        combat_state = []
        phase = (atb_state or {}).get("phase")
        if phase == "winding":
            combat_state.append("telegraph")
        elif phase in {"ready", "resolving"}:
            combat_state.append("ready")
        if selected_target_kind == "enemy" and selected_target_id == enemy.get("id"):
            status_chips = list(status_chips) + [_chip("Targeted", "my_location", "danger")]
            combat_state.append("selected")
        group_key = str(enemy.get("template_key") or enemy.get("key") or enemy.get("id") or "").strip().lower()
        enemy_name_seen[group_key] = enemy_name_seen.get(group_key, 0) + 1
        display_name = str(enemy.get("key") or "Enemy")
        if enemy_name_totals.get(group_key, 0) > 1:
            suffix = enemy_name_seen[group_key]
            last_token = display_name.rsplit(" ", 1)[-1]
            if not last_token.isdigit():
                display_name = f"{display_name} {suffix}"
        enemy_entries.append(
            _entry(
                display_name,
                lines=lines,
                icon=_enemy_icon(enemy),
                background_icon=_enemy_icon(enemy),
                size_class=_combat_card_size_class(enemy, enemy=True),
                command=f"attack {enemy['id']}",
                chips=status_chips,
                meters=[atb_meter(atb_state, enemy=True), hp_meter(enemy["hp"], enemy["max_hp"])],
                selected=bool(selected_target_kind == "enemy" and selected_target_id == enemy.get("id")),
                combat_state=combat_state,
                entry_ref=f"e:{enemy['id']}",
            )
        )

    tutorial_guidance = []
    guidance_eyebrow = None
    guidance_title = None
    try:
        from world.tutorial import get_tutorial_combat_focus
    except Exception:
        tutorial_focus = []
    else:
        tutorial_focus = get_tutorial_combat_focus(character, encounter)
    if tutorial_focus:
        guidance_eyebrow = "Combat Tutorial"
        guidance_title = "Training Focus"
        tutorial_guidance = [
            (
                f"{str(item.get('title', 'Training') or 'Training').strip()}: {str(item.get('text', '') or '').strip()}"
                if str(item.get("text", "") or "").strip()
                else str(item.get("title", "Training") or "Training").strip(),
                item.get("icon") or "school",
            )
            for item in tutorial_focus
        ]

    return {
        **_make_view(
            "Combat",
            encounter_title,
            eyebrow_icon="swords",
            title_icon="warning",
            subtitle=" • ".join(
                bit
                for bit in (
                    f"{ally_count} {ally_label}",
                    f"{companion_count} {companion_label}" if companion_count else "",
                    f"{foe_count} {foe_label}",
                )
                if bit
            ),
            actions=[
                build_combat_action_picker("Abilities", "bolt", combat_actions.get("abilities", []), "No usable combat abilities."),
                build_combat_action_picker("Items", "lunch_dining", combat_actions.get("items", []), "No combat consumables packed."),
                _action("Flee", "flee", "logout", tone="danger"),
            ],
            sections=[
                _section("Party", "groups", "entries", items=party_entries or [_entry("No active party members.", icon="person_off")], variant="party", span="compact" if party_count >= 3 else None),
                _section("Enemies", "warning", "entries", items=enemy_entries or [_entry("No enemies remain.", icon="task_alt")], variant="targets"),
            ],
            reactive=_reactive_view(encounter.obj, scene="combat", danger="combat"),
        ),
        "variant": "combat",
        "guidance": tutorial_guidance,
        "guidance_eyebrow": guidance_eyebrow,
        "guidance_title": guidance_title,
        "combat_actions": combat_actions,
        "reaction_window": reaction_window,
        "party_count": party_count,
        "enemy_count": foe_count,
        "sticky": True,
    }


def build_combat_victory_view(
    encounter,
    character,
    *,
    xp_total,
    reward_silver=0,
    reward_items=None,
    progress_messages=None,
    remote=False,
    party_size=1,
):
    """Return a browser-first victory screen for completed encounters."""

    reward_items = reward_items or []
    raw_progress_messages = [message for message in (progress_messages or []) if message]

    # 1. Extract XP and Silver from progress messages to consolidate them in Rewards
    quest_xp = 0
    quest_silver = 0
    filtered_messages = []
    
    import re
    xp_pattern = re.compile(r"gain\s+\|w?(\d+)\|?n?\s+xp", re.IGNORECASE)
    silver_pattern = re.compile(r"receive\s+\|w?(\d+)\|?n?\s+silver", re.IGNORECASE)

    for msg in raw_progress_messages:
        lowered = msg.lower()
        xp_match = xp_pattern.search(lowered)
        if xp_match:
            quest_xp += int(xp_match.group(1))
            continue
        silver_match = silver_pattern.search(lowered)
        if silver_match:
            quest_silver += int(silver_match.group(1))
            continue
        
        # Filter out purely informational tracking messages that are redundant on Victory
        if "tracked quest:" in lowered:
            continue
            
        filtered_messages.append(msg)

    # 2. Consolidate Quest Progress by Title
    # quest_states: { title: { 'latest_progress': str, 'completed': bool, 'new': bool, 'leads': [str] } }
    quest_states = {}
    other_messages = []
    
    for msg in filtered_messages:
        if ":" in msg:
            prefix, detail = [part.strip() for part in msg.split(":", 1)]
            prefix_lowered = prefix.lower()
        else:
            prefix, detail = "", msg
            prefix_lowered = ""

        if prefix_lowered == "quest updated":
            title = detail.split(" - ")[0] if " - " in detail else detail
            state = quest_states.setdefault(title, {"completed": False, "new": False, "leads": []})
            state["latest_progress"] = detail
        elif prefix_lowered == "quest complete":
            state = quest_states.setdefault(detail, {"completed": False, "new": False, "leads": []})
            state["completed"] = True
        elif prefix_lowered == "new quest":
            state = quest_states.setdefault(detail, {"completed": False, "new": False, "leads": []})
            state["new"] = True
        elif prefix_lowered == "next lead":
            # Associate with the most recent quest entry
            if quest_states:
                last_title = list(quest_states.keys())[-1]
                quest_states[last_title]["leads"].append(detail)
            else:
                other_messages.append(msg)
        else:
            other_messages.append(msg)

    # Reconstruct consolidated progress messages
    consolidated_entries = []
    for title, state in quest_states.items():
        lines = []
        if state["completed"]:
            meta = "Quest Complete"
            icon = "task_alt"
            display_title = title
        elif state["new"]:
            meta = "New Quest"
            icon = "flag"
            display_title = title
            lines.append("A new thread is ready to follow.")
        else:
            meta = "Quest Updated"
            icon = "assignment"
            display_title = state.get("latest_progress", title)
        
        lines.extend(state["leads"])
        consolidated_entries.append(_entry(display_title, meta=meta, icon=icon, lines=lines))

    level_up_messages = [message for message in other_messages if "you are now level" in message.lower()]
    companion_reward_messages = [message for message in other_messages if " bond +" in message.lower()]
    final_other_messages = [
        message for message in other_messages 
        if message not in level_up_messages and message not in companion_reward_messages
    ]
    
    is_capstone = (getattr(encounter.db, "encounter_title", "") or "").strip().lower() == "the hollow lantern"

    reward_pairs = [
        _pair("XP Earned", xp_total + quest_xp, "auto_awesome"),
        _pair("Silver", (reward_silver or 0) + quest_silver, "savings"),
    ]

    for message in companion_reward_messages:
        text = str(message or "").strip().rstrip(".")
        lowered = text.lower()
        split_index = lowered.find(" bond +")
        if split_index > 0:
            companion_name = text[:split_index].strip()
            bond_gain = text[split_index + 6 :].strip()
            reward_pairs.append(_pair(f"{companion_name} Bond", bond_gain, "pets"))
        else:
            reward_pairs.append(_pair("Companion Bond", text, "pets"))

    loot_items_list = []
    for template_id, quantity in reward_items:
        template = ITEM_TEMPLATES.get(template_id, {})
        item_name = template.get("name", template_id.replace("_", " ").title())
        kind = template.get("kind")
        icon = {
            "meal": "restaurant",
            "ingredient": "kitchen",
            "equipment": "checkroom",
        }.get(kind, "category")
        text = f"{item_name} x{quantity}" if quantity > 1 else item_name
        loot_items_list.append(_item(text, icon=icon))
    
    sections = [
        _section(
            "Rewards",
            "workspace_premium",
            "pairs",
            items=reward_pairs,
            variant="receipt",
        )
    ]
    
    if is_capstone:
        sections.append(
            _section(
                "Chapter Close",
                "emoji_events",
                "lines",
                lines=[
                    "The drowned weir is quiet.",
                    "The south light is finally dark.",
                    "Brambleford gets to take the win home.",
                ],
                variant="receipt",
            )
        )
    
    if loot_items_list:
        sections.append(_section("Recovered Loot", "inventory_2", "list", items=loot_items_list, variant="receipt"))
    
    if level_up_messages:
        sections.append(_section("LEVEL UP", "north", "lines", lines=level_up_messages, variant="receipt"))
    
    progress_items = consolidated_entries + [
        _entry(msg, meta="Progress", icon="task_alt") for msg in final_other_messages
    ]
    
    if progress_items:
        sections.append(
            _section(
                "Chapter Progress" if is_capstone else "Progress",
                "flag",
                "entries",
                items=progress_items,
                variant="receipt",
            )
        )

    return {
        **_make_view(
            "",
            "VICTORY",
            eyebrow_icon=None,
            title_icon="military_tech",
            sections=sections,
            actions=[_action("Continue", "look", None, tone="accent", no_icon=True)],
            reactive=_reactive_view(
                encounter.obj,
                scene="victory",
                danger="safe",
                boss=is_capstone,
            ),
        ),
        "variant": "combat-result",
    }


def build_sheet_view(character):
    """Return a browser-first main view for the character sheet."""

    race = RACES[character.db.brave_race]
    class_data = CLASSES[character.db.brave_class]
    level = character.db.brave_level
    primary = character.db.brave_primary_stats or {}
    derived = character.db.brave_derived_stats or {}
    resources = character.db.brave_resources or {}
    class_actions, passives, unknown_abilities = split_unlocked_abilities(character.db.brave_class, level)
    get_unlocked = getattr(character, "get_unlocked_abilities", None)
    if callable(get_unlocked):
        unlocked_names = list(get_unlocked())
        actions = [
            ability_name
            for ability_name in unlocked_names
            if ability_key(ability_name) in ABILITY_LIBRARY and ability_key(ability_name) in CHARACTER_CONTENT.implemented_ability_keys
        ]
        if not actions:
            actions = list(class_actions)
    else:
        actions = list(class_actions)
    next_level_xp = xp_needed_for_next_level(level)
    current_xp = character.db.brave_xp or 0
    xp_meter_max = next_level_xp or max(1, current_xp)
    xp_meter_value = min(current_xp, xp_meter_max)
    resonance_key = get_resonance_key(character)
    resonance_label = get_resonance_label(character)

    meal_buff = character.db.brave_meal_buff or {}
    blessing = get_active_blessing(character)

    combat_pairs = [
        _pair(get_stat_label("attack_power", character), derived.get("attack_power", 0), "swords"),
        _pair(get_stat_label("spell_power", character), derived.get("spell_power", 0), "auto_awesome"),
        _pair(get_stat_label("armor", character), derived.get("armor", 0), "shield"),
        _pair(get_stat_label("accuracy", character), derived.get("accuracy", 0), "near_me"),
        _pair(get_stat_label("dodge", character), derived.get("dodge", 0), "air"),
    ]
    if derived.get("precision", 0):
        combat_pairs.append(_pair(get_stat_label("precision", character), derived["precision"], "location_searching"))
    if derived.get("threat", 0):
        combat_pairs.append(_pair(get_stat_label("threat", character), derived["threat"], "warning"))

    status_entry = _entry(
        character.key,
        meta=f"{race['name']} {class_data['name']} · Level {level}",
        lines=[class_data["summary"]],
        icon=get_class_icon(character.db.brave_class, class_data),
        chips=[
            _chip(get_brave_gender_label(getattr(character.db, "brave_gender", None), default="Non-binary"), "person", "muted"),
            _chip(race["name"], get_race_icon(character.db.brave_race, race), "muted"),
            *(
                [_chip(resonance_label, "travel_explore", "accent")]
                if resonance_key != "fantasy"
                else []
            ),
        ],
        meters=[
            _meter(
                get_resource_label("hp", character),
                resources.get("hp", 0),
                derived.get("max_hp", 0),
                tone=_hp_meter_tone(resources.get("hp", 0), derived.get("max_hp", 0)),
            ),
            _meter(
                get_resource_label("mana", character),
                resources.get("mana", 0),
                derived.get("max_mana", 0),
                tone="mana",
            ),
            _meter(
                get_resource_label("stamina", character),
                resources.get("stamina", 0),
                derived.get("max_stamina", 0),
                tone="stamina",
            ),
            _meter(
                "XP",
                xp_meter_value,
                xp_meter_max,
                tone="xp",
                value="Level Cap" if not next_level_xp else f"{current_xp} / {next_level_xp}",
            ),
        ],
    )

    sections = [
        _section(
            "",
            "person",
            "entries",
            items=[status_entry],
            hide_label=True,
            span="wide",
            variant="status",
        ),
        _section(
            "Build",
            "bar_chart",
            "pairs",
            items=[
                _pair(get_stat_label("strength", character), primary.get("strength", 0), "construction"),
                _pair(get_stat_label("agility", character), primary.get("agility", 0), "air"),
                _pair(get_stat_label("intellect", character), primary.get("intellect", 0), "school"),
                _pair(get_stat_label("spirit", character), primary.get("spirit", 0), "auto_awesome"),
                _pair(get_stat_label("vitality", character), primary.get("vitality", 0), "favorite"),
            ],
            variant="stats",
        ),
        _section("Combat", "tune", "pairs", items=combat_pairs, variant="stats"),
        _section(
            "Class",
            "military_tech",
            "entries",
            items=[
                _entry(
                    feature["name"],
                    lines=[feature["summary"]],
                    icon=feature.get("icon", "star"),
                )
                for feature in get_class_features(character.db.brave_class)
            ]
            or [_entry("No class feature notes found.", icon="info")],
            variant="abilities",
        ),
        _section(
            "Abilities",
            "bolt",
            "list",
            items=[_build_sheet_ability_item(character, ability) for ability in actions]
            or [_item("No unlocked combat actions yet.", icon="info")],
            variant="abilities",
        ),
    ]

    if character.db.brave_class == "ranger":
        active_companion = dict(getattr(character, "get_active_companion", lambda: {})() or {})
        unlocked_companions = list(getattr(character, "get_unlocked_companions", lambda: [])() or [])
        sections.insert(
            4,
            _section(
                "Companion",
                "pets",
                "entries",
                items=[
                    _entry(
                        active_companion.get("name", "No active companion"),
                        meta="Active Bond",
                        lines=[
                            active_companion.get("summary", "No bonded companion is currently set."),
                            active_companion.get("bond_label", "Bond 1"),
                            (
                                "Bond XP capped"
                                if (active_companion.get("bond", {}) or {}).get("at_cap")
                                else f"{(active_companion.get('bond', {}) or {}).get('xp_to_next', 0)} XP to next bond"
                            ),
                            f"Unlocked companions: {len(unlocked_companions)}",
                        ],
                        icon=active_companion.get("icon", "pets"),
                    )
                ],
                variant="abilities",
            ),
        )
    elif character.db.brave_class == "paladin":
        active_oath = dict(getattr(character, "get_active_oath", lambda: {})() or {})
        unlocked_oaths = list(getattr(character, "get_unlocked_oaths", lambda: [])() or [])
        sections.insert(
            4,
            _section(
                "Sacred Oath",
                "military_tech",
                "entries",
                items=[
                    _entry(
                        active_oath.get("name", "No active oath"),
                        meta="Active Vigil",
                        lines=[
                            active_oath.get("summary", "No sacred oath is currently guiding your vigil."),
                            f"Sworn oaths: {len(unlocked_oaths)}",
                        ],
                        icon="military_tech",
                    )
                ],
                variant="abilities",
            ),
        )
    elif character.db.brave_class == "rogue":
        theft_log = list(getattr(character, "get_rogue_theft_log", lambda: [])() or [])
        latest = theft_log[-1] if theft_log else {}
        sections.insert(
            4,
            _section(
                "Illicit Access",
                "key",
                "entries",
                items=[
                    _entry(
                        "Worked Angles",
                        meta="Rogue-exclusive theft ledger",
                        lines=[
                            f"Worked marks: {len(theft_log)}",
                            f"Latest lift: {latest['target']}" if latest.get("target") else "No theft angles worked yet.",
                        ],
                        icon="key",
                    )
                ],
                variant="abilities",
            ),
        )
    elif character.db.brave_class == "druid":
        unlocked_form_names = [
            ability_name
            for ability_name in actions
            if ability_key(ability_name) in {"wolfform", "bearform", "crowform", "serpentform"}
        ]
        form_items = []
        for ability_name in unlocked_form_names:
            form = get_druid_form(ability_key(ability_name).replace("form", ""))
            form_items.append(
                _entry(
                    form.get("name", ability_name),
                    meta="Unlocked Form",
                    lines=[form.get("summary", ABILITY_LIBRARY.get(ability_key(ability_name), {}).get("summary", ""))],
                    icon="forest",
                )
            )
        sections.insert(
            4,
            _section(
                "Primal Forms",
                "forest",
                "entries",
                items=form_items or [_entry("No primal forms unlocked.", icon="info")],
                variant="abilities",
            ),
        )

    passive_items = [
        _build_sheet_passive_item(
            character,
            race["perk"],
            icon_name="star_outline",
            summary_line=race.get("perk_summary") or race["summary"],
            bonus_map=race.get("perk_bonuses", {}),
        )
    ]
    passive_items.extend(
        _build_sheet_passive_item(
            character,
            ability,
            icon_name="passive",
            bonus_map=PASSIVE_ABILITY_BONUSES.get(ability_key(ability), {}).get("bonuses", {}),
        )
        for ability in passives
    )

    if passive_items:
        sections.append(
            _section(
                "Traits",
                "auto_awesome",
                "list",
                items=passive_items,
                variant="abilities",
            )
        )

    effect_entries = []
    if meal_buff:
        meal_lines = []
        meal_bonus_text = _format_context_bonus_summary(character.get_active_meal_bonuses(), character)
        if meal_bonus_text:
            meal_lines.append("Bonuses: " + meal_bonus_text)
        effect_entries.append(
            _entry(
                meal_buff.get("name", "Meal Buff"),
                meta="Meal Buff",
                icon="restaurant",
                lines=meal_lines or ["A prepared meal is currently strengthening you."],
                chips=[_chip("Cozy", "night_shelter", "good")] if meal_buff.get("cozy") else [],
            )
        )

    if blessing:
        blessing_lines = [blessing.get("duration", "Until your next encounter ends.")]
        blessing_bonus_text = _format_context_bonus_summary(blessing.get("bonuses", {}), character)
        if blessing_bonus_text:
            blessing_lines.append("Bonuses: " + blessing_bonus_text)
        if (blessing.get("rite") or {}).get("name"):
            blessing_lines.append("Rite: " + blessing["rite"]["name"])
        effect_entries.append(
            _entry(
                blessing.get("name", "Blessing"),
                meta="Blessing",
                icon="wb_sunny",
                lines=blessing_lines,
            )
        )

    if resonance_key != "fantasy":
        effect_entries.append(
            _entry(
                resonance_label,
                meta="Resonance",
                icon="travel_explore",
                lines=[
                    "This world renames your abilities and resource labels, but your core build remains the same.",
                ],
            )
        )

    if unknown_abilities:
        effect_entries.append(
            _entry(
                "Progression Notes",
                meta="Unclassified",
                icon="info",
                lines=[", ".join(unknown_abilities)],
            )
        )

    if effect_entries:
        sections.append(
            _section(
                "Effects",
                "wb_sunny",
                "entries",
                items=effect_entries,
                span="wide",
                variant="effects",
            )
        )

    return {
        **_make_view(
            "",
            "Character Sheet",
            eyebrow_icon=None,
            title_icon="person",
            subtitle="",
            chips=[],
            sections=sections,
            back=True,
            reactive=_reactive_from_character(character, scene="character"),
        ),
        "variant": "sheet",
    }


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
        picker=_picker(title, subtitle=subtitle, body=body),
        tooltip=tooltip,
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
