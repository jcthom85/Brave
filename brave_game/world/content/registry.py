"""Registry-backed access to Brave authored content.

This module creates a stable runtime boundary between engine code and content
storage. The current implementation loads Brave's authored domains from JSON
packs while preserving the same typed lookup APIs for runtime code.
"""

from dataclasses import dataclass
import json
from pathlib import Path

CONTENT_ROOT = Path(__file__).resolve().parent
PACK_ROOT = CONTENT_ROOT / "packs"
CORE_PACK_ROOT = PACK_ROOT / "core"
CHARACTERS_PACK_PATH = CORE_PACK_ROOT / "characters.json"
ITEMS_PACK_PATH = CORE_PACK_ROOT / "items.json"
QUESTS_PACK_PATH = CORE_PACK_ROOT / "quests.json"
WORLD_PACK_PATH = CORE_PACK_ROOT / "world.json"
ENCOUNTERS_PACK_PATH = CORE_PACK_ROOT / "encounters.json"
DIALOGUE_PACK_PATH = CORE_PACK_ROOT / "dialogue.json"
SYSTEMS_PACK_PATH = CORE_PACK_ROOT / "systems.json"


@dataclass(frozen=True)
class CharacterContentRegistry:
    source_path: str
    primary_stats: tuple
    starting_race: str
    starting_class: str
    max_level: int
    vertical_slice_classes: tuple
    xp_for_level: dict
    races: dict
    classes: dict
    ability_library: dict
    implemented_ability_keys: set
    passive_ability_bonuses: dict

    def get_race(self, race_key):
        return self.races[race_key]

    def get_class(self, class_key):
        return self.classes[class_key]

    def get_ability(self, ability_key):
        return self.ability_library.get(ability_key)

    def get_passive(self, ability_key):
        return self.passive_ability_bonuses.get(ability_key)

    def ability_key(self, name):
        return "".join(char for char in (name or "").lower() if char.isalnum())

    def get_progression_ability_names(self, class_key, level):
        class_data = self.get_class(class_key)
        return [ability for unlock_level, ability in class_data["progression"] if unlock_level <= level]

    def split_unlocked_abilities(self, class_key, level):
        actions = []
        passives = []
        unknown = []
        for ability_name in self.get_progression_ability_names(class_key, level):
            key = self.ability_key(ability_name)
            if key in self.implemented_ability_keys:
                actions.append(ability_name)
            elif key in self.passive_ability_bonuses:
                passives.append(ability_name)
            else:
                unknown.append(ability_name)
        return actions, passives, unknown

    def get_passive_ability_bonuses(self, class_key, level):
        totals = {}
        _actions, passives, _unknown = self.split_unlocked_abilities(class_key, level)
        for ability_name in passives:
            bonus_def = self.get_passive(self.ability_key(ability_name)) or {}
            for stat, amount in bonus_def.get("bonuses", {}).items():
                totals[stat] = totals.get(stat, 0) + amount
        return totals

    def xp_needed_for_next_level(self, level):
        if level >= self.max_level:
            return None
        return self.xp_for_level[level + 1]


