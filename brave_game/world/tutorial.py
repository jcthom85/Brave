"""Tutorial state and guided onboarding helpers for Brave."""

from world.bootstrap import get_room
from world.content import get_content_registry
from world.questing import _refresh_tracked_quest_scene, _is_active_quest, _is_completed_quest

CONTENT = get_content_registry()
CLASSES = CONTENT.characters.classes


TUTORIAL_START_ROOM_ID = "tutorial_wayfarers_yard"
TUTORIAL_GATE_ROOM_ID = "tutorial_gate_walk"
TUTORIAL_TRAINING_ROOM_ID = "brambleford_training_yard"
TUTORIAL_HOME_ROOM_ID = "brambleford_town_green"
TUTORIAL_VERMIN_ROOM_ID = "tutorial_vermin_pens"
TUTORIAL_REWARD_ITEM_ID = "wayfarer_clasp"

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
    "used_class_ability",
    "won_vermin_fight",
    "received_wayfarer_clasp",
    "equipped_wayfarer_clasp",
    "rested_after_fight",
    "visited_family_post",
    "talked_peep",
    "read_family_post_sign",
    "viewed_map",
    "viewed_sheet",
    "viewed_journal",
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

LANTERNFALL_WELCOME_PAGES = [
    {
        "title": "A New Hero Arrives!",
        "text": "Brambleford is a town of warmth and light, but today the shadows are growing long. You are here because the town needs heart, muscle, and a hero. Your journey starts now—let's get you moving!",
        "icon": "auto_awesome",
    },
    {
        "title": "Lanternfall",
        "text": "The bell hits before dawn. A south road lantern has gone black, and the cart dragged through Brambleford's gate carries cut harness, clawed mud, and fence splinters. Sergeant Tamsin says you can stand, so now the yard finds out whether you can help.",
        "icon": "bell",
    },
    {
        "title": "No Time To Drift",
        "text": "Brambleford is warm behind you and wide awake around you. Sergeant Tamsin has one hand on the yard gate and one job for you: get your bearings before panic gets a vote.",
        "icon": "explore",
    },
]

LANTERNFALL_RECAP_PAGES = [
    {
        "title": "A New Hero Arrives!",
        "text": "Brambleford is a town of warmth and light, but today the shadows are growing long. You are here because the town needs heart, muscle, and a hero. Your journey starts now—let's get you moving!",
        "icon": "auto_awesome",
    },
    {
        "title": "Lanternfall",
        "text": "The bell hits before dawn. A south road lantern has gone black, and the cart dragged through Brambleford's gate carries cut harness, clawed mud, and fence splinters. Captain Harl Rowan is already watching the gate. Tamsin says you can stand, so now we find out whether you can help.",
        "icon": "bell",
    },
    {
        "title": "Report In",
        "text": "You know the basics, so Captain Harl is skipping the yard lesson. Talk to him now: the cellar is first, the road comes next, and the dead lantern is still the question.",
        "icon": "flag",
    },
]

LANTERNFALL_TERMINAL_INTRO = (
    "|wLanternfall|n\n\n"
    "The bell hits before dawn. Somewhere south of town, a road lantern has gone black, "
    "and the cart that just limped through the gate is packed with splintered fence rails and clawed mud.\n\n"
    "Sergeant Tamsin Vale has one hand on the yard gate and one job for you: get your bearings before panic gets a vote. "
    "Use |wtalk tamsin|n to begin."
)

LANTERNFALL_RECAP_TERMINAL_INTRO = (
    "|wLanternfall|n\n\n"
    "The bell hits before dawn. Somewhere south of town, a road lantern has gone black, "
    "and a damaged cart has come through Brambleford's gate with cut harness, clawed mud, and fence splinters.\n\n"
    "Captain Harl Rowan is already watching the yard. Use |wtalk harl|n to report in."
)

