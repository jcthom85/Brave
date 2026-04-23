"""Navigation helpers for Brave's cardinal-first movement model."""

from collections import deque

from evennia.utils import search

from world.content import get_content_registry


CONTENT = get_content_registry()
ENCOUNTER_CONTENT = CONTENT.encounters
QUEST_CONTENT = CONTENT.quests
SYSTEMS_CONTENT = CONTENT.systems


DIRECTION_ORDER = [
    "north",
    "east",
    "south",
    "west",
    "up",
    "down",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "in",
    "out",
]

DIRECTION_SHORT = {
    "north": "N",
    "east": "E",
    "south": "S",
    "west": "W",
    "up": "U",
    "down": "D",
    "northeast": "NE",
    "northwest": "NW",
    "southeast": "SE",
    "southwest": "SW",
    "in": "IN",
    "out": "OUT",
}

CARDINAL_DELTAS = {
    "north": (0, 1),
    "east": (1, 0),
    "south": (0, -1),
    "west": (-1, 0),
}

MAP_MARKERS = {
    "current": {"icon": "player", "label": "You", "tone": "current"},
    "quest": {"icon": "castle-flag", "label": "Tracked Quest", "tone": "quest"},
    "boss": {"icon": "skull-trophy", "label": "Boss", "tone": "danger"},
    "portal": {"icon": "spawn-node", "label": "Portal", "tone": "portal"},
    "forge": {"icon": "anvil", "label": "Forge", "tone": "service"},
    "shop": {"icon": "wooden-sign", "label": "Shop", "tone": "service"},
    "rest": {"icon": "campfire", "label": "Rest", "tone": "service"},
    "trophy": {"icon": "trophy", "label": "Trophy Hall", "tone": "service"},
    "fishing": {"icon": "fish", "label": "Fishing", "tone": "activity"},
    "cooking": {"icon": "knife-fork", "label": "Cooking", "tone": "activity"},
    "party": {"icon": "double-team", "label": "Party", "tone": "party"},
}

MAP_MARKER_PRIORITY = (
    "current",
    "quest",
    "boss",
    "portal",
    "forge",
    "shop",
    "rest",
    "trophy",
    "fishing",
    "cooking",
    "party",
)


def get_exit_direction(exit_obj):
    """Return a stable direction key for an exit."""

    return (getattr(exit_obj.db, "brave_direction", None) or exit_obj.key or "").lower()


def get_exit_label(exit_obj):
    """Return a human label for an exit destination."""

    return getattr(exit_obj.db, "brave_exit_label", None) or exit_obj.destination.key


def sort_exits(exits):
    """Sort exits in a predictable directional order."""

    def sort_key(exit_obj):
        direction = get_exit_direction(exit_obj)
        try:
            order = DIRECTION_ORDER.index(direction)
        except ValueError:
            order = len(DIRECTION_ORDER)
        return (order, direction, get_exit_label(exit_obj).lower())

    return sorted(exits, key=sort_key)


def format_exit_summary(exits):
    """Return a compact one-line exit summary."""

    parts = []
    for exit_obj in sort_exits(exits):
        short = DIRECTION_SHORT.get(get_exit_direction(exit_obj), get_exit_direction(exit_obj).upper())
        parts.append(f"{short}: {get_exit_label(exit_obj)}")
    return ", ".join(parts)


def format_travel_option(exit_obj):
    """Return a travel list line for one exit."""

    direction = get_exit_direction(exit_obj)
    short = DIRECTION_SHORT.get(direction, direction.upper())
    aliases = [alias for alias in exit_obj.aliases.all() if alias.lower() != short.lower()]
    alias_suffix = f" (aliases: {', '.join(aliases)})" if aliases else ""
    return f"  - {direction} ({short}) -> {get_exit_label(exit_obj)}{alias_suffix}"


def get_rooms_in_map_region(region_name):
    """Return all rooms belonging to a specific map region."""

    return [
        room
        for room in search.search_typeclass("typeclasses.rooms.Room")
        if getattr(room.db, "brave_map_region", None) == region_name
    ]


