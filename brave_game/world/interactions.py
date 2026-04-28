"""Contextual NPC and readable interactions for Brave's first slice."""

from world.activities import format_catch_log, format_kitchen_hearth_text, format_pole_rack_text
from world.commerce import format_shop_bonus, get_sellable_entries, get_shop_bonus
from world.content import get_content_registry
from world.forging import get_forge_entries
from world.questing import (
    advance_room_visit,
    advance_talk_to_npc,
    ensure_starter_quests,
    unlock_quest,
)
from world.race_world_hooks import get_extra_read_insight
from world.resonance import format_portal_plaque_text
from world.trophies import format_trophy_case_text
from world.tutorial import get_tutorial_entity_response

CONTENT = get_content_registry()
DIALOGUE_CONTENT = CONTENT.dialogue
TALK_RULES = DIALOGUE_CONTENT.talk_rules
STATIC_READ_RESPONSES = DIALOGUE_CONTENT.static_read_responses


def _quest_state(character, quest_key):
    return (character.db.brave_quests or {}).get(quest_key, {})


def _is_active(character, quest_key):
    return _quest_state(character, quest_key).get("status") == "active"


def _is_completed(character, quest_key):
    return _quest_state(character, quest_key).get("status") == "completed"


def _normalize_values(value):
    if value is None:
        return ()
    if isinstance(value, (tuple, list, set)):
        return tuple(value)
    return (value,)


def _matches_rule(character, rule):
    active = _normalize_values(rule.get("active"))
    if active and not all(_is_active(character, quest_key) for quest_key in active):
        return False

    completed = _normalize_values(rule.get("completed"))
    if completed and not all(_is_completed(character, quest_key) for quest_key in completed):
        return False

    active_any = _normalize_values(rule.get("active_any"))
    if active_any and not any(_is_active(character, quest_key) for quest_key in active_any):
        return False

    completed_any = _normalize_values(rule.get("completed_any"))
    if completed_any and not any(_is_completed(character, quest_key) for quest_key in completed_any):
        return False

    room_id = rule.get("room_id")
    if room_id and getattr(getattr(character, "location", None), "db", None):
        if getattr(character.location.db, "brave_room_id", None) != room_id:
            return False
    elif room_id:
        return False

    resonance = rule.get("resonance")
    if resonance:
        current = getattr(getattr(character.location, "db", None), "brave_resonance", "fantasy")
        if current != resonance:
            return False

    resource_key = rule.get("resource_below_max")
    if resource_key:
        resources = character.db.brave_resources or {}
        derived = character.db.brave_derived_stats or {}
        if resources.get(resource_key, 0) >= derived.get(f"max_{resource_key}", 0):
            return False

    xp_eq = rule.get("xp_eq")
    if xp_eq is not None and (character.db.brave_xp or 0) != xp_eq:
        return False

    can_customize_build = rule.get("can_customize_build")
    if can_customize_build is not None and bool(character.can_customize_build()) != bool(can_customize_build):
        return False

    return True


def _resolve_talk_response(character, entity_id):
    for rule in TALK_RULES.get(entity_id, ()):
        if _matches_rule(character, rule):
            return rule["text"]
    return None


def _leda_thornwick(character, is_action=False):
    sellables = get_sellable_entries(character)
    bonus = get_shop_bonus(character)

    if bonus:
        return (
            "You've already put in enough useful work for one stretch. Bring your finds to the counter and I'll honor "
            f"that |w{format_shop_bonus(bonus)}|n."
        )
    if sellables:
        names = ", ".join(entry["name"] for entry in sellables[:3])
        if len(sellables) > 3:
            names += ", ..."
        return (
            "You have trade goods worth my time. Check the shop to see prices, sell your items to cash them out, or "
            f"use a shift if you want me in a better mood first. Right now I can move {names}."
        )
    return (
        "If it keeps a traveler dry, shod, fed, or sensibly tied to their pack, I care. Bring me pelts, salvage, herbs, "
        "and other practical finds. Check the shop for current prices or use a shift if you want to help at the counter."
    )