TUTORIAL_STEPS = {
    "first_steps": {
        "order": 1,
        "title": "Lanternfall",
        "summary": "The south road bell is ringing. Talk to Sergeant Tamsin, then head east so Nella can check your kit.",
        "how_to": "Click Sergeant Tamsin Vale's card in the Vicinity panel to receive your orders.",
    },
    "pack_before_walk": {
        "order": 2,
        "title": "Kit Before The Gate",
        "summary": "Nella is issuing field checks. Check your gear, open your pack, read the supply board, then return west to the yard.",
        "how_to": "Click the MENU button to check your Gear and Pack",
    },
    "stand_your_ground": {
        "order": 3,
        "title": "Stand Your Ground",
        "summary": "The pens are rattling. Speak with Ringhand Brask before you test yourself in a controlled fight.",
        "how_to": "Talk to NPCs by clicking their cards. Check the Map icon in the toolbar to see the yard layout.",
    },
    "clear_the_pens": {
        "order": 4,
        "title": "Clear The Pens",
        "summary": "Start a fight in the vermin pens, read the enemy line, use your class skill, and win cleanly.",
        "how_to": "Click the Fight button to engage. In combat, use your class skill to satisfy Brask's test.",
    },
    "fit_your_clasp": {
        "order": 5,
        "title": "Fit Your Clasp",
        "summary": "You recovered a Wayfarer Clasp. Equip it, notice what changed, then check your bearings before you report.",
        "how_to": "Open Gear, click your Clasp, and choose Equip. Check your Sheet to see your improved stats.",
    },
    "catch_your_breath": {
        "order": 6,
        "title": "Catch Your Breath",
        "summary": "Return to Wayfarer's Yard and rest. Brave hands recover before they report.",
        "how_to": "Click the Rest button in the Vicinity panel to recover your health and resources.",
    },
    "through_the_gate": {
        "order": 7,
        "title": "Through The Gate",
        "summary": "Head south to the Training Yard and report to Captain Harl Rowan. The town has its first real job ready.",
        "how_to": "Use the navigation compass or cardinal buttons to move South to the Training Yard.",
    },
}


def get_lanternfall_intro_text():
    """Return the text intro for non-browser first-time onboarding."""

    return LANTERNFALL_TERMINAL_INTRO


def get_lanternfall_recap_text():
    """Return the text intro for tutorial-skipped new-character onboarding."""

    return LANTERNFALL_RECAP_TERMINAL_INTRO


def should_show_lanternfall_recap(character):
    """Whether a tutorial-skipped character should see the opening recap."""

    if not character or is_tutorial_active(character):
        return False
    if getattr(character.db, "brave_lanternfall_intro_shown", False):
        return False
    room = getattr(character, "location", None)
    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    return room_id == TUTORIAL_TRAINING_ROOM_ID and _is_active_quest(character, "practice_makes_heroes")


def _default_flags():
    return {flag: False for flag in TUTORIAL_FLAGS}


def _get_normalized_tutorial_state(character):
    """Internal helper to get state WITHOUT saving, to avoid recursion."""
    raw = getattr(getattr(character, "db", None), "brave_tutorial", None) or {}
    state = dict(raw)
    flags = dict(state.get("flags") or {})
    for flag in TUTORIAL_FLAGS:
        flags.setdefault(flag, False)

    status = state.get("status") or "inactive"
    step = state.get("step")

    if status == "active":
        step = _determine_step(flags)
        if step is None:
            status = "completed"

    return {"status": status, "step": step, "flags": flags}


def _save_state(character, state):
    character.db.brave_tutorial = state
    character.db.brave_tutorial_current_step = state.get("step")

    # Guard against recursion loops from UI refresh
    ndb = getattr(character, "ndb", None)
    if ndb is not None and not getattr(ndb, "brave_refreshing_tutorial_ui", False):
        ndb.brave_refreshing_tutorial_ui = True
        try:
            from world.browser_panels import send_objectives_refresh
            send_objectives_refresh(character)
        finally:
            ndb.brave_refreshing_tutorial_ui = False

    return state


