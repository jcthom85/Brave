"""Ability mastery helpers for Brave."""

from world.content import get_content_registry
from world.resonance import format_ability_display

CONTENT = get_content_registry()
ABILITY_LIBRARY = CONTENT.characters.ability_library

MASTERY_ROOM_ID = "brambleford_mastery_hall"
MASTERY_TRAINER_ENTITY_ID = "mistress_elira_thorne"
MASTERY_RESPEC_SILVER_COST = 30
MASTERY_POINT_LEVELS = (3, 5, 7, 9)
MASTERY_ROMAN = {1: "I", 2: "II", 3: "III"}
MASTERY_EXPOSITION = {1: "Known", 2: "Trained", 3: "Mastered"}

ROLE_DEFAULT = "strike"
ZERO_BONUS = {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0}


def _bonus(*, accuracy=0, power=0, heal=0, guard=0, turn=0):
    """Return a normalized mastery bonus payload."""

    return {
        "accuracy": int(accuracy),
        "power": int(power),
        "heal": int(heal),
        "guard": int(guard),
        "turn": int(turn),
    }


def _ability_entry(role, rank2, rank3, text2, text3):
    """Build one authored mastery definition."""

    return {
        "role": role,
        "bonuses": {
            1: dict(ZERO_BONUS),
            2: _bonus(**rank2),
            3: _bonus(**rank3),
        },
        "text": {
            2: text2,
            3: text3,
        },
    }


