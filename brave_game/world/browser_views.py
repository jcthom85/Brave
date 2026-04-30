"""Browser-only main-pane view payloads for Brave's richer command screens."""

from world.arcade import format_arcade_score, get_personal_best, get_reward_definition, has_arcade_reward
from world.data.arcade import ARCADE_GAMES
from world.data.themes import THEMES, THEME_BY_KEY, normalize_theme_key
from world.chapel import get_active_blessing
from world.character_icons import get_class_icon, get_race_icon
from world.class_features import get_class_features
from world.genders import BRAVE_GENDER_LABELS, get_brave_gender_label
from world.navigation import build_map_snapshot, visible_exits
from world.tutorial import LANTERNFALL_RECAP_PAGES, LANTERNFALL_WELCOME_PAGES

from world.browser_context import (
    ABILITY_LIBRARY,
    CHARACTER_CONTENT,
    CLASSES,
    COOKING_RECIPES,
    ENCOUNTER_CONTENT,
    ENEMY_TEMPLATES,
    EQUIPMENT_SLOTS,
    ITEM_TEMPLATES,
    PASSIVE_ABILITY_BONUSES,
    PORTALS,
    PORTAL_STATUS_LABELS,
    QUESTS,
    RACES,
    STARTING_QUESTS,
    SYSTEMS_CONTENT,
    VERTICAL_SLICE_CLASSES,
    ability_key,
    format_ingredient_list,
    get_item_category,
    get_item_use_profile,
    get_quest_region,
    group_quest_keys_by_region,
    split_unlocked_abilities,
    xp_needed_for_next_level,
)
from world.browser_formatting import (
    _format_context_bonus_summary,
    _format_item_value_text,
    _format_restore_summary,
)
from world.browser_inventory_views import (
    GEAR_SLOT_ICONS,
    GEAR_SLOT_LABELS,
    PACK_KIND_LABELS,
    PACK_KIND_ORDER,
    build_gear_view,
    build_pack_view,
)
from world.browser_journal_views import build_quests_view
from world.browser_party_views import build_party_view
from world.browser_room_helpers import (
    ROOM_ENTITY_ID_ICONS,
    ROOM_ENTITY_KIND_ICONS,
    TUTORIAL_READ_ENTITY_IDS,
    TUTORIAL_TALK_ENTITY_IDS,
    _build_room_social_presence,
    _build_world_interaction_picker,
    _format_room_context_action_items,
    _format_room_entity_items,
    _format_room_threat_items,
    _local_npc_keys,
    _local_player_characters,
    _movement_command,
    _short_direction,
)
from world.browser_service_views import (
    build_cook_view,
    build_fishing_view,
    build_forge_view,
    build_shop_view,
    build_tinker_view,
)
from world.item_rarity import build_item_rarity_display
from world.browser_ui import (
    _action,
    _chip,
    _combat_card_size_class,
    _display_name,
    _enemy_icon,
    _entry,
    _hp_meter_tone,
    _item,
    _line,
    _make_view,
    _meter,
    _pair,
    _picker,
    _picker_option,
    _reactive_from_character,
    _reactive_view,
    _resource_meter_tone,
    _section,
)

WELCOME_PAGES = LANTERNFALL_WELCOME_PAGES
RECAP_PAGES = LANTERNFALL_RECAP_PAGES


def _pre_section(label, icon, text, *, span=None, tone=None, hide_label=False, grid=None):
    section = {
        "label": label,
        "icon": icon,
        "kind": "pre",
        "text": text,
    }
    if span:
        section["span"] = span
    if tone:
        section["tone"] = tone
    if hide_label:
        section["hide_label"] = True
    if grid:
        section["grid"] = grid
    return section


CHARGEN_STEP_ORDER = (
    "menunode_choose_race",
    "menunode_choose_class",
    "menunode_choose_gender",
    "menunode_choose_name",
    "menunode_confirm",
)

CHARGEN_STEP_META = {
    "menunode_choose_race": {
        "eyebrow": "Ancestry",
        "title": "Choose Your Origin",
        "title_icon": "diversity_3",
        "subtitle": "Your blood carries the weight of history and ancient perks.",
        "step_index": 1,
    },
    "menunode_choose_class": {
        "eyebrow": "Calling",
        "title": "Choose A Class",
        "title_icon": "swords",
        "subtitle": "How do you face the world when it bites back?",
        "step_index": 2,
    },
    "menunode_choose_gender": {
        "eyebrow": "Identity",
        "title": "Choose A Gender",
        "title_icon": "person",
        "subtitle": "Select the gender identity for your character.",
        "step_index": 3,
    },
    "menunode_choose_name": {
        "eyebrow": "Identity",
        "title": "Choose A Name",
        "title_icon": "badge",
        "subtitle": "Set the name this character will carry into the world.",
        "step_index": 4,
    },
    "menunode_confirm": {
        "eyebrow": "Finality",
        "title": "Review And Forge",
        "title_icon": "task_alt",
        "subtitle": "The path is clear. Is this the one who will walk it?",
        "step_index": 5,
    },
}


