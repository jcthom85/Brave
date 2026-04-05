"""
Scripts

Scripts are powerful jacks-of-all-trades. They have no in-game
existence and can be used to represent persistent game systems in some
circumstances. Scripts can also have a time component that allows them
to "fire" regularly or a limited number of times.

There is generally no "tree" of Scripts inheriting from each other.
Rather, each script tends to inherit from the base Script class and
just overloads its hooks to have it perform its function.

"""

import random
import time
from collections.abc import Mapping
from urllib.parse import urlencode

from evennia.objects.models import ObjectDB
from evennia.scripts.scripts import DefaultScript
from evennia.utils.ansi import strip_ansi
from evennia.utils import create, delay

from world.bootstrap import get_room
from world.combat_atb import (
    advance_atb_state_by_ms,
    atb_state_ms_until_ready,
    create_atb_state,
    finish_atb_action,
    get_ability_atb_profile,
    get_item_atb_profile,
    normalize_atb_profile,
    start_atb_action,
    tick_atb_state,
)
from world.combat_execution import execute_combat_ability
from world.content import get_content_registry

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
ENCOUNTER_CONTENT = CONTENT.encounters
ABILITY_LIBRARY = CHARACTER_CONTENT.ability_library
PASSIVE_ABILITY_BONUSES = CHARACTER_CONTENT.passive_ability_bonuses
ENEMY_TEMPLATES = ENCOUNTER_CONTENT.enemy_templates
ROOM_ENCOUNTERS = ENCOUNTER_CONTENT.room_encounters
get_enemy_rank = ENCOUNTER_CONTENT.get_enemy_rank
get_enemy_temperament = ENCOUNTER_CONTENT.get_enemy_temperament
get_enemy_temperament_label = ENCOUNTER_CONTENT.get_enemy_temperament_label
get_relative_threat_label = ENCOUNTER_CONTENT.get_relative_threat_label
from world.data.items import ITEM_TEMPLATES, get_item_use_profile, match_inventory_item
from world.questing import advance_enemy_defeat, pop_recent_quest_updates
from world.resonance import get_ability_display_name, get_resource_label, resolve_ability_query
from world.rewards import format_reward_summary, merge_reward_entries, roll_enemy_rewards
from world.tutorial import get_tutorial_defeat_room, record_encounter_victory

COMBAT_BOSS_CREDIT_RATIO = (2, 3)
COMBAT_ACTION_SCORE_CAP = 3.0
COMBAT_UTILITY_WEIGHT = 6
COMBAT_HITS_TAKEN_WEIGHT = 2
COMBAT_TURN_LOCK_MS = 1200
# The browser defeat fall is 860ms. Leave enough headroom for network/render
# latency plus a brief beat so players can actually watch the final death.
COMBAT_FINISH_FX_DELAY = 1.5


def _normalize_token(value):
    """Normalize free-text tokens for matching."""

    return "".join(char for char in (value or "").lower() if char.isalnum())


def _ability_display_name(character, ability_key):
    """Return the resonance-aware display name for an ability key."""

    ability = ABILITY_LIBRARY.get(ability_key) or PASSIVE_ABILITY_BONUSES.get(ability_key)
    if not ability:
        return ability_key.replace("_", " ").title()
    return get_ability_display_name(ability["name"], character)


def _combat_target_id(target):
    """Return a stable id for combat targets backed by mappings or objects."""

    if isinstance(target, Mapping):
        return target.get("id")
    return getattr(target, "id", None)


def _combat_target_name(target, default=""):
    """Return a display name for combat targets backed by mappings or objects."""

    if isinstance(target, Mapping):
        return target.get("key", default) or default
    return getattr(target, "key", default) or default


def _combat_entry_ref(target):
    """Return the browser combat entry ref for a participant or enemy."""

    if isinstance(target, Mapping):
        target_id = target.get("id")
        return f"e:{target_id}" if target_id else None
    target_id = getattr(target, "id", None)
    return f"p:{target_id}" if target_id is not None else None


def _combat_fx_marker(**fields):
    """Return a hidden client FX marker embedded in combat log text."""

    payload = {
        key: value
        for key, value in fields.items()
        if value not in (None, "", False)
    }
    if not payload:
        return ""
    return f" [[BRAVEFX {urlencode(payload)}]]"


def _enemy_damage_type(enemy):
    """Return a broad damage type tag for an enemy action."""

    template_key = str((enemy or {}).get("template_key") or "").lower()
    if template_key in {"tower_archer", "old_greymaw", "forest_wolf", "grave_crow", "carrion_hound", "mire_hound", "silt_stalker"}:
        return "physical"
    if template_key in {"barrow_wisp", "restless_shade", "sir_edric_restless", "hollow_wisp", "hollow_lantern"}:
        return "shadow"
    if template_key in {"fen_wisp", "bog_creeper", "miretooth"}:
        return "nature"
    if template_key in {"mag_clamp_drone", "foreman_coilback", "relay_tick"}:
        return "lightning"
    return "physical"


THREAT_ARCHETYPE_TAG_PRIORITY = (
    "dragon",
    "drake",
    "knight",
    "soldier",
    "wolf",
    "hound",
    "archer",
    "hexer",
    "caster",
    "wisp",
    "shade",
    "skeleton",
    "undead",
    "construct",
    "beast",
    "goblin",
    "raider",
    "brute",
    "skirmisher",
    "support",
)

THREAT_ARCHETYPE_LABELS = {
    "dragon": "dragon",
    "drake": "drake",
    "knight": "knight",
    "soldier": "soldier",
    "wolf": "wolf",
    "hound": "hound",
    "archer": "archer",
    "hexer": "hexer",
    "caster": "caster",
    "wisp": "wisp",
    "shade": "shade",
    "skeleton": "skeleton",
    "undead": "undead",
    "construct": "construct",
    "beast": "beast",
    "goblin": "goblin",
    "raider": "raider",
    "brute": "brute",
    "skirmisher": "skirmisher",
    "support": "support",
}

ROOM_THREAT_SKULL_DELTA = 3


ROOM_THREAT_RESPAWN_DELAY = 45

ATB_READY_GAUGE = 400

DEFAULT_ATTACK_ATB_PROFILE = normalize_atb_profile({"windup_ticks": 1, "recovery_ticks": 0, "interruptible": False})
DEFAULT_FLEE_ATB_PROFILE = normalize_atb_profile({"windup_ticks": 1, "recovery_ticks": 0, "telegraph": True})
DEFAULT_ENEMY_ATTACK_ATB_PROFILE = normalize_atb_profile({"windup_ticks": 1, "recovery_ticks": 0, "interruptible": False})


PARTY_SCALING = {
    1: {"label": "Solo", "hp": 0.88, "power": 0.88, "accuracy": -3, "xp": 1.0},
    2: {"label": "Duo", "hp": 0.94, "power": 0.95, "accuracy": -1, "xp": 1.0},
    3: {"label": "Trio", "hp": 1.08, "power": 1.02, "accuracy": 1, "xp": 1.03},
    4: {"label": "Full Party", "hp": 1.22, "power": 1.1, "accuracy": 3, "xp": 1.08},
}


class Script(DefaultScript):
    """
    This is the base TypeClass for all Scripts. Scripts describe
    all entities/systems without a physical existence in the game world
    that require database storage (like an economic system or
    combat tracker). They
    can also have a timer/ticker component.

    A script type is customized by redefining some or all of its hook
    methods and variables.

    * available properties (check docs for full listing, this could be
      outdated).

     key (string) - name of object
     name (string)- same as key
     aliases (list of strings) - aliases to the object. Will be saved
              to database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     desc (string)      - optional description of script, shown in listings
     obj (Object)       - optional object that this script is connected to
                          and acts on (set automatically by obj.scripts.add())
     interval (int)     - how often script should run, in seconds. <0 turns
                          off ticker
     start_delay (bool) - if the script should start repeating right away or
                          wait self.interval seconds
     repeats (int)      - how many times the script should repeat before
                          stopping. 0 means infinite repeats
     persistent (bool)  - if script should survive a server shutdown or not
     is_active (bool)   - if script is currently running

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                        self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                        create a database entry when storing data

    * Helper methods

     create(key, **kwargs)
     start() - start script (this usually happens automatically at creation
               and obj.script.add() etc)
     stop()  - stop script, and delete it
     pause() - put the script on hold, until unpause() is called. If script
               is persistent, the pause state will survive a shutdown.
     unpause() - restart a previously paused script. The script will continue
                 from the paused timer (but at_start() will be called).
     time_until_next_repeat() - if a timed script (interval>0), returns time
                 until next tick

    * Hook methods (should also include self as the first argument):

     at_script_creation() - called only once, when an object of this
                            class is first created.
     is_valid() - is called to check if the script is valid to be running
                  at the current time. If is_valid() returns False, the running
                  script is stopped and removed from the game. You can use this
                  to check state changes (i.e. an script tracking some combat
                  stats at regular intervals is only valid to run while there is
                  actual combat going on).
      at_start() - Called every time the script is started, which for persistent
                  scripts is at least once every server start. Note that this is
                  unaffected by self.delay_start, which only delays the first
                  call to at_repeat().
      at_repeat() - Called every self.interval seconds. It will be called
                  immediately upon launch unless self.delay_start is True, which
                  will delay the first call of this method by self.interval
                  seconds. If self.interval==0, this method will never
                  be called.
      at_pause()
      at_stop() - Called as the script object is stopped and is about to be
                  removed from the game, e.g. because is_valid() returned False.
      at_script_delete()
      at_server_reload() - Called when server reloads. Can be used to
                  save temporary variables you want should survive a reload.
      at_server_shutdown() - called at a full server shutdown.
      at_server_start()

    """

    pass


