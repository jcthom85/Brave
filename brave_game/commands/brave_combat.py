"""Combat commands extracted from Brave's main command module."""

from world.browser_views import build_combat_view
from world.browser_panels import build_combat_panel
from world.party import get_present_party_members

from .brave import BraveCharacterCommand


def _refresh_combat_scene(command, encounter, character):
    """Refresh combat for text sessions without double-pushing browser views."""

    snapshot = encounter.format_combat_snapshot()
    if command.get_web_session():
        command.send_other_sessions(snapshot)
        return
    command.msg(snapshot)


class CmdFight(BraveCharacterCommand):
    """
    Engage the threats in your current area.

    Usage:
      fight

    Starts or joins the current room encounter. If a battle is already underway here,
    this joins it explicitly instead of auto-pulling you in.
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

        selected_preview = None
        if self.args.strip():
            selected_preview = BraveEncounter.find_room_threat(character.location, self.args.strip())
            if isinstance(selected_preview, list):
                self.msg(
                    "Be more specific. That could mean: "
                    + ", ".join(
                        threat.get("encounter_title") or threat.get("encounter_key") or "hostiles"
                        for threat in selected_preview
                    )
                )
                return
            if not selected_preview:
                self.msg("No visible threat here matches that target.")
                return

        encounter, created = BraveEncounter.start_for_room(
            character.location,
            expected_party_size=self.get_present_party_size(character),
            query=self.args.strip() or None,
            preview=selected_preview,
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

        lines = []
        for threat in threats:
            detail = threat.get("detail")
            summary = f"{threat['key']}: {threat['threat_label'].lower()} threat"
            if detail:
                summary += f" · {detail}"
            lines.append(summary)
        self.msg("Threats here:\n  " + "\n  ".join(lines) + "\nUse |wattack <name>|n to open a fight or |wfight|n to join the current one.")


class CmdThreatDebug(BraveCharacterCommand):
    """
    Inspect and control server-side roaming threats.

    Usage:
      threatdebug
      threatdebug zone
      threatdebug seed
      threatdebug tick

    Developer-only helper for inspecting current room/zone roaming state and
    forcing a server-side seed or roam tick.
    """

    key = "threatdebug"
    aliases = ["roamdebug", "threatsdebug"]
    locks = "cmd:pperm(Player)"
    help_category = "Brave"

    def func(self):
        from typeclasses.scripts import BraveEncounter

        character = self.get_character()
        if not character or not character.location:
            self.msg("No active character location.")
            return

        action = (self.args or "").strip().lower()
        if action == "seed":
            BraveEncounter.ensure_roaming_threat_population()
        elif action == "tick":
            BraveEncounter.advance_roaming_threats()

        room = character.location
        room_previews = BraveEncounter._get_room_threat_preview_states(room)
        active_zone_previews = []
        room_zone = str(getattr(room.db, "brave_zone", "") or "").strip()
        for candidate in BraveEncounter._iter_world_rooms():
            if str(getattr(candidate.db, "brave_zone", "") or "").strip() != room_zone:
                continue
            previews = BraveEncounter._get_room_threat_preview_states(candidate)
            for preview in previews:
                active_zone_previews.append(
                    (
                        getattr(candidate.db, "brave_room_id", ""),
                        preview.get("encounter_key"),
                        preview.get("origin_room_id"),
                    )
                )

        lines = [
            f"Room: {getattr(room.db, 'brave_room_id', '?')}",
            f"Zone: {room_zone or '?'}",
            f"Safe: {bool(getattr(room.db, 'brave_safe', False))}",
            f"Movement Blocked: {bool(getattr(room.db, 'brave_enemy_movement_blocked', False))}",
            f"Current Previews: {len(room_previews)}",
        ]
        for index, room_preview in enumerate(room_previews[:6], start=1):
            lines.extend(
                [
                    f"Preview {index}: {room_preview.get('encounter_key')}",
                    f"  Origin: {room_preview.get('origin_room_id')}",
                    f"  Allowed Zones: {', '.join(room_preview.get('allowed_zone_keys', [])) or 'none'}",
                    f"  Roaming: {bool(room_preview.get('roaming', False))}",
                    f"  Roam Radius: {room_preview.get('roam_radius')}",
                ]
            )
        lines.append(f"Active Zone Previews: {len(active_zone_previews)}")
        if action == "zone" or action == "tick" or action == "seed":
            for room_id, encounter_key, origin_room_id in active_zone_previews:
                lines.append(f"  {room_id}: {encounter_key} (origin {origin_room_id})")
        output = "\n".join(lines)
        if self.send_browser_notice(
            "Threat Debug",
            lines=lines,
            tone="muted",
            icon="bug_report",
            duration_ms=12000,
            sticky=True,
        ):
            self.send_other_sessions(output)
            return
        self.msg(output)


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

    def _refresh_combat_scene(self, encounter, character):
        _refresh_combat_scene(self, encounter, character)

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
                    self.msg("Be more specific. That could mean: " + ", ".join(threat.get("encounter_title") or threat.get("encounter_key") or "hostiles" for threat in preview_match))
                    return
                if not preview_match:
                    self.msg("No visible threat here matches that target.")
                    return

            encounter, _created = BraveEncounter.start_for_room(
                character.location,
                expected_party_size=self.get_present_party_size(character),
                preview=preview_match if self.args.strip() else None,
                query=self.args.strip() or None,
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

        self._refresh_combat_scene(encounter, character)
        self.msg(message)


class CmdUse(BraveCharacterCommand):
    """
    Use a class ability or consumable.

    Usage:
      use <ability or consumable>
      use <ability or consumable> = <target>

    In combat, queues one of the currently implemented unlocked combat abilities or
    a carried combat consumable for the next round. Outside combat, uses a carried
    exploration consumable immediately.
    """

    key = "use"
    aliases = ["cast"]
    help_category = "Brave"

    def _refresh_combat_scene(self, encounter, character):
        _refresh_combat_scene(self, encounter, character)

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("Usage: use <ability> [= target]")
            return

        action_name = self.lhs if self.rhs is not None else self.args
        target_name = self.rhs.strip() if self.rhs else None
        action_name = action_name.strip()

        encounter = self.get_encounter(character, require=False)
        if not encounter or not encounter.is_participant(character):
            ok, message, result = self.use_explore_consumable(character, action_name, target_name)
            if self.deliver_consumable_notice(ok, message, result):
                return
            self.msg(message)
            return

        ok, message = encounter.queue_ability(character, action_name, target_name)
        if not ok:
            consumable_match = encounter.find_consumable(character, action_name, context="combat")
            if consumable_match:
                ok, message = encounter.queue_item(character, action_name, target_name)
        if not ok:
            self.msg(message)
            return

        self._refresh_combat_scene(encounter, character)
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

    def _refresh_combat_scene(self, encounter, character):
        _refresh_combat_scene(self, encounter, character)

    def func(self):
        character = self.get_character()
        if not character:
            return

        encounter = self.get_encounter(character, require=True)
        if not encounter:
            return

        ok, message = encounter.queue_flee(character)
        if ok:
            self._refresh_combat_scene(encounter, character)
        self.msg(message)
