"""Helpers for Brave quest state and room-visit progression."""

from copy import deepcopy

from world.content import get_content_registry
from world.trophies import unlock_trophy

CONTENT = get_content_registry()
ITEM_CONTENT = CONTENT.items
QUEST_CONTENT = CONTENT.quests


def _build_initial_objective_state(objective):
    required = objective.get("count", 1)
    return {
        "description": objective["description"],
        "completed": False,
        "progress": 0,
        "required": required,
    }


def _prerequisites_met(quest_log, definition):
    return all(quest_log.get(quest_key, {}).get("status") == "completed" for quest_key in definition.get("prerequisites", []))


def _count_inventory_item(character, template_id):
    return sum(
        entry.get("quantity", 0)
        for entry in (character.db.brave_inventory or [])
        if entry.get("template") == template_id
    )


def _format_quest_reward_text(definition):
    rewards = definition.get("rewards", {})
    parts = []
    if rewards.get("xp"):
        parts.append(f"{rewards['xp']} XP")
    if rewards.get("silver"):
        parts.append(f"{rewards['silver']} silver")
    for item_reward in rewards.get("items", []):
        template_id = item_reward.get("item")
        if not template_id:
            continue
        item_name = ITEM_CONTENT.item_templates.get(template_id, {}).get("name", template_id)
        quantity = item_reward.get("quantity", 1)
        parts.append(item_name + (f" x{quantity}" if quantity > 1 else ""))
    return ", ".join(parts)


def _record_recent_updates(character, messages):
    """Store recent quest/progression messages for the next rich UI surface."""

    recent = list(getattr(character.ndb, "brave_recent_quest_updates", []) or [])
    recent.extend(message for message in (messages or []) if message)
    character.ndb.brave_recent_quest_updates = recent[-12:]


def _refresh_tracked_quest_scene(character):
    """Refresh the exploration tracked-quest card for active webclient sessions."""

    if not character:
        return

    try:
        from world.browser_panels import send_webclient_event
    except Exception:
        return

    tracked = get_tracked_quest_payload(character)
    send_webclient_event(character, brave_scene={"tracked_quest": tracked} if tracked else {})


def pop_recent_quest_updates(character):
    """Return and clear recent quest/progression messages."""

    recent = list(getattr(character.ndb, "brave_recent_quest_updates", []) or [])
    character.ndb.brave_recent_quest_updates = []
    return recent


def _build_initial_quest_state(quest_key, definition, quest_log):
    return {
        "status": "active" if _prerequisites_met(quest_log, definition) else "locked",
        "objectives": [
            _build_initial_objective_state(objective) for objective in definition["objectives"]
        ],
    }


def _normalize_quest_state(quest_key, quest_state):
    definition = QUEST_CONTENT.quests[quest_key]
    objectives = quest_state.get("objectives", [])
    changed = False

    if len(objectives) < len(definition["objectives"]):
        for objective in definition["objectives"][len(objectives) :]:
            objectives.append(_build_initial_objective_state(objective))
            changed = True
    elif len(objectives) > len(definition["objectives"]):
        del objectives[len(definition["objectives"]) :]
        changed = True

    for index, objective in enumerate(definition["objectives"]):
        objective_state = objectives[index]
        required = objective.get("count", 1)
        if "description" not in objective_state:
            objective_state["description"] = objective["description"]
            changed = True
        if "required" not in objective_state:
            objective_state["required"] = required
            changed = True
        if "progress" not in objective_state:
            objective_state["progress"] = required if objective_state.get("completed") else 0
            changed = True
        if objective_state.get("completed") and objective_state["progress"] < objective_state["required"]:
            objective_state["progress"] = objective_state["required"]
            changed = True
        if objective_state["progress"] >= objective_state["required"] and not objective_state.get("completed"):
            objective_state["completed"] = True
            changed = True

    quest_state["objectives"] = objectives
    if quest_state.get("status") not in {"active", "completed", "locked"}:
        quest_state["status"] = "completed" if all(objective["completed"] for objective in objectives) else "active"
        changed = True

    if quest_state.get("status") != "locked" and all(objective["completed"] for objective in objectives):
        if quest_state["status"] != "completed":
            quest_state["status"] = "completed"
            changed = True

    return changed


