"""Browser-only companion panel helpers for the Brave webclient."""

import time
from collections.abc import Mapping

from evennia.utils.ansi import strip_ansi
from world.ability_icons import get_ability_icon_name, get_passive_icon_name
from world.combat_atb import render_atb_state
from world.character_icons import get_class_icon, get_race_icon
from world.enemy_icons import get_enemy_icon_name
from world.commerce import get_reserved_entries, get_sellable_entries, get_shop_bonus
from world.content import get_content_registry
from world.forging import get_forge_entries
from world.navigation import format_route_hint, sort_exits
from world.party import get_follow_target, get_party_leader, get_party_members
from world.questing import get_active_quests, get_completed_quests, get_tracked_quest
from world.resonance import get_resource_label, get_resonance_label, get_stat_label
from world.tutorial import TUTORIAL_STEPS, ensure_tutorial_state

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
ITEM_CONTENT = CONTENT.items
QUEST_CONTENT = CONTENT.quests
SYSTEMS_CONTENT = CONTENT.systems

CLASSES = CHARACTER_CONTENT.classes
RACES = CHARACTER_CONTENT.races
ABILITY_LIBRARY = CHARACTER_CONTENT.ability_library
ability_key = CHARACTER_CONTENT.ability_key
xp_needed_for_next_level = CHARACTER_CONTENT.xp_needed_for_next_level

EQUIPMENT_SLOTS = ITEM_CONTENT.equipment_slots
ITEM_TEMPLATES = ITEM_CONTENT.item_templates
get_item_category = ITEM_CONTENT.get_item_category

QUESTS = QUEST_CONTENT.quests
STARTING_QUESTS = QUEST_CONTENT.starting_quests
group_quest_keys_by_region = QUEST_CONTENT.group_quest_keys_by_region
PORTALS = SYSTEMS_CONTENT.portals
PORTAL_STATUS_LABELS = SYSTEMS_CONTENT.portal_status_labels


WEB_PROTOCOLS = {"websocket", "ajax/comet", "webclient"}

GEAR_PANEL_ICONS = {
    "main_hand": "swords",
    "off_hand": "shield",
    "head": "face",
    "chest": "security",
    "hands": "back_hand",
    "legs": "accessibility_new",
    "feet": "hiking",
    "ring": "diamond",
    "trinket": "auto_awesome",
    "snack": "lunch_dining",
}

CHARGEN_STEP_META = {
    "menunode_welcome": {
        "title": "Overview",
        "title_icon": "person_add",
        "guidance": [
            ("review your draft and open slots", "overview"),
            ("pick a race, class, and name", "checklist"),
        ],
    },
    "menunode_choose_race": {
        "title": "Choose a Race",
        "title_icon": "diversity_3",
        "guidance": [
            ("pick the ancestry that fits your character", "forest"),
            ("race sets your starting perk", "star"),
        ],
    },
    "menunode_choose_class": {
        "title": "Choose a Class",
        "title_icon": "swords",
        "guidance": [
            ("pick a playable class for this slice", "target"),
            ("class sets your starter role and kit", "shield"),
        ],
    },
    "menunode_choose_name": {
        "title": "Choose a Name",
        "title_icon": "badge",
        "guidance": [
            ("enter a unique name for this finished build", "edit_note"),
            ("letters, spaces, apostrophes, and hyphens only", "rule"),
        ],
    },
    "menunode_confirm": {
        "title": "Confirm Character",
        "title_icon": "task_alt",
        "guidance": [
            ("review your build choices", "fact_check"),
            ("create the character when it looks right", "play_arrow"),
        ],
    },
}


def _is_web_session(session):
    protocol = (getattr(session, "protocol_key", "") or "").lower()
    return protocol in WEB_PROTOCOLS


def _plain_notice_text(text):
    return strip_ansi(str(text or "")).replace("||", "|").strip()


def _get_available_sessions(target):
    sessions = getattr(target, "sessions", None)
    if not sessions:
        return []
    if hasattr(sessions, "get"):
        return list(sessions.get())
    if hasattr(sessions, "all"):
        return list(sessions.all())
    return []


def _get_non_web_sessions(target):
    return [candidate for candidate in _get_available_sessions(target) if not _is_web_session(candidate)]


def _get_web_sessions(target):
    return [candidate for candidate in _get_available_sessions(target) if _is_web_session(candidate)]


