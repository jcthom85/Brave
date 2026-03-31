"""Idempotent world bootstrap for Brave."""

from evennia.utils import create, logger, search

from world.data.starting_world import EXITS, ROOMS, WORLD_OBJECTS

ROOM_TAG_CATEGORY = "brave_room"
EXIT_TAG_CATEGORY = "brave_exit"
ENTITY_TAG_CATEGORY = "brave_entity"


def _first_match(tag_key, category):
    matches = list(search.search_tag(tag_key, category=category))
    return matches[0] if matches else None


def get_room(room_id):
    """Return a Brave room by stable id, if it exists."""

    return _first_match(room_id, ROOM_TAG_CATEGORY)


def get_entity(entity_id):
    """Return a Brave world entity by stable id, if it exists."""

    return _first_match(entity_id, ENTITY_TAG_CATEGORY)


def _ensure_room(room_data):
    room = get_room(room_data["id"])
    if not room:
        room = create.create_object(
            typeclass="typeclasses.rooms.Room",
            key=room_data["key"],
            tags=[(room_data["id"], ROOM_TAG_CATEGORY)],
            nohome=True,
        )

    room.key = room_data["key"]
    room.db.desc = room_data["desc"]
    room.db.brave_room_id = room_data["id"]
    room.db.brave_zone = room_data["zone"]
    room.db.brave_world = room_data.get("world", "Brave")
    room.db.brave_resonance = room_data.get("resonance", "fantasy")
    room.db.brave_map_region = room_data.get("map_region", room_data["zone"])
    room.db.brave_map_x = room_data.get("map_x", 0)
    room.db.brave_map_y = room_data.get("map_y", 0)
    room.db.brave_map_icon = room_data.get("map_icon", room_data["key"][:1].upper())
    room.db.brave_safe = room_data["safe"]
    room.db.brave_activities = list(room_data.get("activities", []))
    room.db.brave_portal_hub = bool(room_data.get("portal_hub", False))
    room.tags.add(room_data["id"], category=ROOM_TAG_CATEGORY)
    room.save()
    return room


def _ensure_exit(exit_data, rooms_by_id):
    exit_obj = _first_match(exit_data["id"], EXIT_TAG_CATEGORY)
    source = rooms_by_id[exit_data["source"]]
    destination = rooms_by_id[exit_data["destination"]]

    if not exit_obj:
        exit_obj = create.create_object(
            typeclass="typeclasses.exits.Exit",
            key=exit_data["key"],
            location=source,
            destination=destination,
            home=source,
            tags=[(exit_data["id"], EXIT_TAG_CATEGORY)],
        )

    exit_obj.key = exit_data["key"]
    exit_obj.location = source
    exit_obj.destination = destination
    exit_obj.home = source
    exit_obj.db.brave_exit_id = exit_data["id"]
    exit_obj.db.brave_direction = exit_data.get("direction", exit_data["key"])
    exit_obj.db.brave_exit_label = exit_data.get("label", destination.key)
    exit_obj.tags.add(exit_data["id"], category=EXIT_TAG_CATEGORY)
    exit_obj.aliases.clear()
    for alias in exit_data.get("aliases", []):
        exit_obj.aliases.add(alias)
    exit_obj.save()
    return exit_obj


def _ensure_world_object(entity_data, rooms_by_id):
    obj = _first_match(entity_data["id"], ENTITY_TAG_CATEGORY)
    start_room = rooms_by_id["brambleford_town_green"]
    typeclass_path = entity_data.get("typeclass", "typeclasses.objects.Object")
    if not obj:
        obj = create.create_object(
            typeclass=typeclass_path,
            key=entity_data["key"],
            location=rooms_by_id[entity_data["location"]],
            home=start_room,
            tags=[(entity_data["id"], ENTITY_TAG_CATEGORY)],
        )
        obj.locks.add("get:false();call:false();puppet:false()")
    elif not obj.is_typeclass(typeclass_path, exact=False):
        obj.swap_typeclass(typeclass_path, clean_attributes=False, no_default=True)

    obj.key = entity_data["key"]
    obj.location = rooms_by_id[entity_data["location"]]
    obj.home = start_room
    obj.db.desc = entity_data["desc"]
    obj.db.brave_display_name = entity_data.get("display_name", "")
    obj.db.brave_entity_id = entity_data["id"]
    obj.db.brave_entity_kind = entity_data.get("kind", "scenery")
    if obj.db.brave_entity_kind == "arcade":
        obj.db.brave_arcade_games = list(entity_data.get("arcade_games", []))
        obj.db.brave_arcade_price = entity_data.get("arcade_price", 1)
        obj.db.brave_arcade_rewards = dict(entity_data.get("arcade_rewards", {}))
    obj.tags.add(entity_data["id"], category=ENTITY_TAG_CATEGORY)
    obj.aliases.clear()
    for alias in entity_data.get("aliases", []):
        obj.aliases.add(alias)
    obj.save()
    return obj


def ensure_brave_world():
    """Create or repair the first Brave world slice."""

    try:
        rooms_by_id = {room_data["id"]: _ensure_room(room_data) for room_data in ROOMS}
        start_room = rooms_by_id["brambleford_town_green"]
        for room in rooms_by_id.values():
            if room == start_room:
                room.home = start_room
            elif not room.home:
                room.home = start_room
            room.save()
        for exit_data in EXITS:
            _ensure_exit(exit_data, rooms_by_id)
        for entity_data in WORLD_OBJECTS:
            _ensure_world_object(entity_data, rooms_by_id)
        return rooms_by_id
    except Exception:
        logger.log_trace("Brave world bootstrap failed.")
        raise