def _complete_quest(character, definition, state, messages):
    if state.get("status") == "completed":
        return False

    state["status"] = "completed"
    messages.append(f"|yQuest complete:|n {definition['title']}")
    rewards = definition.get("rewards", {})
    reward_xp = rewards.get("xp", 0)
    if reward_xp:
        level_messages = character.grant_xp(reward_xp)
        messages.append(f"You gain |w{reward_xp}|n XP.")
        messages.extend(level_messages)

    reward_silver = rewards.get("silver", 0)
    if reward_silver:
        character.db.brave_silver = (character.db.brave_silver or 0) + reward_silver
        messages.append(f"You receive |w{reward_silver}|n silver.")

    for item_reward in rewards.get("items", []):
        template_id = item_reward.get("item")
        quantity = item_reward.get("quantity", 1)
        if not template_id or quantity <= 0:
            continue
        character.add_item_to_inventory(template_id, quantity)
        item_name = ITEM_CONTENT.item_templates.get(template_id, {}).get("name", template_id)
        messages.append(f"You receive |w{item_name}|n" + (f" x{quantity}." if quantity > 1 else "."))

    for trophy_key in rewards.get("trophies", []):
        if unlock_trophy(trophy_key, awarded_to=character.key):
            messages.append(f"|cTrophy added to the hall:|n {definition['title']}")
    if definition.get("chapter_complete"):
        messages.append(f"|yChapter complete:|n {definition['chapter_complete']}")
        messages.append("|cTown reaction:|n Joss, Mayor Elric, and the Trophy Hall all have something new to say.")
    if definition.get("next_step"):
        messages.append(f"|cNext lead:|n {definition['next_step']}")
    return True


def _unlock_available_quests(quest_log, messages):
    changed = False
    for quest_key in QUEST_CONTENT.starting_quests:
        state = quest_log.get(quest_key)
        definition = QUEST_CONTENT.quests[quest_key]
        if not state or state.get("status") != "locked":
            continue
        if not _prerequisites_met(quest_log, definition):
            continue
        state["status"] = "active"
        changed = True
        messages.append(f"|cNew quest:|n {definition['title']}")
        if definition.get("next_step"):
            messages.append(f"|cLead:|n {definition['next_step']}")
    return changed


def _sync_tracked_quest(character, quest_log, messages):
    changed = False
    active_keys = [quest_key for quest_key in QUEST_CONTENT.starting_quests if quest_log.get(quest_key, {}).get("status") == "active"]
    tracked = getattr(character.db, "brave_tracked_quest", None)
    suppressed = bool(getattr(character.db, "brave_track_suppressed", False))

    if tracked in active_keys:
        return False

    if tracked and tracked not in active_keys:
        character.db.brave_tracked_quest = None
        changed = True

    if suppressed or not active_keys:
        return changed

    new_tracked = active_keys[0]
    if getattr(character.db, "brave_tracked_quest", None) != new_tracked:
        character.db.brave_tracked_quest = new_tracked
        changed = True
        messages.append(f"|mTracked quest:|n {QUEST_CONTENT.quests[new_tracked]['title']}")

    return changed


def _sync_collect_item_progress(character, quest_log, messages):
    changed = False
    for quest_key, state in quest_log.items():
        if state.get("status") != "active":
            continue

        definition = QUEST_CONTENT.quests.get(quest_key)
        if not definition:
            continue

        for index, objective in enumerate(definition["objectives"]):
            if objective.get("type") != "collect_item":
                continue

            objective_state = state["objectives"][index]
            required = objective_state.get("required", 1)
            progress = min(required, _count_inventory_item(character, objective["item_id"]))
            previous = objective_state.get("progress", 0)
            if progress != previous:
                objective_state["progress"] = progress
                changed = True
                messages.append(
                    f"|gQuest updated:|n {definition['title']} - {progress}/{required}"
                )
            if progress >= required and not objective_state.get("completed"):
                objective_state["completed"] = True
                changed = True
    return changed


def _complete_ready_quests(character, quest_log, messages):
    changed = False
    for quest_key, state in quest_log.items():
        if state.get("status") != "active":
            continue
        if not all(objective.get("completed") for objective in state.get("objectives", [])):
            continue
        definition = QUEST_CONTENT.quests.get(quest_key)
        if definition:
            changed = _complete_quest(character, definition, state, messages) or changed
    return changed


