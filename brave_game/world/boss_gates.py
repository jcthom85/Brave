"""Room-roster boss gate staging and resolution."""

import time
import uuid

from evennia.utils import create

from world.bootstrap import get_room
from world.character_icons import get_class_icon
from world.content import get_content_registry

CONTENT = get_content_registry()
BOSS_GATES = CONTENT.systems.boss_gates
CHARACTER_CONTENT = CONTENT.characters
BOSS_GATE_SLOT_COUNT = 4
BOSS_GATE_REJOIN_COOLDOWN_SECONDS = 20


def _normalize_token(value):
    return "".join(char for char in str(value or "").lower() if char.isalnum())


def get_boss_gate(gate_key):
    return BOSS_GATES.get(str(gate_key or ""))


def _character_id(character):
    return getattr(character, "id", None)


def _room_id(room):
    return str(getattr(getattr(room, "db", None), "brave_room_id", "") or "")


def _boss_clears(character):
    clears = getattr(getattr(character, "db", None), "brave_boss_clears", None) or {}
    return dict(clears) if isinstance(clears, dict) else {}


def character_has_cleared_gate(character, gate_key):
    return bool(_boss_clears(character).get(str(gate_key or "")))


def character_needs_gate(character, gate_key):
    return bool(character and gate_key and not character_has_cleared_gate(character, gate_key))


def set_character_gate_clear(character, gate_key):
    clears = _boss_clears(character)
    clears[str(gate_key)] = True
    character.db.brave_boss_clears = clears


def room_characters(room):
    occupants = []
    for candidate in list(getattr(room, "contents", []) or []):
        if not hasattr(candidate, "db") or not hasattr(candidate, "location"):
            continue
        if getattr(candidate, "location", None) != room:
            continue
        occupants.append(candidate)
    occupants.sort(key=lambda char: (str(getattr(char, "key", "")).lower(), getattr(char, "id", 0) or 0))
    return occupants


def connected_room_characters(room):
    return [char for char in room_characters(room) if bool(getattr(char, "is_connected", False))]


def find_gate_for_preview(room, preview):
    if not room or not preview:
        return None, None
    room_id = _room_id(room)
    encounter_key = str((preview or {}).get("encounter_key") or (preview or {}).get("key") or "")
    enemy_keys = {str(enemy.get("template_key") or enemy.get("key") or "") for enemy in (preview or {}).get("enemies", [])}
    for gate_key, gate in BOSS_GATES.items():
        if gate.get("trigger_room_id") != room_id:
            continue
        if gate.get("encounter_key") == encounter_key:
            return gate_key, gate
        if gate.get("boss_enemy_key") in enemy_keys:
            return gate_key, gate
    return None, None


def find_gate_for_exit(exit_obj):
    gate_key = getattr(getattr(exit_obj, "db", None), "brave_boss_gate", None)
    gate = get_boss_gate(gate_key)
    return (gate_key, gate) if gate else (None, None)


def _now():
    return time.time()


def _room_gate_runs(room):
    runs = getattr(getattr(room, "ndb", None), "brave_boss_gate_runs", None) or {}
    return {str(run_id): dict(run) for run_id, run in dict(runs).items()}


def _save_room_gate_runs(room, runs):
    room.ndb.brave_boss_gate_runs = {str(run_id): dict(run) for run_id, run in dict(runs or {}).items()}


def _legacy_clear_room_gate_staging(room):
    if hasattr(getattr(room, "ndb", None), "brave_boss_gate_staging"):
        room.ndb.brave_boss_gate_staging = {}


def _get_gate_run(room, run_id):
    return _room_gate_runs(room).get(str(run_id or ""))


def _save_gate_run(room, run):
    runs = _room_gate_runs(room)
    runs[str(run["run_id"])] = dict(run)
    _save_room_gate_runs(room, runs)


def _delete_gate_run(room, run_id):
    runs = _room_gate_runs(room)
    runs.pop(str(run_id or ""), None)
    _save_room_gate_runs(room, runs)


