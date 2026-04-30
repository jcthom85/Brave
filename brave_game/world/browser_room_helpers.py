"""Room-view helper payload builders shared by browser view modules."""

from world.activities import room_supports_activity
from world.chapel import get_active_blessing, is_chapel_room
from world.interactions import get_entity_response
from world.party import get_follow_target, get_party_leader, get_party_members
from world.resting import room_allows_rest
from world.browser_ui import (
    _action,
    _display_name,
    _item,
    _picker,
    _picker_option,
)

ROOM_ENTITY_KIND_ICONS = {
    "npc": "forum",
    "readable": "menu_book",
    "arcade": "videogame_asset",
    "object": "category",
}

ROOM_ENTITY_ID_ICONS = {
    "kitchen_hearth": "soup_kitchen",
}

TUTORIAL_TALK_ENTITY_IDS = {
    "sergeant_tamsin_vale",
    "quartermaster_nella_cobb",
    "courier_peep_marrow",
    "ringhand_brask",
    "captain_harl_rowan",
}

TUTORIAL_READ_ENTITY_IDS = {
    "tutorial_supply_board",
    "family_post_sign",
    "tutorial_damaged_cart",
}

def _format_dialogue_line(line):
    return str(line or "").strip()

def _build_talk_actions(target):
    actions = []
    entity_id = getattr(getattr(target, "db", None), "brave_entity_id", None)

    if entity_id == "leda_thornwick":
        actions.append(_action("Open Shop", "shop", "storefront", tone="accent"))
    elif entity_id == "torren_ironroot":
        actions.append(_action("Open Forge", "forge", "construction", tone="accent"))
    elif entity_id == "mistress_elira_thorne":
        actions.append(_action("Mastery", "mastery", "school", tone="accent"))
    elif entity_id == "mender_veska_flint":
        actions.append(_action("Open Tinkering", "tinker", "handyman", tone="accent"))

    return actions

def _build_world_interaction_picker(viewer, target):
    kind = getattr(getattr(target, "db", None), "brave_entity_kind", None)
    entity_id = getattr(getattr(target, "db", None), "brave_entity_id", None)
    title = _display_name(target) or getattr(target, "key", "Details")

    if kind == "npc":
        response = get_entity_response(viewer, target, "talk")
        body = [line.strip() for line in str(response or "").splitlines() if line.strip()]
        if not body:
            body = ["They have nothing to say right now."]
        options = [
            _picker_option(
                action["label"],
                command=action.get("command"),
                icon=action.get("icon"),
                meta=action.get("confirm"),
                tone=action.get("tone"),
            )
            for action in _build_talk_actions(target)
        ]
        options.append(_picker_option("Continue", icon="check_circle", tone="accent", close_picker=True))
        return _picker(title, body=body, options=options, title_icon="forum")

    if kind == "readable":
        response = get_entity_response(viewer, target, "read")
        body = [line.strip() for line in str(response or "").splitlines() if line.strip()]
        if not body:
            body = ["There is nothing legible here right now."]
        options = []
        if entity_id == "kitchen_hearth":
            options.append(_picker_option("Cook", command="cook", icon="restaurant", tone="accent"))
        return _picker(title, body=body, options=options, title_icon="menu_book")

    if kind == "arcade":
        description = [line.strip() for line in str(getattr(getattr(target, "db", None), "desc", "") or "").splitlines() if line.strip()]
        if not description:
            description = ["The cabinet hums softly, waiting for a coin and a steady hand."]
        return _picker(
            title,
            body=description,
            title_icon="sports_esports",
            options=[_picker_option("Play", command=f"arcade open {target.key}", icon="sports_esports", tone="accent")],
        )

    return None

def _short_direction(direction):
    token = str(direction or "").strip().lower()
    return {
        "north": "N",
        "east": "E",
        "south": "S",
        "west": "W",
        "up": "U",
        "down": "D",
    }.get(token, token.upper()[:3] or "?")