def _sync_quest_log(character, quest_log, messages):
    changed = False

    for quest_key in QUEST_CONTENT.starting_quests:
        definition = QUEST_CONTENT.quests[quest_key]
        if quest_key not in quest_log:
            quest_log[quest_key] = _build_initial_quest_state(quest_key, definition, quest_log)
            changed = True
        else:
            changed = _normalize_quest_state(quest_key, quest_log[quest_key]) or changed
            if (
                quest_log[quest_key].get("status") == "locked"
                and not definition.get("prerequisites")
            ):
                quest_log[quest_key]["status"] = "active"
                changed = True

    while True:
        progressed = False
        progressed = _unlock_available_quests(quest_log, messages) or progressed
        progressed = _sync_collect_item_progress(character, quest_log, messages) or progressed
        progressed = _complete_ready_quests(character, quest_log, messages) or progressed
        if not progressed:
            break
        changed = True

    changed = _sync_tracked_quest(character, quest_log, messages) or changed

    return changed


def ensure_starter_quests(character):
    """Populate starter quests on a character if missing."""

    quest_log = deepcopy(character.db.brave_quests or {})
    changed = _sync_quest_log(character, quest_log, [])

    if changed:
        character.db.brave_quests = quest_log

    return quest_log


def get_active_quests(character):
    """Return active quest keys in stable order."""

    quest_log = character.db.brave_quests or {}
    return [quest_key for quest_key in QUEST_CONTENT.starting_quests if quest_log.get(quest_key, {}).get("status") == "active"]


def get_completed_quests(character):
    """Return completed quest keys in stable order."""

    quest_log = character.db.brave_quests or {}
    return [quest_key for quest_key in QUEST_CONTENT.starting_quests if quest_log.get(quest_key, {}).get("status") == "completed"]


def get_tracked_quest(character):
    """Return the currently tracked active quest key, if any."""

    quest_key = getattr(character.db, "brave_tracked_quest", None)
    if not quest_key:
        return None

    state = (character.db.brave_quests or {}).get(quest_key, {})
    return quest_key if state.get("status") == "active" else None


def clear_tracked_quest(character):
    """Clear any tracked quest on the character."""

    character.db.brave_tracked_quest = None
    character.db.brave_track_suppressed = True
    _refresh_tracked_quest_scene(character)


def set_tracked_quest(character, quest_key):
    """Track one active quest by key."""

    if quest_key not in get_active_quests(character):
        return False

    character.db.brave_tracked_quest = quest_key
    character.db.brave_track_suppressed = False
    _refresh_tracked_quest_scene(character)
    return True


def resolve_active_quest_query(character, query):
    """Resolve a quest lookup from an index or title fragment."""

    active_keys = get_active_quests(character)
    token = "".join(char for char in (query or "").lower() if char.isalnum())
    if not token:
        return None

    if token.isdigit():
        index = int(token) - 1
        if 0 <= index < len(active_keys):
            return active_keys[index]

    title_map = {
        quest_key: "".join(char for char in QUEST_CONTENT.quests[quest_key]["title"].lower() if char.isalnum())
        for quest_key in active_keys
    }

    for quest_key in active_keys:
        if token == quest_key.lower() or token == title_map[quest_key]:
            return quest_key

    startswith_matches = [quest_key for quest_key in active_keys if title_map[quest_key].startswith(token)]
    if len(startswith_matches) == 1:
        return startswith_matches[0]

    contains_matches = [quest_key for quest_key in active_keys if token in title_map[quest_key]]
    if len(contains_matches) == 1:
        return contains_matches[0]

    return None


def get_tracked_quest_payload(character):
    """Return compact tracked-quest data for browser exploration UI."""

    quest_key = get_tracked_quest(character)
    if not quest_key:
        return None

    definition = QUEST_CONTENT.quests[quest_key]
    state = (character.db.brave_quests or {}).get(quest_key, {})
    objectives = []
    for objective in state.get("objectives", []):
        text = objective.get("description", "Objective")
        required = objective.get("required", 1)
        if required > 1:
            text += f" ({objective.get('progress', 0)}/{required})"
        objectives.append({
            "text": text,
            "completed": bool(objective.get("completed")),
        })

    if not objectives:
        return None

    return {
        "title": definition["title"],
        "giver": definition["giver"],
        "objectives": objectives[:3],
    }