def _participant_available(character, room):
    if not character or getattr(character, "location", None) != room:
        return False
    if not bool(getattr(character, "is_connected", False)):
        return False
    resources = getattr(getattr(character, "db", None), "brave_resources", None) or {}
    if int(resources.get("hp", 1) or 0) <= 0:
        return False
    getter = getattr(character, "get_active_encounter", None)
    encounter = getter() if callable(getter) else getattr(getattr(character, "ndb", None), "brave_encounter", None)
    return not bool(encounter)


def _character_summary(character):
    race_key = str(getattr(getattr(character, "db", None), "brave_race", "") or CHARACTER_CONTENT.starting_race)
    class_key = str(getattr(getattr(character, "db", None), "brave_class", "") or CHARACTER_CONTENT.starting_class)
    race = CHARACTER_CONTENT.races.get(race_key, {})
    class_data = CHARACTER_CONTENT.classes.get(class_key, {})
    return {
        "id": _character_id(character),
        "name": getattr(character, "key", "Someone"),
        "race_key": race_key,
        "race_name": race.get("name", race_key.replace("_", " ").title()),
        "class_key": class_key,
        "class_name": class_data.get("name", class_key.replace("_", " ").title()),
        "class_icon": get_class_icon(class_key, class_data),
    }


def _normalize_slot_ids(slot_ids):
    slots = list(slot_ids or [])[:BOSS_GATE_SLOT_COUNT]
    while len(slots) < BOSS_GATE_SLOT_COUNT:
        slots.append(None)
    return slots


def _run_participant_ids(run):
    return [char_id for char_id in _normalize_slot_ids(run.get("slot_ids")) if char_id]


def _find_character_in_room(room, character_id):
    try:
        character_id = int(character_id)
    except (TypeError, ValueError):
        return None
    for occupant in room_characters(room):
        if getattr(occupant, "id", None) == character_id:
            return occupant
    return None


def _run_has_open_slot(run):
    return any(slot_id is None for slot_id in _normalize_slot_ids(run.get("slot_ids")))


def _run_kick_remaining(run, character):
    kicked_until = dict(run.get("kicked_until") or {})
    until = float(kicked_until.get(str(getattr(character, "id", ""))) or 0)
    remaining = int(round(until - _now()))
    return max(0, remaining)


def build_gate_roster_snapshot(character, gate_key):
    gate = get_boss_gate(gate_key)
    room = getattr(character, "location", None)
    roster = {
        "needs_clear": [],
        "can_assist": [],
        "unavailable": [],
    }
    if not gate or not room:
        return roster
    for occupant in room_characters(room):
        entry = {
            "id": _character_id(occupant),
            "name": getattr(occupant, "key", "Someone"),
            "ready": False,
        }
        if not _participant_available(occupant, room):
            roster["unavailable"].append(entry)
        elif character_needs_gate(occupant, gate_key):
            roster["needs_clear"].append(entry)
        elif gate.get("allow_non_party_helpers", True):
            roster["can_assist"].append(entry)
    return roster


def get_waiting_gate_runs(room, gate_key):
    """Return waiting boss-gate runs for this room/gate."""

    runs = []
    occupants = {occupant.id: occupant for occupant in connected_room_characters(room)}
    changed = False
    all_runs = _room_gate_runs(room)
    for run_id, run in list(all_runs.items()):
        if run.get("gate_key") != gate_key:
            continue
        slot_ids = _normalize_slot_ids(run.get("slot_ids"))
        initiator_id = run.get("initiator_id")
        if initiator_id not in occupants:
            all_runs.pop(run_id, None)
            changed = True
            continue
        run["slot_ids"] = slot_ids
        runs.append(run)
    if changed:
        _save_room_gate_runs(room, all_runs)
    runs.sort(key=lambda run: (float(run.get("created_at", 0) or 0), str(run.get("run_id", ""))))
    return runs


def _room_has_gate_needer(room, gate_key):
    return any(
        _participant_available(occupant, room) and character_needs_gate(occupant, gate_key)
        for occupant in room_characters(room)
    )