def get_room_route(source_room, destination_room, max_steps=40):
    """Return a shortest exit-direction route between two rooms."""

    if not source_room or not destination_room:
        return None
    if source_room.id == destination_room.id:
        return []

    queue = deque([(source_room, [])])
    visited = {source_room.id}

    while queue:
        room, route = queue.popleft()
        if len(route) >= max_steps:
            continue

        for exit_obj in sort_exits(list(room.exits)):
            destination = getattr(exit_obj, "destination", None)
            if not destination or destination.id in visited:
                continue
            direction = get_exit_direction(exit_obj)
            next_route = route + [direction]
            if destination.id == destination_room.id:
                return next_route
            visited.add(destination.id)
            queue.append((destination, next_route))

    return None


def format_route_hint(source_room, destination_room):
    """Format a readable route hint between rooms."""

    if not source_room or not destination_room:
        return "route unavailable"
    if source_room.id == destination_room.id:
        return "here with you"

    route = get_room_route(source_room, destination_room)
    if route is None:
        return "route unavailable"

    shown = route[:4]
    summary = ", ".join(direction for direction in shown)
    if len(route) > len(shown):
        summary += ", ..."
    step_label = "step" if len(route) == 1 else "steps"
    return f"{summary} ({len(route)} {step_label})"


def _has_connection(room_by_coord, x, y, direction):
    room = room_by_coord.get((x, y))
    if not room:
        return False
    for exit_obj in room.exits:
        if get_exit_direction(exit_obj) == direction:
            return True
    return False


def _map_marker(marker_key):
    """Return a serialized map marker for the browser renderer."""

    marker = MAP_MARKERS[marker_key]
    return {
        "key": marker_key,
        "icon": marker["icon"],
        "label": marker["label"],
        "tone": marker["tone"],
    }


def _tracked_quest_room_ids(character):
    """Return incomplete visit-room objectives for the tracked active quest."""

    if not character:
        return set()

    tracked_key = getattr(character.db, "brave_tracked_quest", None)
    quest_state = getattr(character.db, "brave_quests", None) or {}
    if not tracked_key or not isinstance(quest_state, dict):
        return set()

    active_state = quest_state.get(tracked_key) or {}
    if active_state.get("status") != "active":
        return set()

    quest_data = QUEST_CONTENT.quests.get(tracked_key) or {}
    objectives = quest_data.get("objectives") or []
    state_objectives = active_state.get("objectives") or []
    room_ids = set()
    for index, objective in enumerate(objectives):
        objective_state = state_objectives[index] if index < len(state_objectives) else {}
        if objective_state.get("completed"):
            continue
        if objective.get("type") == "visit_room" and objective.get("room_id"):
            room_ids.add(objective["room_id"])
    return room_ids


def _room_has_boss_encounter(room_id):
    """Return True if any encounter in the room includes a boss-tagged enemy."""

    for encounter in ENCOUNTER_CONTENT.get_room_encounters(room_id):
        enemy_keys = encounter.get("enemies") or []
        for enemy_key in enemy_keys:
            enemy_data = ENCOUNTER_CONTENT.enemy_templates.get(enemy_key) or {}
            if "boss" in (enemy_data.get("tags") or []):
                return True
    return False


def _map_marker_keys(room, *, current=False, party=False, tracked_room_ids=None):
    """Return prioritized full-map marker keys for one room."""

    tracked_room_ids = tracked_room_ids or set()
    room_id = getattr(room.db, "brave_room_id", None)
    activities = set(getattr(room.db, "brave_activities", None) or [])
    keys = set()

    if current:
        keys.add("current")
    if room_id and room_id in tracked_room_ids:
        keys.add("quest")
    if room_id and _room_has_boss_encounter(room_id):
        keys.add("boss")
    if getattr(room.db, "brave_portal_hub", False) or (
        room_id and any(portal.get("entry_room") == room_id for portal in SYSTEMS_CONTENT.portals.values())
    ):
        keys.add("portal")
    if room_id and room_id == SYSTEMS_CONTENT.forge_room_id:
        keys.add("forge")
    if room_id and room_id == SYSTEMS_CONTENT.outfitters_room_id:
        keys.add("shop")
    if "cooking" in activities:
        keys.add("rest")
        keys.add("cooking")
    if room_id and room_id in SYSTEMS_CONTENT.fishing_spots:
        keys.add("fishing")
    if room_id and "trophy" in room_id:
        keys.add("trophy")
    if party:
        keys.add("party")

    return [marker_key for marker_key in MAP_MARKER_PRIORITY if marker_key in keys]


