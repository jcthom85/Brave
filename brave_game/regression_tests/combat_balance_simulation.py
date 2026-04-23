import argparse
import hashlib
import json
import os
import random
import time
from pathlib import Path
from statistics import mean
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import CHARACTER_CONTENT
from typeclasses.scripts import ABILITY_LIBRARY, BraveEncounter
from world.combat_atb import create_atb_state, finish_atb_action, get_ability_atb_profile, start_atb_action, tick_atb_state
from world.content import get_content_registry


CONTENT = get_content_registry()
ENCOUNTER_CONTENT = CONTENT.encounters
DEFAULT_LEVEL = 10
DEFAULT_RACE = CHARACTER_CONTENT.starting_race
DEFAULT_OUTPUT_DIR = Path("/home/jcthom85/Brave/tmp/combat-simulation")
TELEGRAPH_RESPONSE_ABILITIES = {
    "shieldbash",
    "intercept",
    "guardianlight",
    "sanctuary",
    "frostbind",
    "manashield",
    "evasiveroll",
}
INTERRUPT_RESPONSE_ABILITIES = {
    "warrior": "shieldbash",
    "mage": "frostbind",
}

PARTY_SCENARIOS = (
    {
        "key": "solo_warrior",
        "label": "Solo Warrior",
        "members": ("warrior",),
        "companions": {},
    },
    {
        "key": "duo_warrior_cleric",
        "label": "Duo Warrior+Cleric",
        "members": ("warrior", "cleric"),
        "companions": {},
    },
    {
        "key": "trio_warrior_cleric_mage",
        "label": "Trio Warrior+Cleric+Mage",
        "members": ("warrior", "cleric", "mage"),
        "companions": {},
    },
    {
        "key": "full_party",
        "label": "Full Party",
        "members": ("warrior", "cleric", "mage", "ranger"),
        "companions": {"ranger": "marsh_hound"},
    },
    {
        "key": "solo_ranger_no_companion",
        "label": "Solo Ranger",
        "members": ("ranger",),
        "companions": {"ranger": None},
    },
    {
        "key": "solo_ranger_with_companion",
        "label": "Solo Ranger + Companion",
        "members": ("ranger",),
        "companions": {"ranger": "marsh_hound"},
    },
)


def _ability_key(name):
    return CHARACTER_CONTENT.ability_key(name)


def _resource_key_for_class(class_key):
    return "mana" if class_key in {"cleric", "mage", "druid"} else "stamina"


def _seed_to_int(*parts):
    payload = "::".join(str(part) for part in parts)
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16], 16)


def classify_encounter_rank(encounter_data):
    enemy_keys = list(encounter_data.get("enemies") or [])
    max_rank = 1
    tags = set()
    for template_key in enemy_keys:
        template = ENCOUNTER_CONTENT.get_enemy_template(template_key) or {}
        tags.update(str(tag).lower() for tag in (template.get("tags") or []))
        max_rank = max(max_rank, ENCOUNTER_CONTENT.get_enemy_rank(template_key, template))
    if "boss" in tags:
        return "boss", max_rank
    if tags.intersection({"elite", "captain", "commander"}):
        return "elite", max_rank
    return "normal", max_rank


def collect_authored_encounters():
    authored = []
    for room_id, encounters in sorted(ENCOUNTER_CONTENT.room_encounters.items()):
        for encounter_data in encounters:
            authored.append(
                {
                    "source": f"room:{room_id}",
                    "source_kind": "room",
                    "room_id": room_id,
                    "encounter_data": dict(encounter_data),
                }
            )
    for party_key, roaming in sorted(ENCOUNTER_CONTENT.roaming_parties.items()):
        encounter_data = dict((roaming or {}).get("encounter") or {})
        if not encounter_data:
            continue
        authored.append(
            {
                "source": f"roaming:{party_key}",
                "source_kind": "roaming",
                "room_id": str(roaming.get("start_room") or ""),
                "encounter_data": encounter_data,
            }
        )
    return authored


class DummyRoom:
    def __init__(self, key):
        self.key = key
        self.db = SimpleNamespace(brave_resonance="fantasy")
        self.ndb = SimpleNamespace(brave_encounter=None)
        self.messages = []

    def msg_contents(self, message, **_kwargs):
        self.messages.append(str(message))