def _ensure_gate_available(character, gate_key):
    gate = get_boss_gate(gate_key)
    room = getattr(character, "location", None)
    if not gate or not room:
        return False, None, None, "No boss gate is ready here."
    if _room_id(room) != gate.get("trigger_room_id"):
        return False, gate, room, "That boss is not staged here."
    if not _room_has_gate_needer(room, gate_key):
        return False, gate, room, f"{gate.get('name', gate_key)} no longer blocks anyone here."
    return True, gate, room, ""


def create_gate_run(initiator, gate_key):
    """Create a waiting boss-gate run with the initiator in slot one."""

    ok, gate, room, message = _ensure_gate_available(initiator, gate_key)
    if not ok:
        return False, message
    if not _participant_available(initiator, room):
        return False, "You cannot start that boss run right now."
    run_id = f"{gate_key}-{initiator.id}-{uuid.uuid4().hex[:8]}"
    run = {
        "run_id": run_id,
        "gate_key": gate_key,
        "initiator_id": initiator.id,
        "slot_ids": [initiator.id, None, None, None],
        "created_at": _now(),
        "kicked_until": {},
    }
    _save_gate_run(room, run)
    _legacy_clear_room_gate_staging(room)
    send_gate_run_payload(initiator, run_id)
    return True, run_id


def _run_slot_payload(room, run, viewer):
    slot_ids = _normalize_slot_ids(run.get("slot_ids"))
    initiator_id = run.get("initiator_id")
    slots = []
    for index, character_id in enumerate(slot_ids):
        if not character_id:
            slots.append({"index": index, "empty": True, "label": f"Open Slot {index + 1}"})
            continue
        character = _find_character_in_room(room, character_id)
        summary = _character_summary(character) if character else {
            "id": character_id,
            "name": "Missing Player",
            "race_name": "Unknown",
            "class_name": "Unknown",
            "class_icon": "player",
        }
        summary.update(
            {
                "index": index,
                "empty": False,
                "caller": character_id == initiator_id,
                "can_remove": viewer and viewer.id == initiator_id and character_id != initiator_id,
            }
        )
        if summary["can_remove"]:
            summary["remove_command"] = f"bossgate remove {run.get('run_id')} {character_id}"
        slots.append(summary)
    return slots


def build_gate_run_payload(viewer, run_id):
    """Build the dedicated boss-run overlay payload."""

    room = getattr(viewer, "location", None)
    run = _get_gate_run(room, run_id) if room else None
    if not run:
        return {"kind": "closed", "title": "Boss Run", "message": "That boss run is no longer waiting."}
    gate_key = run.get("gate_key")
    gate = get_boss_gate(gate_key) or {}
    slots = _run_slot_payload(room, run, viewer)
    filled = len([slot for slot in slots if not slot.get("empty")])
    is_initiator = bool(viewer and viewer.id == run.get("initiator_id"))
    in_run = viewer and viewer.id in _run_participant_ids(run)
    actions = []
    if is_initiator:
        actions.append({"label": "Start Encounter", "command": f"bossgate start {run_id}", "icon": "swords", "tone": "danger"})
        actions.append({"label": "Not Now", "command": f"bossgate cancel {run_id}", "icon": "close", "tone": "muted"})
    elif in_run:
        actions.append({"label": "Leave Run", "command": f"bossgate leave {run_id}", "icon": "logout", "tone": "muted"})
    elif _run_has_open_slot(run):
        remaining = _run_kick_remaining(run, viewer)
        if remaining:
            actions.append({"label": f"Wait {remaining}s", "icon": "hourglass_empty", "tone": "muted", "disabled": True})
        else:
            actions.append({"label": "Join Run", "command": f"bossgate join {run_id}", "icon": "person_add", "tone": "accent"})
    caller = _find_character_in_room(room, run.get("initiator_id"))
    return {
        "kind": "run",
        "gate_key": gate_key,
        "run_id": run_id,
        "title": gate.get("name", gate_key),
        "summary": gate.get("summary", "A hard fight blocks the way ahead."),
        "caller": getattr(caller, "key", "Someone"),
        "filled": filled,
        "max_slots": BOSS_GATE_SLOT_COUNT,
        "viewer_id": getattr(viewer, "id", None),
        "is_initiator": is_initiator,
        "slots": slots,
        "actions": actions,
    }