def send_webclient_event(target, session=None, **payload):
    """Send an OOB event to webclient sessions only."""

    if session is not None:
        if _is_web_session(session) and hasattr(target, "msg"):
            if target is session or not hasattr(target, "sessions"):
                target.msg(**payload)
            else:
                target.msg(session=session, **payload)
        return

    sessions = getattr(target, "sessions", None)
    if not sessions:
        return

    if hasattr(sessions, "get"):
        available = list(sessions.get())
    elif hasattr(sessions, "all"):
        available = list(sessions.all())
    else:
        available = []

    web_sessions = [candidate for candidate in available if _is_web_session(candidate)]
    if web_sessions and hasattr(target, "msg"):
        target.msg(session=web_sessions, **payload)


def send_browser_notice_event(
    target,
    message,
    *,
    title="Notice",
    tone="muted",
    icon=None,
    duration_ms=None,
    sticky=False,
):
    """Send a browser notice to web sessions and plain text to non-web sessions."""

    plain_message = _plain_notice_text(message)
    lines = [line for line in plain_message.splitlines() if line.strip()]
    if lines:
        payload = {
            "title": title or "Notice",
            "tone": tone or "muted",
            "lines": lines,
        }
        if icon:
            payload["icon"] = icon
        if duration_ms is not None:
            payload["duration_ms"] = max(0, int(duration_ms))
        if sticky:
            payload["sticky"] = True
        web_sessions = _get_web_sessions(target)
        if web_sessions and hasattr(target, "msg"):
            target.msg(session=web_sessions, brave_notice=payload)

    available = _get_available_sessions(target)
    if not available:
        if hasattr(target, "msg"):
            target.msg(message)
        return

    non_web_sessions = _get_non_web_sessions(target)
    if non_web_sessions and hasattr(target, "msg"):
        target.msg(message, session=non_web_sessions)


def send_text_to_non_web_sessions(target, text):
    """Deliver plain text only to non-web sessions attached to a target."""

    if not text:
        return

    available = _get_available_sessions(target)
    if not available:
        if hasattr(target, "msg"):
            target.msg(text)
        return

    non_web_sessions = _get_non_web_sessions(target)
    if non_web_sessions and hasattr(target, "msg"):
        target.msg(text, session=non_web_sessions)


def send_room_activity_event(target, text, *, cls="out", category=None):
    """Send exploration activity to web sessions and plain room text elsewhere."""

    plain_text = _plain_notice_text(text)
    if plain_text:
        web_sessions = _get_web_sessions(target)
        if web_sessions and hasattr(target, "msg"):
            payload = {"text": plain_text, "cls": cls or "out"}
            if category:
                payload["category"] = category
            target.msg(session=web_sessions, brave_room_activity=payload)

    non_web_sessions = _get_non_web_sessions(target)
    if non_web_sessions and hasattr(target, "msg"):
        target.msg(text, session=non_web_sessions)


def broadcast_room_activity(room, text, *, exclude=None, cls="out", category=None):
    """Broadcast room activity without leaking raw text into the web scene pane."""

    if not room or not text:
        return

    excluded = set(exclude or [])
    for obj in getattr(room, "contents", []) or []:
        if obj in excluded or not hasattr(obj, "msg") or not hasattr(obj, "sessions"):
            continue
        send_room_activity_event(obj, text, cls=cls, category=category)


def broadcast_room_text_non_web(room, text, *, exclude=None):
    """Broadcast plain room text only to non-web sessions."""

    if not room or not text:
        return

    excluded = set(exclude or [])
    contents = list(getattr(room, "contents", []) or [])
    if not contents and hasattr(room, "msg_contents"):
        kwargs = {"exclude": list(excluded)} if excluded else {}
        room.msg_contents(text, **kwargs)
        return

    for obj in contents:
        if obj in excluded or not hasattr(obj, "msg"):
            continue
        send_text_to_non_web_sessions(obj, text)


def _chip(label, icon, tone=None):
    return {"label": label, "icon": icon, "tone": tone}


def _meter(current, maximum, tone="accent"):
    current_value = max(0, int(current or 0))
    maximum_value = max(1, int(maximum or 0))
    percent = max(0, min(100, int(round((current_value / maximum_value) * 100))))
    return {"value": f"{current_value}/{maximum_value}", "percent": percent, "tone": tone}


def _item(text, icon=None, badge=None, meta=None, meter=None):
    item = {"text": text, "icon": icon, "badge": badge}
    if meta:
        item["meta"] = meta
    if meter:
        item["meter"] = meter
    return item


def _section(label, icon, items):
    return {"label": label, "icon": icon, "items": items}


