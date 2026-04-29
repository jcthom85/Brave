"""Party browser view payload builders."""

from world.browser_room_helpers import _local_player_characters
from world.browser_ui import (
    _action,
    _entry,
    _item,
    _make_view,
    _reactive_from_character,
    _section,
)
from world.navigation import format_route_hint
from world.party import get_character_by_id, get_follow_target, get_party_leader, get_party_members

def _build_party_member_entry(viewer, member, leader_id, mode="status"):
    member.ensure_brave_character()
    location = member.location.key if member.location else "Nowhere"
    online = "online" if member.is_connected else "offline"
    lines = [f"{'Leader' if member.id == leader_id else 'Member'} · {online}", f"Room: {location}"]
    command = None
    actions = []
    follow_target = get_follow_target(viewer)

    if mode == "status":
        resources = member.db.brave_resources or {}
        derived = member.db.brave_derived_stats or {}
        lines.append(f"HP: {resources.get('hp', 0)}/{derived.get('max_hp', 0)}")
        route = format_route_hint(viewer.location, member.location) if viewer.location else "route unavailable"
        lines.append(f"Route from you: {route}")
        member_follow_target = get_follow_target(member)
        if member_follow_target:
            lines.append(f"Following: {member_follow_target.key}")
    else:
        route = format_route_hint(viewer.location, member.location) if viewer.location else "route unavailable"
        lines.append(f"Route: {route}")

    if member.id != viewer.id:
        if member.location and viewer.location and member.location == viewer.location:
            if follow_target and follow_target.id == member.id:
                command = "party stay"
                actions.append(_action("Stay", "party stay", "do_not_disturb_on", tone="muted"))
            else:
                command = f"party follow {member.key}"
                actions.append(_action("Follow", command, "directions_walk"))
        actions.append(_action("Where", "party where", "location_searching", tone="muted"))
        if leader_id == viewer.id:
            actions.append(
                _action(
                    "Kick",
                    f"party kick {member.key}",
                    "person_remove",
                    tone="danger",
                    confirm=f"Remove {member.key} from the party?",
                )
            )

    return _entry(member.key, lines=lines, icon="person", command=command, actions=actions)

def build_party_view(character, mode="status"):
    """Return a browser-first main view for party screens."""

    members = get_party_members(character)
    leader = get_party_leader(character)
    invites = [
        leader_obj for leader_obj in (
            get_character_by_id(invite_id) for invite_id in (character.db.brave_party_invites or [])
        ) if leader_obj
    ]
    follow_target = get_follow_target(character)
    viewer_party_id = getattr(character.db, "brave_party_id", None)
    party_leader_id = getattr(character.db, "brave_party_leader_id", None)
    party_is_full = len(members) >= 4

    nearby_player_items = []
    for nearby in _local_player_characters(character):
        nearby_party_id = getattr(nearby.db, "brave_party_id", None)
        if viewer_party_id and nearby_party_id == viewer_party_id:
            continue
        if nearby_party_id:
            continue
        if viewer_party_id and party_leader_id != character.id:
            continue
        if party_is_full:
            continue

        nearby_player_items.append(
            _item(
                nearby.key,
                icon="person",
                command=f"party invite {nearby.key}",
            )
        )

    sections = []
    if not members:
        sections.append(
            _section(
                "Status",
                "groups",
                "lines",
                lines=[
                    "You are not currently in a party.",
                    "Invite someone nearby to start one.",
                ],
            )
        )
    else:
        sections.append(
            _section(
                "Members" if mode == "status" else "Party Routes",
                "groups",
                "entries",
                items=[_build_party_member_entry(character, member, character.db.brave_party_leader_id, mode=mode) for member in members],
            )
        )

    if nearby_player_items:
        sections.append(
            _section(
                "Nearby Players",
                "person_add",
                "list",
                items=nearby_player_items,
            )
        )

    if invites:
        sections.append(
            _section(
                "Invites",
                "mail",
                "list",
                items=[
                    _item(
                        invite.key,
                        icon="person_add",
                        command=f"party accept {invite.key}",
                        actions=[_action("Decline", f"party decline {invite.key}", "person_off", tone="danger")],
                    )
                    for invite in invites
                ],
            )
        )

    if members:
        command_items = [_item("Locate your party", icon="location_searching", command="party where")]
        if follow_target:
            command_items.append(_item("Stop following", icon="do_not_disturb_on", command="party stay"))
        command_items.append(_item("Leave party", icon="logout", command="party leave"))
        sections.append(_section("Actions", "terminal", "list", items=command_items))

    view = _make_view(
        "",
        "Party",
        eyebrow_icon=None,
        title_icon="group",
        subtitle="",
        chips=[],
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="party"),
    )
    if view.get("back_action"):
        view["back_action"]["label"] = ""
        view["back_action"]["aria_label"] = "Close"
    return {**view, "variant": "party"}