def _micromap_symbol_name(*, current=False, party=False):
    """Return the low-noise room symbol used by the micromap."""

    if current:
        return "player"
    if party:
        return "double-team"
    return "radio_button_unchecked"


def get_discovered_room_ids(character):
    """Return the set of room ids discovered by a character."""

    if not character:
        return set()
    discovered = getattr(character.db, "brave_discovered_rooms", None) or []
    return {str(room_id) for room_id in discovered if room_id}


def discover_room(character, room):
    """Persist discovery for a room on the character."""

    if not character or not room:
        return False

    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    if not room_id:
        return False

    discovered = list(getattr(character.db, "brave_discovered_rooms", None) or [])
    room_id = str(room_id)
    if room_id in discovered:
        return False

    discovered.append(room_id)
    character.db.brave_discovered_rooms = discovered
    return True


def build_map_snapshot(room, radius=None, character=None):
    """Build structured regional-map data for text and browser renderers."""

    region = getattr(room.db, "brave_map_region", None)
    if not region:
        return None

    rooms = get_rooms_in_map_region(region)
    if not rooms:
        return None

    discovered_room_ids = get_discovered_room_ids(character)
    if character:
        current_room_id = str(getattr(room.db, "brave_room_id", None) or "")
        rooms = [
            candidate
            for candidate in rooms
            if str(getattr(candidate.db, "brave_room_id", None) or "") in discovered_room_ids
            or candidate.id == room.id
            or (current_room_id and str(getattr(candidate.db, "brave_room_id", None) or "") == current_room_id)
        ]
        if not rooms:
            rooms = [room]

    current_x = getattr(room.db, "brave_map_x", 0)
    current_y = getattr(room.db, "brave_map_y", 0)

    if radius is not None:
        rooms = [
            candidate
            for candidate in rooms
            if abs(getattr(candidate.db, "brave_map_x", 0) - current_x) <= radius
            and abs(getattr(candidate.db, "brave_map_y", 0) - current_y) <= radius
        ]

    room_by_coord = {
        (getattr(candidate.db, "brave_map_x", 0), getattr(candidate.db, "brave_map_y", 0)): candidate
        for candidate in rooms
    }
    coords = list(room_by_coord)
    if not coords:
        return None

    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)

    party_names_by_room = {}
    party_members = []
    party_coords = set()
    if character and getattr(character.db, "brave_party_id", None):
        from world.party import get_party_members

        party_members = [member for member in get_party_members(character) if member.id != character.id]
        for member in party_members:
            if not member.location:
                continue
            party_names_by_room.setdefault(member.location.id, []).append(member.key)
            if getattr(member.location.db, "brave_map_region", None) == region:
                party_coords.add(
                    (
                        getattr(member.location.db, "brave_map_x", 0),
                        getattr(member.location.db, "brave_map_y", 0),
                    )
                )
    tracked_room_ids = _tracked_quest_room_ids(character)

    def connector_cell(axis):
        return {"kind": "connector", "axis": axis}

    def empty_cell():
        return {"kind": "empty"}

    def tile_rows(x, y):
        candidate = room_by_coord.get((x, y))
        if not candidate:
            empty_row = [empty_cell(), empty_cell(), empty_cell()]
            return {
                "text": ["   ", "   ", "   "],
                "cells": [list(empty_row), list(empty_row), list(empty_row)],
            }

        north = _has_connection(room_by_coord, x, y, "north")
        south = _has_connection(room_by_coord, x, y, "south")
        west = _has_connection(room_by_coord, x, y, "west")
        east = _has_connection(room_by_coord, x, y, "east")
        is_current = candidate.id == room.id
        has_party = (x, y) in party_coords
        glyph = str(getattr(candidate.db, "brave_map_icon", "?") or "?")[:1]
        center = glyph
        marker_keys = _map_marker_keys(
            candidate,
            current=is_current,
            party=has_party,
            tracked_room_ids=tracked_room_ids,
        )
        markers = [_map_marker(marker_key) for marker_key in marker_keys]
        primary_marker = markers[0] if markers else None
        symbol = primary_marker["icon"] if primary_marker else "radio_button_unchecked"
        members_here = party_names_by_room.get(candidate.id, [])
        tooltip = candidate.key
        if markers:
            tooltip += f" · {', '.join(marker['label'] for marker in markers)}"
        if members_here:
            tooltip += f" · Party: {', '.join(sorted(members_here))}"

        return {
            "text": [
                f" {'|' if north else ' '} ",
                f"{'-' if west else ' '}{center}{'-' if east else ' '}",
                f" {'|' if south else ' '} ",
            ],
            "cells": [
                [empty_cell(), connector_cell("vertical") if north else empty_cell(), empty_cell()],
                [
                    connector_cell("horizontal") if west else empty_cell(),
                    {
                        "kind": "room",
                        "symbol": symbol,
                        "micro_symbol": _micromap_symbol_name(current=is_current, party=has_party),
                        "glyph": center,
                        "title": tooltip,
                        "tone": primary_marker["tone"] if primary_marker else "room",
                        "primary_marker": primary_marker["key"] if primary_marker else "",
                        "markers": markers,
                    },
                    connector_cell("horizontal") if east else empty_cell(),
                ],
                [empty_cell(), connector_cell("vertical") if south else empty_cell(), empty_cell()],
            ],
        }

    lines = []
    grid_rows = []
    for y in range(max_y, min_y - 1, -1):
        row_bands = [[], [], []]
        cell_bands = [[], [], []]
        for x in range(min_x, max_x + 1):
            tile = tile_rows(x, y)
            for index in range(3):
                row_bands[index].append(tile["text"][index])
                cell_bands[index].extend(tile["cells"][index])
        lines.extend("".join(parts).rstrip() for parts in row_bands)
        grid_rows.extend(cell_bands)

    current_party = party_names_by_room.get(room.id, [])
    used_marker_keys = []
    for row in grid_rows:
        for cell in row:
            if cell.get("kind") != "room":
                continue
            for marker in cell.get("markers") or []:
                used_marker_keys.append(marker["key"])
    legend = []
    for marker_key in MAP_MARKER_PRIORITY:
        if marker_key not in used_marker_keys:
            continue
        marker = _map_marker(marker_key)
        legend.append(
            {
                "icon": marker["icon"],
                "symbol": marker["icon"],
                "label": marker["label"],
                "tone": marker["tone"],
                "suffix": f"Party: {', '.join(sorted(current_party))}" if marker_key == "current" and current_party else "",
            }
        )
    for room_id, member_names in sorted(party_names_by_room.items()):
        if room_id == room.id:
            continue
        legend.append(
            {
                "icon": MAP_MARKERS["party"]["icon"],
                "symbol": MAP_MARKERS["party"]["icon"],
                "label": "Party",
                "tone": MAP_MARKERS["party"]["tone"],
                "suffix": ", ".join(sorted(member_names)),
            }
        )

    current_exits = sort_exits(room.exits)
    party_status = []
    for member in party_members:
        status = "online" if getattr(member, "is_connected", False) else "offline"
        location = member.location.key if member.location else "Nowhere"
        route = format_route_hint(room, member.location)
        party_status.append(
            {
                "name": member.key,
                "status": status,
                "location": location,
                "route": route,
            }
        )

    return {
        "region": region,
        "room": room,
        "map_text": "\n".join(lines),
        "map_tiles": {
            "columns": len(grid_rows[0]) if grid_rows else 0,
            "rows": grid_rows,
        },
        "legend": legend,
        "exits": current_exits,
        "party": party_status,
        "radius": radius,
    }


