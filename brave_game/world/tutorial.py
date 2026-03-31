"""Tutorial state and guided onboarding helpers for Brave."""

from world.bootstrap import get_room
from world.data.character_options import CLASSES


TUTORIAL_START_ROOM_ID = "tutorial_wayfarers_yard"
TUTORIAL_GATE_ROOM_ID = "tutorial_gate_walk"
TUTORIAL_TRAINING_ROOM_ID = "brambleford_training_yard"
TUTORIAL_HOME_ROOM_ID = "brambleford_town_green"
TUTORIAL_VERMIN_ROOM_ID = "tutorial_vermin_pens"

TUTORIAL_ROOM_IDS = {
    "tutorial_wayfarers_yard",
    "tutorial_quartermaster_shed",
    "tutorial_family_post",
    "tutorial_sparring_ring",
    "tutorial_vermin_pens",
    "tutorial_gate_walk",
}

TUTORIAL_FLAGS = (
    "talked_tamsin",
    "visited_quartermaster_shed",
    "returned_to_wayfarers_yard",
    "talked_nella",
    "viewed_gear",
    "viewed_pack",
    "read_supply_board",
    "talked_brask",
    "won_vermin_fight",
    "talked_peep",
    "read_family_post_sign",
    "talked_harl",
)

CLASS_ABILITY_HINTS = {
    "warrior": "Strike",
    "ranger": "Quick Shot",
    "cleric": "Smite",
    "mage": "Firebolt",
    "rogue": "Stab",
    "paladin": "Holy Strike",
    "druid": "Thorn Lash",
}

TUTORIAL_STEPS = {
    "first_steps": {
        "title": "First Steps In Brambleford",
        "summary": "Talk to Sergeant Tamsin, head east to the shed, and return to Wayfarer's Yard.",
    },
    "pack_before_walk": {
        "title": "Pack Before You Walk",
        "summary": "Let Nella square your kit away, then check your gear, open your pack, and read the supply board.",
    },
    "stand_your_ground": {
        "title": "Stand Your Ground",
        "summary": "Speak with Ringhand Brask before you test yourself in the vermin pens.",
    },
    "clear_the_pens": {
        "title": "Clear The Pens",
        "summary": "Start a fight in the vermin pens and win one clean encounter.",
    },
    "through_the_gate": {
        "title": "Through The Gate",
        "summary": "Head south to the Training Yard and report to Captain Harl Rowan.",
    },
}


def _default_flags():
    return {flag: False for flag in TUTORIAL_FLAGS}


def _save_state(character, state):
    character.db.brave_tutorial = state
    character.db.brave_tutorial_current_step = state.get("step")
    return state


def should_start_tutorial(account):
    """Whether a newly created character should start in the tutorial."""

    return not getattr(account.db, "brave_tutorial_completed", False)


def ensure_tutorial_state(character):
    """Normalize tutorial state for this character."""

    state = dict(character.db.brave_tutorial or {})
    flags = dict(state.get("flags") or {})
    for flag in TUTORIAL_FLAGS:
        flags.setdefault(flag, False)

    status = state.get("status") or "inactive"
    step = state.get("step")
    state = {"status": status, "step": step, "flags": flags}

    if status == "active":
        state["step"] = _determine_step(flags)
        if state["step"] is None:
            state = complete_tutorial(character, save=False)
    return _save_state(character, state)


def begin_tutorial(character):
    """Mark the tutorial as active on a new character."""

    state = {
        "status": "active",
        "flags": _default_flags(),
        "step": "first_steps",
    }
    return _save_state(character, state)


def complete_tutorial(character, save=True):
    """Mark the tutorial as completed and unlock later skips for the account."""

    state = {
        "status": "completed",
        "step": None,
        "flags": dict((character.db.brave_tutorial or {}).get("flags") or _default_flags()),
    }
    account = getattr(character, "account", None)
    if account:
        account.db.brave_tutorial_completed = True

    home_room = get_room(TUTORIAL_HOME_ROOM_ID)
    if home_room:
        character.home = home_room

    if save:
        return _save_state(character, state)
    return state


def is_tutorial_active(character):
    """Whether the character is in the active tutorial flow."""

    return ensure_tutorial_state(character).get("status") == "active"


def is_tutorial_room(room):
    """Whether a room belongs to the tutorial branch."""

    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    return room_id in TUTORIAL_ROOM_IDS


def get_tutorial_start_room():
    """Return the tutorial spawn room, if available."""

    return get_room(TUTORIAL_START_ROOM_ID)


def get_tutorial_defeat_room(character):
    """Return the tutorial recovery room if the character is still onboarding."""

    if not is_tutorial_active(character):
        return None
    return get_room(TUTORIAL_START_ROOM_ID)