def _torren_ironroot(character, is_action=False):
    entries = get_forge_entries(character)
    ready = [entry for entry in entries if entry["ready"]]

    if ready:
        names = ", ".join(entry["result_name"] for entry in ready[:2])
        if len(ready) > 2:
            names += ", ..."
        return (
            "You've got enough scrap and silver for me to do honest work. Open the forge and pick a piece. "
            f"Right now I could turn your kit into {names}."
        )
    if entries:
        first = entries[0]
        missing = [
            f"{material['name']} {material['owned']}/{material['required']}"
            for material in first["materials"]
            if material["owned"] < material["required"]
        ]
        return (
            f"I can rework that {first['source_name']} into a {first['result_name']}, but not from optimism alone. "
            f"Bring me {', '.join(missing)} and {first['silver_cost']} silver. Check the forge if you want the full ledger."
        )
    return (
        "I improve field kit, not heirloom nonsense. Wear the piece you want fixed proper, bring me useful scrap and "
        "silver, and use the forge so we can both stop pretending this is a mystery."
    )


def _captain_harl_rowan(character, is_action=False):
    response = _resolve_talk_response(character, "captain_harl_rowan")
    room = getattr(character, "location", None)
    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)

    # Fallback response if no specific talk rule matched but the quest is active
    if not response and room_id == "brambleford_training_yard" and _is_active(character, "practice_makes_heroes"):
        response = (
            "Tamsin sent you through with your head on straight. Good. The south lantern going dark is not your first job; surviving long enough to reach it is. "
            "Start close: head south to the green, then west to the inn. Uncle Pib's cellar is tearing itself apart, and the stores matter if the road stays cut. "
            "Clear that, then Mira will put a name to what hit the fences."
        )

    if (
        not response
        and room_id == "brambleford_training_yard"
        and _is_completed(character, "practice_makes_heroes")
        and not bool(getattr(character.db, "brave_harl_cellar_job_assigned", False))
    ):
        response = (
            "You got through the first report fast enough. Good. The south lantern is out, the road cart came in torn, "
            "and we still start close: head south to the green, then west to Uncle Pib. His cellar is tearing itself apart, "
            "and food stores matter if the road stays cut."
        )

    if is_action and response and room_id == "brambleford_training_yard" and (
        _is_active(character, "practice_makes_heroes")
        or (
            _is_completed(character, "practice_makes_heroes")
            and not bool(getattr(character.db, "brave_harl_cellar_job_assigned", False))
        )
    ):
        character.db.brave_harl_cellar_job_assigned = True
        character.db.brave_opening_sequence_active = False
        advance_talk_to_npc(character, "captain_harl_rowan")
        unlock_quest(character, "rats_in_the_kettle")
        ensure_starter_quests(character)
    return response


