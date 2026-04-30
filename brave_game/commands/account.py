"""Account-level startup and character-management commands for Brave."""

import re

from django.conf import settings

from world.browser_panels import send_webclient_event
from world.browser_views import build_connection_view, build_theme_view
from world.chargen import clear_chargen_state, get_chargen_state, has_chargen_progress, start_brave_chargen
from world.data.themes import THEMES, THEME_BY_KEY, normalize_theme_key

from evennia.commands.default import account as default_account
from evennia.commands.default import unloggedin as default_unloggedin
from evennia.commands.cmdhandler import CMD_LOGINSTART
from evennia.utils import logger, utils
from evennia.utils.evmenu import get_input

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)
WEB_PROTOCOLS = {"websocket", "ajax/comet", "webclient"}

THEME_OPTIONS = [(theme["key"], theme["name"]) for theme in THEMES]
THEME_ALIASES = {
    theme["key"]: {theme["key"], *(theme.get("aliases") or [])}
    for theme in THEMES
}

def _normalize_theme_query(value):
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _resolve_theme(query):
    normalized = _normalize_theme_query(query)
    if not normalized:
        return None

    for key, label in THEME_OPTIONS:
        aliases = {_normalize_theme_query(alias) for alias in THEME_ALIASES.get(key, {key})}
        aliases.add(_normalize_theme_query(label))
        if normalized in aliases:
            return key, label

    partial = []
    for key, label in THEME_OPTIONS:
        aliases = {_normalize_theme_query(alias) for alias in THEME_ALIASES.get(key, {key})}
        aliases.add(_normalize_theme_query(label))
        if any(normalized in alias for alias in aliases):
            partial.append((key, label))

    if len(partial) == 1:
        return partial[0]
    return None


def _is_web_session(session):
    protocol = (getattr(session, "protocol_key", "") or "").lower()
    return protocol in WEB_PROTOCOLS


def _render_connection_screen(session, *, screen="menu", error=None, username=""):
    if not _is_web_session(session):
        return
    send_webclient_event(session, session=session, brave_clear_all={})
    send_webclient_event(
        session,
        session=session,
        brave_view=build_connection_view(
            screen=screen,
            error=error,
            username=username,
            registration_enabled=settings.NEW_ACCOUNT_REGISTRATION_ENABLED,
        ),
    )


def _theme_event_payload(theme_key):
    theme = THEME_BY_KEY.get(normalize_theme_key(theme_key)) or THEMES[0]
    return {
        "theme": theme["key"],
        "font": theme["font_key"],
        "size": theme["font_scale"],
    }


def _playable_characters(account):
    return list(account.characters.all())


def _resolve_character_selection(account, query, allow_default=False):
    """Resolve a character by numeric slot or name."""

    characters = _playable_characters(account)
    if not characters:
        return None, "You don't have any characters yet. Use |wcreate|n to make one."

    if not query:
        if allow_default:
            if account.db._last_puppet and account.db._last_puppet in characters:
                return account.db._last_puppet, None
            if len(characters) == 1:
                return characters[0], None
        return None, "You must choose a character by number or name."

    query = query.strip()
    if query.isdigit():
        index = int(query) - 1
        if 0 <= index < len(characters):
            return characters[index], None
        return None, "There is no character in that slot."

    lowered = query.lower()
    exact = [character for character in characters if character.key.lower() == lowered]
    if len(exact) == 1:
        return exact[0], None

    partial = [character for character in characters if lowered in character.key.lower()]
    if len(partial) == 1:
        return partial[0], None
    if len(partial) > 1:
        return None, "That matches more than one character. Use the number instead."
    return None, "You do not have a character by that name."


def _release_existing_puppets_for_play(account, session, character):
    """Free any current puppet that would block entering the requested character."""

    if not account or not character or not hasattr(account, "get_all_puppets"):
        return

    current_session_puppet = getattr(session, "puppet", None)
    existing_puppets = list(account.get_all_puppets() or [])
    if current_session_puppet is character and existing_puppets == [character]:
        return
    if any(puppet is not character for puppet in existing_puppets) or (
        current_session_puppet and current_session_puppet is not character
    ):
        account.unpuppet_all()


class CmdBraveOOCLook(default_account.CmdOOCLook):
    """
    Show the Brave title screen.

    Usage:
      look
      menu
      title
      characters
    """

    key = "menu"
    aliases = ["title", "characters"]


class CmdBravePlay(default_account.CmdIC):
    """
    Enter the world as one of your characters.

    Usage:
      play <number or name>
      play
      ic <number or name>
    """

    key = "ic"
    aliases = ["play", "puppet"]

    def func(self):
        account = self.account
        character, error = _resolve_character_selection(account, self.args, allow_default=True)
        if error:
            self.msg(error)
            return
        _release_existing_puppets_for_play(account, self.session, character)
        self.args = character.key
        super().func()


