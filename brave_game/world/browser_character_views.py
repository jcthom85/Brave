"""Character-focused browser view payload builders for Brave."""

import world.browser_views as browser_views
from world.character_icons import get_class_icon, get_race_icon
from world.class_features import get_class_features
from world.druid_forms import get_druid_form
from world.genders import get_brave_gender_label
from world.resonance import (
    get_resource_label,
    get_stat_label,
)
from world.browser_views import (
    ABILITY_LIBRARY,
    CHARACTER_CONTENT,
    CLASSES,
    PASSIVE_ABILITY_BONUSES,
    RACES,
    _build_sheet_ability_item,
    _build_sheet_passive_item,
    _chip,
    _entry,
    _hp_meter_tone,
    _item,
    _make_view,
    _meter,
    _pair,
    _reactive_from_character,
    _section,
    ability_key,
    xp_needed_for_next_level,
)


def build_sheet_view(character):
    """Return a browser-first main view for the character sheet."""

    race = RACES[character.db.brave_race]
    class_data = CLASSES[character.db.brave_class]
    level = character.db.brave_level
    primary = character.db.brave_primary_stats or {}
    derived = character.db.brave_derived_stats or {}
    resources = character.db.brave_resources or {}
    class_actions, passives, unknown_abilities = browser_views.split_unlocked_abilities(character.db.brave_class, level)
    get_unlocked = getattr(character, "get_unlocked_abilities", None)
    if callable(get_unlocked):
        unlocked_names = list(get_unlocked())
        actions = [
            ability_name
            for ability_name in unlocked_names
            if ability_key(ability_name) in ABILITY_LIBRARY and ability_key(ability_name) in CHARACTER_CONTENT.implemented_ability_keys
        ]
        if not actions:
            actions = list(class_actions)
    else:
        actions = list(class_actions)
    next_level_xp = xp_needed_for_next_level(level)
    current_xp = character.db.brave_xp or 0
    xp_meter_max = next_level_xp or max(1, current_xp)
    xp_meter_value = min(current_xp, xp_meter_max)
    resonance_key = browser_views.get_resonance_key(character)
    resonance_label = browser_views.get_resonance_label(character)

    meal_buff = character.db.brave_meal_buff or {}
    blessing = browser_views.get_active_blessing(character)

    combat_pairs = [
        _pair(get_stat_label("attack_power", character), derived.get("attack_power", 0), "swords"),
        _pair(get_stat_label("spell_power", character), derived.get("spell_power", 0), "auto_awesome"),
        _pair(get_stat_label("armor", character), derived.get("armor", 0), "shield"),
        _pair(get_stat_label("accuracy", character), derived.get("accuracy", 0), "near_me"),
        _pair(get_stat_label("dodge", character), derived.get("dodge", 0), "air"),
    ]
    if derived.get("precision", 0):
        combat_pairs.append(_pair(get_stat_label("precision", character), derived["precision"], "location_searching"))
    if derived.get("threat", 0):
        combat_pairs.append(_pair(get_stat_label("threat", character), derived["threat"], "warning"))

    status_entry = _entry(
        character.key,
        meta=f"{race['name']} {class_data['name']} · Level {level}",
        lines=[class_data["summary"]],
        icon=get_class_icon(character.db.brave_class, class_data),
        chips=[
            _chip(get_brave_gender_label(getattr(character.db, "brave_gender", None), default="Non-binary"), "person", "muted"),
            _chip(race["name"], get_race_icon(character.db.brave_race, race), "muted"),
            *(
                [_chip(resonance_label, "travel_explore", "accent")]
                if resonance_key != "fantasy"
                else []
            ),
        ],
        meters=[
            _meter(
                get_resource_label("hp", character),
                resources.get("hp", 0),
                derived.get("max_hp", 0),
                tone=_hp_meter_tone(resources.get("hp", 0), derived.get("max_hp", 0)),
            ),
            _meter(
                get_resource_label("mana", character),
                resources.get("mana", 0),
                derived.get("max_mana", 0),
                tone="mana",
            ),
            _meter(
                get_resource_label("stamina", character),
                resources.get("stamina", 0),
                derived.get("max_stamina", 0),
                tone="stamina",
            ),
            _meter(
                "XP",
                xp_meter_value,
                xp_meter_max,
                tone="xp",
                value="Level Cap" if not next_level_xp else f"{current_xp} / {next_level_xp}",
            ),
        ],
    )

    sections = [
        _section(
            "",
            "person",
            "entries",
            items=[status_entry],
            hide_label=True,
            span="wide",
            variant="status",
        ),
        _section(
            "Build",
            "bar_chart",
            "pairs",
            items=[
                _pair(get_stat_label("strength", character), primary.get("strength", 0), "construction"),
                _pair(get_stat_label("agility", character), primary.get("agility", 0), "air"),
                _pair(get_stat_label("intellect", character), primary.get("intellect", 0), "school"),
                _pair(get_stat_label("spirit", character), primary.get("spirit", 0), "auto_awesome"),
                _pair(get_stat_label("vitality", character), primary.get("vitality", 0), "favorite"),
            ],
            variant="stats",
        ),
        _section("Combat", "tune", "pairs", items=combat_pairs, variant="stats"),
        _section(
            "Class",
            "military_tech",
            "entries",
            items=[
                _entry(
                    feature["name"],
                    lines=[feature["summary"]],
                    icon=feature.get("icon", "star"),
                )
                for feature in get_class_features(character.db.brave_class)
            ]
            or [_entry("No class feature notes found.", icon="info")],
            variant="abilities",
        ),
        _section(
            "Abilities",
            "bolt",
            "list",
            items=[_build_sheet_ability_item(character, ability) for ability in actions]
            or [_item("No unlocked combat actions yet.", icon="info")],
            variant="abilities",
        ),
    ]

    if character.db.brave_class == "ranger":
        active_companion = dict(getattr(character, "get_active_companion", lambda: {})() or {})
        unlocked_companions = list(getattr(character, "get_unlocked_companions", lambda: [])() or [])
        sections.insert(
            4,
            _section(
                "Companion",
                "pets",
                "entries",
                items=[
                    _entry(
                        active_companion.get("name", "No active companion"),
                        meta="Active Bond",
                        lines=[
                            active_companion.get("summary", "No bonded companion is currently set."),
                            active_companion.get("bond_label", "Bond 1"),
                            (
                                "Bond XP capped"
                                if (active_companion.get("bond", {}) or {}).get("at_cap")
                                else f"{(active_companion.get('bond', {}) or {}).get('xp_to_next', 0)} XP to next bond"
                            ),
                            f"Unlocked companions: {len(unlocked_companions)}",
                        ],
                        icon=active_companion.get("icon", "pets"),
                    )
                ],
                variant="abilities",
            ),
        )
    elif character.db.brave_class == "paladin":
        active_oath = dict(getattr(character, "get_active_oath", lambda: {})() or {})
        unlocked_oaths = list(getattr(character, "get_unlocked_oaths", lambda: [])() or [])
        sections.insert(
            4,
            _section(
                "Sacred Oath",
                "military_tech",
                "entries",
                items=[
                    _entry(
                        active_oath.get("name", "No active oath"),
                        meta="Active Vigil",
                        lines=[
                            active_oath.get("summary", "No sacred oath is currently guiding your vigil."),
                            f"Sworn oaths: {len(unlocked_oaths)}",
                        ],
                        icon="military_tech",
                    )
                ],
                variant="abilities",
            ),
        )
    elif character.db.brave_class == "rogue":
        theft_log = list(getattr(character, "get_rogue_theft_log", lambda: [])() or [])
        latest = theft_log[-1] if theft_log else {}
        sections.insert(
            4,
            _section(
                "Illicit Access",
                "key",
                "entries",
                items=[
                    _entry(
                        "Worked Angles",
                        meta="Rogue-exclusive theft ledger",
                        lines=[
                            f"Worked marks: {len(theft_log)}",
                            f"Latest lift: {latest['target']}" if latest.get("target") else "No theft angles worked yet.",
                        ],
                        icon="key",
                    )
                ],
                variant="abilities",
            ),
        )
    elif character.db.brave_class == "druid":
        unlocked_form_names = [
            ability_name
            for ability_name in actions
            if ability_key(ability_name) in {"wolfform", "bearform", "crowform", "serpentform"}
        ]
        form_items = []
        for ability_name in unlocked_form_names:
            form = get_druid_form(ability_key(ability_name).replace("form", ""))
            form_items.append(
                _entry(
                    form.get("name", ability_name),
                    meta="Unlocked Form",
                    lines=[form.get("summary", ABILITY_LIBRARY.get(ability_key(ability_name), {}).get("summary", ""))],
                    icon="forest",
                )
            )
        sections.insert(
            4,
            _section(
                "Primal Forms",
                "forest",
                "entries",
                items=form_items or [_entry("No primal forms unlocked.", icon="info")],
                variant="abilities",
            ),
        )

    passive_items = [
        _build_sheet_passive_item(
            character,
            race["perk"],
            icon_name="star_outline",
            summary_line=race.get("perk_summary") or race["summary"],
            bonus_map=race.get("perk_bonuses", {}),
        )
    ]
    passive_items.extend(
        _build_sheet_passive_item(
            character,
            ability,
            icon_name="passive",
            bonus_map=PASSIVE_ABILITY_BONUSES.get(ability_key(ability), {}).get("bonuses", {}),
        )
        for ability in passives
    )

    if passive_items:
        sections.append(
            _section(
                "Traits",
                "auto_awesome",
                "list",
                items=passive_items,
                variant="abilities",
            )
        )

    effect_entries = []
    if meal_buff:
        meal_lines = []
        meal_bonus_text = browser_views._format_context_bonus_summary(character.get_active_meal_bonuses(), character)
        if meal_bonus_text:
            meal_lines.append("Bonuses: " + meal_bonus_text)
        effect_entries.append(
            _entry(
                meal_buff.get("name", "Meal Buff"),
                meta="Meal Buff",
                icon="restaurant",
                lines=meal_lines or ["A prepared meal is currently strengthening you."],
                chips=[_chip("Cozy", "night_shelter", "good")] if meal_buff.get("cozy") else [],
            )
        )

    if blessing:
        blessing_lines = [blessing.get("duration", "Until your next encounter ends.")]
        blessing_bonus_text = browser_views._format_context_bonus_summary(blessing.get("bonuses", {}), character)
        if blessing_bonus_text:
            blessing_lines.append("Bonuses: " + blessing_bonus_text)
        if (blessing.get("rite") or {}).get("name"):
            blessing_lines.append("Rite: " + blessing["rite"]["name"])
        effect_entries.append(
            _entry(
                blessing.get("name", "Blessing"),
                meta="Blessing",
                icon="wb_sunny",
                lines=blessing_lines,
            )
        )

    if resonance_key != "fantasy":
        effect_entries.append(
            _entry(
                resonance_label,
                meta="Resonance",
                icon="travel_explore",
                lines=[
                    "This world renames your abilities and resource labels, but your core build remains the same.",
                ],
            )
        )

    if unknown_abilities:
        effect_entries.append(
            _entry(
                "Progression Notes",
                meta="Unclassified",
                icon="info",
                lines=[", ".join(unknown_abilities)],
            )
        )

    if effect_entries:
        sections.append(
            _section(
                "Effects",
                "wb_sunny",
                "entries",
                items=effect_entries,
                span="wide",
                variant="effects",
            )
        )

    return {
        **_make_view(
            "",
            "Character Sheet",
            eyebrow_icon=None,
            title_icon="person",
            subtitle="",
            chips=[],
            sections=sections,
            back=True,
            reactive=_reactive_from_character(character, scene="character"),
        ),
        "variant": "sheet",
    }