def build_minimap_snapshot(room, radius=2, character=None):
    """Build a fixed-size local minimap snapshot for browser and text use."""

    snapshot = build_map_snapshot(room, radius=radius, character=character)
    if not snapshot:
        return None
    map_tiles = snapshot.get("map_tiles") or {"columns": 0, "rows": []}
    compact_rows = []
    for row in map_tiles.get("rows") or []:
        compact_row = []
        for cell in row:
            if cell.get("kind") != "room":
                compact_row.append(cell)
                continue
            compact_cell = dict(cell)
            compact_cell["symbol"] = compact_cell.get("micro_symbol") or compact_cell.get("symbol") or "guarded-tower"
            compact_cell["markers"] = []
            compact_cell["primary_marker"] = ""
            compact_row.append(compact_cell)
        compact_rows.append(compact_row)
    return {
        "map_text": snapshot.get("map_text", ""),
        "map_tiles": {
            "columns": map_tiles.get("columns", 0),
            "rows": compact_rows,
        },
        "radius": radius,
    }


def render_map(room, radius=None, character=None):
    """Render an ASCII map or minimap for the current room region."""

    snapshot = build_map_snapshot(room, radius=radius, character=character)
    if not snapshot:
        return "No map data is available for this area yet."

    lines = [snapshot["map_text"], ""]
    for entry in snapshot["legend"]:
        suffix = f" [{entry['suffix']}]" if entry.get("suffix") else ""
        lines.append(f"{entry['icon']} = {entry['label']}{suffix}")

    current_exits = snapshot["exits"]
    if current_exits:
        lines.append("")
        lines.append(f"|wVisible Exits:|n {format_exit_summary(current_exits)}")

    if snapshot["party"]:
        lines.append("")
        lines.append("Party:")
        for member in snapshot["party"]:
            lines.append(f"{member['name']} [{member['status']}] - {member['location']} - {member['route']}")

    return "\n".join(lines)


