"""Registry-backed constants shared by browser view builders."""

from world.content import get_content_registry


CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
ITEM_CONTENT = CONTENT.items
QUEST_CONTENT = CONTENT.quests
SYSTEMS_CONTENT = CONTENT.systems
ENCOUNTER_CONTENT = CONTENT.encounters

ABILITY_LIBRARY = CHARACTER_CONTENT.ability_library
CLASSES = CHARACTER_CONTENT.classes
PASSIVE_ABILITY_BONUSES = CHARACTER_CONTENT.passive_ability_bonuses
RACES = CHARACTER_CONTENT.races
VERTICAL_SLICE_CLASSES = CHARACTER_CONTENT.vertical_slice_classes
ability_key = CHARACTER_CONTENT.ability_key
split_unlocked_abilities = CHARACTER_CONTENT.split_unlocked_abilities
xp_needed_for_next_level = CHARACTER_CONTENT.xp_needed_for_next_level

EQUIPMENT_SLOTS = ITEM_CONTENT.equipment_slots
ITEM_TEMPLATES = ITEM_CONTENT.item_templates
get_item_category = ITEM_CONTENT.get_item_category
get_item_use_profile = ITEM_CONTENT.get_item_use_profile

QUESTS = QUEST_CONTENT.quests
STARTING_QUESTS = QUEST_CONTENT.starting_quests
get_quest_region = QUEST_CONTENT.get_quest_region
group_quest_keys_by_region = QUEST_CONTENT.group_quest_keys_by_region

ENEMY_TEMPLATES = ENCOUNTER_CONTENT.enemy_templates

COOKING_RECIPES = SYSTEMS_CONTENT.cooking_recipes
format_ingredient_list = SYSTEMS_CONTENT.format_ingredient_list
PORTALS = SYSTEMS_CONTENT.portals
PORTAL_STATUS_LABELS = SYSTEMS_CONTENT.portal_status_labels