ABILITY_MASTERY_DATA = {
    "strike": _ability_entry("strike", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 3}, "Trained: timing tightens and the hit lands heavier.", "Mastered: you punish marked or bound targets with real force."),
    "defend": _ability_entry("guard", {"guard": 3}, {"guard": 6, "turn": 1}, "Trained: your stance catches harder hits.", "Mastered: your guard holds longer into the next exchange."),
    "shieldbash": _ability_entry("control", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 1, "turn": 1}, "Trained: the bash lands cleaner.", "Mastered: the stagger lingers and the knock-off-balance sticks."),
    "battlecry": _ability_entry("guard", {"guard": 2}, {"guard": 4, "turn": 1}, "Trained: your cry hardens the whole line.", "Mastered: the rally carries farther through the exchange."),
    "intercept": _ability_entry("guard", {"guard": 3}, {"guard": 5, "turn": 1}, "Trained: you catch more of the blow meant for an ally.", "Mastered: your cover and redirect window hold longer."),
    "tauntingblow": _ability_entry("control", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 2, "turn": 1}, "Trained: the bait lands more reliably.", "Mastered: the taunt pressure clings to the target."),
    "brace": _ability_entry("guard", {"guard": 3}, {"guard": 6, "turn": 1}, "Trained: your planted stance is firmer.", "Mastered: the braced line refuses to break."),
    "laststand": _ability_entry("guard", {"guard": 2, "heal": 2}, {"guard": 4, "heal": 4, "turn": 1}, "Trained: the recovery steadies you harder.", "Mastered: you rebound and hold the ground longer."),
    "quickshot": _ability_entry("strike", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 2}, "Trained: the shot comes off the string cleaner.", "Mastered: the hunt line stays under your pressure."),
    "markprey": _ability_entry("mark", {"accuracy": 1, "turn": 1}, {"accuracy": 2, "power": 1, "turn": 1}, "Trained: quarry focus settles faster.", "Mastered: the mark stays threatening and sharpens follow-through."),
    "aimedshot": _ability_entry("finisher", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 4}, "Trained: setup pays off harder.", "Mastered: the finishing shot bites deep when the line is prepared."),
    "snaretrap": _ability_entry("control", {"accuracy": 1, "power": 1, "turn": 1}, {"accuracy": 2, "power": 1, "turn": 1}, "Trained: the trap closes where you need it.", "Mastered: prey stays pinned and easier to keep marked."),
    "volley": _ability_entry("aoe", {"power": 1}, {"accuracy": 1, "power": 2}, "Trained: the spread lands with cleaner discipline.", "Mastered: the whole line feels the pressure."),
    "evasiveroll": _ability_entry("mobility", {"guard": 2}, {"accuracy": 1, "guard": 4, "turn": 1}, "Trained: the reset is safer.", "Mastered: the new angle leaves a longer opening to exploit."),
    "barbedarrow": _ability_entry("control", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 1, "turn": 1}, "Trained: the barbs bite with better placement.", "Mastered: the bleeding pressure stays on the prey."),
    "rainofarrows": _ability_entry("aoe", {"power": 1, "turn": 1}, {"accuracy": 1, "power": 2, "turn": 1}, "Trained: the barrage blankets the field more effectively.", "Mastered: survivors stay tagged inside the storm."),
    "heal": _ability_entry("heal", {"power": 1, "heal": 3}, {"power": 2, "heal": 6}, "Trained: the prayer restores more life.", "Mastered: recovery surges hardest where the need is greatest."),
    "smite": _ability_entry("strike", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 3}, "Trained: the strike carries cleaner holy force.", "Mastered: condemned and undead targets feel the weight of it."),
    "blessing": _ability_entry("support", {"heal": 2, "guard": 2}, {"power": 1, "heal": 4, "guard": 4}, "Trained: the sheltering prayer steadies allies better.", "Mastered: the blessing guards deeper and heals with more certainty."),
    "renewinglight": _ability_entry("heal", {"power": 1, "heal": 4}, {"power": 2, "heal": 7}, "Trained: the light restores more fully.", "Mastered: cleansing recovery comes through with much more force."),
    "sanctuary": _ability_entry("support", {"heal": 2, "guard": 2}, {"heal": 4, "guard": 4, "turn": 1}, "Trained: the shelter reaches the whole party more firmly.", "Mastered: the sanctuary cushions danger for longer."),
    "cleanse": _ability_entry("support", {"heal": 2}, {"heal": 4, "turn": 1}, "Trained: the rite leaves more strength behind.", "Mastered: the cleansing touch leaves lasting recovery in its wake."),
    "radiantburst": _ability_entry("aoe", {"power": 1}, {"accuracy": 1, "power": 3}, "Trained: the flare catches the line more cleanly.", "Mastered: the burst punishes the restless dead and clustered foes harder."),
    "guardianlight": _ability_entry("guard", {"heal": 2, "guard": 3}, {"heal": 4, "guard": 5, "turn": 1}, "Trained: the ward hangs heavier over its target.", "Mastered: the light protects and recovers longer."),
    "holystrike": _ability_entry("strike", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 3}, "Trained: steel and sacred force arrive together more cleanly.", "Mastered: judged targets and undead take a punishing hit."),
    "guardingaura": _ability_entry("guard", {"guard": 3}, {"guard": 5, "turn": 1}, "Trained: the sacred cover catches more pressure.", "Mastered: the aura lingers and blunts the next exchange better."),
    "judgement": _ability_entry("control", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 2, "turn": 1}, "Trained: condemnation settles on the target more reliably.", "Mastered: the judged state stays on them longer."),
    "handofmercy": _ability_entry("heal", {"power": 1, "heal": 3}, {"power": 2, "heal": 5, "turn": 1}, "Trained: mercy restores more life.", "Mastered: the act of mercy leaves deeper recovery behind."),
    "consecrate": _ability_entry("support", {"power": 1, "heal": 2, "guard": 2}, {"power": 2, "heal": 4, "guard": 3, "turn": 1}, "Trained: the holy ground answers your side more strongly.", "Mastered: the consecrated space reinforces the whole exchange."),
    "shieldofdawn": _ability_entry("guard", {"guard": 3}, {"guard": 5, "turn": 1}, "Trained: the barrier catches more of the incoming strike.", "Mastered: dawnlight holds the line longer."),
    "rebukeevil": _ability_entry("strike", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 3}, "Trained: the rebuke lands with cleaner force.", "Mastered: cruel or corrupted targets feel it immediately."),
    "avenginglight": _ability_entry("aoe", {"power": 1}, {"accuracy": 1, "power": 2, "guard": 1}, "Trained: the retaliatory burst hits broader and harder.", "Mastered: the answering light leaves you harder to punish."),
    "firebolt": _ability_entry("strike", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 3}, "Trained: the bolt flies truer.", "Mastered: pinned or exposed targets are punished much harder."),
    "frostbind": _ability_entry("control", {"accuracy": 1}, {"accuracy": 2, "power": 1, "turn": 1}, "Trained: the cold grips more reliably.", "Mastered: the bind holds longer."),
    "arcspark": _ability_entry("aoe", {"accuracy": 1, "power": 1}, {"accuracy": 1, "power": 2, "turn": 1}, "Trained: the first strike chains cleaner.", "Mastered: charged arcs keep reaching through the line."),
    "flamewave": _ability_entry("aoe", {"power": 1}, {"power": 3, "turn": 1}, "Trained: the wave burns hotter.", "Mastered: enemies already held in place suffer under it longer."),
    "manashield": _ability_entry("guard", {"guard": 3}, {"guard": 6, "turn": 1}, "Trained: the shield gathers more force.", "Mastered: the arcane barrier holds through another exchange."),
    "staticfield": _ability_entry("control", {"power": 1, "turn": 1}, {"accuracy": 1, "power": 1, "turn": 1}, "Trained: the field is better at fixing enemies in place.", "Mastered: charged interference keeps pressure on the whole line."),
    "icelance": _ability_entry("finisher", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 4}, "Trained: the lance lands cleaner on pinned targets.", "Mastered: prepared targets get skewered by the full force of the cold."),
    "meteorsigil": _ability_entry("aoe", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 4}, "Trained: the sigil lands closer to the mark.", "Mastered: the catastrophic impact and splash bite much harder."),
    "mirrorveil": _ability_entry("mobility", {"guard": 2}, {"accuracy": 1, "guard": 4, "turn": 1}, "Trained: the veil catches more of the counterplay.", "Mastered: the mirrored opening stays slippery for longer."),
    "stormlance": _ability_entry("finisher", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 4}, "Trained: the bolt drives harder through prepared targets.", "Mastered: the charge tears through the main target and leaves stronger spillover."),
    "stab": _ability_entry("strike", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 3}, "Trained: the blade finds gaps more easily.", "Mastered: marks and binds are punished ruthlessly."),
    "feint": _ability_entry("mobility", {"guard": 2, "turn": 1}, {"accuracy": 1, "guard": 4, "turn": 1}, "Trained: the fake opening is harder to punish.", "Mastered: the setup window lasts longer."),
    "backstab": _ability_entry("finisher", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 4}, "Trained: compromised targets are carved up more cleanly.", "Mastered: every status opening gets cashed in hard."),
    "poisonblade": _ability_entry("control", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 1, "turn": 1}, "Trained: the venomous cut lands more surely.", "Mastered: the poison hangs in the blood longer."),
    "vanish": _ability_entry("mobility", {"guard": 1, "turn": 1}, {"guard": 2, "turn": 1}, "Trained: you disappear cleaner into the break.", "Mastered: the stealth window stays open longer."),
    "cheapshot": _ability_entry("control", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 2, "turn": 1}, "Trained: the hit catches weak footing more often.", "Mastered: the interruption and bind linger longer."),
    "shadowstep": _ability_entry("mobility", {"accuracy": 1, "guard": 2}, {"accuracy": 2, "guard": 4, "turn": 1}, "Trained: the entry angle is safer and cleaner.", "Mastered: the reposition leaves a stronger reset behind."),
    "eviscerate": _ability_entry("finisher", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 4}, "Trained: the execution blow pays off status setup harder.", "Mastered: every layered opening becomes lethal."),
    "thornlash": _ability_entry("strike", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 3}, "Trained: the lash lands more cleanly through your field.", "Mastered: rooted or marked prey gets dragged through real pain."),
    "minormend": _ability_entry("heal", {"power": 1, "heal": 2}, {"power": 2, "heal": 4}, "Trained: the pulse restores more life.", "Mastered: the mend answers the living field more strongly."),
    "entanglingroots": _ability_entry("control", {"accuracy": 1}, {"accuracy": 2, "power": 1, "turn": 1}, "Trained: roots catch ankles and ground more reliably.", "Mastered: the snare holds longer and reads the field better."),
    "wolfform": _ability_entry("stance", {"power": 1}, {"accuracy": 1, "power": 2, "turn": 1}, "Trained: the hunting form hits with cleaner instinct.", "Mastered: wolf form holds longer and keeps pressure on exposed prey."),
    "crowform": _ability_entry("stance", {"guard": 1, "turn": 1}, {"accuracy": 1, "guard": 2, "turn": 1}, "Trained: the aerial form settles into the field faster.", "Mastered: crow form maintains position and control longer."),
    "moonfire": _ability_entry("aoe", {"accuracy": 1, "power": 1}, {"accuracy": 2, "power": 2, "turn": 1}, "Trained: the pale flame finds harried targets more easily.", "Mastered: the fire keeps quarry pressure alive longer."),
    "barkskin": _ability_entry("guard", {"guard": 3}, {"guard": 5, "turn": 1}, "Trained: the bark ward thickens.", "Mastered: the living shield and grove pressure hold longer."),
    "livingcurrent": _ability_entry("heal", {"power": 1, "heal": 3}, {"power": 2, "heal": 5, "turn": 1}, "Trained: the current restores more life through the line.", "Mastered: the flow lingers and supports the secondary surge better."),
    "swarm": _ability_entry("aoe", {"power": 1, "turn": 1}, {"power": 2, "turn": 1}, "Trained: the harassment spreads better across the line.", "Mastered: the swarm keeps enemies exposed for longer."),
    "rejuvenationgrove": _ability_entry("support", {"heal": 2, "turn": 1}, {"heal": 4, "guard": 2, "turn": 1}, "Trained: the grove sustains the party more strongly.", "Mastered: the living ground keeps shelter and recovery active longer."),
    "bearform": _ability_entry("stance", {"guard": 2}, {"power": 1, "guard": 4, "turn": 1}, "Trained: the heavy form holds space better.", "Mastered: bear form plants harder and lasts longer."),
    "serpentform": _ability_entry("stance", {"power": 1, "turn": 1}, {"accuracy": 1, "power": 2, "turn": 1}, "Trained: the venomous form sharpens field pressure.", "Mastered: serpent form keeps its cruel edge and setup longer."),
    "wrathofthegrove": _ability_entry("aoe", {"accuracy": 1, "power": 2}, {"accuracy": 2, "power": 4, "turn": 1}, "Trained: the grove answers your call with more force.", "Mastered: established roots and forms cash out in a devastating sweep."),
}

