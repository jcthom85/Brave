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
CLASS_CRIT_BASES = {
    "rogue": 8,
    "ranger": 5,
    "warrior": 4,
    "paladin": 4,
    "druid": 4,
    "mage": 3,
    "cleric": 3,
}
ZONE_LEVEL_BANDS = (
    ("tutorial_", 1),
    ("brambleford_", 1),
    ("goblin_road_", 2),
    ("whispering_woods_", 3),
    ("old_barrow_field_", 5),
    ("ruined_watchtower_", 6),
    ("goblin_warrens_", 8),
    ("blackfen_approach_", 10),
    ("drowned_weir_", 10),
)
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
STRESS_TEST_SCENARIOS = {"solo_ranger_no_companion"}

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

FIRST_HOUR_ROUTE_STEPS = (
    {"kind": "encounter", "key": "yard_scuttle", "label": "Wayfarer's Yard vermin"},
    {"kind": "quest", "key": "practice_makes_heroes"},
    {"kind": "encounter", "key": "grain_raiders", "label": "Rat and Kettle cellar"},
    {"kind": "quest", "key": "rats_in_the_kettle"},
    {"kind": "quest", "key": "roadside_howls"},
    {"kind": "encounter", "key": "trailhead_wolf", "label": "Goblin Road trailhead"},
    {"kind": "encounter", "key": "fencebreakers", "label": "Old Fence Line raiders"},
    {"kind": "quest", "key": "fencebreakers"},
    {"kind": "encounter", "key": "wolf_turn_pack", "label": "Wolf Turn"},
    {"kind": "encounter", "key": "ruks_stand", "label": "Ruk's camp"},
    {"kind": "quest", "key": "ruk_the_fence_cutter", "requires_victory": "ruks_stand"},
)
ACT1_CLOSURE_NPCS = (
    "captain_harl_rowan",
    "joss_veller",
    "mayor_elric_thorne",
    "mira_fenleaf",
)
ACT1_REGION_PREFIXES = (
    "tutorial_",
    "brambleford_",
    "goblin_road_",
    "whispering_woods_",
    "old_barrow_field_",
    "ruined_watchtower_",
    "goblin_warrens_",
    "blackfen_approach_",
    "drowned_weir_",
)
NPC_VOICE_ANCHORS = {
    "brother_alden": ("name", "mercy", "chapel", "bell", "prayer", "fear"),
    "captain_harl_rowan": ("route", "clear", "party", "hit", "watch", "tactical"),
    "joss_veller": ("line", "lamp", "lens", "signal", "measure", "rule"),
    "mayor_elric_thorne": ("ledger", "town", "public", "report", "people", "civic"),
    "mira_fenleaf": ("road", "track", "route", "marsh", "wind", "sign"),
    "sister_maybelle": ("harm", "care", "herb", "recover", "injury", "grief"),
    "uncle_pib_underbough": ("stores", "food", "kettle", "flour", "supper", "cellar"),
    "leda_thornwick": ("boots", "gear", "weather", "trade", "trail", "fair"),
    "torren_ironroot": ("forge", "metal", "repair", "iron", "anvil", "scrap"),
    "mender_veska_flint": ("clamp", "trap", "repair", "parts", "wire", "mechanism"),
    "mistress_elira_thorne": ("practice", "shape", "discipline", "pattern", "technique", "standard"),
    "sergeant_tamsin_vale": ("triage", "yard", "alarm", "checklist", "stand", "command"),
    "quartermaster_nella_cobb": ("crate", "supply", "prepared", "inventory", "gear", "slate"),
    "courier_peep_marrow": ("route", "errand", "chalk", "message", "post", "quick"),
    "ringhand_brask": ("fight", "lesson", "timing", "rail", "ring", "bark"),
}
PROSE_DRIFT_PATTERNS = (
    "feels like",
    "looks like",
    "as if",
    "seems to",
    "the sort of",
    "not quite",
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
            "max_mana": 10 + (primary["intellect"] + primary["spirit"]) * 4 + (level * 3),
            "max_stamina": 18 + (primary["strength"] + primary["agility"] + primary["vitality"]) * 2 + (level * 4),
            "attack_power": primary["strength"] * 2 + primary["agility"] + (level * 2),
            "spell_power": primary["intellect"] * 2 + primary["spirit"] + (level * 2),
            "armor": primary["vitality"] * 2 + primary["strength"] + level,
            "accuracy": 65 + primary["agility"] * 2 + level,
            "precision": primary["agility"] * 2 + (level // 2),
            "crit_chance": 0,
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

        direct_crit_bonus = int(derived.get("crit_chance", 0) or 0)
        precision = int(derived.get("precision", 0) or 0)
        derived["crit_chance"] = max(
            0,
            min(
                50,
                CLASS_CRIT_BASES.get(self.db.brave_class, 4)
                + (int(primary.get("agility", 0) or 0) // 2)
                + (precision // 5)
                + direct_crit_bonus,
            ),
        )

        self.db.brave_primary_stats = primary
        self.db.brave_derived_stats = derived

        if restore or not self.db.brave_resources:
            self.restore_resources()
        return primary, derived


METHOD_NAMES = (
    "configure",
    "_apply_large_party_opening_pressure",
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
            "telegraphed_redirects": 0,
            "telegraphed_mitigations": 0,
            "telegraphed_unanswered": 0,
            "telegraphed_response_actions": 0,
            "held_actions": 0,
            "combat_fx_events": 0,
            "ability_actions": 0,
            "basic_attacks": 0,
            "resource_spent_mana": 0,
            "resource_spent_stamina": 0,
            "resource_spent_by_class": {},
            "ability_actions_by_class": {},
            "basic_attacks_by_class": {},
            "ability_uses": {},
            "restore_item_uses": 0,
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

    def _finish_party_defeat(self, room_message):
        self.defeat_message = str(room_message or "")
        self.outcome = "defeat"
        self.ended = True

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

    def _spend_resource(self, character, resource, amount):
        BraveEncounter._spend_resource(self, character, resource, amount)
        if resource in {"mana", "stamina"}:
            self.telemetry[f"resource_spent_{resource}"] += max(0, int(amount or 0))

    def _execute_basic_attack(self, character, target=None):
        self.telemetry["basic_attacks"] += 1
        return BraveEncounter._execute_basic_attack(self, character, target=target)

    def _execute_ability(self, character, action):
        self.telemetry["ability_actions"] += 1
        return BraveEncounter._execute_ability(self, character, action)

    def _enemy_telegraph_message(self, enemy):
        self.telemetry["telegraphed_actions"] += 1
        return BraveEncounter._enemy_telegraph_message(self, enemy)

    def _try_interrupt_enemy_action(self, character, enemy, tool_label):
        interrupted = BraveEncounter._try_interrupt_enemy_action(self, character, enemy, tool_label)
        if interrupted:
            self.telemetry["telegraphed_interrupts"] += 1
        return interrupted

    def _record_telegraph_outcome(self, enemy, outcome, *, label=None, answer=None, target=None):
        BraveEncounter._record_telegraph_outcome(self, enemy, outcome, label=label, answer=answer, target=target)
        if outcome == "redirected":
            self.telemetry["telegraphed_redirects"] += 1
        elif outcome == "mitigated":
            self.telemetry["telegraphed_mitigations"] += 1
        elif outcome == "unanswered":
            self.telemetry["telegraphed_unanswered"] += 1

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


def _simulation_spend_resource(self, character, resource, amount):
    BraveEncounter._spend_resource(self, character, resource, amount)
    if resource in {"mana", "stamina"}:
        spent = max(0, int(amount or 0))
        self.telemetry[f"resource_spent_{resource}"] += spent
        class_key = str(getattr(getattr(character, "db", None), "brave_class", "") or "unknown")
        by_class = self.telemetry.setdefault("resource_spent_by_class", {})
        class_bucket = by_class.setdefault(class_key, {"mana": 0, "stamina": 0})
        class_bucket[resource] = int(class_bucket.get(resource, 0) or 0) + spent


def _simulation_execute_basic_attack(self, character, target=None):
    self.telemetry["basic_attacks"] += 1
    class_key = str(getattr(getattr(character, "db", None), "brave_class", "") or "unknown")
    by_class = self.telemetry.setdefault("basic_attacks_by_class", {})
    by_class[class_key] = int(by_class.get(class_key, 0) or 0) + 1
    return BraveEncounter._execute_basic_attack(self, character, target=target)


def _simulation_execute_ability(self, character, action):
    self.telemetry["ability_actions"] += 1
    class_key = str(getattr(getattr(character, "db", None), "brave_class", "") or "unknown")
    by_class = self.telemetry.setdefault("ability_actions_by_class", {})
    by_class[class_key] = int(by_class.get(class_key, 0) or 0) + 1
    ability_key = _ability_key((action or {}).get("ability") or "")
    if ability_key:
        uses = self.telemetry.setdefault("ability_uses", {})
        uses[ability_key] = int(uses.get(ability_key, 0) or 0) + 1
    return BraveEncounter._execute_ability(self, character, action)


SimulationEncounter._spend_resource = _simulation_spend_resource
SimulationEncounter._execute_basic_attack = _simulation_execute_basic_attack
SimulationEncounter._execute_ability = _simulation_execute_ability


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


def _party_resource_total(party, resource):
    return sum(int((character.db.brave_resources or {}).get(resource, 0) or 0) for character in party)


def _party_resource_max_total(party, resource):
    stat_key = f"max_{resource}"
    return sum(int((character.db.brave_derived_stats or {}).get(stat_key, 0) or 0) for character in party)


def _primary_resource_key_for_character(character):
    if character.db.brave_class in {"cleric", "mage", "druid"}:
        return "mana"
    return "stamina"


def _lowest_primary_resource_ratio(encounter, party):
    ratios = []
    for character in party:
        resource = _primary_resource_key_for_character(character)
        current = int((character.db.brave_resources or {}).get(resource, 0) or 0)
        maximum = int((character.db.brave_derived_stats or {}).get(f"max_{resource}", 0) or 0)
        if maximum > 0:
            ratios.append(current / float(maximum))
    return min(ratios) if ratios else 1.0


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
            "mana": int(resources.get("mana", 0) or 0),
            "max_mana": int(actor.db.brave_derived_stats.get("max_mana", 0) or 0),
            "stamina": int(resources.get("stamina", 0) or 0),
            "max_stamina": int(actor.db.brave_derived_stats.get("max_stamina", 0) or 0),
            "primary_resource": _primary_resource_key_for_character(actor),
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
                    ticks_remaining = int(player.get("ticks_remaining", 0) or 0)
                    if phase == "ready" or (phase == "charging" and ticks_remaining <= 0):
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
                if phase == "ready" or (phase == "charging" and ticks_remaining == 0):
                    summary["interrupt_ready_ticks"] += 1
                    bucket["interrupt_ready_ticks"] += 1
                if phase == "charging" and ticks_remaining == 0:
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


def _harmful_condition_target(encounter):
    candidates = []
    for ally in encounter.get_active_player_participants():
        state = encounter._get_participant_state(ally)
        condition_count = sum(
            1
            for key in ("bleed_turns", "poison_turns", "curse_turns", "snare_turns")
            if int(state.get(key, 0) or 0) > 0
        )
        if condition_count:
            candidates.append((condition_count, 1.0 - _actor_hp_ratio(ally), -int(ally.id), ally))
    if not candidates:
        return None
    return max(candidates)[-1]


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
        afflicted = _harmful_condition_target(encounter)
        if afflicted and _can_use(character, "cleanse"):
            return {"kind": "ability", "ability": "cleanse", "target": afflicted.id}
        if afflicted and _can_use(character, "renewinglight"):
            return {"kind": "ability", "ability": "renewinglight", "target": afflicted.id}
        if afflicted and _can_use(character, "blessing"):
            return {"kind": "ability", "ability": "blessing", "target": afflicted.id}
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
        afflicted = _harmful_condition_target(encounter)
        if telegraphed_enemy and predicted_target and not isinstance(predicted_target, dict) and _can_use(character, "guardianlight"):
            return {"kind": "ability", "ability": "guardianlight", "target": predicted_target.id}
        if sum(1 for ally in encounter.get_active_player_participants() if _actor_hp_ratio(ally) <= 0.75) >= 2 and _can_use(character, "sanctuary"):
            return {"kind": "ability", "ability": "sanctuary", "target": character.id}
        if afflicted and _actor_hp_ratio(afflicted) <= 0.75 and _can_use(character, "renewinglight"):
            return {"kind": "ability", "ability": "renewinglight", "target": afflicted.id}
        if afflicted and _can_use(character, "cleanse"):
            return {"kind": "ability", "ability": "cleanse", "target": afflicted.id}
        if afflicted and _can_use(character, "blessing"):
            return {"kind": "ability", "ability": "blessing", "target": afflicted.id}
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
        atb_state = encounter._get_actor_atb_state(character=character)
        ticks_remaining = int((atb_state or {}).get("ticks_remaining", 0) or 0)
        if phase in {"winding", "resolving", "recovering", "cooldown"}:
            continue
        if phase == "charging" and ticks_remaining > 1:
            continue
        if str(character.id) in telegraph_plans:
            continue
        hold_action = _telegraph_hold_action(encounter, character)
        if hold_action:
            if pending.get(str(character.id)) != hold_action:
                encounter.telemetry["held_actions"] += 1
            pending[str(character.id)] = hold_action
            continue
        if phase == "ready" or phase == "charging" or str(character.id) not in pending:
            action = choose_player_action(encounter, character)
            if telegraphed_enemy and action.get("kind") == "ability" and action.get("ability") in TELEGRAPH_RESPONSE_ABILITIES:
                encounter.telemetry["telegraphed_response_actions"] += 1
            pending[str(character.id)] = action
    encounter.db.pending_actions = pending


def infer_expected_level(authored):
    """Return the approximate intended level for an authored encounter."""

    room_id = str((authored or {}).get("room_id") or "")
    for prefix, level in ZONE_LEVEL_BANDS:
        if room_id.startswith(prefix):
            return level
    return DEFAULT_LEVEL


def _build_party(scenario, *, level=None):
    party = []
    scenario_level = int(scenario.get("level", level if level is not None else DEFAULT_LEVEL) or DEFAULT_LEVEL)
    for index, class_key in enumerate(scenario["members"], start=1):
        companion_key = scenario.get("companions", {}).get(class_key)
        party.append(
            SimulatedCharacter(
                index,
                class_key,
                level=scenario_level,
                companion_key=companion_key,
            )
        )
    return party


def simulate_encounter(authored, scenario, *, base_seed=1, max_rounds=160, trace=False, level=None):
    encounter_data = dict(authored["encounter_data"])
    scenario_level = int(level if level is not None else scenario.get("level", DEFAULT_LEVEL) or DEFAULT_LEVEL)
    seed = _seed_to_int(base_seed, authored["source"], encounter_data.get("key"), scenario["key"], scenario_level)
    random.seed(seed)

    room = DummyRoom(authored["room_id"] or authored["source"])
    encounter = SimulationEncounter(
        room,
        encounter_data,
        expected_party_size=len(scenario["members"]),
        seed=seed,
    )
    party = _build_party(scenario, level=scenario_level)
    for character in party:
        encounter.add_simulated_participant(character)
    initial_mana_total = _party_resource_total(party, "mana")
    initial_stamina_total = _party_resource_total(party, "stamina")
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
    player_mana_total = _party_resource_total(party, "mana")
    player_mana_max = _party_resource_max_total(party, "mana")
    player_stamina_total = _party_resource_total(party, "stamina")
    player_stamina_max = _party_resource_max_total(party, "stamina")
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
    healing_done_by_class = {}
    for character in party:
        contribution = dict(contributions.get(str(character.id), {}) or {})
        class_key = str(character.db.brave_class or "unknown")
        healing_done_by_class[class_key] = healing_done_by_class.get(class_key, 0) + int(contribution.get("healing_done", 0) or 0)

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
        "character_level": scenario_level,
        "expected_level": infer_expected_level(authored),
        "party_size": len(scenario["members"]),
        "party_classes": list(scenario["members"]),
        "companion_enabled": bool(any(scenario.get("companions", {}).values())),
        "seed": seed,
        "outcome": encounter.outcome,
        "rounds": int(encounter.db.round or 0),
        "player_remaining_hp": player_hp_total,
        "player_remaining_hp_ratio": round(player_hp_total / float(max(1, player_hp_max)), 4),
        "party_remaining_mana": player_mana_total,
        "party_remaining_mana_ratio": round(player_mana_total / float(max(1, player_mana_max)), 4),
        "party_remaining_stamina": player_stamina_total,
        "party_remaining_stamina_ratio": round(player_stamina_total / float(max(1, player_stamina_max)), 4),
        "party_mana_spent": max(0, initial_mana_total - player_mana_total),
        "party_stamina_spent": max(0, initial_stamina_total - player_stamina_total),
        "lowest_primary_resource_ratio": round(_lowest_primary_resource_ratio(encounter, party), 4),
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
        "telegraphed_redirects": int(encounter.telemetry["telegraphed_redirects"]),
        "telegraphed_mitigations": int(encounter.telemetry["telegraphed_mitigations"]),
        "telegraphed_unanswered": int(encounter.telemetry["telegraphed_unanswered"]),
        "telegraphed_response_actions": int(encounter.telemetry["telegraphed_response_actions"]),
        "held_actions": int(encounter.telemetry["held_actions"]),
        "combat_fx_events": int(encounter.telemetry["combat_fx_events"]),
        "ability_actions": int(encounter.telemetry["ability_actions"]),
        "basic_attacks": int(encounter.telemetry["basic_attacks"]),
        "ability_action_ratio": round(
            int(encounter.telemetry["ability_actions"])
            / float(max(1, int(encounter.telemetry["ability_actions"]) + int(encounter.telemetry["basic_attacks"]))),
            4,
        ),
        "resource_spent_mana": int(encounter.telemetry["resource_spent_mana"]),
        "resource_spent_stamina": int(encounter.telemetry["resource_spent_stamina"]),
        "resource_spent_by_class": dict(encounter.telemetry.get("resource_spent_by_class") or {}),
        "ability_actions_by_class": dict(encounter.telemetry.get("ability_actions_by_class") or {}),
        "basic_attacks_by_class": dict(encounter.telemetry.get("basic_attacks_by_class") or {}),
        "ability_uses": dict(encounter.telemetry.get("ability_uses") or {}),
        "healing_done_by_class": healing_done_by_class,
        "restore_item_uses": int(encounter.telemetry.get("restore_item_uses", 0) or 0),
        "near_wipe": bool(player_hp_total > 0 and (player_hp_total / float(max(1, player_hp_max))) <= 0.2),
        "trace": trace_log,
    }


def build_summary(runs):
    by_scenario = {}
    by_rank = {}
    by_encounter = {}
    primary_runs = [run for run in runs if run.get("scenario_key") not in STRESS_TEST_SCENARIOS]
    stress_runs = [run for run in runs if run.get("scenario_key") in STRESS_TEST_SCENARIOS]
    for run in runs:
        scenario_bucket = by_scenario.setdefault(run["scenario_key"], [])
        scenario_bucket.append(run)
        if run in primary_runs:
            rank_bucket = by_rank.setdefault(run["rank_bucket"], [])
            rank_bucket.append(run)
            encounter_bucket = by_encounter.setdefault(run["encounter_key"], [])
            encounter_bucket.append(run)

    def _aggregate(entries):
        telegraphed_actions = sum(int(entry.get("telegraphed_actions", 0) or 0) for entry in entries)
        telegraphed_answers = sum(
            int(entry.get("telegraphed_interrupts", 0) or 0)
            + int(entry.get("telegraphed_redirects", 0) or 0)
            + int(entry.get("telegraphed_mitigations", 0) or 0)
            for entry in entries
        )
        return {
            "runs": len(entries),
            "victories": sum(1 for entry in entries if entry["outcome"] == "victory"),
            "defeats": sum(1 for entry in entries if entry["outcome"] == "defeat"),
            "timeouts": sum(1 for entry in entries if entry["outcome"] == "timeout"),
            "near_wipes": sum(1 for entry in entries if entry.get("near_wipe")),
            "win_rate": round(sum(1 for entry in entries if entry["outcome"] == "victory") / float(max(1, len(entries))), 4),
            "avg_rounds": round(mean(entry["rounds"] for entry in entries), 2),
            "avg_remaining_hp_ratio": round(mean(entry["player_remaining_hp_ratio"] for entry in entries), 4),
            "avg_remaining_mana_ratio": round(mean(entry.get("party_remaining_mana_ratio", 1.0) for entry in entries), 4),
            "avg_remaining_stamina_ratio": round(mean(entry.get("party_remaining_stamina_ratio", 1.0) for entry in entries), 4),
            "avg_lowest_primary_resource_ratio": round(mean(entry.get("lowest_primary_resource_ratio", 1.0) for entry in entries), 4),
            "avg_ability_action_ratio": round(mean(entry.get("ability_action_ratio", 0.0) for entry in entries), 4),
            "avg_mana_spent": round(mean(entry.get("party_mana_spent", 0) for entry in entries), 2),
            "avg_stamina_spent": round(mean(entry.get("party_stamina_spent", 0) for entry in entries), 2),
            "avg_damage_taken": round(mean(entry["damage_taken"] for entry in entries), 2),
            "avg_healing_done": round(mean(entry["healing_done"] for entry in entries), 2),
            "avg_mitigation_done": round(mean(entry["mitigation_done"] for entry in entries), 2),
            "telegraphed_actions": telegraphed_actions,
            "telegraphed_answers": telegraphed_answers,
            "telegraph_answer_rate": round(telegraphed_answers / float(max(1, telegraphed_actions)), 4),
            "telegraphed_unanswered": sum(int(entry.get("telegraphed_unanswered", 0) or 0) for entry in entries),
        }

    scenario_summary = {
        key: {
            **_aggregate(entries),
            "balance_bucket": "stress_test" if key in STRESS_TEST_SCENARIOS else "primary",
        }
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
    near_wipes = sorted(
        [run for run in runs if run.get("near_wipe")],
        key=lambda entry: (
            entry["player_remaining_hp_ratio"],
            -entry["rounds"],
            entry["scenario_key"],
            entry["encounter_key"],
        ),
    )[:12]
    longest_victories = sorted(
        [run for run in runs if run["outcome"] == "victory"],
        key=lambda entry: (
            -entry["rounds"],
            entry["player_remaining_hp_ratio"],
            entry["scenario_key"],
            entry["encounter_key"],
        ),
    )[:12]
    telegraph_risks = sorted(
        [
            run
            for run in runs
            if int(run.get("telegraphed_actions", 0) or 0) > 0
            and int(run.get("telegraphed_interrupts", 0) or 0)
            + int(run.get("telegraphed_redirects", 0) or 0)
            + int(run.get("telegraphed_mitigations", 0) or 0)
            <= 0
        ],
        key=lambda entry: (
            -int(entry.get("telegraphed_actions", 0) or 0),
            entry["outcome"] == "victory",
            entry["player_remaining_hp_ratio"],
            entry["scenario_key"],
            entry["encounter_key"],
        ),
    )[:12]

    encounter_summary = {}
    for encounter_key, entries in sorted(by_encounter.items()):
        aggregate = _aggregate(entries)
        encounter_summary[encounter_key] = {
            **aggregate,
            "rank_bucket": entries[0]["rank_bucket"] if entries else "normal",
            "source": entries[0]["source"] if entries else "",
            "enemy_templates": list(entries[0].get("enemy_templates") or []) if entries else [],
        }

    encounter_risks = sorted(
        encounter_summary.items(),
        key=lambda item: (
            item[1]["win_rate"],
            item[1]["avg_remaining_hp_ratio"],
            -item[1]["near_wipes"],
            -item[1]["avg_rounds"],
            item[0],
        ),
    )[:15]
    primary_failures = sorted(
        [run for run in primary_runs if run.get("outcome") != "victory"],
        key=lambda entry: (
            entry.get("outcome") != "timeout",
            entry.get("scenario_key", ""),
            entry.get("encounter_key", ""),
        ),
    )

    return {
        "totals": {
            "encounters": len({(run["source"], run["encounter_key"]) for run in runs}),
            "runs": len(runs),
            "victories": sum(1 for run in runs if run["outcome"] == "victory"),
            "defeats": sum(1 for run in runs if run["outcome"] == "defeat"),
            "timeouts": sum(1 for run in runs if run["outcome"] == "timeout"),
            "near_wipes": sum(1 for run in runs if run.get("near_wipe")),
            "primary_runs": len(primary_runs),
            "primary_victories": sum(1 for run in primary_runs if run["outcome"] == "victory"),
            "primary_defeats": sum(1 for run in primary_runs if run["outcome"] == "defeat"),
            "primary_timeouts": sum(1 for run in primary_runs if run["outcome"] == "timeout"),
            "primary_near_wipes": sum(1 for run in primary_runs if run.get("near_wipe")),
            "stress_runs": len(stress_runs),
            "stress_victories": sum(1 for run in stress_runs if run["outcome"] == "victory"),
            "stress_defeats": sum(1 for run in stress_runs if run["outcome"] == "defeat"),
            "stress_timeouts": sum(1 for run in stress_runs if run["outcome"] == "timeout"),
            "stress_near_wipes": sum(1 for run in stress_runs if run.get("near_wipe")),
        },
        "primary_summary": _aggregate(primary_runs) if primary_runs else {},
        "stress_summary": _aggregate(stress_runs) if stress_runs else {},
        "scenario_summary": scenario_summary,
        "rank_summary": rank_summary,
        "encounter_summary": encounter_summary,
        "ranger_companion_delta": ranger_deltas,
        "toughest_runs": toughest,
        "near_wipes": near_wipes,
        "longest_victories": longest_victories,
        "telegraph_risks": telegraph_risks,
        "primary_failures": primary_failures,
        "encounter_risks": [
            {"encounter_key": key, **data}
            for key, data in encounter_risks
        ],
    }


def _average(entries, key, default=0):
    if not entries:
        return default
    return round(mean(float(entry.get(key, default) or 0) for entry in entries), 4)


def build_resource_economy_report(runs):
    primary_runs = [run for run in runs if run.get("scenario_key") not in STRESS_TEST_SCENARIOS]
    scenario_rows = []
    class_buckets = {}
    ability_uses = {}

    for run in runs:
        for ability_key, count in (run.get("ability_uses") or {}).items():
            ability_uses[ability_key] = ability_uses.get(ability_key, 0) + int(count or 0)
        for class_key in run.get("party_classes") or []:
            class_buckets.setdefault(
                class_key,
                {
                    "runs": 0,
                    "mana_spent": 0,
                    "stamina_spent": 0,
                    "ability_actions": 0,
                    "basic_attacks": 0,
                    "healing_done": 0,
                },
            )["runs"] += 1
        for class_key, spent in (run.get("resource_spent_by_class") or {}).items():
            bucket = class_buckets.setdefault(
                class_key,
                {
                    "runs": 0,
                    "mana_spent": 0,
                    "stamina_spent": 0,
                    "ability_actions": 0,
                    "basic_attacks": 0,
                    "healing_done": 0,
                },
            )
            bucket["mana_spent"] += int((spent or {}).get("mana", 0) or 0)
            bucket["stamina_spent"] += int((spent or {}).get("stamina", 0) or 0)
        for class_key, count in (run.get("ability_actions_by_class") or {}).items():
            class_buckets.setdefault(
                class_key,
                {
                    "runs": 0,
                    "mana_spent": 0,
                    "stamina_spent": 0,
                    "ability_actions": 0,
                    "basic_attacks": 0,
                    "healing_done": 0,
                },
            )["ability_actions"] += int(count or 0)
        for class_key, count in (run.get("basic_attacks_by_class") or {}).items():
            class_buckets.setdefault(
                class_key,
                {
                    "runs": 0,
                    "mana_spent": 0,
                    "stamina_spent": 0,
                    "ability_actions": 0,
                    "basic_attacks": 0,
                    "healing_done": 0,
                },
            )["basic_attacks"] += int(count or 0)
        for class_key, amount in (run.get("healing_done_by_class") or {}).items():
            class_buckets.setdefault(
                class_key,
                {
                    "runs": 0,
                    "mana_spent": 0,
                    "stamina_spent": 0,
                    "ability_actions": 0,
                    "basic_attacks": 0,
                    "healing_done": 0,
                },
            )["healing_done"] += int(amount or 0)

    by_scenario = {}
    for run in runs:
        by_scenario.setdefault(run["scenario_key"], []).append(run)
    for scenario_key, entries in sorted(by_scenario.items()):
        restore_uses = sum(int(entry.get("restore_item_uses", 0) or 0) for entry in entries)
        scenario_rows.append(
            {
                "scenario_key": scenario_key,
                "balance_bucket": "stress_test" if scenario_key in STRESS_TEST_SCENARIOS else "primary",
                "runs": len(entries),
                "wins": sum(1 for entry in entries if entry.get("outcome") == "victory"),
                "avg_remaining_hp_ratio": _average(entries, "player_remaining_hp_ratio"),
                "avg_remaining_mana_ratio": _average(entries, "party_remaining_mana_ratio", 1),
                "avg_remaining_stamina_ratio": _average(entries, "party_remaining_stamina_ratio", 1),
                "avg_lowest_primary_resource_ratio": _average(entries, "lowest_primary_resource_ratio", 1),
                "avg_mana_spent": round(mean(float(entry.get("party_mana_spent", 0) or 0) for entry in entries), 2),
                "avg_stamina_spent": round(mean(float(entry.get("party_stamina_spent", 0) or 0) for entry in entries), 2),
                "avg_healing_done": round(mean(float(entry.get("healing_done", 0) or 0) for entry in entries), 2),
                "restore_item_uses": restore_uses,
            }
        )

    class_rows = []
    for class_key, data in sorted(class_buckets.items()):
        runs_count = max(1, int(data.get("runs", 0) or 0))
        total_actions = int(data.get("ability_actions", 0) or 0) + int(data.get("basic_attacks", 0) or 0)
        class_rows.append(
            {
                "class": class_key,
                "runs": int(data.get("runs", 0) or 0),
                "avg_mana_spent": round(float(data.get("mana_spent", 0) or 0) / runs_count, 2),
                "avg_stamina_spent": round(float(data.get("stamina_spent", 0) or 0) / runs_count, 2),
                "ability_actions": int(data.get("ability_actions", 0) or 0),
                "basic_attacks": int(data.get("basic_attacks", 0) or 0),
                "ability_action_ratio": round(int(data.get("ability_actions", 0) or 0) / float(max(1, total_actions)), 4),
                "avg_healing_done": round(float(data.get("healing_done", 0) or 0) / runs_count, 2),
            }
        )

    low_relevance = sorted(
        [
            run
            for run in primary_runs
            if run.get("outcome") == "victory"
            and float(run.get("player_remaining_hp_ratio", 0) or 0) >= 0.9
            and float(run.get("lowest_primary_resource_ratio", 0) or 0) >= 0.65
            and int(run.get("healing_done", 0) or 0) <= 0
        ],
        key=lambda entry: (
            -float(entry.get("player_remaining_hp_ratio", 0) or 0),
            -float(entry.get("lowest_primary_resource_ratio", 0) or 0),
            entry.get("scenario_key", ""),
            entry.get("encounter_key", ""),
        ),
    )[:20]
    top_abilities = [
        {"ability_key": key, "uses": count}
        for key, count in sorted(ability_uses.items(), key=lambda item: (-item[1], item[0]))[:20]
    ]
    return {
        "totals": {
            "runs": len(runs),
            "primary_runs": len(primary_runs),
            "restore_item_uses": sum(int(run.get("restore_item_uses", 0) or 0) for run in runs),
            "low_relevance_primary_runs": len(low_relevance),
        },
        "scenario_rows": scenario_rows,
        "class_rows": class_rows,
        "top_abilities": top_abilities,
        "low_relevance_runs": low_relevance,
        "notes": [
            "restore_item_uses is currently zero because the deterministic combat simulator does not consume inventory items.",
            "solo_ranger_no_companion remains marked as a stress-test scenario, not the primary tuning target.",
        ],
    }


def build_progression_runs(*, base_seed=1, max_rounds=160, limit=None):
    authored = collect_authored_encounters()
    if limit is not None:
        authored = authored[: max(0, int(limit))]
    runs = []
    for encounter in authored:
        level = infer_expected_level(encounter)
        for scenario in PARTY_SCENARIOS:
            runs.append(simulate_encounter(encounter, scenario, base_seed=base_seed, max_rounds=max_rounds, level=level))
    return runs


def _level_for_xp(xp_total):
    level = 1
    for candidate in range(2, CHARACTER_CONTENT.max_level + 1):
        if int(xp_total or 0) >= int(CHARACTER_CONTENT.xp_for_level[candidate]):
            level = candidate
    return level


def _find_authored_encounter(encounter_key):
    for authored in collect_authored_encounters():
        if authored["encounter_data"].get("key") == encounter_key:
            return authored
    raise KeyError(f"Unknown encounter key: {encounter_key}")


def _encounter_xp(encounter_data):
    total = 0
    for template_key in encounter_data.get("enemies") or []:
        template = ENCOUNTER_CONTENT.get_enemy_template(template_key) or {}
        total += int(template.get("xp", 0) or 0)
    return total


def _merge_item_rewards(entries):
    totals = {}
    for template_id, quantity in entries:
        if not template_id:
            continue
        totals[template_id] = totals.get(template_id, 0) + max(1, int(quantity or 1))
    return [
        {"item": template_id, "quantity": totals[template_id]}
        for template_id in sorted(totals)
    ]


def _quest_reward_profile(quest_key):
    definition = CONTENT.quests.get(quest_key) or {}
    rewards = definition.get("rewards") or {}
    return {
        "xp": int(rewards.get("xp", 0) or 0),
        "silver": int(rewards.get("silver", 0) or 0),
        "items": [
            {"item": entry.get("item"), "quantity": int(entry.get("quantity", 1) or 1)}
            for entry in rewards.get("items", [])
            if entry.get("item")
        ],
    }


def _encounter_reward_profile(encounter_data):
    silver_min = 0
    silver_max = 0
    guaranteed_items = []
    possible_items = []
    for template_key in encounter_data.get("enemies") or []:
        template = ENCOUNTER_CONTENT.get_enemy_template(template_key) or {}
        min_silver, max_silver = template.get("silver", (0, 0))
        silver_min += int(min_silver or 0)
        silver_max += int(max_silver or 0)
        for drop in template.get("loot", []):
            item_id = drop.get("item")
            if not item_id:
                continue
            quantity = int(drop.get("min", 1) or 1)
            if float(drop.get("chance", 0) or 0) >= 1.0:
                guaranteed_items.append((item_id, quantity))
            else:
                possible_items.append((item_id, quantity))
    return {
        "xp": _encounter_xp(encounter_data),
        "silver_min": silver_min,
        "silver_max": silver_max,
        "guaranteed_items": _merge_item_rewards(guaranteed_items),
        "possible_items": _merge_item_rewards(possible_items),
    }


def _quest_xp(quest_key):
    return _quest_reward_profile(quest_key)["xp"]


def _quests_unlocked_by(quest_key):
    return [
        candidate_key
        for candidate_key in CONTENT.quests.starting_quests
        if quest_key in (CONTENT.quests.get(candidate_key) or {}).get("prerequisites", [])
    ]


def _quest_next_step(quest_key):
    return str((CONTENT.quests.get(quest_key) or {}).get("next_step") or "").strip()


def _quests_with_prerequisite(quest_key):
    return [
        candidate_key
        for candidate_key, definition in sorted(CONTENT.quests.quests.items())
        if quest_key in (definition or {}).get("prerequisites", [])
    ]


def _dialogue_has_completed_rule(npc_key, quest_key):
    for rule in CONTENT.dialogue.get_talk_rules(npc_key):
        if rule.get("completed") == quest_key or quest_key in (rule.get("completed_any") or []):
            return True
    return False


def _first_hour_pacing_flags(steps, post_ruk_unlock_order):
    flags = []
    for step in steps:
        if step["kind"] == "quest":
            if not step.get("next_step"):
                flags.append(
                    {
                        "kind": "missing_next_step",
                        "step": step["key"],
                        "message": f"Quest {step['key']} has no next_step handoff.",
                    }
                )
            continue

        if step.get("outcome") != "victory":
            flags.append(
                {
                    "kind": "encounter_not_victory",
                    "step": step["key"],
                    "message": f"Encounter {step['key']} ended with {step.get('outcome')}.",
                }
            )
        if float(step.get("remaining_hp_ratio") or 0) < 0.35:
            flags.append(
                {
                    "kind": "low_remaining_hp",
                    "step": step["key"],
                    "message": f"Encounter {step['key']} ended below 35% HP.",
                }
            )
        if int(step.get("rounds") or 0) > 45:
            flags.append(
                {
                    "kind": "long_encounter",
                    "step": step["key"],
                    "message": f"Encounter {step['key']} took {step['rounds']} rounds.",
                }
            )
        if int(step.get("telegraphed_unanswered") or 0) > 0:
            flags.append(
                {
                    "kind": "unanswered_telegraphs",
                    "step": step["key"],
                    "message": f"Encounter {step['key']} had {step['telegraphed_unanswered']} unanswered telegraphs.",
                }
            )

    for quest_key in post_ruk_unlock_order:
        if not _quest_next_step(quest_key):
            flags.append(
                {
                    "kind": "missing_post_ruk_next_step",
                    "step": quest_key,
                    "message": f"Post-Ruk lead {quest_key} has no next_step handoff.",
                }
            )
    return flags


def build_first_hour_route_report(*, scenario_key="solo_warrior", base_seed=1, max_rounds=160):
    """Simulate the canonical first-hour route with XP and level pacing."""

    scenario = next(entry for entry in PARTY_SCENARIOS if entry["key"] == scenario_key)
    xp_total = 0
    silver_total_min = 0
    silver_total_max = 0
    guaranteed_items_total = []
    possible_items_total = []
    level = 1
    steps = []
    encounter_outcomes = {}
    tracked_quest = next((step["key"] for step in FIRST_HOUR_ROUTE_STEPS if step["kind"] == "quest"), None)
    tracked_quest_transitions = []
    unlock_order_after_ruk = [
        quest_key
        for quest_key in CONTENT.quests.starting_quests
        if "ruk_the_fence_cutter" in (CONTENT.quests.get(quest_key) or {}).get("prerequisites", [])
    ]

    for index, step in enumerate(FIRST_HOUR_ROUTE_STEPS, start=1):
        before_xp = xp_total
        before_silver_min = silver_total_min
        before_silver_max = silver_total_max
        before_level = level
        if step["kind"] == "quest":
            quest_key = step["key"]
            required_victory = step.get("requires_victory")
            tracked_before = tracked_quest
            if required_victory and encounter_outcomes.get(required_victory) != "victory":
                steps.append(
                    {
                        "index": index,
                        "kind": "quest",
                        "key": quest_key,
                        "title": (CONTENT.quests.get(quest_key) or {}).get("title", quest_key),
                        "blocked": True,
                        "blocked_by": required_victory,
                        "xp_awarded": 0,
                        "silver_awarded": 0,
                        "item_rewards": [],
                        "xp_before": before_xp,
                        "xp_after": xp_total,
                        "silver_before_min": before_silver_min,
                        "silver_before_max": before_silver_max,
                        "silver_after_min": silver_total_min,
                        "silver_after_max": silver_total_max,
                        "level_before": before_level,
                        "level_after": level,
                        "next_step": _quest_next_step(quest_key),
                        "unlocks": _quests_unlocked_by(quest_key),
                        "tracked_quest_before": tracked_before,
                        "tracked_quest_after": tracked_quest,
                    }
                )
                continue
            rewards = _quest_reward_profile(quest_key)
            xp_awarded = rewards["xp"]
            xp_total += xp_awarded
            silver_total_min += rewards["silver"]
            silver_total_max += rewards["silver"]
            guaranteed_items_total.extend((entry["item"], entry["quantity"]) for entry in rewards["items"])
            level = _level_for_xp(xp_total)
            unlocks = _quests_unlocked_by(quest_key)
            tracked_quest = unlocks[0] if unlocks else tracked_quest
            tracked_quest_transitions.append(
                {
                    "step": quest_key,
                    "before": tracked_before,
                    "after": tracked_quest,
                    "unlocks": unlocks,
                }
            )
            steps.append(
                {
                    "index": index,
                    "kind": "quest",
                    "key": quest_key,
                    "title": (CONTENT.quests.get(quest_key) or {}).get("title", quest_key),
                    "xp_awarded": xp_awarded,
                    "silver_awarded": rewards["silver"],
                    "item_rewards": rewards["items"],
                    "xp_before": before_xp,
                    "xp_after": xp_total,
                    "silver_before_min": before_silver_min,
                    "silver_before_max": before_silver_max,
                    "silver_after_min": silver_total_min,
                    "silver_after_max": silver_total_max,
                    "level_before": before_level,
                    "level_after": level,
                    "next_step": _quest_next_step(quest_key),
                    "unlocks": unlocks,
                    "tracked_quest_before": tracked_before,
                    "tracked_quest_after": tracked_quest,
                }
            )
            continue

        authored = _find_authored_encounter(step["key"])
        run = simulate_encounter(authored, scenario, base_seed=base_seed, max_rounds=max_rounds, level=level)
        encounter_outcomes[step["key"]] = run["outcome"]
        rewards = _encounter_reward_profile(authored["encounter_data"])
        xp_awarded = rewards["xp"] if run["outcome"] == "victory" else 0
        silver_min_awarded = rewards["silver_min"] if run["outcome"] == "victory" else 0
        silver_max_awarded = rewards["silver_max"] if run["outcome"] == "victory" else 0
        xp_total += xp_awarded
        silver_total_min += silver_min_awarded
        silver_total_max += silver_max_awarded
        if run["outcome"] == "victory":
            guaranteed_items_total.extend((entry["item"], entry["quantity"]) for entry in rewards["guaranteed_items"])
            possible_items_total.extend((entry["item"], entry["quantity"]) for entry in rewards["possible_items"])
        level = _level_for_xp(xp_total)
        steps.append(
            {
                "index": index,
                "kind": "encounter",
                "key": step["key"],
                "title": authored["encounter_data"].get("title") or step.get("label"),
                "source": authored["source"],
                "xp_awarded": xp_awarded,
                "silver_awarded_min": silver_min_awarded,
                "silver_awarded_max": silver_max_awarded,
                "guaranteed_item_rewards": rewards["guaranteed_items"] if run["outcome"] == "victory" else [],
                "possible_item_rewards": rewards["possible_items"] if run["outcome"] == "victory" else [],
                "xp_before": before_xp,
                "xp_after": xp_total,
                "silver_before_min": before_silver_min,
                "silver_before_max": before_silver_max,
                "silver_after_min": silver_total_min,
                "silver_after_max": silver_total_max,
                "level_before": before_level,
                "level_after": level,
                "outcome": run["outcome"],
                "rounds": run["rounds"],
                "remaining_hp_ratio": run["player_remaining_hp_ratio"],
                "telegraphed_actions": run["telegraphed_actions"],
                "telegraphed_answers": run["telegraphed_interrupts"] + run["telegraphed_redirects"] + run["telegraphed_mitigations"],
                "telegraphed_unanswered": run["telegraphed_unanswered"],
            }
        )

    pacing_flags = _first_hour_pacing_flags(steps, unlock_order_after_ruk)
    return {
        "scenario_key": scenario_key,
        "final_xp": xp_total,
        "final_silver_min": silver_total_min,
        "final_silver_max": silver_total_max,
        "guaranteed_items": _merge_item_rewards(guaranteed_items_total),
        "possible_items": _merge_item_rewards(possible_items_total),
        "final_level": level,
        "steps": steps,
        "post_ruk_unlock_order": unlock_order_after_ruk,
        "post_ruk_leads": [
            {
                "key": quest_key,
                "title": (CONTENT.quests.get(quest_key) or {}).get("title", quest_key),
                "next_step": _quest_next_step(quest_key),
            }
            for quest_key in unlock_order_after_ruk
        ],
        "tracked_quest_transitions": tracked_quest_transitions,
        "pacing_flags": pacing_flags,
    }


def build_act1_spine_report():
    """Audit Act 1 quest handoffs, terminal closure, and trophy proof."""

    quest_keys = list(CONTENT.quests.starting_quests)
    quest_rows = []
    missing_next_steps = []
    terminal_quests = []
    trophy_rewards = []
    for index, quest_key in enumerate(quest_keys, start=1):
        quest = CONTENT.quests.get(quest_key) or {}
        next_step = _quest_next_step(quest_key)
        unlocks = _quests_with_prerequisite(quest_key)
        trophies = list((quest.get("rewards") or {}).get("trophies") or [])
        row = {
            "index": index,
            "key": quest_key,
            "title": quest.get("title", quest_key),
            "region": CONTENT.quests.get_quest_region(quest_key),
            "prerequisites": list(quest.get("prerequisites") or []),
            "unlocks": unlocks,
            "next_step": next_step,
            "trophies": trophies,
            "chapter_complete": quest.get("chapter_complete") or "",
        }
        quest_rows.append(row)
        if not next_step:
            missing_next_steps.append(quest_key)
        if not unlocks:
            terminal_quests.append(quest_key)
        for trophy_key in trophies:
            trophy = CONTENT.systems.trophies.get(trophy_key) or {}
            trophy_rewards.append(
                {
                    "quest": quest_key,
                    "trophy": trophy_key,
                    "name": trophy.get("name", trophy_key),
                    "known": bool(trophy),
                }
            )

    hollow = CONTENT.quests.get("the_hollow_lantern") or {}
    trophy_text = CONTENT.dialogue.get_static_read_response("trophy_vitrine") or ""
    closure = {
        "final_quest": "the_hollow_lantern",
        "chapter_complete": hollow.get("chapter_complete") or "",
        "next_step": _quest_next_step("the_hollow_lantern"),
        "completed_dialogue": {
            npc_key: _dialogue_has_completed_rule(npc_key, "the_hollow_lantern")
            for npc_key in ACT1_CLOSURE_NPCS
        },
        "trophy_vitrine_mentions": {
            entry["trophy"]: entry["name"] in trophy_text
            for entry in trophy_rewards
            if entry.get("known")
        },
    }

    flags = []
    for quest_key in missing_next_steps:
        flags.append(
            {
                "kind": "missing_next_step",
                "quest": quest_key,
                "message": f"Quest {quest_key} has no journal next_step handoff.",
            }
        )
    for entry in trophy_rewards:
        if not entry["known"]:
            flags.append(
                {
                    "kind": "unknown_trophy",
                    "quest": entry["quest"],
                    "message": f"Quest {entry['quest']} rewards unknown trophy {entry['trophy']}.",
                }
            )
    for npc_key, present in closure["completed_dialogue"].items():
        if not present:
            flags.append(
                {
                    "kind": "missing_hollow_lantern_closure_dialogue",
                    "quest": "the_hollow_lantern",
                    "message": f"{npc_key} has no completed dialogue for the Hollow Lantern.",
                }
            )
    for trophy_key, present in closure["trophy_vitrine_mentions"].items():
        if not present:
            flags.append(
                {
                    "kind": "missing_trophy_vitrine_mention",
                    "quest": "the_hollow_lantern",
                    "message": f"Trophy vitrine text does not mention {trophy_key}.",
                }
            )
    if not closure["chapter_complete"]:
        flags.append(
            {
                "kind": "missing_chapter_complete",
                "quest": "the_hollow_lantern",
                "message": "The Hollow Lantern does not mark Act 1 chapter completion.",
            }
        )

    return {
        "quest_count": len(quest_rows),
        "quests": quest_rows,
        "terminal_quests": terminal_quests,
        "trophy_rewards": trophy_rewards,
        "closure": closure,
        "flags": flags,
    }


def render_act1_spine_markdown(report):
    lines = [
        "# Act 1 Spine Audit",
        "",
        f"- Quest count: {report['quest_count']}",
        f"- Terminal quest(s): {', '.join(f'`{key}`' for key in report.get('terminal_quests') or [])}",
        "",
        "## Quest Handoffs",
        "",
    ]
    for row in report["quests"]:
        lines.append(
            f"- {row['index']}. `{row['key']}` ({row['region']}): "
            f"unlocks {row.get('unlocks') or []}; next `{row.get('next_step') or 'MISSING'}`"
        )
    lines.extend(["", "## Act 1 Closure", ""])
    closure = report["closure"]
    lines.append(f"- Final quest: `{closure['final_quest']}`")
    lines.append(f"- Chapter complete: {closure.get('chapter_complete') or 'MISSING'}")
    lines.append(f"- Final next step: {closure.get('next_step') or 'MISSING'}")
    for npc_key, present in closure.get("completed_dialogue", {}).items():
        lines.append(f"- `{npc_key}` Hollow Lantern completion dialogue: {'yes' if present else 'MISSING'}")
    for trophy_key, present in closure.get("trophy_vitrine_mentions", {}).items():
        lines.append(f"- Trophy vitrine mentions `{trophy_key}`: {'yes' if present else 'MISSING'}")
    lines.extend(["", "## Flags", ""])
    if not report.get("flags"):
        lines.append("- No Act 1 spine flags.")
    else:
        for flag in report["flags"]:
            lines.append(f"- `{flag['kind']}` on `{flag['quest']}`: {flag['message']}")
    lines.append("")
    return "\n".join(lines)


def _split_sentences(text):
    normalized = str(text or "").replace("!", ".").replace("?", ".")
    return [part.strip() for part in normalized.split(".") if part.strip()]


def _word_count(text):
    return len([word for word in str(text or "").replace("\n", " ").split(" ") if word.strip()])


def _pattern_counts(text):
    lowered = str(text or "").lower()
    return {
        pattern: lowered.count(pattern)
        for pattern in PROSE_DRIFT_PATTERNS
        if lowered.count(pattern)
    }


def _voice_anchor_hits(text, anchors):
    lowered = str(text or "").lower()
    return sorted(anchor for anchor in anchors if anchor in lowered)


def _room_region(room):
    room_id = str(room.get("id") or "")
    for prefix in ACT1_REGION_PREFIXES:
        if room_id.startswith(prefix):
            return prefix.rstrip("_")
    return str(room.get("map_region") or room.get("zone") or "other").lower().replace(" ", "_")


def build_prose_voice_report():
    """Audit Act 1 prose cadence and NPC voice anchors."""

    rooms = []
    region_buckets = {}
    for room in CONTENT.world.rooms:
        room_id = str(room.get("id") or "")
        if not any(room_id.startswith(prefix) for prefix in ACT1_REGION_PREFIXES):
            continue
        desc = str(room.get("desc") or "")
        sentences = _split_sentences(desc)
        pattern_counts = _pattern_counts(desc)
        region = _room_region(room)
        row = {
            "id": room_id,
            "key": room.get("key") or room_id,
            "region": region,
            "word_count": _word_count(desc),
            "sentence_count": len(sentences),
            "avg_sentence_words": round(_word_count(desc) / float(max(1, len(sentences))), 2),
            "pattern_counts": pattern_counts,
        }
        rooms.append(row)
        bucket = region_buckets.setdefault(region, {"rooms": 0, "words": 0, "patterns": {}})
        bucket["rooms"] += 1
        bucket["words"] += row["word_count"]
        for pattern, count in pattern_counts.items():
            bucket["patterns"][pattern] = bucket["patterns"].get(pattern, 0) + count

    readables = []
    for entity_id, text in sorted(CONTENT.dialogue.static_read_responses.items()):
        pattern_counts = _pattern_counts(text)
        readables.append(
            {
                "id": entity_id,
                "word_count": _word_count(text),
                "sentence_count": len(_split_sentences(text)),
                "pattern_counts": pattern_counts,
            }
        )

    npc_rows = []
    for npc_key, anchors in sorted(NPC_VOICE_ANCHORS.items()):
        rules = CONTENT.dialogue.get_talk_rules(npc_key)
        combined = " ".join(str(rule.get("text") or "") for rule in rules)
        hits = _voice_anchor_hits(combined, anchors)
        npc_rows.append(
            {
                "npc": npc_key,
                "rules": len(rules),
                "anchor_hits": hits,
                "missing_anchors": [anchor for anchor in anchors if anchor not in hits],
                "word_count": _word_count(combined),
                "pattern_counts": _pattern_counts(combined),
            }
        )

    flags = []
    for room in rooms:
        if room["avg_sentence_words"] > 34:
            flags.append(
                {
                    "kind": "long_room_sentence_average",
                    "target": room["id"],
                    "message": f"{room['key']} averages {room['avg_sentence_words']} words per sentence.",
                }
            )
        if sum(room["pattern_counts"].values()) >= 2:
            flags.append(
                {
                    "kind": "repeated_room_abstraction",
                    "target": room["id"],
                    "message": f"{room['key']} uses repeated abstraction patterns: {room['pattern_counts']}.",
                }
            )
    for npc in npc_rows:
        if npc["rules"] and len(npc["anchor_hits"]) < 2:
            flags.append(
                {
                    "kind": "thin_voice_anchor",
                    "target": npc["npc"],
                    "message": f"{npc['npc']} has fewer than two voice anchor hits.",
                }
            )

    return {
        "rooms": rooms,
        "regions": region_buckets,
        "readables": readables,
        "npcs": npc_rows,
        "flags": flags,
    }


def render_prose_voice_markdown(report):
    lines = [
        "# Act 1 Prose and Voice Audit",
        "",
        "## Region Cadence",
        "",
    ]
    for region, data in sorted(report["regions"].items()):
        avg_words = round(data["words"] / float(max(1, data["rooms"])), 2)
        lines.append(
            f"- `{region}`: {data['rooms']} room(s), avg {avg_words} words, patterns {data.get('patterns') or {}}"
        )
    lines.extend(["", "## NPC Voice Anchors", ""])
    for npc in report["npcs"]:
        lines.append(
            f"- `{npc['npc']}`: {npc['rules']} rule(s), anchors {npc['anchor_hits']}, "
            f"missing {npc['missing_anchors']}"
        )
    lines.extend(["", "## Room Pattern Watch", ""])
    watched_rooms = [room for room in report["rooms"] if room.get("pattern_counts")]
    if not watched_rooms:
        lines.append("- No repeated abstraction patterns in Act 1 room descriptions.")
    else:
        for room in watched_rooms[:40]:
            lines.append(f"- `{room['id']}`: {room['pattern_counts']}")
    lines.extend(["", "## Flags", ""])
    if not report["flags"]:
        lines.append("- No prose/voice audit flags.")
    else:
        for flag in report["flags"]:
            lines.append(f"- `{flag['kind']}` on `{flag['target']}`: {flag['message']}")
    lines.append("")
    return "\n".join(lines)


def render_first_hour_route_markdown(report):
    silver_total = (
        str(report["final_silver_min"])
        if report["final_silver_min"] == report["final_silver_max"]
        else f"{report['final_silver_min']}-{report['final_silver_max']}"
    )
    lines = [
        "# First Hour Route Summary",
        "",
        f"- Scenario: `{report['scenario_key']}`",
        f"- Final XP/level: {report['final_xp']} XP, level {report['final_level']}",
        f"- Reward totals: {silver_total} silver, "
        f"{len(report.get('guaranteed_items') or [])} guaranteed item type(s), "
        f"{len(report.get('possible_items') or [])} possible drop type(s)",
        f"- First post-Ruk lead: `{(report.get('post_ruk_unlock_order') or [''])[0]}`",
        "",
        "## Route",
        "",
    ]
    for step in report["steps"]:
        if step["kind"] == "quest":
            item_text = ""
            if step.get("item_rewards"):
                item_text = ", items " + ", ".join(
                    f"{entry['item']} x{entry['quantity']}" for entry in step["item_rewards"]
                )
            if step.get("blocked"):
                lines.append(
                    f"- {step['index']}. Quest `{step['key']}`: blocked by `{step['blocked_by']}`, "
                    f"level {step['level_before']} -> {step['level_after']}"
                )
                continue
            lines.append(
                f"- {step['index']}. Quest `{step['key']}`: +{step['xp_awarded']} XP, "
                f"+{step['silver_awarded']} silver{item_text}, "
                f"level {step['level_before']} -> {step['level_after']}, "
                f"tracked `{step.get('tracked_quest_before')}` -> `{step.get('tracked_quest_after')}`, "
                f"unlocks {step.get('unlocks') or []}"
            )
        else:
            silver = (
                str(step["silver_awarded_min"])
                if step["silver_awarded_min"] == step["silver_awarded_max"]
                else f"{step['silver_awarded_min']}-{step['silver_awarded_max']}"
            )
            lines.append(
                f"- {step['index']}. Encounter `{step['key']}`: {step['outcome']}, "
                f"+{step['xp_awarded']} XP, {silver} silver, "
                f"level {step['level_before']} -> {step['level_after']}, "
                f"{step['rounds']} rounds, HP {step['remaining_hp_ratio']}, "
                f"telegraphs {step['telegraphed_answers']}/{step['telegraphed_actions']} "
                f"({step['telegraphed_unanswered']} unanswered)"
            )
    lines.extend(["", "## Post-Ruk Leads", ""])
    for lead in report.get("post_ruk_leads") or []:
        lines.append(f"- `{lead['key']}`: {lead.get('next_step') or 'MISSING next_step'}")
    lines.extend(["", "## Tracked Quest Transitions", ""])
    for transition in report.get("tracked_quest_transitions") or []:
        lines.append(f"- `{transition['step']}`: `{transition['before']}` -> `{transition['after']}`")
    lines.extend(["", "## Pacing Flags", ""])
    if not report.get("pacing_flags"):
        lines.append("- No pacing flags.")
    else:
        for flag in report["pacing_flags"]:
            lines.append(f"- `{flag['kind']}` on `{flag['step']}`: {flag['message']}")
    lines.append("")
    return "\n".join(lines)


def _ability_role(ability):
    target = str((ability or {}).get("target") or "")
    icon = str((ability or {}).get("icon_role") or "")
    if target == "ally" or icon in {"heal", "cleanse", "blessing"}:
        return "support"
    if target == "self" or icon in {"guard", "mobility", "stealth"}:
        return "defense"
    if target == "none" or icon in {"field", "barrage", "rally"}:
        return "field"
    if icon in {"frost", "root", "taunt", "mark", "poison"}:
        return "control"
    return "damage"


def build_ability_audit_report():
    """Return a compact class ability audit from authored character content."""

    rows = []
    by_class = {}
    for class_key, class_data in sorted(CHARACTER_CONTENT.classes.items()):
        entries = []
        for unlock_level, ability_name in class_data.get("progression", []):
            ability_key = str(ability_name or "").replace(" ", "").lower()
            ability = dict(ABILITY_LIBRARY.get(ability_key) or {})
            if not ability:
                continue
            timing = get_ability_atb_profile(ability_key, ability)
            row = {
                "class": class_key,
                "level": int(unlock_level or 1),
                "ability_key": ability_key,
                "name": ability.get("name", ability_name),
                "role": _ability_role(ability),
                "resource": ability.get("resource"),
                "cost": int(ability.get("cost", 0) or 0),
                "target": ability.get("target"),
                "gauge_cost": int(timing.get("gauge_cost", 0) or 0),
                "windup_ticks": int(timing.get("windup_ticks", 0) or 0),
                "recovery_ticks": int(timing.get("recovery_ticks", 0) or 0),
                "cooldown_ticks": int(timing.get("cooldown_ticks", 0) or 0),
                "telegraph": bool(timing.get("telegraph")),
            }
            rows.append(row)
            entries.append(row)
        by_class[class_key] = entries
    return {"rows": rows, "by_class": by_class}


def render_ability_audit_markdown(report):
    lines = [
        "# Ability Audit",
        "",
        "This audit is generated from character content and ATB timing profiles.",
        "",
    ]
    for class_key, entries in report.get("by_class", {}).items():
        lines.extend([f"## {class_key.title()}", "", "| Level | Ability | Role | Resource | Cost | Target | ATB |", "| --- | --- | --- | --- | ---: | --- | --- |"])
        for entry in entries:
            atb = f"{entry['gauge_cost']}g / W{entry['windup_ticks']} R{entry['recovery_ticks']} C{entry['cooldown_ticks']}"
            if entry["telegraph"]:
                atb += " / telegraph"
            lines.append(
                f"| {entry['level']} | `{entry['ability_key']}` | {entry['role']} | {entry['resource']} | {entry['cost']} | {entry['target']} | {atb} |"
            )
        lines.append("")
    return "\n".join(lines)


def build_item_rarity_report():
    counts = {}
    rare_plus = []
    for template_id, item in sorted(CONTENT.items.item_templates.items()):
        rarity = str(item.get("rarity") or "common").lower()
        counts[rarity] = counts.get(rarity, 0) + 1
        if rarity in {"rare", "epic", "legendary"}:
            rare_plus.append(
                {
                    "template_id": template_id,
                    "name": item.get("name", template_id),
                    "rarity": rarity,
                    "kind": item.get("kind"),
                    "slot": item.get("slot"),
                }
            )
    return {
        "counts": dict(sorted(counts.items())),
        "rare_plus": rare_plus,
    }


def render_item_rarity_markdown(report):
    lines = [
        "# Item Rarity Audit",
        "",
        "Act 1 policy: common by default, uncommon for useful named/crafted gear, rare for standout boss or capstone gear, story for proof/key items.",
        "",
        "## Distribution",
        "",
    ]
    for rarity, count in report.get("counts", {}).items():
        lines.append(f"- `{rarity}`: {count}")
    lines.extend(["", "## Rare Or Higher", ""])
    rare_plus = report.get("rare_plus") or []
    if not rare_plus:
        lines.append("- No rare+ gameplay items.")
    else:
        for item in rare_plus:
            slot = f", {item['slot']}" if item.get("slot") else ""
            lines.append(f"- `{item['template_id']}`: {item['name']} ({item['rarity']}{slot})")
    lines.append("")
    return "\n".join(lines)


def render_resource_economy_markdown(report):
    lines = [
        "# Resource Economy Audit",
        "",
        f"- Runs covered: {report['totals']['runs']}",
        f"- Primary runs: {report['totals']['primary_runs']}",
        f"- Restore item uses: {report['totals']['restore_item_uses']}",
        f"- Low-relevance primary runs sampled: {report['totals']['low_relevance_primary_runs']}",
        "",
        "## Scenario Economy",
        "",
    ]
    for row in report.get("scenario_rows", []):
        lines.append(
            f"- `{row['scenario_key']}` ({row['balance_bucket']}): {row['wins']}/{row['runs']} wins, "
            f"HP {row['avg_remaining_hp_ratio']}, mana {row['avg_remaining_mana_ratio']}, "
            f"stamina {row['avg_remaining_stamina_ratio']}, resource floor {row['avg_lowest_primary_resource_ratio']}, "
            f"spent mana {row['avg_mana_spent']}, spent stamina {row['avg_stamina_spent']}, "
            f"healing {row['avg_healing_done']}, restores {row['restore_item_uses']}"
        )
    lines.extend(["", "## Class Spend", ""])
    for row in report.get("class_rows", []):
        lines.append(
            f"- `{row['class']}`: runs {row['runs']}, avg mana spent {row['avg_mana_spent']}, "
            f"avg stamina spent {row['avg_stamina_spent']}, ability/basic {row['ability_actions']}/{row['basic_attacks']}, "
            f"ability ratio {row['ability_action_ratio']}, healing {row['avg_healing_done']}"
        )
    lines.extend(["", "## Top Ability Uses", ""])
    for row in report.get("top_abilities", []):
        lines.append(f"- `{row['ability_key']}`: {row['uses']} uses")
    lines.extend(["", "## Low-Relevance Encounters", ""])
    if not report.get("low_relevance_runs"):
        lines.append("- No primary victory runs met the low-relevance threshold.")
    else:
        for run in report.get("low_relevance_runs", []):
            lines.append(
                f"- `{run['scenario_key']}` vs `{run['encounter_key']}`: HP {run['player_remaining_hp_ratio']}, "
                f"resource floor {run.get('lowest_primary_resource_ratio', 1.0)}, rounds {run['rounds']}"
            )
    lines.extend(["", "## Notes", ""])
    for note in report.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def render_markdown(summary):
    lines = [
        "# Combat Simulation Summary",
        "",
        f"- Encounter definitions covered: {summary['totals']['encounters']}",
        f"- Scenario runs: {summary['totals']['runs']}",
        f"- Victories/defeats/timeouts: {summary['totals']['victories']}/{summary['totals']['defeats']}/{summary['totals']['timeouts']}",
        f"- Near wipes: {summary['totals']['near_wipes']}",
        f"- Primary balance runs: {summary['totals'].get('primary_runs', summary['totals']['runs'])}",
        f"- Primary victories/defeats/timeouts: {summary['totals'].get('primary_victories', summary['totals']['victories'])}/{summary['totals'].get('primary_defeats', summary['totals']['defeats'])}/{summary['totals'].get('primary_timeouts', summary['totals']['timeouts'])}",
        f"- Stress-test runs: {summary['totals'].get('stress_runs', 0)}",
        f"- Stress-test victories/defeats/timeouts: {summary['totals'].get('stress_victories', 0)}/{summary['totals'].get('stress_defeats', 0)}/{summary['totals'].get('stress_timeouts', 0)}",
        "",
        "## Scenario Summary",
        "",
    ]
    for key, data in summary["scenario_summary"].items():
        bucket = data.get("balance_bucket", "primary")
        lines.append(
            f"- `{key}` ({bucket}): {data['victories']}/{data['runs']} wins, "
            f"{data['defeats']} defeats, {data['timeouts']} timeouts, "
            f"near wipes {data['near_wipes']}, avg rounds {data['avg_rounds']}, "
            f"avg remaining HP {data['avg_remaining_hp_ratio']}, "
            f"resource floor {data['avg_lowest_primary_resource_ratio']}, "
            f"ability ratio {data['avg_ability_action_ratio']}, "
            f"telegraph answer rate {data['telegraph_answer_rate']}"
        )
    lines.extend(["", "## Rank Summary", ""])
    for key, data in summary["rank_summary"].items():
        lines.append(
            f"- `{key}`: {data['victories']}/{data['runs']} wins, "
            f"near wipes {data['near_wipes']}, avg rounds {data['avg_rounds']}, "
            f"avg remaining HP {data['avg_remaining_hp_ratio']}, "
            f"resource floor {data['avg_lowest_primary_resource_ratio']}, "
            f"ability ratio {data['avg_ability_action_ratio']}, "
            f"telegraph answer rate {data['telegraph_answer_rate']}"
        )
    lines.extend(["", "## Encounter Risk List", ""])
    if not summary["encounter_risks"]:
        lines.append("- No encounter risk data.")
    else:
        for risk in summary["encounter_risks"]:
            lines.append(
                f"- `{risk['encounter_key']}` ({risk['rank_bucket']}): win rate {risk['win_rate']}, "
                f"near wipes {risk['near_wipes']}, avg rounds {risk['avg_rounds']}, "
                f"avg remaining HP {risk['avg_remaining_hp_ratio']}, "
                f"resource floor {risk['avg_lowest_primary_resource_ratio']}"
            )
    lines.extend(["", "## Primary Failure Set", ""])
    if not summary.get("primary_failures"):
        lines.append("- No primary scenario failures.")
    else:
        for run in summary.get("primary_failures", []):
            lines.append(
                f"- `{run['scenario_key']}` vs `{run['encounter_key']}`: {run['outcome']}, "
                f"rounds {run['rounds']}, HP {run['player_remaining_hp_ratio']}, "
                f"resource floor {run.get('lowest_primary_resource_ratio', 1.0)}, "
                f"enemies {', '.join(run.get('enemy_templates') or [])}"
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
            f"resource floor {run.get('lowest_primary_resource_ratio', 1.0)}, "
            f"ability ratio {run.get('ability_action_ratio', 0.0)}, "
            f"telegraphs {run['telegraphed_actions']}/{run['telegraphed_response_actions']}/{run['telegraphed_interrupts']}"
        )
    lines.extend(["", "## Near Wipes", ""])
    if not summary["near_wipes"]:
        lines.append("- No near wipes.")
    else:
        for run in summary["near_wipes"]:
            lines.append(
                f"- `{run['scenario_key']}` vs `{run['encounter_key']}`: rounds {run['rounds']}, "
                f"remaining HP {run['player_remaining_hp_ratio']}, damage taken {run['damage_taken']}"
            )
    lines.extend(["", "## Longest Victories", ""])
    for run in summary["longest_victories"]:
        lines.append(
            f"- `{run['scenario_key']}` vs `{run['encounter_key']}`: rounds {run['rounds']}, "
            f"remaining HP {run['player_remaining_hp_ratio']}, rank {run['rank_bucket']}"
        )
    lines.extend(["", "## Telegraph Risks", ""])
    if not summary["telegraph_risks"]:
        lines.append("- No unanswered telegraph risks.")
    else:
        for run in summary["telegraph_risks"]:
            lines.append(
                f"- `{run['scenario_key']}` vs `{run['encounter_key']}`: {run['telegraphed_actions']} telegraphs, "
                f"{run['telegraphed_unanswered']} unanswered, outcome {run['outcome']}, remaining HP {run['player_remaining_hp_ratio']}"
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
    first_hour_route_json = output_path / "first_hour_route.json"
    first_hour_route_md = output_path / "first_hour_route.md"
    act1_spine_json = output_path / "act1_spine.json"
    act1_spine_md = output_path / "act1_spine.md"
    prose_voice_json = output_path / "prose_voice.json"
    prose_voice_md = output_path / "prose_voice.md"
    ability_audit_json = output_path / "ability_audit.json"
    ability_audit_md = output_path / "ability_audit.md"
    item_rarity_json = output_path / "item_rarity.json"
    item_rarity_md = output_path / "item_rarity.md"
    resource_economy_json = output_path / "resource_economy.json"
    resource_economy_md = output_path / "resource_economy.md"
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
    first_hour_route = {
        scenario["key"]: build_first_hour_route_report(
            scenario_key=scenario["key"],
            base_seed=base_seed,
            max_rounds=max_rounds,
        )
        for scenario in PARTY_SCENARIOS
    }
    first_hour_route_json.write_text(json.dumps(first_hour_route, indent=2), encoding="utf-8")
    first_hour_route_md.write_text(
        "\n".join(render_first_hour_route_markdown(report) for report in first_hour_route.values()),
        encoding="utf-8",
    )
    act1_spine = build_act1_spine_report()
    act1_spine_json.write_text(json.dumps(act1_spine, indent=2), encoding="utf-8")
    act1_spine_md.write_text(render_act1_spine_markdown(act1_spine), encoding="utf-8")
    prose_voice = build_prose_voice_report()
    prose_voice_json.write_text(json.dumps(prose_voice, indent=2), encoding="utf-8")
    prose_voice_md.write_text(render_prose_voice_markdown(prose_voice), encoding="utf-8")
    ability_audit = build_ability_audit_report()
    ability_audit_json.write_text(json.dumps(ability_audit, indent=2), encoding="utf-8")
    ability_audit_md.write_text(render_ability_audit_markdown(ability_audit), encoding="utf-8")
    item_rarity_report = build_item_rarity_report()
    item_rarity_json.write_text(json.dumps(item_rarity_report, indent=2), encoding="utf-8")
    item_rarity_md.write_text(render_item_rarity_markdown(item_rarity_report), encoding="utf-8")
    resource_economy_report = build_resource_economy_report(runs)
    resource_economy_json.write_text(json.dumps(resource_economy_report, indent=2), encoding="utf-8")
    resource_economy_md.write_text(render_resource_economy_markdown(resource_economy_report), encoding="utf-8")
    return {
        "output_dir": str(output_path),
        "report_json": str(report_json),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "interrupt_opportunity_json": str(interrupt_opportunity_json),
        "interrupt_opportunity_md": str(interrupt_opportunity_md),
        "first_hour_route_json": str(first_hour_route_json),
        "first_hour_route_md": str(first_hour_route_md),
        "act1_spine_json": str(act1_spine_json),
        "act1_spine_md": str(act1_spine_md),
        "prose_voice_json": str(prose_voice_json),
        "prose_voice_md": str(prose_voice_md),
        "ability_audit_json": str(ability_audit_json),
        "ability_audit_md": str(ability_audit_md),
        "item_rarity_json": str(item_rarity_json),
        "item_rarity_md": str(item_rarity_md),
        "resource_economy_json": str(resource_economy_json),
        "resource_economy_md": str(resource_economy_md),
        "trace_dir": str(trace_dir),
        "trace_files": trace_files,
        "runs": runs,
        "summary": summary,
        "interrupt_opportunity_report": interrupt_opportunity_report,
        "first_hour_route": first_hour_route,
        "act1_spine": act1_spine,
        "prose_voice": prose_voice,
        "ability_audit": ability_audit,
        "item_rarity_report": item_rarity_report,
        "resource_economy_report": resource_economy_report,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Brave's deterministic combat telemetry harness.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--base-seed", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=160)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--trace-encounter", action="append", default=[])
    parser.add_argument("--trace-scenario", action="append", default=[])
    parser.add_argument("--progression-levels", action="store_true")
    parser.add_argument("--first-hour-route", action="store_true")
    args = parser.parse_args()

    if args.progression_levels:
        runs = build_progression_runs(base_seed=args.base_seed, max_rounds=args.max_rounds, limit=args.limit)
        summary = build_summary(runs)
        print(render_markdown(summary))
        return

    if args.first_hour_route:
        report = build_first_hour_route_report(base_seed=args.base_seed, max_rounds=args.max_rounds)
        print(render_first_hour_route_markdown(report))
        return

    result = run_harness(
        output_dir=args.output_dir,
        base_seed=args.base_seed,
        max_rounds=args.max_rounds,
        limit=args.limit,
        trace_encounters=args.trace_encounter,
        trace_scenarios=args.trace_scenario,
    )
    print(Path(result["summary_md"]).read_text(encoding="utf-8"))
    print(f"\nSaved combat simulation outputs to {result['output_dir']}")


if __name__ == "__main__":
    main()