@dataclass(frozen=True)
class ItemContentRegistry:
    source_path: str
    equipment_slots: tuple
    item_class_requirements: dict
    item_templates: dict
    starter_consumables: tuple
    starter_loadouts: dict
    bonus_labels: dict
    rarities: dict

    def get(self, template_id):
        return self.item_templates.get(template_id)

    def get_item_category(self, item_or_template):
        item = item_or_template if isinstance(item_or_template, dict) else self.get(item_or_template)
        if not item:
            return None
        category = item.get("category")
        if category:
            return category
        if item.get("kind") == "meal":
            return "consumable"
        return item.get("kind")

    def get_item_use_profile(self, item_or_template, *, context=None):
        item = item_or_template if isinstance(item_or_template, dict) else self.get(item_or_template)
        if not item:
            return None

        use = dict(item.get("use") or {})
        if item.get("kind") == "meal":
            use.setdefault("verb", "eat")
            use.setdefault("contexts", ("explore", "combat"))
            use.setdefault("target", "self")
            use.setdefault("effect_type", "meal")
            if item.get("restore"):
                use.setdefault("restore", dict(item.get("restore", {})))
            if item.get("meal_bonuses"):
                use.setdefault("buffs", dict(item.get("meal_bonuses", {})))

        contexts = tuple(use.get("contexts") or ())
        if context and contexts and context not in contexts:
            return None
        if not use:
            return None
        use["contexts"] = contexts
        return use

    def get_item_rarity_key(self, item_or_template):
        item = item_or_template if isinstance(item_or_template, dict) else self.get(item_or_template)
        rarity_key = str((item or {}).get("rarity") or "common").strip().lower()
        return rarity_key if rarity_key in self.rarities else "common"

    def get_item_rarity(self, item_or_template):
        rarity_key = self.get_item_rarity_key(item_or_template)
        return self.rarities.get(rarity_key) or self.rarities.get("common") or {
            "label": rarity_key.title(),
            "tone": "rarity-common",
            "icon": "diamond",
            "order": 0,
        }

    def get_item_rarity_label(self, item_or_template):
        rarity = self.get_item_rarity(item_or_template)
        return str(rarity.get("label") or self.get_item_rarity_key(item_or_template).title())

    def get_item_rarity_tone(self, item_or_template):
        rarity = self.get_item_rarity(item_or_template)
        return str(rarity.get("tone") or f"rarity-{self.get_item_rarity_key(item_or_template)}")

    def get_item_rarity_icon(self, item_or_template):
        rarity = self.get_item_rarity(item_or_template)
        return str(rarity.get("icon") or "diamond")

    def is_consumable_item(self, item_or_template, *, context=None):
        return self.get_item_use_profile(item_or_template, context=context) is not None

    def match_inventory_item(self, character, query, *, context=None, category=None, verb=None):
        if not query:
            return None

        token = self._normalize_item_token(query)
        matches = []
        for entry in (character.db.brave_inventory or []):
            template_id = entry.get("template")
            quantity = int(entry.get("quantity", 0) or 0)
            item = self.get(template_id)
            if not item or quantity <= 0:
                continue
            if category and self.get_item_category(item) != category:
                continue
            use = self.get_item_use_profile(item, context=context)
            if verb and (not use or use.get("verb") != verb):
                continue
            if context and not use:
                continue
            names = [template_id, item.get("name", "")]
            if any(token == self._normalize_item_token(name) or token in self._normalize_item_token(name) for name in names):
                matches.append(template_id)
        if not matches:
            return None
        return matches[0] if len(matches) == 1 else matches

    def format_bonus_summary(self, item_data):
        bonuses = item_data.get("bonuses", {})
        if not bonuses:
            return ""

        parts = []
        for key, value in bonuses.items():
            label = self.bonus_labels.get(key, key.replace("_", " ").title())
            sign = "+" if value >= 0 else ""
            parts.append(f"{label} {sign}{value}")
        return ", ".join(parts)

    def get_item_allowed_classes(self, item_or_template):
        item = item_or_template if isinstance(item_or_template, dict) else self.get(item_or_template)
        if not item or item.get("kind") != "equipment":
            return ()

        template_id = None
        if not isinstance(item_or_template, dict):
            template_id = item_or_template
        else:
            template_id = item.get("template") or item.get("id")
            if not template_id:
                for key, value in self.item_templates.items():
                    if value is item or value == item:
                        template_id = key
                        break
        return tuple(self.item_class_requirements.get(template_id, ()))

    def is_equipment_allowed_for_class(self, item_or_template, class_key):
        item = item_or_template if isinstance(item_or_template, dict) else self.get(item_or_template)
        if not item or item.get("kind") != "equipment":
            return True
        if str(class_key or "").lower() == "warrior":
            return True

        allowed = self.get_item_allowed_classes(item_or_template)
        return not allowed or str(class_key or "").lower() in allowed

    def format_allowed_class_summary(self, item_or_template):
        allowed = self.get_item_allowed_classes(item_or_template)
        if not allowed:
            return ""
        return "Allowed: " + ", ".join(class_key.replace("_", " ").title() for class_key in allowed)

    @staticmethod
    def _normalize_item_token(value):
        return "".join(char for char in (value or "").lower() if char.isalnum())


@dataclass(frozen=True)
class QuestContentRegistry:
    source_path: str
    starting_quests: list
    quest_regions: dict
    quests: dict

    def get(self, quest_key):
        return self.quests.get(quest_key)

    def get_quest_region(self, quest_key):
        return self.quest_regions.get(quest_key, "Other Fronts")

    def group_quest_keys_by_region(self, quest_keys):
        grouped = []
        buckets = {}
        for quest_key in quest_keys:
            region = self.get_quest_region(quest_key)
            if region not in buckets:
                buckets[region] = []
                grouped.append((region, buckets[region]))
            buckets[region].append(quest_key)
        return grouped


