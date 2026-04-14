"""Character data used by the first Brave slice."""

PRIMARY_STATS = ("strength", "agility", "intellect", "spirit", "vitality")

STARTING_RACE = "human"
STARTING_CLASS = "warrior"
MAX_LEVEL = 10
VERTICAL_SLICE_CLASSES = ("warrior", "cleric", "ranger", "mage", "rogue", "paladin", "druid")

XP_FOR_LEVEL = {
    1: 0,
    2: 50,
    3: 125,
    4: 225,
    5: 350,
    6: 500,
    7: 675,
    8: 875,
    9: 1100,
    10: 1350,
}

RACES = {
    "human": {
        "name": "Human",
        "perk": "Resolve",
        "summary": "Flexible, ambitious, and practical.",
        "bonuses": {"strength": 1, "agility": 1, "intellect": 1, "spirit": 1, "vitality": 1},
        "trait_bonuses": {},
    },
    "elf": {
        "name": "Elf",
        "perk": "Keen Senses",
        "summary": "Graceful, perceptive, and naturally magical.",
        "bonuses": {"agility": 2, "intellect": 1, "spirit": 1},
        "trait_bonuses": {"accuracy": 2, "precision": 1, "dodge": 1},
    },
    "dwarf": {
        "name": "Dwarf",
        "perk": "Stoneblood",
        "summary": "Hardy, disciplined, and stubborn.",
        "bonuses": {"strength": 1, "spirit": 1, "vitality": 3},
        "trait_bonuses": {"armor": 1, "max_hp": 2},
    },
    "halfling": {
        "name": "Halfling",
        "perk": "Fortune's Step",
        "summary": "Quick, lucky, and easy to underestimate.",
        "bonuses": {"agility": 2, "intellect": 1, "vitality": 1},
        "trait_bonuses": {"accuracy": 1, "crit_chance": 1, "dodge": 1},
    },
    "half_orc": {
        "name": "Half-Orc",
        "perk": "Battle Hunger",
        "summary": "Fierce, intimidating, and strong.",
        "bonuses": {"strength": 3, "vitality": 2},
        "trait_bonuses": {"attack_power": 1, "max_stamina": 1, "threat": 1},
    },
}