def build_gate_run_choice_payload(viewer, gate_key):
    """Build a run-selection overlay payload for a boss gate."""

    room = getattr(viewer, "location", None)
    gate = get_boss_gate(gate_key) or {}
    runs = []
    for run in get_waiting_gate_runs(room, gate_key):
        caller = _find_character_in_room(room, run.get("initiator_id"))
        filled = len(_run_participant_ids(run))
        remaining = _run_kick_remaining(run, viewer)
        full = not _run_has_open_slot(run)
        runs.append(
            {
                "run_id": run.get("run_id"),
                "caller": getattr(caller, "key", "Someone"),
                "filled": filled,
                "max_slots": BOSS_GATE_SLOT_COUNT,
                "disabled": bool(full or remaining),
                "meta": "Full" if full else (f"Wait {remaining}s" if remaining else f"{filled}/{BOSS_GATE_SLOT_COUNT} slots"),
                "command": "" if full or remaining else f"bossgate join {run.get('run_id')}",
            }
        )
    return {
        "kind": "choice",
        "gate_key": gate_key,
        "title": gate.get("name", gate_key),
        "summary": gate.get("summary", "A hard fight blocks the way ahead."),
        "runs": runs,
        "actions": [
            {"label": "Start New Run", "command": f"bossgate new {gate_key}", "icon": "add_circle", "tone": "accent"},
            {"label": "Not Now", "close": True, "icon": "do_not_disturb_on", "tone": "muted"},
        ],
    }


def _send_gate_payload(character, payload):
    from world.browser_panels import send_webclient_event

    send_webclient_event(character, brave_boss_gate=payload)


def send_gate_run_payload(character, run_id):
    payload = build_gate_run_payload(character, run_id)
    _send_gate_payload(character, payload)
    return payload


def send_gate_choice_payload(character, gate_key):
    payload = build_gate_run_choice_payload(character, gate_key)
    _send_gate_payload(character, payload)
    return payload


def broadcast_gate_run_payload(room, run_id):
    run = _get_gate_run(room, run_id)
    if not run:
        return
    for character_id in _run_participant_ids(run):
        character = _find_character_in_room(room, character_id)
        if character:
            send_gate_run_payload(character, run_id)


def start_gate_ready_check(character, gate_key):
    """Open boss-gate run creation or run selection for a character."""

    ok, gate, room, message = _ensure_gate_available(character, gate_key)
    if not ok:
        return False, message
    runs = get_waiting_gate_runs(room, gate_key)
    if not runs:
        created, result = create_gate_run(character, gate_key)
        if not created:
            return False, result
        return True, f"{gate.get('name', gate_key)} run started."
    send_gate_choice_payload(character, gate_key)
    return True, f"{gate.get('name', gate_key)} has waiting runs."


def join_gate_run(character, run_id):
    room = getattr(character, "location", None)
    run = _get_gate_run(room, run_id) if room else None
    if not run:
        return False, "That boss run is no longer waiting."
    if not _participant_available(character, room):
        return False, "You cannot join that boss run right now."
    if character.id in _run_participant_ids(run):
        send_gate_run_payload(character, run_id)
        return True, "You are already in that boss run."
    remaining = _run_kick_remaining(run, character)
    if remaining:
        return False, f"You can try to join that run again in {remaining} seconds."
    slot_ids = _normalize_slot_ids(run.get("slot_ids"))
    try:
        index = slot_ids.index(None)
    except ValueError:
        return False, "That boss run is full."
    slot_ids[index] = character.id
    run["slot_ids"] = slot_ids
    _save_gate_run(room, run)
    broadcast_gate_run_payload(room, run_id)
    return True, "You join the boss run."


def leave_gate_run(character, run_id):
    room = getattr(character, "location", None)
    run = _get_gate_run(room, run_id) if room else None
    if not run:
        return False, "That boss run is no longer waiting."
    if character.id == run.get("initiator_id"):
        return cancel_gate(character, run_id)
    slot_ids = [None if slot_id == character.id else slot_id for slot_id in _normalize_slot_ids(run.get("slot_ids"))]
    run["slot_ids"] = slot_ids
    _save_gate_run(room, run)
    broadcast_gate_run_payload(room, run_id)
    return True, "You leave the boss run."


