"""Brave character creation flow."""

import re

from typeclasses.characters import Character
from world.browser_panels import send_webclient_event
from world.content import get_content_registry
from world.resonance import get_stat_label

from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import dedent

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters

_VALID_NAME = re.compile(r"^[A-Za-z][A-Za-z' -]{1,23}$")
WEB_PROTOCOLS = {"websocket", "ajax/comet", "webclient"}


PRIMARY_STAT_ORDER = ("strength", "agility", "intellect", "spirit", "vitality")


def _format_bonus_line(bonuses):
    parts = []
    for stat in PRIMARY_STAT_ORDER:
        amount = int((bonuses or {}).get(stat) or 0)
        if amount:
            parts.append(f"+{amount} {get_stat_label(stat)}")
    return ", ".join(parts)


def _is_web_session(session):
    protocol = (getattr(session, "protocol_key", "") or "").lower()
    return protocol in WEB_PROTOCOLS


class BraveChargenMenu(EvMenu):
    """EvMenu variant that suppresses legacy menu text for browser sessions."""

    def msg(self, txt):
        if _is_web_session(self.caller):
            return
        super().msg(txt)


def get_chargen_state(account):
    """Return the current chargen state for this account."""

    state = dict(account.db.brave_chargen or {})
    state.setdefault("step", "menunode_welcome")
    state.setdefault("name", None)
    state.setdefault("race", None)
    state.setdefault("class", None)
    return state


def set_chargen_state(account, **updates):
    """Persist chargen state for this account."""

    state = get_chargen_state(account)
    state.update(updates)
    account.db.brave_chargen = state
    return state


def clear_chargen_state(account):
    """Clear any saved chargen progress for this account."""

    account.db.brave_chargen = None


def has_chargen_progress(account):
    """Whether the account has a meaningful saved chargen draft."""

    raw_state = dict(account.db.brave_chargen or {})
    return any(raw_state.get(field) for field in ("name", "race", "class"))


def get_next_chargen_step(state):
    """Return the next required chargen step for the given draft state."""

    if not state.get("name"):
        return "menunode_choose_name"
    if not state.get("race"):
        return "menunode_choose_race"
    if not state.get("class"):
        return "menunode_choose_class"
    return "menunode_confirm"


def get_resume_chargen_step(account):
    """Return the best step to resume this account's chargen flow."""

    state = get_chargen_state(account)
    if not has_chargen_progress(account):
        return "menunode_welcome"
    return get_next_chargen_step(state)


def _clean_ansi(text):
    """Remove lightweight ANSI markers from brief chargen errors for browser UI."""

    return (text or "").replace("|r", "").replace("|g", "").replace("|y", "").replace("|w", "").replace("|c", "").replace("|n", "").strip()


def _push_chargen_view(caller, state, *, error=None):
    """Update the browser-native chargen view for the current session."""

    from world.browser_views import build_chargen_view

    send_webclient_event(
        caller,
        session=caller,
        brave_view=build_chargen_view(caller.account, state, error=_clean_ansi(error)),
    )


def _summarize_state(state):
    race_name = CHARACTER_CONTENT.races.get(state.get("race"), {}).get("name", "-")
    class_name = CHARACTER_CONTENT.classes.get(state.get("class"), {}).get("name", "-")
    return "\n".join(
        [
            f"Name: |c{state.get('name') or '-'}|n",
            f"Race: |c{race_name}|n",
            f"Class: |c{class_name}|n",
        ]
    )


def _finish_chargen(caller, menu):
    """Handle leaving the character creator."""

    account = caller.account
    account.execute_cmd("look", session=caller)


def start_brave_chargen(session):
    """Start or resume the Brave chargen menu for this session."""

    account = session.account
    state = get_chargen_state(account)
    startnode = get_resume_chargen_step(account)
    if state.get("step") != startnode:
        state = set_chargen_state(account, step=startnode)
    send_webclient_event(session, session=session, brave_clear={})
    _push_chargen_view(session, state)
    BraveChargenMenu(
        session,
        __name__,
        startnode=startnode,
        cmd_on_exit=_finish_chargen,
        auto_look=False,
        auto_help=True,
        auto_quit=True,
        persistent=False,
    )


def menunode_welcome(caller, raw_string=None, **kwargs):
    """Chargen introduction / resume node."""

    account = caller.account
    state = set_chargen_state(account, step="menunode_welcome")
    _push_chargen_view(caller, state)
    slots_left = account.get_available_character_slots()
    slot_text = "unlimited" if slots_left is None else str(slots_left)
    next_step = get_next_chargen_step(state)
    next_label = {
        "menunode_choose_name": "Choose a name",
        "menunode_choose_race": "Choose a race",
        "menunode_choose_class": "Choose a class",
        "menunode_confirm": "Review and create your character",
    }[next_step]

    text = dedent(
        f"""\
        |wBrave Character Creation|n

        Build a new adventurer for account |c{account.key}|n.

        Open character slots: |w{slot_text}|n

        Current draft:
        {_summarize_state(state)}

        Next step:
        |w{next_label}|n
        """
    )

    options = [
        {
            "key": ("continue", "begin", "resume", "1"),
            "desc": next_label,
            "goto": (_continue_chargen, {}),
        }
    ]
    return text, options


def _continue_chargen(caller, raw_string=None, **kwargs):
    """Continue the chargen flow from the next required step."""

    state = get_chargen_state(caller.account)
    return get_next_chargen_step(state)