def _determine_step(flags):
    if not flags.get("talked_tamsin"):
        return "first_steps"
    if not flags.get("visited_quartermaster_shed") or not flags.get("returned_to_wayfarers_yard"):
        return "first_steps"
    if not (
        flags.get("talked_nella")
        and flags.get("viewed_gear")
        and flags.get("viewed_pack")
        and flags.get("read_supply_board")
    ):
        return "pack_before_walk"
    if not flags.get("talked_brask"):
        return "stand_your_ground"
    if not flags.get("won_vermin_fight"):
        return "clear_the_pens"
    if not flags.get("talked_harl"):
        return "through_the_gate"
    return None


def _set_flag(character, flag):
    state = ensure_tutorial_state(character)
    if state.get("status") != "active":
        return state
    if flag in state["flags"]:
        state["flags"][flag] = True
    state["step"] = _determine_step(state["flags"])
    if state["step"] is None:
        state = complete_tutorial(character, save=False)
    return _save_state(character, state)


def handle_room_enter(character, room):
    """Advance tutorial state from room movement."""

    state = ensure_tutorial_state(character)
    if state.get("status") != "active" or not room:
        return state

    room_id = getattr(room.db, "brave_room_id", None)
    if room_id == "tutorial_quartermaster_shed":
        return _set_flag(character, "visited_quartermaster_shed")
    if (
        room_id == "tutorial_wayfarers_yard"
        and state["flags"].get("talked_tamsin")
        and state["flags"].get("visited_quartermaster_shed")
    ):
        return _set_flag(character, "returned_to_wayfarers_yard")
    return state


def record_command_event(character, event_key):
    """Advance tutorial state from command usage."""

    mapping = {
        "gear": "viewed_gear",
        "pack": "viewed_pack",
    }
    flag = mapping.get(event_key)
    if not flag:
        return ensure_tutorial_state(character)
    return _set_flag(character, flag)


def record_encounter_victory(character, room):
    """Advance tutorial state from the first live tutorial win."""

    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    if room_id != TUTORIAL_VERMIN_ROOM_ID:
        return ensure_tutorial_state(character)
    return _set_flag(character, "won_vermin_fight")


def _remaining_pack_tasks(flags):
    tasks = []
    if not flags.get("viewed_gear"):
        tasks.append("Use gear")
    if not flags.get("viewed_pack"):
        tasks.append("Use pack")
    if not flags.get("read_supply_board"):
        tasks.append("Read the supply board")
    return tasks


def _is_active_quest(character, quest_key):
    return (character.db.brave_quests or {}).get(quest_key, {}).get("status") == "active"


def format_tutorial_block(character):
    """Return a tutorial journal block for the active onboarding flow."""

    state = ensure_tutorial_state(character)
    if state.get("status") != "active":
        return None

    step_key = state.get("step") or "first_steps"
    step = TUTORIAL_STEPS[step_key]
    flags = state["flags"]
    lines = [
        f"|w{step['title']}|n [Tutorial]",
        f"  {step['summary']}",
    ]

    if step_key == "first_steps":
        lines.append(
            f"  [{'x' if flags.get('talked_tamsin') else ' '}] Speak with Sergeant Tamsin Vale."
        )
        lines.append(
            f"  [{'x' if flags.get('visited_quartermaster_shed') else ' '}] Head east to Quartermaster Shed."
        )
        lines.append(
            f"  [{'x' if flags.get('returned_to_wayfarers_yard') else ' '}] Return to Wayfarer's Yard."
        )
    elif step_key == "pack_before_walk":
        lines.append(
            f"  [{'x' if flags.get('talked_nella') else ' '}] Speak with Quartermaster Nella Cobb."
        )
        lines.append(
            f"  [{'x' if flags.get('viewed_gear') else ' '}] Check your gear."
        )
        lines.append(
            f"  [{'x' if flags.get('viewed_pack') else ' '}] Open your pack."
        )
        lines.append(
            f"  [{'x' if flags.get('read_supply_board') else ' '}] Read the supply board."
        )
    elif step_key == "stand_your_ground":
        lines.append(
            f"  [{'x' if flags.get('talked_brask') else ' '}] Speak with Ringhand Brask in the Sparring Ring."
        )
    elif step_key == "clear_the_pens":
        lines.append(
            f"  [{'x' if flags.get('won_vermin_fight') else ' '}] Win one fight in the Vermin Pens."
        )
    elif step_key == "through_the_gate":
        lines.append(
            f"  [{'x' if flags.get('talked_harl') else ' '}] Report to Captain Harl Rowan in the Training Yard."
        )

    optional_done = flags.get("read_family_post_sign") or flags.get("talked_peep")
    lines.append(
        f"  [{'x' if optional_done else ' '}] Optional: Visit Family Post to learn party basics."
    )
    return "\n".join(lines)