def build_chargen_view(account, state, *, error=None):
    """Return a browser-native main view for the character creator."""

    from world.chargen import get_next_chargen_step

    step_key = state.get("step") or "menunode_choose_race"
    step_meta = CHARGEN_STEP_META.get(step_key, CHARGEN_STEP_META["menunode_choose_race"])
    slots_left = account.get_available_character_slots()
    slot_text = "Unlimited" if slots_left is None else str(slots_left)
    race_name = RACES.get(state.get("race"), {}).get("name", "Not set")
    class_name = CLASSES.get(state.get("class"), {}).get("name", "Not set")
    gender_label = get_brave_gender_label(state.get("gender"))

    chips = [
        _chip(f"Step {step_meta['step_index']} / 5", "steps", "accent"),
        _chip(f"{slot_text} open", "add_circle", "muted"),
    ]
    if state.get("race"):
        chips.append(_chip(race_name, get_race_icon(state.get("race"), RACES.get(state.get("race"))), "muted"))
    if state.get("class"):
        chips.append(_chip(class_name, get_class_icon(state.get("class"), CLASSES.get(state.get("class"))), "muted"))

    sections = [
        _section(
            "Draft",
            "checklist",
            "pairs",
            items=[
                _pair("Name", state.get("name") or "Not set", "badge"),
                _pair("Gender", gender_label, "person"),
                _pair("Race", race_name, get_race_icon(state.get("race"), RACES.get(state.get("race")))),
                _pair("Class", class_name, get_class_icon(state.get("class"), CLASSES.get(state.get("class")))),
            ],
            span="wide",
        )
    ]

    actions = []

    def _race_feel(race_key, race_data):
        if race_key == "human":
            return ("Steady start", "bolt")
        if race_key == "elf":
            return ("Precision", "visibility")
        if race_key == "dwarf":
            return ("Durable", "shield")
        if race_key == "mosskin":
            return ("Evasive", "footprint")
        if race_key == "ashborn":
            return ("Aggressive", "local_fire_department")
        return (race_data.get("perk", "Trait"), "star")

    def _class_style(class_key, class_data):
        role = (class_data.get("role") or "").lower()
        if class_key == "warrior":
            return ("Low upkeep", "Frontline anchor", "security")
        if class_key == "cleric":
            return ("Medium upkeep", "Recovery and rescue", "healing")
        if class_key == "ranger":
            return ("Medium upkeep", "Mark and pick targets", "ads_click")
        if class_key == "mage":
            return ("High upkeep", "Burst and control", "auto_awesome")
        if class_key == "rogue":
            return ("High upkeep", "Exploit openings", "bolt")
        if class_key == "paladin":
            return ("Medium upkeep", "Guard and support", "shield")
        if class_key == "druid":
            return ("High upkeep", "Control and adapt", "forest")
        if "tank" in role:
            return ("Medium upkeep", "Hold pressure", "shield")
        if "healer" in role or "support" in role:
            return ("Medium upkeep", "Keep allies stable", "healing")
        return ("Medium upkeep", "Flexible pressure", "star")

    if step_key == "menunode_welcome":
        next_step = get_next_chargen_step(state)
        next_step_entry = {
            "menunode_choose_race": _entry(
                "Choose Race",
                meta="Step 1",
                icon="diversity_3",
                command="continue",
            ),
            "menunode_choose_class": _entry(
                "Choose Class",
                meta="Step 2",
                icon="swords",
                command="continue",
            ),
            "menunode_choose_gender": _entry(
                "Choose Gender",
                meta="Step 3",
                icon="person",
                command="continue",
            ),
            "menunode_choose_name": _entry(
                "Choose Name",
                meta="Step 4",
                icon="badge",
                command="continue",
            ),
            "menunode_confirm": _entry(
                "Review Character",
                meta="Step 5",
                icon="task_alt",
                command="continue",
                chips=[_chip("Ready", "check_circle", "good")],
            ),
        }[next_step]
        sections.append(_section("Next Step", "format_list_numbered", "entries", items=[next_step_entry]))
    elif step_key == "menunode_choose_gender":
        sections = []
        if error:
            sections.append(
                _section(
                    "Identity Issue",
                    "trash",
                    "lines",
                    lines=[error.replace("|r", "").replace("|n", "")],
                    span="wide",
                )
            )
        gender_entries = []
        for gender_key, label in BRAVE_GENDER_LABELS.items():
            gender_entries.append(
                _entry(
                    label,
                    meta="Selected" if state.get("gender") == gender_key else None,
                    lines=[],
                    icon="person",
                    command=label.lower(),
                    chips=[_chip("Current", "check_circle", "good")] if state.get("gender") == gender_key else [],
                )
            )
        sections.append(_section("Gender", "person", "entries", items=gender_entries, span="wide"))
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
    elif step_key == "menunode_choose_name":
        sections = []
        if error:
            sections.append(
                _section(
                    "Identity Issue",
                    "trash",
                    "lines",
                    lines=[error.replace("|r", "").replace("|n", "")],
                    span="wide",
                )
            )
        sections.append(
            _section(
                "Identity",
                "badge",
                "form",
                span="wide",
                hide_label=True,
                fields=[
                    {
                        "field_label": "Character Name",
                        "field_name": "character_name",
                        "value": state.get("name") or "",
                        "placeholder": "Type your character name here",
                        "maxlength": 24,
                        "minlength": 2,
                        "autocapitalize": "words",
                        "autocomplete": "off",
                        "spellcheck": False,
                        "enterkeyhint": "done",
                        "autofocus": True,
                    }
                ],
                submit_label="Save And Continue",
                submit_icon="arrow_forward",
                submit_tone="accent",
                submit_mode="raw",
            )
        )
        sections.append(
            _section(
                "Rules",
                "rule",
                "list",
                items=[
                    _item("2 to 24 characters", icon="straighten"),
                    _item("Letters, spaces, apostrophes, and hyphens only", icon="spellcheck"),
                    _item("Must be unique across all characters", icon="shield"),
                ],
            )
        )
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
    elif step_key == "menunode_choose_race":
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
        race_entries = []
        for race_key, race_data in RACES.items():
            feel_label, feel_icon = _race_feel(race_key, race_data)
            race_entries.append(
                _entry(
                    race_data["name"],
                    meta="Selected" if state.get("race") == race_key else "Origin",
                    lines=[
                        race_data["summary"],
                        f"Perk: {race_data['perk']}",
                        f"Feel: {feel_label}",
                    ],
                    background_icon=get_race_icon(race_key, race_data),
                    command=race_key,
                    hide_icon=True,
                    chips=[
                        *([_chip("Current", "check_circle", "good")] if state.get("race") == race_key else []),
                        _chip(feel_label, feel_icon, "muted"),
                    ],
                )
            )
        sections.append(_section("Races", "forest", "entries", items=race_entries, span="wide"))
    elif step_key == "menunode_choose_class":
        actions.append(_action("Back", "back", "arrow_back", tone="muted"))
        class_entries = []
        for class_key in VERTICAL_SLICE_CLASSES:
            class_data = CLASSES[class_key]
            features = get_class_features(class_key)
            upkeep_label, style_label, style_icon = _class_style(class_key, class_data)
            class_entries.append(
                _entry(
                    class_data["name"],
                    meta=class_data["role"],
                    lines=[
                        class_data["summary"],
                        f"Approach: {style_label}",
                        *[feature["summary"] for feature in features[:1]],
                    ],
                    background_icon=get_class_icon(class_key, class_data),
                    command=class_key,
                    hide_icon=True,
                    chips=[
                        *([_chip("Current", "check_circle", "good")] if state.get("class") == class_key else []),
                        _chip(upkeep_label, "tune", "muted"),
                        _chip(style_label, style_icon, "muted"),
                        *[_chip(feature["name"], feature.get("icon", "star"), "muted") for feature in features[:2]],
                    ],
                )
            )
        sections.append(_section("Classes", "swords", "entries", items=class_entries, span="wide"))
    elif step_key == "menunode_confirm":
        actions.extend(
            [
                _action("Create And Play", "finish play", "play_arrow", tone="accent"),
                _action("Back", "back", "arrow_back", tone="muted"),
            ]
        )
        race_data = RACES.get(state.get("race"), {})
        class_data = CLASSES.get(state.get("class"), {})
        if error:
            sections.append(
                _section(
                    "Issue",
                    "trash",
                    "lines",
                    lines=[error.replace("|r", "").replace("|n", "")],
                    span="wide",
                )
            )
        sections.append(
            _section(
                "Highlights",
                "star",
                "entries",
                items=[
                    _entry(
                        get_brave_gender_label(state.get("gender")),
                        meta="Identity",
                        lines=["Gender selection locked in for this character."],
                        icon="person",
                    ),
                    _entry(
                        race_data.get("name", "Race"),
                        meta="Race Perk",
                        lines=[race_data.get("perk", "No perk found."), race_data.get("summary", "")],
                        icon=get_race_icon(state.get("race"), race_data),
                    ),
                    _entry(
                        class_data.get("name", "Class"),
                        meta=class_data.get("role", "Role"),
                        lines=[
                            class_data.get("summary", "No class summary found."),
                            f"Approach: {_class_style(state.get('class'), class_data)[1]}",
                        ],
                        icon=get_class_icon(state.get("class"), class_data),
                    ),
                ],
                span="wide",
                variant="grid3",
            )
        )
        sections.append(
            _section(
                "Begin Your Journey",
                "play_arrow",
                "entries",
                items=[
                    _entry(
                        "Create Character",
                        lines=["Create this character and enter the world immediately."],
                        icon="login",
                        command="finish play",
                    ),
                ],
                span="wide",
            )
        )

    return {
        **_make_view(
            step_meta["eyebrow"],
            step_meta["title"],
            eyebrow_icon="person_add",
            title_icon=step_meta["title_icon"],
            wordmark="BRAVE",
            subtitle=step_meta["subtitle"],
            chips=chips,
            sections=sections,
            actions=actions,
            reactive=_reactive_view(scene="account"),
        ),
        "variant": "chargen",
    }