def should_start_tutorial(account):
    """Whether a newly created character should start in the tutorial."""

    return True


def ensure_tutorial_state(character):
    """Normalize and PERSIST tutorial state for this character."""

    state = _get_normalized_tutorial_state(character)
    
    # Special case: if _get_normalized_tutorial_state upgraded us to completed
    existing = getattr(getattr(character, "db", None), "brave_tutorial", None) or {}
    if state["status"] == "completed" and existing.get("status") != "completed":
        return complete_tutorial(character)

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


def get_tutorial_exit_block(character, destination):
    """Return a message if an active tutorial character cannot leave the newbie area."""

    if not character or not destination or not is_tutorial_active(character):
        return None

    source = getattr(character, "location", None)
    source_id = getattr(getattr(source, "db", None), "brave_room_id", None)
    destination_id = getattr(getattr(destination, "db", None), "brave_room_id", None)
    if source_id not in TUTORIAL_ROOM_IDS or destination_id in TUTORIAL_ROOM_IDS:
        return None

    state = ensure_tutorial_state(character)
    if state.get("step") == "through_the_gate":
        return None
    return f"Tamsin stops you at the gate. {get_tutorial_blocker_hint(state)}"


def get_tutorial_blocker_hint(state):
    """Return the current contextual reason the tutorial gate is still locked."""

    step = (state or {}).get("step") or "first_steps"
    flags = (state or {}).get("flags") or {}

    if step == "first_steps":
        if not flags.get("talked_tamsin"):
            return "Talk to Sergeant Tamsin first; she is holding the yard together."
        return "Head east to the Quartermaster Shed so Nella can check your kit."
    if step == "pack_before_walk":
        if not flags.get("talked_nella"):
            return "Let Quartermaster Nella check your kit in the shed."
        if not flags.get("viewed_gear"):
            return "Open your gear and see what you are wearing."
        if not flags.get("viewed_pack"):
            return "Open your pack and see what you are carrying."
        if not flags.get("read_supply_board"):
            return "Read the supply board before you leave the yard."
        return "Return west to Wayfarer's Yard before Brask tests you."
    if step == "stand_your_ground":
        return "Head west to the Sparring Ring and speak with Ringhand Brask."
    if step == "clear_the_pens":
        if not flags.get("used_class_ability"):
            return "Use your class ability in the Vermin Pens so Brask knows you can do more than swing wildly."
        return "Win one controlled fight in the Vermin Pens."
    if step == "fit_your_clasp":
        return "Equip the Wayfarer Clasp you earned before you report in."
    if step == "catch_your_breath":
        return "Rest in Wayfarer's Yard before you report to Captain Harl."
    return "Finish the yard lesson before you report to Captain Harl."


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
    if not flags.get("visited_quartermaster_shed"):
        return "first_steps"
    if not (
        flags.get("talked_nella")
        and flags.get("viewed_gear")
        and flags.get("viewed_pack")
        and flags.get("read_supply_board")
        and flags.get("returned_to_wayfarers_yard")
    ):
        return "pack_before_walk"
    if not flags.get("talked_brask"):
        return "stand_your_ground"
    if not flags.get("used_class_ability") or not flags.get("won_vermin_fight"):
        return "clear_the_pens"
    if not flags.get("equipped_wayfarer_clasp"):
        return "fit_your_clasp"
    if not flags.get("rested_after_fight"):
        return "catch_your_breath"
    if not flags.get("talked_harl"):
        return "through_the_gate"
    return None