def format_quest_block(character, quest_key):
    """Format a single quest block for display."""

    definition = QUEST_CONTENT.quests[quest_key]
    state = (character.db.brave_quests or {}).get(quest_key)
    if not state or state.get("status") == "locked":
        return None

    status = state["status"].replace("_", " ").title()
    lines = [
        f"|w{definition['title']}|n [{status}]",
        f"  {definition['summary']}",
        f"  Given by: {definition['giver']}",
    ]
    for objective in state["objectives"]:
        marker = "x" if objective["completed"] else " "
        progress_suffix = ""
        if objective.get("required", 1) > 1:
            progress_suffix = f" ({objective['progress']}/{objective['required']})"
        lines.append(f"  [{marker}] {objective['description']}{progress_suffix}")

    reward_text = _format_quest_reward_text(definition)
    if reward_text:
        lines.append(f"  Reward: {reward_text}")
    if definition.get("next_step") and state.get("status") == "active":
        lines.append(f"  Next: {definition['next_step']}")
    return "\n".join(lines)


def advance_room_visit(character, room):
    """Update room-visit objectives when a character enters a tagged room."""

    room_id = getattr(room.db, "brave_room_id", None)
    if not room_id:
        return

    quest_log = deepcopy(character.db.brave_quests or {})
    messages = []
    changed = False

    for quest_key, state in quest_log.items():
        if state.get("status") != "active":
            continue

        definition = QUEST_CONTENT.quests.get(quest_key)
        if not definition:
            continue

        for index, objective in enumerate(definition["objectives"]):
            objective_state = state["objectives"][index]
            if objective_state["completed"]:
                continue
            if objective["type"] == "visit_room" and objective["room_id"] == room_id:
                objective_state["progress"] = objective_state.get("required", 1)
                objective_state["completed"] = True
                changed = True
                messages.append(
                    f"|gQuest updated:|n {definition['title']} - {objective['description']}"
                )

    changed = _sync_quest_log(character, quest_log, messages) or changed

    if changed:
        character.db.brave_quests = quest_log
        _refresh_tracked_quest_scene(character)

    if messages:
        _record_recent_updates(character, messages)
    for message in messages:
        character.msg(message)


def advance_enemy_defeat(character, enemy_tags):
    """Update defeat objectives when a character defeats a matching enemy."""

    enemy_tags = set(enemy_tags or [])
    if not enemy_tags:
        return

    quest_log = deepcopy(character.db.brave_quests or {})
    messages = []
    changed = False

    for quest_key, state in quest_log.items():
        if state.get("status") != "active":
            continue

        definition = QUEST_CONTENT.quests.get(quest_key)
        if not definition:
            continue

        for index, objective in enumerate(definition["objectives"]):
            objective_state = state["objectives"][index]
            if objective_state["completed"]:
                continue
            if objective["type"] != "defeat_enemy":
                continue

            target_tag = objective.get("enemy_tag")
            if target_tag not in enemy_tags:
                continue

            objective_state["progress"] = min(
                objective_state["required"], objective_state["progress"] + 1
            )
            changed = True
            if objective_state["progress"] >= objective_state["required"]:
                objective_state["completed"] = True
            messages.append(
                f"|gQuest updated:|n {definition['title']} - "
                f"{objective_state['progress']}/{objective_state['required']}"
            )

    changed = _sync_quest_log(character, quest_log, messages) or changed

    if changed:
        character.db.brave_quests = quest_log
        _refresh_tracked_quest_scene(character)

    if messages:
        _record_recent_updates(character, messages)
    for message in messages:
        character.msg(message)


def advance_item_collection(character):
    """Update collect-item objectives after inventory changes."""

    quest_log = deepcopy(character.db.brave_quests or {})
    messages = []
    changed = _sync_quest_log(character, quest_log, messages)

    if changed:
        character.db.brave_quests = quest_log
        _refresh_tracked_quest_scene(character)

    if messages:
        _record_recent_updates(character, messages)
    for message in messages:
        character.msg(message)