def _movement_command(direction, fallback):
    token = str(direction or "").strip().lower()
    return {
        "north": "n",
        "east": "e",
        "south": "s",
        "west": "w",
        "up": "u",
        "down": "d",
    }.get(token, fallback)

def _local_npc_keys(character):
    if not getattr(character, "location", None):
        return set()
    return {
        obj.key
        for obj in character.location.contents
        if getattr(getattr(obj, "db", None), "brave_entity_kind", None) == "npc"
    }

def _local_player_characters(character):
    if not getattr(character, "location", None):
        return []
    return [
        obj
        for obj in character.location.contents
        if obj != character and hasattr(obj, "ensure_brave_character") and getattr(obj, "is_connected", False)
    ]

def _format_room_threat_items(visible_threats):
    """Format visible hostile threats for the room view."""

    items = []
    for threat in visible_threats or []:
        inspect_lines = []
        display_name = str(threat.get("display_name") or threat.get("key") or "").strip()
        composition = str(threat.get("composition") or threat.get("detail") or "").strip()
        intro = str(threat.get("intro") or "").strip()
        if composition and composition != display_name:
            inspect_lines.append(composition)
        if intro:
            inspect_lines.append(intro)
        inspect_picker = _picker(
            display_name,
            body=inspect_lines,
            options=[
                _picker_option("Fight", command=threat.get("command") or "fight", icon="swords", tone="danger")
            ],
            picker_id=f"room-threat-{str(threat.get('key') or display_name).strip().lower().replace(' ', '-')}",
        )
        items.append(
            _item(
                display_name,
                icon=threat.get("icon") or "monster-skull",
                badge=threat.get("badge") or threat.get("count"),
                picker=inspect_picker,
                detail="Engaged" if threat.get("engaged") else None,
                tooltip=threat.get("tooltip"),
                marker_icon=threat.get("marker_icon"),
                actions=[
                    _action(
                        "Inspect",
                        None,
                        "search",
                        tone="muted",
                        picker=inspect_picker,
                    ),
                    _action(
                        "Fight",
                        threat.get("command") or "fight",
                        "swords",
                        tone="danger",
                    ),
                ],
            )
        )
    return items

