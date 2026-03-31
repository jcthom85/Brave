"""Browser-only main-pane view payloads for Brave's richer command screens."""

from world.arcade import format_arcade_score, get_personal_best, get_reward_definition, has_arcade_reward
from world.data.arcade import ARCADE_GAMES
from world.data.activities import COOKING_RECIPES, format_ingredient_list
from world.commerce import format_shop_bonus, get_reserved_entries, get_sellable_entries, get_shop_bonus
from world.data.character_options import CLASSES, RACES, VERTICAL_SLICE_CLASSES, xp_needed_for_next_level
from world.data.items import EQUIPMENT_SLOTS, ITEM_TEMPLATES
from world.data.portals import PORTALS, PORTAL_STATUS_LABELS
from world.data.quests import QUESTS, STARTING_QUESTS
from world.data.themes import THEMES, THEME_BY_KEY, normalize_theme_key
from world.data.world_tones import get_world_tone_key
from world.chapel import get_active_blessing
from world.forging import get_forge_entries
from world.navigation import (
    build_map_snapshot,
    format_exit_summary,
    format_route_hint,
    get_exit_direction,
    get_exit_label,
    sort_exits,
)
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
from world.tutorial import TUTORIAL_STEPS, ensure_tutorial_state


PACK_KIND_ORDER = ("meal", "ingredient", "loot", "equipment")
PACK_KIND_LABELS = {
    "meal": ("Meals", "restaurant"),
    "ingredient": ("Ingredients", "kitchen"),
    "loot": ("Loot And Materials", "category"),
    "equipment": ("Spare Gear", "checkroom"),
}

ROOM_ENTITY_KIND_ICONS = {
    "npc": "forum",
    "readable": "menu_book",
    "arcade": "sports_esports",
    "object": "category",
}

ROOM_ENTITY_ID_ICONS = {
    "kitchen_hearth": "soup_kitchen",
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


def _action(label, command, icon, *, tone=None, confirm=None, icon_only=False, aria_label=None, picker=None):
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
    return action


def _item(text, *, icon=None, badge=None, command=None, prefill=None, confirm=None, actions=None, picker=None):
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
    return item


def _pair(label, value, icon=None):
    return {"label": label, "value": str(value), "icon": icon}


def _meter(label, current, maximum, *, tone="accent"):
    current_value = max(0, int(current or 0))
    maximum_value = max(1, int(maximum or 0))
    percent = max(0, min(100, int(round((current_value / maximum_value) * 100))))
    return {
        "label": label,
        "value": f"{current_value} / {maximum_value}",
        "percent": percent,
        "tone": tone,
    }


def _entry(
    title,
    *,
    meta=None,
    lines=None,
    summary=None,
    icon=None,
    badge=None,
    command=None,
    prefill=None,
    confirm=None,
    actions=None,
    picker=None,
    chips=None,
    meters=None,
):
    entry = {
        "title": title,
        "meta": meta,
        "lines": [line for line in (lines or []) if line],
        "summary": summary or "",
        "icon": icon,
        "badge": badge,
    }
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
    return entry


def _picker_option(label, *, command=None, prefill=None, icon=None, meta=None, tone=None):
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
    return option


def _picker(title, *, subtitle=None, options=None):
    picker = {
        "title": title,
        "options": [option for option in (options or []) if option],
    }
    if subtitle:
        picker["subtitle"] = subtitle
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
):
    view_actions = list(actions or [])
    if back and not any(action.get("command") == "look" for action in view_actions):
        view_actions.append(_action("Back", "look", "arrow_back", tone="muted"))
    return {
        "eyebrow": eyebrow,
        "eyebrow_icon": eyebrow_icon,
        "title": title,
        "title_icon": title_icon,
        "wordmark": wordmark or "",
        "subtitle": subtitle or "",
        "chips": [chip for chip in (chips or []) if chip],
        "sections": sections or [],
        "actions": view_actions,
        "reactive": reactive or {},
    }


def _reactive_view(source=None, *, scene="system", danger=None, boss=False):
    """Build semantic browser-reactivity metadata for a view."""

    reactive = {
        "scene": scene,
        "world_tone": get_world_tone_key(source),
    }
    if danger:
        reactive["danger"] = danger
    if boss:
        reactive["boss"] = True
    return reactive


def _reactive_from_character(character, *, scene="system", danger=None, boss=False):
    """Convenience wrapper using the character's current room."""

    return _reactive_view(getattr(character, "location", None), scene=scene, danger=danger, boss=boss)


def _pre_section(label, icon, text, *, span=None, tone=None):
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
    "menunode_welcome",
    "menunode_choose_name",
    "menunode_choose_race",
    "menunode_choose_class",
    "menunode_confirm",
)

CHARGEN_STEP_META = {
    "menunode_welcome": {
        "eyebrow": "Character Creation",
        "title": "Build Your Adventurer",
        "title_icon": "person_add",
        "subtitle": "Name, race, class, then review.",
        "step_index": 0,
    },
    "menunode_choose_name": {
        "eyebrow": "Character Creation",
        "title": "Choose A Name",
        "title_icon": "badge",
        "subtitle": "Type a name and press Enter.",
        "step_index": 1,
    },
    "menunode_choose_race": {
        "eyebrow": "Character Creation",
        "title": "Choose A Race",
        "title_icon": "diversity_3",
        "subtitle": "Choose a race.",
        "step_index": 2,
    },
    "menunode_choose_class": {
        "eyebrow": "Character Creation",
        "title": "Choose A Class",
        "title_icon": "swords",
        "subtitle": "Choose a class.",
        "step_index": 3,
    },
    "menunode_confirm": {
        "eyebrow": "Character Creation",
        "title": "Review And Create",
        "title_icon": "task_alt",
        "subtitle": "Review, then create.",
        "step_index": 4,
    },
}