def build_map_view(room, character, *, mode="map"):
    """Return a browser-first large map view."""

    radius = None if mode == "map" else 2
    snapshot = build_map_snapshot(room, radius=radius, character=character)
    if not snapshot:
        return _make_view(
            "",
            "Map Unavailable",
            eyebrow_icon=None,
            title_icon="map",
            subtitle="",
            chips=[],
            sections=[_section("Status", "info", "lines", lines=["No regional coordinates are configured for this room."])],
            back=True,
        )

    region_room = snapshot["room"]
    region_label = region_room.db.brave_zone or snapshot["region"] or "Region"

    legend_items = []
    for entry in snapshot["legend"]:
        text = entry["label"]
        if entry.get("suffix"):
            text += f" · {entry['suffix']}"
        legend_items.append({"text": text, "icon": entry.get("symbol") or "place"})

    sections = [
        _pre_section(region_label, "grid_view", snapshot["map_text"], span="mapwide", tone="map", grid=snapshot.get("map_tiles")),
        _section("Legend", "category", "list", items=legend_items),
    ]

    if snapshot["party"]:
        sections.append(
            _section(
                "Party",
                "groups",
                "entries",
                items=[
                    _entry(
                        member["name"],
                        meta=member["status"].title(),
                        lines=[member["location"], member["route"]],
                        icon="person",
                    )
                    for member in snapshot["party"]
                ],
            )
        )

    view = _make_view(
        "",
        "Map" if mode == "map" else "Local Map",
        eyebrow_icon=None,
        title_icon="map",
        subtitle="",
        chips=[],
        sections=sections,
        back=True,
        reactive=_reactive_view(
            region_room,
            scene="map",
            danger="safe" if getattr(region_room.db, "brave_safe", False) else "danger",
        ),
    )
    if view.get("back_action"):
        view["back_action"]["label"] = ""
        view["back_action"]["aria_label"] = "Close"
    return {**view, "variant": "map"}


