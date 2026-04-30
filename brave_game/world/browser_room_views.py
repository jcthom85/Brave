"""Room-focused browser view payload builders for Brave."""

from world.browser_mobile_views import (
    _build_mobile_pack_payload,
    _build_mobile_room_payload,
)
from world.browser_room_helpers import (
    _build_room_social_presence,
    _format_room_context_action_items,
    _format_room_entity_items,
    _format_room_threat_items,
    _movement_command,
    _short_direction,
)
from world.browser_ui import (
    _item,
    _make_view,
    _reactive_view,
    _section,
)
from world.navigation import build_minimap_snapshot, get_exit_direction, get_exit_label, visible_exits
from world.tutorial import (
    LANTERNFALL_RECAP_PAGES,
    LANTERNFALL_WELCOME_PAGES,
    get_tutorial_mechanical_guidance,
    is_tutorial_active,
)


def build_room_view(room, looker, *, visible_threats=None, visible_entities=None, visible_chars=None):
    """Return a browser-first room view for exploration and movement."""

    world_name = getattr(room.db, "brave_world", "Brave") or "Brave"
    region_name = getattr(room.db, "brave_map_region", None) or room.db.brave_zone or world_name
    description = room.db.desc or "A place of mystery and potential."
    primary_exits = {}
    vertical_exits = []
    special_exits = []
    for exit_obj in visible_exits(room, looker):
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