def build_chargen_view(account, state, *, error=None):
    """Return a browser-native main view for the character creator."""

    from world.chargen import get_next_chargen_step

    step_key = state.get("step") or "menunode_welcome"
    step_meta = CHARGEN_STEP_META.get(step_key, CHARGEN_STEP_META["menunode_welcome"])
    slots_left = account.get_available_character_slots()
    slot_text = "Unlimited" if slots_left is None else str(slots_left)
    race_name = RACES.get(state.get("race"), {}).get("name", "Not set")
    class_name = CLASSES.get(state.get("class"), {}).get("name", "Not set")

    chips = [
        _chip(f"Step {step_meta['step_index'] + 1} / 5", "steps", "accent"),
        _chip(f"{slot_text} open", "add_circle", "muted"),
    ]
    if state.get("race"):
        chips.append(_chip(race_name, "diversity_3", "muted"))
    if state.get("class"):
        chips.append(_chip(class_name, "swords", "muted"))

    sections = [
        _section(
            "Draft",
            "checklist",
            "pairs",
            items=[
                _pair("Name", state.get("name") or "Not set", "badge"),
                _pair("Race", race_name, "diversity_3"),
                _pair("Class", class_name, "swords"),
            ],
            span="wide",
        )
    ]

    actions = []

    if step_key == "menunode_welcome":
        next_step = get_next_chargen_step(state)
        next_step_entry = {
            "menunode_choose_name": _entry(
                "Choose Name",
                meta="Step 1",
                icon="badge",
                command="continue",
            ),
            "menunode_choose_race": _entry(
                "Choose Race",
                meta="Step 2",
                icon="diversity_3",
                command="continue",
            ),
            "menunode_choose_class": _entry(
                "Choose Class",
                meta="Step 3",
                icon="swords",
                command="continue",
            ),
            "menunode_confirm": _entry(
                "Review Character",
                meta="Step 4",
                icon="task_alt",
                command="continue",
                chips=[_chip("Ready", "check_circle", "good")],
            ),
        }[next_step]
        sections.append(_section("Next Step", "format_list_numbered", "entries", items=[next_step_entry]))
    elif step_key == "menunode_choose_name":
        if error:
            sections.append(
                _section(
                    "Name Issue",
                    "warning",
                    "lines",
                    lines=[error.replace("|r", "").replace("|n", "")],
                    span="wide",
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
            race_entries.append(
                _entry(
                    race_data["name"],
                    meta="Selected" if state.get("race") == race_key else "Available",
                    lines=[race_data["summary"], f"Perk: {race_data['perk']}"],
                    icon="forest",
                    command=race_key,
                    chips=[_chip("Current", "check_circle", "good")] if state.get("race") == race_key else [],
                )
            )
        sections.append(_section("Races", "forest", "entries", items=race_entries, span="wide"))
    elif step_key == "menunode_choose_class":
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
        class_entries = []
        for class_key in VERTICAL_SLICE_CLASSES:
            class_data = CLASSES[class_key]
            class_entries.append(
                _entry(
                    class_data["name"],
                    meta=class_data["role"],
                    lines=[class_data["summary"]],
                    icon="swords",
                    command=class_key,
                    chips=[_chip("Current", "check_circle", "good")] if state.get("class") == class_key else [],
                )
            )
        sections.append(_section("Classes", "swords", "entries", items=class_entries, span="wide"))
    elif step_key == "menunode_confirm":
        actions.extend(
            [
                _action("Create Character", "finish", "play_arrow", tone="good"),
                _action("Back", "back", "arrow_back", tone="muted"),
            ]
        )
        race_data = RACES.get(state.get("race"), {})
        class_data = CLASSES.get(state.get("class"), {})
        if error:
            sections.append(
                _section(
                    "Issue",
                    "warning",
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
                        race_data.get("name", "Race"),
                        meta="Race Perk",
                        lines=[race_data.get("perk", "No perk found.")],
                        icon="forest",
                    ),
                    _entry(
                        class_data.get("name", "Class"),
                        meta=class_data.get("role", "Role"),
                        lines=[class_data.get("summary", "No class summary found.")],
                        icon="swords",
                    ),
                ],
            )
        )
        sections.append(
            _section(
                "Ready",
                "play_arrow",
                "entries",
                items=[
                    _entry(
                        "Create Character",
                        meta="Final Step",
                        lines=["Create and return to your character list."],
                        icon="play_arrow",
                        command="finish",
                        chips=[_chip("Ready", "check_circle", "good")],
                    )
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
        text = f"{threat['key']} · {threat['temperament_label']} · {threat['threat_label']} threat"
        if threat.get("engaged"):
            text += " · Engaged"
        items.append(
            _item(
                text,
                icon="warning",
                command=threat.get("command"),
                actions=[_action("Attack", threat.get("command"), "swords", tone="danger")] if threat.get("command") else None,
            )
        )
    return items


def _format_room_entity_items(viewer, visible_entities, visible_chars):
    items = []
    viewer_party_id = getattr(getattr(viewer, "db", None), "brave_party_id", None)
    follow_target = get_follow_target(viewer) if viewer else None
    party_leader = get_party_leader(viewer) if viewer else None
    party_size = len(get_party_members(viewer)) if viewer else 0

    for obj in visible_chars or []:
        actions = []
        same_party = bool(viewer_party_id and viewer_party_id == getattr(obj.db, "brave_party_id", None))
        if same_party:
            if follow_target and follow_target.id == obj.id:
                actions.append(_action("Stay", "party stay", "do_not_disturb_on", tone="muted"))
            else:
                actions.append(_action("Follow", f"party follow {obj.key}", "directions_walk"))
            actions.append(_action("Where", "party where", "location_searching", tone="muted"))
            if party_leader and party_leader.id == viewer.id:
                actions.append(
                    _action(
                        "Kick",
                        f"party kick {obj.key}",
                        "person_remove",
                        tone="danger",
                        confirm=f"Remove {obj.key} from the party?",
                    )
                )
        elif not getattr(obj.db, "brave_party_id", None) and (not viewer_party_id or (party_leader and party_leader.id == viewer.id and party_size < 4)):
            actions.append(_action("Invite", f"party invite {obj.key}", "person_add"))
        items.append(
            _item(
                obj.key,
                icon="person",
                actions=actions,
            )
        )

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
        if kind == "npc":
            command = f"talk {obj.key}"
        elif kind == "readable":
            command = "cook" if entity_id == "kitchen_hearth" else f"read {obj.key}"
        elif kind == "arcade":
            command = f"arcade {obj.key}"
        items.append(
            _item(
                label,
                icon=ROOM_ENTITY_ID_ICONS.get(entity_id, ROOM_ENTITY_KIND_ICONS.get(kind, "category")),
                command=command,
            )
        )

    return items


def build_room_view(room, looker, *, visible_threats=None, visible_entities=None, visible_chars=None):
    """Return a browser-first room view for exploration and movement."""

    world_name = getattr(room.db, "brave_world", "Brave") or "Brave"
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
    sections = [
        _section(
            "Ways Forward",
            "route",
            "navpad",
            items=nav_items,
            span="medium",
            vertical_items=vertical_exits,
            extra_items=special_exits,
            variant="routes",
        )
    ]
    sections.append(
        _section(
            "Threats Here",
            "warning",
            "list",
            items=threat_items or [_item("No immediate threats.", icon="task_alt")],
            variant="threats",
        )
    )
    sections.append(
        _section(
            "Visible Here",
            "visibility",
            "list",
            items=visible_items or [_item("Nothing notable in view.", icon="visibility_off")],
            variant="entities",
        )
    )

    return {
        **_make_view(
            room.db.brave_zone or world_name,
            room.key,
            eyebrow_icon=None,
            title_icon="home_pin",
            subtitle=description,
            sections=sections,
            reactive=_reactive_view(
                room,
                scene="explore",
                danger="safe" if room.db.brave_safe else "danger",
            ),
        ),
        "layout": "explore",
        "mobile_pack": _build_mobile_pack_payload(looker),
        "variant": "room",
        "tone": "safe" if room.db.brave_safe else "danger",
    }


def build_map_view(room, character, *, mode="map"):
    """Return a browser-first large map view."""

    radius = None if mode == "map" else 2
    snapshot = build_map_snapshot(room, radius=radius, character=character)
    if not snapshot:
        return _make_view(
            "Navigation",
            "Map Unavailable",
            eyebrow_icon="explore",
            title_icon="map",
            subtitle="No map data is available for this area yet.",
            sections=[_section("Status", "info", "lines", lines=["No regional coordinates are configured for this room."])],
            back=True,
        )

    region_room = snapshot["room"]
    world_name = getattr(region_room.db, "brave_world", "Brave") or "Brave"
    chips = [
        _chip(region_room.db.brave_zone or snapshot["region"], "location_on", "accent"),
        _chip(region_room.key, "my_location", "muted"),
    ]
    if world_name != "Brave":
        chips.append(_chip(get_world_label(region_room), "public", "muted"))
        chips.append(_chip(get_resonance_label(region_room), "travel_explore", "accent"))

    legend_items = []
    for entry in snapshot["legend"]:
        text = entry["label"]
        if entry.get("suffix"):
            text += f" · {entry['suffix']}"
        legend_items.append({"text": text, "badge": entry["icon"]})

    detail_lines = []
    exit_summary = format_exit_summary(snapshot["exits"]) if snapshot["exits"] else "No visible exits."
    detail_lines.append(f"Visible exits: {exit_summary}")
    if mode == "map":
        detail_lines.append("This map shows the full connected regional layout from your current area.")
    else:
        detail_lines.append("This view is the local map around your current room.")

    sections = [
        _pre_section("Layout", "grid_view", snapshot["map_text"], span="mapwide", tone="map"),
        _section("Legend", "category", "list", items=legend_items),
        _section("Notes", "tips_and_updates", "lines", lines=detail_lines),
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

    return {
        **_make_view(
            "Navigation",
            "Map" if mode == "map" else "Local Map",
            eyebrow_icon="explore",
            title_icon="map",
            subtitle="A larger navigational chart for the current region, with legend and local route context.",
            chips=chips,
            sections=sections,
            back=True,
            reactive=_reactive_view(
                region_room,
                scene="map",
                danger="safe" if getattr(region_room.db, "brave_safe", False) else "danger",
            ),
        ),
        "variant": "map",
    }


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
    item_types = 0
    meals = 0
    ingredients = 0
    preview = []

    for entry in inventory:
        template_id = entry.get("template")
        if not template_id:
            continue
        item_types += 1
        quantity = max(0, int(entry.get("quantity", 0) or 0))
        template = ITEM_TEMPLATES.get(template_id, {})
        kind = template.get("kind")
        if kind == "meal":
            meals += quantity
        elif kind == "ingredient":
            ingredients += quantity
        if len(preview) < 4:
            item_name = template.get("name", template_id.replace("_", " ").title())
            preview.append({"label": item_name, "quantity": quantity})

    return {
        "silver": character.db.brave_silver or 0,
        "item_types": item_types,
        "meals": meals,
        "ingredients": ingredients,
        "preview": preview,
        "overflow": max(0, item_types - len(preview)),
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


def _character_status_label(character):
    return "In Play" if character.sessions.all() else "Ready"


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
                    "delete",
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
        status_parts = [_character_status_label(character)]
        if location_label := _character_location_label(character):
            status_parts.append(location_label)
        lines = [
            f"{race_name} {class_name} · Level {character.db.brave_level}",
            " · ".join(status_parts),
        ]
        entry_chips = []
        if last_played and character.id == last_played.id:
            entry_chips.append(_chip("Last Played", "history", "accent"))
        roster_entries.append(
            _entry(
                character.key,
                meta=f"Slot {index}",
                lines=lines,
                icon="person",
                badge=str(index),
                command=f"play {index}",
                chips=entry_chips,
                actions=[
                    _action(
                        "Delete",
                        f"delete {index} --force",
                        "delete",
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
            items=roster_entries or [_entry("No characters yet.", lines=["Use `create` to make your first adventurer."], icon="person_add")],
            hide_label=True,
        ),
    ]

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
            actions=[],
            reactive=_reactive_view(scene="account"),
        ),
        "variant": "account",
    }


def build_theme_view(current_theme_key=None):
    """Build the browser-native theme selection screen."""

    current_theme = THEME_BY_KEY.get(normalize_theme_key(current_theme_key))
    chips = []
    if current_theme:
        chips.append(_chip(current_theme["name"], current_theme["icon"], "accent"))
        chips.append(_chip(current_theme["font_name"], "text_fields", "muted"))

    entries = []
    default_theme_key = "hearth"
    for theme in THEMES:
        lines = [
            theme["summary"],
            f"Typeface: {theme['font_name']}",
            f"Reading size: {theme['font_scale']}",
            *theme.get("notes", []),
        ]
        actions = []
        meta = "Available"
        chips_for_entry = []
        if theme["key"] == default_theme_key:
            chips_for_entry.append(_chip("Default", "home", "accent"))
        if current_theme_key and theme["key"] == current_theme_key:
            meta = "Current theme"
            chips_for_entry.append(_chip("Current", "check_circle", "good"))
        chips_for_entry.append(_chip(theme["font_name"], "text_fields", "muted"))
        actions.append(_action("Use", f"theme {theme['key']}", "palette", tone="accent"))
        entries.append(
            _entry(
                theme["name"],
                meta=meta,
                summary=theme["summary"],
                lines=lines,
                icon=theme["icon"],
                command=f"theme {theme['key']}",
                actions=actions,
                chips=chips_for_entry,
            )
        )

    sections = [
        _section("Styles", "palette", "entries", items=entries),
        _section(
            "How Themes Work",
            "tune",
            "list",
            items=[
                _item("Themes choose the interface material language: panels, framing, texture, motion, and typography.", icon="style"),
                _item("The world still supplies live area hue, danger tone, combat tension, and reactive accents.", icon="public"),
                _item("Each theme bundles its own typeface and reading scale. There is no separate font picker now.", icon="text_fields"),
                _item("Brave Classic is the canonical default and the theme the game is designed around.", icon="home"),
            ],
        ),
    ]

    actions = [_action("Reset", "theme reset", "restart_alt", tone="muted")]

    return _make_view(
        "Theme",
        "Themes",
        eyebrow_icon="palette",
        title_icon="style",
        subtitle="Choose the browser presentation lens for Brave. Brave Classic is the intended default; the others are alternate ways to read the same world.",
        chips=chips,
        sections=sections,
        actions=actions,
        back=True,
        reactive=_reactive_view(scene="theme"),
    )


def build_prayer_view(character, *, blessing=None, applied=False):
    """Return a browser-first main view for the Chapel blessing."""

    blessing = blessing or get_active_blessing(character)
    blessing_name = blessing.get("name", "Dawn Bell Blessing")
    duration = blessing.get("duration", "Until your next encounter ends.")
    bonus_text = _format_context_bonus_summary(blessing.get("bonuses", {}), character)

    chips = [
        _chip(blessing_name, "wb_sunny", "accent"),
        _chip("One encounter", "schedule", "muted"),
    ]

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
        _section(
            "Chapel Notes",
            "church",
            "list",
            items=[
                _item("Brother Alden watches the west-side trouble and the barrow line.", icon="forum"),
                _item("Sister Maybelle tends the hurt and keeps the town practical about what bravery costs.", icon="forum"),
                _item("Return here before a harder run when you want the Dawn Bell at your back.", icon="flag"),
            ],
        ),
    ]

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
    flags = state.get("flags", {})
    lines = [step["summary"]]

    if step_key == "first_steps":
        lines.extend(
            [
                f"[{'x' if flags.get('talked_tamsin') else ' '}] Speak with Sergeant Tamsin Vale.",
                f"[{'x' if flags.get('visited_quartermaster_shed') else ' '}] Head east to Quartermaster Shed.",
                f"[{'x' if flags.get('returned_to_wayfarers_yard') else ' '}] Return to Wayfarer's Yard.",
            ]
        )
    elif step_key == "pack_before_walk":
        lines.extend(
            [
                f"[{'x' if flags.get('talked_nella') else ' '}] Speak with Quartermaster Nella Cobb.",
                f"[{'x' if flags.get('viewed_gear') else ' '}] Check your gear.",
                f"[{'x' if flags.get('viewed_pack') else ' '}] Open your pack.",
                f"[{'x' if flags.get('read_supply_board') else ' '}] Read the supply board.",
            ]
        )
    elif step_key == "stand_your_ground":
        lines.append(f"[{'x' if flags.get('talked_brask') else ' '}] Speak with Ringhand Brask.")
    elif step_key == "clear_the_pens":
        lines.append(f"[{'x' if flags.get('won_vermin_fight') else ' '}] Win one fight in the Vermin Pens.")
    elif step_key == "through_the_gate":
        lines.append(f"[{'x' if flags.get('talked_harl') else ' '}] Report to Captain Harl Rowan.")

    optional_done = flags.get("read_family_post_sign") or flags.get("talked_peep")
    lines.append(f"[{'x' if optional_done else ' '}] Optional: Visit Family Post for party basics.")
    return _entry(step["title"], meta="Tutorial", lines=lines, icon="school")


def _format_objective_progress(objective):
    text = objective.get("description", "Objective")
    required = objective.get("required", 1)
    if required > 1:
        text += f" ({objective.get('progress', 0)}/{required})"
    return text


def _build_tracked_quest_entry(character, tracked_key, nearby_npcs):
    if not tracked_key:
        return None

    state = (character.db.brave_quests or {}).get(tracked_key, {})
    if state.get("status") != "active":
        return None

    definition = QUESTS[tracked_key]
    remaining_objectives = [
        objective for objective in state.get("objectives", []) if not objective.get("completed")
    ]
    objective_lines = [f"[ ] {_format_objective_progress(objective)}" for objective in remaining_objectives[:4]]
    completed_count = len(state.get("objectives", [])) - len(remaining_objectives)
    total_count = max(1, len(state.get("objectives", [])))
    actions = [_action("Untrack", "quests untrack", "flag", tone="accent")]
    if definition["giver"] in nearby_npcs:
        actions.append(_action("Talk", f"talk {definition['giver']}", "forum", tone="muted"))

    return _entry(
        definition["title"],
        meta="Tracked Quest",
        lines=[definition["summary"], f"Given by: {definition['giver']}"] + objective_lines,
        icon="flag",
        actions=actions,
        chips=[_chip(f"{completed_count}/{total_count} steps", "checklist", "accent")],
    )


def _build_quest_entries(character, tracked_key=None):
    active = []
    completed = []
    nearby_npcs = _local_npc_keys(character)
    active_index = 0
    for quest_key in STARTING_QUESTS:
        state = (character.db.brave_quests or {}).get(quest_key)
        if not state or state.get("status") == "locked":
            continue

        definition = QUESTS[quest_key]
        remaining_objectives = [
            objective for objective in state.get("objectives", []) if not objective.get("completed")
        ]
        next_objective = remaining_objectives[0] if remaining_objectives else None
        next_step = _format_objective_progress(next_objective) if next_objective else definition["summary"]
        actions = []
        command = None

        if state.get("status") == "completed":
            completed.append(
                _item(
                    f"{definition['title']} · {definition['giver']}",
                    icon="task_alt",
                )
            )
        else:
            active_index += 1
            command = f"quests track {active_index}"
            if quest_key == tracked_key:
                command = "quests untrack"
                actions.append(_action("Untrack", "quests untrack", "flag", tone="accent"))
            else:
                actions.append(_action("Track", command, "flag", tone="accent"))

            if definition["giver"] in nearby_npcs:
                actions.append(_action("Talk", f"talk {definition['giver']}", "forum", tone="muted"))

            active.append(
                _item(
                    f"{definition['title']} · Next: {next_step}",
                    badge=str(active_index),
                    command=command,
                    actions=actions,
                )
            )
    return active, completed


def build_quests_view(character):
    """Return a browser-first main view for the quest journal."""

    tutorial_entry = _build_tutorial_entry(character)
    tracked_key = get_tracked_quest(character)
    nearby_npcs = _local_npc_keys(character)
    tracked_entry = _build_tracked_quest_entry(character, tracked_key, nearby_npcs)
    active_entries, completed_entries = _build_quest_entries(character, tracked_key=tracked_key)

    chips = [
        _chip(f"{len(active_entries)} active", "assignment", "accent"),
        _chip(f"{len(completed_entries)} completed", "task_alt", "muted"),
    ]
    if tracked_entry:
        chips.append(_chip("Tracking 1", "flag", "good"))

    focus_items = [entry for entry in (tracked_entry, tutorial_entry) if entry]
    if not focus_items:
        focus_items = [
            _entry(
                "No tracked quest",
                meta="Current Focus",
                lines=["Track an active quest to pin its objectives and quick actions here."],
                icon="flag",
            )
        ]

    sections = [
        _section(
            "Current Focus",
            "flag",
            "entries",
            items=focus_items,
            variant="focus",
        ),
        _section(
            "Active Quests",
            "assignment",
            "list",
            items=active_entries or [_item("No active quests right now.", icon="info")],
            variant="active",
        ),
        _section(
            "Completed Archive",
            "task_alt",
            "list",
            items=completed_entries or [_item("No completed quests yet.", icon="info")],
            variant="archive",
        ),
    ]

    return {
        **_make_view(
            "Adventure Log",
            "Journal",
            eyebrow_icon="assignment",
            title_icon="menu_book",
            subtitle="Track one quest in detail, scan the active roster, and keep finished work archived below.",
            chips=chips,
            sections=sections,
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

    chips = []
    if members:
        chips.append(_chip(f"{len(members)} members", "groups", "accent"))
    else:
        chips.append(_chip("Solo", "person", "muted"))
    if invites:
        chips.append(_chip(f"{len(invites)} invite{'s' if len(invites) != 1 else ''}", "mail", "warn"))

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

    return _make_view(
        "Family",
        "Party",
        eyebrow_icon="groups",
        title_icon="diversity_3",
        subtitle="Keep the family together and moving as one group.",
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="party"),
    )


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
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_cook_view(character, *, status_message=None, status_tone="muted"):
    """Return a browser-first main view for the hearth and meal loop."""

    inventory = _inventory_totals(character)
    ready_entries = []
    missing_entries = []
    meal_entries = []

    for recipe in COOKING_RECIPES.values():
        ingredient_text = format_ingredient_list(recipe["ingredients"], ITEM_TEMPLATES)
        missing = []
        for template_id, quantity in recipe["ingredients"].items():
            have = inventory.get(template_id, 0)
            if have < quantity:
                missing.append(f"{ITEM_TEMPLATES[template_id]['name']} {have}/{quantity}")

        lines = [ingredient_text, "Ready to cook" if not missing else "Missing: " + ", ".join(missing)]
        formatted = _entry(
            recipe["name"],
            lines=lines,
            summary=recipe["summary"],
            icon="restaurant" if not missing else "kitchen",
            command=f"cook {recipe['name']}" if not missing else None,
            actions=[_action("Cook", f"cook {recipe['name']}", "restaurant", tone="accent")] if not missing else [],
        )
        if missing:
            missing_entries.append(formatted)
        else:
            ready_entries.append(formatted)

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
            _section("Missing", "grocery", "entries", items=missing_entries or [_entry("No missing recipes right now.", icon="task_alt")]),
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


def build_talk_view(target, response):
    """Return a browser-first view for NPC dialogue."""

    paragraphs = [line.strip() for line in str(response or "").splitlines() if line.strip()]
    quoted_lines = [f"\u201c{line}\u201d" for line in paragraphs] if paragraphs else ["They have nothing to say right now."]
    return _make_view(
        "Conversation",
        target.key,
        eyebrow_icon="forum",
        title_icon="person",
        sections=[
            _section(
                "",
                "forum",
                "lines",
                lines=quoted_lines,
                variant="quote",
                hide_label=True,
            )
        ],
        back=True,
        reactive=_reactive_view(getattr(target, "location", None), scene="dialogue"),
    )


def build_read_view(target, response):
    """Return a browser-first view for readable world text."""

    paragraphs = [line.strip() for line in str(response or "").splitlines() if line.strip()]
    return _make_view(
        "",
        _display_name(target),
        eyebrow_icon=None,
        title_icon=None,
        sections=[
            _section(
                "",
                "menu_book",
                "lines",
                lines=paragraphs or ["There is nothing legible here right now."],
                hide_label=True,
            )
        ],
        back=True,
        reactive=_reactive_view(getattr(target, "location", None), scene="read"),
    )


def build_arcade_view(character, cabinet, *, focus_game=None):
    """Return a browser-first view for one local arcade cabinet."""

    available_games = [game_key for game_key in cabinet.get_available_games() if game_key in ARCADE_GAMES]
    selected_game = focus_game if focus_game in available_games else (available_games[0] if available_games else None)

    game_entries = []
    for game_key in available_games:
        definition = ARCADE_GAMES[game_key]
        reward = get_reward_definition(cabinet, game_key)
        prize_text = ""
        threshold = reward.get("threshold", 0)
        if threshold and reward.get("item_name"):
            if has_arcade_reward(character, cabinet, game_key):
                prize_text = f"Prize claimed: {reward['item_name']}."
            else:
                prize_text = (
                    f"Prize at {format_arcade_score(threshold)}: {reward['item_name']}. "
                    f"Your best: {format_arcade_score(get_personal_best(character, cabinet, game_key))}."
                )
        lines = [definition.get("summary", ""), definition.get("score_summary", ""), prize_text]
        game_entries.append(
            _entry(
                definition["name"],
                meta=f"{cabinet.get_game_price(game_key)} silver",
                lines=[line for line in lines if line],
                icon="sports_esports",
                command=f"arcade play {game_key}",
                actions=[
                    _action("Play", f"arcade play {game_key}", "play_arrow", tone="accent"),
                    _action("Scores", f"arcade scores {game_key}", "military_tech", tone="muted"),
                ],
            )
        )

    leaderboard_items = []
    if selected_game:
        for index, entry in enumerate(cabinet.get_leaderboard(selected_game), start=1):
            leaderboard_items.append(
                _item(
                    f"{index}. {entry.get('name', 'Unknown')} · {format_arcade_score(entry.get('score', 0))}",
                    icon="military_tech",
                )
            )
    if not leaderboard_items:
        leaderboard_items = [_item("Nobody has claimed this board yet.", icon="star_outline")]

    instruction_lines = []
    if selected_game:
        instruction_lines.extend(ARCADE_GAMES[selected_game].get("instructions", []))

    return {
        **_make_view(
            _display_name(cabinet),
            "ARCADE",
            eyebrow_icon="sports_esports",
            title_icon="sports_esports",
            chips=[_chip(f"{len(available_games)} game" + ("" if len(available_games) == 1 else "s"), "stadia_controller", "accent")],
            sections=[
                _section(
                    "Cabinet Lineup",
                    "sports_esports",
                    "entries",
                    items=game_entries or [_entry("This cabinet is dark right now.", icon="power_off")],
                    span="wide",
                ),
                _section(
                    "Local Scores",
                    "military_tech",
                    "list",
                    items=leaderboard_items,
                ),
                _section(
                    "How To Play",
                    "gamepad",
                    "lines",
                    lines=instruction_lines or ["No active program notes are posted for this cabinet yet."],
                ),
            ],
            back=True,
            reactive=_reactive_from_character(character, scene="arcade"),
        ),
        "variant": "arcade",
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

    def format_pending(label):
        if not label:
            return "Basic attack"
        return label[0].upper() + label[1:]

    def build_participant_status_chips(state):
        chips = []
        if state.get("guard", 0) > 0:
            chips.append(_chip("Guarding", "shield", "good"))
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
        return chips

    def build_enemy_status_chips(enemy):
        chips = []
        if enemy.get("marked_turns", 0) > 0:
            chips.append(_chip(f"Marked {enemy['marked_turns']}", "my_location", "accent"))
        if enemy.get("bound_turns", 0) > 0:
            chips.append(_chip(f"Bound {enemy['bound_turns']}", "block", "warn"))
        if enemy.get("hidden_turns", 0) > 0:
            chips.append(_chip(f"Hidden {enemy['hidden_turns']}", "visibility_off", "muted"))
        if enemy.get("shielded"):
            chips.append(_chip("Warded", "shield", "good"))
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
        return _meter(short_label, current_value, max_value, tone="accent")

    enemies = encounter.get_active_enemies()
    participants = encounter.get_active_participants()
    encounter_title = (getattr(encounter.db, "encounter_title", "") or "").strip() or "Combat"

    ordered_participants = sorted(
        participants,
        key=lambda participant: (0 if participant.id == character.id else 1, participant.key.lower()),
    )

    def build_ability_item(ability_name, ability):
        target_type = ability["target"]
        resource_key = ability["resource"]
        resource_name = get_resource_label(resource_key, character)
        resource_current = (character.db.brave_resources or {}).get(resource_key, 0)
        can_afford = resource_current >= ability["cost"]
        display_name = format_ability_display(ability_name, character)
        short_resource = resource_name[:3].upper()
        target_badge = {
            "self": "S",
            "enemy": "E",
            "ally": "A",
        }.get(target_type, "?")
        text = f"{display_name} · {ability['cost']} {short_resource}"
        command = None
        prefill = None
        picker = None

        if not can_afford:
            text += f" · NEED {ability['cost'] - resource_current}"
        elif target_type == "enemy":
            if not enemies:
                text += " · NO TARGET"
            elif len(enemies) == 1:
                command = f"use {ability_name} = {enemies[0]['id']}"
            else:
                picker = _picker(
                    f"{display_name} Target",
                    subtitle="Choose an enemy.",
                    options=[
                        _picker_option(
                            enemy["key"],
                            command=f"use {ability_name} = {enemy['id']}",
                            icon="warning",
                            meta=enemy["id"].upper(),
                            tone="danger",
                        )
                        for enemy in enemies
                    ],
                )
                text += " · TARGET"
        elif target_type == "ally":
            if not ordered_participants:
                text += " · NO TARGET"
            elif len(ordered_participants) == 1:
                command = f"use {ability_name}"
            else:
                picker = _picker(
                    f"{display_name} Target",
                    subtitle="Choose an ally.",
                    options=[
                        _picker_option(
                            participant.key,
                            command=f"use {ability_name}" if participant.id == character.id else f"use {ability_name} = {participant.key}",
                            icon="person",
                            meta="You" if participant.id == character.id else "Ally",
                            tone="accent" if participant.id == character.id else "good",
                        )
                        for participant in ordered_participants
                    ],
                )
                text += " · TARGET"
        else:
            command = f"use {ability_name}"

        return _item(
            text,
            badge=target_badge,
            command=command,
            prefill=prefill,
            picker=picker,
        )

    unlocked = []
    for ability_name in character.get_unlocked_abilities():
        ability_key = resolve_ability_query(character, ability_name)
        if isinstance(ability_key, list) or not ability_key:
            continue
        ability = ABILITY_LIBRARY.get(ability_key)
        if not ability:
            continue
        unlocked.append((ability_key, ability_name, ability))

    ability_items = []
    for _ability_key, ability_name, ability in unlocked:
        ability_items.append(build_ability_item(ability_name, ability))

    party_entries = []
    for participant in ordered_participants:
        participant.ensure_brave_character()
        resources = participant.db.brave_resources or {}
        derived = participant.db.brave_derived_stats or {}
        primary_resource = "mana" if participant.db.brave_class in {"cleric", "mage", "druid"} else "stamina"
        state = encounter._get_participant_state(participant)
        status_chips = build_participant_status_chips(state)
        pending_text = format_pending(encounter._describe_pending_action(participant))
        lines = []
        if pending_text != "Basic attack":
            lines.append(f"Queued: {pending_text}")

        party_entries.append(
            _entry(
                participant.key,
                meta="You" if participant.id == character.id else None,
                lines=lines,
                icon="person",
                chips=status_chips,
                meters=[
                    hp_meter(resources.get("hp", 0), derived.get("max_hp", 0)),
                    resource_meter(primary_resource, resources.get(primary_resource, 0), derived.get(f"max_{primary_resource}", 0)),
                ],
            )
        )

    enemy_entries = []
    for enemy in enemies:
        status_chips = build_enemy_status_chips(enemy)
        lines = ["Ready basic attack."]
        enemy_entries.append(
            _entry(
                enemy["key"],
                meta=f"Target {enemy['id'].upper()}",
                lines=lines,
                icon="warning",
                badge=enemy["id"].upper(),
                command=f"attack {enemy['id']}",
                actions=[_action("Attack", f"attack {enemy['id']}", "swords", tone="danger")],
                chips=status_chips,
                meters=[hp_meter(enemy["hp"], enemy["max_hp"])],
            )
        )

    return {
        **_make_view(
            "Combat",
            encounter_title,
            eyebrow_icon="swords",
            title_icon="warning",
            subtitle="",
            actions=[_action("Flee", "flee", "logout", tone="danger")],
            sections=[
                _section("Abilities", "bolt", "list", items=ability_items or [_item("No usable combat abilities.", icon="info")], span="wide", variant="abilities"),
                _section("Party", "groups", "entries", items=party_entries or [_entry("No active party members.", icon="person_off")], variant="party"),
                _section("Enemies", "warning", "entries", items=enemy_entries or [_entry("No enemies remain.", icon="task_alt")], variant="targets"),
            ],
            reactive=_reactive_view(encounter.obj, scene="combat", danger="combat"),
        ),
        "variant": "combat",
        "preserve_rail": True,
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
    progress_messages = [message for message in (progress_messages or []) if message]
    level_up_messages = [message for message in progress_messages if "you are now level" in message.lower()]
    other_progress_messages = [message for message in progress_messages if message not in level_up_messages]
    is_capstone = (getattr(encounter.db, "encounter_title", "") or "").strip().lower() == "the hollow lantern"

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
            items=[
                _pair("XP Earned", xp_total, "timeline"),
                _pair("Silver", reward_silver or 0, "savings"),
            ],
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
        sections.append(
            _section(
                "LEVEL UP",
                "north",
                "lines",
                lines=level_up_messages,
                variant="receipt",
            )
        )
    if other_progress_messages:
        sections.append(
            _section(
                "Chapter Progress" if is_capstone else "Progress",
                "trending_up",
                "lines",
                lines=other_progress_messages,
                variant="receipt",
            )
        )

    return {
        **_make_view(
            "",
            "VICTORY",
            eyebrow_icon=None,
            title_icon=None,
            sections=sections,
            actions=[_action("Continue", "look", "north_east", tone="accent")],
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
    primary = character.db.brave_primary_stats or {}
    derived = character.db.brave_derived_stats or {}
    resources = character.db.brave_resources or {}
    abilities = character.get_unlocked_abilities()
    next_level_xp = xp_needed_for_next_level(character.db.brave_level)
    xp_text = (
        f"{character.db.brave_xp}/{next_level_xp} XP"
        if next_level_xp
        else f"{character.db.brave_xp} XP (cap)"
    )

    chips = [
        _chip(f"{race['name']} {class_data['name']}", "badge", "muted"),
        _chip(f"Level {character.db.brave_level}", "star", "accent"),
        _chip(xp_text, "timeline", "muted"),
    ]
    if get_resonance_key(character) != "fantasy":
        chips.append(_chip(get_resonance_label(character), "travel_explore", "accent"))

    meal_buff = character.db.brave_meal_buff or {}
    if meal_buff:
        chips.append(_chip(meal_buff.get("name", "Meal Buff"), "restaurant", "good"))

    blessing = get_active_blessing(character)
    if blessing:
        chips.append(_chip(blessing.get("name", "Blessing"), "wb_sunny", "accent"))

    combat_pairs = [
        _pair(get_stat_label("attack_power", character), derived.get("attack_power", 0), "swords"),
        _pair(get_stat_label("spell_power", character), derived.get("spell_power", 0), "auto_awesome"),
        _pair(get_stat_label("armor", character), derived.get("armor", 0), "shield"),
        _pair(get_stat_label("accuracy", character), derived.get("accuracy", 0), "my_location"),
        _pair(get_stat_label("dodge", character), derived.get("dodge", 0), "air"),
    ]
    if derived.get("precision", 0):
        combat_pairs.append(_pair(get_stat_label("precision", character), derived["precision"], "target"))
    if derived.get("threat", 0):
        combat_pairs.append(_pair(get_stat_label("threat", character), derived["threat"], "campaign"))

    sections = [
        _section(
            "Overview",
            "assignment_ind",
            "pairs",
            items=[
                _pair("Race", race["name"], "diversity_3"),
                _pair("Class", class_data["name"], "swords"),
                _pair("Perk", race["perk"], "star"),
                _pair("Role", class_data["role"], "military_tech"),
                _pair("Silver", character.db.brave_silver or 0, "savings"),
                _pair("Resonance", get_resonance_label(character), "travel_explore"),
            ],
        ),
        _section(
            "Resources",
            "monitor_heart",
            "pairs",
            items=[
                _pair(
                    get_resource_label("hp", character),
                    f"{resources.get('hp', 0)} / {derived.get('max_hp', 0)}",
                    "favorite",
                ),
                _pair(
                    get_resource_label("mana", character),
                    f"{resources.get('mana', 0)} / {derived.get('max_mana', 0)}",
                    "auto_awesome",
                ),
                _pair(
                    get_resource_label("stamina", character),
                    f"{resources.get('stamina', 0)} / {derived.get('max_stamina', 0)}",
                    "directions_run",
                ),
            ],
        ),
        _section(
            "Primary Stats",
            "bar_chart",
            "pairs",
            items=[
                _pair(get_stat_label(stat, character), primary.get(stat, 0))
                for stat in ("strength", "agility", "intellect", "spirit", "vitality")
            ],
        ),
        _section("Combat", "tune", "pairs", items=combat_pairs),
        _section(
            "Abilities",
            "bolt",
            "list",
            items=[
                {"text": format_ability_display(ability, character), "icon": "chevron_right"}
                for ability in abilities
            ] or [{"text": "No unlocked abilities yet.", "icon": "info"}],
        ),
    ]

    if meal_buff:
        meal_lines = [meal_buff.get("name", "Meal Buff") + (" [Cozy]" if meal_buff.get("cozy") else "")]
        meal_bonus_text = _format_context_bonus_summary(character.get_active_meal_bonuses(), character)
        if meal_bonus_text:
            meal_lines.append("Bonuses: " + meal_bonus_text)
        sections.append(_section("Meal Buff", "restaurant", "lines", lines=meal_lines))

    if blessing:
        blessing_lines = [blessing.get("duration", "Until your next encounter ends.")]
        blessing_bonus_text = _format_context_bonus_summary(blessing.get("bonuses", {}), character)
        if blessing_bonus_text:
            blessing_lines.append("Bonuses: " + blessing_bonus_text)
        sections.append(_section("Blessing", "wb_sunny", "lines", lines=blessing_lines))

    if get_resonance_key(character) != "fantasy":
        sections.append(
            _section(
                "Resonance Note",
                "travel_explore",
                "lines",
                lines=[
                    "This world renames your abilities and resource labels, but your core build remains the same.",
                ],
            )
        )

    return _make_view(
        "Character Sheet",
        character.key,
        eyebrow_icon="assignment_ind",
        title_icon="person",
        subtitle=f"{race['name']} {class_data['name']} · Level {character.db.brave_level} · {class_data['summary']}",
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="character"),
    )


def build_gear_view(character):
    """Return a browser-first main view for equipped gear."""

    equipment = character.db.brave_equipment or {}
    entries = []
    open_slots = []

    for slot in EQUIPMENT_SLOTS:
        label = slot.replace("_", " ").title()
        template_id = equipment.get(slot)
        if not template_id:
            open_slots.append({"text": label, "icon": "inventory_2"})
            continue

        item = ITEM_TEMPLATES.get(template_id, {})
        bonus_text = _format_context_bonus_summary(item.get("bonuses", {}), character)
        lines = ["Bonuses: " + bonus_text] if bonus_text else []
        entries.append(
            _entry(
                item.get("name", template_id),
                meta=label,
                lines=lines,
                summary=item.get("summary"),
                icon="checkroom",
            )
        )

    total_bonus_text = _format_context_bonus_summary(_format_equipment_totals(character), character)
    sections = [
        _section(
            "Equipped",
            "checkroom",
            "entries",
            items=entries or [_entry("Nothing equipped yet.", icon="inventory_2")],
        )
    ]
    if open_slots:
        sections.append(_section("Open Slots", "add_box", "list", items=open_slots))
    if total_bonus_text:
        sections.append(_section("Total Bonus", "tune", "lines", lines=[total_bonus_text]))

    return _make_view(
        "Kit",
        "Gear",
        eyebrow_icon="shield",
        title_icon="inventory_2",
        subtitle="What you are wearing right now.",
        chips=[_chip(f"{len(entries)}/{len(EQUIPMENT_SLOTS)} slots filled", "checkroom", "accent")],
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="character"),
    )


def build_pack_view(character):
    """Return a browser-first main view for inventory."""

    inventory = list(character.db.brave_inventory or [])
    inventory.sort(key=lambda entry: ITEM_TEMPLATES.get(entry["template"], {}).get("name", entry["template"]))
    grouped = {kind: [] for kind in PACK_KIND_ORDER}
    other_entries = []

    for entry in inventory:
        template_id = entry["template"]
        quantity = entry.get("quantity", 1)
        item = ITEM_TEMPLATES.get(template_id, {})
        lines = []
        value_text = _format_item_value_text(item, quantity)
        if value_text:
            lines.append("Value: " + value_text)
        if item.get("kind") == "meal":
            restore_text = _format_restore_summary(item.get("restore", {}), character)
            if restore_text:
                lines.append("Restore: " + restore_text)
            buff_text = _format_context_bonus_summary(item.get("meal_bonuses", {}), character)
            if buff_text:
                lines.append("Buff: " + buff_text)
        elif item.get("kind") == "equipment":
            bonus_text = _format_context_bonus_summary(item.get("bonuses", {}), character)
            if bonus_text:
                lines.append("Bonuses: " + bonus_text)

        formatted = _entry(
            item.get("name", template_id) + (f" x{quantity}" if quantity > 1 else ""),
            lines=lines,
            summary=item.get("summary"),
            icon="inventory_2",
        )
        if item.get("kind") == "meal":
            command = f"eat {item.get('name', template_id)}"
            formatted["command"] = command
            formatted["actions"] = [_action("Eat", command, "restaurant", tone="good")]
        kind = item.get("kind")
        if kind in grouped:
            grouped[kind].append(formatted)
        else:
            other_entries.append(formatted)

    sections = []
    for kind in PACK_KIND_ORDER:
        if grouped[kind]:
            label, icon = PACK_KIND_LABELS[kind]
            sections.append(_section(label, icon, "entries", items=grouped[kind]))
    if other_entries:
        sections.append(_section("Other", "inventory_2", "entries", items=other_entries))
    if not sections:
        sections.append(_section("Carried", "backpack", "lines", lines=["Your pack is empty."]))

    return _make_view(
        "Inventory",
        "Pack",
        eyebrow_icon="backpack",
        title_icon="inventory_2",
        subtitle="What you are carrying between rooms, fights, and town stops.",
        chips=[
            _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
            _chip(f"{len(inventory)} item types", "category", "muted"),
        ],
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="character"),
    )
