"""Navigation helpers for Brave's cardinal-first movement model."""

from collections import deque

from evennia.utils import search


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


def build_map_snapshot(room, radius=None, character=None):
    """Build structured regional-map data for text and browser renderers."""

    region = getattr(room.db, "brave_map_region", None)
    if not region:
        return None

    rooms = get_rooms_in_map_region(region)
    if not rooms:
        return None

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
    if character and getattr(character.db, "brave_party_id", None):
        from world.party import get_party_members

        party_members = [member for member in get_party_members(character) if member.id != character.id]
        for member in party_members:
            if not member.location:
                continue
            party_names_by_room.setdefault(member.location.id, []).append(member.key)

    lines = []
    node_gap = "-----"
    node_blank = "     "
    node_pipe = "  |  "

    for y in range(max_y, min_y - 1, -1):
        node_line = []
        for x in range(min_x, max_x + 1):
            candidate = room_by_coord.get((x, y))
            if candidate:
                icon = "@" if candidate.id == room.id else getattr(candidate.db, "brave_map_icon", "?")
                node_line.append(f"[ {icon} ]")
            else:
                node_line.append(node_blank)

            if x < max_x:
                node_line.append(node_gap if _has_connection(room_by_coord, x, y, "east") else node_blank)
        lines.append("".join(node_line).rstrip())

        if y > min_y:
            connector_line = []
            for x in range(min_x, max_x + 1):
                connector_line.append(node_pipe if _has_connection(room_by_coord, x, y, "south") else node_blank)
                if x < max_x:
                    connector_line.append(node_blank)
            if any(segment.strip() for segment in connector_line):
                lines.append("".join(connector_line).rstrip())

    visible_rooms = sorted(
        rooms,
        key=lambda candidate: (
            getattr(candidate.db, "brave_map_y", 0),
            getattr(candidate.db, "brave_map_x", 0),
            candidate.key.lower(),
        ),
    )

    current_party = party_names_by_room.get(room.id, [])
    legend = [{"icon": "@", "label": "You", "suffix": f"Party: {', '.join(sorted(current_party))}" if current_party else ""}]
    for candidate in visible_rooms:
        if candidate.id == room.id:
            continue
        icon = getattr(candidate.db, "brave_map_icon", "?")
        members_here = party_names_by_room.get(candidate.id, [])
        legend.append(
            {
                "icon": icon,
                "label": candidate.key,
                "suffix": f"Party: {', '.join(sorted(members_here))}" if members_here else "",
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
        "legend": legend,
        "exits": current_exits,
        "party": party_status,
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
