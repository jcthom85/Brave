"""Shared icon taxonomy for active abilities and passive traits.

This is metadata-driven first. Content definitions can set `icon_role`
directly, which keeps UI wiring stable even if ability names or kits change.
"""


ABILITY_ROLE_ICON = {
    "attack": "swords",
    "guard": "shield",
    "taunt": "forum",
    "rally": "forum",
    "shot": "near_me",
    "mark": "visibility",
    "trap": "route",
    "barrage": "groups",
    "mobility": "air",
    "heal": "favorite",
    "cleanse": "water",
    "blessing": "auto_awesome",
    "holy": "wb_sunny",
    "fire": "local_fire_department",
    "frost": "ac_unit",
    "lightning": "bolt",
    "arcane": "auto_awesome",
    "stealth": "visibility_off",
    "poison": "eco",
    "nature": "forest",
    "root": "eco",
    "field": "groups",
}

PASSIVE_ROLE_ICON = {
    "offense": "swords",
    "defense": "shield",
    "vitality": "favorite",
    "precision": "location_searching",
    "mobility": "air",
    "magic": "auto_awesome",
    "healing": "favorite",
    "nature": "forest",
    "holy": "wb_sunny",
    "resource": "auto_awesome",
    "utility": "route",
}

ALLOWED_ABILITY_ICON_ROLES = frozenset(ABILITY_ROLE_ICON.keys())
ALLOWED_PASSIVE_ICON_ROLES = frozenset(PASSIVE_ROLE_ICON.keys())


def infer_ability_icon_role(ability_key, ability=None):
    """Infer a role when content metadata does not provide one."""
    ability = dict(ability or {})
    target_mode = ability.get("target")
    resource_key = ability.get("resource")
    normalized = str(ability_key or "").strip().lower()

    if any(token in normalized for token in ("heal", "mend", "mercy")):
        return "heal"
    if any(token in normalized for token in ("cleanse", "purity")):
        return "cleanse"
    if any(token in normalized for token in ("defend", "guard", "shield", "brace", "sanctuary", "barkskin")):
        return "guard"
    if any(token in normalized for token in ("taunt", "cry")):
        return "taunt"
    if any(token in normalized for token in ("step", "roll", "vanish", "feint")):
        return "mobility"
    if any(token in normalized for token in ("trap", "snare")):
        return "trap"
    if any(token in normalized for token in ("volley", "rain", "burst", "swarm", "wave", "field", "grove")):
        return "field"
    if any(token in normalized for token in ("shot", "arrow", "prey")):
        return "shot"
    if any(token in normalized for token in ("fire", "flame", "meteor")):
        return "fire"
    if any(token in normalized for token in ("frost", "ice")):
        return "frost"
    if any(token in normalized for token in ("spark", "static")):
        return "lightning"
    if any(token in normalized for token in ("smite", "holy", "radiant", "dawn", "rebuke", "judgement", "consecrate", "avenging")):
        return "holy"
    if any(token in normalized for token in ("thorn", "root", "moon", "nature", "wild")):
        return "nature"
    if any(token in normalized for token in ("poison",)):
        return "poison"
    if any(token in normalized for token in ("mark",)):
        return "mark"
    if target_mode == "ally":
        return "blessing" if resource_key == "mana" else "guard"
    if target_mode == "self":
        return "guard"
    if target_mode == "none":
        return "field"
    if resource_key == "mana":
        return "arcane"
    return "attack"


def infer_passive_icon_role(passive_key, passive=None):
    """Infer a passive role when content metadata does not provide one."""
    passive = dict(passive or {})
    bonuses = set((passive.get("bonuses") or {}).keys())
    normalized = str(passive_key or "").strip().lower()

    if {"armor", "threat"} & bonuses:
        return "defense"
    if {"max_hp"} & bonuses:
        return "vitality"
    if {"healing_power"} & bonuses and {"spell_power", "max_mana"} & bonuses:
        return "healing"
    if {"spell_power", "max_mana"} & bonuses:
        return "magic"
    if {"dodge"} & bonuses:
        return "mobility"
    if {"crit_chance", "accuracy", "precision", "attack_power"} & bonuses:
        return "precision"
    if "nature" in normalized or "wild" in normalized or "trail" in normalized:
        return "nature"
    if "faith" in normalized or "blessed" in normalized or "beacon" in normalized:
        return "holy"
    return "utility"


def get_ability_icon_name(ability_key, ability=None):
    """Return the canonical UI icon for an active ability."""
    ability = dict(ability or {})
    if ability.get("icon"):
        return str(ability["icon"])
    role = str(ability.get("icon_role") or infer_ability_icon_role(ability_key, ability))
    return ABILITY_ROLE_ICON.get(role, "bolt")


def get_passive_icon_name(passive_key, passive=None):
    """Return the canonical UI icon for a passive trait."""
    passive = dict(passive or {})
    if passive.get("icon"):
        return str(passive["icon"])
    role = str(passive.get("icon_role") or infer_passive_icon_role(passive_key, passive))
    return PASSIVE_ROLE_ICON.get(role, "star_outline")