def _format_room_entity_items(viewer, visible_entities, visible_chars):
    items = []

    kind_order = {"npc": 0, "readable": 1, "arcade": 2, "object": 3}
    sorted_entities = sorted(
        list(visible_entities or []),
        key=lambda obj: (kind_order.get((getattr(obj.db, "brave_entity_kind", "") or "object"), 3), obj.key.lower()),
    )
    for obj in sorted_entities:
        kind = getattr(obj.db, "brave_entity_kind", "") or "object"
        entity_id = getattr(obj.db, "brave_entity_id", None)
        label = obj.key if kind == "npc" else _display_name(obj)
        command = None
        picker = None
        on_open_command = None
        dismiss_bubble_speaker = None
        if kind == "npc":
            command = f"talk {obj.key}"
            picker = _build_world_interaction_picker(viewer, obj)
            if entity_id in TUTORIAL_TALK_ENTITY_IDS:
                on_open_command = f"_bravepopup talk {obj.key}"
                dismiss_bubble_speaker = obj.key
        elif kind == "readable":
            command = f"read {obj.key}"
            picker = _build_world_interaction_picker(viewer, obj)
            if entity_id in TUTORIAL_READ_ENTITY_IDS:
                on_open_command = f"_bravepopup read {obj.key}"
        elif kind == "arcade":
            command = f"arcade inspect {obj.key}"
            picker = _build_world_interaction_picker(viewer, obj)
        items.append(
            _item(
                label,
                icon=ROOM_ENTITY_ID_ICONS.get(entity_id, ROOM_ENTITY_KIND_ICONS.get(kind, "category")),
                command=command,
                picker=picker,
                actions=[
                    _action(
                        "Emote At",
                        None,
                        "sentiment_satisfied",
                        tone="muted",
                        picker=_build_targeted_room_emote_picker(obj.key),
                    ),
                    _action(
                        "Talk",
                        command,
                        "forum",
                        tone="accent",
                        picker=picker,
                        on_open_command=on_open_command,
                        dismiss_bubble_speaker=dismiss_bubble_speaker,
                    ),
                ] if kind == "npc" else None,
                on_open_command=on_open_command,
                dismiss_bubble_speaker=dismiss_bubble_speaker,
            )
        )

    viewer_party_id = getattr(getattr(viewer, "db", None), "brave_party_id", None)
    follow_target = get_follow_target(viewer) if viewer and viewer_party_id else None
    party_leader = get_party_leader(viewer) if viewer and viewer_party_id else None
    room = getattr(viewer, "location", None)
    encounter = getattr(getattr(room, "ndb", None), "brave_encounter", None) if room else None
    engaged_participant_ids = set()
    if encounter and getattr(encounter, "db", None):
        engaged_participant_ids = {
            int(participant_id)
            for participant_id in (getattr(encounter.db, "participants", None) or [])
            if participant_id is not None
        }

    char_entries = []
    for obj in list(visible_chars or []):
        party_id = getattr(getattr(obj, "db", None), "brave_party_id", None)
        same_party = bool(viewer_party_id and viewer_party_id == party_id)
        grouped = bool(party_id)
        engaged = bool(getattr(obj, "id", None) in engaged_participant_ids)
        following = bool(follow_target and follow_target.id == getattr(obj, "id", None))
        leader = bool(party_leader and party_leader.id == getattr(obj, "id", None))
        can_invite = bool(
            not party_id
            and (not viewer_party_id or (party_leader and party_leader.id == viewer.id and len(get_party_members(viewer)) < 4))
        )
        can_kick = bool(same_party and party_leader and party_leader.id == viewer.id)

        detail_bits = []
        if engaged:
            detail_bits.append("Engaged")
        elif same_party:
            detail_bits.append("Party")
        elif grouped:
            detail_bits.append("Grouped")
        if leader:
            detail_bits.append("Leader")
        if following:
            detail_bits.append("Following")

        priority = 0
        if engaged:
            priority -= 30
        if same_party:
            priority -= 24
        if leader:
            priority -= 18
        if following:
            priority -= 12
        if grouped:
            priority -= 6

        char_entries.append(
            (
                priority,
                obj.key.lower(),
                _item(
                    obj.key,
                    icon="person",
                    detail=" · ".join(detail_bits) if detail_bits else None,
                    marker_icon="swords" if engaged else None,
                    picker=_build_room_character_picker(
                        viewer,
                        obj,
                        same_party=same_party,
                        engaged=engaged,
                        following=following,
                        leader=leader,
                        can_invite=can_invite,
                        can_kick=can_kick,
                    ),
                ),
            )
        )

    items.extend(entry for _priority, _key, entry in sorted(char_entries, key=lambda value: (value[0], value[1])))

    return items

def _build_targeted_room_emote_picker(target_name):
    return _picker(
        f"Emote At {target_name}",
        subtitle="Choose a quick social emote aimed at this person.",
        title_icon="sentiment_satisfied",
        options=[
            _picker_option("Smile", command=f"emote smiles at {target_name}", icon="sentiment_satisfied"),
            _picker_option("Nod", command=f"emote nods to {target_name}", icon="how_to_reg"),
            _picker_option("Wave", command=f"emote waves at {target_name}", icon="waving_hand"),
            _picker_option("Laugh", command=f"emote laughs with {target_name}", icon="sentiment_very_satisfied"),
            _picker_option("Bow", command=f"emote bows to {target_name}", icon="self_improvement"),
        ],
    )

