"""Compatibility accessors for Brave quest content."""

from world.content.registry import get_content_registry


CONTENT = get_content_registry()
QUEST_CONTENT = CONTENT.quests

STARTING_QUESTS = QUEST_CONTENT.starting_quests
QUEST_REGIONS = QUEST_CONTENT.quest_regions
QUESTS = QUEST_CONTENT.quests


def get_quest_region(quest_key):
    """Return the broad region label for a quest."""

    return QUEST_CONTENT.get_quest_region(quest_key)


def group_quest_keys_by_region(quest_keys):
    """Group quest keys by region while preserving first-seen order."""

    return QUEST_CONTENT.group_quest_keys_by_region(quest_keys)
