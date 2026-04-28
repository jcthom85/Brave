"""Rest-site helpers for Brave exploration."""

DEFAULT_REST_ROOM_IDS = {
    "brambleford_lantern_rest_inn",
    "tutorial_wayfarers_yard",
}


def room_allows_rest(room):
    """Return whether a room is an authored place where characters can rest."""

    if not room:
        return False
    room_db = getattr(room, "db", None)
    if not bool(getattr(room_db, "brave_safe", False)):
        return False
    if bool(getattr(room_db, "brave_rest_allowed", False)):
        return True
    return getattr(room_db, "brave_room_id", None) in DEFAULT_REST_ROOM_IDS
