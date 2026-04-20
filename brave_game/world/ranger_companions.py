"""Ranger companion data and helpers."""

from copy import deepcopy

BOND_LEVELS = (
    {"level": 1, "title": "New Bond", "xp_required": 0},
    {"level": 2, "title": "Field-Tested", "xp_required": 3},
    {"level": 3, "title": "Hunt-Bound", "xp_required": 8},
    {"level": 4, "title": "Heart-Bound", "xp_required": 15},
)

GENERAL_BOND_BONUSES = {
    1: {
        "hp_ratio_bonus": 0.0,
        "attack_ratio_bonus": 0.0,
        "armor_ratio_bonus": 0.0,
        "accuracy_bonus": 0,
        "dodge_bonus": 0,
        "fill_rate_bonus": 0,
    },
    2: {
        "hp_ratio_bonus": 0.08,
        "attack_ratio_bonus": 0.05,
        "armor_ratio_bonus": 0.05,
        "accuracy_bonus": 1,
        "dodge_bonus": 1,
        "fill_rate_bonus": 2,
    },
    3: {
        "hp_ratio_bonus": 0.16,
        "attack_ratio_bonus": 0.11,
        "armor_ratio_bonus": 0.1,
        "accuracy_bonus": 2,
        "dodge_bonus": 2,
        "fill_rate_bonus": 4,
    },
    4: {
        "hp_ratio_bonus": 0.24,
        "attack_ratio_bonus": 0.18,
        "armor_ratio_bonus": 0.15,
        "accuracy_bonus": 3,
        "dodge_bonus": 3,
        "fill_rate_bonus": 6,
    },
}

SPECIES_BOND_BONUSES = {
    "marsh_hound": {
        2: {"marked_damage_bonus": 1},
        3: {"bleed_bonus": 1},
        4: {"bleed_turn_bonus": 1, "marked_damage_bonus": 2},
    },
    "ash_hawk": {
        2: {"aimed_accuracy_bonus": 1},
        3: {"mark_turn_bonus": 1},
        4: {"rain_mark_turn_bonus": 1, "accuracy_bonus": 1},
    },
    "briar_boar": {
        2: {"snare_damage_bonus": 1},
        3: {"snare_turn_bonus": 1},
        4: {"evasion_guard_bonus": 2, "armor_ratio_bonus": 0.08},
    },
}

RANGER_COMPANIONS = {
    "marsh_hound": {
        "name": "Marsh Hound",
        "icon": "wolf-howl",
        "summary": "A low, wiry fen-hound bred to stay on a trail and keep prey from settling once the hunt starts.",
        "combat": {
            "role": "skirmisher",
            "hp_ratio": 0.55,
            "attack_ratio": 0.62,
            "armor_ratio": 0.7,
            "accuracy_bonus": 4,
            "dodge_bonus": 3,
            "fill_rate_bonus": 8,
            "marked_damage_bonus": 1,
            "bleed_bonus": 1,
            "label": "Hamstring Bite",
        },
    },
    "ash_hawk": {
        "name": "Ash Hawk",
        "icon": "bird-claw",
        "summary": "A sharp-eyed hawk that keeps the quarry in view and turns a clean mark into cleaner follow-up shots.",
        "combat": {
            "role": "harrier",
            "hp_ratio": 0.42,
            "attack_ratio": 0.48,
            "armor_ratio": 0.45,
            "accuracy_bonus": 8,
            "dodge_bonus": 6,
            "fill_rate_bonus": 16,
            "mark_turn_bonus": 1,
            "aimed_accuracy_bonus": 2,
            "rain_mark_turn_bonus": 1,
            "label": "Harrying Pass",
        },
    },
    "briar_boar": {
        "name": "Briar Boar",
        "icon": "tooth",
        "summary": "A stubborn brush-boar that hits trap lines hard, contests space, and makes pinned targets even worse off.",
        "combat": {
            "role": "breaker",
            "hp_ratio": 0.72,
            "attack_ratio": 0.58,
            "armor_ratio": 1.0,
            "accuracy_bonus": 2,
            "dodge_bonus": 0,
            "fill_rate_bonus": 4,
            "snare_turn_bonus": 1,
            "snare_damage_bonus": 1,
            "evasion_guard_bonus": 2,
            "label": "Tusk Rush",
        },
    },
}