CLASSES = {
    "warrior": {
        "name": "Warrior",
        "role": "Tank",
        "resource": "stamina",
        "summary": "Frontline protector who controls enemy attention and absorbs punishment.",
        "base_stats": {"strength": 5, "agility": 2, "intellect": 1, "spirit": 2, "vitality": 6},
        "progression": [
            (1, "Strike"),
            (1, "Defend"),
            (2, "Shield Bash"),
            (3, "Iron Will"),
            (4, "Battle Cry"),
            (5, "Intercept"),
            (6, "Thick Hide"),
            (7, "Taunting Blow"),
            (8, "Brace"),
            (9, "Bulwark"),
            (10, "Last Stand"),
        ],
    },
    "ranger": {
        "name": "Ranger",
        "role": "Ranged DPS",
        "resource": "stamina",
        "summary": "Mobile ranged hunter with target control and reliable damage.",
        "base_stats": {"strength": 3, "agility": 7, "intellect": 2, "spirit": 2, "vitality": 4},
        "progression": [
            (1, "Quick Shot"),
            (1, "Mark Prey"),
            (2, "Aimed Shot"),
            (3, "Trailwise"),
            (4, "Snare Trap"),
            (5, "Volley"),
            (6, "Predator's Eye"),
            (7, "Evasive Roll"),
            (8, "Barbed Arrow"),
            (9, "Deadly Rhythm"),
            (10, "Rain of Arrows"),
        ],
    },
    "mage": {
        "name": "Mage",
        "role": "Magic DPS",
        "resource": "mana",
        "summary": "Elemental caster with burst damage and battlefield control.",
        "base_stats": {"strength": 1, "agility": 2, "intellect": 7, "spirit": 5, "vitality": 3},
        "progression": [
            (1, "Firebolt"),
            (1, "Frost Bind"),
            (2, "Arc Spark"),
            (3, "Deep Focus"),
            (4, "Flame Wave"),
            (5, "Mana Shield"),
            (6, "Spell Echo"),
            (7, "Static Field"),
            (8, "Ice Lance"),
            (9, "Elemental Attunement"),
            (10, "Meteor Sigil"),
        ],
    },
    "cleric": {
        "name": "Cleric",
        "role": "Healer",
        "resource": "mana",
        "summary": "Holy support who keeps the party alive and counters the undead.",
        "base_stats": {"strength": 2, "agility": 2, "intellect": 4, "spirit": 8, "vitality": 4},
        "progression": [
            (1, "Heal"),
            (1, "Smite"),
            (2, "Blessing"),
            (3, "Serene Soul"),
            (4, "Renewing Light"),
            (5, "Sanctuary"),
            (6, "Purity"),
            (7, "Cleanse"),
            (8, "Radiant Burst"),
            (9, "Graceful Hands"),
            (10, "Guardian Light"),
        ],
    },
    "rogue": {
        "name": "Rogue",
        "role": "Burst DPS",
        "resource": "stamina",
        "summary": "Opportunist who strikes hard, repositions, and slips out of danger.",
        "base_stats": {"strength": 3, "agility": 6, "intellect": 2, "spirit": 2, "vitality": 3},
        "progression": [
            (1, "Stab"),
            (1, "Feint"),
            (2, "Backstab"),
            (3, "Light Feet"),
            (4, "Poison Blade"),
            (5, "Vanish"),
            (6, "Ruthless Timing"),
            (7, "Cheap Shot"),
            (8, "Shadowstep"),
            (9, "Killer's Focus"),
            (10, "Eviscerate"),
        ],
    },
    "paladin": {
        "name": "Paladin",
        "role": "Support Tank",
        "resource": "stamina",
        "summary": "Holy armored bruiser blending durability, protection, and light support.",
        "base_stats": {"strength": 4, "agility": 2, "intellect": 2, "spirit": 6, "vitality": 7},
        "progression": [
            (1, "Holy Strike"),
            (1, "Guarding Aura"),
            (2, "Judgement"),
            (3, "Steadfast Faith"),
            (4, "Hand of Mercy"),
            (5, "Consecrate"),
            (6, "Blessed Armor"),
            (7, "Shield of Dawn"),
            (8, "Rebuke Evil"),
            (9, "Beacon Soul"),
            (10, "Avenging Light"),
        ],
    },
    "druid": {
        "name": "Druid",
        "role": "Hybrid Support",
        "resource": "mana",
        "summary": "Nature-bound support blending control, healing, and slow pressure.",
        "base_stats": {"strength": 2, "agility": 4, "intellect": 6, "spirit": 7, "vitality": 4},
        "progression": [
            (1, "Thorn Lash"),
            (1, "Minor Mend"),
            (2, "Entangling Roots"),
            (3, "Wild Grace"),
            (4, "Moonfire"),
            (5, "Verdant Guard"),
            (6, "Barkskin"),
            (7, "Living Current"),
            (8, "Swarm"),
            (9, "Rejuvenation Grove"),
            (10, "Nature's Memory"),
            (10, "Wrath of the Grove"),
        ],
    },
}


def ability_key(name):
    """Return the canonical normalized key for an ability name."""

    return "".join(char for char in (name or "").lower() if char.isalnum())


