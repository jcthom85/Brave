"""Compatibility accessors for Brave item content."""

from world.content.registry import get_content_registry


CONTENT = get_content_registry()
ITEM_CONTENT = CONTENT.items

EQUIPMENT_SLOTS = ITEM_CONTENT.equipment_slots
ITEM_CLASS_REQUIREMENTS = ITEM_CONTENT.item_class_requirements
ITEM_TEMPLATES = ITEM_CONTENT.item_templates
STARTER_CONSUMABLES = ITEM_CONTENT.starter_consumables
STARTER_LOADOUTS = ITEM_CONTENT.starter_loadouts
BONUS_LABELS = ITEM_CONTENT.bonus_labels
RARITIES = ITEM_CONTENT.rarities


def _normalize_item_token(value):
    """Normalize free-text item queries for fuzzy matching."""

    return ITEM_CONTENT._normalize_item_token(value)


def get_item(template_id):
    """Return an item template by id."""

    return ITEM_CONTENT.get(template_id)


def get_item_category(item_or_template):
    """Return the inventory category an item should be grouped under."""

    return ITEM_CONTENT.get_item_category(item_or_template)


def get_item_use_profile(item_or_template, *, context=None):
    """Return normalized use metadata for a consumable item."""

    return ITEM_CONTENT.get_item_use_profile(item_or_template, context=context)


def get_item_rarity_key(item_or_template):
    """Return the normalized rarity key for an item template."""

    return ITEM_CONTENT.get_item_rarity_key(item_or_template)


def get_item_rarity(item_or_template):
    """Return rarity metadata for an item template."""

    return ITEM_CONTENT.get_item_rarity(item_or_template)


def get_item_rarity_label(item_or_template):
    """Return the display rarity label for an item template."""

    return ITEM_CONTENT.get_item_rarity_label(item_or_template)


def get_item_rarity_tone(item_or_template):
    """Return the UI chip tone for an item template rarity."""

    return ITEM_CONTENT.get_item_rarity_tone(item_or_template)


def get_item_rarity_icon(item_or_template):
    """Return the icon role for an item template rarity."""

    return ITEM_CONTENT.get_item_rarity_icon(item_or_template)


def is_consumable_item(item_or_template, *, context=None):
    """Whether an item exposes consumable-use metadata."""

    return ITEM_CONTENT.is_consumable_item(item_or_template, context=context)


def match_inventory_item(character, query, *, context=None, category=None, verb=None):
    """Find a carried inventory item by template id or fuzzy display name."""

    return ITEM_CONTENT.match_inventory_item(
        character,
        query,
        context=context,
        category=category,
        verb=verb,
    )


def format_bonus_summary(item_data):
    """Return a compact bonus string for an item template."""

    return ITEM_CONTENT.format_bonus_summary(item_data)


def get_item_allowed_classes(item_or_template):
    """Return the allowed class list for a piece of equipment, if authored."""

    return ITEM_CONTENT.get_item_allowed_classes(item_or_template)


def is_equipment_allowed_for_class(item_or_template, class_key):
    """Whether a class can equip the given item."""

    return ITEM_CONTENT.is_equipment_allowed_for_class(item_or_template, class_key)


def format_allowed_class_summary(item_or_template):
    """Return a readable allowed-class note for one item."""

    return ITEM_CONTENT.format_allowed_class_summary(item_or_template)
