"""Arcade cabinet commands and score submission flow."""

import secrets
import time

from world.arcade import (
    format_arcade_score,
    get_personal_best,
    get_reward_definition,
    resolve_arcade_game_query,
    submit_arcade_score,
)
from world.browser_panels import send_webclient_event
from world.browser_views import build_arcade_play_view, build_arcade_view
from world.data.arcade import ARCADE_GAMES
from world.screen_text import format_entry, render_screen, wrap_text

from .brave import BraveCharacterCommand, _stack_blocks


def _format_arcade_menu_screen(cabinet, character, focus_game=None):
    """Render a text fallback for a cabinet menu."""

    available_games = [game_key for game_key in cabinet.get_available_games() if game_key in ARCADE_GAMES]
    selected_game = focus_game if focus_game in available_games else (available_games[0] if available_games else None)

    game_blocks = []
    for game_key in available_games:
        definition = ARCADE_GAMES[game_key]
        reward = get_reward_definition(cabinet, game_key)
        details = [
            f"{cabinet.get_game_price(game_key)} silver to play",
            definition.get("score_summary", ""),
        ]
        if reward.get("threshold", 0) and reward.get("item_name"):
            details.append(
                f"Prize at {format_arcade_score(reward['threshold'])}: {reward['item_name']} "
                f"(best {format_arcade_score(get_personal_best(character, cabinet, game_key))})"
            )
        game_blocks.append(format_entry(definition["name"], details=[line for line in details if line], summary=definition.get("summary")))

    score_lines = []
    if selected_game:
        leaderboard = cabinet.get_leaderboard(selected_game)
        if leaderboard:
            for index, entry in enumerate(leaderboard, start=1):
                score_lines.extend(
                    wrap_text(
                        f"{index}. {entry.get('name', 'Unknown')} · {format_arcade_score(entry.get('score', 0))}",
                        indent="  ",
                    )
                )
        else:
            score_lines.append("  Nobody has claimed this board yet.")

    instruction_lines = []
    if selected_game:
        for line in ARCADE_GAMES[selected_game].get("instructions", []):
            instruction_lines.extend(wrap_text(line, indent="  "))

    return render_screen(
        "Arcade",
        subtitle=cabinet.key,
        sections=[
            ("Games", _stack_blocks(game_blocks) if game_blocks else ["  This cabinet is dark right now."]),
            ("Local Scores", score_lines or ["  No scores posted yet."]),
            ("Controls", instruction_lines or ["  Use the webclient to play this cabinet."]),
        ],
    )


def _format_arcade_play_screen(cabinet, game_key):
    """Render a text fallback for launching a cabinet."""

    definition = ARCADE_GAMES[game_key]
    return render_screen(
        definition["name"],
        subtitle=cabinet.key,
        sections=[
            ("Cabinet", ["  The machine hums to life."]),
            ("Controls", [*["  " + line for line in definition.get("instructions", [])], "  Press q to quit."]),
        ],
    )