def _make_panel(eyebrow, title, *, eyebrow_icon, title_icon, chips=None, sections=None):
    return {
        "eyebrow": eyebrow,
        "eyebrow_icon": eyebrow_icon,
        "title": title,
        "title_icon": title_icon,
        "chips": chips or [],
        "sections": sections or [],
    }


def _get_journal_mode(character):
    mode = getattr(getattr(character, "db", None), "brave_journal_tab", "active")
    return mode if mode in {"active", "completed"} else "active"


def _short_direction(exit_obj):
    direction = getattr(exit_obj.db, "brave_direction", exit_obj.key)
    token = (direction or "").strip().lower()
    mapping = {
        "north": "N",
        "east": "E",
        "south": "S",
        "west": "W",
        "up": "U",
        "down": "D",
    }
    if token in mapping:
        return mapping[token]
    return token.upper()[:3] if token else "?"


def build_account_panel(account):
    """Build the browser-side companion panel for the OOC title screen."""

    characters = list(account.characters.all())
    max_slots = account.get_character_slots()
    available_slots = account.get_available_character_slots()
    slot_text = "unlimited" if max_slots is None else str(max_slots)
    open_text = "unlimited" if available_slots is None else str(available_slots)

    chips = [
        _chip(f"{len(characters)} / {slot_text} slots", "groups", "accent"),
        _chip(f"{open_text} open", "add_circle", "good"),
    ]
    if account.db.brave_chargen:
        chips.append(_chip("Draft saved", "edit_note", "warn"))

    command_items = [
        _item("play <number or name>", icon="play_arrow"),
        _item("create", icon="person_add"),
        _item("delete <number or name>", icon="delete"),
        _item("theme [name]", icon="palette"),
    ]

    if characters:
        character_items = []
        for index, character in enumerate(characters, start=1):
            character.ensure_brave_character()
            race_name = RACES[character.db.brave_race]["name"]
            class_name = CLASSES[character.db.brave_class]["name"]
            character_items.append(
                _item(
                    f"{character.key} · {race_name} {class_name} · Lv {character.db.brave_level}",
                    icon="person",
                    badge=str(index),
                )
            )
    else:
        character_items = [_item("No characters yet", icon="person_off")]

    sections = [
        _section("Actions", "menu", command_items),
        _section("Characters", "groups", character_items[:6]),
    ]

    if account.db._last_puppet and account.db._last_puppet in characters:
        sections.append(
            _section(
                "Last Played",
                "history",
                [_item(account.db._last_puppet.key, icon="sports_esports")],
            )
        )

    return _make_panel(
        "Account Menu",
        account.key,
        eyebrow_icon="badge",
        title_icon="sports_esports",
        chips=chips,
        sections=sections,
    )


def build_chargen_panel(account, state):
    """Build the browser-side companion panel for chargen."""

    step_key = state.get("step") or "menunode_welcome"
    step_meta = CHARGEN_STEP_META.get(step_key, CHARGEN_STEP_META["menunode_welcome"])
    slots_left = account.get_available_character_slots()
    slot_text = "unlimited" if slots_left is None else str(slots_left)

    name_value = state.get("name") or "Not set"
    race_value = RACES.get(state.get("race"), {}).get("name", "Not set")
    class_value = CLASSES.get(state.get("class"), {}).get("name", "Not set")

    chips = [_chip(f"{slot_text} open", "add_circle", "accent")]
    if state.get("race"):
        chips.append(_chip(race_value, get_race_icon(state.get("race"), RACES.get(state.get("race"))), "muted"))
    if state.get("class"):
        chips.append(_chip(class_value, get_class_icon(state.get("class"), CLASSES.get(state.get("class"))), "muted"))

    progress_items = [
        _item(f"Name · {name_value}", icon="check_circle" if state.get("name") else "radio_button_unchecked"),
        _item(f"Race · {race_value}", icon="check_circle" if state.get("race") else "radio_button_unchecked"),
        _item(f"Class · {class_value}", icon="check_circle" if state.get("class") else "radio_button_unchecked"),
    ]
    if state.get("name") and state.get("race") and state.get("class"):
        progress_items.append(_item("Ready to create", icon="task_alt"))

    guidance_items = [_item(text, icon=icon_name) for text, icon_name in step_meta["guidance"]]

    return _make_panel(
        "Character Creation",
        step_meta["title"],
        eyebrow_icon="person_add",
        title_icon=step_meta["title_icon"],
        chips=chips,
        sections=[
            _section("Progress", "checklist", progress_items),
            _section("Guidance", "flag", guidance_items),
        ],
    )