def get_tutorial_focus(character, room):
    """Return tutorial-specific scene-card focus prompts for the current room."""

    state = ensure_tutorial_state(character)
    if state.get("status") != "active" or not room:
        return []

    room_id = getattr(room.db, "brave_room_id", None)
    step = state.get("step")
    flags = state["flags"]

    if step == "first_steps":
        if room_id == TUTORIAL_START_ROOM_ID and not flags.get("talked_tamsin"):
            return ["Talk to Sergeant Tamsin"]
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Head east to Quartermaster Shed", "Return here after a quick look"]
        if room_id == "tutorial_quartermaster_shed":
            return ["Head west back to Wayfarer's Yard"]

    if step == "pack_before_walk":
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Head east to Quartermaster Shed", "Talk to Quartermaster Nella"]
        if room_id == "tutorial_quartermaster_shed":
            return _remaining_pack_tasks(flags) or ["Head back west when you're ready"]

    if step == "stand_your_ground":
        if room_id == "tutorial_family_post":
            others = [
                obj.key
                for obj in room.contents
                if obj != character and obj.is_typeclass("typeclasses.characters.Character", exact=False)
            ]
            if others:
                return [f"Invite {others[0]} with party invite", "Read the family post sign"]
            return ["Talk to Courier Peep", "Read the family post sign"]
        if room_id == "tutorial_sparring_ring":
            return ["Talk to Ringhand Brask"]
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Head west to the Sparring Ring"]

    if step == "clear_the_pens":
        hints = ["Use fight to engage the pens", "Use enemies, attack, and your class skill"]
        if room_id == "tutorial_sparring_ring":
            return ["Head south into the Vermin Pens"]
        if room_id == TUTORIAL_VERMIN_ROOM_ID:
            return hints

    if step == "through_the_gate":
        if room_id == TUTORIAL_TRAINING_ROOM_ID:
            return ["Talk to Captain Harl"]
        return ["Head south to the Training Yard", "Report to Captain Harl"]

    return []


def get_beginner_focus(character, room):
    """Return beginner-band scene-card focus prompts after the tutorial."""

    if is_tutorial_active(character) or not room:
        return []

    room_id = getattr(room.db, "brave_room_id", None)

    if _is_active_quest(character, "practice_makes_heroes"):
        if room_id == TUTORIAL_TRAINING_ROOM_ID:
            return ["Talk to Captain Harl", "Check sheet and gear before you head out"]
        if room_id == "brambleford_town_green":
            return ["Head north to the Training Yard", "Read the town notice board"]

    if _is_active_quest(character, "rats_in_the_kettle"):
        if room_id == TUTORIAL_TRAINING_ROOM_ID:
            return ["Head south to Town Green", "Go west to the inn and talk to Uncle Pib"]
        if room_id == "brambleford_town_green":
            return ["Read the town notice board", "Head west to the inn"]
        if room_id == "brambleford_lantern_rest_inn":
            return ["Talk to Uncle Pib", "Go down to the cellar"]
        if room_id == "brambleford_rat_and_kettle_cellar":
            return ["Use fight to engage the rats", "Clear the cellar before heading back up"]

    if _is_active_quest(character, "roadside_howls"):
        if room_id == "brambleford_town_green":
            return ["Head east to East Gate", "Talk to Mira"]
        if room_id == "brambleford_east_gate":
            return ["Talk to Mira", "Head east onto Goblin Road"]
        if room_id == "goblin_road_trailhead":
            return ["Push east to Old Fence Line", "Stay together if family is with you"]
        if room_id == "goblin_road_old_fence_line":
            return ["Push east to Wolf Turn", "Use map if you lose the road"]

    if _is_active_quest(character, "fencebreakers"):
        if room_id in {"goblin_road_trailhead", "goblin_road_old_fence_line", "goblin_road_wolf_turn"}:
            return ["Fight goblin raiders on Goblin Road", "Check pack for road scrap afterward"]

    if _is_active_quest(character, "ruk_the_fence_cutter"):
        if room_id == "goblin_road_wolf_turn":
            return ["Push east to Fencebreaker Camp", "Bring the party if you have one"]
        if room_id == "goblin_road_fencebreaker_camp":
            return ["Use fight to confront Ruk", "Stay grouped when the camp erupts"]

    return []


