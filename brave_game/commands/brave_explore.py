"""Exploration, travel, and activity commands extracted from Brave's helper module."""

import re

from world.activities import (
    borrow_fishing_tackle,
    format_catch_log,
    cook_recipe,
    describe_cooking_recipe,
    format_fishing_screen,
    format_recipe_list,
    get_selected_fishing_lure,
    get_selected_fishing_rod,
    reel_line,
    room_supports_activity,
    set_selected_fishing_lure,
    set_selected_fishing_rod,
    start_fishing,
)
from world.browser_panels import build_cook_panel, build_fishing_panel, build_map_panel, build_travel_panel
from world.browser_views import build_cook_view, build_fishing_view, build_map_view, build_travel_view
from world.navigation import render_map, render_minimap, sort_exits
from world.screen_text import format_entry, render_screen, wrap_text

from .brave import BraveCharacterCommand, _stack_blocks


_EVENNIA_MARKUP_RE = re.compile(r"\|[A-Za-z]")


def _strip_evennia_markup(text):
    """Remove lightweight Evennia color markup for browser-view status text."""

    clean = str(text or "").replace("||", "|")
    return _EVENNIA_MARKUP_RE.sub("", clean)


def _refresh_cook_scene(command, character, message, *, success=False):
    """Keep browser-based hearth actions inside the cooking screen."""

    if not command.get_web_session() or not room_supports_activity(character.location, "cooking"):
        return False

    command.clear_scene()
    command.send_browser_view(
        build_cook_view(
            character,
            status_message=_strip_evennia_markup(message),
            status_tone="good" if success else "muted",
        )
    )
    command.msg(message)
    command.send_other_sessions(message)
    return True


def _refresh_fishing_scene(command, character, message=None, *, success=False):
    """Keep browser-based fishing actions inside the tackle screen."""

    if not command.get_web_session() or not room_supports_activity(character.location, "fishing"):
        return False

    command.clear_scene()
    command.send_browser_view(
        build_fishing_view(
            character,
            status_message=_strip_evennia_markup(message) if message else None,
            status_tone="good" if success else "muted",
        )
    )
    if message:
        command.msg(message)
        command.send_other_sessions(message)
    return True


