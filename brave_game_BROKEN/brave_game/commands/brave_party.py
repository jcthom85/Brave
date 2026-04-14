"""Party commands extracted from Brave's main command module."""

from world.navigation import format_route_hint
from world.screen_text import format_entry, render_screen, wrap_text

from .brave import BraveCharacterCommand, _normalize_token, _stack_blocks


class CmdParty(BraveCharacterCommand):
    """
    Manage your current party.

    Usage:
      party
      party invite <name>
      party accept [leader]
      party decline [leader]
      party follow [name]
      party stay
      party where
      party leave
      party kick <name>

    Shows party status, invites nearby players, and manages a small local multiplayer group.
    """

    key = "party"
    aliases = ["group"]
    help_category = "Brave"

    def _match_leader_invite(self, character, query=None):
        from world.party import ensure_party_state, get_character_by_id

        ensure_party_state(character)
        leaders = [
            leader
            for leader in (
                get_character_by_id(invite_id) for invite_id in (character.db.brave_party_invites or [])
            )
            if leader
        ]
        if not leaders:
            return None, []
        if not query:
            return (leaders[0] if len(leaders) == 1 else leaders), leaders

        query_norm = _normalize_token(query)
        exact = [leader for leader in leaders if query_norm == _normalize_token(leader.key)]
        if exact:
            return (exact[0] if len(exact) == 1 else exact), leaders

        partial = [leader for leader in leaders if query_norm in _normalize_token(leader.key)]
        if not partial:
            return None, leaders
        return (partial[0] if len(partial) == 1 else partial), leaders

    def _match_party_member(self, character, query):
        from world.party import get_party_members

        members = [member for member in get_party_members(character) if member != character]
        if not query:
            return None, members

        query_norm = _normalize_token(query)
        exact = [member for member in members if query_norm == _normalize_token(member.key)]
        if exact:
            return (exact[0] if len(exact) == 1 else exact), members

        partial = [member for member in members if query_norm in _normalize_token(member.key)]
        if not partial:
            return None, members
        return (partial[0] if len(partial) == 1 else partial), members

    def _format_member_block(self, viewer, member, leader_id):
        from world.party import get_follow_target

        member.ensure_brave_character()
        location = member.location.key if member.location else "Nowhere"
        online = "online" if member.is_connected else "offline"
        resources = member.db.brave_resources or {}
        derived = member.db.brave_derived_stats or {}
        hp = f"{resources.get('hp', 0)}/{derived.get('max_hp', 0)} HP"
        role = "Leader" if member.id == leader_id else "Member"
        route = format_route_hint(viewer.location, member.location) if viewer.location else "route unavailable"
        follow_target = get_follow_target(member)
        details = [
            f"{role} · {online}",
            f"Room: {location}",
            f"HP: {hp}",
            f"Route from you: {route}",
        ]
        if follow_target:
            details.append(f"Following: {follow_target.key}")
        return format_entry(member.key, details=details)

    def _show_status(self, character):
        from world.browser_panels import build_party_panel
        from world.browser_views import build_party_view
        from world.party import ensure_party_state, get_follow_target, get_party_leader, get_party_members

        ensure_party_state(character)
        members = get_party_members(character)
        _, leaders = self._match_leader_invite(character)
        follow_target = get_follow_target(character)

        sections = []
        meta = []
        if not members:
            meta.append("Solo")
            sections.append(
                (
                    "Party Status",
                    [
                        *wrap_text("You are not currently in a party.", indent="  "),
                        *wrap_text(
                            "Use |wparty invite <name>|n on someone in the same room to start one.",
                            indent="  ",
                        ),
                    ],
                )
            )
        else:
            leader = get_party_leader(character)
            meta.append(f"{len(members)} members")
            meta.append(f"Leader {leader.key if leader else 'Unknown'}")
            if follow_target:
                meta.append(f"Following {follow_target.key}")
            sections.append(
                (
                    "Members",
                    _stack_blocks(
                        [
                            self._format_member_block(character, member, character.db.brave_party_leader_id)
                            for member in members
                        ]
                    ),
                )
            )

        if leaders:
            sections.append(
                (
                    "Pending Invites",
                    [*wrap_text(", ".join(leader.key for leader in leaders), indent="  ")],
                )
            )
        sections.append(
            (
                "Party Commands",
                [
                    *wrap_text("invite, accept, decline, follow, stay, where, leave, kick", indent="  "),
                ],
            )
        )

        screen = render_screen("Party", subtitle="Keep the family together and moving as one group.", meta=meta, sections=sections)
        self.scene_msg(screen, panel=build_party_panel(character), view=build_party_view(character))

    def _invite(self, character, query):
        from world.party import add_invite, create_party, ensure_party_state, get_party_members, is_party_leader

        if not query:
            self.msg("Usage: party invite <name>")
            return

        ensure_party_state(character)
        if character.db.brave_party_id and not is_party_leader(character):
            self.msg("Only the party leader can invite new members.")
            return

        target, locals_ = self.find_local_character(character, query)
        if isinstance(target, list):
            self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in target))
            return
        if not target:
            if locals_:
                self.msg(
                    "No connected player here matches that name. Nearby players: "
                    + ", ".join(obj.key for obj in locals_)
                )
            else:
                self.msg("No other connected players are here to invite.")
            return
        if target == character:
            self.msg("You are already with yourself.")
            return

        target.ensure_brave_character()
        if target.db.brave_party_id:
            self.msg(f"{target.key} is already in a party.")
            return

        if not character.db.brave_party_id:
            create_party(character)

        if len(get_party_members(character)) >= 4:
            self.msg("Your party is already full for this slice.")
            return

        add_invite(target, character.id)
        self.msg(f"You invite {target.key} to your party.")
        target.msg(
            f"{character.key} invites you to a party. Use |wparty accept {character.key}|n or "
            f"|wparty decline {character.key}|n."
        )

    def _accept(self, character, query):
        from world.party import ensure_party_state, get_party_members, join_party

        ensure_party_state(character)
        if character.db.brave_party_id:
            self.msg("You are already in a party. Leave it before accepting another invitation.")
            return

        leader, leaders = self._match_leader_invite(character, query=query)
        if isinstance(leader, list):
            self.msg("Be more specific. Pending invites: " + ", ".join(obj.key for obj in leader))
            return
        if not leader:
            if leaders:
                self.msg("No pending invite matches that name.")
            else:
                self.msg("You have no pending party invites.")
            return

        leader.ensure_brave_character()
        if leader.db.brave_party_id and len(get_party_members(leader)) >= 4:
            self.msg(f"{leader.key}'s party is already full.")
            return

        join_party(leader, character)
        self.msg(f"You join {leader.key}'s party.")
        for member in get_party_members(character):
            if member != character:
                member.msg(f"{character.key} joins the party.")

    def _decline(self, character, query):
        from world.party import ensure_party_state, get_party_leader, remove_invite

        leader, leaders = self._match_leader_invite(character, query=query)
        if isinstance(leader, list):
            self.msg("Be more specific. Pending invites: " + ", ".join(obj.key for obj in leader))
            return
        if not leader:
            if leaders:
                self.msg("No pending invite matches that name.")
            else:
                self.msg("You have no pending party invites.")
            return

        remove_invite(character, leader.id)
        self.msg(f"You decline {leader.key}'s party invite.")
        leader.msg(f"{character.key} declines your party invite.")

    def _follow(self, character, query):
        from world.party import (
            ensure_party_state,
            get_follow_target,
            get_party_leader,
            get_party_members,
            set_follow_target,
        )

        members = get_party_members(character)
        if len(members) <= 1:
            self.msg("You need to be in a party before following anyone.")
            return

        target = None
        if query:
            target, members = self._match_party_member(character, query)
            if isinstance(target, list):
                self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in target))
                return
            if not target:
                self.msg("No party member matches that name.")
                return
        else:
            target = get_party_leader(character)
            if not target or target == character:
                self.msg("Usage: party follow <name>")
                return

        if target.location != character.location:
            self.msg(f"{target.key} is not here. Stand in the same room before following.")
            return

        set_follow_target(character, target)
        self.msg(f"You fall in behind {target.key}.")
        target.msg(f"{character.key} starts following you.")

    def _stay(self, character):
        from world.party import clear_follow_target, get_follow_target

        follow_target = get_follow_target(character)
        if not follow_target:
            self.msg("You are not currently following anyone.")
            return

        clear_follow_target(character)
        self.msg(f"You stop following {follow_target.key}.")

    def _where(self, character):
        from world.browser_panels import build_party_panel
        from world.browser_views import build_party_view
        from world.party import get_party_members

        members = [member for member in get_party_members(character) if member.id != character.id]
        if not members:
            self.msg("You are not currently in a party.")
            return

        route_blocks = []
        for member in members:
            location = member.location.key if member.location else "Nowhere"
            status = "online" if member.is_connected else "offline"
            route = format_route_hint(character.location, member.location) if character.location else "route unavailable"
            route_blocks.append(
                format_entry(
                    member.key,
                    details=[f"{status} · {location}", f"Route: {route}"],
                )
            )

        screen = render_screen(
            "Party Routes",
            subtitle="Where everyone is relative to your current room.",
            meta=[character.location.key if character.location else "No current room"],
            sections=[("Party Members", _stack_blocks(route_blocks))],
        )
        self.scene_msg(screen, panel=build_party_panel(character, mode="routes"), view=build_party_view(character, mode="routes"))

    def _leave(self, character):
        from world.party import (
            clear_party_membership,
            disband_party,
            get_party_leader,
            get_party_members,
            is_party_leader,
        )

        members = get_party_members(character)
        if not members:
            self.msg("You are not currently in a party.")
            return

        if is_party_leader(character):
            former_members = disband_party(character)
            for member in former_members:
                member.msg("The party disbands.")
            return

        leader = get_party_leader(character)
        clear_party_membership(character)
        self.msg("You leave the party.")
        if leader:
            leader.msg(f"{character.key} leaves the party.")

    def _kick(self, character, query):
        from world.party import clear_party_membership, get_party_members, is_party_leader

        if not is_party_leader(character):
            self.msg("Only the party leader can remove members.")
            return
        if not query:
            self.msg("Usage: party kick <name>")
            return

        target, members = self._match_party_member(character, query)
        if isinstance(target, list):
            self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in target))
            return
        if not target:
            self.msg("No party member matches that name.")
            return

        clear_party_membership(target)
        self.msg(f"You remove {target.key} from the party.")
        target.msg("You are removed from the party.")

    def func(self):
        character = self.get_character()
        if not character:
            return

        if not self.args:
            self._show_status(character)
            return

        command, _, remainder = self.args.strip().partition(" ")
        subcommand = command.lower()
        remainder = remainder.strip()

        if subcommand == "invite":
            self._invite(character, remainder)
            return
        if subcommand == "accept":
            self._accept(character, remainder or None)
            return
        if subcommand == "decline":
            self._decline(character, remainder or None)
            return
        if subcommand == "follow":
            self._follow(character, remainder or None)
            return
        if subcommand in {"stay", "unfollow", "stop"}:
            self._stay(character)
            return
        if subcommand in {"where", "locate"}:
            self._where(character)
            return
        if subcommand in {"leave", "disband"}:
            self._leave(character)
            return
        if subcommand in {"kick", "remove"}:
            self._kick(character, remainder)
            return

        self.msg(
            "Usage: party, party invite <name>, party accept [leader], party decline [leader], "
            "party follow [name], party stay, party where, party leave, party kick <name>"
        )