ABILITY_LIBRARY = {
    "strike": {"name": "Strike", "class": "warrior", "resource": "stamina", "cost": 8, "target": "enemy"},
    "defend": {"name": "Defend", "class": "warrior", "resource": "stamina", "cost": 6, "target": "self"},
    "shieldbash": {"name": "Shield Bash", "class": "warrior", "resource": "stamina", "cost": 10, "target": "enemy"},
    "battlecry": {"name": "Battle Cry", "class": "warrior", "resource": "stamina", "cost": 12, "target": "none"},
    "intercept": {"name": "Intercept", "class": "warrior", "resource": "stamina", "cost": 11, "target": "ally"},
    "tauntingblow": {"name": "Taunting Blow", "class": "warrior", "resource": "stamina", "cost": 10, "target": "enemy"},
    "brace": {"name": "Brace", "class": "warrior", "resource": "stamina", "cost": 10, "target": "self"},
    "laststand": {"name": "Last Stand", "class": "warrior", "resource": "stamina", "cost": 16, "target": "self"},
    "quickshot": {"name": "Quick Shot", "class": "ranger", "resource": "stamina", "cost": 8, "target": "enemy"},
    "markprey": {"name": "Mark Prey", "class": "ranger", "resource": "stamina", "cost": 6, "target": "enemy"},
    "aimedshot": {"name": "Aimed Shot", "class": "ranger", "resource": "stamina", "cost": 11, "target": "enemy"},
    "snaretrap": {"name": "Snare Trap", "class": "ranger", "resource": "stamina", "cost": 9, "target": "enemy"},
    "volley": {"name": "Volley", "class": "ranger", "resource": "stamina", "cost": 13, "target": "none"},
    "evasiveroll": {"name": "Evasive Roll", "class": "ranger", "resource": "stamina", "cost": 8, "target": "self"},
    "barbedarrow": {"name": "Barbed Arrow", "class": "ranger", "resource": "stamina", "cost": 10, "target": "enemy"},
    "rainofarrows": {"name": "Rain of Arrows", "class": "ranger", "resource": "stamina", "cost": 16, "target": "none"},
    "firebolt": {"name": "Firebolt", "class": "mage", "resource": "mana", "cost": 9, "target": "enemy"},
    "frostbind": {"name": "Frost Bind", "class": "mage", "resource": "mana", "cost": 10, "target": "enemy"},
    "arcspark": {"name": "Arc Spark", "class": "mage", "resource": "mana", "cost": 11, "target": "enemy"},
    "flamewave": {"name": "Flame Wave", "class": "mage", "resource": "mana", "cost": 14, "target": "none"},
    "manashield": {"name": "Mana Shield", "class": "mage", "resource": "mana", "cost": 12, "target": "self"},
    "staticfield": {"name": "Static Field", "class": "mage", "resource": "mana", "cost": 13, "target": "none"},
    "icelance": {"name": "Ice Lance", "class": "mage", "resource": "mana", "cost": 12, "target": "enemy"},
    "meteorsigil": {"name": "Meteor Sigil", "class": "mage", "resource": "mana", "cost": 18, "target": "enemy"},
    "heal": {"name": "Heal", "class": "cleric", "resource": "mana", "cost": 10, "target": "ally"},
    "smite": {"name": "Smite", "class": "cleric", "resource": "mana", "cost": 8, "target": "enemy"},
    "blessing": {"name": "Blessing", "class": "cleric", "resource": "mana", "cost": 10, "target": "ally"},
    "renewinglight": {"name": "Renewing Light", "class": "cleric", "resource": "mana", "cost": 14, "target": "ally"},
    "sanctuary": {"name": "Sanctuary", "class": "cleric", "resource": "mana", "cost": 14, "target": "none"},
    "cleanse": {"name": "Cleanse", "class": "cleric", "resource": "mana", "cost": 10, "target": "ally"},
    "radiantburst": {"name": "Radiant Burst", "class": "cleric", "resource": "mana", "cost": 15, "target": "none"},
    "guardianlight": {"name": "Guardian Light", "class": "cleric", "resource": "mana", "cost": 18, "target": "ally"},
    "stab": {"name": "Stab", "class": "rogue", "resource": "stamina", "cost": 7, "target": "enemy"},
    "feint": {"name": "Feint", "class": "rogue", "resource": "stamina", "cost": 6, "target": "self"},
    "backstab": {"name": "Backstab", "class": "rogue", "resource": "stamina", "cost": 10, "target": "enemy"},
    "poisonblade": {"name": "Poison Blade", "class": "rogue", "resource": "stamina", "cost": 9, "target": "enemy"},
    "vanish": {"name": "Vanish", "class": "rogue", "resource": "stamina", "cost": 10, "target": "self"},
    "cheapshot": {"name": "Cheap Shot", "class": "rogue", "resource": "stamina", "cost": 11, "target": "enemy"},
    "shadowstep": {"name": "Shadowstep", "class": "rogue", "resource": "stamina", "cost": 12, "target": "enemy"},
    "eviscerate": {"name": "Eviscerate", "class": "rogue", "resource": "stamina", "cost": 16, "target": "enemy"},
    "holystrike": {"name": "Holy Strike", "class": "paladin", "resource": "stamina", "cost": 8, "target": "enemy"},
    "guardingaura": {"name": "Guarding Aura", "class": "paladin", "resource": "stamina", "cost": 8, "target": "ally"},
    "judgement": {"name": "Judgement", "class": "paladin", "resource": "stamina", "cost": 10, "target": "enemy"},
    "handofmercy": {"name": "Hand of Mercy", "class": "paladin", "resource": "stamina", "cost": 11, "target": "ally"},
    "consecrate": {"name": "Consecrate", "class": "paladin", "resource": "stamina", "cost": 13, "target": "none"},
    "shieldofdawn": {"name": "Shield of Dawn", "class": "paladin", "resource": "stamina", "cost": 12, "target": "ally"},
    "rebukeevil": {"name": "Rebuke Evil", "class": "paladin", "resource": "stamina", "cost": 12, "target": "enemy"},
    "avenginglight": {"name": "Avenging Light", "class": "paladin", "resource": "stamina", "cost": 18, "target": "none"},
    "thornlash": {"name": "Thorn Lash", "class": "druid", "resource": "mana", "cost": 8, "target": "enemy"},
    "minormend": {"name": "Minor Mend", "class": "druid", "resource": "mana", "cost": 8, "target": "ally"},
    "entanglingroots": {"name": "Entangling Roots", "class": "druid", "resource": "mana", "cost": 10, "target": "enemy"},
    "moonfire": {"name": "Moonfire", "class": "druid", "resource": "mana", "cost": 10, "target": "enemy"},
    "barkskin": {"name": "Barkskin", "class": "druid", "resource": "mana", "cost": 10, "target": "ally"},
    "livingcurrent": {"name": "Living Current", "class": "druid", "resource": "mana", "cost": 12, "target": "ally"},
    "swarm": {"name": "Swarm", "class": "druid", "resource": "mana", "cost": 14, "target": "none"},
    "rejuvenationgrove": {"name": "Rejuvenation Grove", "class": "druid", "resource": "mana", "cost": 16, "target": "none"},
    "wrathofthegrove": {"name": "Wrath of the Grove", "class": "druid", "resource": "mana", "cost": 18, "target": "enemy"},
}


