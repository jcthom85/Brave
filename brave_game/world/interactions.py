"""Contextual NPC and readable interactions for Brave's first slice."""

from world.activities import format_catch_log, format_kitchen_hearth_text, format_pole_rack_text
from world.commerce import format_shop_bonus, get_sellable_entries, get_shop_bonus
from world.content import get_content_registry
from world.forging import get_forge_entries
from world.questing import advance_entity_talk
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


def _completed_any(character, *quest_keys):
    return any(_is_completed(character, quest_key) for quest_key in quest_keys)


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


def _leda_thornwick(character):
    if _is_completed(character, "the_hollow_lantern"):
        return (
            "Business improves when the town stops arguing with drowned lights. Road pelts, ridge scrap, marsh salvage, "
            "all of it finally comes in like trade goods instead of evidence. Use |wshop|n if you want the board that matches the calmer mood."
        )
    if _is_completed(character, "miretooths_claim"):
        return (
            "The marsh crews have started bringing things in without looking over their shoulders every six breaths. "
            "That usually means somebody competent solved a problem. If you've got fen salvage, pelts, or road junk, "
            "I'll price it fair at |wshop|n."
        )
    if _is_completed(character, "captain_varn_blackreed"):
        return (
            "The ridge road's breathing again, which means wagons, which means coin, which means people suddenly remember "
            "they need boots and straps. I approve of any victory that improves both safety and leather turnover."
        )
    if _is_completed(character, "greymaws_trail"):
        return (
            "The south trail has stopped sending back every hunter with the same haunted look. Good. If the woods are "
            "behaving even a little better, Brambleford can go back to ruining cloaks the ordinary way."
        )

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
            "You have trade goods worth my time. Use |wshop|n to see prices, |wsell <item>|n to cash them out, or "
            f"|wshift|n if you want me in a better mood first. Right now I can move {names}."
        )
    return (
        "If it keeps a traveler dry, shod, fed, or sensibly tied to their pack, I care. Bring me pelts, salvage, herbs, "
        "and other practical finds. Use |wshop|n for current prices or |wshift|n if you want to help at the counter."
    )


def _torren_ironroot(character):
    if _is_completed(character, "the_hollow_lantern"):
        return (
            "Road iron, ridge fittings, goblin junk, marsh salvage, and now drowned line brass. That's a proper season's "
            "worth of work in one ugly stretch. If you've hauled any of it back, use |wforge|n and I'll turn the right pieces into something that stays useful."
        )
    if _is_completed(character, "captain_varn_blackreed"):
        return (
            "The watch can finally stop spending good metal replacing arrows and panic. I've got cleaner time for real kit work now. "
            "Bring me road scrap and silver and we'll see whether your field gear deserves improvement."
        )
    if _is_completed(character, "the_knight_without_rest"):
        return (
            "Chapel folk asked for quieter work after the barrow business. Hinges, lantern brackets, a new bell-clapper cap. "
            "Town gets like that after the dead remember how to stand up."
        )

    entries = get_forge_entries(character)
    ready = [entry for entry in entries if entry["ready"]]

    if ready:
        names = ", ".join(entry["result_name"] for entry in ready[:2])
        if len(ready) > 2:
            names += ", ..."
        return (
            "You've got enough scrap and silver for me to do honest work. Use |wforge|n and pick a piece. "
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
            f"Bring me {', '.join(missing)} and {first['silver_cost']} silver. Use |wforge|n if you want the full ledger."
        )
    return (
        "I improve field kit, not heirloom nonsense. Wear the piece you want fixed proper, bring me useful scrap and "
        "silver, and use |wforge|n so we can both stop pretending this is a mystery."
    )


def _town_notice_board(character):
    post_ruk_return = _is_completed(character, "ruk_the_fence_cutter") and not any(
        _is_active(character, quest_key)
        for quest_key in (
            "what_whispers_in_the_wood",
            "herbs_for_sister_maybelle",
            "greymaws_trail",
            "lanterns_at_dusk",
            "do_not_disturb_the_dead",
            "the_knight_without_rest",
            "smoke_on_the_ridge",
            "loose_arrows",
            "captain_varn_blackreed",
        )
    )

    lines = [
        "Several notices have been pinned and re-pinned so often that the corners are mostly thread.",
        "",
        "- Wolves bold near the east road. Do not leave goats tethered overnight.",
        "- Missing flour sacks and fence planks reported by farms beyond the gate.",
        "- Militia requests steady hands, not loud ones.",
    ]

    if _is_active(character, "practice_makes_heroes"):
        lines.append("- Rowan's chalk note: New hands head west to the inn after the yard. Pib's cellar is the first real test.")
    if _is_active(character, "rats_in_the_kettle"):
        lines.append("- Uncle Pib requests immediate help with cellar rats, missing flour, and civic dignity. Inn west, cellar below.")
    elif _is_active(character, "roadside_howls") or _is_active(character, "fencebreakers"):
        lines.append("- Mira's note: Trouble thickest beyond East Gate. Travel in company and report at the gate first.")
    elif _is_active(character, "ruk_the_fence_cutter"):
        lines.append("- A newer warning reads: Fence chief still active beyond Wolf Turn. Do not go alone.")
    elif _is_active(character, "what_whispers_in_the_wood") or _is_active(character, "greymaws_trail"):
        lines.append("- Sister Maybelle requests fresh moonleaf and fewer mauled volunteers from the south trail.")
    elif _is_completed(character, "fencebreakers"):
        lines.append("- One newer note reads: Road slightly less terrible. Do not get ambitious.")
    if _is_completed(character, "ruk_the_fence_cutter"):
        lines.append("- Someone has scrawled underneath: Ruk is dead. The road might breathe again.")
    if post_ruk_return:
        lines.append("- Fresh town note: Maybelle wants capable hands on the south trail now that the road has breathing room.")
        lines.append("- Margin note in a different hand: Mayor and observatory both expect the town's next trouble to be older, not louder.")
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
    return "\n".join(lines)