def _character_location_label(character):
    return character.location.key if character.location else ""


def build_account_view(account):
    """Return a browser-first main view for the OOC account screen."""

    from world.chargen import has_chargen_progress

    characters = list(account.characters.all())
    last_played = account.db._last_puppet if account.db._last_puppet in characters else None
    available_slots = account.get_available_character_slots()
    pending = dict(account.db.brave_chargen or {})
    has_pending = has_chargen_progress(account)

    roster_entries = []
    can_create = available_slots is None or available_slots > 0 or has_pending
    if can_create:
        create_lines = []
        create_meta = None
        create_icon = "person_add"
        create_chips = []
        create_actions = []
        if has_pending:
            create_meta = None
            create_icon = "edit_note"
            create_chips.append(_chip("Draft", "edit_note", "warn"))
            create_lines = [
                f"Name: {pending.get('name') or '-'}",
                f"Race: {RACES.get(pending.get('race'), {}).get('name', '-')}",
                f"Class: {CLASSES.get(pending.get('class'), {}).get('name', '-')}",
            ]
            create_title = "Resume Character Creation"
            create_actions.append(
                _action(
                    "Discard draft",
                    "create discard",
                    "trash",
                    tone="danger",
                    confirm="Discard this saved character draft?",
                    icon_only=True,
                    aria_label="Discard saved character draft",
                )
            )
        else:
            create_title = "Create Character"

        roster_entries.append(
            _entry(
                create_title,
                meta=create_meta,
                lines=create_lines,
                icon=create_icon,
                command="create",
                chips=create_chips,
                actions=create_actions,
            )
        )

    for index, character in enumerate(characters, start=1):
        character.ensure_brave_character()
        race_name = RACES[character.db.brave_race]["name"]
        class_name = CLASSES[character.db.brave_class]["name"]
        lines = [
            f"{race_name} {class_name} · Level {character.db.brave_level}",
        ]
        if location_label := _character_location_label(character):
            lines.append(location_label)
        entry_chips = []
        if last_played and character.id == last_played.id:
            entry_chips.append(_chip("Last Played", "history", "accent"))
        roster_entries.append(
            _entry(
                character.key,
                meta=None,
                lines=lines,
                icon=get_class_icon(character.db.brave_class, CLASSES.get(character.db.brave_class)),
                badge=str(index),
                command=f"play {index}",
                chips=entry_chips,
                actions=[
                    _action(
                        "Delete",
                        f"delete {index} --force",
                        "trash",
                        tone="danger",
                        confirm=f"Delete {character.key} permanently?",
                        icon_only=True,
                        aria_label=f"Delete {character.key}",
                    )
                ],
            )
        )

    sections = [
        _section(
            "",
            "groups",
            "entries",
            items=roster_entries or [_entry("No characters yet.", lines=["Create your first adventurer to begin."], icon="person_add")],
            hide_label=True,
        ),
    ]

    actions = [_action("Logout", "logout", "logout", tone="muted")]

    return {
        **_make_view(
            account.key,
            "",
            eyebrow_icon="badge",
            title_icon=None,
            wordmark="BRAVE",
            subtitle="",
            chips=[],
            sections=sections,
            actions=actions,
            reactive=_reactive_view(scene="account"),
        ),
        "variant": "account",
    }