ABILITY_MASTERY_ROLES = {
    ability_key: data["role"]
    for ability_key, data in ABILITY_MASTERY_DATA.items()
}

ROLE_BONUS_TABLE = {
    "strike": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 1, "power": 1, "heal": 0, "guard": 0, "turn": 0},
        3: {"accuracy": 2, "power": 2, "heal": 0, "guard": 0, "turn": 0},
    },
    "finisher": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 1, "power": 2, "heal": 0, "guard": 0, "turn": 0},
        3: {"accuracy": 2, "power": 3, "heal": 0, "guard": 0, "turn": 1},
    },
    "control": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 1, "power": 1, "heal": 0, "guard": 0, "turn": 0},
        3: {"accuracy": 2, "power": 1, "heal": 0, "guard": 0, "turn": 1},
    },
    "mark": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 1, "power": 0, "heal": 0, "guard": 0, "turn": 1},
        3: {"accuracy": 2, "power": 1, "heal": 0, "guard": 0, "turn": 1},
    },
    "guard": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 0, "power": 0, "heal": 0, "guard": 2, "turn": 0},
        3: {"accuracy": 0, "power": 0, "heal": 0, "guard": 5, "turn": 1},
    },
    "heal": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 0, "power": 1, "heal": 3, "guard": 0, "turn": 0},
        3: {"accuracy": 0, "power": 2, "heal": 6, "guard": 1, "turn": 1},
    },
    "support": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 0, "power": 1, "heal": 2, "guard": 2, "turn": 0},
        3: {"accuracy": 1, "power": 2, "heal": 4, "guard": 4, "turn": 1},
    },
    "aoe": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 0, "power": 1, "heal": 0, "guard": 0, "turn": 0},
        3: {"accuracy": 1, "power": 2, "heal": 0, "guard": 1, "turn": 1},
    },
    "mobility": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 1, "power": 0, "heal": 0, "guard": 2, "turn": 0},
        3: {"accuracy": 2, "power": 0, "heal": 0, "guard": 4, "turn": 1},
    },
    "stance": {
        1: {"accuracy": 0, "power": 0, "heal": 0, "guard": 0, "turn": 0},
        2: {"accuracy": 0, "power": 1, "heal": 0, "guard": 2, "turn": 0},
        3: {"accuracy": 1, "power": 2, "heal": 0, "guard": 4, "turn": 1},
    },
}