def build_build_panel(character):
    """Build the browser-side companion panel for build planning."""

    race_name = RACES[character.db.brave_race]["name"]
    class_name = CLASSES[character.db.brave_class]["name"]
    change_text = "Open" if character.can_customize_build() else "Locked"

    return _make_panel(
        "Build Planner",
        character.key,
        eyebrow_icon="tune",
        title_icon="badge",
        chips=[
            _chip(race_name, get_race_icon(character.db.brave_race, RACES.get(character.db.brave_race)), "muted"),
            _chip(class_name, get_class_icon(character.db.brave_class, CLASSES.get(character.db.brave_class)), "muted"),
            _chip(change_text, "lock_open" if character.can_customize_build() else "lock", "accent"),
        ],
        sections=[
            _section(
                "Next",
                "flag",
                [
                    _item("race <name>", icon="forest"),
                    _item("class <name>", icon="swords"),
                    _item("gear", icon="shield"),
                ],
            )
        ],
    )


def build_sheet_panel(character):
    """Build the browser-side companion panel for the character sheet."""

    race = RACES[character.db.brave_race]["name"]
    class_name = CLASSES[character.db.brave_class]["name"]
    level = character.db.brave_level
    derived = character.db.brave_derived_stats or {}
    resources = character.db.brave_resources or {}
    next_level_xp = xp_needed_for_next_level(level)
    xp_text = f"{character.db.brave_xp}/{next_level_xp}" if next_level_xp else f"{character.db.brave_xp}"
    abilities = character.get_unlocked_abilities()[:4]

    resource_items = [
        _item(
            f"{get_resource_label('hp', character)} {resources.get('hp', 0)}/{derived.get('max_hp', 0)}",
            icon="favorite",
        ),
        _item(
            f"{get_resource_label('mana', character)} {resources.get('mana', 0)}/{derived.get('max_mana', 0)}",
            icon="auto_awesome",
        ),
        _item(
            f"{get_resource_label('stamina', character)} {resources.get('stamina', 0)}/{derived.get('max_stamina', 0)}",
            icon="directions_run",
        ),
    ]

    derived_items = [
        _item(f"{get_stat_label('attack_power', character)} {derived.get('attack_power', 0)}", icon="swords"),
        _item(f"{get_stat_label('armor', character)} {derived.get('armor', 0)}", icon="shield"),
        _item(f"{get_stat_label('dodge', character)} {derived.get('dodge', 0)}", icon="air"),
    ]

    sections = [
        _section("Resources", "monitor_heart", resource_items),
        _section("Combat", "tune", derived_items),
    ]
    if abilities:
        sections.append(
            _section(
                "Abilities",
                "bolt",
                [
                    _item(
                        ability,
                        icon=(
                            get_ability_icon_name(key)
                            if key in ABILITY_LIBRARY
                            else get_passive_icon_name(key)
                        ),
                    )
                    for ability in abilities
                    for key in [ability_key(ability)]
                ],
            )
        )

    meal_buff = character.db.brave_meal_buff or {}
    chips = [
        _chip(f"{race} {class_name}", "badge", "muted"),
        _chip(f"Level {level}", "star", "accent"),
        _chip(f"XP {xp_text}", "timeline", "muted"),
    ]
    if meal_buff:
        chips.append(_chip(meal_buff.get("name", "Meal Buff"), "restaurant", "good"))
    if get_resonance_label(character) != "Fantasy Resonance":
        chips.append(_chip(get_resonance_label(character), "tune", "accent"))

    return _make_panel(
        "Character Sheet",
        character.key,
        eyebrow_icon="assignment_ind",
        title_icon="person",
        chips=chips,
        sections=sections,
    )


def build_gear_panel(character):
    """Build the browser-side companion panel for equipped gear."""

    equipment = character.db.brave_equipment or {}
    slot_items = []
    for slot in EQUIPMENT_SLOTS:
        label = slot.replace("_", " ").title()
        template_id = equipment.get(slot)
        item_name = ITEM_TEMPLATES.get(template_id, {}).get("name", template_id) if template_id else "Empty"
        slot_items.append(_item(f"{label} · {item_name}", icon=GEAR_PANEL_ICONS.get(slot, "shield")))

    return _make_panel(
        "",
        "Equipment",
        eyebrow_icon=None,
        title_icon="shield",
        chips=[],
        sections=[_section("Slots", "shield", slot_items)],
    )