def remove_gate_run_member(caller, run_id, target_id):
    room = getattr(caller, "location", None)
    run = _get_gate_run(room, run_id) if room else None
    if not run:
        return False, "That boss run is no longer waiting."
    if caller.id != run.get("initiator_id"):
        return False, "Only the player who started this run can remove players."
    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return False, "That player is not in this boss run."
    if target_id == run.get("initiator_id"):
        return False, "The caller cannot be removed from their own run."
    slot_ids = _normalize_slot_ids(run.get("slot_ids"))
    if target_id not in slot_ids:
        return False, "That player is not in this boss run."
    target = _find_character_in_room(room, target_id)
    run["slot_ids"] = [None if slot_id == target_id else slot_id for slot_id in slot_ids]
    kicked_until = dict(run.get("kicked_until") or {})
    kicked_until[str(target_id)] = _now() + BOSS_GATE_REJOIN_COOLDOWN_SECONDS
    run["kicked_until"] = kicked_until
    _save_gate_run(room, run)
    broadcast_gate_run_payload(room, run_id)
    if target:
        _send_gate_payload(
            target,
            {
                "kind": "removed",
                "title": get_boss_gate(run.get("gate_key")).get("name", "Boss Run"),
                "message": "You were removed from this run. You can try that run again in 20 seconds.",
                "actions": [
                    {"label": "Start New Run", "command": f"bossgate new {run.get('gate_key')}", "icon": "add_circle", "tone": "accent"},
                    {"label": "Close", "close": True, "icon": "close", "tone": "muted"},
                ],
            },
        )
    return True, "Player removed from the boss run."


def cancel_gate(character, run_id=None):
    room = getattr(character, "location", None)
    runs = _room_gate_runs(room) if room else {}
    run = _get_gate_run(room, run_id) if run_id else None
    if run is None:
        for candidate in runs.values():
            if candidate.get("initiator_id") == character.id:
                run = candidate
                run_id = candidate.get("run_id")
                break
    if not run:
        return False, "No boss run is being staged here."
    if run.get("initiator_id") != character.id:
        return False, "Only the player who started this run can cancel it."
    participant_ids = _run_participant_ids(run)
    _delete_gate_run(room, run_id)
    for participant_id in participant_ids:
        participant = _find_character_in_room(room, participant_id)
        if participant:
            _send_gate_payload(participant, {"kind": "closed", "title": "Boss Run Cancelled", "message": "The run was called off."})
    return True, "Boss run cancelled."


def _participants_for_run(room, run):
    occupants = {occupant.id: occupant for occupant in connected_room_characters(room)}
    participants = []
    for character_id in _run_participant_ids(run):
        character = occupants.get(character_id)
        if character and _participant_available(character, room):
            participants.append(character)
    return participants