def get_tutorial_entity_response(character, entity, action):
    """Return tutorial-specific interaction text when appropriate."""

    entity_id = getattr(entity.db, "brave_entity_id", None)
    if action == "talk":
        if entity_id == "sergeant_tamsin_vale":
            return _talk_tamsin(character)
        if entity_id == "quartermaster_nella_cobb":
            return _talk_nella(character)
        if entity_id == "courier_peep_marrow":
            return _talk_peep(character)
        if entity_id == "ringhand_brask":
            return _talk_brask(character)
        if entity_id == "captain_harl_rowan" and is_tutorial_active(character):
            return _talk_harl(character)
        return None

    if action == "read":
        if entity_id == "tutorial_supply_board":
            _set_flag(character, "read_supply_board")
            return (
                "The board is all neat frontier block letters: CHECK YOUR GEAR. KNOW YOUR PACK. DO NOT STEP INTO THE PENS "
                "WITHOUT LISTENING TO BRASK FIRST. Someone has added a smaller note beneath it: IF YOU GET LOST, GO BACK TO TAMSIN."
            )
        if entity_id == "family_post_sign":
            _set_flag(character, "read_family_post_sign")
            return (
                "The sign reads: TRAVELING WITH FAMILY? FORM A PARTY BEFORE YOU DRIFT APART. "
                "Use `party invite <name>` to start one, `party accept <leader>` to join, and `party where` if anyone wanders."
            )
        return None

    return None


def _talk_tamsin(character):
    state = ensure_tutorial_state(character)
    flags = state["flags"]
    step = state.get("step")

    if not flags.get("talked_tamsin"):
        _set_flag(character, "talked_tamsin")
        return (
            "Easy now. You're in Brambleford, not the ditch outside it. First thing: get your bearings. "
            "Head east to the shed, have a look around, then come back and report."
        )

    if step == "first_steps" and not flags.get("visited_quartermaster_shed"):
        return "East to the shed. Quick look, then back here. If you can manage that, we can teach the rest."

    if step == "first_steps":
        return "There you are. Good. Nella will sort your kit out next. Head east and listen to the quartermaster properly this time."

    if step == "pack_before_walk":
        return "Nella's the one with the kit sense. Get your gear straight before Brask decides to test it for you."

    if step == "stand_your_ground":
        return "You know where your gear is now. Good. Brask is waiting in the ring to the west."

    if step == "clear_the_pens":
        return (
            "The pens are live enough to sting and small enough not to kill your confidence. Start the fight when you're ready, "
            "finish it clean, then head south to Harl."
        )

    return "That's enough hand-holding. South takes you to Captain Harl and the rest of town. If you're curious about party travel, Peep is posted north."


def _talk_nella(character):
    state = ensure_tutorial_state(character)
    flags = state["flags"]
    _set_flag(character, "talked_nella")

    remaining = _remaining_pack_tasks(flags)
    if not flags.get("viewed_gear"):
        return (
            "Before you go wandering, know what you're wearing. Use `gear` and look over your kit. "
            "After that, open your pack."
        )
    if not flags.get("viewed_pack"):
        return "Good. Now use `pack` and see what you're carrying before the road teaches you the hard way."
    if not flags.get("read_supply_board"):
        return "One last thing. Read the supply board before you leave the shed."
    if remaining:
        return "You're nearly done here. Finish the last bit of kit-checking before you go chasing instructions elsewhere."
    return "That will do. Brask is west in the ring, and he likes people better when they know where their own straps and knives are."


def _talk_peep(character):
    _set_flag(character, "talked_peep")
    others = [
        obj.key
        for obj in (character.location.contents if character.location else [])
        if obj != character and obj.is_typeclass("typeclasses.characters.Character", exact=False)
    ]
    if others:
        names = ", ".join(others)
        return (
            f"You're not alone out here. If you mean to travel with {names}, form a party first. "
            "Use `party invite <name>` to start, `party accept <leader>` to join, and `party where` if anyone slips off."
        )
    return (
        "If family turns up later, don't just shout and hope. Use `party invite <name>` to group, `party follow <name>` to stay together, "
        "and `party where` when the road makes a liar out of your memory."
    )


def _talk_brask(character):
    _set_flag(character, "talked_brask")
    ability_name = CLASS_ABILITY_HINTS.get(character.db.brave_class, CLASSES[character.db.brave_class]["progression"][0][1])
    ability_token = ability_name.lower().replace(" ", " ")
    return (
        "Don't mash at shadows. In the pens to the south, start the fight with `fight`, check the field with `enemies`, "
        "then pick a target and `attack e1`. If you want cleaner work, try `use "
        f"{ability_token} = e1` once the vermin is in front of you."
    )


def _talk_harl(character):
    state = ensure_tutorial_state(character)
    step = state.get("step")
    if step != "through_the_gate":
        return (
            "You're not done with the north yard yet. Tamsin and Brask are there to keep the first mistakes cheap. "
            "Finish with them, then come back."
        )

    _set_flag(character, "talked_harl")
    complete_tutorial(character)
    return (
        "Tamsin sent you through in one piece, which puts you ahead of plenty. Welcome to Brambleford proper. "
        "Head south to the green, then west to the inn. Uncle Pib has the first real job worth your boots, and it stays close enough to town that a bad mistake won't become a legendary one."
    )
