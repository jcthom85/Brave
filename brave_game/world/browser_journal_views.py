"""Quest journal browser view payload builders."""

from world.browser_context import (
    QUESTS,
    STARTING_QUESTS,
    get_quest_region,
    group_quest_keys_by_region,
)
from world.browser_room_helpers import _local_npc_keys
from world.browser_ui import (
    _action,
    _entry,
    _line,
    _make_view,
    _picker,
    _picker_option,
    _reactive_from_character,
    _section,
)
from world.questing import get_tracked_quest
from world.tutorial import (
    TUTORIAL_STEPS,
    ensure_tutorial_state,
    get_tutorial_objective_entries,
)

def _build_tutorial_entry(character):
    state = ensure_tutorial_state(character)
    if state.get("status") != "active":
        return None

    step_key = state.get("step") or "first_steps"
    step = TUTORIAL_STEPS[step_key]
    tutorial_objectives = get_tutorial_objective_entries(character) or {}
    lines = [step["summary"]]
    lines.extend(
        _line(
            objective.get("text", "Objective"),
            icon="check_box" if objective.get("completed") else "check_box_outline_blank",
        )
        for objective in tutorial_objectives.get("objectives", [])
    )
    return _entry(step["title"], meta="Tutorial", lines=lines, icon="school")

def _format_objective_progress(objective):
    text = objective.get("description", "Objective")
    required = objective.get("required", 1)
    if required > 1:
        text += f" ({objective.get('progress', 0)}/{required})"
    return text

def _get_journal_mode(character):
    mode = getattr(getattr(character, "db", None), "brave_journal_tab", "active")
    return mode if mode in {"active", "completed"} else "active"

def _get_expanded_completed_quest(character):
    value = getattr(getattr(character, "db", None), "brave_journal_expanded_completed", None)
    return value or None

def _build_journal_quest_picker(character, quest_key, *, tracked_key=None, nearby_npcs=None):
    state = (character.db.brave_quests or {}).get(quest_key, {})
    definition = QUESTS[quest_key]
    all_objectives = list(state.get("objectives", []))
    completed = state.get("status") == "completed"
    options = []

    if completed:
        options.append(_picker_option("Completed", icon="check_circle", tone="good"))
    elif quest_key == tracked_key:
        options.append(_picker_option("Untrack", command="quests untrack", icon="flag", tone="accent"))
    else:
        options.append(_picker_option("Track", command=f"quests track {quest_key}", icon="flag", tone="accent"))

    body = [definition["summary"]]
    body.extend(
        _line(
            _format_objective_progress(objective),
            icon="check_box" if objective.get("completed") else "check_box_outline_blank",
        )
        for objective in all_objectives[:8]
    )

    return _picker(
        definition["title"],
        subtitle=f"{get_quest_region(quest_key)} · {definition['giver']}",
        options=options,
        body=body,
    )

def _build_journal_quest_entry(character, quest_key, *, tracked_key=None, nearby_npcs=None, detailed=False, inline_command=None):
    state = (character.db.brave_quests or {}).get(quest_key, {})
    definition = QUESTS[quest_key]
    completed = state.get("status") == "completed"
    all_objectives = list(state.get("objectives", []))
    remaining_objectives = [
        objective for objective in all_objectives if not objective.get("completed")
    ]
    next_objective = remaining_objectives[0] if remaining_objectives else None
    lines = []
    meta = definition["giver"]

    if detailed:
        lines.append(definition["summary"])
        lines.extend(
            _line(
                _format_objective_progress(objective),
                icon="check_box" if objective.get("completed") else "check_box_outline_blank",
            )
            for objective in all_objectives
        )
        return _entry(
            definition["title"],
            meta=f"{get_quest_region(quest_key)} · {definition['giver']}",
            lines=lines,
            icon=None if completed else "flag",
            hide_icon=completed,
            command=inline_command,
            actions=[] if state.get("status") == "completed" else [
                _action("Untrack", "quests untrack", "flag", tone="accent"),
            ],
        )

    if completed:
        return _entry(
            definition["title"],
            meta=f"{get_quest_region(quest_key)} · {definition['giver']}",
            lines=[],
            icon=None,
            hide_icon=True,
            command=inline_command,
        )

    if next_objective:
        lines.append(f"Next: {_format_objective_progress(next_objective)}")
    else:
        lines.append(definition["summary"])

    return _entry(
        definition["title"],
        meta=meta,
        lines=lines,
        icon=None,
        hide_icon=True,
        command=inline_command,
        picker=None if completed else _build_journal_quest_picker(
            character,
            quest_key,
            tracked_key=tracked_key,
            nearby_npcs=nearby_npcs,
        ),
    )