def _build_room_character_picker(viewer, obj, *, same_party=False, engaged=False, following=False, leader=False, can_invite=False, can_kick=False):
    target_name = obj.key
    subtitle = "Choose how to interact with this person nearby."
    options = [
        _picker_option(
            "Whisper",
            prefill=f"whisper {target_name} = ",
            icon="forum",
            chat_open=True,
            chat_prompt=f"Whisper to {target_name}...",
        ),
        _picker_option(
            "Emote At",
            icon="sentiment_satisfied",
            picker=_build_targeted_room_emote_picker(target_name),
        ),
    ]
    if same_party:
        if following:
            options.append(_picker_option("Stay", command="party stay", icon="do_not_disturb_on", meta="Stop following for now."))
        else:
            options.append(_picker_option("Follow", command=f"party follow {target_name}", icon="directions_walk", meta=f"Keep pace with {target_name}."))
        options.append(_picker_option("Where", command="party where", icon="location_searching", meta="Check your party's current location."))
        if can_kick:
            options.append(
                _picker_option(
                    "Kick",
                    command=f"party kick {target_name}",
                    icon="person_remove",
                    meta=f"Remove {target_name} from your party.",
                    tone="danger",
                )
            )
    elif can_invite:
        options.append(_picker_option("Invite", command=f"party invite {target_name}", icon="person_add"))

    body = []
    if same_party:
        body.append("Party member")
    else:
        body.append("Nearby player")
    if leader:
        body.append("Party leader")
    if following:
        body.append("You are following them")
    if engaged:
        body.append("Already engaged in the current fight")

    return _picker(
        target_name,
        subtitle=subtitle,
        title_icon="person",
        body=body,
        options=options,
    )

def _build_room_social_presence(viewer, visible_chars):
    chars = list(visible_chars or [])
    if not chars:
        return {
            "nearby_total": 0,
            "engaged_total": 0,
            "party_total": 0,
            "group_count": 0,
            "people": [],
        }

    viewer_party_id = getattr(getattr(viewer, "db", None), "brave_party_id", None)
    follow_target = get_follow_target(viewer) if viewer and viewer_party_id else None
    party_leader = get_party_leader(viewer) if viewer and viewer_party_id else None
    room = getattr(viewer, "location", None)
    encounter = getattr(getattr(room, "ndb", None), "brave_encounter", None) if room else None
    engaged_participant_ids = set()
    if encounter and getattr(encounter, "db", None):
        engaged_participant_ids = {
            int(participant_id)
            for participant_id in (getattr(encounter.db, "participants", None) or [])
            if participant_id is not None
        }

    people = []
    grouped_party_ids = set()
    nearby_total = 0
    engaged_total = 0
    party_total = 0

    for obj in chars:
        nearby_total += 1
        party_id = getattr(getattr(obj, "db", None), "brave_party_id", None)
        same_party = bool(viewer_party_id and viewer_party_id == party_id)
        grouped = bool(party_id)
        engaged = bool(getattr(obj, "id", None) in engaged_participant_ids)
        following = bool(follow_target and follow_target.id == getattr(obj, "id", None))
        leader = bool(party_leader and party_leader.id == getattr(obj, "id", None))

        if grouped:
            grouped_party_ids.add(party_id)
        if engaged:
            engaged_total += 1
        if same_party:
            party_total += 1

        lines = []
        if same_party:
            lines.append("Party member")
        elif grouped:
            lines.append("Grouped nearby")
        else:
            lines.append("Nearby player")
        if leader:
            lines.append("Party leader")
        if following:
            lines.append("You are following them")
        if engaged:
            lines.append("Already in the current fight")

        priority = 0
        if same_party:
            priority -= 40
        if leader:
            priority -= 30
        if following:
            priority -= 24
        if engaged:
            priority -= 18
        if grouped:
            priority -= 8

        badge = "Engaged" if engaged else ("Party" if same_party else "")

        can_invite = bool(
            not party_id
            and (not viewer_party_id or (party_leader and party_leader.id == viewer.id and len(get_party_members(viewer)) < 4))
        )
        can_kick = bool(same_party and party_leader and party_leader.id == viewer.id)
        people.append(
            {
                "name": obj.key,
                "summary": lines[0],
                "detail": " · ".join(lines[1:]),
                "badge": badge,
                "badge_tone": "danger" if engaged else ("muted" if same_party else ""),
                "priority": priority,
                "picker": _build_room_character_picker(
                    viewer,
                    obj,
                    same_party=same_party,
                    engaged=engaged,
                    following=following,
                    leader=leader,
                    can_invite=can_invite,
                    can_kick=can_kick,
                ),
            }
        )

    people.sort(key=lambda entry: (entry["priority"], entry["name"].lower()))

    return {
        "nearby_total": nearby_total,
        "engaged_total": engaged_total,
        "party_total": party_total,
        "group_count": len(grouped_party_ids),
        "people": [
            {
                "name": entry["name"],
                "summary": entry["summary"],
                "detail": entry["detail"],
                "badge": entry["badge"],
                "badge_tone": entry["badge_tone"],
                "picker": entry["picker"],
            }
            for entry in people
        ],
    }