ROLE_TIER_TEXT = {
    "strike": {
        2: "Trained: lands steadier and hits harder.",
        3: "Mastered: strikes drive through openings with real authority.",
    },
    "finisher": {
        2: "Trained: pays off setup more sharply.",
        3: "Mastered: finishes cleaner and presses every opening harder.",
    },
    "control": {
        2: "Trained: control lands more reliably.",
        3: "Mastered: bindings and pressure linger longer.",
    },
    "mark": {
        2: "Trained: quarrying pressure holds longer.",
        3: "Mastered: marks settle in fast and stay dangerous.",
    },
    "guard": {
        2: "Trained: wards and stance discipline hold firmer.",
        3: "Mastered: protection lasts longer and catches harder hits.",
    },
    "heal": {
        2: "Trained: healing flows stronger.",
        3: "Mastered: healing and recovery effects deepen.",
    },
    "support": {
        2: "Trained: support magic and battle rhythm carry farther.",
        3: "Mastered: support effects reinforce the whole exchange.",
    },
    "aoe": {
        2: "Trained: battlefield pressure grows sharper.",
        3: "Mastered: wide effects strike cleaner and linger longer.",
    },
    "mobility": {
        2: "Trained: evasive timing tightens.",
        3: "Mastered: repositioning leaves cleaner follow-through.",
    },
    "stance": {
        2: "Trained: the form settles faster and hits harder.",
        3: "Mastered: the form holds longer and shapes the field more clearly.",
    },
}


