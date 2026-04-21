"""Roaming hostile party management for Brave."""

from __future__ import annotations

import random
import time

from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.scripts.scripts import DefaultScript
from evennia.utils import create
from evennia.utils.logger import log_trace

from world.bootstrap import get_room
from world.content import get_content_registry
from world.navigation import get_exit_direction, sort_exits

CONTENT = get_content_registry()
ROAMING_CONTENT = CONTENT.encounters
ROAMING_SCRIPT_KEY = "brave_roaming_party_manager"
ROAMING_SCRIPT_TYPECLASS = "world.roaming.BraveRoamingPartyManager"
ROAMING_TICK_INTERVAL = 10
ROAMING_REGIONS = {party.get("region") for party in ROAMING_CONTENT.get_roaming_parties() if party.get("region")}


def _is_connected_character(obj):
    return bool(
        obj
        and getattr(obj, "is_connected", False)
        and obj.is_typeclass("typeclasses.characters.Character", exact=False)
    )


def _room_characters(room):
    if not room:
        return []
    return [obj for obj in room.contents if _is_connected_character(obj)]


def _holds_combat_result(character):
    """Return whether this character should ignore ambient room refreshes."""

    return bool(getattr(getattr(character, "ndb", None), "brave_showing_combat_result", False))


def _party_definition_to_state(party_definition):
    encounter = dict(party_definition.get("encounter") or {})
    encounter.setdefault("key", party_definition.get("key"))
    encounter.setdefault("title", encounter.get("key", "Hostile Party"))
    encounter.setdefault("intro", "")
    encounter.setdefault("enemies", list(encounter.get("enemies") or []))

    interval = max(15, int(party_definition.get("interval", 90) or 90))
    respawn_delay = max(0, int(party_definition.get("respawn_delay", interval * 2) or 0))
    start_room_id = str(party_definition.get("start_room") or "").strip()
    return {
        "key": str(party_definition.get("key") or "").strip(),
        "region": str(party_definition.get("region") or "").strip(),
        "start_room_id": start_room_id,
        "room_id": start_room_id,
        "avoid_safe": bool(party_definition.get("avoid_safe", True)),
        "interval": interval,
        "respawn_delay": respawn_delay,
        "next_move_at": 0.0,
        "respawn_at": 0.0,
        "engaged": False,
        "encounter": encounter,
        "last_room_id": start_room_id,
    }


def _resolve_room_ref(room_ref):
    """Resolve a stored room reference to a Brave room object."""

    if not room_ref:
        return None

    room = get_room(room_ref)
    if room:
        return room

    try:
        room = ObjectDB.objects.get(id=int(room_ref))
    except (TypeError, ValueError, ObjectDB.DoesNotExist):
        return None

    return room if getattr(room.db, "brave_room_id", None) else None


def _stable_room_id(room_ref):
    """Return the Brave room id for any supported room reference."""

    room = _resolve_room_ref(room_ref)
    if room:
        return getattr(room.db, "brave_room_id", None)
    return str(room_ref or "").strip() or None


def build_roaming_room_preview(room):
    """Return a visible room-threat preview from roaming party state, if any."""

    if not room or getattr(room.db, "brave_safe", False):
        return None

    parties = get_roaming_parties_for_room(room)
    if not parties:
        return None

    parties = [party for party in parties if party.get("room_id") == getattr(room.db, "brave_room_id", None)]
    if not parties:
        return None

    from typeclasses.scripts import BraveEncounter

    combined_enemies = []
    titles = []
    intros = []
    for party in parties:
        encounter = dict(party.get("encounter") or {})
        titles.append(str(encounter.get("title") or party.get("key") or "Hostile Party"))
        intro = str(encounter.get("intro") or "").strip()
        if intro:
            intros.append(intro)
        combined_enemies.extend(list(encounter.get("enemies") or []))

    if not combined_enemies:
        return None

    encounter_data = {
        "key": parties[0].get("key") or "roaming_party",
        "title": titles[0] if len(titles) == 1 else "Roaming Hostiles",
        "intro": intros[0] if len(intros) == 1 else (intros[0] if intros else ""),
        "enemies": combined_enemies,
    }
    preview = BraveEncounter._build_preview_data(room, encounter_data)
    preview["roaming_party_keys"] = [party.get("key") for party in parties if party.get("key")]
    preview["roaming_parties"] = parties
    return preview


