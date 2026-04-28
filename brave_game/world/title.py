"""Text helpers for Brave's connection and account title screens."""

from world.content import get_content_registry

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
CLASSES = CHARACTER_CONTENT.classes
RACES = CHARACTER_CONTENT.races

BRAVE_WORDMARK = "|wBRAVE|n"


def _brand_header():
    return BRAVE_WORDMARK


def build_connection_screen():
    """Return the unlogged-in connection screen."""

    lines = [
        _brand_header(),
        "",
        "|wconnect <username> <password>|n",
        "  Sign in to an existing account.",
        "|wcreate <username> <password>|n",
        "  Create a new account. Character creation happens after login.",
        "",
        "|whelp|n for more options.",
    ]
    return "\n".join(lines)


def _character_location(character):
    if character.location:
        return character.location.key
    return ""


def format_character_line(character, index, *, last_played=False):
    """Format one character entry for the account title screen."""

    character.ensure_brave_character()
    race_name = RACES[character.db.brave_race]["name"]
    class_name = CLASSES[character.db.brave_class]["name"]
    last_tag = "  |  |yLast played|n" if last_played else ""
    location = _character_location(character)
    location_part = f"  | {location}" if location else ""
    return (
        f"|w{index}.|n |c{character.key}|n"
        f"  | {race_name} {class_name}"
        f"  | Level {character.db.brave_level}"
        f"{location_part}"
        f"{last_tag}"
    )


def build_account_title_screen(account, session=None):
    """Return the OOC title screen for a logged-in account."""

    from world.chargen import has_chargen_progress

    characters = list(account.characters.all())
    max_slots = account.get_character_slots()
    slot_text = "unlimited" if max_slots is None else str(max_slots)
    available_slots = account.get_available_character_slots()
    available_text = "unlimited" if available_slots is None else str(available_slots)
    pending = dict(account.db.brave_chargen or {})

    lines = [
        _brand_header(),
        "",
        f"Account: |c{account.key}|n",
        f"Characters: |w{len(characters)}|n / |w{slot_text}|n"
        f"  |  Open slots: |w{available_text}|n",
        "",
        "|wCommands|n",
        "  |wplay <number or name>|n  Enter the world with one of your characters.",
        "  |wcreate|n                Start or resume character creation.",
        "  |wdelete <number or name>|n Remove a character permanently.",
        "  |wtheme [name]|n          Browse or change this browser's theme.",
        "  |wlook|n                  Redraw this title screen.",
        "  |wquit|n                  Disconnect from Brave.",
    ]

    if has_chargen_progress(account):
        lines.extend(
            [
                "",
                "|yCharacter creation in progress|n",
                f"  Name: {pending.get('name') or '-'}",
                f"  Race: {RACES.get(pending.get('race'), {}).get('name', '-')}",
                f"  Class: {CLASSES.get(pending.get('class'), {}).get('name', '-')}",
                "  Use |wcreate|n to resume.",
            ]
        )

    lines.append("")
    lines.append("|wYour Characters|n")
    if not characters:
        lines.append("  No characters yet. Use |wcreate|n to make your first adventurer.")
    else:
        last_played = account.db._last_puppet if account.db._last_puppet in characters else None
        for index, character in enumerate(characters, start=1):
            lines.append(
                f"  {format_character_line(character, index, last_played=bool(last_played and character.id == last_played.id))}"
            )

    return "\n".join(lines)