@dataclass(frozen=True)
class WorldContentRegistry:
    source_path: str
    rooms: list
    exits: list
    entities: list

    def get_room(self, room_id):
        for room in self.rooms:
            if room.get("id") == room_id:
                return room
        return None

    def get_entity(self, entity_id):
        for entity in self.entities:
            if entity.get("id") == entity_id:
                return entity
        return None


@dataclass(frozen=True)
class EncounterContentRegistry:
    source_path: str
    enemy_templates: dict
    room_encounters: dict
    roaming_parties: dict
    enemy_temperament_overrides: dict
    temperament_labels: dict

    def get_enemy_template(self, template_key):
        return self.enemy_templates.get(template_key)

    def get_room_encounters(self, room_id):
        return self.room_encounters.get(room_id, [])

    def get_roaming_party(self, party_key):
        return self.roaming_parties.get(party_key)

    def get_roaming_parties(self):
        return list(self.roaming_parties.values())

    def get_enemy_temperament(self, template_key, template=None):
        template = template or self.enemy_templates[template_key]
        if template_key in self.enemy_temperament_overrides:
            return self.enemy_temperament_overrides[template_key]

        tags = set(template.get("tags") or [])
        if "boss" in tags:
            return "relentless"
        if tags.intersection({"goblin", "bandit", "raider", "soldier", "undead"}):
            return "aggressive"
        if tags.intersection({"spider", "plant", "web", "moss", "fey"}):
            return "territorial"
        if tags.intersection({"wolf", "rat", "beast", "crow"}):
            return "wary"
        return "aggressive"

    def get_enemy_temperament_label(self, temperament):
        return self.temperament_labels.get(temperament, str(temperament or "").title() or "Aggressive")

    def get_enemy_rank(self, template_key, template=None):
        template = template or self.enemy_templates[template_key]
        xp_value = max(1, int(template.get("xp", 1)))
        tags = set(template.get("tags") or [])
        rank = max(1, int(round((xp_value + 10) / 25.0)))
        if "boss" in tags:
            rank += 1
        return rank

    @staticmethod
    def get_relative_threat_label(enemy_rank, effective_party_level):
        delta = float(effective_party_level or 1) - float(enemy_rank or 1)
        if delta >= 2.5:
            return "Trivial"
        if delta >= 1.0:
            return "Fair"
        if delta >= -0.5:
            return "Dangerous"
        return "Deadly"


@dataclass(frozen=True)
class DialogueContentRegistry:
    source_path: str
    talk_rules: dict
    static_read_responses: dict

    def get_talk_rules(self, entity_id):
        return self.talk_rules.get(entity_id, ())

    def get_static_read_response(self, entity_id):
        return self.static_read_responses.get(entity_id)


@dataclass(frozen=True)
class SystemsContentRegistry:
    source_path: str
    fishing_spots: dict
    fishing_rods: dict
    fishing_lures: dict
    fishing_behaviors: dict
    cooking_recipes: dict
    tinkering_recipes: dict
    cozy_bonus: dict
    outfitters_room_id: str
    shift_outcomes: tuple
    forge_room_id: str
    forge_recipes: dict
    portals: dict
    portal_status_labels: dict
    trophies: dict
    boss_gates: dict

    def format_ingredient_list(self, ingredients, item_lookup):
        parts = []
        for template_id, quantity in ingredients.items():
            item_name = item_lookup[template_id]["name"]
            parts.append(f"{item_name} x{quantity}")
        return ", ".join(parts)

    def get_portal(self, portal_key):
        return self.portals.get(portal_key)

    def get_portal_status_label(self, status_key):
        return self.portal_status_labels.get(status_key, str(status_key or "").title())

    def get_boss_gate(self, gate_key):
        return self.boss_gates.get(gate_key)


@dataclass(frozen=True)
class BraveContentRegistry:
    characters: CharacterContentRegistry
    items: ItemContentRegistry
    quests: QuestContentRegistry
    world: WorldContentRegistry
    encounters: EncounterContentRegistry
    dialogue: DialogueContentRegistry
    systems: SystemsContentRegistry



def _load_json_pack(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)



