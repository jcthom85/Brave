"""Reactive browser tone profiles for Brave regions and worlds."""

WORLD_TONES = {
    "neutral": {
        "label": "Neutral",
        "accent": "#b58b57",
    },
    "brambleford": {
        "label": "Brambleford",
        "accent": "#d6a261",
    },
    "goblinroad": {
        "label": "Goblin Road",
        "accent": "#c67a4d",
    },
    "woods": {
        "label": "Whispering Woods",
        "accent": "#78b49a",
    },
    "oldbarrow": {
        "label": "Old Barrow",
        "accent": "#b6b0a1",
    },
    "watchtower": {
        "label": "Ruined Watchtower",
        "accent": "#b07a57",
    },
    "warrens": {
        "label": "Goblin Warrens",
        "accent": "#c88d43",
    },
    "blackfen": {
        "label": "Blackfen",
        "accent": "#6fa278",
    },
    "drownedweir": {
        "label": "Drowned Weir",
        "accent": "#7ebbc5",
    },
    "nexus": {
        "label": "Nexus Gate",
        "accent": "#7cb7d7",
    },
    "junkyard": {
        "label": "Junk-Yard Planet",
        "accent": "#dd8f52",
    },
    "portal": {
        "label": "Portal World",
        "accent": "#9ab8da",
    },
}


def _room_source(source):
    """Return the most room-like source available for tone resolution."""

    if not source:
        return None
    if getattr(source, "destination", None):
        source = getattr(source, "destination", None) or source
    if getattr(source, "location", None) and not getattr(getattr(source, "db", None), "brave_zone", None):
        location = getattr(source, "location", None)
        if location and getattr(location, "db", None):
            return location
    return source


def get_world_tone_key(source):
    """Resolve the best-fit world tone key for a room or room-adjacent object."""

    room = _room_source(source)
    if not room or not getattr(room, "db", None):
        return "neutral"

    world = str(getattr(room.db, "brave_world", "Brave") or "Brave").strip()
    zone = str(getattr(room.db, "brave_zone", "") or "").strip()
    room_key = str(getattr(room, "key", "") or "").strip()
    combined = " ".join(part for part in (world, zone, room_key) if part).lower()

    if getattr(room.db, "brave_portal_hub", False) or "nexus" in combined or "observatory" in combined:
        return "nexus"

    if world.lower() != "brave":
        if any(token in combined for token in ("junk", "scrap", "relay trench", "crane grave", "anchor pit")):
            return "junkyard"
        return "portal"

    if any(token in combined for token in ("drowned", "weir", "blackwater", "sluice", "lamp house")):
        return "drownedweir"
    if any(token in combined for token in ("blackfen", "fenreach", "miretooth", "boglight", "reedflats", "carrion rise")):
        return "blackfen"
    if any(token in combined for token in ("warrens", "pot-king", "sinkmouth", "torchgut", "bone midden", "sludge run", "feast hall")):
        return "warrens"
    if any(token in combined for token in ("watchtower", "blackreed", "yard ledge", "broken stair")):
        return "watchtower"
    if any(token in combined for token in ("barrow", "sunken dais", "marker row", "dawn bell")):
        return "oldbarrow"
    if any(token in combined for token in ("whispering", "greymaw", "briar", "stone path")):
        return "woods"
    if any(token in combined for token in ("goblin road", "east gate", "fencebreaker", "old fence line", "wolf turn")):
        return "goblinroad"

    return "brambleford"