class CmdBraveLogout(COMMAND_DEFAULT_CLASS):
    """
    Log out of the current account and return to the login screen.

    Usage:
      logout
    """

    key = "logout"
    aliases = ["log out"]
    locks = "cmd:pperm(Player)"
    help_category = "General"
    account_caller = True

    def func(self):
        session = self.session
        account = self.account
        if not session or not account:
            return

        if not _is_web_session(session):
            session.sessionhandler.disconnect(session, "Good bye! Disconnecting.")
            return

        session.account = None
        session.uid = None
        session.uname = ""
        session.puid = None
        session.puppet = None
        session.cmdset_storage = settings.CMDSET_UNLOGGEDIN
        session.cmdset.update(init_mode=True)
        session.sessionhandler.session_portal_partial_sync(
            {session.sessid: {"logged_in": False, "uid": None}}
        )

        _render_connection_screen(session, screen="menu")


class CmdBraveCreate(COMMAND_DEFAULT_CLASS):
    """
    Start or resume character creation.

    Usage:
      create
      new
      charcreate
    """

    key = "charcreate"
    aliases = ["create", "new", "chargen"]
    locks = "cmd:pperm(Player)"
    help_category = "General"
    account_caller = True

    def func(self):
        query = (self.args or "").strip().lower()
        if query in {"discard", "clear", "reset", "scrap"}:
            if not self.account.db.brave_chargen:
                self.msg("You do not have a saved character draft.")
                return
            clear_chargen_state(self.account)
            self.msg("Saved character draft discarded.")
            self.account.execute_cmd("look", session=self.session)
            return

        state = get_chargen_state(self.account)
        if not has_chargen_progress(self.account):
            if slot_error := self.account.check_available_slots():
                self.msg(slot_error)
                return
        start_brave_chargen(self.session)


class CmdBraveDelete(COMMAND_DEFAULT_CLASS):
    """
    Delete one of your characters.

    Usage:
      delete <number or name>
      chardelete <number or name>
    """

    key = "chardelete"
    aliases = ["delete"]
    locks = "cmd:pperm(Player)"
    help_category = "General"
    account_caller = True

    def func(self):
        raw_args = (self.args or "").strip()
        if not raw_args:
            self.msg("Usage: delete <number or name>")
            return

        tokens = raw_args.split()
        force_delete = False
        filtered_tokens = []
        for token in tokens:
            if token.lower() in {"--force", "--yes", "--confirm"}:
                force_delete = True
                continue
            filtered_tokens.append(token)

        query = " ".join(filtered_tokens).strip()
        if not query:
            self.msg("Usage: delete <number or name>")
            return

        character, error = _resolve_character_selection(self.account, query)
        if error:
            self.msg(error)
            return

        if not character.access(self.account, "delete"):
            self.msg("You do not have permission to delete this character.")
            return

        is_web = _is_web_session(self.session)

        def _delete_character():
            key = character.key
            self.account.unpuppet_all()
            self.account.characters.remove(character)
            character.delete()
            logger.log_sec(
                f"Character Deleted: {key} (Caller: {self.account}, IP: {self.session.address})."
            )
            if is_web:
                self.account.execute_cmd("look", session=self.session)
                return
            self.msg(f"Character '|w{key}|n' was permanently deleted.")
            self.account.execute_cmd("look", session=self.session)

        if is_web and force_delete:
            _delete_character()
            return

        def _callback(caller, prompt, result):
            if (result or "").strip().lower() != "yes":
                self.msg("Deletion was aborted.")
                return
            _delete_character()

        prompt = (
            f"|rThis will permanently destroy '{character.key}'. This cannot be undone.|n "
            "Type |wyes|n to confirm."
        )
        get_input(self.account, prompt, _callback, session=self.session)


class CmdBraveTheme(COMMAND_DEFAULT_CLASS):
    """
    Change the webclient theme for this browser session.

    Usage:
      theme
      theme <name>
      theme reset

    Examples:
      theme
      theme classic
      theme signalglass
      theme terminal
      theme campfire
      theme journal
      theme atlas
    """

    key = "theme"
    locks = "cmd:pperm(Player)"
    help_category = "General"
    account_caller = True

    def _show_theme_screen(self):
        if not _is_web_session(self.session):
            lines = [
                "Available themes for this browser:",
                ", ".join(f"|w{label}|n" for _, label in THEME_OPTIONS),
                "Use |wtheme <name>|n to switch themes.",
                "Use |wtheme reset|n to return to the default theme.",
                "The default is |wBrave Classic|n.",
                "Each theme includes its own font and reading size.",
            ]
            self.msg("\n".join(lines))
            return

        current_theme = normalize_theme_key(getattr(getattr(self.session, "ndb", None), "brave_theme", None))
        self.msg(brave_clear={}, session=self.session)
        self.msg(brave_view=build_theme_view(current_theme), session=self.session)

    def func(self):
        query = (self.args or "").strip()
        is_web = _is_web_session(self.session)

        if not query:
            self._show_theme_screen()
            return

        if _normalize_theme_query(query) in {"reset", "default"}:
            key, label = THEME_OPTIONS[0]
            self.session.ndb.brave_theme = key
            self.msg(brave_theme=_theme_event_payload(key), session=self.session)
            if is_web:
                self.msg(brave_view=build_theme_view(key), session=self.session)
                return
            theme = THEME_BY_KEY[key]
            self.msg(
                f"Theme reset to |w{label}|n for this browser."
                f" Typeface: |w{theme['font_name']}|n at |w{theme['font_scale']}|n scale."
            )
            return

        resolved = _resolve_theme(query)
        if not resolved:
            self.msg("Unknown theme. Use |wtheme|n to browse the available options.")
            return

        key, label = resolved
        self.session.ndb.brave_theme = key
        self.msg(brave_theme=_theme_event_payload(key), session=self.session)
        if is_web:
            self.msg(brave_view=build_theme_view(key), session=self.session)
            return
        theme = THEME_BY_KEY[key]
        self.msg(
            f"Theme changed to |w{label}|n for this browser."
            f" Typeface: |w{theme['font_name']}|n at |w{theme['font_scale']}|n scale."
        )


