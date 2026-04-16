"""Shared RPG Awesome icon resolution for enemy templates."""

from world.content import get_content_registry


CONTENT = get_content_registry()
ENEMY_TEMPLATES = CONTENT.encounters.enemy_templates

DEFAULT_ENEMY_ICON = "monster-skull"

EXPLICIT_ENEMY_ICONS = {
    "bandit_raider": "crossed-swords",
    "bandit_scout": "archer",
    "barrow_wisp": "aura",
    "bog_creeper": "dead-tree",
    "briar_imp": "fairy-wand",
    "captain_varn_blackreed": "knight-helmet",
    "carrion_hound": "wolf-howl",
    "cave_bat_swarm": "batwings",
    "cave_spider": "spider-face",
    "drowned_warder": "crossed-bones",
    "fen_wisp": "aura",
    "foreman_coilback": "gear-hammer",
    "forest_wolf": "wolf-head",
    "goblin_brute": "crossed-axes",
    "goblin_cutter": "axe",
    "goblin_hexer": "crystal-wand",
    "goblin_slinger": "crossbow",
    "goblin_sneak": "daggers",
    "grave_crow": "bird-claw",
    "grubnak_the_pot_king": "crown",
    "hollow_lantern": "lantern-flame",
    "hollow_wisp": "aura",
    "mag_clamp_drone": "robot-arm",
    "mire_hound": "wolf-howl",
    "miretooth": "wolf-head",
    "mossling": "sprout",
    "old_greymaw": "wolf-head",
    "relay_tick": "wireless-signal",
    "restless_shade": "death-skull",
    "road_wolf": "wolf-head",
    "rot_crow": "bird-claw",
    "ruk_fence_cutter": "crossed-axes",
    "salvage_drone": "robot-arm",
    "scrap_hound": "robot-arm",
    "scrap_mite": "beetle",
    "silt_stalker": "bird-claw",
    "sir_edric_restless": "knight-helmet",
    "skeletal_soldier": "crossed-bones",
    "sludge_slime": "water-drop",
    "thorn_rat": "tooth",
    "tower_archer": "archer",
}


def _normalize(value):
    return "".join(char for char in str(value or "").lower() if char.isalnum())


def _icon_from_template(template_key, template):
    template = dict(template or {})
    explicit = str(template.get("icon") or template.get("logo") or "").strip().lower()
    if explicit:
        return explicit

    normalized_key = str(template_key or "").strip().lower()
    if normalized_key in EXPLICIT_ENEMY_ICONS:
        return EXPLICIT_ENEMY_ICONS[normalized_key]

    tags = {str(tag).lower() for tag in template.get("tags", [])}
    name = str(template.get("name") or normalized_key).lower()

    if {"boss", "knight", "captain"} & tags or "boss" in normalized_key or "captain" in name:
        if "king" in name or "queen" in name:
            return "crown"
        return "knight-helmet"
    if {"wolf", "hound"} & tags or any(token in name for token in ("wolf", "hound")):
        return "wolf-head" if "wolf" in name or "wolf" in normalized_key else "wolf-howl"
    if {"bat", "crow", "bird"} & tags or any(token in name for token in ("bat", "crow")):
        return "batwings" if "bat" in name or "bat" in normalized_key else "bird-claw"
    if {"wisp", "shade", "ghost", "spirit"} & tags or any(token in name for token in ("wisp", "shade", "ghost", "spirit")):
        return "aura"
    if {"undead", "skeleton"} & tags or any(token in name for token in ("skeleton", "skeletal")):
        return "crossed-bones"
    if {"goblin", "bandit", "raider", "soldier", "archer"} & tags:
        if "hex" in name:
            return "crystal-wand"
        if "sneak" in name or "cut" in name:
            return "daggers"
        if "archer" in name or "slinger" in name:
            return "archer"
        return "crossed-swords"
    if {"spider", "insect"} & tags or "spider" in name:
        return "spider-face"
    if {"drone", "construct", "tech"} & tags or any(token in name for token in ("drone", "relay", "coilback")):
        if "signal" in name or "relay" in name:
            return "wireless-signal"
        if "foreman" in name:
            return "gear-hammer"
        return "robot-arm"
    if {"plant", "briar", "creeper", "moss"} & tags or any(token in name for token in ("plant", "briar", "creeper", "moss")):
        if "dead" in name or "bog" in name:
            return "dead-tree"
        return "sprout"
    if {"slime", "ooze"} & tags or "slime" in name:
        return "water-drop"
    if {"rat"} & tags or "rat" in name:
        return "tooth"
    if {"beast", "beetle"} & tags or "mite" in name:
        return "beetle"
    return DEFAULT_ENEMY_ICON


def get_enemy_icon_name(template_key, template=None):
    """Return an RPG Awesome icon name for an enemy template."""

    if template_key in EXPLICIT_ENEMY_ICONS:
        return EXPLICIT_ENEMY_ICONS[template_key]

    normalized_key = _normalize(template_key)
    for key, icon in EXPLICIT_ENEMY_ICONS.items():
        if _normalize(key) == normalized_key:
            return icon

    return _icon_from_template(template_key, template)