def _mayors_ledger(character):
    lines = [
        "The ledger has been reopened to the current damage page rather than the tax page, which says most of what it needs to.",
        "",
        "- LANTERN OIL SHORT BY TWO CRATES.",
        "- WEST WATCH REPORTS LIGHT LOSS AT DUSK.",
        "- CHAPEL REQUESTS ADDITIONAL VOLUNTEERS WITH STEADY NERVES.",
    ]

    if _is_completed(character, "greymaws_trail"):
        lines.append("- SOUTH TRAIL UPDATE: Greymaw culled. Herb gatherers returning in pairs instead of funerary language.")
    if _is_completed(character, "the_knight_without_rest"):
        lines.append("- WEST FIELD ENTRY CLOSED: Sir Edric laid to rest. Lantern allotment reduced from crisis levels.")
    if _is_completed(character, "captain_varn_blackreed"):
        lines.append("- RIDGE ROUTE: Blackreed removed. Wagon losses projected to become survivable again.")
    if _is_completed(character, "the_pot_kings_feast"):
        lines.append("- EAST ROAD UNDER-RIDGE THREAT: Goblin crown broken. Watch posture lowered from dire to merely unpleasant.")
    if _is_completed(character, "miretooths_claim"):
        lines.append("- BLACKFEN EDGE: Large predator removed. Marsh remains unacceptable, but now less organized about it.")
    if _is_completed(character, "the_hollow_lantern"):
        lines.append("- SOUTH WEIR NOTE: Wrong light extinguished. Brambleford may resume ordinary frontier anxieties.")

    return "\n".join(lines)


def _outfitters_chalkboard(character):
    lines = [
        "Leda's chalk hand is spare and direct:",
        "",
        "WE BUY PELTS, HERBS, SALVAGE, ROAD SCRAP, AND OTHER SENSIBLE FINDS.",
        "FAIR PRICES FOR FAIR HANDS.",
        "ASK ABOUT A SHIFT IF YOU WANT THE BETTER COLUMN.",
    ]

    if _is_completed(character, "greymaws_trail"):
        lines.append("SOUTH TRAIL NOTE: WOODS PELTS WANTED AGAIN. TRY TO BRING THEM IN LESS CHEWED.")
    if _is_completed(character, "captain_varn_blackreed"):
        lines.append("RIDGE TRADE ADDENDUM: TOWER SCRAP, SPENT ARROW BUNDLES, AND SALVAGEABLE HARNESS PARTS NOW ACCEPTED.")
    if _completed_any(character, "miretooths_claim", "the_hollow_lantern"):
        lines.append("MARSH COLUMN REOPENED: FEN SALVAGE PRICED FAIR IF IT DOES NOT LEAK, HUM, OR CURSE THE COUNTER.")

    return "\n".join(lines)


def _forge_order_board(character):
    lines = [
        "Torren's board reads: NAIL KEGS FOR SOUTH FARM. HINGE SET FOR MAYOR'S HALL. TWO SPEAR TIPS FOR THE WATCH.",
        "Below that, in heavier chalk: FIELD KIT IMPROVEMENTS DONE TO ORDER. WEAR IT IN. BRING SCRAP. PAY SILVER. ASK WITH |wforge|n, NOT WITH STORIES.",
    ]

    if _is_completed(character, "the_knight_without_rest"):
        lines.append("New line added: CHAPEL LANTERN BRACKETS REPLACED AFTER BARROW TROUBLE.")
    if _is_completed(character, "captain_varn_blackreed"):
        lines.append("Watch addendum: RIDGE ARROW CATCH PLATES AND TOWER HOOKS FOR REPAIR.")
    if _is_completed(character, "the_hollow_lantern"):
        lines.append("Newest note, carved harder than the rest: SOUTH WEIR BRASS TO BE MELTED DOWN INTO SOMETHING HONEST.")

    return "\n".join(lines)


DYNAMIC_TALK_HANDLERS = {
    "leda_thornwick": _leda_thornwick,
    "torren_ironroot": _torren_ironroot,
}


DYNAMIC_READ_HANDLERS = {
    "town_notice_board": _town_notice_board,
    "mayors_ledger": _mayors_ledger,
    "outfitters_chalkboard": _outfitters_chalkboard,
    "forge_order_board": _forge_order_board,
    "great_catch_log": lambda _character: format_catch_log(),
    "kitchen_hearth": format_kitchen_hearth_text,
    "loaner_pole_rack": lambda _character: format_pole_rack_text(),
    "trophy_vitrine": lambda _character: format_trophy_case_text(),
}


def get_entity_response(character, entity, action):
    """Return contextual interaction text for a local entity."""

    entity_id = getattr(entity.db, "brave_entity_id", None)
    entity_kind = getattr(entity.db, "brave_entity_kind", None)

    if action == "talk" and entity_kind != "npc":
        return None
    if action == "read" and entity_kind != "readable":
        return None

    tutorial_response = get_tutorial_entity_response(character, entity, action)
    if tutorial_response is not None:
        if action == "talk":
            advance_entity_talk(character, entity_id)
        return tutorial_response

    if action == "talk":
        advance_entity_talk(character, entity_id)
        response = _resolve_talk_response(character, entity_id)
        if response is not None:
            return response
        handler = DYNAMIC_TALK_HANDLERS.get(entity_id)
        return handler(character) if handler else None

    if action == "read":
        handler = DYNAMIC_READ_HANDLERS.get(entity_id)
        if handler:
            return handler(character)
        return STATIC_READ_RESPONSES.get(entity_id)

    return None
