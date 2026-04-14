"""Tutorial state and guided onboarding helpers for Brave."""

from world.bootstrap import get_room
from world.content import get_content_registry

CONTENT = get_content_registry()
CLASSES = CONTENT.characters.classes


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

TUTORIAL_QUEST_KEY = "tutorial_brambleford_basics"
TUTORIAL_QUEST_GIVER = "Sergeant Tamsin Vale"
TUTORIAL_QUEST_REGION = "Tutorial"

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
        "summary": "Let Nella square your kit away before you report to Brask at the ring.",
    },
    "stand_your_ground": {
        "title": "Stand Your Ground",
        "summary": "Speak with Ringhand Brask, then win one clean fight in the vermin pens.",
    },
    "through_the_gate": {
        "title": "Through The Gate",
        "summary": "Head south to the Training Yard and report to Captain Harl Rowan.",
    },
}

TUTORIAL_STEP_OBJECTIVES = {
    "first_steps": (
        ("talked_tamsin", "Speak with Sergeant Tamsin Vale."),
        ("visited_quartermaster_shed", "Head east to Quartermaster Shed."),
        ("returned_to_wayfarers_yard", "Return to Wayfarer's Yard."),
    ),
    "pack_before_walk": (
        ("talked_nella", "Speak with Quartermaster Nella Cobb."),
    ),
    "stand_your_ground": (
        ("talked_brask", "Speak with Ringhand Brask in the Sparring Ring."),
        ("won_vermin_fight", "Win one fight in the Vermin Pens."),
    ),
    "through_the_gate": (
        ("talked_harl", "Report to Captain Harl Rowan in the Training Yard."),
    ),
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
    if not flags.get("talked_nella"):
        return "pack_before_walk"
    if not flags.get("talked_brask") or not flags.get("won_vermin_fight"):
        return "stand_your_ground"
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


def _is_completed_quest(character, quest_key):
    return (character.db.brave_quests or {}).get(quest_key, {}).get("status") == "completed"


def _quest_objective_done(character, quest_key, index):
    objectives = (character.db.brave_quests or {}).get(quest_key, {}).get("objectives", [])
    if index < 0 or index >= len(objectives):
        return False
    return bool(objectives[index].get("completed"))


def _tutorial_objectives_for_state(state):
    step_key = state.get("step") or "first_steps"
    flags = state.get("flags", {})
    objectives = []
    for flag, description in TUTORIAL_STEP_OBJECTIVES.get(step_key, ()):
        completed = bool(flags.get(flag))
        objectives.append(
            {
                "description": description,
                "completed": completed,
                "progress": 1 if completed else 0,
                "required": 1,
                "flag": flag,
            }
        )
    return objectives


def get_tutorial_objectives(character):
    """Return quest-style objective state for the active tutorial step."""

    state = ensure_tutorial_state(character)
    if state.get("status") != "active":
        return []
    return _tutorial_objectives_for_state(state)


def get_tutorial_quest_payload(character):
    """Return compact quest data for tutorial-driven onboarding UI."""

    state = ensure_tutorial_state(character)
    if state.get("status") != "active":
        return None

    step_key = state.get("step") or "first_steps"
    step = TUTORIAL_STEPS[step_key]
    objectives = _tutorial_objectives_for_state(state)
    required_objectives = [objective for objective in objectives if not objective.get("optional")]
    remaining_required = [
        objective for objective in required_objectives if not objective.get("completed")
    ]
    remaining_optional = [
        objective
        for objective in objectives
        if objective.get("optional") and not objective.get("completed")
    ]
    visible_objectives = []
    for objective in objectives:
        visible_objectives.append(objective)
        if not objective.get("completed"):
            break
    completed_required = len(required_objectives) - len(remaining_required)
    total_required = max(1, len(required_objectives))

    return {
        "key": TUTORIAL_QUEST_KEY,
        "source": "tutorial",
        "title": step["title"],
        "giver": TUTORIAL_QUEST_GIVER,
        "region": TUTORIAL_QUEST_REGION,
        "summary": step["summary"],
        "objectives": [
            {"text": objective["description"], "completed": bool(objective.get("completed"))}
            for objective in visible_objectives
        ],
        "objective_details": objectives,
        "progress_label": f"{completed_required}/{total_required} steps",
        "step": step_key,
        "icon": "school",
    }


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
    elif step_key == "stand_your_ground":
        lines.append(
            f"  [{'x' if flags.get('talked_brask') else ' '}] Speak with Ringhand Brask in the Sparring Ring."
        )
        lines.append(
            f"  [{'x' if flags.get('won_vermin_fight') else ' '}] Win one fight in the Vermin Pens."
        )
    elif step_key == "through_the_gate":
        lines.append(
            f"  [{'x' if flags.get('talked_harl') else ' '}] Report to Captain Harl Rowan in the Training Yard."
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
            if flags.get("talked_brask"):
                return ["Head south into the Vermin Pens"]
            return ["Talk to Ringhand Brask"]
        if room_id == TUTORIAL_VERMIN_ROOM_ID:
            return ["Use fight to engage the pens", "Use enemies, attack, and your class skill"]
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Head west to the Sparring Ring"]

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
            if not _quest_objective_done(character, "practice_makes_heroes", 0):
                return ["Talk to Captain Harl", "Get the town handoff"]
            return ["Head south to Town Green", "Then west to the Lantern Rest Inn"]
        if room_id == "brambleford_town_green":
            return ["Head west to the Lantern Rest Inn", "Talk to Uncle Pib"]
        if room_id == "brambleford_lantern_rest_inn":
            if _quest_objective_done(character, "practice_makes_heroes", 6):
                return ["Talk to Uncle Pib", "Collect the cellar reward"]
            if _quest_objective_done(character, "practice_makes_heroes", 3):
                return ["Go down to the cellar", "Clear the rats"]
            return ["Talk to Uncle Pib", "Take the cellar job"]
        if room_id == "brambleford_rat_and_kettle_cellar":
            if _quest_objective_done(character, "practice_makes_heroes", 5):
                return ["Go up to Uncle Pib", "Collect the cellar reward"]
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
        character.db.brave_welcome_shown = True
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
        return (
            "The pens are live enough to sting and small enough not to kill your confidence. Start the fight when you're ready, "
            "finish it clean, then head south to Harl."
        )

    return "That's enough hand-holding. South takes you to Captain Harl and the rest of town. If you're curious about party travel, Peep is posted north."


def _talk_nella(character):
    _set_flag(character, "talked_nella")
    return (
        "That will do. Your kit is squared away enough for Brask. You can still use `gear`, `pack`, or read the supply board "
        "if you want the details, but the ring waits west."
    )


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
