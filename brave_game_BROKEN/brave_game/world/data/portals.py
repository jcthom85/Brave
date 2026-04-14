"""Portal definitions for Brave's first Nexus slice."""

PORTALS = {
    "junkyard_planet": {
        "name": "Junk-Yard Planet",
        "status": "stable",
        "resonance": "tech",
        "summary": "A scrapyard world of broken rails, humming salvage, and practical tech violence.",
        "travel_hint": "east",
        "entry_room": "junkyard_planet_landing_pad",
    },
    "training_island": {
        "name": "Training Island",
        "status": "dormant",
        "resonance": "martial",
        "summary": "A fast bright world meant for ki, speed, and martial experiments.",
        "travel_hint": None,
        "entry_room": None,
    },
    "drafting_table": {
        "name": "The Drafting Table",
        "status": "sealed",
        "resonance": "sandbox",
        "summary": "A blank builder's dimension waiting for the family's first custom rooms.",
        "travel_hint": None,
        "entry_room": None,
    },
}

PORTAL_STATUS_LABELS = {
    "stable": "Stable",
    "dormant": "Dormant",
    "sealed": "Sealed",
}


def get_portal(portal_key):
    """Return a portal definition by key."""

    return PORTALS.get(portal_key)