def room_uses_roaming_threats(room):
    """Return whether this room belongs to a region managed by roaming parties."""

    if not room:
        return False
    return getattr(room.db, "brave_map_region", None) in ROAMING_REGIONS


def get_roaming_parties_for_room(room):
    """Return live roaming parties occupying a room from persistent manager state."""

    if not room:
        return []
    manager = _get_roaming_manager(create_if_missing=False)
    if not manager:
        return []
    room_id = getattr(room.db, "brave_room_id", None)
    parties = []
    for party in manager._get_parties().values():
        if _stable_room_id(party.get("room_id")) != room_id:
            continue
        normalized = dict(party)
        normalized["room_id"] = room_id
        parties.append(normalized)
    parties.sort(key=lambda party: (party.get("key") or "").lower())
    return parties


def _refresh_room_views(room_ids):
    """Refresh browser room views for connected characters in the given rooms."""

    expanded_room_ids = {room_id for room_id in room_ids if room_id}
    for room_id in list(expanded_room_ids):
        room = get_room(room_id)
        if not room:
            continue
        for exit_obj in sort_exits(list(room.exits)):
            neighbor = getattr(exit_obj, "destination", None)
            neighbor_room_id = getattr(getattr(neighbor, "db", None), "brave_room_id", None)
            if neighbor_room_id:
                expanded_room_ids.add(neighbor_room_id)

    for room_id in expanded_room_ids:
        room = get_room(room_id)
        if not room:
            continue
        for character in _room_characters(room):
            if _holds_combat_result(character):
                continue
            room.return_appearance(character)


def _party_title(party):
    encounter = dict(party.get("encounter") or {})
    return str(encounter.get("title") or party.get("key") or "Hostile Party").strip() or "Hostile Party"


def _find_direction(source_room, destination_room):
    if not source_room or not destination_room:
        return None
    for exit_obj in sort_exits(list(source_room.exits)):
        if getattr(exit_obj, "destination", None) == destination_room:
            return get_exit_direction(exit_obj)
    return None


def _opposite_direction(direction):
    reverse = {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
        "up": "down",
        "down": "up",
        "northeast": "southwest",
        "southwest": "northeast",
        "northwest": "southeast",
        "southeast": "northwest",
        "in": "out",
        "out": "in",
    }
    return reverse.get(direction)


def _notify_room_activity(room, text, *, category=None):
    if not room or not text:
        return
    from world.browser_panels import broadcast_room_activity

    broadcast_room_activity(room, text, cls="out", category=category)