def mastery_points_earned(level):
    """Return total mastery points earned by level milestones."""

    current_level = max(1, int(level or 1))
    return sum(1 for unlock_level in MASTERY_POINT_LEVELS if current_level >= unlock_level)


def mastery_rank_roman(rank):
    """Return roman numeral display for one mastery rank."""

    return MASTERY_ROMAN.get(max(1, min(int(rank or 1), 3)), "I")


def mastery_rank_label(rank):
    """Return exposition label for one mastery rank."""

    return MASTERY_EXPOSITION.get(max(1, min(int(rank or 1), 3)), "Known")


def format_mastery_name(name, rank):
    """Return a menu-friendly ability display with roman rank suffix."""

    rank = int(rank or 1)
    if rank <= 1:
        return name
    return f"{name} {mastery_rank_roman(rank)}"


def get_ability_mastery_role(ability_key):
    """Return the mastery role for one combat ability."""

    normalized = str(ability_key or "").lower()
    authored = ABILITY_MASTERY_DATA.get(normalized)
    if authored:
        return authored["role"]
    return ABILITY_MASTERY_ROLES.get(normalized, ROLE_DEFAULT)


def get_ability_mastery_bonuses(ability_key, rank):
    """Return normalized generic bonuses for one mastery rank."""

    clamped = max(1, min(int(rank or 1), 3))
    normalized = str(ability_key or "").lower()
    authored = ABILITY_MASTERY_DATA.get(normalized)
    role = get_ability_mastery_role(normalized)
    if authored:
        base = dict(authored["bonuses"].get(clamped, ZERO_BONUS))
    else:
        base = dict(ROLE_BONUS_TABLE.get(role, ROLE_BONUS_TABLE[ROLE_DEFAULT]).get(clamped, {}))
    base["rank"] = clamped
    base["role"] = role
    return base


def get_next_mastery_text(ability_key, current_rank):
    """Return the next mastery exposition line, if any."""

    next_rank = max(1, int(current_rank or 1)) + 1
    if next_rank > 3:
        return None
    normalized = str(ability_key or "").lower()
    authored = ABILITY_MASTERY_DATA.get(normalized)
    if authored:
        return authored["text"].get(next_rank)
    role = get_ability_mastery_role(normalized)
    return ROLE_TIER_TEXT.get(role, {}).get(next_rank)