IMPLEMENTED_ABILITY_KEYS = {
    "strike",
    "defend",
    "shieldbash",
    "battlecry",
    "intercept",
    "tauntingblow",
    "brace",
    "laststand",
    "quickshot",
    "markprey",
    "aimedshot",
    "snaretrap",
    "volley",
    "evasiveroll",
    "barbedarrow",
    "rainofarrows",
    "heal",
    "smite",
    "blessing",
    "renewinglight",
    "sanctuary",
    "cleanse",
    "radiantburst",
    "guardianlight",
    "firebolt",
    "frostbind",
    "arcspark",
    "flamewave",
    "manashield",
    "staticfield",
    "icelance",
    "meteorsigil",
    "stab",
    "feint",
    "backstab",
    "poisonblade",
    "vanish",
    "cheapshot",
    "shadowstep",
    "eviscerate",
    "holystrike",
    "guardingaura",
    "judgement",
    "handofmercy",
    "consecrate",
    "shieldofdawn",
    "rebukeevil",
    "avenginglight",
    "thornlash",
    "minormend",
    "entanglingroots",
    "moonfire",
    "barkskin",
    "livingcurrent",
    "swarm",
    "rejuvenationgrove",
    "wrathofthegrove",
}


PASSIVE_ABILITY_BONUSES = {
    "ironwill": {"name": "Iron Will", "bonuses": {"max_hp": 12, "threat": 2}},
    "thickhide": {"name": "Thick Hide", "bonuses": {"armor": 3}},
    "bulwark": {"name": "Bulwark", "bonuses": {"max_hp": 12, "armor": 3, "threat": 2}},
    "trailwise": {"name": "Trailwise", "bonuses": {"dodge": 2}},
    "predatorseye": {"name": "Predator's Eye", "bonuses": {"accuracy": 4, "precision": 2}},
    "deadlyrhythm": {"name": "Deadly Rhythm", "bonuses": {"attack_power": 3, "crit_chance": 2}},
    "deepfocus": {"name": "Deep Focus", "bonuses": {"max_mana": 14}},
    "spellecho": {"name": "Spell Echo", "bonuses": {"spell_power": 3}},
    "elementalattunement": {"name": "Elemental Attunement", "bonuses": {"spell_power": 2, "accuracy": 2}},
    "serenesoul": {"name": "Serene Soul", "bonuses": {"max_mana": 12, "spell_power": 2}},
    "purity": {"name": "Purity", "bonuses": {"armor": 2, "healing_power": 2}},
    "gracefulhands": {"name": "Graceful Hands", "bonuses": {"spell_power": 2, "healing_power": 3}},
    "lightfeet": {"name": "Light Feet", "bonuses": {"dodge": 3}},
    "ruthlesstiming": {"name": "Ruthless Timing", "bonuses": {"attack_power": 3, "accuracy": 2}},
    "killersfocus": {"name": "Killer's Focus", "bonuses": {"precision": 3, "crit_chance": 3}},
    "steadfastfaith": {"name": "Steadfast Faith", "bonuses": {"max_hp": 10, "max_mana": 8}},
    "blessedarmor": {"name": "Blessed Armor", "bonuses": {"armor": 3, "threat": 1}},
    "beaconsoul": {"name": "Beacon Soul", "bonuses": {"spell_power": 2, "healing_power": 2, "threat": 1}},
    "wildgrace": {"name": "Wild Grace", "bonuses": {"dodge": 2, "accuracy": 2}},
    "verdantguard": {"name": "Verdant Guard", "bonuses": {"max_hp": 8, "armor": 2, "healing_power": 1}},
    "naturesmemory": {"name": "Nature's Memory", "bonuses": {"max_mana": 10, "spell_power": 2, "healing_power": 2}},
}