def _build_character_registry_from_payload(payload, source_path):
    return CharacterContentRegistry(
        source_path=str(source_path),
        primary_stats=tuple(payload.get("primary_stats", ())),
        starting_race=str(payload.get("starting_race", "")),
        starting_class=str(payload.get("starting_class", "")),
        max_level=int(payload.get("max_level", 0)),
        vertical_slice_classes=tuple(payload.get("vertical_slice_classes", ())),
        xp_for_level={int(level): amount for level, amount in payload.get("xp_for_level", {}).items()},
        races=dict(payload.get("races", {})),
        classes=dict(payload.get("classes", {})),
        ability_library=dict(payload.get("ability_library", {})),
        implemented_ability_keys=set(payload.get("implemented_ability_keys", [])),
        passive_ability_bonuses=dict(payload.get("passive_ability_bonuses", {})),
    )


def _build_character_registry():
    return _build_character_registry_from_payload(_load_json_pack(CHARACTERS_PACK_PATH), CHARACTERS_PACK_PATH)


def _build_item_registry_from_payload(payload, source_path):
    return ItemContentRegistry(
        source_path=str(source_path),
        equipment_slots=tuple(payload.get("equipment_slots", ())),
        item_class_requirements={
            template_id: tuple(class_keys or ())
            for template_id, class_keys in payload.get("item_class_requirements", {}).items()
        },
        item_templates=dict(payload.get("item_templates", {})),
        starter_consumables=tuple(tuple(entry) for entry in payload.get("starter_consumables", [])),
        starter_loadouts=dict(payload.get("starter_loadouts", {})),
        bonus_labels=dict(payload.get("bonus_labels", {})),
        rarities=dict(payload.get("rarities", {})),
    )


def _build_item_registry():
    return _build_item_registry_from_payload(_load_json_pack(ITEMS_PACK_PATH), ITEMS_PACK_PATH)


def _build_quest_registry_from_payload(payload, source_path):
    return QuestContentRegistry(
        source_path=str(source_path),
        starting_quests=list(payload.get("starting_quests", [])),
        quest_regions=dict(payload.get("quest_regions", {})),
        quests=dict(payload.get("quests", {})),
    )


def _build_quest_registry():
    return _build_quest_registry_from_payload(_load_json_pack(QUESTS_PACK_PATH), QUESTS_PACK_PATH)


def _build_world_registry_from_payload(payload, source_path):
    return WorldContentRegistry(
        source_path=str(source_path),
        rooms=list(payload.get("rooms", [])),
        exits=list(payload.get("exits", [])),
        entities=list(payload.get("entities", [])),
    )


def _build_world_registry():
    return _build_world_registry_from_payload(_load_json_pack(WORLD_PACK_PATH), WORLD_PACK_PATH)


def _build_encounter_registry_from_payload(payload, source_path):
    roaming_parties = {}
    for party in payload.get("roaming_parties", []):
        party_key = party.get("key")
        if party_key:
            roaming_parties[party_key] = dict(party)
    return EncounterContentRegistry(
        source_path=str(source_path),
        enemy_templates=dict(payload.get("enemy_templates", {})),
        room_encounters=dict(payload.get("room_encounters", {})),
        roaming_parties=roaming_parties,
        enemy_temperament_overrides=dict(payload.get("enemy_temperament_overrides", {})),
        temperament_labels=dict(payload.get("temperament_labels", {})),
    )


def _build_encounter_registry():
    return _build_encounter_registry_from_payload(_load_json_pack(ENCOUNTERS_PACK_PATH), ENCOUNTERS_PACK_PATH)


def _build_dialogue_registry_from_payload(payload, source_path):
    return DialogueContentRegistry(
        source_path=str(source_path),
        talk_rules=dict(payload.get("talk_rules", {})),
        static_read_responses=dict(payload.get("static_read_responses", {})),
    )


def _build_dialogue_registry():
    return _build_dialogue_registry_from_payload(_load_json_pack(DIALOGUE_PACK_PATH), DIALOGUE_PACK_PATH)


