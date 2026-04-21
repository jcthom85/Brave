"""Lightweight party helpers for Brave's first multiplayer slice."""

from evennia.objects.models import ObjectDB

CHARACTER_TYPECLASS = "typeclasses.characters.Character"


def _all_brave_characters():
    return list(ObjectDB.objects.filter(db_typeclass_path=CHARACTER_TYPECLASS).order_by("id"))


def get_character_by_id(dbref):
    """Return a Brave character by dbref, if it still exists."""

    try:
        return ObjectDB.objects.get(id=dbref, db_typeclass_path=CHARACTER_TYPECLASS)
    except ObjectDB.DoesNotExist:
        return None


def ensure_party_state(character):
    """Initialize party-related attributes on a character if missing."""

    if character.db.brave_party_id is None:
        character.db.brave_party_id = None
    if character.db.brave_party_leader_id is None:
        character.db.brave_party_leader_id = None
    if character.db.brave_party_invites is None:
        character.db.brave_party_invites = []
    if character.db.brave_follow_target_id is None:
        character.db.brave_follow_target_id = None


def is_party_leader(character):
    """Return whether the character currently leads their party."""

    ensure_party_state(character)
    return bool(character.db.brave_party_id) and character.db.brave_party_leader_id == character.id


def create_party(leader):
    """Create or refresh a party with `leader` as its head."""

    ensure_party_state(leader)
    party_id = f"party-{leader.id}"
    leader.db.brave_party_id = party_id
    leader.db.brave_party_leader_id = leader.id
    leader.db.brave_follow_target_id = None
    return party_id


def set_party_membership(member, party_id, leader_id):
    """Assign a member to a specific party."""

    ensure_party_state(member)
    member.db.brave_party_id = party_id
    member.db.brave_party_leader_id = leader_id


def clear_party_membership(member):
    """Remove a character from any current party."""

    ensure_party_state(member)
    member.db.brave_party_id = None
    member.db.brave_party_leader_id = None
    member.db.brave_follow_target_id = None


def get_party_leader(character):
    """Return the current party leader object, if any."""

    ensure_party_state(character)
    return get_character_by_id(character.db.brave_party_leader_id)


def get_party_members(character):
    """Return all members in the same party as `character`."""

    ensure_party_state(character)
    party_id = character.db.brave_party_id
    if not party_id:
        return []

    leader_id = character.db.brave_party_leader_id
    members = [member for member in _all_brave_characters() if member.db.brave_party_id == party_id]
    members.sort(key=lambda member: (member.id != leader_id, member.key.lower()))
    return members


def get_follow_target(character):
    """Return the current follow target if still valid."""

    ensure_party_state(character)
    target_id = character.db.brave_follow_target_id
    if not target_id:
        return None

    target = get_character_by_id(target_id)
    if not target or target == character:
        character.db.brave_follow_target_id = None
        return None

    if not character.db.brave_party_id or target.db.brave_party_id != character.db.brave_party_id:
        character.db.brave_follow_target_id = None
        return None

    return target


def set_follow_target(character, target):
    """Assign a party follow target."""

    ensure_party_state(character)
    character.db.brave_follow_target_id = getattr(target, "id", None)


def clear_follow_target(character):
    """Stop following anyone."""

    ensure_party_state(character)
    character.db.brave_follow_target_id = None


def get_followers(leader, location=None):
    """Return party members currently set to follow `leader`."""

    if not leader.db.brave_party_id:
        return []

    followers = [
        member
        for member in get_party_members(leader)
        if member.id != leader.id and get_follow_target(member) == leader
    ]
    if location is not None:
        followers = [member for member in followers if member.location == location]
    return followers


def get_present_party_members(character):
    """Return party members currently standing in the same room."""

    if not character.location:
        return []
    return [
        member for member in get_party_members(character) if member.location == character.location
    ]


def add_invite(target, leader_id):
    """Add a party invite to the target character."""

    ensure_party_state(target)
    invites = [invite for invite in (target.db.brave_party_invites or []) if invite != leader_id]
    invites.append(leader_id)
    target.db.brave_party_invites = invites


def remove_invite(target, leader_id):
    """Remove a party invite from the target character."""

    ensure_party_state(target)
    target.db.brave_party_invites = [
        invite for invite in (target.db.brave_party_invites or []) if invite != leader_id
    ]


def join_party(leader, member):
    """Join `member` to the leader's party, creating it if needed."""

    party_id = leader.db.brave_party_id or create_party(leader)
    set_party_membership(member, party_id, leader.id)
    clear_follow_target(member)
    remove_invite(member, leader.id)


def disband_party(leader):
    """Disband the leader's party and return the former member list."""

    members = get_party_members(leader)
    for member in members:
        clear_party_membership(member)
    return members


def handle_party_follow(leader, source_location, move_type="move"):
    """Move present followers after their leader changes rooms."""

    from world.browser_panels import send_browser_notice_event

    if move_type == "defeat" or not source_location or leader.location == source_location:
        return
    if not getattr(leader, "is_connected", False):
        return

    exit_obj = next(
        (
            candidate
            for candidate in source_location.exits
            if candidate.destination == leader.location
        ),
        None,
    )

    for follower in get_followers(leader, location=source_location):
        if not getattr(follower, "is_connected", False):
            continue
        if hasattr(follower, "get_active_encounter"):
            encounter = follower.get_active_encounter()
            if encounter and encounter.is_participant(follower):
                send_browser_notice_event(
                    follower,
                    f"You lose {leader.key} in the chaos of the fight.",
                    title="Party",
                    tone="warn",
                    icon="groups",
                    duration_ms=3200,
                )
                continue

        if exit_obj and exit_obj.access(follower, "traverse"):
            send_browser_notice_event(
                follower,
                f"You follow {leader.key}.",
                title="Party",
                tone="muted",
                icon="groups",
                duration_ms=2400,
            )
            exit_obj.at_traverse(follower, exit_obj.destination)
            continue

        if follower.move_to(leader.location, quiet=True, move_type="follow"):
            send_browser_notice_event(
                follower,
                f"You catch up with {leader.key}.",
                title="Party",
                tone="muted",
                icon="groups",
                duration_ms=2400,
            )
            follower.at_look(leader.location)