class CmdFish(BraveCharacterCommand):
    """
    Cast a line where fishing is available.

    Usage:
      fish
      fish cast
      fish tackle
      fish log
      fish borrow kit
      fish borrow rod
      fish borrow lure
      fish rod <rod>
      fish lure <lure>

    Review your tackle, swap rod or lure, or cast a line where fishing is available.
    """

    key = "fish"
    aliases = ["angle"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        raw = self.args.strip()
        lowered = raw.lower()

        if lowered in {"", "tackle", "kit", "gear"}:
            if not raw:
                if self.get_web_session() and room_supports_activity(character.location, "fishing"):
                    self.scene_msg(format_fishing_screen(character), panel=build_fishing_panel(character), view=build_fishing_view(character))
                    return
                ok, message = start_fishing(character)
                self.msg(message)
                return
            self.scene_msg(format_fishing_screen(character), panel=build_fishing_panel(character), view=build_fishing_view(character))
            return

        if lowered == "log":
            self.scene_msg(format_catch_log(), panel=build_fishing_panel(character), view=build_fishing_view(character, status_message="Great Catch log opened.", status_tone="muted"))
            return

        if lowered == "cast":
            ok, message = start_fishing(character)
            if _refresh_fishing_scene(self, character, message, success=ok):
                return
            self.msg(message)
            return

        if lowered.startswith("borrow"):
            selection = raw[6:].strip() or "kit"
            ok, message = borrow_fishing_tackle(character, selection)
            if _refresh_fishing_scene(self, character, message, success=ok):
                return
            self.msg(message)
            return

        if lowered.startswith("rod "):
            ok, message = set_selected_fishing_rod(character, raw[4:].strip())
            if _refresh_fishing_scene(self, character, message, success=ok):
                return
            self.msg(message)
            return

        if lowered.startswith("lure "):
            ok, message = set_selected_fishing_lure(character, raw[5:].strip())
            if _refresh_fishing_scene(self, character, message, success=ok):
                return
            self.msg(message)
            return

        self.msg("Usage: fish, fish cast, fish tackle, fish log, fish borrow <kit|rod|lure>, fish rod <rod>, or fish lure <lure>")


class CmdReel(BraveCharacterCommand):
    """
    Reel in a fish after a bite.

    Usage:
      reel

    Sets the hook and resolves an active fishing bite.
    """

    key = "reel"
    aliases = ["hook"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        ok, message = reel_line(character)
        if _refresh_fishing_scene(self, character, message, success=ok):
            return
        self.msg(message)


class CmdCook(BraveCharacterCommand):
    """
    Review or prepare simple hearth recipes.

    Usage:
      cook
      cook inspect <recipe>
      cook <recipe>

    Shows what you can make at the Lantern Rest hearth, or cooks a named recipe.
    """

    key = "cook"
    aliases = ["recipes"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        if not self.args:
            self.scene_msg(format_recipe_list(character), panel=build_cook_panel(character), view=build_cook_view(character))
            return

        raw = self.args.strip()
        lowered = raw.lower()
        if lowered.startswith("inspect "):
            ok, message = describe_cooking_recipe(character, raw[8:].strip())
            self.msg(message)
            return

        ok, message = cook_recipe(character, raw)
        if _refresh_cook_scene(self, character, message, success=ok):
            return
        self.msg(message)


class CmdEat(BraveCharacterCommand):
    """
    Eat a prepared meal from your pack.

    Usage:
      eat <meal>

    Consumes a cooked meal, restores resources, and applies its current meal buff.
    """

    key = "eat"
    aliases = ["meal"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("Usage: eat <meal>")
            return

        encounter = self.get_encounter(character, require=False)
        if encounter and encounter.is_participant(character):
            ok, message = encounter.queue_meal(character, self.args.strip())
            self.msg(message)
            return

        ok, message, result = self.use_explore_consumable(character, self.args.strip(), verb="eat")
        if _refresh_cook_scene(self, character, message, success=ok):
            return
        if self.deliver_consumable_notice(ok, message, result):
            return
        self.msg(message)


class CmdItem(BraveCharacterCommand):
    """
    Use a consumable item from your pack.

    Usage:
      item <consumable>
      item <consumable> = <target>

    Uses a carried consumable outside combat, or queues it during combat.
    """

    key = "item"
    aliases = ["consume", "useitem"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("Usage: item <consumable> [= target]")
            return

        item_name = self.lhs.strip() if self.rhs is not None else self.args.strip()
        target_name = self.rhs.strip() if self.rhs else None

        encounter = self.get_encounter(character, require=False)
        if encounter and encounter.is_participant(character):
            ok, message = encounter.queue_item(character, item_name, target_name)
            self.msg(message)
            return

        ok, message, result = self.use_explore_consumable(character, item_name, target_name)
        if _refresh_cook_scene(self, character, message, success=ok):
            return
        if self.deliver_consumable_notice(ok, message, result):
            return
        self.msg(message)


class CmdTravel(BraveCharacterCommand):
    """
    Travel using simple destination names.

    Usage:
      travel
      travel <destination>

    With no arguments, shows available travel options from your current room.
    With a destination, moves you along a matching exit.
    """

    key = "travel"
    aliases = ["go"]
    help_category = "Brave"

    def _format_options(self, exits):
        blocks = []
        for exit_obj in sort_exits(exits):
            direction = getattr(exit_obj.db, "brave_direction", exit_obj.key).lower()
            aliases = [alias for alias in exit_obj.aliases.all() if alias.lower() != direction]
            details = []
            if aliases:
                details.append("Aliases: " + ", ".join(aliases))
            blocks.append(
                format_entry(
                    f"{direction.title()} -> {exit_obj.destination.key}",
                    details=details,
                )
            )
        return _stack_blocks(blocks)

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not character.location:
            self.msg("You have no location to travel from.")
            return

        exits = sort_exits(list(character.location.exits))
        if not exits:
            self.msg("There are no clear paths onward from here.")
            return

        base_sections = [
            ("Routes", self._format_options(exits)),
            (
                "Travel Notes",
                [
                    *wrap_text("You can type the direction directly, like |wn|n or |we|n.", indent="  "),
                    *wrap_text("Use |wtravel <destination>|n if you prefer named fallback.", indent="  "),
                ],
            ),
        ]

        if not self.args:
            screen = render_screen(
                "Travel",
                subtitle=f"Current room: {character.location.key}",
                meta=[f"{len(exits)} available exits"],
                sections=base_sections,
            )
            self.scene_msg(screen, panel=build_travel_panel(character), view=build_travel_view(character))
            return

        query = self.args.strip().lower()
        matches = []
        for exit_obj in exits:
            names = [exit_obj.key.lower(), exit_obj.destination.key.lower()]
            names.extend(alias.lower() for alias in exit_obj.aliases.all())
            if any(query == name or query in name for name in names):
                matches.append(exit_obj)

        if not matches:
            screen = render_screen(
                "Travel",
                subtitle=f"No route matches '{self.args.strip()}'.",
                meta=[f"{len(exits)} available exits"],
                sections=base_sections,
            )
            self.scene_msg(screen, panel=build_travel_panel(character), view=build_travel_view(character))
            return
        if len(matches) > 1:
            names = ", ".join(exit_obj.key for exit_obj in matches)
            self.msg(f"Be more specific. That could mean: {names}")
            return

        exit_obj = matches[0]
        if exit_obj.access(character, "traverse"):
            exit_obj.at_traverse(character, exit_obj.destination)
        else:
            self.msg("You can't travel that way right now.")


class CmdMap(BraveCharacterCommand):
    """
    Show a regional map or local minimap.

    Usage:
      map
      minimap

    Shows the current area's layout using your room coordinates.
    """

    key = "map"
    aliases = ["minimap"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not character.location:
            self.msg("You have no location to map from.")
            return

        if self.cmdstring.lower() == "minimap":
            self.scene_msg(
                render_minimap(character.location, radius=2, character=character),
                panel=build_map_panel(character, mode="minimap"),
                view=build_map_view(character.location, character, mode="minimap"),
            )
            return

        self.scene_msg(
            render_map(character.location, radius=None, character=character),
            panel=build_map_panel(character, mode="map"),
            view=build_map_view(character.location, character, mode="map"),
        )


class CmdEmote(BraveCharacterCommand):
    """
    Show a quick social emote.

    Usage:
      emote <message>

    Sends a short expressive line to the current room.
    """

    key = "emote"
    aliases = ["pose"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        if not self.args:
            self.msg("Usage: emote <message>")
            return

        self.send_room_emote(self.args.strip())


class CmdRest(BraveCharacterCommand):
    """
    Recover in a safe place.

    Usage:
      rest

    Restores your current HP, mana, and stamina when you are in a safe room and not in combat.
    """

    key = "rest"
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        encounter = self.get_encounter(character)
        if encounter and encounter.is_participant(character):
            self.msg("You can't rest in the middle of a fight.")
            return
        if not character.location or not character.location.db.brave_safe:
            self.msg("You need a safe place before you can properly rest.")
            return

        character.restore_resources()
        self.msg("You take a moment to recover your strength.")