class BraveEncounter(Script):
    """Simple room-based combat controller for Brave's first vertical slice."""

    @classmethod
    def get_for_room(cls, room):
        """Return the active Brave encounter for a room, if any."""

        if not room:
            return None

        encounter = room.ndb.brave_encounter
        if encounter and encounter.id and getattr(encounter, "is_active", False):
            return encounter
        room.ndb.brave_encounter = None

        if not encounter or not encounter.id or not getattr(encounter, "is_active", False):
            matches = room.scripts.get("brave_encounter")
            if hasattr(matches, "all"):
                matches = matches.all()
            for encounter in matches:
                if not getattr(encounter, "is_active", False):
                    continue
                room.ndb.brave_encounter = encounter
                return encounter
        return None

    @classmethod
    def _clear_room_threat_preview(cls, room, *, cooldown=0):
        """Clear any cached room-threat preview and optionally set a respawn delay."""

        if not room:
            return
        room.ndb.brave_room_threat_preview = None
        room.ndb.brave_room_threat_ready_at = time.time() + max(0, int(cooldown or 0))

    @classmethod
    def _build_preview_data(cls, room, encounter_data):
        """Create a stable, visible room-threat preview from encounter data."""

        template_totals = {}
        for template_key in encounter_data["enemies"]:
            template_totals[template_key] = template_totals.get(template_key, 0) + 1

        template_seen = {}
        enemies = []
        for template_key in encounter_data["enemies"]:
            template = ENEMY_TEMPLATES[template_key]
            template_seen[template_key] = template_seen.get(template_key, 0) + 1
            display_key = template["name"]
            if template_totals[template_key] > 1:
                display_key = f"{display_key} {template_seen[template_key]}"
            temperament = get_enemy_temperament(template_key, template)
            enemies.append(
                {
                    "template_key": template_key,
                    "key": display_key,
                    "desc": template.get("desc", ""),
                    "tags": list(template.get("tags", [])),
                    "temperament": temperament,
                    "temperament_label": get_enemy_temperament_label(temperament),
                    "rank": get_enemy_rank(template_key, template),
                }
            )

        return {
            "room_id": getattr(room.db, "brave_room_id", None),
            "encounter_data": encounter_data,
            "encounter_key": encounter_data["key"],
            "encounter_title": encounter_data["title"],
            "encounter_intro": encounter_data["intro"],
            "enemies": enemies,
        }

    @classmethod
    def get_room_threat_preview(cls, room):
        """Return the current visible room-threat preview, creating one if needed."""

        if not room or getattr(room.db, "brave_safe", False):
            return None

        encounter = cls.get_for_room(room)
        if encounter:
            return {
                "room_id": getattr(room.db, "brave_room_id", None),
                "encounter_key": encounter.db.encounter_key,
                "encounter_title": encounter.db.encounter_title,
                "encounter_intro": encounter.db.encounter_intro,
                "enemies": [
                    {
                        "id": enemy["id"],
                        "template_key": enemy["template_key"],
                        "key": enemy["key"],
                        "desc": ENEMY_TEMPLATES[enemy["template_key"]].get("desc", ""),
                        "tags": list(ENEMY_TEMPLATES[enemy["template_key"]].get("tags", [])),
                        "temperament": get_enemy_temperament(enemy["template_key"]),
                        "temperament_label": get_enemy_temperament_label(get_enemy_temperament(enemy["template_key"])),
                        "rank": get_enemy_rank(enemy["template_key"]),
                        "engaged": True,
                    }
                    for enemy in encounter.get_active_enemies()
                ],
            }

        ready_at = getattr(room.ndb, "brave_room_threat_ready_at", 0) or 0
        if ready_at and ready_at > time.time():
            return None

        preview = getattr(room.ndb, "brave_room_threat_preview", None)
        room_id = getattr(room.db, "brave_room_id", None)
        if preview and preview.get("room_id") == room_id:
            return preview

        choices = ROOM_ENCOUNTERS.get(room_id)
        if not choices:
            return None

        preview = cls._build_preview_data(room, random.choice(choices))
        room.ndb.brave_room_threat_preview = preview
        room.ndb.brave_room_threat_ready_at = 0
        return preview

    @classmethod
    def _get_present_party_targets(cls, character):
        """Return the connected present party members who should count together."""

        if not character:
            return []
        members = [character]
        if getattr(character.db, "brave_party_id", None):
            from world.party import get_present_party_members

            members = [
                member
                for member in get_present_party_members(character)
                if getattr(member, "is_connected", False) and member.location == character.location
            ] or [character]
        seen = set()
        ordered = []
        for member in members:
            if not member or member.id in seen:
                continue
            seen.add(member.id)
            ordered.append(member)
        return ordered

    @classmethod
    def _effective_party_level(cls, character):
        """Estimate the party's effective level for room-threat evaluation."""

        members = cls._get_present_party_targets(character)
        if not members:
            return 1.0
        levels = [max(1, int(getattr(member.db, "brave_level", 1) or 1)) for member in members]
        average = sum(levels) / len(levels)
        return average + (0.6 * max(0, len(members) - 1))

    @classmethod
    def _extract_enemy_archetype(cls, enemy):
        """Return a compact archetype token for a room-threat preview enemy."""

        tags = list(enemy.get("tags") or [])
        for tag in THREAT_ARCHETYPE_TAG_PRIORITY:
            if tag in tags:
                return THREAT_ARCHETYPE_LABELS.get(tag, tag)

        name = str(enemy.get("key") or enemy.get("template_key") or "").strip().lower()
        if not name:
            return "foe"
        token = name.split()[-1]
        return THREAT_ARCHETYPE_LABELS.get(token, token)

    @classmethod
    def _pluralize_archetype(cls, token):
        """Return a simple plural form for homogeneous threat summaries."""

        if token.endswith("y") and len(token) > 1 and token[-2] not in "aeiou":
            return token[:-1] + "ies"
        if token.endswith(("s", "x", "z", "ch", "sh")):
            return token + "es"
        return token + "s"

    @classmethod
    def _compact_encounter_title(cls, preview):
        """Return the short room-view title for an encounter preview."""

        title = str(preview.get("encounter_title") or "").strip()
        if title and len(title) <= 32:
            return title

        enemies = list(preview.get("enemies") or [])
        if not enemies:
            return "Hostile Party"

        lead = max(
            enemies,
            key=lambda enemy: (
                int(enemy.get("rank", 1) or 1),
                str(enemy.get("key", "")).lower(),
            ),
        )
        lead_name = str(lead.get("key") or "Hostile").strip()
        if len(enemies) == 1:
            return lead_name
        if len(lead_name) > 22:
            lead_name = lead_name.split()[0]
        return f"{lead_name} Retinue"

    @classmethod
    def _build_room_threat_card(cls, preview, viewer=None):
        """Build one compact room threat card from an encounter preview."""

        enemies = list(preview.get("enemies") or [])
        if not enemies:
            return None

        effective_level = cls._effective_party_level(viewer) if viewer else 1.0
        viewer_level = max(1, int(getattr(getattr(viewer, "db", None), "brave_level", 1) or 1))
        lead_rank = max(int(enemy.get("rank", 1) or 1) for enemy in enemies)
        lead_threat = get_relative_threat_label(lead_rank, effective_level)

        sorted_enemies = sorted(
            enemies,
            key=lambda enemy: (
                -int(enemy.get("rank", 1) or 1),
                str(enemy.get("key", "")).lower(),
            ),
        )
        archetypes = []
        seen = set()
        for enemy in sorted_enemies:
            token = cls._extract_enemy_archetype(enemy)
            if token in seen:
                continue
            seen.add(token)
            archetypes.append(token)

        if not archetypes:
            descriptor = "hostiles"
        elif len(archetypes) == 1:
            descriptor = cls._pluralize_archetype(archetypes[0]) if len(enemies) > 1 else archetypes[0]
        else:
            descriptor = ", ".join(archetypes[:3])

        overpowering = any(int(enemy.get("rank", 1) or 1) >= viewer_level + ROOM_THREAT_SKULL_DELTA for enemy in enemies)
        tooltip_bits = [f"{len(enemies)} hostiles", f"{lead_threat.lower()} threat"]
        intro = str(preview.get("encounter_intro") or "").strip()
        if intro:
            tooltip_bits.append(intro)
        engaged = any(bool(enemy.get("engaged")) for enemy in enemies)
        if engaged:
            tooltip_bits.append("fight underway")

        return {
            "key": cls._compact_encounter_title(preview),
            "detail": f"Engaged · {descriptor}" if engaged else descriptor,
            "badge": str(len(enemies)),
            "tooltip": " · ".join(bit for bit in tooltip_bits if bit),
            "command": "fight",
            "engaged": engaged,
            "marker_icon": "swords" if engaged else ("skull" if overpowering else None),
            "icon": "warning",
            "temperament_label": max(
                (str(enemy.get("temperament_label") or "Aggressive") for enemy in enemies),
                key=lambda label: (label == "Relentless", label == "Aggressive", label),
            ),
            "threat_label": lead_threat,
        }

    @classmethod
    def get_visible_room_threats(cls, room, viewer=None):
        """Return visible hostile threats for room rendering and threat commands."""

        preview = cls.get_room_threat_preview(room)
        if not preview:
            return []

        card = cls._build_room_threat_card(preview, viewer=viewer)
        return [card] if card else []

    @classmethod
    def find_room_threat(cls, room, query):
        """Find a visible room threat by name before combat has started."""

        if not room:
            return None

        preview = cls.get_room_threat_preview(room)
        if not preview:
            return None

        query_norm = _normalize_token(query)
        if not query_norm:
            return preview["enemies"][0] if preview.get("enemies") else None

        matches = []
        for enemy in preview.get("enemies", []):
            if query_norm == _normalize_token(enemy["key"]):
                matches.append(enemy)
        if matches:
            return matches[0] if len(matches) == 1 else matches

        for enemy in preview.get("enemies", []):
            if query_norm in _normalize_token(enemy["key"]):
                matches.append(enemy)
        if not matches:
            return None
        return matches[0] if len(matches) == 1 else matches

    @classmethod
    def _should_auto_aggro(cls, room, character):
        """Return whether visible room threats should auto-engage this party."""

        preview = cls.get_room_threat_preview(room)
        if not preview or not character:
            return False

        effective_level = cls._effective_party_level(character)
        for enemy in preview.get("enemies", []):
            temperament = enemy.get("temperament", "aggressive")
            threat_label = get_relative_threat_label(enemy.get("rank", 1), effective_level)
            if temperament == "relentless":
                return True
            if temperament == "aggressive" and threat_label != "Trivial":
                return True
        return False

    @classmethod
    def maybe_auto_aggro(cls, character):
        """Start a fight automatically if the room's threats are hostile enough."""

        if not character or not character.location or getattr(character.location.db, "brave_safe", False):
            return None

        encounter = cls.get_for_room(character.location)
        if encounter and encounter.is_participant(character):
            return encounter

        if not cls._should_auto_aggro(character.location, character):
            return None

        party_targets = cls._get_present_party_targets(character)
        encounter, _created = cls.start_for_room(character.location, expected_party_size=len(party_targets))
        if not encounter:
            return None

        joined = False
        for participant in party_targets:
            ok, _error = encounter.add_participant(participant)
            joined = joined or ok

        if joined:
            character.msg("|rThe room turns before you can set your feet.|n")
        return encounter

    @classmethod
    def start_for_room(cls, room, expected_party_size=1):
        """Create a new encounter for a room if encounter data exists."""

        encounter = cls.get_for_room(room)
        if encounter:
            return encounter, False

        preview = cls.get_room_threat_preview(room)
        if not preview:
            return None, False

        encounter = create.create_script(
            cls,
            key="brave_encounter",
            obj=room,
            autostart=False,
            persistent=False,
        )
        encounter.configure(preview["room_id"], preview["encounter_data"], expected_party_size=expected_party_size)
        room.ndb.brave_room_threat_preview = None
        room.ndb.brave_encounter = encounter
        encounter.start()
        return encounter, True

    def at_script_creation(self):
        self.interval = 1
        self.start_delay = True
        self.persistent = False
        self.desc = "Brave room encounter"

    def configure(self, room_id, encounter_data, expected_party_size=1):
        """Populate the encounter from static room data."""

        self.db.room_id = room_id
        self.db.encounter_key = encounter_data["key"]
        self.db.encounter_title = encounter_data["title"]
        self.db.encounter_intro = encounter_data["intro"]
        self.db.expected_party_size = max(1, min(4, int(expected_party_size or 1)))
        self.db.pending_actions = {}
        self.db.participants = []
        self.db.defeated_participants = []
        self.db.participant_states = {}
        self.db.participant_contributions = {}
        self.db.atb_states = {}
        self.db.threat = {}
        self.db.turn_count = 0
        self.db.enemies = []
        self.db.enemy_counter = 0

        template_totals = {}
        for template_key in encounter_data["enemies"]:
            template_totals[template_key] = template_totals.get(template_key, 0) + 1

        template_seen = {}
        for template_key in encounter_data["enemies"]:
            template_seen[template_key] = template_seen.get(template_key, 0) + 1
            display_key = None
            if template_totals[template_key] > 1:
                display_key = f"{ENEMY_TEMPLATES[template_key]['name']} {template_seen[template_key]}"
            self._spawn_enemy(template_key, display_key=display_key, announce=False)

    def at_start(self):
        if self.obj:
            self.obj.ndb.brave_encounter = self
            intro = (self.db.encounter_intro or "").strip()
            if intro:
                self.obj.msg_contents(f"|r{intro}|n")
            else:
                self.obj.msg_contents(f"|r{self.db.encounter_title}!|n")
        self._refresh_browser_combat_views()

    def at_stop(self):
        participants = list(self.get_participants())
        self._clear_browser_combat_views(participants)
        if self.obj:
            self.obj.ndb.brave_encounter = None
            if not self.get_active_enemies():
                self._clear_room_threat_preview(self.obj, cooldown=ROOM_THREAT_RESPAWN_DELAY)
            else:
                self._clear_room_threat_preview(self.obj, cooldown=0)
        for participant in participants:
            participant.ndb.brave_encounter = None

    def is_participant(self, character):
        """Return whether a character is in the encounter."""

        return character and character.id in (self.db.participants or [])

    def _get_character(self, dbref):
        try:
            return ObjectDB.objects.get(id=dbref)
        except ObjectDB.DoesNotExist:
            return None

    def get_participants(self):
        """Resolve all participant dbrefs into characters."""

        participants = []
        for participant_id in self.db.participants or []:
            participant = self._get_character(participant_id)
            if participant:
                participants.append(participant)
        return participants

    def get_defeated_participants(self):
        """Resolve defeated participant dbrefs into characters."""

        participants = []
        for participant_id in self.db.defeated_participants or []:
            participant = self._get_character(participant_id)
            if participant:
                participants.append(participant)
        return participants

    def get_registered_participants(self):
        """Return all encounter participants, including defeated members."""

        seen = set()
        participants = []
        for participant in self.get_participants() + self.get_defeated_participants():
            if not participant or participant.id in seen:
                continue
            seen.add(participant.id)
            participants.append(participant)
        return participants

    def _combat_turn_count(self):
        """Return the number of resolved combat turns in this encounter."""

        db = getattr(self, "db", None)
        if db is None:
            return 0
        turn_count = getattr(db, "turn_count", None)
        if turn_count is None:
            turn_count = getattr(db, "round", 0)
        return max(0, int(turn_count or 0))

    def _record_combat_turn(self):
        """Advance the resolved-turn counter once one action actually lands."""

        turn_count = BraveEncounter._combat_turn_count(self) + 1
        self.db.turn_count = turn_count
        return turn_count

    def _boss_credit_open(self):
        """Return whether boss/quest credit is still open for new joiners."""

        numerator, denominator = COMBAT_BOSS_CREDIT_RATIO
        for enemy in self.get_active_enemies():
            if "boss" not in set(enemy.get("tags", [])):
                continue
            if enemy.get("hp", 0) * denominator <= enemy.get("max_hp", 1) * numerator:
                return False
        return True

    def _get_participant_contribution(self, character):
        """Return or create contribution tracking for a participant."""

        contributions = dict(self.db.participant_contributions or {})
        key = str(character.id)
        contribution = dict(contributions.get(key) or {})
        if not contribution:
            contribution = {
                "joined_turn": BraveEncounter._combat_turn_count(self),
                "meaningful_actions": 0,
                "damage_done": 0,
                "healing_done": 0,
                "damage_prevented": 0,
                "utility_points": 0,
                "hits_taken": 0,
                "boss_credit_eligible": bool(self._boss_credit_open()),
            }
            contributions[key] = contribution
            self.db.participant_contributions = contributions
        return contribution

    def _save_participant_contribution(self, character, contribution):
        """Persist contribution tracking for a participant."""

        contributions = dict(self.db.participant_contributions or {})
        contributions[str(character.id)] = dict(contribution or {})
        self.db.participant_contributions = contributions

    def _record_participant_contribution(
        self,
        character,
        *,
        meaningful=False,
        damage=0,
        healing=0,
        mitigation=0,
        utility=0,
        hits_taken=0,
    ):
        """Add a contribution event for a participant."""

        if not character or getattr(character, "id", None) is None:
            return
        contribution = self._get_participant_contribution(character)
        if meaningful:
            contribution["meaningful_actions"] = int(contribution.get("meaningful_actions", 0)) + 1
        if damage:
            contribution["damage_done"] = int(contribution.get("damage_done", 0)) + max(0, int(damage))
        if healing:
            contribution["healing_done"] = int(contribution.get("healing_done", 0)) + max(0, int(healing))
        if mitigation:
            contribution["damage_prevented"] = int(contribution.get("damage_prevented", 0)) + max(0, int(mitigation))
        if utility:
            contribution["utility_points"] = int(contribution.get("utility_points", 0)) + max(0, int(utility))
        if hits_taken:
            contribution["hits_taken"] = int(contribution.get("hits_taken", 0)) + max(0, int(hits_taken))
        self._save_participant_contribution(character, contribution)

    def _participant_reward_eligible(self, character):
        """Return whether a participant earned a reward share."""

        return int(self._get_participant_contribution(character).get("meaningful_actions", 0)) > 0

    def _participant_impact_score(self, character):
        """Return an encounter impact score for weighted reward splits."""

        contribution = self._get_participant_contribution(character)
        return (
            int(contribution.get("damage_done", 0))
            + int(contribution.get("healing_done", 0))
            + int(contribution.get("damage_prevented", 0))
            + int(contribution.get("utility_points", 0)) * COMBAT_UTILITY_WEIGHT
            + int(contribution.get("hits_taken", 0)) * COMBAT_HITS_TAKEN_WEIGHT
        )

    def _participant_reward_weight(self, character, *, max_turn, top_impact):
        """Return weighted contribution used for XP and silver splits."""

        contribution = self._get_participant_contribution(character)
        joined_turn = int(contribution.get("joined_turn", contribution.get("joined_round", 0)) or 0)
        total_turns = max(1, int(max_turn or 1))
        turns_present = max(1, total_turns - joined_turn)
        time_weight = max(0.2, min(1.0, turns_present / float(total_turns)))
        action_score = min(
            1.0,
            int(contribution.get("meaningful_actions", 0)) / float(COMBAT_ACTION_SCORE_CAP),
        )
        impact_total = self._participant_impact_score(character)
        impact_score = impact_total / float(max(1, int(top_impact or 1)))
        return (0.35 * time_weight) + (0.25 * action_score) + (0.40 * impact_score)

    @staticmethod
    def _allocate_weighted_pool(total, weighted_entries, *, minimum=0):
        """Allocate an integer reward pool across weighted entries."""

        allocations = {key: 0 for key, _weight in weighted_entries}
        if total <= 0 or not weighted_entries:
            return allocations

        total = int(total)
        minimum = max(0, int(minimum or 0))
        keys = [key for key, _weight in weighted_entries]
        if minimum and total >= len(keys) * minimum:
            for key in keys:
                allocations[key] = minimum
            total -= len(keys) * minimum

        if total <= 0:
            return allocations

        weight_sum = sum(max(0.0, float(weight or 0.0)) for _key, weight in weighted_entries)
        if weight_sum <= 0:
            per_entry = total // len(keys)
            remainder = total % len(keys)
            for index, key in enumerate(keys):
                allocations[key] += per_entry + (1 if index < remainder else 0)
            return allocations

        remainders = []
        distributed = 0
        for key, weight in weighted_entries:
            exact = (max(0.0, float(weight or 0.0)) / weight_sum) * total
            whole = int(exact)
            allocations[key] += whole
            distributed += whole
            remainders.append((exact - whole, key))

        remainder = total - distributed
        for _fraction, key in sorted(remainders, key=lambda item: (-item[0], str(item[1]))):
            if remainder <= 0:
                break
            allocations[key] += 1
            remainder -= 1

        return allocations

    @staticmethod
    def _distribute_reward_items(reward_items, weighted_entries):
        """Distribute rolled encounter loot across eligible participants."""

        distributed = {key: [] for key, _weight in weighted_entries}
        if not reward_items or not weighted_entries:
            return distributed

        assigned_units = {key: 0 for key, _weight in weighted_entries}
        weights = {key: max(0.0, float(weight or 0.0)) for key, weight in weighted_entries}
        ordered_keys = [key for key, _weight in weighted_entries]

        for template_id, quantity in reward_items:
            for _index in range(max(0, int(quantity or 0))):
                recipient = max(
                    ordered_keys,
                    key=lambda key: (
                        weights.get(key, 0.0) / float(1 + assigned_units.get(key, 0)),
                        -assigned_units.get(key, 0),
                        -ordered_keys.index(key),
                    ),
                )
                distributed[recipient].append((template_id, 1))
                assigned_units[recipient] = assigned_units.get(recipient, 0) + 1

        return {
            key: merge_reward_entries(entries)
            for key, entries in distributed.items()
        }

    def _participant_eligible_for_enemy_credit(self, character, enemy):
        """Return whether this participant should receive kill/quest credit."""

        if not self._participant_reward_eligible(character):
            return False
        if "boss" not in set(enemy.get("tags", [])):
            return True
        contribution = self._get_participant_contribution(character)
        return bool(contribution.get("boss_credit_eligible"))

    def _award_enemy_defeat_credit(self, enemy):
        """Advance kill-credit hooks for eligible participants only."""

        for participant in self.get_registered_participants():
            if self._participant_eligible_for_enemy_credit(participant, enemy):
                advance_enemy_defeat(participant, enemy["tags"])

    def _enemy_reaction_state(self, enemy):
        """Return the current ATB action context for an enemy."""

        atb_state = self._get_actor_atb_state(enemy=enemy)
        action = dict((atb_state or {}).get("current_action") or {})
        timing = dict((atb_state or {}).get("timing") or {})
        return {
            "atb_state": atb_state,
            "action": action,
            "timing": timing,
            "phase": (atb_state or {}).get("phase"),
            "telegraphed": bool(timing.get("telegraph")),
            "interruptible": bool(timing.get("interruptible")),
            "label": action.get("label") or self._enemy_action_label(enemy),
        }

    def _set_enemy_recovery_state(self, enemy, ticks=1):
        """Put an enemy into a short recovery after an interruption."""

        current = self._get_actor_atb_state(enemy=enemy)
        self._save_actor_atb_state(
            create_atb_state(
                fill_rate=(current or {}).get("fill_rate", self._default_atb_fill_rate(enemy=enemy)),
                gauge=0,
                phase="recovering",
                ticks_remaining=max(1, int(ticks or 1)),
                current_action=None,
                timing=None,
                ready_gauge=(current or {}).get("ready_gauge", ATB_READY_GAUGE),
                tick_ms=BraveEncounter._atb_tick_ms(self),
            ),
            enemy=enemy,
        )

    def _apply_reaction_guard(self, source, target, *, amount, label, redirect_to=None):
        """Apply a telegraph-answering guard or redirect effect."""

        state = self._get_participant_state(target)
        state["reaction_guard"] = max(int(state.get("reaction_guard", 0) or 0), max(0, int(amount or 0)))
        state["reaction_guard_source"] = getattr(source, "id", None)
        state["reaction_label"] = label
        state["reaction_redirect_to"] = redirect_to
        self._save_participant_state(target, state)

    def _clear_reaction_state(self, state):
        """Clear one participant's temporary reaction metadata."""

        state["reaction_guard"] = 0
        state["reaction_guard_source"] = None
        state["reaction_label"] = None
        state["reaction_redirect_to"] = None
        return state

    def _try_interrupt_enemy_action(self, character, enemy, tool_label):
        """Attempt to break an enemy's telegraphed action before it lands."""

        if not enemy or enemy.get("hp", 0) <= 0:
            return False
        reaction = self._enemy_reaction_state(enemy)
        if reaction["phase"] != "winding" or not reaction["telegraphed"] or not reaction["interruptible"]:
            return False
        self._set_enemy_recovery_state(enemy, ticks=1)
        self.obj.msg_contents(
            f"|g{character.key}'s {tool_label} interrupts {enemy['key']}'s {reaction['label']}.|n"
        )
        self._record_participant_contribution(character, meaningful=True, utility=2)
        return True

    def _mark_defeated_participant(self, character):
        """Remember a participant who was defeated before the fight ended."""

        defeated = list(self.db.defeated_participants or [])
        if character.id not in defeated:
            defeated.append(character.id)
            self.db.defeated_participants = defeated

    def get_active_participants(self):
        """Return participants still present and standing."""

        active = []
        for participant in self.get_participants():
            resources = participant.db.brave_resources or {}
            if participant.location == self.obj and resources.get("hp", 0) > 0:
                active.append(participant)
        return active

    def _refresh_browser_combat_views(self, participants=None):
        """Refresh browser combat UI for current participants without clearing the log."""

        from world.browser_panels import build_combat_panel, send_webclient_event
        from world.browser_views import build_combat_view

        targets = participants if participants is not None else self.get_active_participants()
        for participant in targets:
            if not participant or participant.location != self.obj:
                continue
            send_webclient_event(
                participant,
                brave_view=build_combat_view(self, participant),
                brave_panel=build_combat_panel(self),
            )

    def _emit_combat_fx(self, **event):
        """Send structured combat FX events to active combat viewers."""

        from world.browser_panels import send_webclient_event

        event = dict(event or {})
        event.setdefault("lock_ms", BraveEncounter._remaining_combat_turn_lock_ms(self))
        get_active_participants = getattr(self, "get_active_participants", None)
        participants = list(get_active_participants()) if callable(get_active_participants) else []
        for participant in participants:
            if participant and participant.location == self.obj:
                send_webclient_event(participant, brave_combat_fx=event)

    def _emit_miss_fx(self, source, target, text="MISS"):
        """Emit a miss event so whiffs still read on the battle board."""

        source_name = source.get("key") if isinstance(source, dict) else getattr(source, "key", None)
        target_name = target.get("key") if isinstance(target, dict) else getattr(target, "key", None)
        if not source_name or not target_name:
            return
        emitter = getattr(self, "_emit_combat_fx", None)
        if not callable(emitter):
            emitter = lambda **event: BraveEncounter._emit_combat_fx(self, **event)
        emitter(
            kind="miss",
            source=source_name,
            target=target_name,
            source_ref=_combat_entry_ref(source),
            target_ref=_combat_entry_ref(target),
            text=text,
            tone="warn",
            impact="miss",
            lunge=True,
        )

    def _emit_defeat_fx(self, target, text="DOWN"):
        """Emit a defeat event so removals still animate on the battle board."""

        target_name = target.get("key") if isinstance(target, dict) else getattr(target, "key", None)
        if not target_name:
            return
        emitter = getattr(self, "_emit_combat_fx", None)
        if not callable(emitter):
            emitter = lambda **event: BraveEncounter._emit_combat_fx(self, **event)
        emitter(
            kind="defeat",
            target=target_name,
            target_ref=_combat_entry_ref(target),
            text=text,
            tone="break",
            impact="break",
            defeat=True,
        )

    def _clear_browser_combat_views(self, participants=None):
        """Remove any sticky browser combat UI for participants."""

        from world.browser_panels import send_webclient_event

        targets = participants if participants is not None else self.get_participants()
        for participant in targets:
            if participant:
                send_webclient_event(participant, brave_combat_done={})

    def get_enemy(self, enemy_id):
        """Return an enemy dict by id."""

        for enemy in self.db.enemies or []:
            if enemy["id"] == enemy_id:
                return enemy
        return None

    def get_active_enemies(self):
        """Return all currently living enemies."""

        return [enemy for enemy in self.db.enemies or [] if enemy["hp"] > 0]

    def _get_scaling_profile(self):
        size = max(1, min(4, int(self.db.expected_party_size or 1)))
        return PARTY_SCALING[size]

    def _primary_resource_key(self, character):
        if character.db.brave_class in {"cleric", "mage", "druid"}:
            return "mana"
        return "stamina"

    def _actor_atb_key(self, character=None, enemy=None):
        if character is not None:
            return f"p:{character.id}"
        if enemy is not None:
            return f"e:{enemy['id']}"
        raise ValueError("ATB actor key requires a character or enemy.")

    def _combat_turn_lock_until_ms(self):
        return max(0, int(getattr(getattr(self, "db", None), "atb_turn_lock_until_ms", 0) or 0))

    def _combat_turn_locked(self, now_ms=None):
        current_ms = int(now_ms if now_ms is not None else round(time.time() * 1000))
        return current_ms < BraveEncounter._combat_turn_lock_until_ms(self)

    def _remaining_combat_turn_lock_ms(self, now_ms=None):
        current_ms = int(now_ms if now_ms is not None else round(time.time() * 1000))
        return max(0, BraveEncounter._combat_turn_lock_until_ms(self) - current_ms)

    def _set_combat_turn_lock(self, duration_ms=COMBAT_TURN_LOCK_MS, *, now_ms=None):
        current_ms = int(now_ms if now_ms is not None else round(time.time() * 1000))
        duration_ms = max(0, int(duration_ms or 0))
        lock_until_ms = max(BraveEncounter._combat_turn_lock_until_ms(self), current_ms + duration_ms)
        self.db.atb_turn_lock_until_ms = lock_until_ms
        return lock_until_ms

    def _atb_tick_ms(self):
        return max(1, int(round(float(getattr(self, "interval", 0.25) or 0.25) * 1000)))

    def _default_atb_fill_rate(self, *, character=None, enemy=None):
        if character is not None:
            class_base = {
                "rogue": 104,
                "ranger": 96,
                "warrior": 82,
                "paladin": 76,
                "cleric": 74,
                "mage": 78,
                "druid": 84,
            }.get(getattr(character.db, "brave_class", ""), 84)
            primary = dict(getattr(character.db, "brave_primary_stats", {}) or {})
            agility = int(primary.get("agility", 0) or 0)
            return max(68, min(168, class_base + (agility * 8)))
        if enemy is not None:
            fill_rate = 78 + (int(enemy.get("dodge", 0) or 0) * 5) + (int(enemy.get("accuracy", 0) or 0) // 20)
            tags = set(enemy.get("tags", []) or [])
            if "boss" in tags:
                fill_rate -= 12
            if {"flying", "beast", "skirmisher", "wisp"} & tags:
                fill_rate += 10
            if {"armored", "undead", "slime"} & tags:
                fill_rate -= 6
            return max(70, min(170, fill_rate))
        return 84

    def _get_actor_atb_state(self, character=None, enemy=None):
        states = dict(self.db.atb_states or {})
        key = self._actor_atb_key(character=character, enemy=enemy)
        if key not in states:
            states[key] = create_atb_state(
                fill_rate=self._default_atb_fill_rate(character=character, enemy=enemy),
                ready_gauge=ATB_READY_GAUGE,
                tick_ms=BraveEncounter._atb_tick_ms(self),
            )
            self.db.atb_states = states
        return states[key]

    def _save_actor_atb_state(self, state, *, character=None, enemy=None):
        states = dict(self.db.atb_states or {})
        key = self._actor_atb_key(character=character, enemy=enemy)
        raw_state = dict(state or {})
        raw_state.setdefault("ready_gauge", ATB_READY_GAUGE)
        states[key] = create_atb_state(**raw_state, tick_ms=BraveEncounter._atb_tick_ms(self))
        self.db.atb_states = states

    def _clear_actor_atb_state(self, *, character=None, enemy=None):
        states = dict(self.db.atb_states or {})
        states.pop(self._actor_atb_key(character=character, enemy=enemy), None)
        self.db.atb_states = states

    def _pause_non_active_atb_states(self, duration_ms, *, active_character=None, active_enemy=None):
        """Shift paused actors forward in time so frozen bars resume cleanly."""

        pause_ms = max(0, int(duration_ms or 0))
        if pause_ms <= 0:
            return

        active_key = None
        if active_character is not None:
            active_key = self._actor_atb_key(character=active_character)
        elif active_enemy is not None:
            active_key = self._actor_atb_key(enemy=active_enemy)

        freezeable_phases = {"charging", "recovering", "cooldown"}
        tick_ms = BraveEncounter._atb_tick_ms(self)
        now_ms = int(round(time.time() * 1000))

        get_active_participants = getattr(self, "get_active_participants", None)
        participants = list(get_active_participants()) if callable(get_active_participants) else []
        for participant in participants:
            actor_key = self._actor_atb_key(character=participant)
            if actor_key == active_key:
                continue
            state = dict(self._get_actor_atb_state(character=participant) or {})
            if state.get("phase") not in freezeable_phases:
                continue
            started_at = int(state.get("phase_started_at_ms", now_ms) or now_ms)
            elapsed_ms = max(0, now_ms - started_at)
            state = advance_atb_state_by_ms(
                state,
                elapsed_ms,
                tick_ms=tick_ms,
                now_ms=started_at,
            )
            state["phase_started_at_ms"] = int(state.get("phase_started_at_ms", now_ms) or now_ms) + pause_ms
            self._save_actor_atb_state(state, character=participant)

        get_active_enemies = getattr(self, "get_active_enemies", None)
        enemies = list(get_active_enemies()) if callable(get_active_enemies) else []
        for enemy in enemies:
            actor_key = self._actor_atb_key(enemy=enemy)
            if actor_key == active_key:
                continue
            state = dict(self._get_actor_atb_state(enemy=enemy) or {})
            if state.get("phase") not in freezeable_phases:
                continue
            started_at = int(state.get("phase_started_at_ms", now_ms) or now_ms)
            elapsed_ms = max(0, now_ms - started_at)
            state = advance_atb_state_by_ms(
                state,
                elapsed_ms,
                tick_ms=tick_ms,
                now_ms=started_at,
            )
            state["phase_started_at_ms"] = int(state.get("phase_started_at_ms", now_ms) or now_ms) + pause_ms
            self._save_actor_atb_state(state, enemy=enemy)

    def _player_action_timing(self, action):
        kind = (action or {}).get("kind")
        if kind == "ability":
            return get_ability_atb_profile(action.get("ability"), ABILITY_LIBRARY.get(action.get("ability")))
        if kind == "item":
            item = ITEM_TEMPLATES.get(action.get("item"), {})
            use = get_item_use_profile(item, context="combat") or {}
            return get_item_atb_profile(action.get("item"), use)
        if kind == "flee":
            return dict(DEFAULT_FLEE_ATB_PROFILE)
        return dict(DEFAULT_ATTACK_ATB_PROFILE)

    def _enemy_action_timing(self, enemy):
        template_key = (enemy or {}).get("template_key")
        if template_key in {"old_greymaw", "miretooth", "tower_archer", "mag_clamp_drone"}:
            return normalize_atb_profile({"windup_ticks": 1, "recovery_ticks": 1, "telegraph": True})
        if template_key in {"sir_edric_restless", "foreman_coilback", "captain_varn_blackreed", "grubnak_the_pot_king", "hollow_lantern"}:
            return normalize_atb_profile({"windup_ticks": 2, "recovery_ticks": 1, "telegraph": True})
        return dict(DEFAULT_ENEMY_ATTACK_ATB_PROFILE)

    def _enemy_action_label(self, enemy):
        template_key = (enemy or {}).get("template_key")
        return {
            "old_greymaw": "Brush Pounce",
            "miretooth": "Reed Ambush",
            "tower_archer": "Aimed Shot",
            "mag_clamp_drone": "Clamp Burst",
            "sir_edric_restless": "Funeral Charge",
            "foreman_coilback": "Overcharge Arc",
            "captain_varn_blackreed": "Execution Cut",
            "grubnak_the_pot_king": "Cauldron Rush",
            "hollow_lantern": "Blackwater Flare",
        }.get(template_key, "Attack")

    def _enemy_telegraph_message(self, enemy):
        label = self._enemy_action_label(enemy)
        return {
            "old_greymaw": f"|y{enemy['key']} lowers into the brush, gathering for {label}.|n",
            "miretooth": f"|y{enemy['key']} disappears into the reeds and lines up {label}.|n",
            "tower_archer": f"|y{enemy['key']} draws a careful bead for {label}.|n",
            "mag_clamp_drone": f"|y{enemy['key']} locks its rig and charges {label}.|n",
            "sir_edric_restless": f"|y{enemy['key']} raises his blade for {label}.|n",
            "foreman_coilback": f"|y{enemy['key']} routes static through the frame for {label}.|n",
            "captain_varn_blackreed": f"|y{enemy['key']} shifts his stance and sets up {label}.|n",
            "grubnak_the_pot_king": f"|y{enemy['key']} heaves the cauldron high for {label}.|n",
            "hollow_lantern": f"|y{enemy['key']} swells with drowned light and prepares {label}.|n",
        }.get((enemy or {}).get("template_key"), f"|y{enemy['key']} prepares an attack.|n")

    def _describe_pending_action(self, character, action_override=None):
        if action_override is None:
            atb_state = self._get_actor_atb_state(character=character)
            active_action = atb_state.get("current_action")
            if active_action and atb_state.get("phase") == "winding":
                action_text = self._describe_pending_action(character, action_override=active_action)
                return f"winding -> {action_text}"
            if atb_state.get("phase") in {"recovering", "cooldown"}:
                return "recovering"
        pending = dict(self.db.pending_actions or {})
        action = action_override or pending.get(str(character.id))
        if not action:
            return "basic attack"

        if action["kind"] == "attack":
            target = self.get_enemy(action["target"]) if action.get("target") else self._default_enemy_target()
            target_name = _combat_target_name(target, "nearest enemy")
            return f"attack -> {target_name}"

        if action["kind"] == "ability":
            ability_name = _ability_display_name(character, action["ability"])
            target_name = "self"
            ability = ABILITY_LIBRARY[action["ability"]]
            if ability["target"] == "enemy":
                target = self.get_enemy(action["target"]) if action.get("target") else self._default_enemy_target()
                target_name = _combat_target_name(target, "nearest enemy")
            elif ability["target"] == "ally":
                target = self._get_character(action.get("target")) if action.get("target") else character
                target_name = target.key if target else character.key
            return f"{ability_name} -> {target_name}"

        if action["kind"] == "flee":
            destination_name = action.get("destination_name") or "the previous room"
            return f"flee -> {destination_name}"

        if action["kind"] == "item":
            item = ITEM_TEMPLATES.get(action.get("item"))
            use = get_item_use_profile(item) or {}
            verb = use.get("verb", "use")
            target_name = item["name"] if item else "item"
            if use.get("target") == "enemy":
                target = self.get_enemy(action.get("target")) if action.get("target") else self._default_enemy_target()
                target_name = _combat_target_name(target, target_name)
            elif use.get("target") == "ally":
                target = self._get_character(action.get("target")) if action.get("target") else character
                target_name = target.key if target else character.key
            return f"{verb} -> {target_name}"

        return "action queued"

    def format_enemy_status(self):
        """Return a formatted enemy list."""

        enemies = self.get_active_enemies()
        if not enemies:
            return "No enemies remain."

        lines = ["|wEnemies|n"]
        for enemy in enemies:
            status = f"{enemy['hp']}/{enemy['max_hp']} HP"
            conditions = []
            if enemy["marked_turns"] > 0:
                conditions.append("marked")
            if enemy.get("bound_turns", 0) > 0:
                conditions.append("bound")
            if enemy.get("hidden_turns", 0) > 0:
                conditions.append("hidden")
            if enemy.get("shielded"):
                conditions.append("warded")
            if conditions:
                status += ", " + ", ".join(conditions)
            lines.append(f"  {enemy['id']}: {enemy['key']} ({status})")
        return "\n".join(lines)

    def _render_bar(self, current, maximum, width=15, color="|g", empty_color="|x"):
        """Render a text-based progress bar."""
        if maximum <= 0: return "[ " + " " * width + " ]"
        filled = int((max(0, current) / maximum) * width)
        return f"[{color}{'|' * filled}{empty_color}{'-' * (width - filled)}|n]"

    def format_enemy_status(self):
        """Return a visual enemy dashboard."""
        enemies = self.get_active_enemies()
        if not enemies:
            return "    |x(No active threats)|n"

        lines = []
        for enemy in enemies:
            bar = self._render_bar(enemy["hp"], enemy["max_hp"], width=20, color="|r")
            
            # Status flags
            flags = []
            if enemy.get("marked_turns", 0) > 0: flags.append("|m[MARK]|n")
            if enemy.get("bound_turns", 0) > 0: flags.append("|c[BIND]|n")
            flag_str = " ".join(flags)

            lines.append(
                f"  {enemy['id'].ljust(3)} |w{enemy['key'].ljust(18)}|n {bar} "
                f"{str(enemy['hp']).rjust(3)}/{str(enemy['max_hp']).ljust(3)} {flag_str}"
            )
        return "\n".join(lines)

    def format_party_status(self):
        """Return a visual party dashboard."""
        participants = self.get_active_participants()
        if not participants:
            return "    |x(No conscious members)|n"

        lines = []
        for participant in participants:
            participant.ensure_brave_character()
            resources = participant.db.brave_resources or {}
            derived = participant.db.brave_derived_stats or {}
            primary_resource = self._primary_resource_key(participant)
            primary_label = get_resource_label(primary_resource, participant)
            state = self._get_participant_state(participant)
            
            # Health and Resource Bars
            hp_bar = self._render_bar(resources.get("hp", 0), derived.get("max_hp", 1), width=12, color="|g")
            res_color = "|b" if primary_resource == "mana" else "|y"
            res_bar = self._render_bar(resources.get(primary_resource, 0), derived.get(f"max_{primary_resource}", 1), width=12, color=res_color)
            
            # Condition Icons
            conds = []
            if state.get("guard", 0) > 0: conds.append("|w[G]|n")
            if state.get("bleed_turns", 0) > 0: conds.append("|r[B]|n")
            if state.get("poison_turns", 0) > 0: conds.append("|g[P]|n")
            if state.get("feint_turns", 0) > 0: conds.append("|m[F]|n")
            cond_str = "".join(conds).ljust(6)
            
            action_text = self._describe_pending_action(participant)

            lines.append(
                f"  |w{participant.key.ljust(10)}|n {hp_bar} |wHP|n  {res_bar} |w{primary_label[:3].upper()}|n {cond_str}\n"
                f"    |x└─ NEXT:|n |c{action_text}|n"
            )
        return "\n".join(lines)

    def format_combat_snapshot(self):
        """Return a balanced, boxed snapshot of the current fight."""
        
        from world.resonance import get_resonance_profile
        profile = get_resonance_profile(self.obj)
        cp = profile["color_primary"]
        cb = "|x" # Subtle grey border

        header = f"{cp}{self.db.encounter_title.upper()}|n"
        
        snapshot = [
            "\n" + f"{cb}" + "=" * 70 + "|n",
            f"  {header}".ljust(79) + f"{cb}|n",
            f"{cb}" + "=" * 70 + "|n",
            "  |wPARTY STATUS|n",
            self.format_party_status(),
            "\n  |x" + "-" * 66 + "|n",
            "  |wENEMIES|n",
            self.format_enemy_status(),
            f"{cb}" + "=" * 70 + "|n\n"
        ]
        return "\n".join(snapshot)

    def find_enemy(self, query=None):
        """Find an enemy by id or fuzzy name."""

        enemies = self.get_active_enemies()
        if not enemies:
            return None
        if not query:
            return enemies[0]

        query_norm = _normalize_token(query)
        for enemy in enemies:
            if query_norm == _normalize_token(enemy["id"]):
                return enemy
            if query_norm == _normalize_token(enemy["key"]):
                return enemy
        for enemy in enemies:
            if query_norm in _normalize_token(enemy["key"]):
                return enemy
        return None

    def find_participant(self, query, default=None):
        """Find a participant by fuzzy name."""

        participants = self.get_active_participants()
        if not query:
            return default or None

        query_norm = _normalize_token(query)
        for participant in participants:
            if query_norm == _normalize_token(participant.key):
                return participant
        for participant in participants:
            if query_norm in _normalize_token(participant.key):
                return participant
        return None

    def find_consumable(self, character, query, *, context="combat", verb=None):
        """Find a carried combat-usable consumable by fuzzy name."""

        return match_inventory_item(character, query, context=context, category="consumable", verb=verb)

    def add_participant(self, character):
        """Join a character to the encounter."""

        if not character or character.location != self.obj:
            return False, "You are not in the right place to join this fight."

        character.ensure_brave_character()
        if (character.db.brave_resources or {}).get("hp", 0) <= 0:
            return False, "You can't join a fight while down."

        if character.id not in self.db.participants:
            self.db.participants = list(self.db.participants or []) + [character.id]
            participant_states = dict(self.db.participant_states or {})
            participant_states[str(character.id)] = {
                "guard": 0,
                "reaction_guard": 0,
                "reaction_guard_source": None,
                "reaction_label": None,
                "reaction_redirect_to": None,
                "bleed_turns": 0,
                "bleed_damage": 0,
                "poison_turns": 0,
                "poison_damage": 0,
                "poison_accuracy_penalty": 0,
                "curse_turns": 0,
                "curse_armor_penalty": 0,
                "snare_turns": 0,
                "snare_accuracy_penalty": 0,
                "snare_dodge_penalty": 0,
                "feint_turns": 0,
                "feint_accuracy_bonus": 0,
                "feint_dodge_bonus": 0,
                "stealth_turns": 0,
            }
            self.db.participant_states = participant_states
            self._save_actor_atb_state(
                create_atb_state(
                    fill_rate=self._default_atb_fill_rate(character=character),
                    ready_gauge=ATB_READY_GAUGE,
                    tick_ms=self._atb_tick_ms(),
                ),
                character=character,
            )
            threat = dict(self.db.threat or {})
            threat[str(character.id)] = threat.get(str(character.id), 0)
            self.db.threat = threat
            self._get_participant_contribution(character)
            character.ndb.brave_encounter = self
            self.obj.msg_contents(f"{character.key} joins the fight.", exclude=[character])
            character.msg("You join the fight.")
        else:
            character.ndb.brave_encounter = self
            self._get_participant_contribution(character)

        self._refresh_browser_combat_views()

        return True, None

    def queue_attack(self, character, target_query=None):
        """Queue a basic attack."""

        target = self.find_enemy(target_query)
        if target_query and not target:
            return False, "No enemy here matches that target."

        pending = dict(self.db.pending_actions or {})
        pending[str(character.id)] = {"kind": "attack", "target": _combat_target_id(target)}
        self.db.pending_actions = pending
        target_text = _combat_target_name(target, "the nearest enemy")
        self._refresh_browser_combat_views()
        return True, f"You ready an attack against {target_text}."

    def queue_ability(self, character, raw_ability, target_query=None):
        """Queue an ability for the next combat turn."""

        ability_key = resolve_ability_query(character, raw_ability)
        if isinstance(ability_key, list):
            names = ", ".join(_ability_display_name(character, key) for key in ability_key)
            return False, f"Be more specific. That could mean: {names}"

        ability = ABILITY_LIBRARY.get(ability_key)
        if not ability and ability_key in PASSIVE_ABILITY_BONUSES:
            return False, f"{_ability_display_name(character, ability_key)} is a passive trait and is always active."
        if not ability or ability["class"] != character.db.brave_class:
            return False, "That ability is not available to your current class in this slice."

        unlocked = {_normalize_token(name) for name in character.get_unlocked_abilities()}
        if ability_key not in unlocked:
            return False, "You have not unlocked that ability yet."

        current = character.db.brave_resources[ability["resource"]]
        if current < ability["cost"]:
            resource_name = get_resource_label(ability["resource"], character).lower()
            return False, f"You don't have enough {resource_name} for {_ability_display_name(character, ability_key)}."

        target = None
        if ability["target"] == "enemy":
            target = self.find_enemy(target_query)
            if target_query and not target:
                return False, "No enemy here matches that target."
        elif ability["target"] == "ally":
            target = self.find_participant(target_query, default=character)
            if target_query and not target:
                return False, "No ally here matches that target."
            if not target:
                target = character
        elif ability["target"] == "none":
            target = None
        else:
            target = character

        pending = dict(self.db.pending_actions or {})
        pending[str(character.id)] = {
            "kind": "ability",
            "ability": ability_key,
            "target": _combat_target_id(target),
        }
        self.db.pending_actions = pending

        target_text = "the field" if ability["target"] == "none" else _combat_target_name(target, character.key)
        self._refresh_browser_combat_views()
        return True, f"You prepare {_ability_display_name(character, ability_key)} for {target_text}."

    def _get_flee_destination(self, character):
        destination = getattr(getattr(character, "ndb", None), "brave_previous_location", None)
        if not destination or destination == self.obj:
            return None
        return destination

    def _get_flee_chance(self, character):
        derived = self._get_effective_derived(character)
        state = self._get_participant_state(character)
        enemy_count = len(self.get_active_enemies())
        chance = 52 + derived.get("dodge", 0) - max(0, enemy_count - 1) * 6
        if state.get("snare_turns", 0) > 0:
            chance -= 20
        if state.get("bleed_turns", 0) > 0:
            chance -= 5
        return max(20, min(85, chance))

    def queue_flee(self, character):
        """Queue a retreat back to the previous room."""

        destination = self._get_flee_destination(character)
        if not destination:
            return False, "You do not have a clear route to fall back from here."

        pending = dict(self.db.pending_actions or {})
        pending[str(character.id)] = {
            "kind": "flee",
            "destination_name": destination.key,
        }
        self.db.pending_actions = pending
        self._refresh_browser_combat_views()
        return True, f"You look for an opening to fall back to {destination.key}."

    def queue_item(self, character, query, target_query=None):
        """Queue a combat-usable consumable for the next combat turn."""

        match = self.find_consumable(character, query, context="combat")
        if isinstance(match, list):
            names = ", ".join(ITEM_TEMPLATES[key]["name"] for key in match)
            return False, f"Be more specific. That could mean: {names}"
        if not match:
            return False, "You do not have a combat-usable consumable matching that."

        use = get_item_use_profile(match, context="combat") or {}
        target_type = use.get("target", "self")
        target = None
        if target_type == "enemy":
            target = self.find_enemy(target_query)
            if target_query and not target:
                return False, "No enemy here matches that target."
        elif target_type == "ally":
            target = self.find_participant(target_query, default=character)
            if target_query and not target:
                return False, "No ally here matches that target."
            if not target:
                target = character
        elif target_type == "none":
            target = None
        else:
            target = character

        pending = dict(self.db.pending_actions or {})
        pending[str(character.id)] = {
            "kind": "item",
            "item": match,
            "target": _combat_target_id(target),
        }
        self.db.pending_actions = pending

        target_text = "the field" if target_type == "none" else _combat_target_name(target, character.key)
        self._refresh_browser_combat_views()
        return True, f"You ready {ITEM_TEMPLATES[match]['name']} for {target_text}."

    def queue_meal(self, character, query):
        """Backward-compatible meal wrapper for older command paths."""

        return self.queue_item(character, query)

    def _get_participant_state(self, character):
        states = dict(self.db.participant_states or {})
        key = str(character.id)
        if key not in states:
            states[key] = {
                "guard": 0,
                "reaction_guard": 0,
                "reaction_guard_source": None,
                "reaction_label": None,
                "reaction_redirect_to": None,
                "bleed_turns": 0,
                "bleed_damage": 0,
                "poison_turns": 0,
                "poison_damage": 0,
                "poison_accuracy_penalty": 0,
                "curse_turns": 0,
                "curse_armor_penalty": 0,
                "snare_turns": 0,
                "snare_accuracy_penalty": 0,
                "snare_dodge_penalty": 0,
                "feint_turns": 0,
                "feint_accuracy_bonus": 0,
                "feint_dodge_bonus": 0,
                "stealth_turns": 0,
            }
            self.db.participant_states = states
        return states[key]

    def _save_participant_state(self, character, state):
        states = dict(self.db.participant_states or {})
        states[str(character.id)] = state
        self.db.participant_states = states

    def _save_enemy(self, enemy):
        enemies = []
        for current in self.db.enemies or []:
            enemies.append(enemy if current["id"] == enemy["id"] else current)
        self.db.enemies = enemies

    def _spawn_enemy(self, template_key, display_key=None, announce=True):
        """Create and add a new enemy entry from a template."""

        template = ENEMY_TEMPLATES[template_key]
        counter = int(self.db.enemy_counter or 0) + 1
        self.db.enemy_counter = counter
        enemy = {
            "id": f"e{counter}",
            "template_key": template_key,
            "key": display_key or template["name"],
            "tags": list(template["tags"]),
            "max_hp": template["max_hp"],
            "hp": template["max_hp"],
            "attack_power": template["attack_power"],
            "armor": template["armor"],
            "accuracy": template["accuracy"],
            "dodge": template["dodge"],
            "xp": template["xp"],
            "attack_kind": template.get("attack_kind", "weapon"),
            "spell_power": template.get("spell_power", template["attack_power"]),
            "target_strategy": template.get("target_strategy", "highest_threat"),
            "special": template.get("special"),
            "marked_turns": 0,
            "bound_turns": 0,
            "bleed_turns": 0,
            "bleed_damage": 0,
            "poison_turns": 0,
            "poison_damage": 0,
            "called_help": False,
            "enraged": False,
            "hidden_turns": 0,
            "reposition_ready": False,
            "reposition_used": False,
            "shielded": False,
            "shield_broken": False,
        }

        scaling = self._get_scaling_profile()
        enemy["max_hp"] = max(1, int(round(enemy["max_hp"] * scaling["hp"])))
        enemy["hp"] = enemy["max_hp"]
        enemy["attack_power"] = max(1, int(round(enemy["attack_power"] * scaling["power"])))
        enemy["spell_power"] = max(1, int(round(enemy["spell_power"] * scaling["power"])))
        enemy["accuracy"] = max(35, enemy["accuracy"] + scaling["accuracy"])

        enemies = list(self.db.enemies or [])
        enemies.append(enemy)
        self.db.enemies = enemies
        self._save_actor_atb_state(
            create_atb_state(
                fill_rate=self._default_atb_fill_rate(enemy=enemy),
                ready_gauge=ATB_READY_GAUGE,
                tick_ms=self._atb_tick_ms(),
            ),
            enemy=enemy,
        )
        if announce and self.obj:
            self.obj.msg_contents(f"|r{enemy['key']} joins the fight!|n")
        return enemy

    def _add_threat(self, character, amount):
        threat = dict(self.db.threat or {})
        key = str(character.id)
        threat[key] = threat.get(key, 0) + max(0, amount)
        self.db.threat = threat

    def _roll_hit(self, accuracy, dodge):
        chance = max(35, min(95, 55 + accuracy - dodge))
        return random.randint(1, 100) <= chance

    def _weapon_damage(self, attack_power, armor, bonus=0):
        return max(1, attack_power // 2 + random.randint(2, 6) + bonus - armor // 4)

    def _spell_damage(self, spell_power, armor, bonus=0):
        return max(1, spell_power // 2 + random.randint(3, 7) + bonus - armor // 5)

    def _spend_resource(self, character, resource, amount):
        resources = dict(character.db.brave_resources or {})
        resources[resource] = max(0, resources[resource] - amount)
        character.db.brave_resources = resources

    def _get_effective_derived(self, character):
        derived = dict(character.db.brave_derived_stats or {})
        state = self._get_participant_state(character)
        if state.get("curse_turns", 0) > 0:
            derived["armor"] = max(0, derived.get("armor", 0) - state.get("curse_armor_penalty", 0))
        if state.get("snare_turns", 0) > 0:
            derived["accuracy"] = max(0, derived.get("accuracy", 0) - state.get("snare_accuracy_penalty", 0))
            derived["dodge"] = max(0, derived.get("dodge", 0) - state.get("snare_dodge_penalty", 0))
        if state.get("poison_turns", 0) > 0:
            derived["accuracy"] = max(0, derived.get("accuracy", 0) - state.get("poison_accuracy_penalty", 0))
        if state.get("feint_turns", 0) > 0:
            derived["accuracy"] = derived.get("accuracy", 0) + state.get("feint_accuracy_bonus", 0)
            derived["dodge"] = derived.get("dodge", 0) + state.get("feint_dodge_bonus", 0)
        return derived

    def _consume_feint_bonus(self, character):
        """Consume an active rogue feint setup for bonus damage."""

        state = self._get_participant_state(character)
        if state.get("feint_turns", 0) <= 0:
            return 0

        bonus = 4
        state["feint_turns"] = 0
        state["feint_accuracy_bonus"] = 0
        state["feint_dodge_bonus"] = 0
        self._save_participant_state(character, state)
        return bonus

    def _scaled_heal_amount(self, derived, base, variance=4, divisor=3):
        """Return a healing amount that scales with spell power and healing traits."""

        return base + derived.get("spell_power", 0) // max(1, divisor) + derived.get("healing_power", 0) + random.randint(0, variance)

    def _consume_stealth_bonus(self, character):
        """Consume a one-turn stealth setup for rogue burst abilities."""

        state = self._get_participant_state(character)
        if state.get("stealth_turns", 0) <= 0:
            return 0

        state["stealth_turns"] = 0
        self._save_participant_state(character, state)
        return 6

    def _damage_enemy(self, attacker, enemy, damage, extra_text="", damage_type="physical"):
        if enemy["marked_turns"] > 0:
            damage += 4
        if enemy.get("shielded"):
            damage = max(1, damage // 2)
            extra_text = " The ward absorbs part of the blow." + extra_text
        enemy["hp"] = max(0, enemy["hp"] - damage)
        self._save_enemy(enemy)
        self._add_threat(attacker, damage + (8 if attacker.db.brave_class == "warrior" else 0))
        self._record_participant_contribution(attacker, meaningful=True, damage=damage)
        marked_text = " The mark flares." if enemy["marked_turns"] > 0 else ""
        self.obj.msg_contents(f"{attacker.key} hits {enemy['key']} for {damage} damage.{marked_text}{extra_text}")
        self._emit_combat_fx(
            kind="damage",
            source=attacker.key,
            target=enemy["key"],
            source_ref=_combat_entry_ref(attacker),
            target_ref=_combat_entry_ref(enemy),
            amount=damage,
            text=str(damage),
            tone="damage",
            impact="damage",
            element=damage_type,
            lunge=True,
        )
        if enemy["hp"] <= 0:
            self._emit_defeat_fx(enemy)
            self.obj.msg_contents(f"{enemy['key']} falls.")
            self._award_enemy_defeat_credit(enemy)

    def _heal_character(self, source, target, amount, heal_type="healing"):
        resources = dict(target.db.brave_resources or {})
        max_hp = target.db.brave_derived_stats["max_hp"]
        before = resources["hp"]
        resources["hp"] = min(max_hp, resources["hp"] + amount)
        target.db.brave_resources = resources
        healed = resources["hp"] - before
        self._add_threat(source, max(1, healed // 2))
        if healed > 0:
            self._record_participant_contribution(source, meaningful=True, healing=healed)
        self.obj.msg_contents(f"{source.key} restores {healed} HP to {target.key}.")
        self._emit_combat_fx(
            kind="heal",
            source=source.key,
            target=target.key,
            source_ref=_combat_entry_ref(source),
            target_ref=_combat_entry_ref(target),
            amount=healed,
            text=str(healed),
            tone="heal",
            impact="heal",
            element=heal_type,
        )

    def _heal_enemy(self, source_enemy, target_enemy, amount):
        before = target_enemy["hp"]
        target_enemy["hp"] = min(target_enemy["max_hp"], target_enemy["hp"] + amount)
        healed = target_enemy["hp"] - before
        if healed <= 0:
            return False
        self._save_enemy(target_enemy)
        self.obj.msg_contents(f"{source_enemy['key']} mends {target_enemy['key']} for {healed} HP.")
        return True

    def _apply_bleed(self, target, turns, damage):
        state = self._get_participant_state(target)
        state["bleed_turns"] = max(state.get("bleed_turns", 0), turns)
        state["bleed_damage"] = max(state.get("bleed_damage", 0), damage)
        self._save_participant_state(target, state)
        self.obj.msg_contents(f"|r{target.key} starts bleeding!|n")

    def _apply_curse(self, target, turns, armor_penalty, message=None):
        state = self._get_participant_state(target)
        state["curse_turns"] = max(state.get("curse_turns", 0), turns)
        state["curse_armor_penalty"] = max(state.get("curse_armor_penalty", 0), armor_penalty)
        self._save_participant_state(target, state)
        self.obj.msg_contents(message or f"|m{target.key} is cursed!|n")

    def _apply_poison(self, target, turns, damage, accuracy_penalty, message=None):
        state = self._get_participant_state(target)
        state["poison_turns"] = max(state.get("poison_turns", 0), turns)
        state["poison_damage"] = max(state.get("poison_damage", 0), damage)
        state["poison_accuracy_penalty"] = max(state.get("poison_accuracy_penalty", 0), accuracy_penalty)
        self._save_participant_state(target, state)
        self.obj.msg_contents(message or f"|g{target.key} is poisoned!|n")

    def _apply_enemy_bleed(self, enemy, turns, damage, message=None):
        enemy["bleed_turns"] = max(enemy.get("bleed_turns", 0), turns)
        enemy["bleed_damage"] = max(enemy.get("bleed_damage", 0), damage)
        self._save_enemy(enemy)
        self.obj.msg_contents(message or f"|r{enemy['key']} starts bleeding!|n")

    def _apply_enemy_poison(self, enemy, turns, damage, message=None):
        enemy["poison_turns"] = max(enemy.get("poison_turns", 0), turns)
        enemy["poison_damage"] = max(enemy.get("poison_damage", 0), damage)
        self._save_enemy(enemy)
        self.obj.msg_contents(message or f"|g{enemy['key']} is poisoned!|n")

    def _apply_snare(self, target, turns, accuracy_penalty, dodge_penalty):
        state = self._get_participant_state(target)
        state["snare_turns"] = max(state.get("snare_turns", 0), turns)
        state["snare_accuracy_penalty"] = max(state.get("snare_accuracy_penalty", 0), accuracy_penalty)
        state["snare_dodge_penalty"] = max(state.get("snare_dodge_penalty", 0), dodge_penalty)
        self._save_participant_state(target, state)
        self.obj.msg_contents(f"|y{target.key} is tangled in webbing!|n")

    def _clear_one_harmful_effect(self, target):
        """Clear one harmful participant effect if present."""

        state = self._get_participant_state(target)
        cleared = None

        if state.get("bleed_turns", 0) > 0:
            state["bleed_turns"] = 0
            state["bleed_damage"] = 0
            cleared = "bleeding"
        elif state.get("poison_turns", 0) > 0:
            state["poison_turns"] = 0
            state["poison_damage"] = 0
            state["poison_accuracy_penalty"] = 0
            cleared = "poison"
        elif state.get("curse_turns", 0) > 0:
            state["curse_turns"] = 0
            state["curse_armor_penalty"] = 0
            cleared = "curse"
        elif state.get("snare_turns", 0) > 0:
            state["snare_turns"] = 0
            state["snare_accuracy_penalty"] = 0
            state["snare_dodge_penalty"] = 0
            cleared = "snare"

        if cleared:
            self._save_participant_state(target, state)
        return cleared

    def _apply_participant_effects(self):
        for participant in list(self.get_active_participants()):
            state = self._get_participant_state(participant)
            bleed_turns = state.get("bleed_turns", 0)
            resources = dict(participant.db.brave_resources or {})

            if bleed_turns > 0:
                damage = max(1, state.get("bleed_damage", 1))
                resources["hp"] = max(0, resources["hp"] - damage)
                participant.db.brave_resources = resources
                self.obj.msg_contents(f"|r{participant.key} bleeds for {damage} damage.|n")
                self._emit_combat_fx(
                    kind="damage",
                    target=participant.key,
                    target_ref=_combat_entry_ref(participant),
                    amount=damage,
                    text=str(damage),
                    tone="damage",
                    impact="damage",
                    element="bleed",
                )
                state["bleed_turns"] = max(0, bleed_turns - 1)
                if state["bleed_turns"] <= 0:
                    state["bleed_damage"] = 0

                if resources["hp"] <= 0:
                    self._save_participant_state(participant, state)
                    self._defeat_character(participant)
                    continue

            poison_turns = state.get("poison_turns", 0)
            if poison_turns > 0:
                damage = max(1, state.get("poison_damage", 1))
                resources["hp"] = max(0, resources["hp"] - damage)
                participant.db.brave_resources = resources
                self.obj.msg_contents(f"|g{participant.key} suffers {damage} poison damage.|n")
                self._emit_combat_fx(
                    kind="damage",
                    target=participant.key,
                    target_ref=_combat_entry_ref(participant),
                    amount=damage,
                    text=str(damage),
                    tone="damage",
                    impact="damage",
                    element="poison",
                )
                state["poison_turns"] = max(0, poison_turns - 1)
                if state["poison_turns"] <= 0:
                    state["poison_damage"] = 0
                    state["poison_accuracy_penalty"] = 0
                    self.obj.msg_contents(f"{participant.key} fights the poison clear.")

                if resources["hp"] <= 0:
                    self._save_participant_state(participant, state)
                    self._defeat_character(participant)
                    continue

            if state.get("curse_turns", 0) > 0:
                state["curse_turns"] = max(0, state["curse_turns"] - 1)
                if state["curse_turns"] <= 0 and state.get("curse_armor_penalty", 0):
                    state["curse_armor_penalty"] = 0
                    self.obj.msg_contents(f"{participant.key} shakes off the curse.")

            if state.get("snare_turns", 0) > 0:
                state["snare_turns"] = max(0, state["snare_turns"] - 1)
                if state["snare_turns"] <= 0:
                    state["snare_accuracy_penalty"] = 0
                    state["snare_dodge_penalty"] = 0
                    self.obj.msg_contents(f"{participant.key} tears free of the webbing.")

            self._save_participant_state(participant, state)

    def _apply_enemy_effects(self):
        """Tick persistent bleed and poison effects on living enemies."""

        for enemy in list(self.get_active_enemies()):
            changed = False

            if enemy.get("bleed_turns", 0) > 0:
                damage = max(1, enemy.get("bleed_damage", 1))
                enemy["hp"] = max(0, enemy["hp"] - damage)
                enemy["bleed_turns"] = max(0, enemy["bleed_turns"] - 1)
                if enemy["bleed_turns"] <= 0:
                    enemy["bleed_damage"] = 0
                self.obj.msg_contents(f"|r{enemy['key']} bleeds for {damage} damage.|n")
                changed = True

            if enemy["hp"] > 0 and enemy.get("poison_turns", 0) > 0:
                damage = max(1, enemy.get("poison_damage", 1))
                enemy["hp"] = max(0, enemy["hp"] - damage)
                enemy["poison_turns"] = max(0, enemy["poison_turns"] - 1)
                if enemy["poison_turns"] <= 0:
                    enemy["poison_damage"] = 0
                self.obj.msg_contents(f"|g{enemy['key']} suffers {damage} poison damage.|n")
                self._emit_combat_fx(
                    kind="damage",
                    target=enemy["key"],
                    target_ref=_combat_entry_ref(enemy),
                    amount=damage,
                    text=str(damage),
                    tone="damage",
                    impact="damage",
                    element="poison",
                )
                changed = True

            if changed:
                self._save_enemy(enemy)
                if enemy["hp"] <= 0:
                    self._emit_defeat_fx(enemy)
                    self.obj.msg_contents(f"{enemy['key']} falls.")
                    self._award_enemy_defeat_credit(enemy)

    def _handle_enemy_specials(self, enemy):
        """Apply special boss or elite behaviors before an enemy acts."""

        changed = False
        if enemy["template_key"] == "ruk_fence_cutter":
            if enemy["hp"] <= enemy["max_hp"] // 2 and not enemy.get("enraged"):
                enemy["enraged"] = True
                enemy["attack_power"] += 4
                enemy["accuracy"] += 6
                self.obj.msg_contents("|rRuk howls and fights with renewed savagery!|n")
                changed = True

            if enemy["hp"] <= enemy["max_hp"] // 2 and not enemy.get("called_help"):
                self._spawn_enemy("goblin_slinger", display_key="Goblin Slinger Reinforcement")
                enemy["called_help"] = True
                self.obj.msg_contents("|rRuk bellows for help, and another goblin scrambles into the camp!|n")
                changed = True

        if enemy["template_key"] == "old_greymaw":
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("reposition_used"):
                enemy["reposition_used"] = True
                enemy["hidden_turns"] = 1
                enemy["reposition_ready"] = True
                enemy["marked_turns"] = 0
                self.obj.msg_contents("|rOld Greymaw vanishes into the brush.|n")
                changed = True

        if enemy["template_key"] == "foreman_coilback":
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("called_help"):
                self._spawn_enemy("relay_tick", display_key="Relay Tick Overwatch")
                enemy["called_help"] = True
                self.obj.msg_contents("|rForeman Coilback vents static through the pit and a relay tick drops into the fight!|n")
                changed = True

            if enemy["hp"] <= enemy["max_hp"] // 2 and not enemy.get("enraged"):
                enemy["enraged"] = True
                enemy["attack_power"] += 3
                enemy["spell_power"] += 4
                enemy["accuracy"] += 4
                self.obj.msg_contents("|rForeman Coilback overcharges his rig and the whole pit starts to scream.|n")
                changed = True

        if enemy["template_key"] == "sir_edric_restless":
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("called_help"):
                self._spawn_enemy("restless_shade", display_key="Edric's Grave Shade")
                self._spawn_enemy("barrow_wisp", display_key="Edric's Grave-Light")
                enemy["called_help"] = True
                enemy["shielded"] = True
                self.obj.msg_contents(
                    "|rSir Edric raises his blade and the barrow answers. Grave-light coils around him as lesser dead rise to his call!|n"
                )
                changed = True

            if enemy.get("shielded"):
                other_dead = [
                    other
                    for other in self.get_active_enemies()
                    if other["id"] != enemy["id"]
                ]
                if not other_dead:
                    enemy["shielded"] = False
                    enemy["shield_broken"] = True
                    self.obj.msg_contents("|ySir Edric's grave ward gutters out as his summoned dead collapse.|n")
                    changed = True

            if enemy["hp"] <= enemy["max_hp"] // 3 and not enemy.get("enraged"):
                enemy["enraged"] = True
                enemy["attack_power"] += 4
                enemy["spell_power"] += 4
                enemy["accuracy"] += 5
                self.obj.msg_contents("|rSir Edric lowers the last of his restraint and advances with funeral wrath.|n")
                changed = True

        if enemy["template_key"] == "captain_varn_blackreed":
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("called_help"):
                self._spawn_enemy("tower_archer", display_key="Blackreed Tower Archer")
                self._spawn_enemy("bandit_raider", display_key="Blackreed Shieldman")
                enemy["called_help"] = True
                self.obj.msg_contents(
                    "|rBlackreed snaps a command across the tower and the upper line answers at once: one bow, one shield, no wasted motion.|n"
                )
                changed = True

            if enemy["hp"] <= enemy["max_hp"] // 2 and not enemy.get("enraged"):
                enemy["enraged"] = True
                enemy["attack_power"] += 4
                enemy["accuracy"] += 5
                enemy["dodge"] += 3
                self.obj.msg_contents("|rBlackreed shifts his footing, reads the fight, and starts cutting for the weak points.|n")
                changed = True

        if enemy["template_key"] == "grubnak_the_pot_king":
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("called_help"):
                self._spawn_enemy("goblin_brute", display_key="Pot-King Guard")
                self._spawn_enemy("goblin_hexer", display_key="Cauldron Hexer")
                enemy["called_help"] = True
                self.obj.msg_contents(
                    "|rGrubnak hammers his ladle against the court stones and the warrens answer: one brute, one hexer, both already halfway into the kill.|n"
                )
                changed = True

            if enemy["hp"] <= enemy["max_hp"] // 2 and not enemy.get("enraged"):
                enemy["enraged"] = True
                enemy["attack_power"] += 4
                enemy["spell_power"] += 4
                enemy["accuracy"] += 4
                self.obj.msg_contents("|rGrubnak kicks the cauldron trench wide and comes on in a boiling frenzy.|n")
                changed = True

        if enemy["template_key"] == "miretooth":
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("reposition_used"):
                enemy["reposition_used"] = True
                enemy["hidden_turns"] = 1
                enemy["reposition_ready"] = True
                enemy["marked_turns"] = 0
                self.obj.msg_contents("|rMiretooth slips under the reeds and the whole fen holds its breath around the gap he left behind.|n")
                changed = True

            if enemy["hp"] <= enemy["max_hp"] // 2 and not enemy.get("enraged"):
                enemy["enraged"] = True
                enemy["attack_power"] += 5
                enemy["accuracy"] += 4
                enemy["dodge"] += 4
                self.obj.msg_contents("|rMiretooth throws back a low fen howl and comes on meaner, faster, and much too sure of himself.|n")
                changed = True

        if enemy["template_key"] == "hollow_lantern":
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("called_help"):
                self._spawn_enemy("drowned_warder", display_key="Blackwater Warder")
                self._spawn_enemy("hollow_wisp", display_key="Lamp Wisp")
                enemy["called_help"] = True
                enemy["shielded"] = True
                self.obj.msg_contents(
                    "|rThe Hollow Lantern flares through the drowned lenswork and the old line answers. A warder rises from the blackwater while a lamp wisp feeds the light around it.|n"
                )
                changed = True

            if enemy.get("shielded"):
                other_lights = [
                    other
                    for other in self.get_active_enemies()
                    if other["id"] != enemy["id"]
                ]
                if not other_lights:
                    enemy["shielded"] = False
                    enemy["shield_broken"] = True
                    self.obj.msg_contents("|yThe Hollow Lantern's ward gutters out as the drowned support holding it together collapses.|n")
                    changed = True

            if enemy["hp"] <= enemy["max_hp"] // 2 and not enemy.get("enraged"):
                enemy["enraged"] = True
                enemy["attack_power"] += 4
                enemy["spell_power"] += 5
                enemy["accuracy"] += 4
                self.obj.msg_contents("|rThe Hollow Lantern burns hotter and the whole lamp house starts answering in bad light.|n")
                changed = True

        if changed:
            self._save_enemy(enemy)
        return enemy

    def _defeat_character(self, character):
        self._emit_defeat_fx(character)
        start_room = get_tutorial_defeat_room(character) or get_room("brambleford_town_green")
        character.clear_chapel_blessing()
        character.restore_resources()
        self._mark_defeated_participant(character)
        self.remove_participant(character)
        if start_room:
            character.move_to(start_room, quiet=True, move_type="defeat")
        if get_tutorial_defeat_room(character):
            character.msg("|rThe lesson lands hard, but not fatally. You are hauled back to Wayfarer's Yard to catch your breath and try again.|n")
        else:
            character.msg("|rYou are overwhelmed and carried back to Brambleford to recover.|n")

    def remove_participant(self, character):
        """Remove a participant from the fight."""

        participants = [pid for pid in (self.db.participants or []) if pid != character.id]
        self.db.participants = participants
        pending = dict(self.db.pending_actions or {})
        pending.pop(str(character.id), None)
        self.db.pending_actions = pending
        states = dict(self.db.participant_states or {})
        states.pop(str(character.id), None)
        self.db.participant_states = states
        self._clear_actor_atb_state(character=character)
        threat = dict(self.db.threat or {})
        threat.pop(str(character.id), None)
        self.db.threat = threat
        character.ndb.brave_encounter = None
        self._refresh_browser_combat_views()

    def _default_enemy_target(self):
        enemies = self.get_active_enemies()
        return enemies[0] if enemies else None

    def _find_wounded_enemy(self, exclude_id=None):
        candidates = [
            enemy
            for enemy in self.get_active_enemies()
            if enemy["hp"] < enemy["max_hp"] and enemy["id"] != exclude_id
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda enemy: (enemy["hp"] / enemy["max_hp"], enemy["hp"], enemy["id"]))

    def _execute_basic_attack(self, character, target=None):
        target = target or self._default_enemy_target()
        if not target:
            return

        derived = self._get_effective_derived(character)
        if not self._roll_hit(derived["accuracy"], target["dodge"]):
            self.obj.msg_contents(f"{character.key} misses {target['key']}.")
            self._emit_miss_fx(character, target)
            self._add_threat(character, 2)
            return

        bonus = self._consume_feint_bonus(character) if character.db.brave_class == "rogue" else 0
        extra_text = " The feint opens a clean line." if bonus else ""
        damage = self._weapon_damage(derived["attack_power"], target["armor"], bonus=bonus)
        self._damage_enemy(character, target, damage, extra_text=extra_text)

    def _execute_ability(self, character, action):
        ability = ABILITY_LIBRARY[action["ability"]]
        ability_name = _ability_display_name(character, action["ability"])
        target = None
        if ability["target"] == "enemy":
            target = self.get_enemy(action["target"])
        elif ability["target"] == "ally":
            target = self._get_character(action["target"])
        if ability["target"] == "enemy" and (not target or target["hp"] <= 0):
            target = self._default_enemy_target()
        if ability["target"] == "ally" and not target:
            target = character
        if ability["target"] != "none" and not target:
            return

        self._spend_resource(character, ability["resource"], ability["cost"])
        derived = self._get_effective_derived(character)
        level = max(1, int(character.db.brave_level or 1))
        allies = list(self.get_active_participants())
        enemies = list(self.get_active_enemies())
        execute_combat_ability(
            self,
            character,
            action["ability"],
            ability_name,
            target,
            derived,
            level,
            allies,
            enemies,
        )

    def _execute_flee(self, character):
        destination = self._get_flee_destination(character)
        if not destination:
            self.obj.msg_contents(f"{character.key} looks for a retreat but finds no clean way out.")
            return

        if random.randint(1, 100) > self._get_flee_chance(character):
            self.obj.msg_contents(f"{character.key} tries to break away but gets dragged back into the fight.")
            self._add_threat(character, 2)
            return

        if not character.move_to(destination, quiet=True, move_type="flee"):
            self.obj.msg_contents(f"{character.key} finds an opening but cannot get clear.")
            return

        self.remove_participant(character)
        self.obj.msg_contents(f"{character.key} breaks away and falls back to {destination.key}.")
        character.msg(f"|yYou break away from the fight and fall back to {destination.key}.|n")
        if character.location:
            character.msg(character.at_look(character.location))

    def _execute_item(self, character, action):
        from world.activities import _consume_item_by_template

        template_id = action.get("item")
        item = ITEM_TEMPLATES.get(template_id, {})
        use = get_item_use_profile(item, context="combat") or {}
        target = None
        if use.get("target") == "enemy":
            target = self.get_enemy(action.get("target")) if action.get("target") else self._default_enemy_target()
        elif use.get("target") == "ally":
            target = self._get_character(action.get("target")) if action.get("target") else character
            if not target:
                target = character

        ok, player_message, result = _consume_item_by_template(
            character,
            template_id,
            context="combat",
            cozy=False,
            target=target,
            encounter=self,
        )
        if not ok:
            character.msg(player_message)
            self.obj.msg_contents(f"{character.key} fumbles for supplies that are no longer there.")
            return

        if result and result.get("public_message"):
            self.obj.msg_contents(result["public_message"])
        if result:
            use = dict(result.get("use") or {})
            effect_type = use.get("effect_type")
            if effect_type == "damage":
                pass
            elif effect_type == "guard":
                if target is not None:
                    self._apply_reaction_guard(character, target, amount=int(result.get("guard_amount", 0) or 0), label=item.get("name", "Guard Item"))
                self._record_participant_contribution(
                    character,
                    meaningful=True,
                    mitigation=int(result.get("guard_amount", 0) or 0),
                    utility=1,
                )
            elif effect_type == "cleanse":
                self._record_participant_contribution(
                    character,
                    meaningful=bool(result.get("cleanse_result") or result.get("restore_total")),
                    healing=int(result.get("restore_total", 0) or 0),
                    utility=1 if result.get("cleanse_result") else 0,
                )
            elif effect_type in {"restore", "meal"}:
                self._record_participant_contribution(
                    character,
                    meaningful=bool(result.get("restore_total")),
                    healing=int(result.get("restore_total", 0) or 0),
                )
            else:
                self._record_participant_contribution(character, meaningful=True, utility=1)
        self._add_threat(character, 2)

    def _consume_player_pending_action(self, character):
        pending = dict(self.db.pending_actions or {})
        action = pending.pop(str(character.id), None)
        self.db.pending_actions = pending
        return action or {"kind": "attack", "target": None}

    def _resolve_player_action(self, character, action):
        if action["kind"] == "attack":
            target = self.get_enemy(action["target"]) if action.get("target") else None
            if target and target["hp"] <= 0:
                target = self._default_enemy_target()
            self._execute_basic_attack(character, target=target)
            return
        if action["kind"] == "ability":
            self._execute_ability(character, action)
            return
        if action["kind"] == "flee":
            self._execute_flee(character)
            return
        if action["kind"] == "item":
            self._execute_item(character, action)

    def _advance_player_atb(self, character):
        tick_ms = BraveEncounter._atb_tick_ms(self)
        state = tick_atb_state(self._get_actor_atb_state(character=character), tick_ms=tick_ms)
        self._save_actor_atb_state(state, character=character)
        handler = getattr(self, "_handle_player_atb_state", None)
        if not callable(handler):
            handler = lambda actor: BraveEncounter._handle_player_atb_state(self, actor)
        return handler(character)

    def _handle_player_atb_state(self, character):
        """Consume one player's ready or resolving ATB state."""

        tick_ms = BraveEncounter._atb_tick_ms(self)
        refresher = getattr(self, "_refresh_browser_combat_views", None)
        state = self._get_actor_atb_state(character=character)
        if state.get("phase") == "ready":
            action = self._consume_player_pending_action(character)
            state = start_atb_action(state, action, self._player_action_timing(action), tick_ms=tick_ms)
            if state.get("phase") == "winding":
                pauser = getattr(self, "_pause_non_active_atb_states", None)
                if not callable(pauser):
                    pauser = lambda duration_ms, **kwargs: BraveEncounter._pause_non_active_atb_states(
                        self,
                        duration_ms,
                        **kwargs,
                    )
                pauser(state.get("phase_duration_ms", 0), active_character=character)
                self._save_actor_atb_state(state, character=character)
                if callable(refresher):
                    refresher()
        if state.get("phase") == "resolving":
            setter = getattr(self, "_set_combat_turn_lock", None)
            if not callable(setter):
                setter = lambda *args, **kwargs: BraveEncounter._set_combat_turn_lock(self, *args, **kwargs)
            setter()
            pauser = getattr(self, "_pause_non_active_atb_states", None)
            if not callable(pauser):
                pauser = lambda duration_ms, **kwargs: BraveEncounter._pause_non_active_atb_states(
                    self,
                    duration_ms,
                    **kwargs,
                )
            pauser(COMBAT_TURN_LOCK_MS, active_character=character)
            self._save_actor_atb_state(state, character=character)
            if callable(refresher):
                refresher()
            action = dict(state.get("current_action") or {"kind": "attack", "target": None})
            self._resolve_player_action(character, action)
            recorder = getattr(self, "_record_combat_turn", None)
            if not callable(recorder):
                recorder = lambda: BraveEncounter._record_combat_turn(self)
            recorder()
            state = finish_atb_action(state, tick_ms=tick_ms)
        self._save_actor_atb_state(state, character=character)
        return state

    def _choose_enemy_target(self, enemy=None):
        participants = self.get_active_participants()
        if not participants:
            return None

        visible_participants = [
            participant
            for participant in participants
            if self._get_participant_state(participant).get("stealth_turns", 0) <= 0
        ]
        if visible_participants:
            participants = visible_participants

        if enemy and enemy.get("target_strategy") == "lowest_hp":
            return min(
                participants,
                key=lambda participant: (
                    (participant.db.brave_resources or {}).get("hp", 0),
                    participant.key.lower(),
                ),
            )

        threat = self.db.threat or {}
        highest = max(threat.get(str(participant.id), 0) for participant in participants)
        candidates = [
            participant
            for participant in participants
            if threat.get(str(participant.id), 0) == highest
        ]
        return random.choice(candidates) if candidates else participants[0]

    def _execute_enemy_turn(self, enemy):
        reaction_state = self._enemy_reaction_state(enemy)
        telegraphed = reaction_state["telegraphed"]
        action_label = reaction_state["label"]
        enemy = self._handle_enemy_specials(enemy)
        if enemy.get("hidden_turns", 0) > 0:
            enemy["hidden_turns"] = max(0, enemy["hidden_turns"] - 1)
            self._save_enemy(enemy)
            if enemy["template_key"] == "miretooth":
                self.obj.msg_contents("|rMiretooth ghosts through the reeds somewhere just outside your sightline.|n")
            else:
                self.obj.msg_contents("|rOld Greymaw slips unseen through the brush.|n")
            return

        if enemy["template_key"] == "mossling":
            ally = self._find_wounded_enemy(exclude_id=enemy["id"])
            if ally and ally["hp"] <= (ally["max_hp"] * 3) // 4:
                heal_amount = random.randint(8, 12)
                if self._heal_enemy(enemy, ally, heal_amount):
                    return

            if enemy["template_key"] == "barrow_wisp":
                ally = self._find_wounded_enemy(exclude_id=enemy["id"])
                if ally and ally["hp"] <= (ally["max_hp"] * 3) // 4:
                    heal_amount = random.randint(7, 11)
                    if self._heal_enemy(enemy, ally, heal_amount):
                        self.obj.msg_contents(f"|m{enemy['key']} feeds cold grave-light into {ally['key']}.|n")
                        return

            if enemy["template_key"] == "fen_wisp":
                ally = self._find_wounded_enemy(exclude_id=enemy["id"])
                if ally and ally["hp"] <= (ally["max_hp"] * 3) // 4:
                    heal_amount = random.randint(8, 12)
                    if self._heal_enemy(enemy, ally, heal_amount):
                        self.obj.msg_contents(f"|g{enemy['key']} sheds sick marsh light over {ally['key']}.|n")
                        return

            if enemy["template_key"] == "hollow_wisp":
                ally = self._find_wounded_enemy(exclude_id=enemy["id"])
                if ally and ally["hp"] <= (ally["max_hp"] * 3) // 4:
                    heal_amount = random.randint(9, 13)
                    if self._heal_enemy(enemy, ally, heal_amount):
                        self.obj.msg_contents(f"|y{enemy['key']} spills drowned lamp-light into {ally['key']}.|n")
                        return

        target = self._choose_enemy_target(enemy)
        if not target:
            return

        original_target = target
        original_target_state = self._get_participant_state(target)
        redirected_by = None
        if telegraphed:
            redirect_to = original_target_state.get("reaction_redirect_to")
            redirect_target = self._get_character(redirect_to) if redirect_to else None
            if redirect_target and redirect_target in self.get_active_participants():
                redirected_by = redirect_target
                target = redirect_target

        derived = self._get_effective_derived(target)

        if enemy.get("bound_turns", 0) > 0:
            enemy["bound_turns"] = max(0, enemy["bound_turns"] - 1)
            self._save_enemy(enemy)
            self.obj.msg_contents(f"{enemy['key']} struggles against the frost and loses the moment.")
            return

        damage_bonus = 0
        hit_text = f"{enemy['key']} hits {target.key} for {{damage}} damage."
        if enemy["template_key"] == "forest_wolf" and (target.db.brave_resources or {}).get("hp", 0) <= target.db.brave_derived_stats["max_hp"] // 2:
            damage_bonus += 3
            hit_text = f"{enemy['key']} lunges at {target.key} for {{damage}} damage."

        if enemy["template_key"] == "old_greymaw" and enemy.get("reposition_ready"):
            damage_bonus += 6
            hit_text = f"|rOld Greymaw bursts from the brush and tears into {target.key} for {{damage}} damage!|n"
            enemy["reposition_ready"] = False
            self._save_enemy(enemy)

        if enemy["template_key"] == "tower_archer":
            bandit_support = [
                other
                for other in self.get_active_enemies()
                if other["id"] != enemy["id"] and "bandit" in other.get("tags", [])
            ]
            if bandit_support:
                damage_bonus += 2
                hit_text = f"{enemy['key']} shoots through the melee and drills {target.key} for {{damage}} damage."

        if enemy["template_key"] == "captain_varn_blackreed" and (target.db.brave_resources or {}).get("hp", 0) <= target.db.brave_derived_stats["max_hp"] // 2:
            damage_bonus += 5
            hit_text = f"|rBlackreed spots the weakness and drives into {target.key} for {{damage}} damage!|n"

        if enemy["template_key"] == "grubnak_the_pot_king" and enemy.get("enraged"):
            damage_bonus += 3
            hit_text = f"|rGrubnak slams through the steam and batters {target.key} for {{damage}} damage!|n"

        if enemy["template_key"] == "miretooth" and enemy.get("reposition_ready"):
            damage_bonus += 7
            hit_text = f"|rMiretooth erupts out of the black reeds and mauls {target.key} for {{damage}} damage!|n"
            enemy["reposition_ready"] = False
            self._save_enemy(enemy)

        if enemy["template_key"] == "hollow_lantern" and enemy.get("enraged"):
            damage_bonus += 4
            hit_text = f"|rThe Hollow Lantern floods the chamber with white-black fire and sears {target.key} for {{damage}} damage!|n"

        if not self._roll_hit(enemy["accuracy"], derived["dodge"]):
            self.obj.msg_contents(f"{enemy['key']} misses {target.key}.")
            self._emit_miss_fx(enemy, target)
            return

        if enemy.get("attack_kind") == "spell":
            damage = self._spell_damage(enemy.get("spell_power", enemy["attack_power"]), derived["armor"], bonus=damage_bonus)
        else:
            damage = self._weapon_damage(enemy["attack_power"], derived["armor"], bonus=damage_bonus)
        state = self._get_participant_state(target)
        reaction_prevented = 0
        reaction_source = None
        reaction_label = state.get("reaction_label") or "guard"
        if telegraphed and state.get("reaction_guard", 0):
            reaction_prevented = min(max(0, damage - 1), int(state.get("reaction_guard", 0) or 0))
            reaction_source = self._get_character(state.get("reaction_guard_source")) if state.get("reaction_guard_source") else None
            damage = max(1, damage - reaction_prevented)
        if state.get("guard", 0):
            prevented = min(damage - 1, state["guard"])
            damage = max(1, damage - state["guard"])
            if prevented > 0:
                self._record_participant_contribution(target, mitigation=prevented)
        if telegraphed:
            if redirected_by:
                self.obj.msg_contents(
                    f"|y{redirected_by.key} cuts in front of {enemy['key']}'s {action_label}, dragging it off {original_target.key}.|n"
                )
            if reaction_prevented > 0:
                source_name = reaction_source.key if reaction_source else target.key
                self.obj.msg_contents(
                    f"|y{source_name}'s {reaction_label} blunts {enemy['key']}'s {action_label}.|n"
                )
            elif not redirected_by:
                self.obj.msg_contents(f"|r{enemy['key']}'s {action_label} lands clean.|n")
        resources = dict(target.db.brave_resources or {})
        resources["hp"] = max(0, resources["hp"] - damage)
        target.db.brave_resources = resources
        if telegraphed and reaction_prevented > 0:
            self._record_participant_contribution(reaction_source or target, mitigation=reaction_prevented, utility=1)
        self._record_participant_contribution(target, hits_taken=damage)
        self.obj.msg_contents(hit_text.format(damage=damage))
        emitter = getattr(self, "_emit_combat_fx", None)
        if not callable(emitter):
            emitter = lambda **event: BraveEncounter._emit_combat_fx(self, **event)
        emitter(
            kind="damage",
            source=enemy["key"],
            target=target.key,
            source_ref=_combat_entry_ref(enemy),
            target_ref=_combat_entry_ref(target),
            amount=damage,
            text=str(damage),
            tone="damage",
            impact="damage",
            element=_enemy_damage_type(enemy),
            lunge=True,
        )

        if enemy["template_key"] == "ruk_fence_cutter" and resources["hp"] > 0 and random.randint(1, 100) <= 55:
            self._apply_bleed(target, turns=2, damage=4)
        elif enemy["template_key"] == "old_greymaw" and resources["hp"] > 0:
            self._apply_bleed(target, turns=2, damage=5 if damage_bonus else 4)
        elif enemy["template_key"] == "grave_crow" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
            self._apply_bleed(target, turns=2, damage=3)
        elif enemy["template_key"] == "carrion_hound" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
            self._apply_bleed(target, turns=2, damage=4)
        elif enemy["template_key"] == "cave_spider" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
            self._apply_snare(target, turns=2, accuracy_penalty=6, dodge_penalty=6)
        elif enemy["template_key"] == "briar_imp" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_curse(target, turns=2, armor_penalty=4, message=f"|m{target.key} is wrapped in a briar curse!|n")
        elif enemy["template_key"] == "goblin_hexer" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_curse(target, turns=2, armor_penalty=4, message=f"|m{target.key} is knotted up in goblin hex-thread!|n")
        elif enemy["template_key"] == "cave_bat_swarm" and resources["hp"] > 0 and random.randint(1, 100) <= 40:
            self._apply_bleed(target, turns=2, damage=3)
        elif enemy["template_key"] == "sludge_slime" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_snare(target, turns=2, accuracy_penalty=5, dodge_penalty=5)
        elif enemy["template_key"] in {"restless_shade", "barrow_wisp", "sir_edric_restless"} and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_curse(target, turns=2, armor_penalty=4, message=f"|m{target.key} shudders under a grave-cold curse!|n")
        elif enemy["template_key"] in {"mag_clamp_drone", "foreman_coilback"} and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_snare(target, turns=2, accuracy_penalty=5, dodge_penalty=5)
        elif enemy["template_key"] == "grubnak_the_pot_king" and resources["hp"] > 0 and random.randint(1, 100) <= 55:
            self._apply_snare(target, turns=2, accuracy_penalty=4, dodge_penalty=4)
        elif enemy["template_key"] == "bog_creeper" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_snare(target, turns=2, accuracy_penalty=6, dodge_penalty=6)
        elif enemy["template_key"] == "fen_wisp" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_curse(target, turns=2, armor_penalty=5, message=f"|m{target.key} shudders under a marsh-light curse!|n")
        elif enemy["template_key"] == "rot_crow" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
            self._apply_bleed(target, turns=2, damage=4)
        elif enemy["template_key"] == "mire_hound" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
            self._apply_poison(target, turns=2, damage=4, accuracy_penalty=5, message=f"|g{target.key} reels under a swamp-sick bite!|n")
        elif enemy["template_key"] == "miretooth" and resources["hp"] > 0 and random.randint(1, 100) <= 60:
            self._apply_poison(target, turns=3, damage=5, accuracy_penalty=6, message=f"|gMiretooth's bite leaves black fen venom burning through {target.key}!|n")
        elif enemy["template_key"] == "drowned_warder" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
            self._apply_snare(target, turns=2, accuracy_penalty=5, dodge_penalty=5)
        elif enemy["template_key"] == "silt_stalker" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
            self._apply_bleed(target, turns=2, damage=4)
        elif enemy["template_key"] == "hollow_wisp" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
            self._apply_curse(target, turns=2, armor_penalty=5, message=f"|m{target.key} shudders under a hollow-light curse!|n")
        elif enemy["template_key"] == "hollow_lantern" and resources["hp"] > 0 and random.randint(1, 100) <= 60:
            self._apply_curse(target, turns=3, armor_penalty=6, message=f"|mThe Hollow Lantern brands {target.key} in wrong light!|n")

        if resources["hp"] <= 0:
            self._defeat_character(target)

    def _advance_enemy_atb(self, enemy):
        tick_ms = BraveEncounter._atb_tick_ms(self)
        state = tick_atb_state(self._get_actor_atb_state(enemy=enemy), tick_ms=tick_ms)
        self._save_actor_atb_state(state, enemy=enemy)
        handler = getattr(self, "_handle_enemy_atb_state", None)
        if not callable(handler):
            handler = lambda actor: BraveEncounter._handle_enemy_atb_state(self, actor)
        return handler(enemy)

    def _handle_enemy_atb_state(self, enemy):
        """Consume one enemy's ready or resolving ATB state."""

        tick_ms = BraveEncounter._atb_tick_ms(self)
        refresher = getattr(self, "_refresh_browser_combat_views", None)
        state = self._get_actor_atb_state(enemy=enemy)
        if state.get("phase") == "ready":
            action = {
                "kind": "enemy_attack",
                "enemy_id": enemy["id"],
                "label": self._enemy_action_label(enemy),
            }
            state = start_atb_action(
                state,
                action,
                self._enemy_action_timing(enemy),
                tick_ms=tick_ms,
            )
            if state.get("phase") == "winding" and dict(state.get("timing") or {}).get("telegraph"):
                pauser = getattr(self, "_pause_non_active_atb_states", None)
                if not callable(pauser):
                    pauser = lambda duration_ms, **kwargs: BraveEncounter._pause_non_active_atb_states(
                        self,
                        duration_ms,
                        **kwargs,
                    )
                pauser(state.get("phase_duration_ms", 0), active_enemy=enemy)
                self._save_actor_atb_state(state, enemy=enemy)
                if callable(refresher):
                    refresher()
                self.obj.msg_contents(self._enemy_telegraph_message(enemy))
            elif state.get("phase") == "winding":
                pauser = getattr(self, "_pause_non_active_atb_states", None)
                if not callable(pauser):
                    pauser = lambda duration_ms, **kwargs: BraveEncounter._pause_non_active_atb_states(
                        self,
                        duration_ms,
                        **kwargs,
                    )
                pauser(state.get("phase_duration_ms", 0), active_enemy=enemy)
                self._save_actor_atb_state(state, enemy=enemy)
                if callable(refresher):
                    refresher()
        if state.get("phase") == "resolving":
            setter = getattr(self, "_set_combat_turn_lock", None)
            if not callable(setter):
                setter = lambda *args, **kwargs: BraveEncounter._set_combat_turn_lock(self, *args, **kwargs)
            setter()
            pauser = getattr(self, "_pause_non_active_atb_states", None)
            if not callable(pauser):
                pauser = lambda duration_ms, **kwargs: BraveEncounter._pause_non_active_atb_states(
                    self,
                    duration_ms,
                    **kwargs,
                )
            pauser(COMBAT_TURN_LOCK_MS, active_enemy=enemy)
            self._save_actor_atb_state(state, enemy=enemy)
            if callable(refresher):
                refresher()
            self._execute_enemy_turn(enemy)
            recorder = getattr(self, "_record_combat_turn", None)
            if not callable(recorder):
                recorder = lambda: BraveEncounter._record_combat_turn(self)
            recorder()
            state = finish_atb_action(state, tick_ms=tick_ms)
        self._save_actor_atb_state(state, enemy=enemy)
        return state

    def _tick_all_atb_states(self, participants, enemies):
        """Advance ATB timers for everyone without resolving more than one turn."""

        tick_ms = BraveEncounter._atb_tick_ms(self)
        for participant in participants:
            raw_state = self._get_actor_atb_state(character=participant)
            state_start_ms = int((raw_state or {}).get("phase_started_at_ms", 0) or 0)
            if state_start_ms <= 0:
                state_start_ms = int(round(time.time() * 1000)) - tick_ms
            state = advance_atb_state_by_ms(
                raw_state,
                tick_ms,
                tick_ms=tick_ms,
                now_ms=state_start_ms,
            )
            self._save_actor_atb_state(state, character=participant)
        for enemy in enemies:
            raw_state = self._get_actor_atb_state(enemy=enemy)
            state_start_ms = int((raw_state or {}).get("phase_started_at_ms", 0) or 0)
            if state_start_ms <= 0:
                state_start_ms = int(round(time.time() * 1000)) - tick_ms
            state = advance_atb_state_by_ms(
                raw_state,
                tick_ms,
                tick_ms=tick_ms,
                now_ms=state_start_ms,
            )
            self._save_actor_atb_state(state, enemy=enemy)

    def _advance_idle_atb_states(self, participants, enemies):
        """Advance the field only until the next actor becomes ready."""

        tick_ms = BraveEncounter._atb_tick_ms(self)
        earliest_ready_ms = None

        for participant in participants:
            ready_ms = atb_state_ms_until_ready(self._get_actor_atb_state(character=participant), tick_ms=tick_ms)
            if earliest_ready_ms is None or ready_ms < earliest_ready_ms:
                earliest_ready_ms = ready_ms
        for enemy in enemies:
            ready_ms = atb_state_ms_until_ready(self._get_actor_atb_state(enemy=enemy), tick_ms=tick_ms)
            if earliest_ready_ms is None or ready_ms < earliest_ready_ms:
                earliest_ready_ms = ready_ms

        if earliest_ready_ms is None or earliest_ready_ms <= 0:
            return 0

        advance_ms = min(tick_ms, earliest_ready_ms)
        for participant in participants:
            raw_state = self._get_actor_atb_state(character=participant)
            state_start_ms = int((raw_state or {}).get("phase_started_at_ms", 0) or 0)
            if state_start_ms <= 0:
                state_start_ms = int(round(time.time() * 1000)) - advance_ms
            state = advance_atb_state_by_ms(
                raw_state,
                advance_ms,
                tick_ms=tick_ms,
                now_ms=state_start_ms,
            )
            self._save_actor_atb_state(state, character=participant)
        for enemy in enemies:
            raw_state = self._get_actor_atb_state(enemy=enemy)
            state_start_ms = int((raw_state or {}).get("phase_started_at_ms", 0) or 0)
            if state_start_ms <= 0:
                state_start_ms = int(round(time.time() * 1000)) - advance_ms
            state = advance_atb_state_by_ms(
                raw_state,
                advance_ms,
                tick_ms=tick_ms,
                now_ms=state_start_ms,
            )
            self._save_actor_atb_state(state, enemy=enemy)
        return advance_ms

    def _next_atb_actor(self, participants, enemies, *, phases=None):
        """Return the next actor allowed to take a turn this repeat."""

        phase_order = {"resolving": 0, "winding": 1, "ready": 2}
        allowed_phases = set(phases or ("ready", "resolving"))
        candidates = []
        for participant in participants:
            state = self._get_actor_atb_state(character=participant)
            phase = state.get("phase")
            if phase not in allowed_phases:
                continue
            candidates.append(
                {
                    "kind": "participant",
                    "actor": participant,
                    "phase": phase,
                    "started_at": int(state.get("phase_started_at_ms", 0) or 0),
                    "fill_rate": int(state.get("fill_rate", 0) or 0),
                    "sort_id": f"p:{participant.id}",
                }
            )
        for enemy in enemies:
            state = self._get_actor_atb_state(enemy=enemy)
            phase = state.get("phase")
            if phase not in allowed_phases:
                continue
            candidates.append(
                {
                    "kind": "enemy",
                    "actor": enemy,
                    "phase": phase,
                    "started_at": int(state.get("phase_started_at_ms", 0) or 0),
                    "fill_rate": int(state.get("fill_rate", 0) or 0),
                    "sort_id": f"e:{enemy['id']}",
                }
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda entry: (
                phase_order.get(entry["phase"], 99),
                entry["started_at"],
                -entry["fill_rate"],
                0 if entry["kind"] == "participant" else 1,
                entry["sort_id"],
            )
        )
        return candidates[0]

    def _active_atb_actor(self, participants, enemies):
        """Return the actor whose windup or resolution currently freezes the field."""

        return BraveEncounter._next_atb_actor(self, participants, enemies, phases=("resolving", "winding"))

    def _clear_turn_states(self):
        states = dict(self.db.participant_states or {})
        for participant_key, state in states.items():
            state["guard"] = 0
            self._clear_reaction_state(state)
            if state.get("feint_turns", 0) > 0:
                state["feint_turns"] = max(0, state["feint_turns"] - 1)
                if state["feint_turns"] <= 0:
                    state["feint_accuracy_bonus"] = 0
                    state["feint_dodge_bonus"] = 0
            if state.get("stealth_turns", 0) > 0:
                state["stealth_turns"] = max(0, state["stealth_turns"] - 1)
        self.db.participant_states = states

        enemies = []
        for enemy in self.db.enemies or []:
            enemy["marked_turns"] = max(0, enemy["marked_turns"] - 1)
            enemies.append(enemy)
        self.db.enemies = enemies

    def _reward_victory(self):
        from world.browser_panels import send_webclient_event
        from world.browser_views import build_combat_victory_view

        scaling = self._get_scaling_profile()
        xp_total = max(1, int(round(sum(enemy["xp"] for enemy in self.db.enemies or []) * scaling["xp"])))
        active_participants = self.get_active_participants()
        participants = self.get_registered_participants()
        if not participants:
            return []

        eligible = [participant for participant in participants if self._participant_reward_eligible(participant)]
        top_impact = max((self._participant_impact_score(participant) for participant in eligible), default=0)
        max_turn = max(1, BraveEncounter._combat_turn_count(self) or 1)
        weighted_entries = [
            (participant.id, self._participant_reward_weight(participant, max_turn=max_turn, top_impact=top_impact))
            for participant in eligible
        ]
        xp_shares = self._allocate_weighted_pool(xp_total, weighted_entries, minimum=1)

        reward_bundles = [roll_enemy_rewards(enemy) for enemy in (self.db.enemies or [])]
        silver_total = sum(bundle["silver"] for bundle in reward_bundles)
        silver_shares = self._allocate_weighted_pool(silver_total, weighted_entries)
        reward_items = []
        for bundle in reward_bundles:
            reward_items.extend(bundle["items"])
        item_shares = self._distribute_reward_items(reward_items, weighted_entries)

        for participant in participants:
            remote_victory = participant not in active_participants
            participant_xp = int(xp_shares.get(participant.id, 0))
            participant_silver = int(silver_shares.get(participant.id, 0))
            reward_eligible = participant in eligible
            if remote_victory:
                if reward_eligible:
                    participant.msg("|gYour family carries the fight. The victory still holds for you.|n")
                else:
                    participant.msg("|yThe fight ends without you earning a share of the victory.|n")
            else:
                if reward_eligible:
                    participant.msg(f"|gVictory.|n You gain |w{participant_xp}|n XP.")
                else:
                    participant.msg("|yVictory passes you by before you can claim a share.|n")
            progress_messages = []
            if participant_xp:
                for message in participant.grant_xp(participant_xp):
                    participant.msg(message)
                    progress_messages.append(strip_ansi(message))
            if reward_eligible:
                record_encounter_victory(participant, self.obj)

            if participant_silver:
                participant.db.brave_silver = (participant.db.brave_silver or 0) + participant_silver

            merged_items = item_shares.get(participant.id, []) if reward_eligible else []
            for template_id, quantity in merged_items:
                participant.add_item_to_inventory(template_id, quantity)

            reward_summary = format_reward_summary(
                {"silver": participant_silver, "items": merged_items}
            )
            if reward_summary:
                participant.msg(f"You recover {reward_summary}.")

            quest_updates = [strip_ansi(message) for message in pop_recent_quest_updates(participant)]
            if not reward_eligible:
                progress_messages.append("No reward share earned.")

            send_webclient_event(
                participant,
                brave_view=build_combat_victory_view(
                    self,
                    participant,
                    xp_total=participant_xp,
                    reward_silver=participant_silver,
                    reward_items=merged_items,
                    progress_messages=quest_updates + progress_messages,
                    remote=remote_victory,
                    party_size=len(participants),
                ),
            )
            participant.clear_chapel_blessing()

        return participants

    def _finish_victory_sequence(self, room_message, *, exclude_rewarded=True):
        """Deliver victory rewards and stop after combat FX have played."""

        if hasattr(self, "ndb"):
            self.ndb.brave_victory_pending = False
        rewarded = self._reward_victory()
        if self.obj and room_message:
            kwargs = {"exclude": rewarded} if exclude_rewarded else {}
            self.obj.msg_contents(room_message, **kwargs)
        self.stop()

    def _schedule_victory_sequence(self, room_message, *, exclude_rewarded=True):
        """Wait for final defeat FX before swapping away from combat."""

        if getattr(getattr(self, "ndb", None), "brave_victory_pending", False):
            return
        if hasattr(self, "ndb"):
            self.ndb.brave_victory_pending = True
        # Push one last combat-state refresh with the defeated enemy removed so
        # the browser can play the same removal animation used for non-final kills.
        self._refresh_browser_combat_views()
        delay(
            COMBAT_FINISH_FX_DELAY,
            self._finish_victory_sequence,
            room_message,
            exclude_rewarded=exclude_rewarded,
            persistent=False,
        )

    def at_repeat(self):
        active_participants = self.get_active_participants()
        active_enemies = self.get_active_enemies()

        now_ms = int(round(time.time() * 1000))
        turn_locked = getattr(self, "_combat_turn_locked", None)
        if not callable(turn_locked):
            turn_locked = lambda **kwargs: BraveEncounter._combat_turn_locked(self, **kwargs)
        if turn_locked(now_ms=now_ms):
            return

        if not active_participants:
            self.obj.msg_contents("|rThe fight breaks wrong, and the danger keeps the road.|n")
            self.stop()
            return
        if not active_enemies:
            self._schedule_victory_sequence("|gThe last of them falls. The way is clear for now.|n")
            return

        self._apply_participant_effects()
        if not self.get_active_participants():
            self.obj.msg_contents("|rThe line breaks and the party is driven back toward town.|n")
            self.stop()
            return
        self._apply_enemy_effects()
        if not self.get_active_enemies():
            self._schedule_victory_sequence("|gThe last of them falls. The way is clear for now.|n")
            return

        active_participants = self.get_active_participants()
        active_enemies = self.get_active_enemies()
        active_actor_getter = getattr(self, "_active_atb_actor", None)
        if not callable(active_actor_getter):
            active_actor_getter = lambda participants, enemies: BraveEncounter._active_atb_actor(self, participants, enemies)
        active_actor = active_actor_getter(active_participants, active_enemies)
        actor_activity = bool(active_actor)
        next_actor_getter = getattr(self, "_next_atb_actor", None)
        if not callable(next_actor_getter):
            next_actor_getter = lambda participants, enemies: BraveEncounter._next_atb_actor(self, participants, enemies)
        if active_actor:
            tick_now_ms = int(round(time.time() * 1000))
            if active_actor["kind"] == "participant":
                state = tick_atb_state(
                    self._get_actor_atb_state(character=active_actor["actor"]),
                    tick_ms=BraveEncounter._atb_tick_ms(self),
                    now_ms=tick_now_ms,
                )
                self._save_actor_atb_state(state, character=active_actor["actor"])
                self._handle_player_atb_state(active_actor["actor"])
            else:
                state = tick_atb_state(
                    self._get_actor_atb_state(enemy=active_actor["actor"]),
                    tick_ms=BraveEncounter._atb_tick_ms(self),
                    now_ms=tick_now_ms,
                )
                self._save_actor_atb_state(state, enemy=active_actor["actor"])
                self._handle_enemy_atb_state(active_actor["actor"])
        else:
            next_actor = next_actor_getter(active_participants, active_enemies)
            if not next_actor:
                advance_idle_states = getattr(self, "_advance_idle_atb_states", None)
                if not callable(advance_idle_states):
                    advance_idle_states = lambda participants, enemies: BraveEncounter._advance_idle_atb_states(
                        self,
                        participants,
                        enemies,
                    )
                advance_idle_states(active_participants, active_enemies)
                next_actor = next_actor_getter(active_participants, active_enemies)
        next_actor = None if active_actor else next_actor
        if next_actor:
            actor_activity = True
            if next_actor["kind"] == "participant":
                self._handle_player_atb_state(next_actor["actor"])
            else:
                self._handle_enemy_atb_state(next_actor["actor"])
        if not self.get_active_participants():
            self.obj.msg_contents("The fight ends with the road still dangerous.")
            self.stop()
            return
        if not self.get_active_enemies():
            self._schedule_victory_sequence("|gThe encounter is over. The road is clear for now.|n")
            return
        if not self.get_active_participants():
            self.obj.msg_contents("|rThe party is driven back toward town.|n")
            self.stop()
            return

        if not actor_activity:
            return

        clear_turn_states = getattr(self, "_clear_turn_states", None)
        if not callable(clear_turn_states):
            clear_turn_states = lambda: BraveEncounter._clear_turn_states(self)
        clear_turn_states()
        self._refresh_browser_combat_views()