def render_minimap(room, radius=2, character=None):
    """Render a fixed-size local minimap centered on the current room."""

    region = getattr(room.db, "brave_map_region", None)
    if not region:
        return ""

    rooms = get_rooms_in_map_region(region)
    if not rooms:
        return ""

    room_by_coord = {
        (getattr(candidate.db, "brave_map_x", 0), getattr(candidate.db, "brave_map_y", 0)): candidate
        for candidate in rooms
    }

    current_x = getattr(room.db, "brave_map_x", 0)
    current_y = getattr(room.db, "brave_map_y", 0)

    party_coords = set()
    if character and getattr(character.db, "brave_party_id", None):
        from world.party import get_party_members

        for member in get_party_members(character):
            if member.id == character.id or not member.location:
                continue
            if getattr(member.location.db, "brave_map_region", None) != region:
                continue
            party_coords.add(
                (
                    getattr(member.location.db, "brave_map_x", 0),
                    getattr(member.location.db, "brave_map_y", 0),
                )
            )

    def tile_for(x, y):
        candidate = room_by_coord.get((x, y))
        if not candidate:
            return ["   ", "   ", "   "]

        north = "|" if _has_connection(room_by_coord, x, y, "north") else " "
        south = "|" if _has_connection(room_by_coord, x, y, "south") else " "
        east = "-" if _has_connection(room_by_coord, x, y, "east") else " "
        west = "-" if _has_connection(room_by_coord, x, y, "west") else " "

        if candidate.id == room.id:
            center = "@"
        elif (x, y) in party_coords:
            center = "P"
        else:
            center = "o"

        return [
            f" {north} ",
            f"{west}{center}{east}",
            f" {south} ",
        ]

    lines = []

    for y in range(current_y + radius, current_y - radius - 1, -1):
        tile_rows = [[], [], []]
        for x in range(current_x - radius, current_x + radius + 1):
            tile = tile_for(x, y)
            for index in range(3):
                tile_rows[index].append(tile[index])
        lines.extend("".join(row) for row in tile_rows)

    return "\n".join(lines)