class SimulatedCharacter:
    def __init__(self, char_id, class_key, *, race_key=DEFAULT_RACE, level=DEFAULT_LEVEL, companion_key=None):
        self.id = char_id
        self.key = f"{class_key.title()} {char_id}"
        self.location = None
        self.messages = []
        self.ndb = SimpleNamespace(brave_encounter=None)
        self.db = SimpleNamespace(
            brave_race=race_key,
            brave_class=class_key,
            brave_level=int(level),
            brave_xp=0,
            brave_primary_stats={},
            brave_derived_stats={},
            brave_resources={},
            brave_inventory=[],
            brave_learned_abilities=[],
            brave_ability_mastery={},
            brave_active_companion=companion_key or "",
            brave_companions=[companion_key] if companion_key else [],
            brave_companion_bonds={companion_key: {"xp": 0}} if companion_key else {},
            brave_active_oath="",
            brave_paladin_oaths=[],
            brave_chapel_blessing={},
            brave_meal_buff={},
            brave_equipment={},
            brave_gender="neutral",
        )
        self.recalculate_stats(restore=True)

    def msg(self, message):
        self.messages.append(str(message))

    def ensure_brave_character(self):
        return None

    def get_learned_abilities(self):
        return []

    def get_unlocked_abilities(self):
        class_data = CHARACTER_CONTENT.classes[self.db.brave_class]
        level = int(self.db.brave_level or 1)
        return [ability for unlock_level, ability in class_data["progression"] if unlock_level <= level]

    def get_ability_mastery_rank(self, ability_key):
        return max(1, int((self.db.brave_ability_mastery or {}).get(_ability_key(ability_key), 1) or 1))

    def get_companion_bond_state(self, companion_key):
        state = dict((self.db.brave_companion_bonds or {}).get(str(companion_key or "").lower(), {}) or {})
        return {"xp": int(state.get("xp", 0) or 0)}

    def get_active_companion(self):
        from world.ranger_companions import get_companion

        companion_key = str(self.db.brave_active_companion or "").lower()
        if not companion_key:
            return {}
        payload = dict(get_companion(companion_key, self.get_companion_bond_state(companion_key)) or {})
        if not payload:
            return {}
        payload["key"] = companion_key
        return payload

    def award_companion_bond_xp(self, companion_key, amount):
        bonds = dict(self.db.brave_companion_bonds or {})
        key = str(companion_key or "").lower()
        current = dict(bonds.get(key, {}) or {})
        current["xp"] = int(current.get("xp", 0) or 0) + max(0, int(amount or 0))
        bonds[key] = current
        self.db.brave_companion_bonds = bonds
        return []

    def clear_chapel_blessing(self):
        self.db.brave_chapel_blessing = {}

    def restore_resources(self):
        derived = dict(self.db.brave_derived_stats or {})
        self.db.brave_resources = {
            "hp": int(derived.get("max_hp", 1) or 1),
            "mana": int(derived.get("max_mana", 0) or 0),
            "stamina": int(derived.get("max_stamina", 0) or 0),
        }

    def move_to(self, destination, quiet=True, move_type="move"):
        self.location = destination
        return True

    def recalculate_stats(self, restore=False):
        race = CHARACTER_CONTENT.races[self.db.brave_race]
        class_data = CHARACTER_CONTENT.classes[self.db.brave_class]
        level = max(1, min(int(self.db.brave_level or 1), CHARACTER_CONTENT.max_level))
        passive_bonuses = CHARACTER_CONTENT.get_passive_ability_bonuses(self.db.brave_class, level)
        race_perk_bonuses = dict(race.get("perk_bonuses", {}))

        primary = {}
        for stat in CHARACTER_CONTENT.primary_stats:
            primary[stat] = class_data["base_stats"].get(stat, 0) + race["bonuses"].get(stat, 0) + passive_bonuses.get(stat, 0)

        derived = {
            "max_hp": 55 + (primary["vitality"] * 10) + (level * 8),
            "max_mana": 12 + (primary["intellect"] + primary["spirit"]) * 5 + (level * 4),
            "max_stamina": 24 + (primary["strength"] + primary["agility"] + primary["vitality"]) * 3 + (level * 5),
            "attack_power": primary["strength"] * 2 + primary["agility"] + (level * 2),
            "spell_power": primary["intellect"] * 2 + primary["spirit"] + (level * 2),
            "armor": primary["vitality"] * 2 + primary["strength"] + level,
            "accuracy": 65 + primary["agility"] * 2 + level,
            "precision": primary["agility"] * 2 + (level // 2),
            "crit_chance": 5 + (primary["agility"] // 2),
            "dodge": 3 + primary["agility"] + (level // 2),
            "threat": 5 + primary["vitality"] + (5 if self.db.brave_class in {"warrior", "paladin"} else 0),
            "healing_power": 0,
        }
        for stat, bonus in race_perk_bonuses.items():
            if stat not in CHARACTER_CONTENT.primary_stats:
                derived[stat] = derived.get(stat, 0) + bonus
        for stat, bonus in passive_bonuses.items():
            if stat not in CHARACTER_CONTENT.primary_stats:
                derived[stat] = derived.get(stat, 0) + bonus

        self.db.brave_primary_stats = primary
        self.db.brave_derived_stats = derived

        if restore or not self.db.brave_resources:
            self.restore_resources()
        return primary, derived


METHOD_NAMES = (
    "configure",
    "_companion_state_template",
    "_get_scaling_profile",
    "_atb_tick_ms",
    "_default_atb_fill_rate",
    "_actor_atb_key",
    "_clear_actor_atb_state",
    "_player_action_timing",
    "_enemy_action_timing",
    "_enemy_action_label",
    "get_player_participants",
    "get_defeated_participants",
    "get_registered_participants",
    "get_active_player_participants",
    "_get_companion",
    "get_active_companions",
    "_save_companion",
    "_spawn_ranger_companion",
    "_remove_companion",
    "_boss_credit_open",
    "_get_participant_contribution",
    "_save_participant_contribution",
    "_record_participant_contribution",
    "_participant_reward_eligible",
    "_participant_impact_score",
    "_announce_combat_action",
    "_enemy_reaction_state",
    "_set_enemy_recovery_state",
    "_apply_reaction_guard",
    "_clear_reaction_state",
    "_try_interrupt_enemy_action",
    "_get_participant_state",
    "_save_participant_state",
    "_save_enemy",
    "_spawn_enemy",
    "_add_threat",
    "_roll_hit",
    "_weapon_damage",
    "_spell_damage",
    "_spend_resource",
    "_get_effective_derived",
    "_consume_feint_bonus",
    "_scaled_heal_amount",
    "_consume_stealth_bonus",
    "_damage_enemy",
    "_heal_character",
    "_heal_enemy",
    "_apply_bleed",
    "_apply_curse",
    "_apply_poison",
    "_apply_enemy_bleed",
    "_apply_enemy_poison",
    "_apply_snare",
    "_clear_one_harmful_effect",
    "_apply_participant_effects",
    "_apply_enemy_effects",
    "_mark_defeated_participant",
    "get_active_participants",
    "get_enemy",
    "get_active_enemies",
    "find_enemy",
    "find_participant",
    "_get_participant_target",
    "remove_participant",
    "_default_enemy_target",
    "_find_wounded_enemy",
    "_execute_basic_attack",
    "_execute_ability",
    "_consume_player_pending_action",
    "_resolve_player_action",
    "_choose_companion_target",
    "_execute_companion_turn",
    "_choose_enemy_target",
    "_handle_enemy_specials",
    "_execute_enemy_turn",
    "_defeat_companion",
    "_clear_round_states",
)


class SimulationEncounter:
    interval = 0.25

    def __init__(self, room, encounter_data, *, expected_party_size, seed):
        self.obj = room
        self.db = SimpleNamespace()
        self.ndb = SimpleNamespace(brave_victory_pending=False, brave_skip_combat_done=False)
        self._characters = {}
        self._seed = int(seed)
        self._now_ms = int(round(time.time() * 1000))
        self.ended = False
        self.outcome = "active"
        self.victory_message = ""
        self.telemetry = {
            "telegraphed_actions": 0,
            "telegraphed_interrupts": 0,
            "telegraphed_response_actions": 0,
            "held_actions": 0,
            "combat_fx_events": 0,
        }
        self.configure(room.key, encounter_data, expected_party_size=expected_party_size)

    def _get_character(self, dbref):
        return self._characters.get(int(dbref)) if str(dbref).isdigit() else None

    def _refresh_browser_combat_views(self, participants=None):
        return None

    def _clear_browser_combat_views(self, participants=None):
        return None

    def _get_actor_atb_state(self, character=None, enemy=None, companion=None):
        states = dict(self.db.atb_states or {})
        key = self._actor_atb_key(character=character, enemy=enemy, companion=companion)
        if key not in states:
            states[key] = create_atb_state(
                fill_rate=self._default_atb_fill_rate(character=character, enemy=enemy, companion=companion),
                tick_ms=self._atb_tick_ms(),
                phase_started_at_ms=self._now_ms,
            )
            self.db.atb_states = states
        return states[key]

    def _save_actor_atb_state(self, state, *, character=None, enemy=None, companion=None):
        states = dict(self.db.atb_states or {})
        key = self._actor_atb_key(character=character, enemy=enemy, companion=companion)
        normalized = dict(state or {})
        normalized.setdefault("phase_started_at_ms", self._now_ms)
        states[key] = create_atb_state(**normalized, tick_ms=self._atb_tick_ms())
        self.db.atb_states = states

    def _emit_combat_fx(self, **event):
        self.telemetry["combat_fx_events"] += 1
        return event

    def _emit_miss_fx(self, source, target, text="MISS"):
        self.telemetry["combat_fx_events"] += 1
        return {"kind": "miss", "text": text}

    def _emit_defeat_fx(self, target, text="DOWN"):
        self.telemetry["combat_fx_events"] += 1
        return {"kind": "defeat", "text": text}

    def _schedule_victory_sequence(self, room_message, *, exclude_rewarded=True):
        self.victory_message = str(room_message or "")
        self.outcome = "victory"
        self.ended = True
        self.ndb.brave_victory_pending = True

    def _award_enemy_defeat_credit(self, enemy):
        return None

    def stop(self):
        if self.outcome == "active":
            if self.get_active_enemies():
                self.outcome = "defeat"
            else:
                self.outcome = "victory"
        self.ended = True

    def _defeat_character(self, character):
        self._emit_defeat_fx(character)
        resources = dict(character.db.brave_resources or {})
        resources["hp"] = 0
        character.db.brave_resources = resources
        self._mark_defeated_participant(character)
        self.remove_participant(character, refresh=False)

    def _enemy_telegraph_message(self, enemy):
        self.telemetry["telegraphed_actions"] += 1
        return BraveEncounter._enemy_telegraph_message(self, enemy)

    def _try_interrupt_enemy_action(self, character, enemy, tool_label):
        interrupted = BraveEncounter._try_interrupt_enemy_action(self, character, enemy, tool_label)
        if interrupted:
            self.telemetry["telegraphed_interrupts"] += 1
        return interrupted

    def _advance_player_atb(self, character):
        tick_ms = self._atb_tick_ms()
        state = tick_atb_state(self._get_actor_atb_state(character=character), tick_ms=tick_ms, now_ms=self._now_ms)
        if state.get("phase") == "ready":
            pending = dict(self.db.pending_actions or {})
            held_action = pending.get(str(character.id))
            if held_action and held_action.get("kind") == "hold":
                self._save_actor_atb_state(state, character=character)
                return
            action = self._consume_player_pending_action(character)
            state = start_atb_action(
                state,
                action,
                self._player_action_timing(action),
                tick_ms=tick_ms,
                now_ms=self._now_ms,
            )
        if state.get("phase") == "resolving":
            action = dict(state.get("current_action") or {"kind": "attack", "target": None})
            self._resolve_player_action(character, action)
            state = finish_atb_action(state, tick_ms=tick_ms, now_ms=self._now_ms)
        self._save_actor_atb_state(state, character=character)

    def _advance_companion_atb(self, companion):
        tick_ms = self._atb_tick_ms()
        state = tick_atb_state(self._get_actor_atb_state(companion=companion), tick_ms=tick_ms, now_ms=self._now_ms)
        if state.get("phase") == "ready":
            state = start_atb_action(
                state,
                {"kind": "companion_attack", "companion_id": companion["id"], "label": companion["key"]},
                {"windup_ticks": 0, "recovery_ticks": 1, "interruptible": False},
                tick_ms=tick_ms,
                now_ms=self._now_ms,
            )
        if state.get("phase") == "resolving":
            self._execute_companion_turn(companion)
            state = finish_atb_action(state, tick_ms=tick_ms, now_ms=self._now_ms)
        self._save_actor_atb_state(state, companion=companion)

    def _advance_enemy_atb(self, enemy):
        tick_ms = self._atb_tick_ms()
        state = tick_atb_state(self._get_actor_atb_state(enemy=enemy), tick_ms=tick_ms, now_ms=self._now_ms)
        if state.get("phase") == "ready":
            state = start_atb_action(
                state,
                {"kind": "enemy_attack", "enemy_id": enemy["id"], "label": self._enemy_action_label(enemy)},
                self._enemy_action_timing(enemy),
                tick_ms=tick_ms,
                now_ms=self._now_ms,
            )
            if state.get("phase") == "winding":
                self.obj.msg_contents(self._enemy_telegraph_message(enemy))
        if state.get("phase") == "resolving":
            self._execute_enemy_turn(enemy)
            state = finish_atb_action(state, tick_ms=tick_ms, now_ms=self._now_ms)
        self._save_actor_atb_state(state, enemy=enemy)

    def at_repeat(self):
        self._now_ms += self._atb_tick_ms()
        return BraveEncounter.at_repeat(self)

    def add_simulated_participant(self, character):
        character.location = self.obj
        self._characters[character.id] = character
        self.db.participants = list(self.db.participants or []) + [character.id]
        states = dict(self.db.participant_states or {})
        states[str(character.id)] = self._companion_state_template()
        self.db.participant_states = states
        self._save_actor_atb_state(
            {"fill_rate": self._default_atb_fill_rate(character=character)},
            character=character,
        )
        threat = dict(self.db.threat or {})
        threat[str(character.id)] = threat.get(str(character.id), 0)
        self.db.threat = threat
        self._get_participant_contribution(character)
        self._spawn_ranger_companion(character, announce=False)


for method_name in METHOD_NAMES:
    setattr(SimulationEncounter, method_name, getattr(BraveEncounter, method_name))


def _current_actor_phase(encounter, character):
    state = encounter._get_actor_atb_state(character=character)
    return str((state or {}).get("phase") or "")


def _can_use(character, ability_key):
    ability = ABILITY_LIBRARY.get(ability_key)
    if not ability:
        return False
    unlocked = {_ability_key(name) for name in character.get_unlocked_abilities()}
    if ability_key not in unlocked:
        return False
    resource_key = ability.get("resource")
    current = int((character.db.brave_resources or {}).get(resource_key, 0) or 0)
    return current >= int(ability.get("cost", 0) or 0)


def _choose_enemy_for_mark(encounter):
    enemies = encounter.get_active_enemies()
    return max(enemies, key=lambda enemy: (enemy.get("hp", 0), enemy.get("id"))) if enemies else None


def _actor_hp_ratio(actor):
    if isinstance(actor, dict):
        return (actor.get("hp", 0) / max(1, actor.get("max_hp", 1)))
    return ((actor.db.brave_resources or {}).get("hp", 0) / max(1, actor.db.brave_derived_stats.get("max_hp", 1)))


def _actor_id(actor):
    if isinstance(actor, dict):
        return str(actor.get("id"))
    return str(getattr(actor, "id", ""))


def _snapshot_actor_state(encounter, actor, *, actor_type):
    if actor_type == "player":
        atb = encounter._get_actor_atb_state(character=actor)
        resources = dict(actor.db.brave_resources or {})
        return {
            "id": actor.id,
            "key": actor.key,
            "class": actor.db.brave_class,
            "hp": int(resources.get("hp", 0) or 0),
            "max_hp": int(actor.db.brave_derived_stats.get("max_hp", 1) or 1),
            "phase": str((atb or {}).get("phase") or ""),
            "ticks_remaining": int((atb or {}).get("ticks_remaining", 0) or 0),
            "current_action": dict((atb or {}).get("current_action") or {}),
            "pending_action": dict((encounter.db.pending_actions or {}).get(str(actor.id)) or {}),
        }
    atb = encounter._get_actor_atb_state(enemy=actor)
    return {
        "id": actor.get("id"),
        "key": actor.get("key"),
        "template_key": actor.get("template_key"),
        "hp": int(actor.get("hp", 0) or 0),
        "max_hp": int(actor.get("max_hp", 1) or 1),
        "phase": str((atb or {}).get("phase") or ""),
        "ticks_remaining": int((atb or {}).get("ticks_remaining", 0) or 0),
        "current_action": dict((atb or {}).get("current_action") or {}),
    }


def _trace_snapshot(encounter):
    telegraphed_enemy, telegraph_state = _telegraphed_enemy_state(encounter)
    return {
        "round": int(encounter.db.round or 0),
        "outcome": encounter.outcome,
        "pending_actions": {
            str(actor_id): dict(action or {})
            for actor_id, action in dict(encounter.db.pending_actions or {}).items()
        },
        "players": [
            _snapshot_actor_state(encounter, actor, actor_type="player")
            for actor in encounter.get_player_participants()
        ],
        "companions": [
            {
                "id": companion.get("id"),
                "key": companion.get("key"),
                "owner_id": companion.get("owner_id"),
                "hp": int(companion.get("hp", 0) or 0),
                "max_hp": int(companion.get("max_hp", 1) or 1),
                "phase": str((encounter._get_actor_atb_state(companion=companion) or {}).get("phase") or ""),
                "ticks_remaining": int((encounter._get_actor_atb_state(companion=companion) or {}).get("ticks_remaining", 0) or 0),
            }
            for companion in (encounter.db.companions or [])
        ],
        "enemies": [
            _snapshot_actor_state(encounter, enemy, actor_type="enemy")
            for enemy in (encounter.db.enemies or [])
        ],
        "telegraph": {
            "enemy_id": telegraphed_enemy.get("id") if telegraphed_enemy else None,
            "enemy_key": telegraphed_enemy.get("key") if telegraphed_enemy else None,
            "phase": telegraph_state.get("phase") if telegraph_state else None,
            "interruptible": bool(telegraph_state.get("interruptible")) if telegraph_state else False,
            "ticks_remaining": int((telegraph_state.get("atb_state") or {}).get("ticks_remaining", 0) or 0) if telegraph_state else 0,
        },
        "telemetry": dict(encounter.telemetry),
        "messages_tail": list(encounter.obj.messages[-8:]),
    }


def analyze_trace(trace):
    """Summarize telegraph windows against interrupt readiness from one trace log."""

    if not trace:
        return {"telegraph_windows": [], "interrupt_windows": []}

    telegraph_windows = []
    current_window = None
    interrupt_windows = []

    for snapshot in trace:
        telegraph = dict(snapshot.get("telegraph") or {})
        players = list(snapshot.get("players") or [])
        enemy_id = telegraph.get("enemy_id")

        if enemy_id:
            if current_window is None or current_window.get("enemy_id") != enemy_id:
                current_window = {
                    "enemy_id": enemy_id,
                    "enemy_key": telegraph.get("enemy_key"),
                    "round_started": snapshot.get("round"),
                    "round_ended": snapshot.get("round"),
                    "interruptible": bool(telegraph.get("interruptible")),
                    "ticks": [],
                }
                telegraph_windows.append(current_window)
            current_window["round_ended"] = snapshot.get("round")

            interrupt_actor = None
            late_interrupt_actor = None
            unavailable_reasons = []
            for player in players:
                pending = dict(player.get("pending_action") or {})
                phase = str(player.get("phase") or "")
                if pending.get("ability") in {"shieldbash", "frostbind"}:
                    if phase == "ready":
                        interrupt_actor = player["key"]
                    else:
                        late_interrupt_actor = player["key"]
                if player.get("class") in INTERRUPT_RESPONSE_ABILITIES:
                    unavailable_reasons.append(f"{player['key']}:{phase}:{player.get('ticks_remaining', 0)}")

            tick_summary = {
                "round": snapshot.get("round"),
                "telegraph_ticks_remaining": int(telegraph.get("ticks_remaining", 0) or 0),
                "interrupt_ready_actor": interrupt_actor,
                "interrupt_pending_actor": late_interrupt_actor,
                "players": [
                    {
                        "key": player.get("key"),
                        "class": player.get("class"),
                        "phase": player.get("phase"),
                        "ticks_remaining": player.get("ticks_remaining"),
                        "pending_action": dict(player.get("pending_action") or {}),
                    }
                    for player in players
                ],
                "unavailable_reasons": unavailable_reasons,
                "messages_tail": list(snapshot.get("messages_tail") or []),
            }
            current_window["ticks"].append(tick_summary)
            if interrupt_actor or late_interrupt_actor:
                interrupt_windows.append(
                    {
                        "round": snapshot.get("round"),
                        "enemy_key": telegraph.get("enemy_key"),
                        "interrupt_ready_actor": interrupt_actor,
                        "interrupt_pending_actor": late_interrupt_actor,
                    }
                )
        else:
            current_window = None

    return {
        "telegraph_windows": telegraph_windows,
        "interrupt_windows": interrupt_windows,
    }


def analyze_interrupt_opportunities(trace):
    """Summarize interrupt opportunity posture across one trace."""

    analysis = analyze_trace(trace)
    windows = analysis.get("telegraph_windows") or []
    summary = {
        "telegraph_windows": len(windows),
        "telegraph_ticks": 0,
        "interrupt_ready_ticks": 0,
        "interrupt_charging_zero_ticks": 0,
        "interrupt_recovering_ticks": 0,
        "interrupt_late_pending_ticks": 0,
        "by_enemy": {},
    }

    for window in windows:
        enemy_key = str(window.get("enemy_key") or "Unknown")
        bucket = summary["by_enemy"].setdefault(
            enemy_key,
            {
                "windows": 0,
                "ticks": 0,
                "interrupt_ready_ticks": 0,
                "interrupt_charging_zero_ticks": 0,
                "interrupt_recovering_ticks": 0,
                "interrupt_late_pending_ticks": 0,
            },
        )
        bucket["windows"] += 1
        for tick in window.get("ticks") or []:
            summary["telegraph_ticks"] += 1
            bucket["ticks"] += 1
            if tick.get("interrupt_pending_actor"):
                summary["interrupt_late_pending_ticks"] += 1
                bucket["interrupt_late_pending_ticks"] += 1

            for player in tick.get("players") or []:
                if player.get("class") not in INTERRUPT_RESPONSE_ABILITIES:
                    continue
                phase = str(player.get("phase") or "")
                ticks_remaining = int(player.get("ticks_remaining", 0) or 0)
                if phase == "ready":
                    summary["interrupt_ready_ticks"] += 1
                    bucket["interrupt_ready_ticks"] += 1
                elif phase == "charging" and ticks_remaining == 0:
                    summary["interrupt_charging_zero_ticks"] += 1
                    bucket["interrupt_charging_zero_ticks"] += 1
                elif phase == "recovering":
                    summary["interrupt_recovering_ticks"] += 1
                    bucket["interrupt_recovering_ticks"] += 1

    return summary


def build_interrupt_opportunity_report(opportunity_runs):
    report = {
        "totals": {
            "traces": len(opportunity_runs),
            "telegraph_windows": 0,
            "telegraph_ticks": 0,
            "interrupt_ready_ticks": 0,
            "interrupt_charging_zero_ticks": 0,
            "interrupt_recovering_ticks": 0,
            "interrupt_late_pending_ticks": 0,
        },
        "by_trace": {},
    }
    for entry in opportunity_runs:
        trace_key = f"{entry['encounter_key']}__{entry['scenario_key']}"
        summary = dict(entry["summary"])
        report["by_trace"][trace_key] = summary
        for key in report["totals"]:
            if key == "traces":
                continue
            report["totals"][key] += int(summary.get(key, 0) or 0)
    return report


def render_interrupt_opportunity_markdown(report):
    lines = [
        "# Interrupt Opportunity Summary",
        "",
        f"- Traced runs: {report['totals']['traces']}",
        f"- Telegraph windows: {report['totals']['telegraph_windows']}",
        f"- Telegraph ticks: {report['totals']['telegraph_ticks']}",
        f"- Interrupt-ready ticks: {report['totals']['interrupt_ready_ticks']}",
        f"- Charging:0 ticks: {report['totals']['interrupt_charging_zero_ticks']}",
        f"- Recovering ticks: {report['totals']['interrupt_recovering_ticks']}",
        f"- Late pending interrupt ticks: {report['totals']['interrupt_late_pending_ticks']}",
        "",
        "## By Trace",
        "",
    ]
    for trace_key, summary in sorted(report["by_trace"].items()):
        lines.append(
            f"- `{trace_key}`: windows {summary['telegraph_windows']}, ticks {summary['telegraph_ticks']}, "
            f"ready {summary['interrupt_ready_ticks']}, charging:0 {summary['interrupt_charging_zero_ticks']}, "
            f"recovering {summary['interrupt_recovering_ticks']}, late pending {summary['interrupt_late_pending_ticks']}"
        )
    lines.append("")
    return "\n".join(lines)


def _predict_enemy_target(encounter, enemy):
    participants = list(encounter.get_active_participants())
    if not participants:
        return None

    visible = [
        participant
        for participant in participants
        if encounter._get_participant_state(participant).get("stealth_turns", 0) <= 0
    ]
    if visible:
        participants = visible

    if enemy and enemy.get("target_strategy") == "lowest_hp":
        return min(
            participants,
            key=lambda participant: (
                _actor_hp_ratio(participant),
                _actor_id(participant),
            ),
        )

    threat = dict(encounter.db.threat or {})
    return max(
        participants,
        key=lambda participant: (
            int(threat.get(_actor_id(participant), 0) or 0),
            -_actor_hp_ratio(participant),
            _actor_id(participant),
        ),
    )


def _telegraphed_enemy_state(encounter):
    for enemy in encounter.get_active_enemies():
        reaction_state = encounter._enemy_reaction_state(enemy)
        if reaction_state.get("phase") == "winding" and reaction_state.get("telegraphed"):
            return enemy, reaction_state
    return None, {}


def _imminent_boss_telegraph_enemy(encounter):
    for enemy in encounter.get_active_enemies():
        if "boss" not in set(enemy.get("tags", []) or []):
            continue
        timing = encounter._enemy_action_timing(enemy)
        if not timing.get("telegraph"):
            continue
        state = encounter._get_actor_atb_state(enemy=enemy)
        phase = str((state or {}).get("phase") or "")
        ticks_remaining = int((state or {}).get("ticks_remaining", 0) or 0)
        if phase == "ready":
            return enemy
        if phase == "charging" and ticks_remaining <= 1:
            return enemy
    return None


def _ticks_until_player_resolution(encounter, character, action):
    state = encounter._get_actor_atb_state(character=character)
    phase = str((state or {}).get("phase") or "")
    if phase in {"winding", "resolving", "recovering", "cooldown"}:
        return None
    if phase == "ready":
        charge_ticks = 0
    else:
        charge_ticks = int((state or {}).get("ticks_remaining", 0) or 0)
    timing = encounter._player_action_timing(action)
    return charge_ticks + int((timing or {}).get("windup_ticks", 0) or 0)


def _hold_action():
    return {"kind": "hold"}


def _telegraph_hold_action(encounter, character):
    ability_key = INTERRUPT_RESPONSE_ABILITIES.get(character.db.brave_class)
    if not ability_key or not _can_use(character, ability_key):
        return None
    if _current_actor_phase(encounter, character) != "ready":
        return None
    imminent_enemy = _imminent_boss_telegraph_enemy(encounter)
    if not imminent_enemy:
        return None
    interrupt_action = {"kind": "ability", "ability": ability_key, "target": imminent_enemy["id"]}
    if _ticks_until_player_resolution(encounter, character, interrupt_action) is None:
        return None
    return _hold_action()


def _telegraph_response_action(encounter, character, telegraphed_enemy, predicted_target):
    class_key = character.db.brave_class
    if class_key == "warrior":
        if _can_use(character, "shieldbash"):
            return {"kind": "ability", "ability": "shieldbash", "target": telegraphed_enemy["id"]}
        if predicted_target and not isinstance(predicted_target, dict) and predicted_target.id != character.id and _can_use(character, "intercept"):
            return {"kind": "ability", "ability": "intercept", "target": predicted_target.id}
    elif class_key == "mage":
        if _can_use(character, "frostbind"):
            return {"kind": "ability", "ability": "frostbind", "target": telegraphed_enemy["id"]}
        if predicted_target is character and _can_use(character, "manashield"):
            return {"kind": "ability", "ability": "manashield", "target": character.id}
    elif class_key == "cleric":
        if predicted_target and not isinstance(predicted_target, dict) and _can_use(character, "guardianlight"):
            return {"kind": "ability", "ability": "guardianlight", "target": predicted_target.id}
        if _can_use(character, "sanctuary"):
            return {"kind": "ability", "ability": "sanctuary", "target": character.id}
    return None


def _planned_telegraph_responses(encounter):
    telegraphed_enemy, telegraph_state = _telegraphed_enemy_state(encounter)
    if not telegraphed_enemy:
        return {}
    predicted_target = _predict_enemy_target(encounter, telegraphed_enemy)
    enemy_ticks = int((telegraph_state or {}).get("atb_state", {}).get("ticks_remaining", 0) or 0)
    if enemy_ticks <= 0:
        return {}

    planned = {}
    for character in encounter.get_active_player_participants():
        action = _telegraph_response_action(encounter, character, telegraphed_enemy, predicted_target)
        if not action:
            continue
        ticks_to_resolution = _ticks_until_player_resolution(encounter, character, action)
        if ticks_to_resolution is None:
            continue
        if ticks_to_resolution <= enemy_ticks:
            planned[str(character.id)] = action
    return planned


def choose_player_action(encounter, character):
    enemies = encounter.get_active_enemies()
    if not enemies:
        return {"kind": "attack", "target": None}

    class_key = character.db.brave_class
    active_allies = list(encounter.get_active_participants())
    lowest_ally = min(
        active_allies,
        key=lambda ally: (
            _actor_hp_ratio(ally),
            _actor_id(ally),
        ),
    )
    lowest_player_ally = min(
        encounter.get_active_player_participants(),
        key=lambda ally: (_actor_hp_ratio(ally), _actor_id(ally)),
    )
    target_enemy = min(enemies, key=lambda enemy: (enemy.get("hp", 0), enemy.get("id")))
    marked_enemy = next((enemy for enemy in enemies if enemy.get("marked_turns", 0) > 0), None)
    telegraphed_enemy, telegraph_state = _telegraphed_enemy_state(encounter)
    predicted_target = _predict_enemy_target(encounter, telegraphed_enemy) if telegraphed_enemy else None

    if class_key == "cleric":
        target_hp = (lowest_player_ally.db.brave_resources or {}).get("hp", 0)
        target_max_hp = lowest_player_ally.db.brave_derived_stats.get("max_hp", 1)
        if telegraphed_enemy and predicted_target and not isinstance(predicted_target, dict) and _can_use(character, "guardianlight"):
            return {"kind": "ability", "ability": "guardianlight", "target": predicted_target.id}
        if sum(1 for ally in encounter.get_active_player_participants() if _actor_hp_ratio(ally) <= 0.75) >= 2 and _can_use(character, "sanctuary"):
            return {"kind": "ability", "ability": "sanctuary", "target": character.id}
        if target_hp / max(1, target_max_hp) <= 0.35 and _can_use(character, "renewinglight"):
            return {"kind": "ability", "ability": "renewinglight", "target": lowest_player_ally.id}
        if target_hp / max(1, target_max_hp) <= 0.55 and _can_use(character, "heal"):
            return {"kind": "ability", "ability": "heal", "target": lowest_player_ally.id}
        if _can_use(character, "smite"):
            return {"kind": "ability", "ability": "smite", "target": target_enemy["id"]}
    elif class_key == "warrior":
        if telegraphed_enemy and telegraph_state.get("interruptible") and _can_use(character, "shieldbash"):
            return {"kind": "ability", "ability": "shieldbash", "target": telegraphed_enemy["id"]}
        if telegraphed_enemy and predicted_target and not isinstance(predicted_target, dict) and predicted_target.id != character.id and _can_use(character, "intercept"):
            return {"kind": "ability", "ability": "intercept", "target": predicted_target.id}
        if _actor_hp_ratio(character) <= 0.3 and _can_use(character, "laststand"):
            return {"kind": "ability", "ability": "laststand", "target": character.id}
        if _can_use(character, "strike"):
            return {"kind": "ability", "ability": "strike", "target": target_enemy["id"]}
    elif class_key == "mage":
        if telegraphed_enemy and telegraph_state.get("interruptible") and _can_use(character, "frostbind"):
            return {"kind": "ability", "ability": "frostbind", "target": telegraphed_enemy["id"]}
        if predicted_target is character and _can_use(character, "manashield"):
            return {"kind": "ability", "ability": "manashield", "target": character.id}
        if len(enemies) >= 2 and _can_use(character, "arcspark"):
            return {"kind": "ability", "ability": "arcspark", "target": target_enemy["id"]}
        if _can_use(character, "firebolt"):
            return {"kind": "ability", "ability": "firebolt", "target": target_enemy["id"]}
    elif class_key == "ranger":
        if predicted_target is character and _can_use(character, "evasiveroll"):
            return {"kind": "ability", "ability": "evasiveroll", "target": character.id}
        mark_target = _choose_enemy_for_mark(encounter)
        if mark_target and not marked_enemy and _can_use(character, "markprey"):
            return {"kind": "ability", "ability": "markprey", "target": mark_target["id"]}
        chosen = marked_enemy or target_enemy
        if chosen and chosen.get("marked_turns", 0) > 0 and _can_use(character, "aimedshot"):
            return {"kind": "ability", "ability": "aimedshot", "target": chosen["id"]}
        if _can_use(character, "quickshot"):
            return {"kind": "ability", "ability": "quickshot", "target": chosen["id"]}

    return {"kind": "attack", "target": target_enemy["id"]}


def _queue_pending_actions(encounter):
    pending = dict(encounter.db.pending_actions or {})
    telegraphed_enemy, _telegraph_state = _telegraphed_enemy_state(encounter)
    telegraph_plans = _planned_telegraph_responses(encounter) if telegraphed_enemy else {}
    for actor_id, action in telegraph_plans.items():
        if pending.get(actor_id) != action:
            encounter.telemetry["telegraphed_response_actions"] += 1
        pending[actor_id] = action
    for character in encounter.get_active_player_participants():
        phase = _current_actor_phase(encounter, character)
        if phase in {"winding", "resolving", "recovering", "cooldown", "charging"}:
            continue
        if str(character.id) in telegraph_plans:
            continue
        hold_action = _telegraph_hold_action(encounter, character)
        if hold_action:
            if pending.get(str(character.id)) != hold_action:
                encounter.telemetry["held_actions"] += 1
            pending[str(character.id)] = hold_action
            continue
        if phase == "ready" or str(character.id) not in pending:
            action = choose_player_action(encounter, character)
            if telegraphed_enemy and action.get("kind") == "ability" and action.get("ability") in TELEGRAPH_RESPONSE_ABILITIES:
                encounter.telemetry["telegraphed_response_actions"] += 1
            pending[str(character.id)] = action
    encounter.db.pending_actions = pending


def _build_party(scenario):
    party = []
    for index, class_key in enumerate(scenario["members"], start=1):
        companion_key = scenario.get("companions", {}).get(class_key)
        party.append(
            SimulatedCharacter(
                index,
                class_key,
                companion_key=companion_key,
            )
        )
    return party


def simulate_encounter(authored, scenario, *, base_seed=1, max_rounds=160, trace=False):
    encounter_data = dict(authored["encounter_data"])
    seed = _seed_to_int(base_seed, authored["source"], encounter_data.get("key"), scenario["key"])
    random.seed(seed)

    room = DummyRoom(authored["room_id"] or authored["source"])
    encounter = SimulationEncounter(
        room,
        encounter_data,
        expected_party_size=len(scenario["members"]),
        seed=seed,
    )
    party = _build_party(scenario)
    for character in party:
        encounter.add_simulated_participant(character)
    trace_log = [_trace_snapshot(encounter)] if trace else None

    while not encounter.ended and int(encounter.db.round or 0) < int(max_rounds):
        _queue_pending_actions(encounter)
        encounter.at_repeat()
        if trace_log is not None:
            trace_log.append(_trace_snapshot(encounter))

    if not encounter.ended:
        encounter.outcome = "timeout"
        encounter.ended = True

    rank_bucket, max_rank = classify_encounter_rank(encounter_data)
    player_hp_total = sum(int(character.db.brave_resources.get("hp", 0) or 0) for character in party)
    player_hp_max = sum(int(character.db.brave_derived_stats.get("max_hp", 1) or 1) for character in party)
    enemy_hp_total = sum(int(enemy.get("hp", 0) or 0) for enemy in (encounter.db.enemies or []))
    enemy_hp_max = sum(int(enemy.get("max_hp", 1) or 1) for enemy in (encounter.db.enemies or []))
    contributions = dict(encounter.db.participant_contributions or {})
    companion_contribution = sum(
        int(entry.get("damage_done", 0) or 0)
        for actor_id, entry in contributions.items()
        if str(actor_id).startswith("c")
    )
    player_contribution = sum(
        int(entry.get("damage_done", 0) or 0)
        for actor_id, entry in contributions.items()
        if str(actor_id).isdigit()
    )

    return {
        "source": authored["source"],
        "source_kind": authored["source_kind"],
        "room_id": authored["room_id"],
        "encounter_key": encounter_data.get("key"),
        "encounter_title": encounter_data.get("title"),
        "enemy_templates": list(encounter_data.get("enemies") or []),
        "rank_bucket": rank_bucket,
        "max_rank": max_rank,
        "scenario_key": scenario["key"],
        "scenario_label": scenario["label"],
        "party_size": len(scenario["members"]),
        "party_classes": list(scenario["members"]),
        "companion_enabled": bool(any(scenario.get("companions", {}).values())),
        "seed": seed,
        "outcome": encounter.outcome,
        "rounds": int(encounter.db.round or 0),
        "player_remaining_hp": player_hp_total,
        "player_remaining_hp_ratio": round(player_hp_total / float(max(1, player_hp_max)), 4),
        "enemy_remaining_hp": enemy_hp_total,
        "enemy_remaining_hp_ratio": round(enemy_hp_total / float(max(1, enemy_hp_max)), 4),
        "surviving_players": sum(1 for character in party if int(character.db.brave_resources.get("hp", 0) or 0) > 0),
        "enemy_count": len(encounter_data.get("enemies") or []),
        "companion_count": len(encounter.db.companions or []),
        "damage_done_by_players": player_contribution,
        "damage_done_by_companions": companion_contribution,
        "healing_done": sum(int(entry.get("healing_done", 0) or 0) for entry in contributions.values()),
        "mitigation_done": sum(int(entry.get("damage_prevented", 0) or 0) for entry in contributions.values()),
        "damage_taken": sum(int(entry.get("hits_taken", 0) or 0) for entry in contributions.values()),
        "meaningful_actions": sum(int(entry.get("meaningful_actions", 0) or 0) for entry in contributions.values()),
        "telegraphed_actions": int(encounter.telemetry["telegraphed_actions"]),
        "telegraphed_interrupts": int(encounter.telemetry["telegraphed_interrupts"]),
        "telegraphed_response_actions": int(encounter.telemetry["telegraphed_response_actions"]),
        "held_actions": int(encounter.telemetry["held_actions"]),
        "combat_fx_events": int(encounter.telemetry["combat_fx_events"]),
        "near_wipe": bool(player_hp_total > 0 and (player_hp_total / float(max(1, player_hp_max))) <= 0.2),
        "trace": trace_log,
    }


def build_summary(runs):
    by_scenario = {}
    by_rank = {}
    for run in runs:
        scenario_bucket = by_scenario.setdefault(run["scenario_key"], [])
        scenario_bucket.append(run)
        rank_bucket = by_rank.setdefault(run["rank_bucket"], [])
        rank_bucket.append(run)

    def _aggregate(entries):
        return {
            "runs": len(entries),
            "victories": sum(1 for entry in entries if entry["outcome"] == "victory"),
            "defeats": sum(1 for entry in entries if entry["outcome"] == "defeat"),
            "timeouts": sum(1 for entry in entries if entry["outcome"] == "timeout"),
            "win_rate": round(sum(1 for entry in entries if entry["outcome"] == "victory") / float(max(1, len(entries))), 4),
            "avg_rounds": round(mean(entry["rounds"] for entry in entries), 2),
            "avg_remaining_hp_ratio": round(mean(entry["player_remaining_hp_ratio"] for entry in entries), 4),
            "avg_damage_taken": round(mean(entry["damage_taken"] for entry in entries), 2),
        }

    scenario_summary = {
        key: _aggregate(entries)
        for key, entries in sorted(by_scenario.items())
    }
    rank_summary = {
        key: _aggregate(entries)
        for key, entries in sorted(by_rank.items())
    }

    ranger_off = {
        run["encounter_key"]: run
        for run in runs
        if run["scenario_key"] == "solo_ranger_no_companion"
    }
    ranger_on = {
        run["encounter_key"]: run
        for run in runs
        if run["scenario_key"] == "solo_ranger_with_companion"
    }
    ranger_deltas = []
    for encounter_key, off_run in sorted(ranger_off.items()):
        on_run = ranger_on.get(encounter_key)
        if not on_run:
            continue
        ranger_deltas.append(
            {
                "encounter_key": encounter_key,
                "outcome_off": off_run["outcome"],
                "outcome_on": on_run["outcome"],
                "round_delta": on_run["rounds"] - off_run["rounds"],
                "remaining_hp_ratio_delta": round(on_run["player_remaining_hp_ratio"] - off_run["player_remaining_hp_ratio"], 4),
                "companion_damage": on_run["damage_done_by_companions"],
            }
        )

    toughest = sorted(
        runs,
        key=lambda entry: (
            entry["outcome"] == "victory",
            entry["player_remaining_hp_ratio"],
            entry["rounds"],
            entry["encounter_key"],
        ),
    )[:12]

    return {
        "totals": {
            "encounters": len({(run["source"], run["encounter_key"]) for run in runs}),
            "runs": len(runs),
        },
        "scenario_summary": scenario_summary,
        "rank_summary": rank_summary,
        "ranger_companion_delta": ranger_deltas,
        "toughest_runs": toughest,
    }


def render_markdown(summary):
    lines = [
        "# Combat Simulation Summary",
        "",
        f"- Encounter definitions covered: {summary['totals']['encounters']}",
        f"- Scenario runs: {summary['totals']['runs']}",
        "",
        "## Scenario Summary",
        "",
    ]
    for key, data in summary["scenario_summary"].items():
        lines.append(
            f"- `{key}`: {data['victories']}/{data['runs']} wins, "
            f"{data['defeats']} defeats, {data['timeouts']} timeouts, "
            f"avg rounds {data['avg_rounds']}, avg remaining HP {data['avg_remaining_hp_ratio']}"
        )
    lines.extend(["", "## Rank Summary", ""])
    for key, data in summary["rank_summary"].items():
        lines.append(
            f"- `{key}`: {data['victories']}/{data['runs']} wins, "
            f"avg rounds {data['avg_rounds']}, avg remaining HP {data['avg_remaining_hp_ratio']}"
        )
    lines.extend(["", "## Ranger Companion Delta", ""])
    if not summary["ranger_companion_delta"]:
        lines.append("- No ranger companion comparison data.")
    else:
        sample = summary["ranger_companion_delta"][:12]
        for delta in sample:
            lines.append(
                f"- `{delta['encounter_key']}`: off={delta['outcome_off']}, on={delta['outcome_on']}, "
                f"round delta {delta['round_delta']}, HP delta {delta['remaining_hp_ratio_delta']}, "
                f"companion damage {delta['companion_damage']}"
            )
    lines.extend(["", "## Toughest Runs", ""])
    for run in summary["toughest_runs"]:
        lines.append(
                f"- `{run['scenario_key']}` vs `{run['encounter_key']}`: {run['outcome']}, "
                f"rounds {run['rounds']}, remaining HP {run['player_remaining_hp_ratio']}, "
                f"telegraphs {run['telegraphed_actions']}/{run['telegraphed_response_actions']}/{run['telegraphed_interrupts']}"
            )
    lines.append("")
    return "\n".join(lines)


def run_harness(*, output_dir=DEFAULT_OUTPUT_DIR, base_seed=1, max_rounds=160, limit=None, trace_encounters=None, trace_scenarios=None):
    authored = collect_authored_encounters()
    if limit is not None:
        authored = authored[: max(0, int(limit))]
    trace_encounter_set = {str(entry) for entry in (trace_encounters or []) if str(entry).strip()}
    trace_scenario_set = {str(entry) for entry in (trace_scenarios or []) if str(entry).strip()}
    runs = []
    for encounter in authored:
        for scenario in PARTY_SCENARIOS:
            should_trace = (
                (not trace_encounter_set or encounter["encounter_data"].get("key") in trace_encounter_set)
                and (not trace_scenario_set or scenario["key"] in trace_scenario_set)
            )
            runs.append(simulate_encounter(encounter, scenario, base_seed=base_seed, max_rounds=max_rounds, trace=should_trace))
    summary = build_summary(runs)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_json = output_path / "report.json"
    summary_json = output_path / "summary.json"
    summary_md = output_path / "summary.md"
    interrupt_opportunity_json = output_path / "interrupt_opportunities.json"
    interrupt_opportunity_md = output_path / "interrupt_opportunities.md"
    trace_dir = output_path / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(render_markdown(summary), encoding="utf-8")
    trace_files = []
    opportunity_runs = []
    for run in runs:
        if not run.get("trace"):
            continue
        trace_path = trace_dir / f"{run['encounter_key']}__{run['scenario_key']}.json"
        trace_path.write_text(json.dumps(run["trace"], indent=2), encoding="utf-8")
        trace_files.append(str(trace_path))
        analysis_path = trace_dir / f"{run['encounter_key']}__{run['scenario_key']}__analysis.json"
        trace_analysis = analyze_trace(run["trace"])
        analysis_path.write_text(json.dumps(trace_analysis, indent=2), encoding="utf-8")
        trace_files.append(str(analysis_path))
        opportunity_path = trace_dir / f"{run['encounter_key']}__{run['scenario_key']}__opportunities.json"
        opportunity_summary = analyze_interrupt_opportunities(run["trace"])
        opportunity_path.write_text(json.dumps(opportunity_summary, indent=2), encoding="utf-8")
        opportunity_runs.append(
            {
                "encounter_key": run["encounter_key"],
                "scenario_key": run["scenario_key"],
                "summary": opportunity_summary,
            }
        )
        trace_files.append(str(opportunity_path))
    interrupt_opportunity_report = build_interrupt_opportunity_report(opportunity_runs)
    interrupt_opportunity_json.write_text(json.dumps(interrupt_opportunity_report, indent=2), encoding="utf-8")
    interrupt_opportunity_md.write_text(render_interrupt_opportunity_markdown(interrupt_opportunity_report), encoding="utf-8")
    return {
        "output_dir": str(output_path),
        "report_json": str(report_json),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "interrupt_opportunity_json": str(interrupt_opportunity_json),
        "interrupt_opportunity_md": str(interrupt_opportunity_md),
        "trace_dir": str(trace_dir),
        "trace_files": trace_files,
        "runs": runs,
        "summary": summary,
        "interrupt_opportunity_report": interrupt_opportunity_report,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Brave's deterministic combat telemetry harness.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--base-seed", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=160)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--trace-encounter", action="append", default=[])
    parser.add_argument("--trace-scenario", action="append", default=[])
    args = parser.parse_args()

    result = run_harness(
        output_dir=args.output_dir,
        base_seed=args.base_seed,
        max_rounds=args.max_rounds,
        limit=args.limit,
        trace_encounters=args.trace_encounter,
        trace_scenarios=args.trace_scenario,
    )
    print(result["summary_md"])
    print(f"\nSaved combat simulation outputs to {result['output_dir']}")


if __name__ == "__main__":
    main()