def _set_flag(character, flag):
    state = _get_normalized_tutorial_state(character)
    existing = getattr(getattr(character, "db", None), "brave_tutorial", None) or {}
    if state.get("status") == "completed" and existing.get("status") != "completed":
        return complete_tutorial(character)
    if state.get("status") != "active":
        return state

    old_step = state.get("step")

    if flag in state["flags"]:
        state["flags"][flag] = True

    new_step = _determine_step(state["flags"])
    state["step"] = new_step

    if old_step and new_step != old_step:
        # Step completed! Trigger a cinematic popup
        step_title = TUTORIAL_STEPS.get(old_step, {}).get("title", "Tutorial Task")
        from world.browser_panels import send_quest_complete_event
        # Give a small XP reward for tutorial steps too
        send_quest_complete_event(character, step_title, rewards={"xp": 10})

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
    if room_id == "tutorial_family_post":
        return _set_flag(character, "visited_family_post")
    if (
        room_id == "tutorial_wayfarers_yard"
        and state["flags"].get("talked_tamsin")
        and state["flags"].get("visited_quartermaster_shed")
    ):
        return _set_flag(character, "returned_to_wayfarers_yard")
    return state


def record_command_event(character, event_key):
    """Advance tutorial state from command usage."""

    if event_key == "rest":
        state = ensure_tutorial_state(character)
        if not state["flags"].get("won_vermin_fight"):
            return state
        return _set_flag(character, "rested_after_fight")

    if event_key == "equip_gear":
        state = ensure_tutorial_state(character)
        if not state["flags"].get("received_wayfarer_clasp"):
            return state
        return _set_flag(character, "equipped_wayfarer_clasp")

    mapping = {
        "gear": "viewed_gear",
        "pack": "viewed_pack",
        "class_ability": "used_class_ability",
        "map": "viewed_map",
        "sheet": "viewed_sheet",
        "quests": "viewed_journal",
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
    state = _set_flag(character, "won_vermin_fight")
    flags = state.get("flags") or {}
    if not flags.get("received_wayfarer_clasp"):
        if hasattr(character, "add_item_to_inventory"):
            character.add_item_to_inventory(TUTORIAL_REWARD_ITEM_ID, 1)
        state = _set_flag(character, "received_wayfarer_clasp")
        if hasattr(character, "msg"):
            character.msg("|cTraining reward:|n You recover a |wWayfarer Clasp|n. Equip it with |wgear equip trinket clasp|n.")
    return state


def is_tutorial_solo_combat_room(room):
    """Return whether this room should force one-player tutorial combat."""

    room_id = getattr(getattr(room, "db", None), "brave_room_id", None)
    return room_id == TUTORIAL_VERMIN_ROOM_ID


def get_tutorial_combat_focus(character, encounter):
    """Return combat UI tutorial prompts for the active newbie fight."""

    if not getattr(getattr(character, "db", None), "brave_tutorial", None):
        return []
    state = _get_normalized_tutorial_state(character)
    if state.get("status") != "active" or not encounter:
        return []
    room_id = getattr(getattr(getattr(encounter, "obj", None), "db", None), "brave_room_id", None)
    if room_id != TUTORIAL_VERMIN_ROOM_ID:
        return []

    flags = state["flags"]
    prompts = []
    if not flags.get("used_class_ability"):
        ability_name = CLASS_ABILITY_HINTS.get(character.db.brave_class, "your class skill")
        prompts.append(
            {
                "title": f"Use {ability_name}",
                "text": f"Open Abilities or type use {ability_name.lower()} = e1.",
                "icon": "bolt",
            }
        )
    prompts.append(
        {
            "title": "Watch HP And Status",
            "text": "HP bars show who is close to falling. Status chips show marks, binds, poison, bleeding, or snares.",
            "icon": "monitor_heart",
        }
    )
    prompts.append(
        {
            "title": "Finish The Target",
            "text": "Select the enemy target when your action is ready.",
            "icon": "my_location",
        }
    )
    return prompts[:3]


def _is_in_tutorial_combat(character):
    """Return whether combat-specific tutorial guidance should own the overlay."""

    if not character:
        return False
    location = getattr(character, "location", None)
    if not is_tutorial_solo_combat_room(location):
        return False
    get_encounter = getattr(character, "get_active_encounter", None)
    if not callable(get_encounter):
        return False
    encounter = get_encounter()
    if not encounter:
        return False
    is_participant = getattr(encounter, "is_participant", None)
    if callable(is_participant):
        return bool(is_participant(character))
    participants = getattr(encounter, "get_active_participants", None)
    if callable(participants):
        return character in (participants() or [])
    return True


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
    return (getattr(character.db, "brave_quests", None) or {}).get(quest_key, {}).get("status") == "active"


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
            f"  [{'x' if flags.get('talked_tamsin') else ' '}] Consult with Sergeant Tamsin Vale."
        )
        lines.append(
            f"  [{'x' if flags.get('visited_quartermaster_shed') else ' '}] Head east to Quartermaster Nella."
        )
    elif step_key == "pack_before_walk":
        lines.append(
            f"  [{'x' if flags.get('talked_nella') else ' '}] Let Quartermaster Nella square your kit away."
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
        lines.append(
            f"  [{'x' if flags.get('returned_to_wayfarers_yard') else ' '}] Return west to Wayfarer's Yard."
        )
    elif step_key == "stand_your_ground":
        lines.append(
            f"  [{'x' if flags.get('talked_brask') else ' '}] Speak with Ringhand Brask in the Sparring Ring."
        )
    elif step_key == "clear_the_pens":
        lines.append(
            f"  [{'x' if flags.get('used_class_ability') else ' '}] Use your class skill in combat."
        )
        lines.append(
            f"  [{'x' if flags.get('won_vermin_fight') else ' '}] Win one fight in the Vermin Pens."
        )
    elif step_key == "fit_your_clasp":
        lines.append(
            f"  [{'x' if flags.get('received_wayfarer_clasp') else ' '}] Recover the Wayfarer Clasp."
        )
        lines.append(
            f"  [{'x' if flags.get('equipped_wayfarer_clasp') else ' '}] Equip the clasp with gear equip trinket clasp."
        )
        lines.append(
            f"  [{'x' if flags.get('viewed_sheet') else ' '}] Optional: Open your sheet or stats."
        )
        lines.append(
            f"  [{'x' if flags.get('viewed_map') else ' '}] Optional: Check the map."
        )
        lines.append(
            f"  [{'x' if flags.get('viewed_journal') else ' '}] Optional: Open your journal."
        )
    elif step_key == "catch_your_breath":
        lines.append(
            f"  [{'x' if flags.get('rested_after_fight') else ' '}] Rest in Wayfarer's Yard."
        )
    elif step_key == "through_the_gate":
        lines.append(
            f"  [{'x' if flags.get('talked_harl') else ' '}] Report to Captain Harl Rowan in the Training Yard."
        )

    optional_done = flags.get("read_family_post_sign") or flags.get("talked_peep") or flags.get("visited_family_post")
    lines.append(
        f"  [{'x' if optional_done else ' '}] Optional: Visit Family Post to learn party basics."
    )
    return "\n".join(lines)


def get_tutorial_objective_entries(character):
    """Return current tutorial objectives for existing quest/journal UI surfaces."""

    state = _get_normalized_tutorial_state(character)
    if state.get("status") != "active":
        return None

    step_key = state.get("step") or "first_steps"
    step = TUTORIAL_STEPS[step_key]
    flags = state["flags"]
    objectives = []

    def add(text, flag=None, completed=False):
        objectives.append({"text": text, "completed": bool(completed or (flag and flags.get(flag)))})

    if step_key == "first_steps":
        add("Consult with Sergeant Tamsin Vale.", "talked_tamsin")
        add("Head east to Quartermaster Nella.", "visited_quartermaster_shed")
    elif step_key == "pack_before_walk":
        add("Let Quartermaster Nella check your kit.", "talked_nella")
        add("Check your gear.", "viewed_gear")
        add("Open your pack.", "viewed_pack")
        add("Read the supply board.", "read_supply_board")
        add("Return west to Wayfarer's Yard.", "returned_to_wayfarers_yard")
    elif step_key == "stand_your_ground":
        add("Speak with Ringhand Brask in the Sparring Ring.", "talked_brask")
    elif step_key == "clear_the_pens":
        add("Use your class skill in combat.", "used_class_ability")
        add("Win one fight in the Vermin Pens.", "won_vermin_fight")
    elif step_key == "fit_your_clasp":
        add("Recover the Wayfarer Clasp.", "received_wayfarer_clasp")
        add("Equip the clasp with gear equip trinket clasp.", "equipped_wayfarer_clasp")
        add("Optional: Open your sheet or stats.", "viewed_sheet")
        add("Optional: Check the map.", "viewed_map")
        add("Optional: Open your journal.", "viewed_journal")
    elif step_key == "catch_your_breath":
        add("Rest in Wayfarer's Yard.", "rested_after_fight")
    elif step_key == "through_the_gate":
        add("Report to Captain Harl Rowan in the Training Yard.", "talked_harl")

    optional_done = flags.get("read_family_post_sign") or flags.get("talked_peep") or flags.get("visited_family_post")
    add("Optional: Visit Family Post for party basics.", completed=optional_done)
    return {
        "title": step["title"],
        "summary": step["summary"],
        "objectives": objectives,
    }


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
            return ["Talk to Sergeant Tamsin", "Find out why the bell is ringing"]
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Head east to Quartermaster Shed", "Nella is checking road kits"]
        if room_id == "tutorial_quartermaster_shed":
            return ["Talk to Quartermaster Nella"]

    if step == "pack_before_walk":
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Head east to Quartermaster Shed", "Finish Nella's kit check"]
        if room_id == "tutorial_quartermaster_shed":
            return _remaining_pack_tasks(flags) or ["Return west to Wayfarer's Yard"]

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
            return ["Head west to the Sparring Ring", "The pens are rattling"]

    if step == "clear_the_pens":
        hints = ["Use enemies to read the fight", "Select the enemy target", "Use your class skill on e1"]
        if room_id == "tutorial_sparring_ring":
            return ["Head south into the Vermin Pens"]
        if room_id == TUTORIAL_VERMIN_ROOM_ID:
            return hints

    if step == "catch_your_breath":
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Use rest before reporting in", "Head south after you recover"]
        if room_id == TUTORIAL_VERMIN_ROOM_ID:
            return ["Head north to the Sparring Ring", "Return east to Wayfarer's Yard"]
        if room_id == "tutorial_sparring_ring":
            return ["Head east to Wayfarer's Yard", "Use rest there"]

    if step == "fit_your_clasp":
        if room_id == TUTORIAL_VERMIN_ROOM_ID:
            return ["Use gear equip trinket clasp", "Then head north"]
        if room_id == "tutorial_sparring_ring":
            return ["Use gear equip trinket clasp", "Head east to rest"]
        if room_id == TUTORIAL_START_ROOM_ID:
            return ["Use gear equip trinket clasp", "Optional: map, sheet, quests"]

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


def get_tutorial_entity_response(character, entity, action, is_action=False):
    """Return tutorial-specific interaction text when appropriate."""

    entity_id = getattr(entity.db, "brave_entity_id", None)
    if action == "talk":
        if entity_id == "sergeant_tamsin_vale":
            return _talk_tamsin(character, is_action=is_action)
        if entity_id == "quartermaster_nella_cobb":
            return _talk_nella(character, is_action=is_action)
        if entity_id == "courier_peep_marrow":
            return _talk_peep(character, is_action=is_action)
        if entity_id == "ringhand_brask":
            return _talk_brask(character, is_action=is_action)
        if entity_id == "captain_harl_rowan" and is_tutorial_active(character):
            return _talk_harl(character, is_action=is_action)
        return None

    if action == "read":
        if entity_id == "tutorial_supply_board":
            if is_action:
                _set_flag(character, "read_supply_board")
            return (
                "The board is all neat frontier block letters: SOUTH LANTERN OUT. ROAD CART DAMAGED. CHECK YOUR GEAR. "
                "KNOW YOUR PACK. DO NOT STEP INTO THE PENS WITHOUT LISTENING TO BRASK FIRST. "
                "Someone has added a smaller note beneath it: IF YOU GET LOST, GO BACK TO TAMSIN."
            )
        if entity_id == "tutorial_damaged_cart":
            if is_action:
                try:
                    from world.browser_panels import send_audio_cue_once

                    send_audio_cue_once(character, "sfx.story.cart_reveal", key="read_tutorial_damaged_cart", force=True)
                except Exception:
                    pass
            return (
                "The cart tells the story better than a speech: clawed mud on the wheel, split fence rail in the axle, "
                "and harness leather cut in two clean strokes. Whatever hit the south road had tools, not just teeth."
            )
        if entity_id == "family_post_sign":
            if is_action:
                _set_flag(character, "read_family_post_sign")
            return (
                "The sign reads: TRAVELING WITH FAMILY? FORM A PARTY BEFORE YOU DRIFT APART. "
                "Invite your family to join you, and check your map if anyone wanders."
            )
        return None

    return None


def _talk_tamsin(character, is_action=False):
    if is_action:
        _set_flag(character, "talked_tamsin")

    state = _get_normalized_tutorial_state(character)
    flags = state["flags"]
    step = state.get("step")

    if step == "first_steps" and not flags.get("visited_quartermaster_shed"):
        return (
            "\"Hear that bell? South road lantern went black before dawn, and the gate crew just dragged in a cart full of cut harness and clawed mud. "
            "You can help, but first I need you steady and equipped. Head east to Nella in the shed. She checks every road kit before anyone gets pointed at real trouble.\""
        )

    if step == "first_steps" and not flags.get("visited_quartermaster_shed"):
        return "\"East to the shed. Nella is already opening crates, and the road is not waiting for anyone to remember their own pockets.\""

    if step == "first_steps":
        return "\"Stay with Nella until your kit is squared away. Gear, pack, board, then back west to me.\""

    if step == "pack_before_walk":
        return "\"Finish Nella's kit check, then come back west. Brask can test your hands after we know your straps are tight.\""

    if step == "stand_your_ground":
        return "\"You know where your gear is now. Good. Brask is waiting west. The pens started rattling when the south bell did.\""

    if step == "clear_the_pens":
        return (
            "\"The pens are live enough to sting and small enough not to kill your confidence. Start the fight when you're ready, "
            "size up your enemies, use your class skill, finish it clean, then come back here and rest.\""
        )

    if step == "fit_your_clasp":
        return (
            "\"That clasp is small, but small kit still changes the numbers. Equip the clasp in your gear, then check your sheet, map, or objectives "
            "if you want your bearings before you rest.\""
        )

    if step == "catch_your_breath":
        return "\"Good work. Now learn the other half of surviving: recover before you swagger. Rest here in the yard, then south to Harl. He has the cellar first and the road after.\""

    return "\"That's enough hand-holding. South takes you to Captain Harl and the rest of town. That dead lantern is going to become someone's problem, and Harl prefers problems with names.\""


def _talk_nella(character, is_action=False):
    if is_action:
        _set_flag(character, "talked_nella")

    state = _get_normalized_tutorial_state(character)
    flags = state["flags"]

    remaining = _remaining_pack_tasks(flags)
    if not flags.get("viewed_gear"):
        return (
            "\"Before anyone points you at a damaged road, know what you're wearing. Check your gear and look over your kit. "
            "After that, open your pack.\""
        )
    if not flags.get("viewed_pack"):
        return "\"Good. Now open your pack and see what you're carrying before the road gets an opinion.\""
    if not flags.get("read_supply_board"):
        return "\"One last thing. Read the supply board. If a bell is ringing, the board usually knows why.\""
    if remaining:
        return "\"You're nearly done here. Finish the last bit of kit-checking before you go chasing instructions elsewhere.\""
    return "\"That will do. Back west to the yard. Tamsin will point you at Brask once she sees you can move with your kit sorted.\""


def _talk_peep(character, is_action=False):
    if is_action:
        _set_flag(character, "talked_peep")
    others = [
        obj.key
        for obj in (character.location.contents if character.location else [])
        if obj != character and obj.is_typeclass("typeclasses.characters.Character", exact=False)
    ]
    if others:
        names = ", ".join(others)
        return (
            f"\"You're not alone out here. If you mean to travel with {names}, form a party first. "
            "Invite them to group up, and check your map if anyone slips off.\""
        )
    return (
        "\"If family turns up later, don't just shout and hope. Invite them to your party to group up, stay together, "
        "and check your map when the road makes a liar out of your memory.\""
    )


def _talk_brask(character, is_action=False):
    if is_action:
        _set_flag(character, "talked_brask")

    state = _get_normalized_tutorial_state(character)
    ability_name = CLASS_ABILITY_HINTS.get(character.db.brave_class, CLASSES[character.db.brave_class]["progression"][0][1])
    return (
        "\"Road bell spooked the pens, so we make the first mistake here where the fence is short and I'm watching. "
        "Go south, start the controlled fight, and keep your eyes on the field. Before you leave, I need to see your own trick land: "
        f"{ability_name}. The fight itself will show you the target.\""
    )


def _talk_harl(character, is_action=False):
    state = _get_normalized_tutorial_state(character)
    step = state.get("step")
    if step != "through_the_gate":
        return (
            "\"You're not done with the north yard yet. Tamsin and Brask are there to keep the first mistakes cheap, and nobody reports in properly without catching their breath first. "
            "Finish with them, then come back.\""
        )

    if is_action:
        _set_flag(character, "talked_harl")
        complete_tutorial(character)

        from world.questing import advance_talk_to_npc, ensure_starter_quests, unlock_quest

        advance_talk_to_npc(character, "captain_harl_rowan")
        unlock_quest(character, "rats_in_the_kettle")
        ensure_starter_quests(character)

    return (
        "\"Tamsin sent you through with your head on straight. Good. The south lantern going dark is not your first job; surviving long enough to reach it is. "
        "Start close: head south to the green, then west to the inn. Uncle Pib's cellar is tearing itself apart, and the stores matter if the road stays cut. "
        "Clear that, then Mira will put a name to what hit the fences.\""
    )


def get_tutorial_mechanical_guidance(character):
    """Return mechanical 'how-to' guidance for the TUTORIAL overlay."""

    state = _get_normalized_tutorial_state(character)
    if state.get("status") != "active":
        return None
    if _is_in_tutorial_combat(character):
        return None

    step_key = state.get("step") or "first_steps"
    step = TUTORIAL_STEPS[step_key]
    flags = state["flags"]

    guidance = []

    # 1. Primary mechanical instruction for the current step
    guidance.append((f"GUIDE: {step['how_to']}", "help_outline"))

    # 2. Contextual tips based on missing knowledge
    if not flags.get("visited_family_post") and not flags.get("talked_peep"):
        guidance.append(("Traveling with family? Click Family Post west of the yard to learn about Parties.", "groups"))

    if step_key == "clear_the_pens":
        guidance.append(("Need an edge? Use the Emote button to express your character's resolve.", "sentiment_satisfied"))

    return {
        "title": step["title"],
        "eyebrow": "TUTORIAL",
        "guidance": guidance,
    }