def build_connection_view(*, screen="menu", error=None, username="", registration_enabled=True):
    """Return a browser-native login/account-creation view."""

    normalized_screen = (screen or "menu").strip().lower()
    if normalized_screen not in {"menu", "signin", "create"}:
        normalized_screen = "menu"

    chips = []
    if normalized_screen == "create":
        chips.append(_chip("Character creation happens after login", "arrow_forward", "muted"))
    sections = []
    actions = []
    clean_error = (error or "").strip()
    if clean_error:
        sections.append(
            _section(
                "Issue",
                "warning",
                "lines",
                lines=[clean_error],
                span="wide",
            )
        )

    if normalized_screen == "signin":
        actions.append(_action("Back", "", "arrow_back", tone="muted"))
        actions[-1]["connection_screen"] = "menu"
        sections.append(
            _section(
                "Sign In",
                "login",
                "form",
                span="wide",
                fields=[
                    {
                        "field_name": "username",
                        "field_label": "Username",
                        "placeholder": "Username",
                        "value": username,
                        "autocomplete": "username",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "autofocus": True,
                    },
                    {
                        "field_name": "password",
                        "field_label": "Password",
                        "input_type": "password",
                        "placeholder": "Password",
                        "autocomplete": "current-password",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "enterkeyhint": "go",
                    },
                ],
                submit_template="connect {username} {password}",
                submit_label="Sign In",
                submit_icon="login",
                submit_tone="accent",
            )
        )
        sections.append(
            _section(
                "What Happens Next",
                "explore",
                "list",
                items=[
                    _item("Choose a character or resume a draft after login.", icon="groups"),
                    _item("Your last played character will be ready to continue.", icon="history"),
                    _item("If sign-in fails, you stay here with the username preserved.", icon="sync_problem"),
                ],
            )
        )
        eyebrow = "Sign In"
        eyebrow_icon = "login"
        subtitle = ""
    elif normalized_screen == "create":
        actions.append(_action("Back", "", "arrow_back", tone="muted"))
        actions[-1]["connection_screen"] = "menu"
        sections.append(
            _section(
                "Create Account",
                "person_add",
                "form",
                span="wide",
                fields=[
                    {
                        "field_name": "username",
                        "field_label": "Username",
                        "placeholder": "Choose a username",
                        "value": username,
                        "autocomplete": "username",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "autofocus": True,
                    },
                    {
                        "field_name": "password",
                        "field_label": "Password",
                        "input_type": "password",
                        "placeholder": "Choose a password",
                        "autocomplete": "new-password",
                        "autocapitalize": "none",
                        "spellcheck": False,
                    },
                    {
                        "field_name": "password_confirm",
                        "field_label": "Confirm Password",
                        "input_type": "password",
                        "placeholder": "Repeat your password",
                        "autocomplete": "new-password",
                        "autocapitalize": "none",
                        "spellcheck": False,
                        "enterkeyhint": "go",
                    },
                ],
                submit_template="create {username} {password} {password_confirm}",
                submit_label="Create Account",
                submit_icon="person_add",
                submit_tone="accent",
            )
        )
        sections.append(
            _section(
                "Account Rules",
                "rule",
                "list",
                items=[
                    _item("Use a stable username you can remember.", icon="badge"),
                    _item("Pick a password you have not reused elsewhere.", icon="shield"),
                    _item(
                        "After the account is created, you will continue into character setup."
                        if registration_enabled
                        else "New account registration is currently disabled.",
                        icon="arrow_forward" if registration_enabled else "block",
                    ),
                    _item("Use the same account for multiple characters instead of creating multiple logins.", icon="groups"),
                ],
            )
        )
        eyebrow = "Create Account"
        eyebrow_icon = "person_add"
        subtitle = "Make an account, then shape your first adventurer."
    else:
        sections.append(
            _section(
                "Enter Brave",
                "key",
                "list",
                items=[
                    _item("Sign In", icon="key"),
                    _item("Create Account", icon="quill"),
                ],
            )
        )
        sections[0]["items"][0]["connection_screen"] = "signin"
        sections[0]["items"][1]["connection_screen"] = "create"
        eyebrow = ""
        eyebrow_icon = None
        subtitle = ""

    return {
        **_make_view(
            eyebrow,
            "",
            eyebrow_icon=eyebrow_icon,
            title_icon=None,
            wordmark="BRAVE",
            subtitle=subtitle,
            chips=chips,
            sections=sections,
            actions=actions,
            reactive=_reactive_view(scene="account"),
        ),
        "variant": "connection",
    }


def build_theme_view(current_theme_key=None):
    """Build the browser-native theme selection screen."""

    current_theme = THEME_BY_KEY.get(normalize_theme_key(current_theme_key))
    current_theme_key = current_theme["key"] if current_theme else normalize_theme_key(current_theme_key)

    entries = []
    default_theme_key = "hearth"
    for theme in THEMES:
        lines = [theme["summary"]]
        chips_for_entry = []
        if theme["key"] == default_theme_key:
            chips_for_entry.append(_chip("Default", "home", "accent"))
        if theme["key"] == current_theme_key:
            chips_for_entry.append(_chip("Current", "check_circle", "good"))

        entry = _entry(
            theme["name"],
            meta=None,
            summary="",
            lines=lines,
            command=f"theme {theme['key']}",
            chips=chips_for_entry,
        )
        entry["preview"] = {
            "theme_key": theme["key"],
            "font_name": theme["font_name"],
            "summary": theme["summary"],
            "current": theme["key"] == current_theme_key,
        }
        entries.append(entry)

    view = _make_view(
        "",
        "Themes",
        eyebrow_icon=None,
        title_icon="snowflake",
        subtitle="",
        chips=[],
        sections=[_section("", "palette", "entries", items=entries, hide_label=True)],
        actions=[],
        back=True,
        reactive=_reactive_view(scene="theme"),
    )
    if view.get("back_action"):
        view["back_action"]["label"] = ""
        view["back_action"]["aria_label"] = "Close"
    return {**view, "variant": "theme"}