def build_pack_panel(character):
    """Build the browser-side companion panel for the pack screen."""

    inventory = list(character.db.brave_inventory or [])
    inventory.sort(key=lambda entry: ITEM_TEMPLATES.get(entry["template"], {}).get("name", entry["template"]))
    total_pieces = sum(entry.get("quantity", 0) for entry in inventory)
    grouped = {
        "consumable": [],
        "ingredient": [],
        "loot": [],
        "equipment": [],
    }

    for entry in inventory:
        item = ITEM_TEMPLATES.get(entry["template"], {})
        kind = get_item_category(item)
        if item.get("kind") == "equipment":
            icon_name = GEAR_PANEL_ICONS.get(item.get("slot"), "shield")
        elif item.get("kind") == "meal":
            icon_name = "lunch_dining"
        elif kind == "consumable":
            icon_name = "restaurant"
        elif kind == "ingredient":
            icon_name = "kitchen"
        elif kind == "loot":
            icon_name = "category"
        else:
            icon_name = "backpack"
        panel_item = _item(
            item.get("name", entry["template"]),
            icon=icon_name,
            badge=str(entry.get("quantity", 1)) if entry.get("quantity", 1) > 1 else None,
            meta=item.get("slot", "").replace("_", " ").title() if item.get("kind") == "equipment" else None,
        )
        if kind in grouped:
            grouped[kind].append(panel_item)
        else:
            grouped["loot"].append(panel_item)

    sections = [
        _section(
            "On Hand",
            "backpack",
            [
                _item(f"{character.db.brave_silver or 0} silver", icon="savings"),
                _item(f"{len(inventory)} item types", icon="category"),
                _item(f"{total_pieces} pieces", icon="layers"),
            ],
        )
    ]
    if grouped["consumable"]:
        sections.append(_section("Consumables", "restaurant", grouped["consumable"][:4]))
    if grouped["ingredient"]:
        sections.append(_section("Ingredients", "kitchen", grouped["ingredient"][:4]))
    if grouped["loot"]:
        sections.append(_section("Loot And Materials", "category", grouped["loot"][:4]))
    if grouped["equipment"]:
        sections.append(_section("Spare Gear", "shield", grouped["equipment"][:4]))
    if len(sections) == 1:
        sections.append(_section("Contents", "backpack", [_item("Pack is empty", icon="backpack")]))

    return _make_panel(
        "",
        "Pack",
        eyebrow_icon=None,
        title_icon="backpack",
        chips=[],
        sections=sections,
    )


def build_shop_panel(character):
    """Build the browser-side companion panel for Outfitters."""

    sellables = get_sellable_entries(character)
    reserved = get_reserved_entries(character)
    bonus = get_shop_bonus(character)
    items = [
        _item(
            f"{entry['name']} · {entry['total_price']} silver",
            icon="sell",
            badge=str(entry["sellable"]),
        )
        for entry in sellables[:5]
    ] or [_item("Nothing sellable right now", icon="inventory_2")]

    sections = [_section("Sellable", "storefront", items)]
    if reserved:
        sections.append(
            _section(
                "Held For Quests",
                "assignment",
                [_item(entry["name"], icon="lock", badge=str(entry["reserved"])) for entry in reserved[:4]],
            )
        )

    if bonus:
        favor_label = f"+{bonus.get('bonus_pct', 0)}% x{bonus.get('sales_left', 0)}"
    else:
        favor_label = "No favor"

    chips = [
        _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
        _chip(favor_label, "sell", "good" if bonus else "muted"),
    ]

    return _make_panel(
        "Town Service",
        "Brambleford Outfitters",
        eyebrow_icon="storefront",
        title_icon="sell",
        chips=chips,
        sections=sections,
    )


def build_forge_panel(character):
    """Build the browser-side companion panel for forge orders."""

    entries = get_forge_entries(character)
    ready_count = sum(1 for entry in entries if entry["ready"])
    items = []
    for entry in entries[:5]:
        icon_name = "construction" if entry["ready"] else "schedule"
        status = "ready" if entry["ready"] else "not ready"
        items.append(
            _item(
                f"{entry['source_name']} → {entry['result_name']} · {status}",
                icon=icon_name,
            )
        )
    if not items:
        items = [_item("No current rework options", icon="construction")]

    return _make_panel(
        "Town Service",
        "Ironroot Forge",
        eyebrow_icon="construction",
        title_icon="build",
        chips=[
            _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
            _chip(f"{ready_count} ready", "task_alt", "good" if ready_count else "muted"),
        ],
        sections=[_section("Orders", "construction", items)],
    )


