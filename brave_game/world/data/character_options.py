"""Compatibility accessors for Brave character content.

This module used to carry a hand-maintained duplicate of race, class, ability,
and passive definitions. That drifted away from the registry-backed JSON pack.

Keep the old import surface, but source all values from the live content
registry so legacy imports cannot diverge from runtime content again.
"""

from world.content.registry import get_content_registry


CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters

PRIMARY_STATS = CHARACTER_CONTENT.primary_stats
STARTING_RACE = CHARACTER_CONTENT.starting_race
STARTING_CLASS = CHARACTER_CONTENT.starting_class
MAX_LEVEL = CHARACTER_CONTENT.max_level
VERTICAL_SLICE_CLASSES = CHARACTER_CONTENT.vertical_slice_classes
XP_FOR_LEVEL = CHARACTER_CONTENT.xp_for_level

RACES = CHARACTER_CONTENT.races
CLASSES = CHARACTER_CONTENT.classes
ABILITY_LIBRARY = CHARACTER_CONTENT.ability_library
IMPLEMENTED_ABILITY_KEYS = CHARACTER_CONTENT.implemented_ability_keys
PASSIVE_ABILITY_BONUSES = CHARACTER_CONTENT.passive_ability_bonuses


def ability_key(name):
    """Return the canonical normalized key for an ability name."""

    return CHARACTER_CONTENT.ability_key(name)


def get_progression_ability_names(class_key, level):
    """Return progression ability names unlocked for a class at a given level."""

    return CHARACTER_CONTENT.get_progression_ability_names(class_key, level)


def split_unlocked_abilities(class_key, level):
    """Split unlocked progression abilities into combat actions and passive traits."""

    return CHARACTER_CONTENT.split_unlocked_abilities(class_key, level)


def get_passive_ability_bonuses(class_key, level):
    """Aggregate all passive bonuses unlocked for a class at a given level."""

    return CHARACTER_CONTENT.get_passive_ability_bonuses(class_key, level)


def xp_needed_for_next_level(level):
    """Return the XP needed to reach the next level, or None at cap."""

    return CHARACTER_CONTENT.xp_needed_for_next_level(level)