def _character_in_combat(character):
    encounter_getter = getattr(character, "get_active_encounter", None)
    if not callable(encounter_getter):
        return False
    encounter = encounter_getter()
    return bool(encounter and encounter.is_participant(character))

def _build_room_emote_picker():
    return _picker(
        "Emote",
        subtitle="Choose a social emote.",
        options=[
            {"label": "Smile", "icon": "sentiment_satisfied", "command": "emote smile"},
            {"label": "Nod", "icon": "how_to_reg", "command": "emote nod"},
            {"label": "Wave", "icon": "waving_hand", "command": "emote wave"},
            {"label": "Shrug", "icon": "air", "command": "emote shrug"},
            {"label": "Laugh", "icon": "sentiment_very_satisfied", "command": "emote laugh"},
            {"label": "Frown", "icon": "sentiment_dissatisfied", "command": "emote frown"},
            {"label": "Bow", "icon": "self_improvement", "command": "emote bow"},
            {"label": "Think", "icon": "psychology", "command": "emote think"},
        ],
    )

def _format_room_context_action_items(room, viewer):
    """Return room-level buttons for core actions that do not belong to one object."""

    if not room or not viewer or _character_in_combat(viewer):
        return []

    local_entities = list(getattr(room, "contents", []) or [])
    local_arcades = [
        obj
        for obj in local_entities
        if getattr(getattr(obj, "db", None), "brave_entity_kind", None) == "arcade"
    ]

    items = []
    if room_allows_rest(room):
        items.append(_item("Rest", icon="campfire", command="rest"))

    if local_arcades:
        items.append(_item("Play", icon="sports_esports", command="arcade"))

    if room_supports_activity(room, "fishing"):
        fishing_state = getattr(getattr(viewer, "ndb", None), "brave_fishing", None) or {}
        if fishing_state.get("phase") == "bite":
            items.append(_item("Reel", icon="phishing", command="reel", detail="Something is biting."))
        elif fishing_state.get("phase") == "waiting":
            items.append(_item("Line in the water", icon="waves", detail="Wait for a bite."))
        else:
            items.append(_item("Fish", icon="fish", command="fish"))
    if room_supports_activity(room, "cooking"):
        items.append(_item("Cook", icon="restaurant", command="cook"))
    if room_supports_activity(room, "tinkering"):
        items.append(_item("Tinker", icon="build", command="tinker"))
    if room_supports_activity(room, "mastery"):
        items.append(_item("Mastery", icon="school", command="mastery"))

    if is_chapel_room(room):
        blessing = get_active_blessing(viewer)
        items.append(
            _item(
                "Pray" if not blessing else "Review Blessing",
                icon="notifications_active",
                command="pray",
                detail=None if not blessing else "Dawn Bell blessing active.",
            )
        )

    items.append(_item("Emote", icon="sentiment_satisfied", picker=_build_room_emote_picker(), tooltip="Choose a social emote."))
    return items