def build_portals_panel():
    """Build the browser-side companion panel for the current portal list."""

    chips = [_chip(f"{len(PORTALS)} gates", "travel_explore", "accent")]
    items = []
    for portal in PORTALS.values():
        items.append(
            _item(
                f"{portal['name']} · {PORTAL_STATUS_LABELS.get(portal['status'], portal['status'].title())}",
                icon="public",
            )
        )

    return _make_panel(
        "Portal Network",
        "Nexus Gates",
        eyebrow_icon="travel_explore",
        title_icon="public",
        chips=chips,
        sections=[_section("Current Gates", "travel_explore", items[:6])],
    )


def build_travel_panel(character):
    """Build the browser-side companion panel for route browsing."""

    room = character.location
    exits = sort_exits(list(room.exits)) if room else []
    exit_items = [
        _item(
            getattr(exit_obj.destination, "key", exit_obj.key),
            badge=_short_direction(exit_obj),
        )
        for exit_obj in exits[:6]
    ] or [_item("No routes from here", icon="block")]

    return _make_panel(
        "Travel",
        room.key if room else "Unknown",
        eyebrow_icon="explore",
        title_icon="route",
        chips=[_chip(f"{len(exits)} exits", "route", "accent")],
        sections=[_section("Routes", "map", exit_items)],
    )


def build_map_panel(character, mode="map"):
    """Build the browser-side companion panel for map views."""

    room = character.location
    title = "Regional Map" if mode == "map" else "Local Minimap"
    chips = []
    if room:
        chips.append(_chip(room.key, "location_on", "muted"))
        if getattr(room.db, "brave_zone", None):
            chips.append(_chip(room.db.brave_zone, "public", "accent"))

    return _make_panel(
        "Navigation",
        title,
        eyebrow_icon="explore",
        title_icon="map",
        chips=chips,
        sections=[
            _section(
                "Context",
                "flag",
                [
                    _item("n e s w u d to move", icon="near_me"),
                    _item("travel for named fallback", icon="alt_route"),
                ],
            )
        ],
    )


def build_cook_panel(character):
    """Build the browser-side companion panel for the cooking view."""

    meal_buff = character.db.brave_meal_buff or {}
    chips = []
    if meal_buff:
        chips.append(_chip(meal_buff.get("name", "Meal Buff"), "restaurant", "good"))

    return _make_panel(
        "Town Activity",
        "Hearth Recipes",
        eyebrow_icon="restaurant",
        title_icon="local_fire_department",
        chips=chips,
        sections=[
            _section(
                "Actions",
                "menu",
                [
                    _item("cook <recipe>", icon="restaurant"),
                    _item("eat <meal>", icon="lunch_dining"),
                ],
            )
        ],
    )


def build_fishing_panel(character):
    """Build the browser-side companion panel for the fishing view."""

    from world.activities import get_selected_fishing_lure, get_selected_fishing_rod

    rod = get_selected_fishing_rod(character)
    lure = get_selected_fishing_lure(character)
    chips = []
    if rod:
        chips.append(_chip(rod.get("name", "Rod"), "phishing", "accent"))
    if lure:
        chips.append(_chip(lure.get("name", "Lure"), "tune", "muted"))

    return _make_panel(
        "Town Activity",
        "Tackle Roll",
        eyebrow_icon="phishing",
        title_icon="waves",
        chips=chips,
        sections=[
            _section(
                "Actions",
                "menu",
                [
                    _item("fish cast", icon="phishing"),
                    _item("fish borrow kit", icon="inventory_2"),
                    _item("fish log", icon="menu_book"),
                    _item("fish rod <rod>", icon="straighten"),
                    _item("fish lure <lure>", icon="tune"),
                    _item("reel", icon="hook"),
                ],
            )
        ],
    )


def build_tinker_panel(character):
    """Build the browser-side companion panel for the tinkering view."""

    chips = []
    if getattr(character, "db", None):
        chips.append(_chip(f"{character.db.brave_silver or 0} silver", "payments", "muted"))

    return _make_panel(
        "Town Service",
        "Workbench Ledger",
        eyebrow_icon="build",
        title_icon="handyman",
        chips=chips,
        sections=[
            _section(
                "Actions",
                "menu",
                [
                    _item("tinker <design>", icon="build"),
                    _item("pack", icon="inventory_2"),
                ],
            )
        ],
    )