class CmdBraveUnconnectedLook(default_unloggedin.CmdUnconnectedLook):
    """
    Show the connection screen.

    Browser sessions already render a native pre-login screen client-side, so
    they should not also receive the legacy text transcript.
    """

    key = CMD_LOGINSTART
    aliases = ["look", "l"]

    def func(self):
        if _is_web_session(self.caller):
            _render_connection_screen(self.caller)
            return
        super().func()


class CmdBraveUnconnectedConnect(default_unloggedin.CmdUnconnectedConnect):
    """Connect to Brave while preserving browser-native login states."""

    def func(self):
        session = self.caller
        address = session.address

        parts = [part.strip() for part in re.split(r"\"", self.args) if part.strip()]
        if len(parts) == 1:
            parts = parts[0].split(None, 1)
            if len(parts) == 1 and parts[0].lower() == "guest":
                return super().func()

        if len(parts) != 2:
            if _is_web_session(session):
                _render_connection_screen(
                    session,
                    screen="signin",
                    error="Enter both your username and password to sign in.",
                )
                return
            session.msg("\n\r Usage (without <>): connect <name> <password>")
            return

        account_class = utils.class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
        username, password = parts
        account, errors = account_class.authenticate(
            username=username,
            password=password,
            ip=address,
            session=session,
        )
        if account:
            session.sessionhandler.login(session, account)
            return

        error_text = "\n".join(errors) if errors else "Unable to sign in with those credentials."
        if _is_web_session(session):
            _render_connection_screen(session, screen="signin", error=error_text, username=username)
            return
        session.msg(f"|R{error_text}|n")


class CmdBraveUnconnectedCreate(default_unloggedin.CmdUnconnectedCreate):
    """Create an account with browser-native validation and auto-login."""

    def at_pre_cmd(self):
        if not settings.NEW_ACCOUNT_REGISTRATION_ENABLED:
            if _is_web_session(self.caller):
                _render_connection_screen(
                    self.caller,
                    screen="create",
                    error="New account registration is currently disabled.",
                )
            else:
                self.msg("Registration is currently disabled.")
            return True
        return super().at_pre_cmd()

    def func(self):
        session = self.caller
        args = (self.args or "").strip()
        address = session.address
        account_class = utils.class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        parts = [part.strip() for part in re.split(r"\"", args) if part.strip()]
        if len(parts) == 1:
            parts = parts[0].split(None)

        if len(parts) not in {2, 3}:
            error = "Enter a username, password, and matching confirmation password."
            if _is_web_session(session):
                _render_connection_screen(session, screen="create", error=error)
                return
            self.msg(
                "\n Usage (without <>): create <name> <password> <confirm password>"
                "\nIf <name> or <password> contains spaces, enclose it in double quotes."
            )
            return

        username = parts[0]
        password = parts[1]
        password_confirm = parts[2] if len(parts) == 3 else parts[1]
        normalized_username = account_class.normalize_username(username)

        if password != password_confirm:
            error = "Password confirmation did not match."
            if _is_web_session(session):
                _render_connection_screen(
                    session,
                    screen="create",
                    error=error,
                    username=normalized_username,
                )
                return
            self.msg(error)
            return

        account, errors = account_class.create(
            username=normalized_username,
            password=password,
            ip=address,
            session=session,
        )
        if not account:
            error_text = "\n".join(errors) if errors else "Unable to create that account right now."
            if _is_web_session(session):
                _render_connection_screen(
                    session,
                    screen="create",
                    error=error_text,
                    username=normalized_username,
                )
                return
            self.msg(f"|R{error_text}|n")
            return

        session.msg(f"|gAccount created.|n Welcome, |c{account.key}|n.")
        session.sessionhandler.login(session, account)