def get_progression_ability_names(class_key, level):
    """Return progression ability names unlocked for a class at a given level."""

    class_data = CLASSES[class_key]
    return [ability for unlock_level, ability in class_data["progression"] if unlock_level <= level]


def split_unlocked_abilities(class_key, level):
    """Split unlocked progression abilities into combat actions and passive traits."""

    actions = []
    passives = []
    unknown = []
    for ability_name in get_progression_ability_names(class_key, level):
        key = ability_key(ability_name)
        if key in IMPLEMENTED_ABILITY_KEYS:
            actions.append(ability_name)
        elif key in PASSIVE_ABILITY_BONUSES:
            passives.append(ability_name)
        else:
            unknown.append(ability_name)
    return actions, passives, unknown


def get_passive_ability_bonuses(class_key, level):
    """Aggregate all passive bonuses unlocked for a class at a given level."""

    totals = {}
    _actions, passives, _unknown = split_unlocked_abilities(class_key, level)
    for ability_name in passives:
        bonus_def = PASSIVE_ABILITY_BONUSES.get(ability_key(ability_name), {})
        for stat, amount in bonus_def.get("bonuses", {}).items():
            totals[stat] = totals.get(stat, 0) + amount
    return totals


def xp_needed_for_next_level(level):
    """Return the XP needed to reach the next level, or None at cap."""

    if level >= MAX_LEVEL:
        return None
    return XP_FOR_LEVEL[level + 1]
