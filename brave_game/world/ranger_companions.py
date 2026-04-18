"""Ranger companion data and helpers."""

RANGER_COMPANIONS = {
    "marsh_hound": {
        "name": "Marsh Hound",
        "icon": "pets",
        "summary": "A low, wiry fen-hound bred to stay on a trail and keep prey from settling once the hunt starts.",
        "combat": {
            "marked_damage_bonus": 1,
            "bleed_bonus": 1,
        },
    },
    "ash_hawk": {
        "name": "Ash Hawk",
        "icon": "flutter_dash",
        "summary": "A sharp-eyed hawk that keeps the quarry in view and turns a clean mark into cleaner follow-up shots.",
        "combat": {
            "mark_turn_bonus": 1,
            "aimed_accuracy_bonus": 2,
            "rain_mark_turn_bonus": 1,
        },
    },
    "briar_boar": {
        "name": "Briar Boar",
        "icon": "shield",
        "summary": "A stubborn brush-boar that hits trap lines hard, contests space, and makes pinned targets even worse off.",
        "combat": {
            "snare_turn_bonus": 1,
            "snare_damage_bonus": 1,
            "evasion_guard_bonus": 2,
        },
    },
}

DEFAULT_RANGER_COMPANION = "marsh_hound"


def get_companion(companion_key):
    """Return one authored ranger companion."""

    return dict(RANGER_COMPANIONS.get(str(companion_key or "").lower(), {}))


def get_default_ranger_companion():
    """Return the default ranger companion key."""

    return DEFAULT_RANGER_COMPANION


def get_companion_name(companion_key):
    """Return a readable companion name."""

    return get_companion(companion_key).get("name", str(companion_key or "").replace("_", " ").title())
