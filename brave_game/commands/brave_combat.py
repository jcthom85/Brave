"""Combat commands extracted from Brave's main command module."""

from world.browser_views import build_combat_view
from world.browser_panels import build_combat_panel
from world.party import get_present_party_members

from .brave import BraveCharacterCommand


class CmdFight(BraveCharacterCommand):
    """
    Engage the threats in your current area.

    Usage:
      fight

    Starts or joins the current room encounter.
    """

    key = "fight"
    aliases = ["engage"]
    help_category = "Brave"

    def func(self):
        from typeclasses.scripts import BraveEncounter

        character = self.get_character()
        if not character:
            return
        if not character.location:
            self.msg("You have no location to fight in.")
            return
        if character.location.db.brave_safe:
            self.msg("This is a safe place. No immediate fight is pressing in here.")
            return

        encounter, created = BraveEncounter.start_for_room(
            character.location,
            expected_party_size=self.get_present_party_size(character),
        )
        if not encounter:
            self.msg("Nothing stirs here right now.")
            return

        if created:
            encounter.add_participant(character)
            if character.db.brave_party_id:
                for other in get_present_party_members(character):
                    if other != character and getattr(other, "is_connected", False):
                        encounter.add_participant(other)
        else:
            ok, error = encounter.add_participant(character)
            if not ok:
                self.msg(error)
                return

        self.scene_msg(
            encounter.format_combat_snapshot(),
            panel=build_combat_panel(encounter),
            view=build_combat_view(encounter, character),
        )


class CmdEnemies(BraveCharacterCommand):
    """
    View current enemies or likely local threats.

    Usage:
      enemies

    Shows the current combatants if a fight is active, or previews likely dangers in a hostile room.
    """

    key = "enemies"
    aliases = ["foes", "threats"]
    help_category = "Brave"

    def func(self):
        from typeclasses.scripts import BraveEncounter

        character = self.get_character()
        if not character:
            return
        encounter = self.get_encounter(character)
        if encounter and encounter.is_participant(character):
            self.scene_msg(
                encounter.format_combat_snapshot(),
                panel=build_combat_panel(encounter),
                view=build_combat_view(encounter, character),
            )
            return

        threats = BraveEncounter.get_visible_room_threats(character.location, character)
        if not threats:
            self.msg("No immediate enemies are pressing in here.")
            return

        lines = [
            f"{threat['key']}: {threat['temperament_label']}, {threat['threat_label'].lower()} threat"
            for threat in threats
        ]
        self.msg("Threats here:\n  " + "\n  ".join(lines) + "\nUse |wattack <name>|n or |wfight|n to engage.")


class CmdAttack(BraveCharacterCommand):
    """
    Queue a basic attack in combat.

    Usage:
      attack
      attack <enemy>

    Readies a basic attack against the nearest enemy or a chosen target.
    """

    key = "attack"
    help_category = "Brave"

    def func(self):
        from typeclasses.scripts import BraveEncounter

        character = self.get_character()
        if not character:
            return

        encounter = self.get_encounter(character, require=False)
        started_from_room = not encounter or not encounter.is_participant(character)
        if started_from_room:
            if not character.location:
                self.msg("You have no location to fight in.")
                return
            if character.location.db.brave_safe:
                self.msg("This is a safe place. No immediate fight is pressing in here.")
                return

            if self.args.strip():
                preview_match = BraveEncounter.find_room_threat(character.location, self.args.strip())
                if isinstance(preview_match, list):
                    self.msg("Be more specific. That could mean: " + ", ".join(enemy["key"] for enemy in preview_match))
                    return
                if not preview_match:
                    self.msg("No visible threat here matches that target.")
                    return

            encounter, _created = BraveEncounter.start_for_room(
                character.location,
                expected_party_size=self.get_present_party_size(character),
            )
            if not encounter:
                self.msg("Nothing hostile stirs here right now.")
                return

            encounter.add_participant(character)
            if getattr(character.db, "brave_party_id", None):
                for other in get_present_party_members(character):
                    if other != character and getattr(other, "is_connected", False):
                        encounter.add_participant(other)

        ok, message = encounter.queue_attack(character, self.args.strip() or None)
        if not ok:
            self.msg(message)
            return

        if started_from_room:
            self.scene_msg(
                encounter.format_combat_snapshot(),
                panel=build_combat_panel(encounter),
                view=build_combat_view(encounter, character),
            )

        self.msg(message)


class CmdUse(BraveCharacterCommand):
    """
    Queue a class ability or combat consumable in combat.

    Usage:
      use <ability or consumable>
      use <ability or consumable> = <target>

    Queues one of the currently implemented unlocked combat abilities, or a carried
    combat consumable, for the next combat round.
    """

    key = "use"
    aliases = ["cast"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("Usage: use <ability> [= target]")
            return

        encounter = self.get_encounter(character, require=True)
        if not encounter:
            return

        action_name = self.lhs if self.rhs is not None else self.args
        target_name = self.rhs.strip() if self.rhs else None
        action_name = action_name.strip()

        ok, message = encounter.queue_ability(character, action_name, target_name)
        if not ok:
            consumable_match = encounter.find_consumable(character, action_name, context="combat")
            if consumable_match:
                ok, message = encounter.queue_item(character, action_name, target_name)
        self.msg(message)


class CmdFlee(BraveCharacterCommand):
    """
    Queue a retreat from the current fight.

    Usage:
      flee

    Tries to fall back to the room you entered from on the next combat round.
    """

    key = "flee"
    aliases = ["retreat", "run"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        encounter = self.get_encounter(character, require=True)
        if not encounter:
            return

        ok, message = encounter.queue_flee(character)
        self.msg(message)