def build_prayer_view(character, *, blessing=None, applied=False):
    """Return a browser-first main view for the Chapel blessing."""

    blessing = blessing or get_active_blessing(character)
    blessing_name = blessing.get("name", "Dawn Bell Blessing")
    duration = blessing.get("duration", "Until your next encounter ends.")
    bonus_text = _format_context_bonus_summary(blessing.get("bonuses", {}), character)
    rite = dict(blessing.get("rite") or {})

    chips = [
        _chip(blessing_name, "wb_sunny", "accent"),
        _chip("One encounter", "schedule", "muted"),
    ]
    if rite.get("name"):
        chips.append(_chip(rite["name"], "workspace_premium", "good"))

    sections = [
        _section(
            "Blessing",
            "wb_sunny",
            "lines",
            lines=[
                "The bell's steadier note settles into you and follows you back onto the road.",
                duration,
                "Bonuses: " + bonus_text if bonus_text else "No mechanical bonus recorded.",
            ],
        ),
    ]
    if rite:
        sections.append(
            _section(
                "Class Rite",
                "workspace_premium",
                "lines",
                lines=[rite.get("summary", ""), *(rite.get("lines") or [])],
            )
        )
    sections.append(
        _section(
            "Chapel Notes",
            "church",
            "list",
            items=[
                _item("Brother Alden watches the west-side trouble and the barrow line.", icon="forum"),
                _item("Sister Maybelle tends the hurt and keeps the town practical about what bravery costs.", icon="forum"),
                _item("Return here before a harder run when you want the Dawn Bell at your back.", icon="flag"),
            ],
        )
    )

    subtitle = (
        "The Dawn Bell answers and steadies you for the next hard road."
        if applied
        else "The Dawn Bell's ward still rests on you."
    )

    return _make_view(
        "Chapel Of The Dawn Bell",
        "Dawn Bell",
        eyebrow_icon="church",
        title_icon="wb_sunny",
        subtitle=subtitle,
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="chapel"),
    )


def build_portals_view(character):
    """Return a browser-first main view for current Nexus gates."""

    sections = []
    for status_key, section_title in (("stable", "Stable"), ("dormant", "Dormant"), ("sealed", "Sealed")):
        items = []
        for portal in PORTALS.values():
            if portal["status"] != status_key:
                continue
            lines = [f"Resonance: {portal['resonance'].replace('_', ' ').title()}"]
            if portal.get("travel_hint"):
                lines.append(f"Entry route: {portal['travel_hint']}")
            command = None
            actions = []
            if portal["status"] == "stable" and portal.get("travel_hint"):
                command = _movement_command(portal["travel_hint"], f"travel {portal['travel_hint']}")
                actions.append(_action("Travel", command, "travel_explore", tone="accent"))
            items.append(
                _entry(
                    portal["name"],
                    meta=PORTAL_STATUS_LABELS.get(portal["status"], portal["status"].title()),
                    lines=lines,
                    summary=portal["summary"],
                    icon="travel_explore",
                    command=command,
                    actions=actions,
                )
            )
        sections.append(_section(section_title, "travel_explore", "entries", items=items or [_entry("None at the moment.", icon="info")]))

    stable_count = sum(1 for portal in PORTALS.values() if portal["status"] == "stable")
    return _make_view(
        "Nexus",
        "Gates",
        eyebrow_icon="travel_explore",
        title_icon="public",
        subtitle="The ring lists what Brambleford can currently reach and what still refuses to answer.",
        chips=[_chip(f"{stable_count} stable", "travel_explore", "accent" if stable_count else "muted")],
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )


def build_travel_view(character):
    """Return a browser-first main view for travel fallback."""

    room = getattr(character, "location", None)
    exits = visible_exits(room, character) if room else []
    route_entries = []
    for exit_obj in exits:
        direction = getattr(exit_obj.db, "brave_direction", exit_obj.key).lower()
        aliases = [alias for alias in exit_obj.aliases.all() if alias.lower() != direction]
        lines = []
        if aliases:
            lines.append("Aliases: " + ", ".join(aliases))
        command = _movement_command(direction, exit_obj.key)
        route_entries.append(
            _entry(
                getattr(exit_obj.destination, "key", None) or exit_obj.key,
                meta=direction.title(),
                lines=lines,
                icon="route",
                badge=_short_direction(direction),
                command=command,
            )
        )

    return _make_view(
        "Travel",
        "Routes",
        eyebrow_icon="explore",
        title_icon="route",
        subtitle=f"Current room: {room.key}" if room else "No current room.",
        chips=[_chip(f"{len(exits)} exits", "move_selection_right", "accent" if exits else "muted")],
        sections=[
            _section("From Here", "route", "entries", items=route_entries or [_entry("No routes available from here.", icon="block")]),
        ],
        back=True,
        reactive=_reactive_from_character(character, scene="travel"),
    )


def build_arcade_detail_view(cabinet):
    """Return a descriptive inspect view for one local arcade cabinet."""

    paragraphs = [line.strip() for line in str(getattr(getattr(cabinet, "db", None), "desc", "") or "").splitlines() if line.strip()]
    if not paragraphs:
        paragraphs = ["The cabinet hums softly, waiting for a coin and a steady hand."]

    return {
        **_make_view(
            "",
            _display_name(cabinet),
            eyebrow_icon=None,
            title_icon="sports_esports",
            subtitle="",
            sections=[
                _section(
                    "",
                    "menu_book",
                    "lines",
                    lines=paragraphs,
                    hide_label=True,
                )
            ],
            actions=[_action("Play", f"arcade open {cabinet.key}", "sports_esports", tone="accent")],
            back=True,
            reactive=_reactive_view(getattr(cabinet, "location", None), scene="read"),
        ),
        "variant": "read",
    }