def _build_journal_region_sections(character, quest_keys, *, tracked_key=None, status="active"):
    nearby_npcs = _local_npc_keys(character)
    sections = []
    expanded_completed_key = _get_expanded_completed_quest(character) if status == "completed" else None
    filtered_keys = [quest_key for quest_key in quest_keys if not (status == "active" and quest_key == tracked_key)]
    for region, region_keys in group_quest_keys_by_region(filtered_keys):
        items = [
            _build_journal_quest_entry(
                character,
                quest_key,
                tracked_key=tracked_key,
                nearby_npcs=nearby_npcs,
                detailed=(status == "completed" and quest_key == expanded_completed_key),
                inline_command=(
                    f"quests collapse {quest_key}"
                    if status == "completed" and quest_key == expanded_completed_key
                    else (f"quests expand {quest_key}" if status == "completed" else None)
                ),
            )
            for quest_key in region_keys
        ]
        kind = "entries"

        sections.append(
            _section(
                region,
                "explore",
                kind,
                items=items,
                variant="active" if status == "active" else "archive",
            )
        )
    return sections

def build_quests_view(character):
    """Return a browser-first main view for the quest journal."""

    journal_mode = _get_journal_mode(character)
    tutorial_entry = _build_tutorial_entry(character)
    tutorial_active = tutorial_entry is not None
    tracked_key = get_tracked_quest(character)
    nearby_npcs = _local_npc_keys(character)
    tracked_entry = _build_journal_quest_entry(
        character,
        tracked_key,
        tracked_key=tracked_key,
        nearby_npcs=nearby_npcs,
        detailed=True,
    ) if tracked_key and not tutorial_active else None
    active_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if (character.db.brave_quests or {}).get(quest_key, {}).get("status") == "active"
    ]
    completed_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if (character.db.brave_quests or {}).get(quest_key, {}).get("status") == "completed"
    ]

    actions = [
        _action(
            "Active",
            "quests active",
            "assignment",
            tone="accent" if journal_mode == "active" else "muted",
        ),
        _action(
            "Completed",
            "quests completed",
            "check_circle",
            tone="accent" if journal_mode == "completed" else "muted",
        ),
    ]

    sections = [
        _section(
            "",
            "assignment",
            "actions",
            items=actions,
            hide_label=True,
            span="wide",
            variant="switcher",
        )
    ]
    if journal_mode == "active":
        effective_tracked_entry = tutorial_entry or tracked_entry
        if effective_tracked_entry:
            sections.append(
                _section(
                    "",
                    "school" if tutorial_entry else "flag",
                    "entries",
                    items=[effective_tracked_entry],
                    variant="tracked",
                    hide_label=True,
                )
            )
        sections.extend(
            _build_journal_region_sections(
                character,
                active_keys,
                tracked_key=tracked_key,
                status="active",
            )
        )
        if len(sections) == 1:
            sections.append(
                _section(
                    "Active Quests",
                    "assignment",
                    "entries",
                    items=[_entry("No active quests right now.", icon="info")],
                    variant="active",
                )
            )
    else:
        sections.extend(
            _build_journal_region_sections(
                character,
                completed_keys,
                status="completed",
            )
        )
        if len(sections) == 1:
            sections.append(
                _section(
                    "Completed Quests",
                    "task_alt",
                    "entries",
                    items=[_entry("No completed quests yet.", icon="info")],
                    variant="archive",
                )
            )

    return {
        **_make_view(
            "",
            "Journal",
            eyebrow_icon=None,
            title_icon="menu_book",
            subtitle="",
            chips=[],
            sections=sections,
            actions=[],
            back=True,
            reactive=_reactive_from_character(character, scene="journal"),
        ),
        "variant": "journal",
    }
