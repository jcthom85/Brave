"""Shared RPG Awesome icon choices for Brave races and classes."""

DEFAULT_CLASS_ICON = "crossed-swords"
DEFAULT_RACE_ICON = "player"

CLASS_ICONS = {
    "warrior": "heavy-shield",
    "cleric": "hospital-cross",
    "ranger": "archer",
    "mage": "crystal-wand",
    "rogue": "cloak-and-dagger",
    "paladin": "bolt-shield",
    "druid": "sprout-emblem",
}

RACE_ICONS = {
    "human": "player",
    "elf": "fairy",
    "dwarf": "anvil",
    "mosskin": "clover",
    "ashborn": "horns",
}


def get_class_icon(class_key, class_data=None):
    """Return the RPG Awesome icon name for a class."""

    explicit = (class_data or {}).get("icon")
    if explicit:
        return explicit
    return CLASS_ICONS.get(class_key, DEFAULT_CLASS_ICON)


def get_race_icon(race_key, race_data=None):
    """Return the RPG Awesome icon name for a race."""

    explicit = (race_data or {}).get("icon")
    if explicit:
        return explicit
    return RACE_ICONS.get(race_key, DEFAULT_RACE_ICON)