def build_arcade_play_view(character, cabinet, game_key):
    """Return a browser-first play view for one arcade game."""

    definition = ARCADE_GAMES[game_key]
    reward = get_reward_definition(cabinet, game_key)
    leaderboard = cabinet.get_leaderboard(game_key)
    high_score = 0
    if leaderboard:
        try:
            high_score = max(0, int((leaderboard[0] or {}).get("score", 0) or 0))
        except (TypeError, ValueError):
            high_score = 0
    chips = [
        _chip(f"Best {format_arcade_score(get_personal_best(character, cabinet, game_key))}", "military_tech", "muted"),
    ]
    if reward.get("threshold", 0) and reward.get("item_name"):
        if has_arcade_reward(character, cabinet, game_key):
            chips.append(_chip(f"Prize Claimed: {reward['item_name']}", "workspace_premium", "good"))
        else:
            chips.append(
                _chip(f"Prize {format_arcade_score(reward['threshold'])}: {reward['item_name']}", "workspace_premium", "accent")
            )

    return {
        **_make_view(
            _display_name(cabinet),
            definition["name"],
            eyebrow_icon="sports_esports",
            title_icon="videogame_asset",
            chips=chips,
            sections=[
                _section(
                    "Cabinet Screen",
                    "sports_esports",
                    "arcade",
                    lines=[],
                    span="mapwide",
                    game_key=game_key,
                    high_score=high_score,
                    best_score=get_personal_best(character, cabinet, game_key),
                ),
            ],
            actions=[_action("Quit", "arcade quit", "close", tone="muted")],
            reactive=_reactive_from_character(character, scene="arcade"),
        ),
        "variant": "arcade",
    }


from world.browser_combat_views import build_combat_view