def launch_gate_run(character, run_id=None):
    from typeclasses.scripts import BraveEncounter, COMBAT_MAX_PLAYER_CHARACTERS

    room = getattr(character, "location", None)
    run = _get_gate_run(room, run_id) if run_id else None
    if run is None and room:
        for candidate in _room_gate_runs(room).values():
            if candidate.get("initiator_id") == character.id:
                run = candidate
                run_id = candidate.get("run_id")
                break
    if not run:
        return False, "No boss run is being staged here."
    if run.get("initiator_id") != character.id:
        return False, "Only the player who started this run can start it."

    gate_key = run.get("gate_key")
    gate = get_boss_gate(gate_key)
    if not gate:
        return False, "That boss gate is no longer configured."

    max_participants = min(int(gate.get("max_participants") or COMBAT_MAX_PLAYER_CHARACTERS), COMBAT_MAX_PLAYER_CHARACTERS)
    participants = _participants_for_run(room, run)[:max_participants]
    if not participants:
        return False, "No one is ready to face the boss."
    if not any(character_needs_gate(participant, gate_key) for participant in participants):
        return False, "No one in the run needs this gate clear."

    encounter_data = _resolve_encounter_data(gate)
    if not encounter_data:
        return False, "The boss encounter is missing from content."

    temp_room = create.create_object(
        typeclass="typeclasses.rooms.Room",
        key=f"{gate.get('name', gate_key)} Run",
        nohome=True,
    )
    temp_room.db.desc = gate.get("instance_desc") or "The fight closes around the committed group."
    temp_room.db.brave_room_id = f"bossrun:{gate_key}:{getattr(temp_room, 'id', 'new')}"
    temp_room.db.brave_safe = False
    temp_room.db.brave_boss_gate_temp = True
    temp_room.db.brave_boss_gate_entry_room_id = gate.get("entry_room_id") or gate.get("trigger_room_id")
    temp_room.db.brave_boss_gate_success_room_id = gate.get("success_room_id")
    temp_room.db.brave_boss_gate_failure_room_id = gate.get("failure_room_id") or gate.get("entry_room_id")

    needed_at_start = [participant.id for participant in participants if character_needs_gate(participant, gate_key)]
    for occupant in room_characters(room):
        if occupant.id in _run_participant_ids(run):
            _send_gate_payload(occupant, {"kind": "closed", "title": gate.get("name", gate_key), "message": "The run begins."})
    for participant in participants:
        participant.move_to(temp_room, quiet=True, move_type="bossgate")

    encounter = create.create_script(
        BraveEncounter,
        key="brave_encounter",
        obj=temp_room,
        autostart=False,
        persistent=False,
    )
    encounter.configure(gate.get("trigger_room_id"), encounter_data, expected_party_size=len(participants))
    encounter.db.boss_gate_key = gate_key
    encounter.db.boss_gate_needed_at_start = needed_at_start
    encounter.db.boss_gate_entry_room_id = gate.get("entry_room_id") or gate.get("trigger_room_id")
    encounter.db.boss_gate_success_room_id = gate.get("success_room_id")
    encounter.db.boss_gate_failure_room_id = gate.get("failure_room_id") or gate.get("entry_room_id")
    encounter.start()
    for participant in participants:
        encounter.add_participant(participant)
    _delete_gate_run(room, run_id)
    return True, encounter


def _resolve_encounter_data(gate):
    encounter_key = gate.get("encounter_key")
    for encounter in CONTENT.encounters.get_room_encounters(gate.get("trigger_room_id")):
        if encounter.get("key") == encounter_key:
            return dict(encounter)
    return None


def ready_for_gate(character, gate_key=None):
    """Compatibility wrapper: open/create a run instead of text readiness."""

    if not gate_key:
        room = getattr(character, "location", None)
        runs = list(_room_gate_runs(room).values()) if room else []
        gate_key = runs[0].get("gate_key") if runs else None
    return start_gate_ready_check(character, gate_key)


def resolve_gate_victory(encounter, participants):
    gate_key = getattr(getattr(encounter, "db", None), "boss_gate_key", None)
    if not gate_key:
        return
    needed_at_start = set(getattr(encounter.db, "boss_gate_needed_at_start", None) or [])
    success_room = get_room(getattr(encounter.db, "boss_gate_success_room_id", None))
    for participant in participants:
        if participant.id in needed_at_start and encounter._participant_eligible_for_enemy_credit(
            participant,
            {"tags": ["boss"]},
        ):
            set_character_gate_clear(participant, gate_key)
            participant.msg("|gThe way opens for you.|n")
        if success_room and getattr(participant, "location", None) == encounter.obj:
            participant.move_to(success_room, quiet=True, move_type="bossgate")


def resolve_gate_defeat(encounter):
    gate_key = getattr(getattr(encounter, "db", None), "boss_gate_key", None)
    if not gate_key:
        return
    failure_room = get_room(getattr(encounter.db, "boss_gate_failure_room_id", None))
    if not failure_room:
        return
    for participant in encounter.get_registered_participants():
        if getattr(participant, "location", None) == encounter.obj:
            participant.move_to(failure_room, quiet=True, move_type="bossgate")


def cleanup_gate_instance(encounter):
    room = getattr(encounter, "obj", None)
    if room and bool(getattr(getattr(room, "db", None), "brave_boss_gate_temp", False)):
        try:
            room.delete()
        except Exception:
            pass
