"""Helpers for the Chapel of the Dawn Bell and its town blessing."""

from world.paladin_oaths import get_oath
from world.race_world_hooks import get_chapel_bonuses, get_chapel_rite_line

CHAPEL_ROOM_ID = "brambleford_chapel_dawn_bell"


def get_dawn_bell_rite(character):
    """Return any class-specific rite attached to the Dawn Bell blessing."""

    class_key = getattr(getattr(character, "db", None), "brave_class", None) or "warrior"
    if class_key == "cleric":
        return {
            "name": "Bellkeeper Benediction",
            "summary": "The chapel answers you as a custodian of its rites, lending stronger restoration and cleaner holy focus.",
            "lines": [
                "Cleric rite: your blessing carries stronger healing power and steadier sacred casting.",
                "Temples will become a deeper source of rites, blessings, and restoration for this class.",
            ],
        }
    if class_key == "paladin":
        oath = get_oath(getattr(getattr(character, "db", None), "brave_active_oath", None))
        oath_name = oath.get("name", "Oath Of The Bell")
        oath_summary = oath.get("summary", "You take the chapel's vigil on yourself, leaving with a harder ward and a stronger promise to hold for others.")
        oath_lines = list(oath.get("lines") or [])
        race_line = get_chapel_rite_line(character)
        if race_line:
            oath_lines.append(race_line)
        return {
            "name": oath_name,
            "summary": oath_summary,
            "lines": [
                f"Paladin rite: {oath_name} shapes how the Dawn Bell answers your vigil.",
                *oath_lines,
            ],
        }
    return {}


def is_chapel_room(room):
    """Whether the given room is the live chapel room."""

    return getattr(getattr(room, "db", None), "brave_room_id", None) == CHAPEL_ROOM_ID if room else False


def get_dawn_bell_bonuses(character):
    """Return class-aware blessing bonuses for the Dawn Bell."""

    class_key = getattr(getattr(character, "db", None), "brave_class", None) or "warrior"
    bonuses = {"max_hp": 8, "armor": 2, "accuracy": 2}

    if class_key == "cleric":
        bonuses.update({"spell_power": 2, "max_mana": 10, "healing_power": 3})
    elif class_key == "paladin":
        bonuses.update({"attack_power": 1, "spell_power": 1, "max_stamina": 6, "threat": 3, "armor": 3})
        oath = get_oath(getattr(getattr(character, "db", None), "brave_active_oath", None))
        for stat, value in (oath.get("blessing_bonuses", {}) or {}).items():
            bonuses[stat] = bonuses.get(stat, 0) + value
    elif class_key in {"mage", "druid"}:
        bonuses.update({"spell_power": 2, "max_mana": 8})
    else:
        bonuses.update({"attack_power": 2, "max_stamina": 6})

    for stat, value in get_chapel_bonuses(character).items():
        bonuses[stat] = bonuses.get(stat, 0) + value

    return bonuses


def get_active_blessing(character):
    """Return the active Dawn Bell blessing payload, if any."""

    blessing = dict(getattr(getattr(character, "db", None), "brave_chapel_blessing", None) or {})
    if not blessing:
        return {}

    blessing["name"] = blessing.get("name", "Dawn Bell Blessing")
    blessing["source"] = blessing.get("source", "Chapel of the Dawn Bell")
    blessing["duration"] = blessing.get("duration", "Until your next encounter ends.")
    blessing["bonuses"] = get_dawn_bell_bonuses(character)
    blessing["rite"] = get_dawn_bell_rite(character)
    return blessing


def apply_dawn_bell_blessing(character):
    """Apply the active chapel blessing to a character."""

    blessing = {
        "name": "Dawn Bell Blessing",
        "source": "Chapel of the Dawn Bell",
        "duration": "Until your next encounter ends.",
        "bonuses": get_dawn_bell_bonuses(character),
        "rite": get_dawn_bell_rite(character),
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