def _town_notice_board(character):
    lines = [
        "Several notices have been pinned and re-pinned so often that the corners are mostly thread. One fresh sheet is still wet from the rain and the ink has been pressed hard enough to dent the board.",
        "",
        "- SOUTH ROAD LANTERN OUT BEFORE DAWN. REPORT CUT HARNESS, WAGON DAMAGE, OR STRANGE LIGHTS.",
        "- Wolves bold near the east road. Do not leave goats tethered overnight.",
        "- Missing flour sacks and fence planks reported by farms beyond the gate.",
        "- Militia requests steady hands, not loud ones.",
    ]

    if _is_active(character, "practice_makes_heroes"):
        lines.append("- Rowan's chalk note: New hands report to the Training Yard. The inn cellar comes first; the road comes after.")
    if _is_active(character, "rats_in_the_kettle"):
        lines.append("- Uncle Pib requests immediate help with cellar rats, missing flour, and civic dignity. Stores matter if the road stays cut. Inn west, cellar below.")
    elif _is_active(character, "roadside_howls") or _is_active(character, "fencebreakers"):
        lines.append("- Mira's note: Claw mud, cut harness, and stolen rails all point east. Travel in company and report at the gate first.")
    elif _is_active(character, "ruk_the_fence_cutter"):
        lines.append("- A newer warning reads: Fence chief still active beyond Wolf Turn. He may know why the south lantern went black. Do not go alone.")
    elif _is_active(character, "what_whispers_in_the_wood") or _is_active(character, "greymaws_trail"):
        lines.append("- Sister Maybelle requests fresh moonleaf and fewer mauled volunteers from the south trail.")
    elif _is_completed(character, "fencebreakers"):
        lines.append("- One newer note reads: Road slightly less terrible. Do not get ambitious.")
    if _is_completed(character, "ruk_the_fence_cutter"):
        lines.append("- Someone has scrawled underneath: Ruk is dead. The road might breathe again.")
    if _is_completed(character, "greymaws_trail"):
        lines.append("- Another hand has added: Greymaw's dead. The woods are still strange, but less hungry.")
    if _is_active(character, "lanterns_at_dusk"):
        lines.append("- Mayor's hand: Report unusual lights or movement west of the old stone path. Chapel lantern watch doubled.")
    elif _is_active(character, "do_not_disturb_the_dead"):
        lines.append("- Chapel request: Keep children clear of Old Barrow Field until Brother Alden says otherwise.")
    elif _is_active(character, "the_knight_without_rest"):
        lines.append("- A hastier note warns: Do not approach the Sunken Dais alone. The old knight is awake.")
    elif _is_completed(character, "the_knight_without_rest"):
        lines.append("- The western notice is finally crossed through in heavy ink: Barrow watch reduced to normal.")
    if _is_active(character, "smoke_on_the_ridge"):
        lines.append("- A fresh note from Rowan reads: Smoke seen at the ruined ridge watchtower north of Ruk's old camp. Capable hands report in.")
    elif _is_active(character, "loose_arrows") or _is_active(character, "captain_varn_blackreed"):
        lines.append("- New warning: Bandit arrows from the ridge tower. Avoid the north climb unless you mean to clear it.")
    elif _is_completed(character, "captain_varn_blackreed"):
        lines.append("- Someone has written beneath the old ridge warning: Blackreed is down. Road watch returning to normal rotation.")
    if _is_active(character, "below_the_fencebreakers"):
        lines.append("- Mira's hand, sharper than chalk deserves: Goblin sink found east of Ruk's old camp. Capable groups only.")
    elif _is_active(character, "gutters_and_hexes") or _is_active(character, "the_pot_kings_feast"):
        lines.append("- New east-country notice: Goblin warrens confirmed under the ridge. Do not enter hungry, alone, or optimistic.")
    elif _is_completed(character, "the_pot_kings_feast"):
        lines.append("- A greasy note has been pinned over an older warning: Pot-King's down. East road watch downgraded from awful to manageable.")
    if _is_active(character, "bogwater_rumors"):
        lines.append("- Fresh note from Mira: Blackfen trail south of the old camp is open only to capable groups. If the marsh offers lights, decline politely.")
    elif _is_active(character, "lights_in_the_reeds") or _is_active(character, "miretooths_claim"):
        lines.append("- South-watch addendum: Rot crows, marsh lights, and a large predator confirmed in Blackfen. Travel armed and in company.")
    elif _is_active(character, "the_south_light") or _is_active(character, "locks_under_blackwater") or _is_active(character, "the_hollow_lantern"):
        lines.append("- Observatory notice: Wrong south light confirmed beyond Miretooth's Wallow at the old drowned weir. Joss requests capable hands and strongly worded skepticism.")
    elif _is_completed(character, "miretooths_claim"):
        lines.append("- New marsh notice: Miretooth is dead. Blackfen remains a bad idea, but now a quieter one.")
    if _is_completed(character, "the_hollow_lantern"):
        lines.append("- Fresh civic addendum: South weir light extinguished. Please stop asking whether drowned public works count as weather.")
    if _is_active(character, "bridgework_for_joss") or _is_active(character, "signal_in_the_scrap"):
        lines.append("- Joss requests steady salvage hands at the observatory. Strange lights are now considered official.")
    if _is_completed(character, "foreman_coilback"):
        lines.append("- Someone has added in neat script: Beacon Core hung in the Trophy Hall. Please stop tapping the glass.")

    return "\n".join(lines)