class BraveRoamingPartyManager(DefaultScript):
    """Persistent world script that advances hostile roaming parties."""

    def _get_parties(self):
        return dict(self.attributes.get("parties", default={}) or {})

    def _set_parties(self, parties):
        self.attributes.add("parties", dict(parties or {}))

    def _get_room_party_index(self):
        return dict(self.attributes.get("room_party_index", default={}) or {})

    def _set_room_party_index(self, room_party_index):
        self.attributes.add("room_party_index", dict(room_party_index or {}))

    def _set_last_tick_at(self, timestamp):
        self.attributes.add("last_tick_at", float(timestamp or 0))

    def at_script_creation(self):
        self.key = ROAMING_SCRIPT_KEY
        self.interval = 0
        self.start_delay = False
        self.persistent = True
        self.desc = "Brave roaming party manager"

    def _seed_parties(self, parties):
        changed = False
        for party_definition in ROAMING_CONTENT.get_roaming_parties():
            key = party_definition.get("key")
            if not key:
                continue
            state = parties.get(key)
            if not state:
                parties[key] = _party_definition_to_state(party_definition)
                changed = True
                continue
            if self._normalize_state(state, party_definition):
                changed = True
        if changed:
            self._set_parties(parties)
        return parties

    def _normalize_state(self, state, party_definition):
        changed = False
        defaults = _party_definition_to_state(party_definition)
        sync_keys = {"region", "start_room_id", "avoid_safe", "interval", "respawn_delay", "encounter"}
        for key, value in defaults.items():
            if key not in state:
                state[key] = value
                changed = True
                continue
            if key in sync_keys and state.get(key) != value:
                state[key] = value
                changed = True
        if not state.get("room_id") and state.get("respawn_at", 0) <= time.time():
            state["room_id"] = state.get("start_room_id")
            state["last_room_id"] = state.get("room_id")
            state["next_move_at"] = time.time() + random.randint(5, max(10, state["interval"]))
            state["respawn_at"] = 0.0
            state["engaged"] = False
            changed = True
        next_move_at = float(state.get("next_move_at", 0) or 0)
        max_next_move_at = time.time() + max(10, int(state.get("interval", 30) or 30))
        if next_move_at > max_next_move_at:
            state["next_move_at"] = max_next_move_at
            changed = True
        return changed

    def _room_party_index(self, parties):
        index = {}
        for party in parties.values():
            room_id = _stable_room_id(party.get("room_id"))
            if not room_id:
                continue
            party["room_id"] = room_id
            index.setdefault(room_id, []).append(party)
        for parties_in_room in index.values():
            parties_in_room.sort(key=lambda party: (party.get("key") or "").lower())
        return index

    def _sync_room_caches(self):
        parties = self._get_parties()
        old_index = self._get_room_party_index()
        new_index = self._room_party_index(parties)
        self._set_room_party_index({room_id: [party.get("key") for party in room_parties] for room_id, room_parties in new_index.items()})

        room_ids = set(old_index) | set(new_index)
        for room_id in room_ids:
            room = get_room(room_id)
            if not room:
                continue
            room.ndb.brave_roaming_parties = [dict(party) for party in new_index.get(room_id, [])]

    def _refresh_visible_rooms(self, room_ids=None):
        if room_ids is None:
            room_ids = list(self._get_room_party_index().keys())
        _refresh_room_views(room_ids)

    def _room_is_blocked(self, room, *, exclude_key=None):
        if not room:
            return True
        if getattr(room.db, "brave_safe", False):
            return True
        from typeclasses.scripts import BraveEncounter

        return bool(BraveEncounter.get_for_room(room))

    def _select_destination(self, party, parties):
        room = _resolve_room_ref(party.get("room_id"))
        if not room:
            return None

        same_region = party.get("region")
        candidates = []
        fallback = []
        for exit_obj in sort_exits(list(room.exits)):
            destination = getattr(exit_obj, "destination", None)
            if not destination:
                continue
            if getattr(destination.db, "brave_map_region", None) != same_region:
                continue
            if self._room_is_blocked(destination, exclude_key=party.get("key")):
                continue
            candidates.append(destination)
        if candidates:
            return random.choice(candidates)

        for exit_obj in sort_exits(list(room.exits)):
            destination = getattr(exit_obj, "destination", None)
            if not destination:
                continue
            if getattr(destination.db, "brave_map_region", None) != same_region:
                continue
            fallback.append(destination)

        return random.choice(fallback) if fallback else None

    def _advance_parties(self, parties):
        now = time.time()
        changed_rooms = set()

        for party_key in sorted(parties):
            party = parties[party_key]
            if party.get("engaged"):
                continue
            respawn_at = float(party.get("respawn_at", 0) or 0)
            if respawn_at and respawn_at > now:
                continue
            if respawn_at and respawn_at <= now and not party.get("room_id"):
                party["room_id"] = party.get("start_room_id")
                party["last_room_id"] = party.get("room_id")
                party["next_move_at"] = now + random.randint(8, max(12, party["interval"]))
                party["respawn_at"] = 0.0
                changed_rooms.add(party.get("room_id"))
                continue

            next_move_at = float(party.get("next_move_at", 0) or 0)
            if next_move_at and next_move_at > now:
                continue

            source_room_id = party.get("room_id")
            destination = self._select_destination(party, parties)
            if not destination:
                party["next_move_at"] = now + party["interval"]
                continue

            source_room_id = _stable_room_id(source_room_id)
            source_room = get_room(source_room_id)
            destination_room_id = getattr(destination.db, "brave_room_id", None) or destination.key
            destination_room = get_room(destination_room_id)
            travel_direction = _find_direction(source_room, destination_room)
            arrival_direction = _opposite_direction(travel_direction)
            title = _party_title(party)

            if source_room:
                departure_line = f"|x{title} moves on from here.|n"
                if travel_direction:
                    departure_line = f"|x{title} heads {travel_direction}.|n"
                _notify_room_activity(source_room, departure_line, category="departure")

            if destination_room:
                arrival_line = f"|r{title} moves into the area.|n"
                if arrival_direction:
                    arrival_line = f"|r{title} arrives from the {arrival_direction}.|n"
                _notify_room_activity(destination_room, arrival_line, category="threat")

            party["last_room_id"] = source_room_id
            party["room_id"] = destination_room_id
            party["next_move_at"] = now + random.randint(max(10, party["interval"] // 2), party["interval"] + max(10, party["interval"] // 3))
            changed_rooms.update({source_room_id, destination_room_id})

        return changed_rooms

    def mark_parties_engaged(self, party_keys, room_id=None):
        parties = self._get_parties()
        changed_rooms = set()
        now = time.time()
        for party_key in party_keys or []:
            party = parties.get(party_key)
            if not party:
                continue
            if room_id and _stable_room_id(party.get("room_id")) != _stable_room_id(room_id):
                continue
            party["engaged"] = True
            party["next_move_at"] = max(float(party.get("next_move_at", 0) or 0), now + party.get("interval", 30))
            changed_rooms.add(_stable_room_id(party.get("room_id")))
        self._set_parties(parties)
        self._sync_room_caches()
        if changed_rooms:
            self._refresh_visible_rooms(changed_rooms)

    def release_parties(self, party_keys, *, defeated=False):
        parties = self._get_parties()
        changed_rooms = set()
        now = time.time()
        for party_key in party_keys or []:
            party = parties.get(party_key)
            if not party:
                continue
            changed_rooms.add(_stable_room_id(party.get("room_id")))
            if defeated:
                party["last_room_id"] = party.get("room_id")
                party["room_id"] = None
                party["respawn_at"] = now + max(0, int(party.get("respawn_delay", 0) or 0))
                party["engaged"] = False
            else:
                party["engaged"] = False
                party["next_move_at"] = now + max(10, int(party.get("interval", 30) or 30))
        self._set_parties(parties)
        self._sync_room_caches()
        if changed_rooms:
            self._refresh_visible_rooms(changed_rooms)

    def advance_due_parties(self):
        """Advance any roaming parties whose move timer has elapsed."""

        parties = self._seed_parties(self._get_parties())
        self._set_last_tick_at(time.time())
        now = time.time()
        due_keys = [
            party.get("key")
            for party in parties.values()
            if not party.get("engaged")
            and not (float(party.get("respawn_at", 0) or 0) > now)
            and (float(party.get("next_move_at", 0) or 0) <= now or not party.get("room_id"))
        ]
        if not due_keys:
            return set()

        moved_room_ids = self._advance_parties(parties)
        self._set_parties(parties)
        self._sync_room_caches()
        if moved_room_ids:
            self._refresh_visible_rooms(moved_room_ids)
        return moved_room_ids


def _get_roaming_manager(*, create_if_missing=True):
    script = ScriptDB.objects.filter(db_key=ROAMING_SCRIPT_KEY, db_typeclass_path=ROAMING_SCRIPT_TYPECLASS).first()
    if script:
        script.interval = 0
        script.start_delay = False
        script.persistent = True
        return script
    if not create_if_missing:
        return None

    return create.create_script(
        BraveRoamingPartyManager,
        key=ROAMING_SCRIPT_KEY,
        autostart=False,
        persistent=True,
    )


def _initialize_roaming_manager(manager):
    """Seed roaming state and room caches on boot/reload."""

    if not manager:
        return
    manager._set_parties(manager._seed_parties(manager._get_parties()))
    manager._sync_room_caches()
    manager._refresh_visible_rooms()


def ensure_roaming_party_manager():
    """Create or restart the roaming-party manager script."""

    manager = _get_roaming_manager(create_if_missing=True)
    _initialize_roaming_manager(manager)
    return manager


def advance_roaming_parties():
    """Advance overdue roaming parties on demand as a fallback to ticker drift."""

    manager = _get_roaming_manager(create_if_missing=False)
    if not manager:
        return set()
    try:
        return manager.advance_due_parties()
    except Exception:
        log_trace()
        return set()


def _run_roaming_tick():
    """Compatibility shim for legacy restored ticker references."""

    return advance_roaming_parties()


def mark_roaming_parties_engaged(party_keys, room_id=None):
    """Lock roaming parties in place when combat starts."""

    manager = _get_roaming_manager(create_if_missing=False)
    if manager:
        manager.mark_parties_engaged(party_keys, room_id=room_id)


def release_roaming_parties(party_keys, *, defeated=False):
    """Return roaming parties to the world after combat ends."""

    manager = _get_roaming_manager(create_if_missing=False)
    if manager:
        manager.release_parties(party_keys, defeated=defeated)
