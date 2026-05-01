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

import math
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
    create_atb_state,
    finish_atb_action,
    get_ability_atb_profile,
    get_item_atb_profile,
    normalize_atb_profile,
    start_atb_action,
    tick_atb_state,
)
from world.combat_execution import execute_combat_ability
from world.combat_actor_utils import (
    _ally_actor_id,
    _combat_entry_ref,
    _combat_target_id,
    _combat_target_name,
    _enemy_damage_type,
    _is_companion_actor,
)
from world.content import get_content_registry
from world.enemy_icons import get_enemy_icon_name
from world.genders import get_brave_pronoun, resolve_brave_gender
from world.roaming import (
    advance_roaming_parties,
    build_roaming_room_preview,
    mark_roaming_parties_engaged,
    release_roaming_parties,
    room_uses_roaming_threats,
)

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
from world.ranger_companions import get_companion
from world.resonance import get_ability_display_name, get_resource_label, resolve_ability_query
from world.race_perks import (
    adjust_effect_damage,
    adjust_effect_penalty,
    adjust_effect_turns,
    get_atb_fill_rate_bonus,
    get_flee_chance_bonus,
    get_interrupt_recovery_bonus,
    get_wounded_atb_fill_rate_bonus,
    get_wounded_damage_bonus,
)
from world.rewards import format_reward_summary, merge_reward_entries, roll_enemy_rewards
from world.tutorial import get_tutorial_defeat_room, is_tutorial_solo_combat_room, record_encounter_victory

COMBAT_BOSS_CREDIT_RATIO = (2, 3)
COMBAT_ACTION_SCORE_CAP = 3.0
COMBAT_UTILITY_WEIGHT = 6
COMBAT_HITS_TAKEN_WEIGHT = 2
COMBAT_MAX_PLAYER_CHARACTERS = 4
COMBAT_MAX_ENEMIES = 4
COMBAT_MAX_BOSS_ENEMIES = 3
# The browser serializes lunge/impact before the 860ms defeat fall. Leave
# headroom for network/render latency plus a brief beat before victory.
COMBAT_FINISH_FX_DELAY = 1.6
COMBAT_DEFEAT_REFRESH_DELAY = 1.3
COMBAT_DEFEAT_SILVER_LOSS = 5


def _normalize_token(value):
    """Normalize free-text tokens for matching."""

    return "".join(char for char in (value or "").lower() if char.isalnum())


def _base_form_verb(verb):
    """Return a best-effort base form for a social verb."""

    verb = str(verb or "").strip().lower()
    if not verb:
        return ""
    if verb.endswith("ies") and len(verb) > 3:
        return verb[:-3] + "y"
    if verb.endswith("es"):
        stem = verb[:-2]
        if stem.endswith(("s", "x", "z", "ch", "sh", "o")):
            return stem
    if verb.endswith("s") and len(verb) > 1:
        return verb[:-1]
    return verb


def _ability_display_name(character, ability_key):
    """Return the resonance-aware display name for an ability key."""

    ability = ABILITY_LIBRARY.get(ability_key) or PASSIVE_ABILITY_BONUSES.get(ability_key)
    if not ability:
        return ability_key.replace("_", " ").title()
    return get_ability_display_name(ability["name"], character)


def _enemy_gender(enemy):
    """Resolve the authored gender for one enemy mapping."""

    if not isinstance(enemy, Mapping):
        return resolve_brave_gender(enemy)
    template = ENEMY_TEMPLATES.get(enemy.get("template_key")) or {}
    return resolve_brave_gender(
        enemy.get("gender") or enemy.get("brave_gender") or template.get("gender")
    )


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


def _limit_encounter_enemies(template_keys):
    """Clamp encounter enemy templates to the supported combat presentation cap."""

    normalized = [str(template_key or "").strip() for template_key in (template_keys or []) if str(template_key or "").strip()]
    if len(normalized) <= COMBAT_MAX_ENEMIES:
        return normalized

    bosses = []
    others = []
    for template_key in normalized:
        tags = set((ENEMY_TEMPLATES.get(template_key) or {}).get("tags", []) or [])
        if "boss" in tags:
            bosses.append(template_key)
        else:
            others.append(template_key)

    if bosses:
        return bosses[:1] + others[: max(0, COMBAT_MAX_BOSS_ENEMIES - 1)]
    return normalized[:COMBAT_MAX_ENEMIES]


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

TEMPERAMENT_PRIORITY = {
    "relentless": 3,
    "aggressive": 2,
    "territorial": 1,
    "wary": 0,
}


def _enemy_display_name(template_key, template=None):
    """Return a stable display name for a template."""

    template = template or ENEMY_TEMPLATES.get(template_key, {})
    name = str(template.get("short_name") or template.get("name") or template_key.replace("_", " ").title()).strip()
    return name or "Hostile"


def _pluralize_display_name(name):
    """Return a simple plural form for a display name."""

    words = str(name or "").split()
    if not words:
        return "Hostiles"
    tail = words[-1]
    if tail.endswith("y") and len(tail) > 1 and tail[-2] not in "aeiou":
        tail = tail[:-1] + "ies"
    elif tail.endswith(("s", "x", "z", "ch", "sh")):
        tail = tail + "es"
    else:
        tail = tail + "s"
    return " ".join([*words[:-1], tail])


def _format_enemy_count_name(template_key, count, template=None):
    """Return a count-aware enemy name for compact party summaries."""

    name = _enemy_display_name(template_key, template)
    if int(count or 0) <= 1:
        return name
    return f"{int(count)} {_pluralize_display_name(name)}"


def _enemy_role_label(template):
    """Return a loose role label derived from enemy tags."""

    tags = {str(tag).lower() for tag in (template or {}).get("tags", [])}
    for tag in ("boss", "brute", "support", "caster", "archer", "ranged", "skirmisher", "raider", "soldier", "beast", "wolf", "hound", "wisp", "shade"):
        if tag in tags:
            return tag
    return "foe"


def _build_enemy_party_summary(encounter_data):
    """Return a structured summary of the exact enemy makeup."""

    enemies = list(encounter_data.get("enemies") or [])
    counts = {}
    ordered_keys = []
    for template_key in enemies:
        if template_key not in counts:
            ordered_keys.append(template_key)
        counts[template_key] = counts.get(template_key, 0) + 1

    members = []
    composition_parts = []
    dominant = None
    for template_key in ordered_keys:
        template = ENEMY_TEMPLATES.get(template_key) or {}
        count = counts[template_key]
        display_name = _enemy_display_name(template_key, template)
        temperament = get_enemy_temperament(template_key, template)
        temperament_label = get_enemy_temperament_label(temperament)
        rank = get_enemy_rank(template_key, template)
        member = {
            "template_key": template_key,
            "name": display_name,
            "count": count,
            "role": _enemy_role_label(template),
            "temperament": temperament,
            "temperament_label": temperament_label,
            "rank": rank,
        }
        members.append(member)
        composition_parts.append(_format_enemy_count_name(template_key, count, template))
        candidate = (
            int(count or 0),
            int(rank or 1),
            TEMPERAMENT_PRIORITY.get(temperament, 0),
            display_name.lower(),
        )
        if dominant is None or candidate > dominant[0]:
            dominant = (candidate, member)

    if not composition_parts:
        composition = "hostiles"
    elif len(composition_parts) == 1:
        composition = composition_parts[0]
    elif len(composition_parts) == 2:
        composition = " + ".join(composition_parts)
    else:
        composition = ", ".join(composition_parts)

    dominant_member = dominant[1] if dominant else None
    return {
        "count": len(enemies),
        "members": members,
        "composition": composition,
        "dominant_temperament": dominant_member["temperament"] if dominant_member else "aggressive",
        "temperament_label": dominant_member["temperament_label"] if dominant_member else "Aggressive",
        "lead_name": dominant_member["name"] if dominant_member else "Hostile Party",
    }


def _generated_party_name(summary, encounter_title=None):
    """Return a fallback tactical party name from the party summary."""

    members = list(summary.get("members") or [])
    if not members:
        encounter_title = str(encounter_title or "").strip()
        return encounter_title or "Hostile Party"

    lead = max(
        members,
        key=lambda member: (
            int(member.get("rank", 1) or 1),
            int(member.get("count", 1) or 1),
            str(member.get("name") or "").lower(),
        ),
    )
    lead_name = str(lead.get("name") or "Hostile").strip() or "Hostile"
    if len(members) == 1:
        return lead_name
    if len(lead_name) > 22:
        lead_name = lead_name.split()[0]
    return f"{lead_name} Retinue"


ROOM_THREAT_SKULL_DELTA = 3


ROOM_THREAT_RESPAWN_DELAY = 45

DEFAULT_ATTACK_ATB_PROFILE = normalize_atb_profile({"windup_ticks": 0, "recovery_ticks": 1, "interruptible": False})
DEFAULT_FLEE_ATB_PROFILE = normalize_atb_profile({"windup_ticks": 1, "recovery_ticks": 0, "telegraph": True})
DEFAULT_ENEMY_ATTACK_ATB_PROFILE = normalize_atb_profile({"windup_ticks": 0, "recovery_ticks": 1, "interruptible": False})


PARTY_SCALING = {
    1: {"label": "Solo", "hp": 0.88, "power": 0.88, "accuracy": -3, "xp": 1.0},
    2: {"label": "Duo", "hp": 0.94, "power": 0.95, "accuracy": -1, "xp": 1.0},
    3: {"label": "Trio", "hp": 1.08, "power": 1.02, "accuracy": 1, "xp": 1.03},
    4: {"label": "Full Party", "hp": 1.22, "power": 1.1, "accuracy": 3, "xp": 1.08},
}