def menunode_choose_name(caller, raw_string=None, error=None, **kwargs):
    """Prompt for character name."""

    account = caller.account
    state = set_chargen_state(account, step="menunode_choose_name")
    _push_chargen_view(caller, state, error=error)
    prompt = error or "Enter a character name."
    text = dedent(
        f"""\
        |wChoose a Name|n

        {prompt}

        Rules:
          - 2 to 24 characters
          - letters, spaces, apostrophes, and hyphens only
          - must be unique across all characters

        Current draft:
        {_summarize_state(state)}
        """
    )
    options = (
        {"key": "_default", "goto": _set_character_name},
        {"key": ("back", "b"), "desc": "Return to the chargen overview.", "goto": "menunode_welcome"},
    )
    return text, options


def _set_character_name(caller, raw_string, **kwargs):
    """Validate and save a character name."""

    account = caller.account
    name = " ".join((raw_string or "").strip().split())
    name = account.normalize_username(name)
    if not _VALID_NAME.match(name):
        return "menunode_choose_name", {"error": "|rThat name format is not allowed.|n"}
    if Character.objects.filter_family(db_key__iexact=name).exists():
        return "menunode_choose_name", {"error": "|rThat character name is already taken.|n"}

    set_chargen_state(account, name=name, step="menunode_choose_race")
    return "menunode_choose_race"


def menunode_choose_race(caller, raw_string=None, **kwargs):
    """Pick a starting race."""

    account = caller.account
    state = set_chargen_state(account, step="menunode_choose_race")
    _push_chargen_view(caller, state)
    text = dedent(
        f"""\
        |wChoose a Race|n

        {_summarize_state(state)}
        """
    )
    options = []
    for race_key, race_data in CHARACTER_CONTENT.races.items():
        trait_line = _format_bonus_line(race_data.get("trait_bonuses", {}))
        desc = f"{race_data['name']}  |  {race_data['summary']}  |  Perk: {race_data['perk']}"
        if trait_line:
            desc += f"  |  Traits: {trait_line}"
        options.append(
            {
                "key": (race_key, race_data["name"].lower()),
                "desc": desc,
                "goto": (_set_race, {"race_key": race_key}),
            }
        )
    options.append(
        {"key": ("back", "b"), "desc": "Go back to name selection.", "goto": "menunode_choose_name"}
    )
    return text, options


def _set_race(caller, raw_string=None, race_key=None, **kwargs):
    """Save race selection."""

    set_chargen_state(caller.account, race=race_key, step="menunode_choose_class")
    return "menunode_choose_class"


def menunode_choose_class(caller, raw_string=None, **kwargs):
    """Pick a starting class."""

    account = caller.account
    state = set_chargen_state(account, step="menunode_choose_class")
    _push_chargen_view(caller, state)
    text = dedent(
        f"""\
        |wChoose a Class|n

        These are the currently playable classes in the Brave slice.

        {_summarize_state(state)}
        """
    )
    options = []
    for class_key in CHARACTER_CONTENT.vertical_slice_classes:
        class_data = CHARACTER_CONTENT.classes[class_key]
        opening = ", ".join(ability for level, ability in class_data["progression"] if level == 1)
        followup = next((ability for level, ability in class_data["progression"] if level > 1), None)
        desc = f"{class_data['name']}  |  {class_data['role']}  |  {class_data['summary']}  |  Starts with: {opening}"
        if followup:
            desc += f"  |  First unlock: {followup}"
        options.append(
            {
                "key": (class_key, class_data["name"].lower()),
                "desc": desc,
                "goto": (_set_class, {"class_key": class_key}),
            }
        )
    options.append(
        {"key": ("back", "b"), "desc": "Go back to race selection.", "goto": "menunode_choose_race"}
    )
    return text, options


def _set_class(caller, raw_string=None, class_key=None, **kwargs):
    """Save class selection."""

    set_chargen_state(caller.account, **{"class": class_key, "step": "menunode_confirm"})
    return "menunode_confirm"


def menunode_confirm(caller, raw_string=None, error=None, **kwargs):
    """Review and finalize the new character."""

    account = caller.account
    state = set_chargen_state(account, step="menunode_confirm")
    _push_chargen_view(caller, state, error=error)
    missing = [field for field in ("name", "race", "class") if not state.get(field)]
    if missing:
        return "menunode_welcome", {}

    text = dedent(
        f"""\
        |wConfirm Character|n

        {_summarize_state(state)}

        Race perk: |c{CHARACTER_CONTENT.races[state['race']]['perk']}|n
        Class role: |c{CHARACTER_CONTENT.classes[state['class']]['role']}|n

        {error or 'Choose whether to create this character or go back and edit it.'}
        """
    )
    options = (
        {"key": ("finish", "create", "confirm", "1"), "desc": "Create this character", "goto": _finalize_character},
        {"key": ("back", "b"), "desc": "Go back to class selection.", "goto": "menunode_choose_class"},
    )
    return text, options


def _finalize_character(caller, raw_string=None, **kwargs):
    """Create the character from the saved chargen state."""

    account = caller.account
    state = get_chargen_state(account)

    if not all(state.get(field) for field in ("name", "race", "class")):
        return "menunode_confirm", {"error": "|rYour character draft is incomplete.|n"}

    new_character, errors = account.create_character(
        key=state["name"],
        description=Character.default_description,
        ip=caller.address,
    )
    if errors or not new_character:
        message = "\n".join(errors) if errors else "|rCharacter creation failed.|n"
        return "menunode_confirm", {"error": message}

    new_character.set_brave_race(state["race"])
    new_character.set_brave_class(state["class"])
    new_character.restore_resources()
    clear_chargen_state(account)
    caller.msg(f"|gCharacter created.|n Returning to your character list with |c{new_character.key}|n ready to play.")
    return "menunode_exit"


def menunode_exit(caller, raw_string=None, **kwargs):
    """Exit node."""

    return "", None