def _build_systems_registry_from_payload(payload, source_path):
    activities = dict(payload.get("activities", {}))
    commerce = dict(payload.get("commerce", {}))
    forging = dict(payload.get("forging", {}))
    portals = dict(payload.get("portals", {}))
    trophies = dict(payload.get("trophies", {}))
    boss_gates = dict(payload.get("boss_gates", {}))
    return SystemsContentRegistry(
        source_path=str(source_path),
        fishing_spots=dict(activities.get("fishing_spots", {})),
        fishing_rods=dict(activities.get("fishing_rods", {})),
        fishing_lures=dict(activities.get("fishing_lures", {})),
        fishing_behaviors=dict(activities.get("fish_behaviors", {})),
        cooking_recipes=dict(activities.get("cooking_recipes", {})),
        tinkering_recipes=dict(activities.get("tinkering_recipes", {})),
        cozy_bonus=dict(activities.get("cozy_bonus", {})),
        outfitters_room_id=str(commerce.get("outfitters_room_id", "")),
        shift_outcomes=tuple(commerce.get("shift_outcomes", [])),
        forge_room_id=str(forging.get("forge_room_id", "")),
        forge_recipes=dict(forging.get("forge_recipes", {})),
        portals=dict(portals.get("portals", {})),
        portal_status_labels=dict(portals.get("portal_status_labels", {})),
        trophies=dict(trophies.get("trophies", {})),
        boss_gates=dict(boss_gates.get("boss_gates", boss_gates)),
    )


def _build_systems_registry():
    return _build_systems_registry_from_payload(_load_json_pack(SYSTEMS_PACK_PATH), SYSTEMS_PACK_PATH)


def build_content_registry_from_payloads(payloads, *, source_paths=None):
    """Build a standalone registry from already-loaded pack payloads."""

    source_paths = source_paths or {}
    return BraveContentRegistry(
        characters=_build_character_registry_from_payload(payloads["characters"], source_paths.get("characters", CHARACTERS_PACK_PATH)),
        items=_build_item_registry_from_payload(payloads["items"], source_paths.get("items", ITEMS_PACK_PATH)),
        quests=_build_quest_registry_from_payload(payloads["quests"], source_paths.get("quests", QUESTS_PACK_PATH)),
        world=_build_world_registry_from_payload(payloads["world"], source_paths.get("world", WORLD_PACK_PATH)),
        encounters=_build_encounter_registry_from_payload(payloads["encounters"], source_paths.get("encounters", ENCOUNTERS_PACK_PATH)),
        dialogue=_build_dialogue_registry_from_payload(payloads["dialogue"], source_paths.get("dialogue", DIALOGUE_PACK_PATH)),
        systems=_build_systems_registry_from_payload(payloads["systems"], source_paths.get("systems", SYSTEMS_PACK_PATH)),
    )


_CONTENT_REGISTRY = BraveContentRegistry(
    characters=_build_character_registry(),
    items=_build_item_registry(),
    quests=_build_quest_registry(),
    world=_build_world_registry(),
    encounters=_build_encounter_registry(),
    dialogue=_build_dialogue_registry(),
    systems=_build_systems_registry(),
)


def _sync_value_in_place(current, replacement):
    """Refresh mutable content containers without breaking cached references."""

    if isinstance(current, dict) and isinstance(replacement, dict):
        current.clear()
        current.update(replacement)
        return current
    if isinstance(current, list) and isinstance(replacement, list):
        current[:] = replacement
        return current
    if isinstance(current, set) and isinstance(replacement, set):
        current.clear()
        current.update(replacement)
        return current
    return replacement


def _sync_registry_in_place(current, replacement):
    """Refresh a frozen registry dataclass while preserving its object identity."""

    for field_name in getattr(replacement, "__dataclass_fields__", ()):
        value = _sync_value_in_place(getattr(current, field_name), getattr(replacement, field_name))
        object.__setattr__(current, field_name, value)
    return current


def reload_content_registry():
    """Reload the process-wide Brave content registry in place."""

    _sync_registry_in_place(_CONTENT_REGISTRY.characters, _build_character_registry())
    _sync_registry_in_place(_CONTENT_REGISTRY.items, _build_item_registry())
    _sync_registry_in_place(_CONTENT_REGISTRY.quests, _build_quest_registry())
    _sync_registry_in_place(_CONTENT_REGISTRY.world, _build_world_registry())
    _sync_registry_in_place(_CONTENT_REGISTRY.encounters, _build_encounter_registry())
    _sync_registry_in_place(_CONTENT_REGISTRY.dialogue, _build_dialogue_registry())
    _sync_registry_in_place(_CONTENT_REGISTRY.systems, _build_systems_registry())
    return _CONTENT_REGISTRY


def get_content_registry():
    """Return the process-wide Brave content registry."""

    return _CONTENT_REGISTRY