DROWNED_WEIR_SOLO_SCALING = {"hp": 0.9, "power": 0.82, "accuracy": -4}
SOLO_ENCOUNTER_SCALING_OVERRIDES = {
    "high_walk_claim": {"hp": 0.92, "power": 0.86, "accuracy": -2},
    "the_hollow_lantern": {"hp": 0.62, "power": 0.55, "accuracy": -10},
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

        summary = _build_enemy_party_summary(encounter_data)
        encounter_title = str(encounter_data.get("title") or "").strip()
        encounter_intro = str(encounter_data.get("intro") or "").strip()
        party_name = str(encounter_data.get("party_name") or "").strip()
        display_name = party_name or (encounter_title if encounter_title and len(encounter_title) <= 32 else None) or _generated_party_name(summary, encounter_title=encounter_title)

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
                    "icon": get_enemy_icon_name(template_key, template),
                }
            )

        party_icon = None
        if enemies:
            lead_enemy = max(
                enemies,
                key=lambda enemy: (
                    int(enemy.get("rank", 1) or 1),
                    str(enemy.get("key", "")).lower(),
                ),
            )
            party_icon = get_enemy_icon_name(lead_enemy.get("template_key"), ENEMY_TEMPLATES.get(lead_enemy.get("template_key"), {}))

        return {
            "room_id": getattr(room.db, "brave_room_id", None),
            "encounter_data": encounter_data,
            "encounter_key": encounter_data["key"],
            "threat_query": str(encounter_data.get("key") or "").strip(),
            "encounter_title": encounter_title,
            "encounter_intro": encounter_intro,
            "party_name": party_name,
            "display_name": display_name,
            "composition": summary["composition"],
            "count": summary["count"],
            "members": summary["members"],
            "temperament": summary["dominant_temperament"],
            "temperament_label": summary["temperament_label"],
            "icon": party_icon,
            "source": str(encounter_data.get("source") or "room"),
            "engagement_scope": str(encounter_data.get("engagement_scope") or "room"),
            "enemies": enemies,
        }


    @classmethod
    def _room_has_static_boss_encounter(cls, room_id):
        """Return whether this room's authored static encounter contains a boss."""

        if not room_id:
            return False

        for encounter_data in ROOM_ENCOUNTERS.get(room_id, []):
            for template_key in encounter_data.get("enemies", []):
                template = ENEMY_TEMPLATES.get(template_key) or {}
                if "boss" in set(template.get("tags", [])):
                    return True
        return False

    @classmethod
    def get_room_threat_preview(cls, room):
        """Return the current visible room-threat preview, creating one if needed."""

        if not room or getattr(room.db, "brave_safe", False):
            return None

        advance_roaming_parties()

        encounter = cls.get_for_room(room)
        if encounter:
            active_enemies = list(encounter.get_active_enemies())
            encounter_data = {
                "key": encounter.db.encounter_key,
                "title": encounter.db.encounter_title,
                "intro": encounter.db.encounter_intro,
                "enemies": [enemy["template_key"] for enemy in active_enemies],
            }
            preview = cls._build_preview_data(room, encounter_data)
            preview["enemies"] = [
                {
                    "id": enemy["id"],
                    "template_key": enemy["template_key"],
                    "key": enemy["key"],
                    "desc": ENEMY_TEMPLATES[enemy["template_key"]].get("desc", ""),
                    "tags": list(ENEMY_TEMPLATES[enemy["template_key"]].get("tags", [])),
                    "temperament": get_enemy_temperament(enemy["template_key"]),
                    "temperament_label": get_enemy_temperament_label(get_enemy_temperament(enemy["template_key"])),
                    "rank": get_enemy_rank(enemy["template_key"]),
                    "icon": get_enemy_icon_name(enemy["template_key"], ENEMY_TEMPLATES.get(enemy["template_key"], {})),
                    "engaged": True,
                }
                for enemy in active_enemies
            ]
            if active_enemies:
                lead_enemy = max(
                    active_enemies,
                    key=lambda enemy: (
                        int(get_enemy_rank(enemy["template_key"]) or 1),
                        str(enemy.get("key", "")).lower(),
                    ),
                )
                preview["icon"] = get_enemy_icon_name(lead_enemy["template_key"], ENEMY_TEMPLATES.get(lead_enemy["template_key"], {}))
            preview["engaged"] = True
            return preview

        roaming_preview = build_roaming_room_preview(room)
        if roaming_preview:
            return roaming_preview
        room_id = getattr(room.db, "brave_room_id", None)
        if room_uses_roaming_threats(room) and not cls._room_has_static_boss_encounter(room_id):
            return None

        ready_at = getattr(room.ndb, "brave_room_threat_ready_at", 0) or 0
        if ready_at and ready_at > time.time():
            return None

        preview = getattr(room.ndb, "brave_room_threat_preview", None)
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

        title = str(preview.get("display_name") or preview.get("party_name") or "").strip()
        if title:
            return title

        encounter_title = str(preview.get("encounter_title") or "").strip()
        if encounter_title and len(encounter_title) <= 32:
            return encounter_title

        summary = preview.get("members")
        if summary:
            return _generated_party_name({"members": list(summary)}, encounter_title=encounter_title)

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
        display_name = cls._compact_encounter_title(preview)
        composition = str(preview.get("composition") or "hostiles").strip() or "hostiles"
        count = int(preview.get("count") or len(enemies) or 0)
        source = str(preview.get("source") or "room").strip() or "room"
        engagement_scope = str(preview.get("engagement_scope") or "room").strip() or "room"

        overpowering = any(int(enemy.get("rank", 1) or 1) >= viewer_level + ROOM_THREAT_SKULL_DELTA for enemy in enemies)
        tooltip_bits = [f"{count} hostiles", f"{lead_threat.lower()} threat", composition]
        intro = str(preview.get("encounter_intro") or "").strip()
        if intro:
            tooltip_bits.append(intro)
        if source == "roaming":
            tooltip_bits.append("roaming party")
        engaged = any(bool(enemy.get("engaged")) for enemy in enemies)
        if engaged:
            tooltip_bits.append("fight underway")

        temperament_label = str(preview.get("temperament_label") or "").strip()
        if not temperament_label:
            temperament_label = max(
                (str(enemy.get("temperament_label") or "Aggressive") for enemy in enemies),
                key=lambda label: (label == "Relentless", label == "Aggressive", label),
            )

        return {
            "key": display_name,
            "display_name": display_name,
            "party_name": str(preview.get("party_name") or display_name).strip() or display_name,
            "threat_query": str(preview.get("threat_query") or preview.get("encounter_key") or "").strip(),
            "composition": composition,
            "count": count,
            "members": list(preview.get("members") or []),
            "detail": f"Engaged · {composition}" if engaged else composition,
            "badge": str(count),
            "tooltip": " · ".join(bit for bit in tooltip_bits if bit),
            "command": (
                f"fight {str(preview.get('threat_query') or preview.get('encounter_key') or '').strip()}".strip()
                if str(preview.get("threat_query") or preview.get("encounter_key") or "").strip()
                else "fight"
            ),
            "engaged": engaged,
            "marker_icon": "swords" if engaged else ("skull" if overpowering else None),
            "icon": preview.get("icon") or "monster-skull",
            "temperament_label": temperament_label,
            "threat_label": lead_threat,
            "intro": intro,
            "source": source,
            "engagement_scope": engagement_scope,
        }


    @classmethod
    def _build_roaming_room_threat_cards(cls, room, preview, viewer=None):
        """Build one compact threat card for each roaming party in the room."""

        cards = []
        for party in preview.get("roaming_parties") or []:
            encounter_data = dict(party.get("encounter") or {})
            encounter_data["key"] = party.get("key") or encounter_data.get("key") or "roaming_party"
            encounter_data.setdefault("title", encounter_data.get("key") or "Hostile Party")
            encounter_data.setdefault("intro", "")
            encounter_data.setdefault("enemies", list(encounter_data.get("enemies") or []))
            if not encounter_data["enemies"]:
                continue

            party_preview = cls._build_preview_data(room, encounter_data)
            party_preview["source"] = "roaming"
            party_preview["engagement_scope"] = "room"
            party_preview["roaming_party_keys"] = [party.get("key")] if party.get("key") else []
            card = cls._build_room_threat_card(party_preview, viewer=viewer)
            if card:
                cards.append(card)
        return cards


    @classmethod
    def get_visible_room_threats(cls, room, viewer=None):
        """Return visible hostile threats for room rendering and threat commands."""

        preview = cls.get_room_threat_preview(room)
        if not preview:
            return []

        if preview.get("roaming_parties"):
            return cls._build_roaming_room_threat_cards(room, preview, viewer=viewer)

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
    def get_room_threat_options(cls, room):
        """Return concrete selectable room-threat previews for engagement commands."""

        preview = cls.get_room_threat_preview(room)
        if not preview:
            return []

        if preview.get("roaming_parties"):
            options = []
            for party in preview.get("roaming_parties") or []:
                encounter_data = dict(party.get("encounter") or {})
                encounter_data.setdefault("key", party.get("key") or "roaming_party")
                encounter_data.setdefault("title", encounter_data.get("key") or "Hostile Party")
                encounter_data.setdefault("intro", "")
                encounter_data.setdefault("enemies", list(encounter_data.get("enemies") or []))
                if not encounter_data["enemies"]:
                    continue
                party_preview = cls._build_preview_data(room, encounter_data)
                party_preview["source"] = "roaming"
                party_preview["engagement_scope"] = "room"
                party_preview["roaming_party_keys"] = [party.get("key")] if party.get("key") else []
                party_preview["threat_query"] = str(party.get("key") or encounter_data.get("key") or "").strip()
                options.append(party_preview)
            return options

        return [preview]

    @classmethod
    def resolve_room_threat_preview(cls, room, query=None):
        """Resolve a room threat preview for explicit combat selection."""

        options = cls.get_room_threat_options(room)
        if not options:
            return None
        if len(options) == 1 and not query:
            return options[0]

        query_norm = _normalize_token(query)
        if not query_norm:
            return options

        matches = []
        for preview in options:
            tokens = {
                _normalize_token(preview.get("threat_query")),
                _normalize_token(preview.get("encounter_key")),
                _normalize_token(preview.get("display_name")),
                _normalize_token(preview.get("party_name")),
                _normalize_token(preview.get("encounter_title")),
            }
            tokens.update(_normalize_token(enemy.get("key")) for enemy in (preview.get("enemies") or []))
            tokens.discard("")
            if query_norm in tokens:
                matches.append(preview)
        if matches:
            return matches[0] if len(matches) == 1 else matches

        partial_matches = []
        for preview in options:
            haystacks = [
                preview.get("threat_query"),
                preview.get("encounter_key"),
                preview.get("display_name"),
                preview.get("party_name"),
                preview.get("encounter_title"),
            ] + [enemy.get("key") for enemy in (preview.get("enemies") or [])]
            if any(query_norm and query_norm in _normalize_token(value) for value in haystacks):
                partial_matches.append(preview)
        if not partial_matches:
            return None
        return partial_matches[0] if len(partial_matches) == 1 else partial_matches

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
            from world.browser_panels import send_browser_notice_event

            send_browser_notice_event(
                character,
                "|rThe room turns before you can set your feet.|n",
                title="Combat",
                tone="danger",
                icon="warning",
                duration_ms=2600,
            )
        return encounter

    @classmethod
    def start_for_room(cls, room, expected_party_size=1, threat_query=None):
        """Create a new encounter for a room if encounter data exists."""

        encounter = cls.get_for_room(room)
        if encounter:
            return encounter, False

        preview = cls.resolve_room_threat_preview(room, threat_query)
        if isinstance(preview, list):
            if threat_query:
                return None, False
            preview = preview[0] if preview else None
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
        roaming_party_keys = list(preview.get("roaming_party_keys") or [])
        if roaming_party_keys:
            encounter.db.roaming_party_keys = roaming_party_keys
            mark_roaming_parties_engaged(roaming_party_keys, room_id=preview["room_id"])
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
        self.db.expected_party_size = max(1, min(COMBAT_MAX_PLAYER_CHARACTERS, int(expected_party_size or 1)))
        self.db.pending_actions = {}
        self.db.participants = []
        self.db.defeated_participants = []
        self.db.participant_states = {}
        self.db.participant_contributions = {}
        self.db.atb_states = {}
        self.db.threat = {}
        self.db.round = 0
        self.db.enemies = []
        self.db.enemy_counter = 0
        self.db.companions = []
        self.db.companion_counter = 0

        template_totals = {}
        enemy_templates = _limit_encounter_enemies(encounter_data.get("enemies") or [])
        for template_key in enemy_templates:
            template_totals[template_key] = template_totals.get(template_key, 0) + 1

        template_seen = {}
        for template_key in enemy_templates:
            template_seen[template_key] = template_seen.get(template_key, 0) + 1
            display_key = None
            if template_totals[template_key] > 1:
                display_key = f"{ENEMY_TEMPLATES[template_key]['name']} {template_seen[template_key]}"
            self._spawn_enemy(template_key, display_key=display_key, announce=False)

    def at_start(self):
        if self.obj:
            self.obj.ndb.brave_encounter = self
        self._refresh_browser_combat_views()

    def at_stop(self):
        participants = list(self.get_player_participants())
        self._clear_browser_combat_views(participants)
        if self.obj:
            self.obj.ndb.brave_encounter = None
            roaming_party_keys = list(self.db.roaming_party_keys or [])
            if roaming_party_keys:
                release_roaming_parties(roaming_party_keys, defeated=not self.get_active_enemies())
            elif not self.get_active_enemies():
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
        except (ObjectDB.DoesNotExist, TypeError, ValueError):
            return None

    def get_player_participants(self):
        """Resolve encounter participant dbrefs into character objects."""

        participants = []
        for participant_id in self.db.participants or []:
            participant = self._get_character(participant_id)
            if participant:
                participants.append(participant)
        return participants

    def get_participants(self):
        """Return all active allied combatants, including companions."""

        return list(self.get_player_participants()) + list(self.get_active_companions())

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
        for participant in self.get_player_participants() + self.get_defeated_participants():
            if not participant or participant.id in seen:
                continue
            seen.add(participant.id)
            participants.append(participant)
        return participants

    def get_active_player_participants(self):
        """Return conscious player characters still present in the fight."""

        active = []
        for participant in self.get_player_participants():
            resources = participant.db.brave_resources or {}
            if participant.location == self.obj and resources.get("hp", 0) > 0:
                active.append(participant)
        return active

    def _companion_state_template(self):
        """Return the default effect state for a ranger companion."""

        return {
            "guard": 0,
            "reaction_guard": 0,
            "reaction_guard_source": None,
            "reaction_label": None,
            "reaction_redirect_to": None,
            "sacred_aegis_turns": 0,
            "sacred_aegis_source": None,
            "sacred_aegis_power": 0,
            "grove_turns": 0,
            "primal_form": None,
            "primal_form_turns": 0,
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

    def _mark_defeat_consequence(self, character):
        """Apply the soft silver consequence for a non-tutorial defeat."""

        if not character or _is_companion_actor(character):
            return 0
        current = max(0, int(getattr(character.db, "brave_silver", 0) or 0))
        lost = min(COMBAT_DEFEAT_SILVER_LOSS, current)
        character.db.brave_silver = current - lost
        return lost

    def _set_defeat_resources(self, character):
        """Leave a defeated character barely standing until they rest."""

        if not character or _is_companion_actor(character):
            return
        character.db.brave_resources = {
            "hp": 1,
            "mana": 1,
            "stamina": 1,
        }

    def _get_companion(self, companion_id):
        """Return one active encounter companion by id."""

        for companion in self.db.companions or []:
            if str(companion.get("id")) == str(companion_id):
                return dict(companion)
        return None

    def get_active_companions(self, owner=None):
        """Return living encounter companions still fighting."""

        owner_id = getattr(owner, "id", owner)
        companions = []
        for companion in self.db.companions or []:
            if owner_id is not None and companion.get("owner_id") != owner_id:
                continue
            if companion.get("present", True) and int(companion.get("hp", 0) or 0) > 0:
                companions.append(dict(companion))
        return companions

    def _save_companion(self, companion):
        """Persist one encounter companion mapping."""

        companions = []
        for current in self.db.companions or []:
            companions.append(dict(companion) if current.get("id") == companion.get("id") else current)
        self.db.companions = companions

    def _spawn_ranger_companion(self, owner, announce=True):
        """Create the ranger's active bonded companion as an allied combat actor."""

        if not owner or getattr(getattr(owner, "db", None), "brave_class", "") != "ranger":
            return None
        existing = self.get_active_companions(owner=owner.id)
        if existing:
            return existing[0]
        definition = dict(getattr(owner, "get_active_companion", lambda: {})() or {})
        if not definition:
            return None
        combat = dict(definition.get("combat", {}))
        derived = dict(owner.db.brave_derived_stats or {})
        counter = int(self.db.companion_counter or 0) + 1
        self.db.companion_counter = counter
        companion = {
            "kind": "companion",
            "id": f"c{counter}",
            "owner_id": owner.id,
            "companion_key": str(getattr(owner.db, "brave_active_companion", "") or "").lower(),
            "key": definition.get("name", "Companion"),
            "icon": definition.get("icon", "pets"),
            "summary": definition.get("summary", "A bonded ranger companion joins the line."),
            "bond": dict(definition.get("bond", {}) or {}),
            "bond_label": definition.get("bond_label", "Bond 1"),
            "max_hp": max(12, int(round(derived.get("max_hp", 24) * float(combat.get("hp_ratio", 0.5) or 0.5)))),
            "hp": 0,
            "attack_power": max(4, int(round(derived.get("attack_power", 8) * float(combat.get("attack_ratio", 0.5) or 0.5)))),
            "armor": max(0, int(round(derived.get("armor", 4) * float(combat.get("armor_ratio", 0.7) or 0.7)))),
            "accuracy": max(40, int(derived.get("accuracy", 55) + int(combat.get("accuracy_bonus", 0) or 0))),
            "dodge": max(0, int(round(derived.get("dodge", 4) * 0.8)) + int(combat.get("dodge_bonus", 0) or 0)),
            "fill_rate": max(70, int(combat.get("fill_rate_bonus", 0) or 0) + 92),
            "present": True,
        }
        companion["hp"] = companion["max_hp"]
        companions = list(self.db.companions or [])
        companions.append(companion)
        self.db.companions = companions
        states = dict(self.db.participant_states or {})
        states[str(companion["id"])] = self._companion_state_template()
        self.db.participant_states = states
        self._save_actor_atb_state(
            create_atb_state(fill_rate=companion["fill_rate"], tick_ms=self._atb_tick_ms()),
            companion=companion,
        )
        threat = dict(self.db.threat or {})
        threat[str(companion["id"])] = 0
        self.db.threat = threat
        if announce and self.obj:
            self.obj.msg_contents(f"|g{companion['key']} bounds into the fight beside {owner.key}.|n")
        return companion

    def _remove_companion(self, companion, *, refresh=True):
        """Remove a ranger companion from the encounter."""

        companion_id = str(companion.get("id"))
        self.db.companions = [entry for entry in (self.db.companions or []) if str(entry.get("id")) != companion_id]
        states = dict(self.db.participant_states or {})
        states.pop(companion_id, None)
        self.db.participant_states = states
        self._clear_actor_atb_state(companion=companion)
        threat = dict(self.db.threat or {})
        threat.pop(companion_id, None)
        self.db.threat = threat
        if refresh:
            self._refresh_browser_combat_views()

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
        key = str(_ally_actor_id(character))
        contribution = dict(contributions.get(key) or {})
        if not contribution:
            contribution = {
                "joined_round": int(self.db.round or 0),
                "meaningful_actions": 0,
                "damage_done": 0,
                "healing_done": 0,
                "damage_prevented": 0,
                "utility_points": 0,
                "hits_taken": 0,
                "boss_credit_eligible": bool(self._boss_credit_open()),
            }
            if _is_companion_actor(character):
                contribution["owner_id"] = character.get("owner_id")
                contribution["companion_key"] = str(character.get("companion_key") or "").lower()
                contribution["companion_name"] = character.get("key", "Companion")
            contributions[key] = contribution
            self.db.participant_contributions = contributions
        return contribution

    def _save_participant_contribution(self, character, contribution):
        """Persist contribution tracking for a participant."""

        contributions = dict(self.db.participant_contributions or {})
        contributions[str(_ally_actor_id(character))] = dict(contribution or {})
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

        if not character or _ally_actor_id(character) is None:
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

    def _participant_reward_weight(self, character, *, max_round, top_impact):
        """Return weighted contribution used for XP and silver splits."""

        contribution = self._get_participant_contribution(character)
        joined_round = int(contribution.get("joined_round", 0) or 0)
        total_rounds = max(1, int(max_round or 1))
        rounds_present = max(1, total_rounds - joined_round)
        time_weight = max(0.2, min(1.0, rounds_present / float(total_rounds)))
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
                tick_ms=self._atb_tick_ms(),
            ),
            enemy=enemy,
        )

    def _record_telegraph_outcome(self, enemy, outcome, *, label=None, answer=None, target=None):
        """Store the latest answer state for a telegraphed enemy action."""

        if not enemy:
            return
        enemy["telegraph_outcome"] = str(outcome or "").strip().lower() or "unanswered"
        enemy["telegraph_label"] = label or enemy.get("telegraph_label") or self._enemy_action_label(enemy)
        if answer:
            enemy["telegraph_answer"] = str(answer)
        else:
            enemy.pop("telegraph_answer", None)
        if target:
            enemy["telegraph_target"] = _combat_target_name(target, "Companion")
        else:
            enemy.pop("telegraph_target", None)
        saver = getattr(self, "_save_enemy", None)
        if callable(saver):
            saver(enemy)

    def _apply_reaction_guard(self, source, target, *, amount, label, redirect_to=None):
        """Apply a telegraph-answering guard or redirect effect."""

        state = self._get_participant_state(target)
        state["reaction_guard"] = max(int(state.get("reaction_guard", 0) or 0), max(0, int(amount or 0)))
        state["reaction_guard_source"] = getattr(source, "id", None)
        state["reaction_label"] = label
        state["reaction_redirect_to"] = redirect_to
        self._save_participant_state(target, state)
        emitter = getattr(self, "_emit_defend_fx", None)
        if callable(emitter):
            emitter(source, target, text=label or "GUARD")

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
        recovery_ticks = 1 + get_interrupt_recovery_bonus(character)
        self._set_enemy_recovery_state(enemy, ticks=recovery_ticks)
        self._record_telegraph_outcome(enemy, "interrupted", label=reaction["label"], answer=tool_label, target=character)
        self.obj.msg_contents(
            f"|g{character.key}'s {tool_label} breaks {enemy['key']}'s {reaction['label']}.|n"
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
        for participant in self.get_player_participants():
            resources = participant.db.brave_resources or {}
            if participant.location == self.obj and resources.get("hp", 0) > 0:
                active.append(participant)
        active.extend(self.get_active_companions())
        return active

    def _refresh_browser_combat_views(self, participants=None):
        """Refresh browser combat UI for current participants without clearing the log."""

        from world.browser_panels import build_combat_panel, send_webclient_event
        from world.browser_views import build_combat_view

        targets = participants if participants is not None else self.get_active_player_participants()
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

        for participant in self.get_active_player_participants():
            if participant and participant.location == self.obj:
                send_webclient_event(participant, brave_combat_fx=event)

    def _emit_miss_fx(self, source, target, text="MISS"):
        """Emit a miss event so whiffs still read on the battle board."""

        source_name = source.get("key") if isinstance(source, dict) else getattr(source, "key", None)
        target_name = target.get("key") if isinstance(target, dict) else getattr(target, "key", None)
        if not source_name or not target_name:
            return
        self._emit_combat_fx(
            kind="miss",
            source=source_name,
            source_ref=_combat_entry_ref(source),
            target=target_name,
            target_ref=_combat_entry_ref(target),
            text=text,
            tone="warn",
            impact="miss",
            lunge=True,
        )

    def _emit_defend_fx(self, source, target=None, text="GUARD"):
        """Emit a guard/defend event on the protected combat card."""

        protected = target or source
        source_name = source.get("key") if isinstance(source, dict) else getattr(source, "key", None)
        target_name = protected.get("key") if isinstance(protected, dict) else getattr(protected, "key", None)
        if not source_name or not target_name:
            return
        self._emit_combat_fx(
            kind="defend",
            source=source_name,
            source_ref=_combat_entry_ref(source),
            target=target_name,
            target_ref=_combat_entry_ref(protected),
            text=str(text or "GUARD").upper(),
            tone="guard",
            impact="guard",
        )

    def _emit_defeat_fx(self, target, text="DOWN"):
        """Emit a defeat event so removals still animate on the battle board."""

        target_name = target.get("key") if isinstance(target, dict) else getattr(target, "key", None)
        if not target_name:
            return
        self._emit_combat_fx(
            kind="defeat",
            target=target_name,
            target_ref=_combat_entry_ref(target),
            text=text,
            tone="break",
            impact="break",
            defeat=True,
        )

    def _announce_combat_action(self, actor, label, style=None, element=None):
        """Emit a short JRPG-style action banner into the battle feed."""

        if not self.obj or not label:
            return
        actor_name = _combat_target_name(actor, "Companion")
        self.obj.msg_contents(f"|c{actor_name} uses {label}!|n")
        emitter = getattr(self, "_emit_combat_fx", None)
        if callable(emitter):
            emitter(
                kind="action",
                actor=actor_name,
                label=label,
                source=actor_name,
                source_ref=_combat_entry_ref(actor),
                style=style or "ability",
                element=element,
            )

    def _clear_browser_combat_views(self, participants=None):
        """Remove any sticky browser combat UI for participants."""

        from world.browser_panels import send_webclient_event

        if getattr(getattr(self, "ndb", None), "brave_skip_combat_done", False):
            return

        targets = participants if participants is not None else self.get_player_participants()
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

    def react_to_emote(self, character, enemy, emote_text):
        """Optionally react to a targeted social emote."""

        if not enemy or enemy not in self.get_active_enemies():
            return None

        template = ENEMY_TEMPLATES.get(enemy.get("template_key"), {})
        reactions = enemy.get("emote_reactions")
        if not reactions:
            reactions = template.get("emote_reactions")
        if isinstance(reactions, str):
            return reactions

        if isinstance(reactions, dict):
            verb = _base_form_verb(str(emote_text or "").split()[:1][0] if str(emote_text or "").split() else "")
            chosen = reactions.get(verb) or reactions.get("default") or reactions.get("any")
            if isinstance(chosen, dict):
                response = chosen.get("text") or chosen.get("message")
                aggro = int(chosen.get("aggro", chosen.get("threat", 0)) or 0)
            else:
                response = chosen
                aggro = 0
            if aggro > 0 and character:
                self._add_threat(character, aggro)
            return response

        if character and template.get("emote_aggro"):
            self._add_threat(character, int(template.get("emote_aggro", 0) or 0))
        return None

    def _get_scaling_profile(self):
        size = max(1, min(4, int(self.db.expected_party_size or 1)))
        scaling = dict(PARTY_SCALING[size])
        room_id = str(self.db.room_id or "")
        if size == 1 and room_id.startswith("drowned_weir_"):
            scaling["hp"] = round(scaling["hp"] * DROWNED_WEIR_SOLO_SCALING["hp"], 4)
            scaling["power"] = round(scaling["power"] * DROWNED_WEIR_SOLO_SCALING["power"], 4)
            scaling["accuracy"] += DROWNED_WEIR_SOLO_SCALING["accuracy"]
            scaling["label"] = "Solo Drowned Weir"
        encounter_override = SOLO_ENCOUNTER_SCALING_OVERRIDES.get(str(self.db.encounter_key or ""))
        if size == 1 and encounter_override:
            scaling["hp"] = round(scaling["hp"] * encounter_override.get("hp", 1.0), 4)
            scaling["power"] = round(scaling["power"] * encounter_override.get("power", 1.0), 4)
            scaling["accuracy"] += int(encounter_override.get("accuracy", 0) or 0)
        return scaling

    def _primary_resource_key(self, character):
        if character.db.brave_class in {"cleric", "mage", "druid"}:
            return "mana"
        return "stamina"

    def _actor_atb_key(self, character=None, enemy=None, companion=None):
        if character is not None:
            return f"p:{character.id}"
        if enemy is not None:
            return f"e:{enemy['id']}"
        if companion is not None:
            return f"c:{companion['id']}"
        raise ValueError("ATB actor key requires a character or enemy.")

    def _atb_tick_ms(self):
        return max(1, int(round(float(getattr(self, "interval", 0.25) or 0.25) * 1000)))

    def _default_atb_fill_rate(self, *, character=None, enemy=None, companion=None):
        if character is not None:
            class_base = {
                "rogue": 98,
                "ranger": 88,
                "druid": 82,
                "warrior": 80,
                "paladin": 78,
                "cleric": 76,
                "mage": 74,
            }.get(getattr(character.db, "brave_class", ""), 84)
            primary = dict(getattr(character.db, "brave_primary_stats", {}) or {})
            agility = int(primary.get("agility", 0) or 0)
            fill_rate = (
                class_base
                + (agility * 8)
                + get_atb_fill_rate_bonus(character)
                + get_wounded_atb_fill_rate_bonus(character)
            )
            return max(68, min(176, fill_rate))
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
        if companion is not None:
            return max(70, min(176, int(companion.get("fill_rate", 96) or 96)))
        return 84

    def _get_actor_atb_state(self, character=None, enemy=None, companion=None):
        states = dict(self.db.atb_states or {})
        key = self._actor_atb_key(character=character, enemy=enemy, companion=companion)
        if key not in states:
            states[key] = create_atb_state(
                fill_rate=self._default_atb_fill_rate(character=character, enemy=enemy, companion=companion),
                tick_ms=self._atb_tick_ms(),
            )
            self.db.atb_states = states
        return states[key]

    def _save_actor_atb_state(self, state, *, character=None, enemy=None, companion=None):
        states = dict(self.db.atb_states or {})
        key = self._actor_atb_key(character=character, enemy=enemy, companion=companion)
        states[key] = create_atb_state(**dict(state or {}), tick_ms=self._atb_tick_ms())
        self.db.atb_states = states

    def _clear_actor_atb_state(self, *, character=None, enemy=None, companion=None):
        states = dict(self.db.atb_states or {})
        states.pop(self._actor_atb_key(character=character, enemy=enemy, companion=companion), None)
        self.db.atb_states = states

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
        if template_key in {"old_greymaw", "miretooth", "ruk_fence_cutter", "tower_archer", "mag_clamp_drone"}:
            return normalize_atb_profile({"windup_ticks": 1, "recovery_ticks": 1, "telegraph": True})
        if template_key in {"sir_edric_restless", "foreman_coilback", "captain_varn_blackreed", "grubnak_the_pot_king", "hollow_lantern"}:
            return normalize_atb_profile({"windup_ticks": 2, "recovery_ticks": 1, "telegraph": True})
        return dict(DEFAULT_ENEMY_ATTACK_ATB_PROFILE)

    def _enemy_action_label(self, enemy):
        template_key = (enemy or {}).get("template_key")
        return {
            "old_greymaw": "Brush Pounce",
            "miretooth": "Reed Ambush",
            "ruk_fence_cutter": "Fence-Cutter Swing",
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
        possessive = get_brave_pronoun(_enemy_gender(enemy), "possessive_adjective")
        return {
            "old_greymaw": f"|y{enemy['key']} lowers into the brush, gathering for {label}.|n",
            "miretooth": f"|y{enemy['key']} disappears into the reeds and lines up {label}.|n",
            "ruk_fence_cutter": f"|y{enemy['key']} plants his feet and hauls the axe back for {label}.|n",
            "tower_archer": f"|y{enemy['key']} draws a careful bead for {label}.|n",
            "mag_clamp_drone": f"|y{enemy['key']} locks its rig and charges {label}.|n",
            "sir_edric_restless": f"|y{enemy['key']} raises {possessive} blade for {label}.|n",
            "foreman_coilback": f"|y{enemy['key']} routes static through the frame for {label}.|n",
            "captain_varn_blackreed": f"|y{enemy['key']} shifts {possessive} stance and sets up {label}.|n",
            "grubnak_the_pot_king": f"|y{enemy['key']} heaves the cauldron high for {label}.|n",
            "hollow_lantern": f"|y{enemy['key']} swells with drowned light and prepares {label}.|n",
        }.get((enemy or {}).get("template_key"), f"|y{enemy['key']} prepares an attack.|n")

    def _describe_pending_action(self, character, action_override=None):
        if action_override is None:
            if _is_companion_actor(character):
                atb_state = self._get_actor_atb_state(companion=character)
            else:
                atb_state = self._get_actor_atb_state(character=character)
            active_action = atb_state.get("current_action")
            if active_action and atb_state.get("phase") == "winding":
                action_text = self._describe_pending_action(character, action_override=active_action)
                return f"winding -> {action_text}"
            if atb_state.get("phase") in {"recovering", "cooldown"}:
                return "recovering"
        if _is_companion_actor(character):
            return "harry nearest prey"
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
                target = self._get_participant_target(action.get("target")) if action.get("target") else character
                target_name = _combat_target_name(target, character.key)
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
                target = self._get_participant_target(action.get("target")) if action.get("target") else character
                target_name = _combat_target_name(target, character.key)
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
            if _is_companion_actor(participant):
                resources = {"hp": int(participant.get("hp", 0) or 0)}
                derived = {"max_hp": int(participant.get("max_hp", 1) or 1)}
                primary_resource = "stamina"
                primary_label = "Bond"
            else:
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
                f"  |w{_combat_target_name(participant, 'Companion').ljust(10)}|n {hp_bar} |wHP|n  {res_bar} |w{primary_label[:3].upper()}|n {cond_str}\n"
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
            "  |wHEROES|n",
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
            if query_norm == _normalize_token(_combat_target_name(participant)):
                return participant
            if query_norm == _normalize_token(str(_ally_actor_id(participant))):
                return participant
        for participant in participants:
            if query_norm in _normalize_token(_combat_target_name(participant)):
                return participant
        return None

    def _get_participant_target(self, target_id):
        """Resolve an allied target id into a character or companion actor."""

        if target_id in (None, ""):
            return None
        target = self._get_character(target_id)
        if target:
            return target
        return self._get_companion(target_id)

    def find_consumable(self, character, query, *, context="combat", verb=None):
        """Find a carried combat-usable consumable by fuzzy name."""

        return match_inventory_item(character, query, context=context, category="consumable", verb=verb)

    def add_participant(self, character):
        """Join a character to the encounter."""

        if not character or character.location != self.obj:
            return False, "You are not in the right place to join this fight."

        if is_tutorial_solo_combat_room(self.obj):
            active_players = [
                participant
                for participant in self.get_active_player_participants()
                if participant and participant.id != character.id
            ]
            if active_players:
                return False, "The newbie pen is a one-at-a-time lesson. Wait for the current training fight to finish."

        character.ensure_brave_character()
        if (character.db.brave_resources or {}).get("hp", 0) <= 0:
            return False, "You can't join a fight while down."
        if character.id not in (self.db.participants or []) and len(self.get_registered_participants()) >= COMBAT_MAX_PLAYER_CHARACTERS:
            return False, "The ally line is already full."

        if character.id not in self.db.participants:
            self.db.participants = list(self.db.participants or []) + [character.id]
            participant_states = dict(self.db.participant_states or {})
            participant_states[str(character.id)] = self._companion_state_template()
            self.db.participant_states = participant_states
            self._save_actor_atb_state(
                create_atb_state(fill_rate=self._default_atb_fill_rate(character=character), tick_ms=self._atb_tick_ms()),
                character=character,
            )
            threat = dict(self.db.threat or {})
            threat[str(character.id)] = threat.get(str(character.id), 0)
            self.db.threat = threat
            self._get_participant_contribution(character)
            self._spawn_ranger_companion(character)
            character.ndb.brave_encounter = self
            from world.browser_panels import send_browser_notice_event

            send_browser_notice_event(
                character,
                "You join the fight.",
                title="Combat",
                tone="danger",
                icon="swords",
                duration_ms=2600,
            )
        else:
            character.ndb.brave_encounter = self
            self._get_participant_contribution(character)
            self._spawn_ranger_companion(character, announce=False)

        self._refresh_browser_combat_views()
        if character.location == self.obj:
            intro = (self.db.encounter_intro or "").strip()
            character.msg(f"|r{intro}|n" if intro else f"|r{self.db.encounter_title}!|n")

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
        """Queue an ability for the next combat round."""

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
        chance = 52 + derived.get("dodge", 0) - max(0, enemy_count - 1) * 6 + get_flee_chance_bonus(character)
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
        """Queue a combat-usable consumable for the next round."""

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
        key = str(_ally_actor_id(character))
        if key not in states:
            template = getattr(self, "_companion_state_template", None)
            states[key] = template() if callable(template) else {
                "guard": 0,
                "reaction_guard": 0,
                "reaction_guard_source": None,
                "reaction_label": None,
                "reaction_redirect_to": None,
                "sacred_aegis_turns": 0,
                "sacred_aegis_source": None,
                "sacred_aegis_power": 0,
                "grove_turns": 0,
                "primal_form": None,
                "primal_form_turns": 0,
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
        states[str(_ally_actor_id(character))] = state
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
            "emote_reactions": dict(template.get("emote_reactions") or {}),
            "emote_aggro": template.get("emote_aggro", 0),
            "marked_turns": 0,
            "judged_turns": 0,
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
            "icon": get_enemy_icon_name(template_key, template),
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
            create_atb_state(fill_rate=self._default_atb_fill_rate(enemy=enemy), tick_ms=self._atb_tick_ms()),
            enemy=enemy,
        )
        if announce and self.obj:
            self.obj.msg_contents(f"|r{enemy['key']} joins the fight!|n")
        return enemy

    def _add_threat(self, character, amount):
        threat = dict(self.db.threat or {})
        key = str(_ally_actor_id(character))
        threat[key] = threat.get(key, 0) + max(0, amount)
        self.db.threat = threat

    def _roll_hit(self, accuracy, dodge):
        chance = max(35, min(95, 55 + accuracy - dodge))
        return random.randint(1, 100) <= chance

    def _weapon_damage(self, attack_power, armor, bonus=0):
        return max(1, attack_power // 2 + random.randint(2, 6) + bonus - armor // 4)

    def _spell_damage(self, spell_power, armor, bonus=0):
        return max(1, spell_power // 2 + random.randint(3, 7) + bonus - armor // 5)

    def _crit_chance_for_actor(self, actor):
        """Return clamped crit chance for an actor that is allowed to crit."""

        if isinstance(actor, Mapping) and actor.get("template_key"):
            if "crit_chance" not in actor:
                return 0
            chance = actor.get("crit_chance", 0)
        else:
            chance = self._get_effective_derived(actor).get("crit_chance", 0)
        try:
            chance = int(chance or 0)
        except (TypeError, ValueError):
            chance = 0
        return max(0, min(50, chance))

    def _roll_critical(self, actor):
        chance = self._crit_chance_for_actor(actor)
        return chance > 0 and random.randint(1, 100) <= chance

    def _critical_damage(self, base_damage):
        base_damage = max(1, int(base_damage or 0))
        return max(base_damage + 1, int(math.ceil(base_damage * 1.5)))

    def _spend_resource(self, character, resource, amount):
        if _is_companion_actor(character):
            return
        resources = dict(character.db.brave_resources or {})
        resources[resource] = max(0, resources[resource] - amount)
        character.db.brave_resources = resources

    def _get_effective_derived(self, character):
        if _is_companion_actor(character):
            derived = {
                "max_hp": int(character.get("max_hp", 1) or 1),
                "attack_power": int(character.get("attack_power", 0) or 0),
                "armor": int(character.get("armor", 0) or 0),
                "accuracy": int(character.get("accuracy", 0) or 0),
                "dodge": int(character.get("dodge", 0) or 0),
                "crit_chance": int(character.get("crit_chance", 0) or 0),
                "spell_power": 0,
                "healing_power": 0,
            }
            state = self._get_participant_state(character)
            if state.get("curse_turns", 0) > 0:
                derived["armor"] = max(0, derived.get("armor", 0) - state.get("curse_armor_penalty", 0))
            if state.get("snare_turns", 0) > 0:
                derived["accuracy"] = max(0, derived.get("accuracy", 0) - state.get("snare_accuracy_penalty", 0))
                derived["dodge"] = max(0, derived.get("dodge", 0) - state.get("snare_dodge_penalty", 0))
            if state.get("poison_turns", 0) > 0:
                derived["accuracy"] = max(0, derived.get("accuracy", 0) - state.get("poison_accuracy_penalty", 0))
            return derived
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
        form = state.get("primal_form")
        if state.get("primal_form_turns", 0) > 0 and form == "bear":
            derived["armor"] = derived.get("armor", 0) + 3
            derived["attack_power"] = derived.get("attack_power", 0) + 2
            derived["dodge"] = max(0, derived.get("dodge", 0) - 1)
        elif state.get("primal_form_turns", 0) > 0 and form == "wolf":
            derived["accuracy"] = derived.get("accuracy", 0) + 3
            derived["dodge"] = derived.get("dodge", 0) + 4
            derived["attack_power"] = derived.get("attack_power", 0) + 1
        elif state.get("primal_form_turns", 0) > 0 and form == "crow":
            derived["accuracy"] = derived.get("accuracy", 0) + 4
            derived["dodge"] = derived.get("dodge", 0) + 3
            derived["spell_power"] = derived.get("spell_power", 0) + 1
        elif state.get("primal_form_turns", 0) > 0 and form == "serpent":
            derived["attack_power"] = derived.get("attack_power", 0) + 1
            derived["spell_power"] = derived.get("spell_power", 0) + 2
            derived["accuracy"] = derived.get("accuracy", 0) + 2
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
        """Consume a one-round stealth setup for rogue burst abilities."""

        state = self._get_participant_state(character)
        if state.get("stealth_turns", 0) <= 0:
            return 0

        state["stealth_turns"] = 0
        self._save_participant_state(character, state)
        return 6

    def _damage_enemy(self, attacker, enemy, damage, extra_text="", damage_type="physical"):
        race_bonus = get_wounded_damage_bonus(attacker)
        if race_bonus > 0:
            damage += race_bonus
            extra_text = " Battle Hunger drives the blow harder." + extra_text
        if enemy["marked_turns"] > 0:
            damage += 4
        if enemy.get("shielded"):
            damage = max(1, damage // 2)
            extra_text = " The ward absorbs part of the blow." + extra_text
        roller = getattr(self, "_roll_critical", None)
        critical = bool(callable(roller) and roller(attacker))
        if critical:
            damage = self._critical_damage(damage)
        enemy["hp"] = max(0, enemy["hp"] - damage)
        defeated = enemy["hp"] <= 0
        self._save_enemy(enemy)
        attacker_class = getattr(getattr(attacker, "db", None), "brave_class", "")
        self._add_threat(attacker, damage + (8 if attacker_class == "warrior" else 0))
        self._record_participant_contribution(attacker, meaningful=True, damage=damage)
        marked_text = " The mark flares." if enemy["marked_turns"] > 0 else ""
        attacker_name = _combat_target_name(attacker, "Companion")
        crit_text = " Critical hit!" if critical else ""
        self.obj.msg_contents(f"{attacker_name} hits {enemy['key']} for {damage} damage.{crit_text}{marked_text}{extra_text}")
        self._emit_combat_fx(
            kind="damage",
            source=attacker_name,
            source_ref=_combat_entry_ref(attacker),
            target=enemy["key"],
            target_ref=_combat_entry_ref(enemy),
            amount=damage,
            text=str(damage),
            tone="damage",
            impact="critical" if critical else "damage",
            element=damage_type,
            critical=critical,
            shake="subtle" if critical else None,
            defeat=defeated,
            lunge=True,
        )
        if defeated:
            self._emit_defeat_fx(enemy)
            self.obj.msg_contents(f"{enemy['key']} falls.")
            self._award_enemy_defeat_credit(enemy)
            if not self.get_active_enemies():
                self._schedule_victory_sequence("|gThe encounter is over. The road is clear for now.|n")

    def _heal_character(self, source, target, amount, heal_type="healing"):
        if _is_companion_actor(target):
            before = int(target.get("hp", 0) or 0)
            max_hp = int(target.get("max_hp", 1) or 1)
            target["hp"] = min(max_hp, before + amount)
            healed = target["hp"] - before
            self._save_companion(target)
        else:
            resources = dict(target.db.brave_resources or {})
            max_hp = target.db.brave_derived_stats["max_hp"]
            before = resources["hp"]
            resources["hp"] = min(max_hp, resources["hp"] + amount)
            target.db.brave_resources = resources
            healed = resources["hp"] - before
        self._add_threat(source, max(1, healed // 2))
        if healed > 0:
            self._record_participant_contribution(source, meaningful=True, healing=healed)
        source_name = _combat_target_name(source, "Companion")
        target_name = _combat_target_name(target, "Companion")
        self.obj.msg_contents(f"{source_name} restores {healed} HP to {target_name}.")
        self._emit_combat_fx(
            kind="heal",
            source=source_name,
            source_ref=_combat_entry_ref(source),
            target=target_name,
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
        turns = adjust_effect_turns(target, "bleed", turns)
        damage = adjust_effect_damage(target, "bleed", damage)
        if turns <= 0 or damage <= 0:
            self.obj.msg_contents(f"{_combat_target_name(target, 'Companion')} shrugs off the bleeding cut.")
            return
        state = self._get_participant_state(target)
        state["bleed_turns"] = max(state.get("bleed_turns", 0), turns)
        state["bleed_damage"] = max(state.get("bleed_damage", 0), damage)
        self._save_participant_state(target, state)
        self.obj.msg_contents(f"|r{_combat_target_name(target, 'Companion')} starts bleeding!|n")

    def _apply_curse(self, target, turns, armor_penalty, message=None):
        state = self._get_participant_state(target)
        state["curse_turns"] = max(state.get("curse_turns", 0), turns)
        state["curse_armor_penalty"] = max(state.get("curse_armor_penalty", 0), armor_penalty)
        self._save_participant_state(target, state)
        self.obj.msg_contents(message or f"|m{_combat_target_name(target, 'Companion')} is cursed!|n")

    def _apply_poison(self, target, turns, damage, accuracy_penalty, message=None):
        turns = adjust_effect_turns(target, "poison", turns)
        damage = adjust_effect_damage(target, "poison", damage)
        accuracy_penalty = adjust_effect_penalty(target, "poison", "accuracy_penalty", accuracy_penalty)
        if turns <= 0:
            self.obj.msg_contents(f"{_combat_target_name(target, 'Companion')} shrugs off the poison.")
            return
        state = self._get_participant_state(target)
        state["poison_turns"] = max(state.get("poison_turns", 0), turns)
        state["poison_damage"] = max(state.get("poison_damage", 0), damage)
        state["poison_accuracy_penalty"] = max(state.get("poison_accuracy_penalty", 0), accuracy_penalty)
        self._save_participant_state(target, state)
        self.obj.msg_contents(message or f"|g{_combat_target_name(target, 'Companion')} is poisoned!|n")

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
        turns = adjust_effect_turns(target, "snare", turns)
        accuracy_penalty = adjust_effect_penalty(target, "snare", "accuracy_penalty", accuracy_penalty)
        dodge_penalty = adjust_effect_penalty(target, "snare", "dodge_penalty", dodge_penalty)
        if turns <= 0:
            self.obj.msg_contents(f"{_combat_target_name(target, 'Companion')} slips clear before the snare can hold.")
            return
        state = self._get_participant_state(target)
        state["snare_turns"] = max(state.get("snare_turns", 0), turns)
        state["snare_accuracy_penalty"] = max(state.get("snare_accuracy_penalty", 0), accuracy_penalty)
        state["snare_dodge_penalty"] = max(state.get("snare_dodge_penalty", 0), dodge_penalty)
        self._save_participant_state(target, state)
        self.obj.msg_contents(f"|y{_combat_target_name(target, 'Companion')} is tangled in webbing!|n")

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
            if _is_companion_actor(participant):
                resources = {"hp": int(participant.get("hp", 0) or 0)}
            else:
                resources = dict(participant.db.brave_resources or {})

            if bleed_turns > 0:
                damage = max(1, state.get("bleed_damage", 1))
                resources["hp"] = max(0, resources["hp"] - damage)
                if _is_companion_actor(participant):
                    participant["hp"] = resources["hp"]
                    self._save_companion(participant)
                else:
                    participant.db.brave_resources = resources
                self.obj.msg_contents(f"|r{_combat_target_name(participant, 'Companion')} bleeds for {damage} damage.|n")
                self._emit_combat_fx(
                    kind="damage",
                    target=_combat_target_name(participant, "Companion"),
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
                    if _is_companion_actor(participant):
                        self._defeat_companion(participant)
                    else:
                        self._defeat_character(participant)
                    continue

            poison_turns = state.get("poison_turns", 0)
            if poison_turns > 0:
                damage = max(1, state.get("poison_damage", 1))
                resources["hp"] = max(0, resources["hp"] - damage)
                if _is_companion_actor(participant):
                    participant["hp"] = resources["hp"]
                    self._save_companion(participant)
                else:
                    participant.db.brave_resources = resources
                self.obj.msg_contents(f"|g{_combat_target_name(participant, 'Companion')} suffers {damage} poison damage.|n")
                self._emit_combat_fx(
                    kind="damage",
                    target=_combat_target_name(participant, "Companion"),
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
                    self.obj.msg_contents(f"{_combat_target_name(participant, 'Companion')} fights the poison clear.")

                if resources["hp"] <= 0:
                    self._save_participant_state(participant, state)
                    if _is_companion_actor(participant):
                        self._defeat_companion(participant)
                    else:
                        self._defeat_character(participant)
                    continue

            if state.get("curse_turns", 0) > 0:
                state["curse_turns"] = max(0, state["curse_turns"] - 1)
                if state["curse_turns"] <= 0 and state.get("curse_armor_penalty", 0):
                    state["curse_armor_penalty"] = 0
                    self.obj.msg_contents(f"{_combat_target_name(participant, 'Companion')} shakes off the curse.")

            if state.get("snare_turns", 0) > 0:
                state["snare_turns"] = max(0, state["snare_turns"] - 1)
                if state["snare_turns"] <= 0:
                    state["snare_accuracy_penalty"] = 0
                    state["snare_dodge_penalty"] = 0
                    self.obj.msg_contents(f"{_combat_target_name(participant, 'Companion')} tears free of the webbing.")

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
                self._emit_combat_fx(
                    kind="damage",
                    target=enemy["key"],
                    target_ref=_combat_entry_ref(enemy),
                    amount=damage,
                    text=str(damage),
                    tone="damage",
                    impact="damage",
                    element="bleed",
                    defeat=enemy["hp"] <= 0,
                )
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
                    defeat=enemy["hp"] <= 0,
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
            possessive = get_brave_pronoun(_enemy_gender(enemy), "possessive_adjective")
            objective = get_brave_pronoun(_enemy_gender(enemy), "object")
            if enemy["hp"] <= (enemy["max_hp"] * 2) // 3 and not enemy.get("called_help"):
                self._spawn_enemy("restless_shade", display_key="Edric's Grave Shade")
                self._spawn_enemy("barrow_wisp", display_key="Edric's Grave-Light")
                enemy["called_help"] = True
                enemy["shielded"] = True
                self.obj.msg_contents(
                    f"|rSir Edric raises {possessive} blade and the barrow answers. Grave-light coils around {objective} as lesser dead rise to {possessive} call!|n"
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
                self.obj.msg_contents(f"|rSir Edric lowers the last of {possessive} restraint and advances with funeral wrath.|n")
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
        from world.browser_panels import send_text_to_non_web_sessions, send_webclient_event
        from world.browser_views import build_combat_defeat_view
        from world.resting import room_allows_rest

        self._emit_defeat_fx(character)
        tutorial_recovery_room = get_tutorial_defeat_room(character)
        start_room = tutorial_recovery_room or get_room("brambleford_lantern_rest_inn") or get_room("brambleford_town_green")
        character.clear_chapel_blessing()
        character.restore_resources()
        self._set_defeat_resources(character)
        silver_lost = 0
        if not tutorial_recovery_room:
            silver_lost = self._mark_defeat_consequence(character)
        self._mark_defeated_participant(character)
        self.remove_participant(character, refresh=False)
        if start_room:
            character.move_to(start_room, quiet=True, move_type="defeat")
        send_webclient_event(character, brave_combat_done={})
        if character.location:
            send_text_to_non_web_sessions(character, character.at_look(character.location))
        delay(COMBAT_DEFEAT_REFRESH_DELAY, self._refresh_browser_combat_views, persistent=False)
        if tutorial_recovery_room:
            recovery_message = "|rThe lesson lands hard, but not fatally. You are hauled back to Wayfarer's Yard, barely standing. Rest before you try again.|n"
        else:
            recovery_message = "|rYou are overwhelmed and carried back to Brambleford, barely standing. Rest before heading out again.|n"
            if silver_lost:
                recovery_message += f" Recovery costs you {silver_lost} silver."
        send_text_to_non_web_sessions(character, recovery_message)
        send_webclient_event(
            character,
            brave_view=build_combat_defeat_view(
                character,
                recovery_room=character.location,
                silver_lost=silver_lost,
                tutorial=bool(tutorial_recovery_room),
                can_rest=room_allows_rest(character.location),
            ),
        )

    def remove_participant(self, character, *, refresh=True):
        """Remove a participant from the fight."""

        participants = [pid for pid in (self.db.participants or []) if pid != character.id]
        self.db.participants = participants
        for companion in list(self.get_active_companions(owner=character.id)):
            self._remove_companion(companion, refresh=False)
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
        if refresh:
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
            self.obj.msg_contents(f"{_combat_target_name(character, 'Companion')} misses {target['key']}.")
            self._emit_miss_fx(character, target)
            self._add_threat(character, 2)
            return

        bonus = self._consume_feint_bonus(character) if getattr(getattr(character, "db", None), "brave_class", "") == "rogue" else 0
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
            target = self._get_participant_target(action["target"])
        if ability["target"] == "enemy" and (not target or target["hp"] <= 0):
            target = self._default_enemy_target()
        if ability["target"] == "ally" and not target:
            target = character
        if ability["target"] != "none" and not target:
            return

        action_style = "cast" if ability.get("resource") == "mana" else "ability"
        action_element = ability.get("icon_role") if ability.get("icon_role") in {"fire", "frost", "lightning", "holy", "nature", "poison", "shadow"} else None
        try:
            self._announce_combat_action(character, ability_name, style=action_style, element=action_element)
        except TypeError:
            self._announce_combat_action(character, ability_name)
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
        from world.browser_panels import send_browser_notice_event, send_text_to_non_web_sessions, send_webclient_event

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
        send_webclient_event(character, brave_combat_done={})
        if character.location:
            send_text_to_non_web_sessions(character, character.at_look(character.location))
        send_browser_notice_event(
            character,
            f"|yYou break away from the fight and fall back to {destination.key}.|n",
            title="Flee",
            tone="warn",
            icon="directions_run",
            duration_ms=4200,
        )

    def _execute_item(self, character, action):
        from world.activities import _consume_item_by_template

        template_id = action.get("item")
        item = ITEM_TEMPLATES.get(template_id, {})
        use = get_item_use_profile(item, context="combat") or {}
        target = None
        if use.get("target") == "enemy":
            target = self.get_enemy(action.get("target")) if action.get("target") else self._default_enemy_target()
        elif use.get("target") == "ally":
            target = self._get_participant_target(action.get("target")) if action.get("target") else character
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
                else:
                    self._emit_defend_fx(character, character, text=item.get("name", "GUARD"))
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
        tick_ms = self._atb_tick_ms()
        state = tick_atb_state(self._get_actor_atb_state(character=character), tick_ms=tick_ms)
        if state.get("phase") == "ready":
            action = self._consume_player_pending_action(character)
            state = start_atb_action(state, action, self._player_action_timing(action), tick_ms=tick_ms)
        if state.get("phase") == "resolving":
            action = dict(state.get("current_action") or {"kind": "attack", "target": None})
            self._resolve_player_action(character, action)
            state = finish_atb_action(state, tick_ms=tick_ms)
        self._save_actor_atb_state(state, character=character)

    def _choose_companion_target(self, companion):
        """Return the best enemy target for an auto-battling ranger companion."""

        enemies = list(self.get_active_enemies())
        if not enemies:
            return None
        companion_key = str(companion.get("companion_key") or "").lower()
        if companion_key == "ash_hawk":
            marked = [enemy for enemy in enemies if enemy.get("marked_turns", 0) > 0]
            if marked:
                return min(marked, key=lambda enemy: (enemy.get("hp", 0), enemy.get("id")))
        if companion_key == "briar_boar":
            unbound = [enemy for enemy in enemies if enemy.get("bound_turns", 0) <= 0]
            if unbound:
                return min(unbound, key=lambda enemy: (enemy.get("hp", 0), enemy.get("id")))
        marked = [enemy for enemy in enemies if enemy.get("marked_turns", 0) > 0]
        if marked:
            return min(marked, key=lambda enemy: (enemy.get("hp", 0), enemy.get("id")))
        return min(enemies, key=lambda enemy: (enemy.get("hp", 0), enemy.get("id")))

    def _execute_companion_turn(self, companion):
        """Resolve one ranger companion auto-battle turn."""

        enemy = self._choose_companion_target(companion)
        if not enemy:
            return
        companion_definition = get_companion(companion.get("companion_key"))
        action_label = (
            dict((companion_definition or {}).get("combat") or {}).get("label")
            or companion.get("key")
            or "Companion Attack"
        )
        self._announce_combat_action(companion, action_label)
        derived = self._get_effective_derived(companion)
        if not self._roll_hit(derived["accuracy"], enemy["dodge"]):
            self.obj.msg_contents(f"{companion['key']} misses {enemy['key']}.")
            self._emit_miss_fx(companion, enemy)
            self._add_threat(companion, 1)
            return

        companion_key = str(companion.get("companion_key") or "").lower()
        bonus = 1
        extra_text = ""
        if companion_key == "marsh_hound":
            if enemy.get("marked_turns", 0) > 0:
                bonus += 3
                extra_text = " The hound worries the marked prey without letting it settle."
            damage = self._weapon_damage(derived["attack_power"], enemy["armor"], bonus=bonus)
            self._damage_enemy(companion, enemy, damage, extra_text=extra_text)
            if enemy.get("hp", 0) > 0 and enemy.get("marked_turns", 0) > 0:
                self._apply_enemy_bleed(enemy, turns=2, damage=2, message=f"|r{companion['key']} opens fresh cuts across {enemy['key']}!|n")
            return
        if companion_key == "ash_hawk":
            if enemy.get("marked_turns", 0) <= 0:
                enemy["marked_turns"] = max(enemy.get("marked_turns", 0), 2)
                self._save_enemy(enemy)
                extra_text = " The hawk wheels overhead and opens the line."
            else:
                enemy["marked_turns"] = max(enemy.get("marked_turns", 0), 3)
                self._save_enemy(enemy)
                bonus += 2
                extra_text = " The hawk keeps the quarry cleanly marked from above."
            damage = self._weapon_damage(derived["attack_power"], enemy["armor"], bonus=bonus)
            self._damage_enemy(companion, enemy, damage, extra_text=extra_text)
            return
        if companion_key == "briar_boar":
            if enemy.get("bound_turns", 0) <= 0:
                enemy["bound_turns"] = max(enemy.get("bound_turns", 0), 1)
                self._save_enemy(enemy)
                bonus += 2
                extra_text = " The boar crashes through the line and pins the target in bad footing."
            elif enemy.get("marked_turns", 0) > 0:
                bonus += 3
                extra_text = " The boar drives straight through the marked gap."
            damage = self._weapon_damage(derived["attack_power"], enemy["armor"], bonus=bonus)
            self._damage_enemy(companion, enemy, damage, extra_text=extra_text)
            return
        damage = self._weapon_damage(derived["attack_power"], enemy["armor"], bonus=bonus)
        self._damage_enemy(companion, enemy, damage)

    def _advance_companion_atb(self, companion):
        """Tick and resolve ATB for one ranger companion."""

        tick_ms = self._atb_tick_ms()
        state = tick_atb_state(self._get_actor_atb_state(companion=companion), tick_ms=tick_ms)
        if state.get("phase") == "ready":
            state = start_atb_action(
                state,
                {"kind": "companion_attack", "companion_id": companion["id"], "label": companion["key"]},
                normalize_atb_profile({"windup_ticks": 0, "recovery_ticks": 1, "interruptible": False}),
                tick_ms=tick_ms,
            )
        if state.get("phase") == "resolving":
            self._execute_companion_turn(companion)
            state = finish_atb_action(state, tick_ms=tick_ms)
        self._save_actor_atb_state(state, companion=companion)

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
                    (participant.get("hp", 0) if _is_companion_actor(participant) else (participant.db.brave_resources or {}).get("hp", 0)),
                    _combat_target_name(participant).lower(),
                ),
            )

        threat = self.db.threat or {}
        highest = max(threat.get(str(_ally_actor_id(participant)), 0) for participant in participants)
        candidates = [
            participant
            for participant in participants
            if threat.get(str(_ally_actor_id(participant)), 0) == highest
        ]
        return random.choice(candidates) if candidates else participants[0]

    def _execute_enemy_turn(self, enemy):
        from world.combat_enemy_turns import execute_enemy_turn

        return execute_enemy_turn(self, enemy)

    def _advance_enemy_atb(self, enemy):
        tick_ms = self._atb_tick_ms()
        state = tick_atb_state(self._get_actor_atb_state(enemy=enemy), tick_ms=tick_ms)
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
            if state.get("phase") == "winding":
                timing = dict(state.get("timing") or {})
                if timing.get("telegraph"):
                    self._record_telegraph_outcome(enemy, "pending", label=action["label"])
                self.obj.msg_contents(self._enemy_telegraph_message(enemy))
        if state.get("phase") == "resolving":
            self._execute_enemy_turn(enemy)
            state = finish_atb_action(state, tick_ms=tick_ms)
        self._save_actor_atb_state(state, enemy=enemy)

    def _defeat_companion(self, companion):
        """Drop a ranger companion out of the current fight."""

        self._emit_defeat_fx(companion)
        self.obj.msg_contents(f"{companion['key']} is driven out of the fight.")
        self._remove_companion(companion, refresh=False)

    def _clear_round_states(self):
        states = dict(self.db.participant_states or {})
        for participant_key, state in states.items():
            state["guard"] = 0
            self._clear_reaction_state(state)
            if state.get("sacred_aegis_turns", 0) > 0:
                state["sacred_aegis_turns"] = max(0, state["sacred_aegis_turns"] - 1)
                if state["sacred_aegis_turns"] <= 0:
                    state["sacred_aegis_source"] = None
                    state["sacred_aegis_power"] = 0
            if state.get("grove_turns", 0) > 0:
                state["grove_turns"] = max(0, state["grove_turns"] - 1)
            if state.get("primal_form_turns", 0) > 0:
                state["primal_form_turns"] = max(0, state["primal_form_turns"] - 1)
                if state["primal_form_turns"] <= 0:
                    state["primal_form"] = None
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
            enemy["judged_turns"] = max(0, enemy.get("judged_turns", 0) - 1)
            enemies.append(enemy)
        self.db.enemies = enemies

    def _award_companion_bond_progress(self):
        """Award persistent bond XP to companions that meaningfully fought."""

        progress = {}
        contributions = dict(self.db.participant_contributions or {})
        for contribution in contributions.values():
            owner_id = contribution.get("owner_id")
            companion_key = str(contribution.get("companion_key") or "").lower()
            meaningful = int(contribution.get("meaningful_actions", 0) or 0)
            if not owner_id or not companion_key or meaningful <= 0:
                continue
            owner = self._get_character(owner_id)
            if not owner or not hasattr(owner, "award_companion_bond_xp"):
                continue
            if not self._participant_reward_eligible(owner):
                continue
            damage_done = int(contribution.get("damage_done", 0) or 0)
            utility_points = int(contribution.get("utility_points", 0) or 0)
            xp_gain = min(3, max(1, meaningful) + (1 if damage_done >= 10 else 0) + (1 if utility_points >= 2 else 0))
            messages = owner.award_companion_bond_xp(companion_key, xp_gain)
            owner_messages = progress.setdefault(owner.id, [])
            companion_name = contribution.get("companion_name") or companion_key.replace("_", " ").title()
            owner_messages.append(f"{companion_name} bond +{xp_gain} XP.")
            owner_messages.extend(messages)
        return progress

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
        reward_entries = [(participant.id, 1.0) for participant in eligible]
        xp_shares = self._allocate_weighted_pool(xp_total, reward_entries, minimum=1)

        reward_bundles = [roll_enemy_rewards(enemy) for enemy in (self.db.enemies or [])]
        silver_total = sum(bundle["silver"] for bundle in reward_bundles)
        silver_shares = self._allocate_weighted_pool(silver_total, reward_entries)
        reward_items = []
        for bundle in reward_bundles:
            reward_items.extend(bundle["items"])
        item_shares = self._distribute_reward_items(reward_items, reward_entries)
        companion_progress = self._award_companion_bond_progress()

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
            progress_messages.extend(companion_progress.get(participant.id, []))

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
            if hasattr(participant, "ndb"):
                participant.ndb.brave_showing_combat_result = True
            participant.clear_chapel_blessing()

        return participants

    def _finish_victory_sequence(self, room_message, *, exclude_rewarded=True):
        """Deliver victory rewards and stop after combat FX have played."""

        if hasattr(self, "ndb"):
            self.ndb.brave_victory_pending = False
        rewarded = self._reward_victory()
        if self.obj and room_message:
            from world.browser_panels import broadcast_room_text_non_web

            kwargs = {"exclude": rewarded} if exclude_rewarded else {}
            broadcast_room_text_non_web(self.obj, room_message, **kwargs)
        if hasattr(self, "ndb"):
            self.ndb.brave_skip_combat_done = True
        self.stop()

    def _schedule_victory_sequence(self, room_message, *, exclude_rewarded=True):
        """Wait for final defeat FX before swapping away from combat."""

        if getattr(getattr(self, "ndb", None), "brave_victory_pending", False):
            return
        if hasattr(self, "ndb"):
            self.ndb.brave_victory_pending = True
        delay(
            COMBAT_FINISH_FX_DELAY,
            self._finish_victory_sequence,
            room_message,
            exclude_rewarded=exclude_rewarded,
            persistent=False,
        )

    def _finish_party_defeat(self, room_message):
        """Resolve a full party defeat with explicit cleanup and recovery messaging."""

        from world.browser_panels import send_browser_notice_event

        if self.obj and room_message:
            self.obj.msg_contents(room_message)
        for participant in self.get_defeated_participants():
            send_browser_notice_event(
                participant,
                "|rThe whole line breaks. Regroup, catch your breath, and choose when to return.|n",
                title="Party Defeated",
                tone="danger",
                icon="warning",
                duration_ms=5600,
            )
        self.stop()

    def at_repeat(self):
        self.db.round += 1
        active_participants = self.get_active_player_participants()
        active_enemies = self.get_active_enemies()

        if not active_participants:
            self._finish_party_defeat("|rThe fight breaks wrong, and the danger keeps the road.|n")
            return
        if not active_enemies:
            self._schedule_victory_sequence("|gThe last of them falls. The way is clear for now.|n")
            return

        self._apply_participant_effects()
        if not self.get_active_player_participants():
            self._finish_party_defeat("|rThe line breaks and the party is driven back toward town.|n")
            return
        self._apply_enemy_effects()
        if not self.get_active_enemies():
            self._schedule_victory_sequence("|gThe last of them falls. The way is clear for now.|n")
            return

        active_participants = self.get_active_player_participants()
        for participant in active_participants:
            self._advance_player_atb(participant)
        if not self.get_active_player_participants():
            self._finish_party_defeat("|rThe fight ends with the road still dangerous.|n")
            return
        if not self.get_active_enemies():
            self._schedule_victory_sequence("|gThe encounter is over. The road is clear for now.|n")
            return

        for companion in self.get_active_companions():
            self._advance_companion_atb(companion)
        if not self.get_active_enemies():
            self._schedule_victory_sequence("|gThe encounter is over. The road is clear for now.|n")
            return

        for enemy in self.get_active_enemies():
            self._advance_enemy_atb(enemy)
        if not self.get_active_player_participants():
            self._finish_party_defeat("|rThe party is driven back toward town.|n")
            return

        self._clear_round_states()
        self._refresh_browser_combat_views()
