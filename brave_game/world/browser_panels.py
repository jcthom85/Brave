"""Browser-only companion panel helpers for the Brave webclient."""

from world.commerce import get_reserved_entries, get_sellable_entries, get_shop_bonus
from world.data.character_options import CLASSES, RACES, xp_needed_for_next_level
from world.data.items import EQUIPMENT_SLOTS, ITEM_TEMPLATES
from world.data.portals import PORTALS, PORTAL_STATUS_LABELS
from world.data.quests import QUESTS, STARTING_QUESTS, group_quest_keys_by_region
from world.forging import get_forge_entries
from world.navigation import format_route_hint, sort_exits
from world.party import get_follow_target, get_party_leader, get_party_members
from world.questing import get_active_quests, get_completed_quests, get_tracked_quest
from world.resonance import get_resource_label, get_resonance_label, get_stat_label
from world.tutorial import TUTORIAL_STEPS, ensure_tutorial_state


WEB_PROTOCOLS = {"websocket", "ajax/comet", "webclient"}

CHARGEN_STEP_META = {
    "menunode_welcome": {
        "title": "Overview",
        "title_icon": "person_add",
        "guidance": [
            ("review your draft and open slots", "overview"),
            ("pick a name, race, and class", "checklist"),
        ],
    },
    "menunode_choose_name": {
        "title": "Choose a Name",
        "title_icon": "badge",
        "guidance": [
            ("enter a unique name", "edit_note"),
            ("letters, spaces, apostrophes, and hyphens only", "rule"),
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
        chips.append(_chip(race_value, "diversity_3", "muted"))
    if state.get("class"):
        chips.append(_chip(class_value, "swords", "muted"))

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
            _chip(race_name, "diversity_3", "muted"),
            _chip(class_name, "swords", "muted"),
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
            _section("Abilities", "bolt", [_item(ability, icon="chevron_right") for ability in abilities])
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
    filled = 0
    equipped_items = []
    open_items = []
    for slot in EQUIPMENT_SLOTS:
        label = slot.replace("_", " ").title()
        template_id = equipment.get(slot)
        if template_id:
            filled += 1
            item_name = ITEM_TEMPLATES.get(template_id, {}).get("name", template_id)
            equipped_items.append(_item(f"{label} · {item_name}", icon="checkroom"))
        else:
            open_items.append(_item(label, icon="inventory_2"))

    sections = [
        _section("Equipped", "checkroom", equipped_items[:6] or [_item("Nothing equipped yet", icon="inventory_2")]),
    ]
    if open_items:
        sections.append(_section("Open", "add_box", open_items[:6]))

    return _make_panel(
        "Equipment",
        "Equipped Gear",
        eyebrow_icon="shield",
        title_icon="inventory_2",
        chips=[_chip(f"{filled}/{len(EQUIPMENT_SLOTS)} slots", "checkroom", "accent")],
        sections=sections,
    )


def build_pack_panel(character):
    """Build the browser-side companion panel for inventory."""

    inventory = list(character.db.brave_inventory or [])
    inventory.sort(key=lambda entry: ITEM_TEMPLATES.get(entry["template"], {}).get("name", entry["template"]))
    total_pieces = sum(entry.get("quantity", 0) for entry in inventory)
    meals = []
    ingredients = []
    loot = []
    equipment_items = []

    for entry in inventory:
        item = ITEM_TEMPLATES.get(entry["template"], {})
        panel_item = _item(
            item.get("name", entry["template"]),
            icon="inventory_2",
            badge=str(entry.get("quantity", 1)),
        )
        kind = item.get("kind")
        if kind == "meal":
            meals.append(panel_item)
        elif kind == "ingredient":
            ingredients.append(panel_item)
        elif kind == "equipment":
            equipment_items.append(panel_item)
        else:
            loot.append(panel_item)

    sections = []
    if meals:
        sections.append(_section("Meals", "restaurant", meals[:4]))
    if ingredients:
        sections.append(_section("Ingredients", "kitchen", ingredients[:4]))
    if loot:
        sections.append(_section("Loot", "category", loot[:4]))
    if equipment_items:
        sections.append(_section("Spare Gear", "checkroom", equipment_items[:4]))
    if not sections:
        sections = [_section("Carried", "backpack", [_item("Pack is empty", icon="backpack")])]

    return _make_panel(
        "Inventory",
        "Pack",
        eyebrow_icon="backpack",
        title_icon="inventory_2",
        chips=[
            _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
            _chip(f"{len(inventory)} item types", "category", "muted"),
            _chip(f"{total_pieces} pieces", "stack", "muted"),
        ],
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
        sections.append(_section("Tracked", "flag", [_item(" · ".join(tracked_lines), icon="flag")]))

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

    def hp_tone(current_hp, max_hp):
        ratio = (current_hp / max_hp) if max_hp else 0
        if ratio <= 0.25:
            return "danger"
        if ratio <= 0.5:
            return "warn"
        return "good"

    sections = [
        _section(
            "Party",
            "groups",
            [_item(participant.key, icon="person") for participant in participants[:4]]
            or [_item("No active party members", icon="person_off")],
        ),
        _section(
            "Enemies",
            "swords",
            [
                _item(
                    enemy["key"],
                    icon="warning",
                    badge=enemy["id"].upper(),
                    meter=_meter(enemy["hp"], enemy["max_hp"], hp_tone(enemy["hp"], enemy["max_hp"])),
                )
                for enemy in enemies[:5]
            ]
            or [_item("No enemies remain", icon="task_alt")],
        ),
    ]

    return _make_panel(
        "",
        "COMBAT",
        eyebrow_icon=None,
        title_icon="warning",
        chips=[
            _chip(f"{ally_count} {ally_label}", "groups", "muted"),
            _chip(f"{foe_count} {foe_label}", "warning", "danger" if enemies else "good"),
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