def build_combat_victory_view(
    encounter,
    character,
    *,
    xp_total,
    reward_silver=0,
    reward_items=None,
    progress_messages=None,
    remote=False,
    party_size=1,
):
    """Return a browser-first victory screen for completed encounters."""

    reward_items = reward_items or []
    raw_progress_messages = [message for message in (progress_messages or []) if message]

    # 1. Extract quest rewards from progress messages so Victory does not
    # show the same reward information in two different sections.
    quest_xp = 0
    quest_silver = 0
    quest_reward_items = []
    filtered_messages = []
    
    import re
    xp_pattern = re.compile(r"^\s*you\s+gain\s+(?:\|w)?(\d+)(?:\|n)?\s+xp\.?\s*$", re.IGNORECASE)
    silver_pattern = re.compile(r"^\s*you\s+receive\s+(?:\|w)?(\d+)(?:\|n)?\s+silver\.?\s*$", re.IGNORECASE)
    item_reward_pattern = re.compile(
        r"^\s*you\s+receive\s+(?:\|w)?(.+?)(?:\|n)?(?:\s+x(\d+))?\.?\s*$",
        re.IGNORECASE,
    )
    item_names = {
        str(template.get("name") or template_id).strip().lower(): template_id
        for template_id, template in ITEM_TEMPLATES.items()
    }

    for msg in raw_progress_messages:
        lowered = msg.lower()
        xp_match = xp_pattern.search(lowered)
        if xp_match:
            quest_xp += int(xp_match.group(1))
            continue
        silver_match = silver_pattern.search(lowered)
        if silver_match:
            quest_silver += int(silver_match.group(1))
            continue

        item_match = item_reward_pattern.search(str(msg or ""))
        if item_match:
            item_name = re.sub(r"\|[a-zA-Z]", "", item_match.group(1) or "").strip().lower()
            template_id = item_names.get(item_name)
            if template_id:
                quest_reward_items.append((template_id, int(item_match.group(2) or 1)))
                continue
        
        # Filter out purely informational tracking messages that are redundant on Victory
        if "tracked quest:" in lowered:
            continue
            
        filtered_messages.append(msg)

    # 2. Consolidate Quest Progress by Title
    # quest_states: { title: { 'latest_progress': str, 'completed': bool, 'new': bool, 'leads': [str] } }
    quest_states = {}
    other_messages = []
    
    for msg in filtered_messages:
        if ":" in msg:
            prefix, detail = [part.strip() for part in msg.split(":", 1)]
            prefix_lowered = prefix.lower()
        else:
            prefix, detail = "", msg
            prefix_lowered = ""

        if prefix_lowered == "quest updated":
            title = detail.split(" - ")[0] if " - " in detail else detail
            state = quest_states.setdefault(title, {"completed": False, "new": False, "leads": []})
            state["latest_progress"] = detail
        elif prefix_lowered == "quest complete":
            state = quest_states.setdefault(detail, {"completed": False, "new": False, "leads": []})
            state["completed"] = True
        elif prefix_lowered == "new quest":
            state = quest_states.setdefault(detail, {"completed": False, "new": False, "leads": []})
            state["new"] = True
        elif prefix_lowered in {"lead", "next lead"}:
            continue
        else:
            other_messages.append(msg)

    # Reconstruct consolidated progress messages
    consolidated_entries = []
    for title, state in quest_states.items():
        lines = []
        if state["completed"]:
            meta = "Quest Complete"
            icon = "task_alt"
            display_title = title
        elif state["new"]:
            meta = "New Quest"
            icon = "flag"
            display_title = title
            lines.append("A new thread is ready to follow.")
        else:
            meta = "Quest Updated"
            icon = "assignment"
            display_title = state.get("latest_progress", title)
        
        lines.extend(state["leads"])
        consolidated_entries.append(_entry(display_title, meta=meta, icon=icon, lines=lines))

    level_up_messages = [message for message in other_messages if "you are now level" in message.lower()]
    companion_reward_messages = [message for message in other_messages if " bond +" in message.lower()]
    final_other_messages = [
        message for message in other_messages 
        if message not in level_up_messages and message not in companion_reward_messages
    ]
    
    is_capstone = (getattr(encounter.db, "encounter_title", "") or "").strip().lower() == "the hollow lantern"

    reward_pairs = [
        _pair("XP Earned", xp_total + quest_xp, "auto_awesome"),
        _pair("Silver", (reward_silver or 0) + quest_silver, "savings"),
    ]

    for message in companion_reward_messages:
        text = str(message or "").strip().rstrip(".")
        lowered = text.lower()
        split_index = lowered.find(" bond +")
        if split_index > 0:
            companion_name = text[:split_index].strip()
            bond_gain = text[split_index + 6 :].strip()
            reward_pairs.append(_pair(f"{companion_name} Bond", bond_gain, "pets"))
        else:
            reward_pairs.append(_pair("Companion Bond", text, "pets"))

    loot_items_list = []
    merged_loot_items = {}
    for template_id, quantity in list(reward_items) + quest_reward_items:
        merged_loot_items[template_id] = merged_loot_items.get(template_id, 0) + int(quantity or 0)

    for template_id, quantity in merged_loot_items.items():
        if quantity <= 0:
            continue
        template = ITEM_TEMPLATES.get(template_id, {})
        item_name = template.get("name", template_id.replace("_", " ").title())
        kind = template.get("kind")
        icon = {
            "meal": "restaurant",
            "ingredient": "kitchen",
            "equipment": "checkroom",
        }.get(kind, "category")
        text = f"{item_name} x{quantity}" if quantity > 1 else item_name
        loot_items_list.append(_item(text, icon=icon, **build_item_rarity_display(template)))
    
    sections = [
        _section(
            "Rewards",
            "workspace_premium",
            "pairs",
            items=reward_pairs,
            variant="receipt",
        )
    ]
    
    if is_capstone:
        sections.append(
            _section(
                "Chapter Close",
                "emoji_events",
                "lines",
                lines=[
                    "The drowned weir is quiet.",
                    "The south light is finally dark.",
                    "Brambleford gets to take the win home.",
                ],
                variant="receipt",
            )
        )
    
    if loot_items_list:
        sections.append(_section("Recovered Loot", "inventory_2", "list", items=loot_items_list, variant="receipt"))
    
    if level_up_messages:
        sections.append(_section("LEVEL UP", "north", "lines", lines=level_up_messages, variant="receipt"))
    
    progress_items = consolidated_entries + [
        _entry(msg, meta="Progress", icon="task_alt") for msg in final_other_messages
    ]
    
    if progress_items:
        sections.append(
            _section(
                "Chapter Progress" if is_capstone else "Progress",
                "flag",
                "entries",
                items=progress_items,
                variant="receipt",
            )
        )

    return {
        **_make_view(
            "",
            "VICTORY",
            eyebrow_icon=None,
            title_icon="military_tech",
            sections=sections,
            actions=[_action("Continue", "look", None, tone="accent", no_icon=True)],
            reactive=_reactive_view(
                encounter.obj,
                scene="victory",
                danger="safe",
                boss=is_capstone,
            ),
        ),
        "variant": "combat-result",
    }


def build_combat_defeat_view(
    character,
    *,
    recovery_room=None,
    silver_lost=0,
    tutorial=False,
    can_rest=False,
):
    """Return a browser-first defeat screen for combat recovery."""

    recovery_name = getattr(recovery_room, "key", None) or "safety"
    subtitle = (
        f"You are carried back to {recovery_name}, barely standing. Rest before you try again."
        if tutorial
        else f"You are carried back to {recovery_name}, barely standing. Rest before heading out again."
    )
    outcome_pairs = [
        _pair("HP", "1", "favorite"),
        _pair("Mana", "1", "auto_awesome"),
        _pair("Stamina", "1", "bolt"),
        _pair("Silver Lost", silver_lost, "savings"),
    ]
    sections = [
        _section(
            "Recovery",
            "healing",
            "pairs",
            items=outcome_pairs,
            variant="receipt",
        ),
        _section(
            "Next Step",
            "campfire",
            "lines",
            lines=[
                "Rest here to refill HP, mana, and stamina.",
                "Your progress is intact. The road can wait until you are ready.",
            ],
            variant="receipt",
        ),
    ]
    actions = []
    if can_rest:
        actions.append(_action("Rest", "rest", "campfire", tone="accent"))
    actions.append(_action("Continue", "look", None, tone="muted", no_icon=True))

    return {
        **_make_view(
            "",
            "DEFEATED",
            eyebrow_icon=None,
            title_icon="shield",
            subtitle=subtitle,
            sections=sections,
            actions=actions,
            reactive=_reactive_from_character(character, scene="defeat", danger="safe"),
        ),
        "variant": "combat-result",
    }


from world.browser_character_views import build_sheet_view


from world.browser_room_views import build_room_view