def build_party_panel(character, mode="status"):
    """Build the browser-side companion panel for party views."""

    members = get_party_members(character)
    leader = get_party_leader(character)
    follow_target = get_follow_target(character)

    chips = []
    if members:
        role_text = "Leader" if leader and leader.id == character.id else "Member"
        chips.append(_chip(role_text, "groups", "accent"))
        chips.append(_chip(f"{len(members)} in party", "group", "muted"))
    else:
        chips.append(_chip("Solo", "person", "muted"))
    if follow_target:
        chips.append(_chip(f"Following {follow_target.key}", "directions_walk", "good"))

    sections = []
    if mode == "routes":
        route_items = []
        for member in members:
            if member.id == character.id:
                continue
            location = member.location.key if member.location else "Nowhere"
            route = format_route_hint(character.location, member.location) if character.location else "route unavailable"
            route_items.append(_item(f"{member.key} · {location} · {route}", icon="route"))
        sections.append(_section("Routes", "map", route_items or [_item("No other party members", icon="person_off")]))
    else:
        member_items = []
        for member in members:
            role = "leader" if leader and member.id == leader.id else "member"
            location = member.location.key if member.location else "Nowhere"
            member_items.append(_item(f"{member.key} · {role} · {location}", icon="person"))
        sections.append(_section("Members", "groups", member_items or [_item("Not currently in a party", icon="person_off")]))

    sections.append(
        _section(
            "Actions",
            "menu",
            [
                _item("party invite <name>", icon="person_add"),
                _item("party follow <name>", icon="directions_walk"),
                _item("party where", icon="location_searching"),
            ],
        )
    )

    title = "Party Routes" if mode == "routes" else "Party"
    return _make_panel(
        "Multiplayer",
        title,
        eyebrow_icon="groups",
        title_icon="group",
        chips=chips,
        sections=sections,
    )


def build_quests_panel(character):
    """Build the browser-side companion panel for the quest journal."""

    journal_mode = _get_journal_mode(character)
    active_keys = get_active_quests(character)
    completed_keys = get_completed_quests(character)
    quest_log = character.db.brave_quests or {}
    tracked_key = get_tracked_quest(character)
    tutorial_state = ensure_tutorial_state(character)

    view_items = [
        _item("quests active", icon="assignment", badge="ON" if journal_mode == "active" else None),
        _item("quests completed", icon="task_alt", badge="ON" if journal_mode == "completed" else None),
    ]
    sections = [_section("View", "menu", view_items)]

    if journal_mode == "active" and tracked_key:
        tracked_definition = QUESTS[tracked_key]
        tracked_state = quest_log.get(tracked_key, {})
        remaining = [
            objective
            for objective in tracked_state.get("objectives", [])
            if not objective.get("completed")
        ]
        tracked_lines = [tracked_definition["title"]]
        if remaining:
            objective = remaining[0]
            suffix = ""
            required = objective.get("required", 1)
            if required > 1:
                suffix = f" ({objective.get('progress', 0)}/{required})"
            tracked_lines.append(f"Next: {objective['description']}{suffix}")
        sections.append(_section("Tracked", "flag", [_item(" · ".join(tracked_lines), icon="check_box_outline_blank")]))

    if journal_mode == "active" and tutorial_state.get("status") == "active":
        step_key = tutorial_state.get("step") or "first_steps"
        step = TUTORIAL_STEPS.get(step_key)
        if step:
            sections.append(
                _section(
                    "Tutorial",
                    "school",
                    [_item(f"{step['title']} · {step['summary']}", icon="flag")],
                ),
            )

    region_source = active_keys if journal_mode == "active" else completed_keys
    region_items = []
    for region, region_keys in group_quest_keys_by_region(region_source):
        label = "quest" if len(region_keys) == 1 else "quests"
        region_items.append(_item(f"{region} · {len(region_keys)} {label}", icon="explore"))
    if not region_items:
        region_items = [_item("No quests in this view.", icon="info")]
    sections.append(_section("Regions", "explore", region_items))

    if journal_mode == "active" and not active_keys and tutorial_state.get("status") != "active":
        sections.append(
            _section(
                "Status",
                "info",
                [_item("No active quests right now.", icon="task_alt")],
            )
        )
    if journal_mode == "completed" and not completed_keys:
        sections.append(
            _section(
                "Status",
                "info",
                [_item("No completed quests yet.", icon="task_alt")],
            )
        )

    return _make_panel(
        "",
        "Journal",
        eyebrow_icon=None,
        title_icon="menu_book",
        sections=sections,
    )


