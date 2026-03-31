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
    },
    "elf": {
        "name": "Elf",
        "perk": "Keen Senses",
        "summary": "Graceful, perceptive, and naturally magical.",
        "bonuses": {"agility": 2, "intellect": 1, "spirit": 1},
    },
    "dwarf": {
        "name": "Dwarf",
        "perk": "Stoneblood",
        "summary": "Hardy, disciplined, and stubborn.",
        "bonuses": {"strength": 1, "spirit": 1, "vitality": 3},
    },
    "halfling": {
        "name": "Halfling",
        "perk": "Fortune's Step",
        "summary": "Quick, lucky, and easy to underestimate.",
        "bonuses": {"agility": 2, "intellect": 1, "vitality": 1},
    },
    "half_orc": {
        "name": "Half-Orc",
        "perk": "Battle Hunger",
        "summary": "Fierce, intimidating, and strong.",
        "bonuses": {"strength": 3, "vitality": 2},
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
        "base_stats": {"strength": 3, "agility": 6, "intellect": 2, "spirit": 2, "vitality": 4},
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
        "base_stats": {"strength": 2, "agility": 2, "intellect": 3, "spirit": 7, "vitality": 5},
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
        "base_stats": {"strength": 3, "agility": 6, "intellect": 2, "spirit": 2, "vitality": 4},
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
        "base_stats": {"strength": 4, "agility": 2, "intellect": 2, "spirit": 5, "vitality": 6},
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
        "base_stats": {"strength": 2, "agility": 3, "intellect": 5, "spirit": 6, "vitality": 4},
        "progression": [
            (1, "Thorn Lash"),
            (1, "Minor Mend"),
            (2, "Entangling Roots"),
            (3, "Wild Grace"),
            (4, "Moonfire"),
            (5, "Barkskin"),
            (6, "Living Current"),
            (7, "Swarm"),
            (8, "Rejuvenation Grove"),
            (9, "Nature's Memory"),
            (10, "Wrath of the Grove"),
        ],
    },
}


def xp_needed_for_next_level(level):
    """Return the XP needed to reach the next level, or None at cap."""

    if level >= MAX_LEVEL:
        return None
    return XP_FOR_LEVEL[level + 1]