DYNAMIC_TALK_HANDLERS = {
    "captain_harl_rowan": _captain_harl_rowan,
    "leda_thornwick": _leda_thornwick,
    "torren_ironroot": _torren_ironroot,
}


DYNAMIC_READ_HANDLERS = {
    "town_notice_board": _town_notice_board,
    "great_catch_log": lambda _character: format_catch_log(),
    "kitchen_hearth": format_kitchen_hearth_text,
    "loaner_pole_rack": lambda _character: format_pole_rack_text(),
    "nexus_gate_plaque": lambda _character: format_portal_plaque_text(),
    "trophy_vitrine": lambda _character: format_trophy_case_text(),
}


def get_entity_response(character, entity, action, is_action=False):
    """Return contextual interaction text for a local entity."""

    entity_id = getattr(entity.db, "brave_entity_id", None)
    entity_kind = getattr(entity.db, "brave_entity_kind", None)

    if action == "talk" and entity_kind != "npc":
        return None
    if action == "read" and entity_kind != "readable":
        return None

    response = get_tutorial_entity_response(character, entity, action, is_action=is_action)
    if response is None:
        if action == "talk":
            handler = DYNAMIC_TALK_HANDLERS.get(entity_id)
            if handler:
                try:
                    response = handler(character, is_action=is_action)
                except TypeError:
                    response = handler(character)
            else:
                response = _resolve_talk_response(character, entity_id)

        elif action == "read":
            handler = DYNAMIC_READ_HANDLERS.get(entity_id)
            extra = get_extra_read_insight(character, entity_id)
            if handler:
                response = handler(character)
            else:
                response = STATIC_READ_RESPONSES.get(entity_id)

            if response and extra:
                response += "\n\n" + extra

    if is_action and action == "talk" and response:
        speech_line = " ".join(str(response).replace("\n", " ").split())
        if speech_line:
            sentence_end = min(
                [index for index in (speech_line.find("."), speech_line.find("!"), speech_line.find("?")) if index >= 0]
                or [-1]
            )
            if sentence_end >= 0:
                speech_line = speech_line[: sentence_end + 1]
            if len(speech_line) > 150:
                speech_line = speech_line[:147].rstrip() + "..."

            from world.browser_panels import broadcast_npc_speech, send_npc_speech_event

            send_npc_speech_event(character, entity.key, speech_line)
            broadcast_npc_speech(character.location, entity.key, speech_line, exclude=[character])

    return response


def get_entity_emote_response(character, entity, emote_text):
    """Return an optional authored response for a targeted emote."""

    if getattr(entity.db, "brave_entity_kind", None) != "npc":
        return None

    reactions = getattr(entity.db, "brave_emote_reactions", None)
    if isinstance(reactions, str):
        return reactions
    if not isinstance(reactions, dict):
        return getattr(entity.db, "brave_emote_response", None)

    lowered = str(emote_text or "").strip().lower()
    if not lowered:
        return reactions.get("default") or reactions.get("any")

    verb = lowered.split()[0]
    if verb.endswith("ies") and len(verb) > 3:
        verb = verb[:-3] + "y"
    elif verb.endswith("es"):
        stem = verb[:-2]
        if stem.endswith(("s", "x", "z", "ch", "sh", "o")):
            verb = stem
    elif verb.endswith("s") and len(verb) > 1:
        verb = verb[:-1]

    for key in (verb, lowered.split()[0], "default", "any"):
        response = reactions.get(key)
        if response:
            return response
    return None