DEFAULT_RANGER_COMPANION = "marsh_hound"


def _bond_meta_for_level(level):
    normalized = max(1, min(int(level or 1), BOND_LEVELS[-1]["level"]))
    for entry in BOND_LEVELS:
        if entry["level"] == normalized:
            return dict(entry)
    return dict(BOND_LEVELS[0])


def _bond_level_for_xp(xp):
    xp_total = max(0, int(xp or 0))
    current = 1
    for entry in BOND_LEVELS:
        if xp_total >= entry["xp_required"]:
            current = entry["level"]
    return current


def normalize_companion_bond_state(state=None):
    """Return normalized companion bond state with derived progression metadata."""

    raw = dict(state or {})
    xp_total = max(0, int(raw.get("xp", 0) or 0))
    level = _bond_level_for_xp(xp_total)
    current = _bond_meta_for_level(level)
    next_entry = _bond_meta_for_level(level + 1) if level < BOND_LEVELS[-1]["level"] else None
    return {
        "xp": xp_total,
        "level": level,
        "title": current["title"],
        "xp_required": current["xp_required"],
        "next_level": next_entry["level"] if next_entry else None,
        "next_xp_required": next_entry["xp_required"] if next_entry else None,
        "xp_to_next": max(0, next_entry["xp_required"] - xp_total) if next_entry else 0,
        "at_cap": next_entry is None,
    }


def _apply_bond_bonuses(companion_key, combat, bond_level):
    """Return a combat profile adjusted by bond tier bonuses."""

    adjusted = dict(combat or {})
    level = max(1, min(int(bond_level or 1), BOND_LEVELS[-1]["level"]))
    general = GENERAL_BOND_BONUSES.get(level, {})
    for key, value in general.items():
        if key.endswith("_ratio_bonus"):
            ratio_key = key[: -len("_bonus")]
            adjusted[ratio_key] = float(adjusted.get(ratio_key, 0.0) or 0.0) + float(value or 0.0)
        elif key.endswith("_bonus"):
            adjusted[key] = int(adjusted.get(key, 0) or 0) + int(value or 0)
    for tier in range(2, level + 1):
        for key, value in SPECIES_BOND_BONUSES.get(str(companion_key or "").lower(), {}).get(tier, {}).items():
            if key.endswith("_ratio_bonus"):
                ratio_key = key[: -len("_bonus")]
                adjusted[ratio_key] = float(adjusted.get(ratio_key, 0.0) or 0.0) + float(value or 0.0)
            else:
                adjusted[key] = int(adjusted.get(key, 0) or 0) + int(value or 0)
    return adjusted


def get_companion(companion_key, bond_state=None):
    """Return one authored ranger companion with optional bond metadata applied."""

    normalized_key = str(companion_key or "").lower()
    companion = deepcopy(RANGER_COMPANIONS.get(normalized_key, {}))
    if not companion:
        return {}
    bond = normalize_companion_bond_state(bond_state)
    companion["combat"] = _apply_bond_bonuses(normalized_key, companion.get("combat", {}), bond["level"])
    companion["bond"] = bond
    companion["bond_label"] = f"Bond {bond['level']} · {bond['title']}"
    return companion


def get_default_ranger_companion():
    """Return the default ranger companion key."""

    return DEFAULT_RANGER_COMPANION


def get_companion_name(companion_key):
    """Return a readable companion name."""

    return get_companion(companion_key).get("name", str(companion_key or "").replace("_", " ").title())
