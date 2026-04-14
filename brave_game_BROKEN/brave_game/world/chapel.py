"""Helpers for the Chapel of the Dawn Bell and its town blessing."""

CHAPEL_ROOM_ID = "brambleford_chapel_dawn_bell"


def is_chapel_room(room):
    """Whether the given room is the live chapel room."""

    return getattr(getattr(room, "db", None), "brave_room_id", None) == CHAPEL_ROOM_ID if room else False


def get_dawn_bell_bonuses(character):
    """Return class-aware blessing bonuses for the Dawn Bell."""

    class_key = getattr(getattr(character, "db", None), "brave_class", None) or "warrior"
    bonuses = {"max_hp": 8, "armor": 2, "accuracy": 2}

    if class_key in {"cleric", "mage", "druid"}:
        bonuses.update({"spell_power": 2, "max_mana": 8})
    elif class_key == "paladin":
        bonuses.update({"attack_power": 1, "spell_power": 1, "max_stamina": 6, "threat": 2})
    else:
        bonuses.update({"attack_power": 2, "max_stamina": 6})

    return bonuses


def get_active_blessing(character):
    """Return the active Dawn Bell blessing payload, if any."""

    blessing = dict(getattr(getattr(character, "db", None), "brave_chapel_blessing", None) or {})
    if not blessing:
        return {}

    blessing.setdefault("name", "Dawn Bell Blessing")
    blessing.setdefault("source", "Chapel of the Dawn Bell")
    blessing.setdefault("duration", "Until your next encounter ends.")
    blessing.setdefault("bonuses", get_dawn_bell_bonuses(character))
    return blessing


def apply_dawn_bell_blessing(character):
    """Apply the active chapel blessing to a character."""

    blessing = {
        "name": "Dawn Bell Blessing",
        "source": "Chapel of the Dawn Bell",
        "duration": "Until your next encounter ends.",
        "bonuses": get_dawn_bell_bonuses(character),
    }
    character.db.brave_chapel_blessing = blessing
    character.recalculate_stats()
    return blessing


def clear_dawn_bell_blessing(character):
    """Clear the active chapel blessing, returning whether one existed."""

    if not getattr(getattr(character, "db", None), "brave_chapel_blessing", None):
        return False
    character.db.brave_chapel_blessing = {}
    character.recalculate_stats()
    return True