class CmdArcade(BraveCharacterCommand):
    """
    Browse or play a local arcade cabinet.

    Usage:
      arcade
      arcade <cabinet>
      arcade scores [game]
      arcade play <game>
      arcade quit
    """

    key = "arcade"
    aliases = ["cabinet"]
    help_category = "Brave"

    def _remember_cabinet(self, character, cabinet):
        character.ndb.brave_arcade_last_cabinet = getattr(cabinet.db, "brave_entity_id", None) or cabinet.id

    def _resolve_cabinet(self, character, query=None):
        cabinets = self.get_local_entities(character, kind="arcade")
        if query:
            match, _ = self.find_local_entity(character, query, kind="arcade")
            if isinstance(match, list):
                self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in match))
                return None
            return match

        remembered = getattr(character.ndb, "brave_arcade_last_cabinet", None)
        if remembered:
            for cabinet in cabinets:
                if cabinet.id == remembered or getattr(cabinet.db, "brave_entity_id", None) == remembered:
                    return cabinet

        if len(cabinets) == 1:
            return cabinets[0]
        if not cabinets:
            self.msg("There is no playable arcade cabinet here.")
            return None
        self.msg("There are multiple cabinets here. Open one by name with |warcade <cabinet>|n.")
        return None

    def _show_menu(self, character, cabinet, focus_game=None):
        self._remember_cabinet(character, cabinet)
        screen = _format_arcade_menu_screen(cabinet, character, focus_game=focus_game)
        self.scene_msg(screen, view=build_arcade_view(character, cabinet, focus_game=focus_game))

    def _quit_arcade(self, character):
        session_data = getattr(character.ndb, "brave_arcade_session", None)
        if not session_data:
            self.msg("You are not currently on a cabinet.")
            return

        session = self.get_web_session()
        if session:
            send_webclient_event(character, session=session, brave_arcade_done={})
        character.ndb.brave_arcade_session = None
        self.msg("You step away from the cabinet.")
        character.execute_cmd("look", session=self.session)

    def func(self):
        character = self.get_character()
        if not character:
            return

        raw = (self.args or "").strip()
        query = raw.lower()
        if query == "quit":
            self._quit_arcade(character)
            return

        if query.startswith("play "):
            cabinet = self._resolve_cabinet(character)
            if not cabinet:
                return
            if character.get_active_encounter():
                self.msg("You cannot lean into a cabinet while a fight is still on you.")
                return
            session = self.get_web_session()
            if not session:
                self.msg("The cabinets only light up properly in the webclient.")
                return

            game_query = raw[5:].strip()
            match, options = resolve_arcade_game_query(game_query, cabinet.get_available_games())
            if isinstance(match, list):
                names = ", ".join(ARCADE_GAMES[game_key]["name"] for game_key in match)
                self.msg("Be more specific. That could mean: " + names)
                return
            if not match:
                if options:
                    names = ", ".join(ARCADE_GAMES[game_key]["name"] for game_key in options)
                    self.msg(f"That cabinet currently offers: {names}")
                else:
                    self.msg("That cabinet is dark right now.")
                return

            price = cabinet.get_game_price(match)
            if (character.db.brave_silver or 0) < price:
                self.msg(f"You need {price} silver to wake that cabinet up.")
                return

            character.db.brave_silver = max(0, (character.db.brave_silver or 0) - price)
            self._remember_cabinet(character, cabinet)
            nonce = secrets.token_hex(8)
            character.ndb.brave_arcade_session = {
                "nonce": nonce,
                "cabinet_id": getattr(cabinet.db, "brave_entity_id", None) or cabinet.id,
                "game_key": match,
                "started_at": time.time(),
            }

            screen = _format_arcade_play_screen(cabinet, match)
            self.scene_msg(screen, view=build_arcade_play_view(character, cabinet, match))
            send_webclient_event(
                character,
                session=session,
                brave_arcade={
                    "game": match,
                    "title": ARCADE_GAMES[match]["name"],
                    "nonce": nonce,
                    "submit_prefix": f"arcade_submit {nonce}",
                    "quit_command": "arcade quit",
                },
            )
            return

        if query == "scores" or query.startswith("scores "):
            cabinet = self._resolve_cabinet(character)
            if not cabinet:
                return
            focus_query = raw[7:].strip() if len(raw) > 6 else ""
            focus_game = None
            if focus_query:
                match, options = resolve_arcade_game_query(focus_query, cabinet.get_available_games())
                if isinstance(match, list):
                    names = ", ".join(ARCADE_GAMES[game_key]["name"] for game_key in match)
                    self.msg("Be more specific. That could mean: " + names)
                    return
                if not match:
                    if options:
                        names = ", ".join(ARCADE_GAMES[game_key]["name"] for game_key in options)
                        self.msg(f"That cabinet currently offers: {names}")
                    else:
                        self.msg("That cabinet is dark right now.")
                    return
                focus_game = match
            self._show_menu(character, cabinet, focus_game=focus_game)
            return

        cabinet = self._resolve_cabinet(character, query=raw or None)
        if not cabinet:
            return
        self._show_menu(character, cabinet)


class CmdArcadeSubmit(BraveCharacterCommand):
    """Internal score submission command used by the webclient arcade runtime."""

    key = "arcade_submit"
    aliases = []
    help_category = "Brave"
    auto_help = False

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("That cabinet run is no longer active.")
            return

        session_data = getattr(character.ndb, "brave_arcade_session", None) or {}
        if not session_data:
            self.msg("That cabinet run is no longer active.")
            return

        parts = self.args.strip().split()
        if len(parts) != 2:
            self.msg("That cabinet run is no longer active.")
            return

        nonce, score_text = parts
        if nonce != session_data.get("nonce"):
            self.msg("That cabinet run is no longer active.")
            return

        try:
            score = max(0, min(999999, int(score_text)))
        except ValueError:
            self.msg("That cabinet run is no longer active.")
            return

        cabinet_id = session_data.get("cabinet_id")
        cabinet = None
        for candidate in self.get_local_entities(character, kind="arcade"):
            if candidate.id == cabinet_id or getattr(candidate.db, "brave_entity_id", None) == cabinet_id:
                cabinet = candidate
                break
        if not cabinet:
            self.msg("The cabinet falls dark before it can take your score.")
            character.ndb.brave_arcade_session = None
            return

        game_key = session_data.get("game_key")
        if game_key not in ARCADE_GAMES:
            self.msg("That cabinet run is no longer active.")
            character.ndb.brave_arcade_session = None
            return

        details = submit_arcade_score(character, cabinet, game_key, score)
        session = self.get_web_session()
        if session:
            send_webclient_event(character, session=session, brave_arcade_done={})
        character.ndb.brave_arcade_session = None

        game_name = ARCADE_GAMES[game_key]["name"]
        self.msg(f"Your {game_name} run ends at |w{format_arcade_score(score)}|n.")
        if details.get("improved_personal_best"):
            self.msg(f"New personal best on this cabinet: |w{format_arcade_score(details['best_score'])}|n.")
        if details.get("rank"):
            self.msg(f"Local cabinet rank: |w#{details['rank']}|n.")
        if details.get("reward"):
            self.msg(f"The prize drawer clicks open: |w{details['reward']['item_name']}|n.")
        if details.get("new_top_score") and cabinet.location:
            cabinet.location.msg_contents(
                f"|mThe cabinet bursts into bright static as {character.key} claims the top {game_name} score: {format_arcade_score(score)}.|n",
                exclude=[character],
            )

        character.execute_cmd("look", session=self.session)