def is_mastery_room(room):
    """Return whether this room is the Brambleford mastery trainer room."""

    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    return room_id == MASTERY_ROOM_ID


def can_train_ability(character, ability_key):
    """Return whether a character can train one combat ability."""

    if not character:
        return False
    ability_key = str(ability_key or "").lower()
    ability = ABILITY_LIBRARY.get(ability_key) or {}
    if not ability:
        return False
    get_actions = getattr(character, "get_unlocked_combat_abilities", None)
    if not callable(get_actions):
        return False
    unlocked_keys = {
        CONTENT.characters.ability_key(name)
        for name in (get_actions() or [])
    }
    return ability_key in unlocked_keys


def _format_mastery_bonus_text(ability_key, rank):
    bonuses = get_ability_mastery_bonuses(ability_key, rank)
    labels = {
        "accuracy": "Accuracy",
        "power": "Power",
        "heal": "Heal",
        "guard": "Guard",
        "turn": "Duration",
    }
    parts = [
        f"{label} +{bonuses[key]}"
        for key, label in labels.items()
        if bonuses.get(key)
    ]
    return ", ".join(parts)


def build_mastery_payload(character, *, status_message=None, status_tone="muted"):
    """Return a browser overlay payload for ability mastery training."""

    in_room = is_mastery_room(getattr(character, "location", None))
    earned = getattr(character, "get_earned_mastery_points", lambda: 0)()
    spent = getattr(character, "get_spent_mastery_points", lambda: 0)()
    available = getattr(character, "get_available_mastery_points", lambda: 0)()
    silver = int(getattr(getattr(character, "db", None), "brave_silver", 0) or 0)
    techniques = []

    for ability_name in getattr(character, "get_unlocked_combat_abilities", lambda: [])():
        ability_key = CONTENT.characters.ability_key(ability_name)
        ability = ABILITY_LIBRARY.get(ability_key) or {}
        rank = getattr(character, "get_ability_mastery_rank", lambda _key: 1)(ability_key)
        display_name = format_ability_display(ability_name, character)
        next_text = get_next_mastery_text(ability_key, rank)
        trainable = can_train_ability(character, ability_key)
        can_train = bool(in_room and trainable and rank < 3 and available > 0)
        role = get_ability_mastery_role(ability_key).replace("_", " ").title()
        if rank >= 3:
            status = "Mastered"
        elif not in_room:
            status = "Trainer required"
        elif available <= 0:
            status = "No mastery points"
        else:
            status = "Ready to train"

        techniques.append(
            {
                "key": ability_key,
                "name": display_name,
                "display_name": format_mastery_name(display_name, rank),
                "summary": ability.get("summary", ""),
                "role": role,
                "rank": rank,
                "rank_label": mastery_rank_label(rank),
                "current_bonus": _format_mastery_bonus_text(ability_key, rank),
                "next_bonus": _format_mastery_bonus_text(ability_key, rank + 1) if rank < 3 else "",
                "next_text": next_text or ("This technique is already mastered." if rank >= 3 else ""),
                "can_train": can_train,
                "status": status,
                "command": f"mastery {ability_key}" if can_train else "",
                "confirm": f"Train {display_name} to rank {rank + 1}?" if can_train else "",
            }
        )

    techniques.sort(key=lambda entry: (0 if entry["can_train"] else 1, entry["name"].lower()))

    return {
        "phase": "setup",
        "title": "Ability Mastery",
        "message": status_message or "",
        "message_tone": status_tone or "muted",
        "in_mastery_room": bool(in_room),
        "available": available,
        "spent": spent,
        "earned": earned,
        "silver": silver,
        "respec_cost": MASTERY_RESPEC_SILVER_COST,
        "can_respec": bool(in_room and spent > 0 and silver >= MASTERY_RESPEC_SILVER_COST),
        "respec_command": "mastery respec" if in_room and spent > 0 else "",
        "techniques": techniques,
    }