def build_combat_panel(encounter):
    """Build the browser-side companion panel for combat snapshots."""

    enemies = encounter.get_active_enemies()
    participants = encounter.get_active_participants()
    ally_count = len(participants)
    foe_count = len(enemies)
    ally_label = "ally" if ally_count == 1 else "allies"
    foe_label = "foe" if foe_count == 1 else "foes"
    imminent_count = 0
    opening_count = 0

    def hp_tone(current_hp, max_hp):
        ratio = (current_hp / max_hp) if max_hp else 0
        if ratio <= 0.25:
            return "danger"
        if ratio <= 0.5:
            return "warn"
        return "good"

    render_now_ms = int(round(time.time() * 1000))
    render_tick_ms = max(1, int(round(float(getattr(encounter, "interval", 1) or 1) * 1000)))

    def participant_name(participant):
        return str(participant.get("key") if isinstance(participant, Mapping) else participant.key)

    def participant_icon(participant):
        return str(participant.get("icon", "pets") if isinstance(participant, Mapping) else "person")

    def actor_atb_state(*, participant=None, enemy=None):
        getter = getattr(encounter, "_get_actor_atb_state", None)
        if not callable(getter):
            return {}
        try:
            if participant is not None:
                if isinstance(participant, Mapping):
                    return render_atb_state(getter(companion=participant) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
                return render_atb_state(getter(character=participant) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
            if enemy is not None:
                return render_atb_state(getter(enemy=enemy) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
        except Exception:
            return {}
        return {}

    def atb_badge(state):
        phase = (state or {}).get("phase")
        if phase == "ready":
            return "READY"
        if phase == "winding":
            return f"W{int((state or {}).get('ticks_remaining', 0) or 0)}"
        if phase == "recovering":
            return f"R{int((state or {}).get('ticks_remaining', 0) or 0)}"
        if phase == "cooldown":
            return f"CD{int((state or {}).get('ticks_remaining', 0) or 0)}"
        gauge = int((state or {}).get("gauge", 0) or 0)
        ready = max(1, int((state or {}).get("ready_gauge", 400) or 400))
        return f"ATB {int(round((gauge / ready) * 100))}%"

    sections = [
        _section(
            "Party",
            "groups",
            [
                _item(
                    participant_name(participant),
                    icon=participant_icon(participant),
                    badge=atb_badge(actor_atb_state(participant=participant)),
                    meta=(
                        "ready"
                        if (actor_atb_state(participant=participant).get("phase") == "ready")
                        else None
                    ),
                )
                for participant in participants[:4]
            ]
            or [_item("No active party members", icon="person_off")],
        ),
        _section(
            "Enemies",
            "swords",
            [
                _item(
                    enemy["key"],
                    icon=str(enemy.get("icon") or get_enemy_icon_name(enemy.get("template_key"), None)),
                    badge=atb_badge(actor_atb_state(enemy=enemy)),
                    meta=(
                        dict(actor_atb_state(enemy=enemy).get("current_action") or {}).get("label")
                        if actor_atb_state(enemy=enemy).get("phase") == "winding"
                        else ("recovering" if actor_atb_state(enemy=enemy).get("phase") in {"recovering", "cooldown"} else None)
                    ),
                    meter=_meter(enemy["hp"], enemy["max_hp"], hp_tone(enemy["hp"], enemy["max_hp"])),
                )
                for enemy in enemies[:5]
            ]
            or [_item("No enemies remain", icon="task_alt")],
        ),
    ]

    for participant in participants:
        phase = (actor_atb_state(participant=participant) or {}).get("phase")
        if phase == "ready":
            imminent_count += 1
    for enemy in enemies:
        phase = (actor_atb_state(enemy=enemy) or {}).get("phase")
        if phase in {"winding", "ready"}:
            imminent_count += 1
        elif phase in {"recovering", "cooldown"}:
            opening_count += 1

    return _make_panel(
        "",
        "COMBAT",
        eyebrow_icon=None,
        title_icon="warning",
        chips=[
            _chip(f"{ally_count} {ally_label}", "groups", "muted"),
            _chip(f"{foe_count} {foe_label}", "warning", "danger" if enemies else "good"),
            _chip(f"{imminent_count} hot", "priority_high", "danger" if imminent_count else "muted"),
            _chip(f"{opening_count} open", "schedule", "good" if opening_count else "muted"),
        ],
        sections=sections,
    )


def build_talk_panel(target):
    """Build a browser-side companion panel for NPC dialogue."""

    return _make_panel(
        "",
        target.key,
        eyebrow_icon=None,
        title_icon="person",
        sections=[_section("Actions", "flag", [_item(f"talk {target.key}", icon="forum")])],
    )


def build_read_panel(target):
    """Build a browser-side companion panel for readable text."""

    return _make_panel(
        "Readable",
        target.key,
        eyebrow_icon="menu_book",
        title_icon="article",
        chips=[_chip("Readable", "menu_book", "muted")],
        sections=[_section("Actions", "flag", [_item(f"read {target.key}", icon="menu_book")])],
    )
