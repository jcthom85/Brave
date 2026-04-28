"""Profile, build, inventory, and journal commands extracted from Brave's helper module."""

import re

from world.browser_panels import (
    build_build_panel,
    build_gear_panel,
    build_pack_panel,
    build_quests_panel,
    build_sheet_panel,
    send_webclient_event,
)
from world.browser_views import build_gear_view, build_pack_view, build_quests_view, build_sheet_view
from world.chapel import get_active_blessing
from world.content import get_content_registry
from world.mastery import (
    MASTERY_RESPEC_SILVER_COST,
    build_mastery_payload,
    can_train_ability,
    format_mastery_name,
    get_next_mastery_text,
    is_mastery_room,
    mastery_rank_label,
)
from world.questing import (
    clear_tracked_quest,
    get_tracked_quest,
    resolve_active_quest_query,
    set_tracked_quest,
)
from world.ranger_companions import get_companion_name
from world.resonance import (
    format_ability_display,
    get_resonance_key,
    get_resonance_label,
    get_resource_label,
    get_stat_label,
)
from world.screen_text import format_entry, format_pairs, render_screen, wrap_text
from world.tutorial import ensure_tutorial_state, record_command_event

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
ITEM_CONTENT = CONTENT.items
QUEST_CONTENT = CONTENT.quests

from .brave import (
    BraveCharacterCommand,
    PACK_KIND_LABELS,
    PACK_KIND_ORDER,
    _format_context_bonus_summary,
    _format_equipment_totals,
    _format_equipped_item_entry,
    _format_inventory_entry,
    _format_quest_screen_block,
    _format_tutorial_screen_block,
    _stack_blocks,
    _wrap_paragraphs,
)


_EVENNIA_MARKUP_RE = re.compile(r"\|[A-Za-z]")


def _strip_evennia_markup(text):
    """Remove lightweight Evennia color markup for browser overlay status text."""

    clean = str(text or "").replace("||", "|")
    return _EVENNIA_MARKUP_RE.sub("", clean)


def _send_mastery_payload(command, character, payload):
    """Send a mastery overlay payload to the current web session."""

    session = command.get_web_session()
    if not session or not payload:
        return False
    send_webclient_event(character, session=session, brave_mastery=payload)
    return True


def _refresh_mastery_scene(command, character, message=None, *, success=False):
    """Keep browser-based mastery actions inside the mastery overlay."""

    if not command.get_web_session():
        return False
    _send_mastery_payload(
        command,
        character,
        build_mastery_payload(
            character,
            status_message=_strip_evennia_markup(message),
            status_tone="good" if success else "muted",
        ),
    )
    if message:
        command.send_other_sessions(message)
    return True


def _get_journal_mode(character):
    mode = getattr(getattr(character, "db", None), "brave_journal_tab", "active")
    return mode if mode in {"active", "completed"} else "active"


def _set_journal_mode(character, mode):
    character.db.brave_journal_tab = "completed" if mode == "completed" else "active"
    if mode != "completed":
        character.db.brave_journal_expanded_completed = None


def _get_expanded_completed_quest(character):
    value = getattr(getattr(character, "db", None), "brave_journal_expanded_completed", None)
    return value or None


def _set_expanded_completed_quest(character, quest_key=None):
    character.db.brave_journal_expanded_completed = quest_key or None


def _normalize_query(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _resolve_completed_quest_query(character, query):
    completed_keys = [
        quest_key
        for quest_key in QUEST_CONTENT.starting_quests
        if (character.db.brave_quests or {}).get(quest_key, {}).get("status") == "completed"
    ]
    token = "".join(char for char in (query or "").lower() if char.isalnum())
    if not token:
        return None

    if token.isdigit():
        index = int(token) - 1
        if 0 <= index < len(completed_keys):
            return completed_keys[index]

    title_map = {
        quest_key: "".join(char for char in QUEST_CONTENT.quests[quest_key]["title"].lower() if char.isalnum())
        for quest_key in completed_keys
    }

    for quest_key in completed_keys:
        if token == quest_key.lower() or token == title_map[quest_key]:
            return quest_key

    startswith_matches = [quest_key for quest_key in completed_keys if title_map[quest_key].startswith(token)]
    if len(startswith_matches) == 1:
        return startswith_matches[0]

    contains_matches = [quest_key for quest_key in completed_keys if token in title_map[quest_key]]
    if len(contains_matches) == 1:
        return contains_matches[0]

    return None


class CmdBuild(BraveCharacterCommand):
    """
    View or plan your starting build.

    Usage:
      build

    Shows your current race and class along with the currently playable class options.
    """

    key = "build"
    aliases = ["origin", "choices"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        race = CHARACTER_CONTENT.races[character.db.brave_race]
        class_data = CHARACTER_CONTENT.classes[character.db.brave_class]
        race_blocks = [
            format_entry(f"{race_data['name']} · {race_data['perk']}", summary=race_data["summary"])
            for race_data in CHARACTER_CONTENT.races.values()
        ]
        class_blocks = [
            format_entry(
                f"{CHARACTER_CONTENT.classes[class_key]['name']} · {CHARACTER_CONTENT.classes[class_key]['role']}",
                summary=CHARACTER_CONTENT.classes[class_key]["summary"],
            )
            for class_key in CHARACTER_CONTENT.vertical_slice_classes
        ]

        screen = render_screen(
            "Build Planner",
            subtitle=class_data["summary"],
            meta=[
                f"Race {race['name']}",
                f"Class {class_data['name']}",
                "Build open" if character.can_customize_build() else "Build locked",
            ],
            sections=[
                (
                    "Current Build",
                    format_pairs(
                        [
                            ("Race", race["name"]),
                            ("Class", class_data["name"]),
                            ("Perk", race["perk"]),
                            ("Role", class_data["role"]),
                            ("Can change", "Yes" if character.can_customize_build() else "No"),
                        ]
                    ),
                ),
                ("Race Options", _stack_blocks(race_blocks)),
                ("Class Options", _stack_blocks(class_blocks)),
                (
                    "Next Steps",
                    [
                        *wrap_text(
                            "Use |wrace <name>|n or |wclass <name>|n before you start leveling.",
                            indent="  ",
                        ),
                        *wrap_text(
                            "Use |wgear|n after choosing a class to inspect your issued kit.",
                            indent="  ",
                        ),
                    ],
                ),
            ],
        )
        self.scene_msg(screen, panel=build_build_panel(character))


class CmdRace(BraveCharacterCommand):
    """
    Change your starting race.

    Usage:
      race <name>

    Sets your race while you are still in the early build-customization window.
    """

    key = "race"
    aliases = ["heritage"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("Usage: race <name>")
            return
        if not character.can_customize_build():
            self.msg("Your origin is already set. New changes should come from progression, not rerolling.")
            return

        query = self.args.strip().lower().replace("-", "_").replace(" ", "_")
        matches = [key for key, data in CHARACTER_CONTENT.races.items() if query in (key, data["name"].lower().replace(" ", "_"))]
        if not matches:
            self.msg("Unknown race. Use |wbuild|n to see available races.")
            return

        race_key = matches[0]
        character.set_brave_race(race_key)
        self.msg(f"Your race is now |w{CHARACTER_CONTENT.races[race_key]['name']}|n.")


class CmdClass(BraveCharacterCommand):
    """
    Change your starting class.

    Usage:
      class <name>

    Sets your class while you are still in the early build-customization window.
    """

    key = "class"
    aliases = ["calling", "profession"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("Usage: class <name>")
            return
        if not character.can_customize_build():
            self.msg("Your starting class is already locked in by play progression.")
            return

        query = self.args.strip().lower().replace("-", "_").replace(" ", "_")
        matches = [
            class_key
            for class_key in CHARACTER_CONTENT.vertical_slice_classes
            if query in (class_key, CHARACTER_CONTENT.classes[class_key]["name"].lower().replace(" ", "_"))
        ]
        if not matches:
            choices = ", ".join(CHARACTER_CONTENT.classes[class_key]["name"] for class_key in CHARACTER_CONTENT.vertical_slice_classes)
            self.msg(f"Playable classes right now are: {choices}")
            return

        class_key = matches[0]
        character.set_brave_class(class_key)
        self.msg(f"Your class is now |w{CHARACTER_CONTENT.classes[class_key]['name']}|n. Your starter gear shifts to match.")


class CmdSheet(BraveCharacterCommand):
    """
    View your current adventurer sheet.

    Usage:
      sheet

    Shows your race, class, level, resources, stats, combat actions, and passive traits.
    """

    key = "sheet"
    aliases = ["stats", "whoami"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        race = CHARACTER_CONTENT.races[character.db.brave_race]
        class_data = CHARACTER_CONTENT.classes[character.db.brave_class]
        primary = character.db.brave_primary_stats
        derived = character.db.brave_derived_stats
        resources = character.db.brave_resources
        active_abilities, passive_abilities, unknown_abilities = CHARACTER_CONTENT.split_unlocked_abilities(
            character.db.brave_class,
            character.db.brave_level,
        )
        next_level_xp = CHARACTER_CONTENT.xp_needed_for_next_level(character.db.brave_level)
        resonance_key = get_resonance_key(character)
        resonance_label = get_resonance_label(character)

        xp_line = (
            f"{character.db.brave_xp} / {next_level_xp} XP"
            if next_level_xp
            else f"{character.db.brave_xp} XP (level cap)"
        )

        combat_pairs = [
            ("Attack", derived["attack_power"]),
            ("Spell", derived["spell_power"]),
            ("Armor", derived["armor"]),
            ("Accuracy", derived["accuracy"]),
            ("Dodge", derived["dodge"]),
        ]
        if derived.get("precision", 0):
            combat_pairs.append(("Precision", derived["precision"]))
        if derived.get("threat", 0):
            combat_pairs.append(("Threat", derived["threat"]))

        sections = [
            (
                "Overview",
                format_pairs(
                    [
                        ("Race", race["name"]),
                        ("Class", class_data["name"]),
                        ("Perk", race["perk"]),
                        ("Role", class_data["role"]),
                        ("XP", xp_line),
                        ("Silver", character.db.brave_silver),
                        ("Resonance", resonance_label),
                    ]
                ),
            ),
            (
                "Resources",
                format_pairs(
                    [
                        (
                            get_resource_label("hp", character),
                            f"{resources['hp']} / {derived['max_hp']}",
                        ),
                        (
                            get_resource_label("mana", character),
                            f"{resources['mana']} / {derived['max_mana']}",
                        ),
                        (
                            get_resource_label("stamina", character),
                            f"{resources['stamina']} / {derived['max_stamina']}",
                        ),
                    ]
                ),
            ),
            (
                "Primary Stats",
                format_pairs(
                    [
                        (get_stat_label(stat, character), primary[stat])
                        for stat in ("strength", "agility", "intellect", "spirit", "vitality")
                    ]
                ),
            ),
            ("Combat Stats", format_pairs(combat_pairs)),
            (
                "Combat Actions",
                [
                    "  "
                    + format_mastery_name(
                        format_ability_display(ability, character),
                        getattr(character, "get_ability_mastery_rank", lambda _key: 1)(CHARACTER_CONTENT.ability_key(ability)),
                    )
                    for ability in active_abilities
                ]
                if active_abilities
                else ["  None yet"],
            ),
        ]

        if passive_abilities:
            sections.append(
                (
                    "Passive Traits",
                    [f"  {format_ability_display(ability, character)}" for ability in passive_abilities],
                )
            )

        if unknown_abilities:
            sections.append(("Progression Notes", [f"  Unclassified: {', '.join(unknown_abilities)}"]))

        meal_buff = character.db.brave_meal_buff or {}
        if meal_buff:
            meal_details = [
                meal_buff.get("name", "Meal")
                + (" [Cozy]" if meal_buff.get("cozy") else "")
            ]
            meal_bonus_text = _format_context_bonus_summary(character.get_active_meal_bonuses(), character)
            if meal_bonus_text:
                meal_details.append("Bonuses: " + meal_bonus_text)
            meal_lines = []
            for detail in meal_details:
                meal_lines.extend(wrap_text(detail, indent="  "))
            sections.append(("Meal Buff", meal_lines))

        blessing = get_active_blessing(character)
        if blessing:
            blessing_lines = _wrap_paragraphs(blessing.get("duration", "Until your next encounter ends."))
            blessing_bonus_text = _format_context_bonus_summary(blessing.get("bonuses", {}), character)
            if blessing_bonus_text:
                blessing_lines.extend(wrap_text("Bonuses: " + blessing_bonus_text, indent="  "))
            sections.append(("Blessing", blessing_lines))

        if resonance_key != "fantasy":
            sections.append(
                (
                    "Resonance Note",
                    wrap_text(
                        "This world renames your abilities and resource labels, but your core build remains the same.",
                        indent="  ",
                    ),
                )
            )

        screen = render_screen(
            character.key,
            subtitle=f"{race['name']} {class_data['name']} · Level {character.db.brave_level}",
            meta=[class_data["summary"]],
            sections=sections,
        )
        self.scene_msg(screen, panel=build_sheet_panel(character), view=build_sheet_view(character))
        record_command_event(character, "sheet")


class CmdMastery(BraveCharacterCommand):
    """
    Review or train combat ability mastery.

    Usage:
      mastery
      mastery <ability>
      mastery respec

    Shows your current combat-ability mastery ranks anywhere. Training and respec
    require the Brambleford mastery trainer.
    """

    key = "mastery"
    aliases = ["train", "master"]
    help_category = "Brave"

    def _resolve_ability(self, character, query):
        token = _normalize_query(query)
        if not token:
            return None
        exact = []
        partial = []
        for ability_name in getattr(character, "get_unlocked_combat_abilities", lambda: [])():
            ability_key = CHARACTER_CONTENT.ability_key(ability_name)
            display = format_ability_display(ability_name, character)
            candidates = {
                _normalize_query(ability_name),
                _normalize_query(display),
                _normalize_query(ability_key),
            }
            if token in candidates:
                exact.append((ability_key, ability_name))
            elif any(token in candidate for candidate in candidates):
                partial.append((ability_key, ability_name))
        matches = exact or partial
        if len(matches) == 1:
            return matches[0]
        return matches

    def func(self):
        character = self.get_character()
        if not character:
            return

        in_mastery_room = is_mastery_room(character.location)
        earned = getattr(character, "get_earned_mastery_points", lambda: 0)()
        spent = getattr(character, "get_spent_mastery_points", lambda: 0)()
        available = getattr(character, "get_available_mastery_points", lambda: 0)()

        if self.args:
            token = _normalize_query(self.args)
            if token in {"respec", "reset"}:
                if not in_mastery_room:
                    message = "You need to visit the mastery trainer in Brambleford before you can reset your focus."
                    if _refresh_mastery_scene(self, character, message, success=False):
                        return
                    self.msg(message)
                    return
                ok, message = character.reset_ability_mastery()
                if _refresh_mastery_scene(self, character, message, success=ok):
                    return
                self.msg(message)
                return

            match = self._resolve_ability(character, self.args)
            if isinstance(match, list):
                message = "Be more specific. That could mean: " + ", ".join(name for _key, name in match)
                if _refresh_mastery_scene(self, character, message, success=False):
                    return
                self.msg(message)
                return
            if not match:
                message = "No unlocked combat ability matches that name."
                if _refresh_mastery_scene(self, character, message, success=False):
                    return
                self.msg(message)
                return
            ability_key, ability_name = match
            if not in_mastery_room:
                message = "You need to be in Brambleford's Mastery Hall to train an ability."
                if _refresh_mastery_scene(self, character, message, success=False):
                    return
                self.msg(message)
                return
            if not can_train_ability(character, ability_key):
                message = "That technique cannot be refined here yet."
                if _refresh_mastery_scene(self, character, message, success=False):
                    return
                self.msg(message)
                return
            ok, message = character.train_ability_mastery(ability_key)
            if ok:
                rank = getattr(character, "get_ability_mastery_rank", lambda _key: 1)(ability_key)
                label = mastery_rank_label(rank)
                display_name = format_ability_display(ability_name, character)
                message = f"{message} {format_mastery_name(display_name, rank)} is now {label.lower()}."
                if _refresh_mastery_scene(self, character, message, success=True):
                    return
                self.msg(message)
            else:
                if _refresh_mastery_scene(self, character, message, success=False):
                    return
                self.msg(message)
            return

        if self.get_web_session():
            _send_mastery_payload(self, character, build_mastery_payload(character))
            return

        blocks = []
        for ability_name in getattr(character, "get_unlocked_combat_abilities", lambda: [])():
            ability_key = CHARACTER_CONTENT.ability_key(ability_name)
            rank = getattr(character, "get_ability_mastery_rank", lambda _key: 1)(ability_key)
            details = [f"Rank {rank} · {mastery_rank_label(rank)}"]
            next_text = get_next_mastery_text(ability_key, rank)
            if next_text:
                details.append(next_text)
            elif can_train_ability(character, ability_key):
                details.append("This technique is already mastered.")
            blocks.append(
                format_entry(
                    format_mastery_name(format_ability_display(ability_name, character), rank),
                    details=details,
                    summary=(CHARACTER_CONTENT.ability_library.get(ability_key) or {}).get("summary"),
                )
            )

        if in_mastery_room:
            tips = [
                *wrap_text(f"Use |wmastery <ability>|n to raise one technique by one rank.", indent="  "),
                *wrap_text(
                    f"Use |wmastery respec|n to reset your mastery for |w{MASTERY_RESPEC_SILVER_COST}|n silver.",
                    indent="  ",
                ),
            ]
        else:
            tips = wrap_text(
                "Training requires Mistress Elira Thorne in the Mastery Hall north of the Brambleford Training Yard.",
                indent="  ",
            )

        screen = render_screen(
            "Ability Mastery",
            subtitle="Known techniques use I / II / III in menus while trained ranks are described in prose as trained or mastered.",
            meta=[
                f"{available} mastery point{'s' if available != 1 else ''} available",
                f"{spent} spent / {earned} earned",
                f"{character.db.brave_silver or 0} silver on hand",
            ],
            sections=[
                ("Techniques", _stack_blocks(blocks) if blocks else ["  No trainable combat techniques unlocked yet."]),
                ("Mastery Hall", tips),
            ],
        )
        self.scene_msg(screen, panel=build_sheet_panel(character), view=build_sheet_view(character))


class CmdGear(BraveCharacterCommand):
    """
    View and manage your currently equipped gear.

    Usage:
      gear
      gear equip <slot> <item>
      gear swap <slot> <item>
      gear unequip <slot>

    Shows your current kit and lets you equip, swap, or unequip items by slot.
    """

    key = "gear"
    aliases = ["equipment", "kit"]
    help_category = "Brave"

    def _render_gear(self, character, feedback=None):
        equipment = character.db.brave_equipment or {}
        slot_blocks = []
        for slot in ITEM_CONTENT.equipment_slots:
            template_id = equipment.get(slot)
            if template_id:
                slot_blocks.append(_format_equipped_item_entry(character, slot, template_id))
            else:
                slot_blocks.append(format_entry(f"{slot.replace('_', ' ').title()} · Empty", summary="Nothing equipped."))
        total_bonus_text = _format_context_bonus_summary(_format_equipment_totals(character), character)

        sections = [
            (
                "Slots",
                _stack_blocks(slot_blocks),
            )
        ]
        if total_bonus_text:
            sections.append(("Current Kit Bonus", wrap_text(total_bonus_text, indent="  ")))
        if feedback:
            sections.insert(0, ("Power Feedback", wrap_text(feedback, indent="  ")))

        screen = render_screen(
            "Equipment",
            sections=sections,
        )
        self.scene_msg(screen, panel=build_gear_panel(character), view=build_gear_view(character, feedback=feedback))
        record_command_event(character, "gear")

    def _resolve_slot(self, query):
        token = _normalize_query(query)
        for slot in ITEM_CONTENT.equipment_slots:
            if token in {slot, slot.replace("_", "")}:
                return slot
            if token == _normalize_query(slot.replace("_", " ")):
                return slot
        return None

    def _resolve_inventory_equipment(self, character, query, slot=None):
        token = _normalize_query(query)
        candidates = character.get_equippable_inventory(slot=slot)
        exact = [
            entry["template"]
            for entry in candidates
            if token in {
                _normalize_query(entry["template"]),
                _normalize_query(entry["name"]),
            }
        ]
        if exact:
            return exact[0]

        partial = [
            entry["template"]
            for entry in candidates
            if token and (
                token in _normalize_query(entry["template"])
                or token in _normalize_query(entry["name"])
            )
        ]
        return partial[0] if partial else None

    def _equip(self, character, slot_query, item_query):
        slot = self._resolve_slot(slot_query)
        if not slot:
            self.msg("Usage: gear equip <slot> <item>")
            return

        template_id = self._resolve_inventory_equipment(character, item_query, slot=slot)
        if not template_id:
            self.msg(f"You are not carrying any matching gear for {slot.replace('_', ' ').title()}.")
            return

        previous_derived = dict(character.db.brave_derived_stats or {})
        success, result = character.equip_inventory_item(template_id, slot=slot)
        if not success:
            self.msg(result)
            return

        equipped_name = ITEM_CONTENT.item_templates[result["equipped"]]["name"]
        replaced_id = result.get("replaced")
        if replaced_id:
            replaced_name = ITEM_CONTENT.item_templates[replaced_id]["name"]
            self.msg(f"You swap in |w{equipped_name}|n and stow |w{replaced_name}|n.")
        else:
            self.msg(f"You equip |w{equipped_name}|n.")
        current_derived = dict(character.db.brave_derived_stats or {})
        improved = []
        for stat in ("max_hp", "armor", "attack_power", "spell_power", "accuracy", "dodge", "max_stamina", "max_mana"):
            delta = int(current_derived.get(stat, 0) or 0) - int(previous_derived.get(stat, 0) or 0)
            if delta > 0:
                improved.append(f"+{delta} {get_stat_label(stat, character)}")
        if improved:
            feedback = "You feel the difference: " + ", ".join(improved[:4]) + "."
            self.msg("|g" + feedback + "|n")
        else:
            feedback = None
        record_command_event(character, "equip_gear")
        self._render_gear(character, feedback=feedback)

    def _unequip(self, character, slot_query):
        slot = self._resolve_slot(slot_query)
        if not slot:
            self.msg("Usage: gear unequip <slot>")
            return

        success, result = character.unequip_slot(slot)
        if not success:
            self.msg(result)
            return

        item_name = ITEM_CONTENT.item_templates[result["unequipped"]]["name"]
        self.msg(f"You unequip |w{item_name}|n.")
        self._render_gear(character)

    def func(self):
        character = self.get_character()
        if not character:
            return

        if self.args:
            command, _, remainder = self.args.strip().partition(" ")
            token = command.lower()
            if token in {"equip", "swap"}:
                slot_query, _, item_query = remainder.strip().partition(" ")
                if not slot_query or not item_query:
                    self.msg("Usage: gear equip <slot> <item>")
                    return
                self._equip(character, slot_query, item_query.strip())
                return
            if token in {"unequip", "remove", "clear"}:
                if not remainder.strip():
                    self.msg("Usage: gear unequip <slot>")
                    return
                self._unequip(character, remainder.strip())
                return
            self.msg("Usage: gear, gear equip <slot> <item>, gear unequip <slot>")
            return

        self._render_gear(character)


class CmdPack(BraveCharacterCommand):
    """
    View your pack and coin.

    Usage:
      pack

    Shows what you are carrying, while still allowing `inventory` as an alias.
    """

    key = "pack"
    aliases = ["inventory", "bag"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        inventory = list(character.db.brave_inventory or [])
        total_pieces = sum(entry.get("quantity", 0) for entry in inventory)
        grouped = {kind: [] for kind in PACK_KIND_ORDER}
        extras = []

        inventory.sort(key=lambda entry: ITEM_CONTENT.item_templates[entry["template"]]["name"])
        for entry in inventory:
            template_id = entry["template"]
            item = ITEM_CONTENT.item_templates[template_id]
            block = _format_inventory_entry(character, template_id, entry["quantity"])
            kind = ITEM_CONTENT.get_item_category(item)
            if kind in grouped:
                grouped[kind].append(block)
            else:
                extras.append(block)

        sections = []
        for kind in PACK_KIND_ORDER:
            if grouped[kind]:
                sections.append((PACK_KIND_LABELS[kind], _stack_blocks(grouped[kind])))
        if extras:
            sections.append(("Other", _stack_blocks(extras)))
        if not sections:
            sections.append(("Carried", ["  Your pack is empty."]))

        screen = render_screen(
            "Pack",
            subtitle="What you are carrying between rooms, fights, and town stops.",
            meta=[
                f"{character.db.brave_silver or 0} silver",
                f"{len(inventory)} item types",
                f"{total_pieces} total pieces",
            ],
            sections=sections,
        )
        self.scene_msg(screen, panel=build_pack_panel(character), view=build_pack_view(character))
        record_command_event(character, "pack")


class CmdCompanion(BraveCharacterCommand):
    """
    Review or change your active ranger companion.

    Usage:
      companion
      companion <name>

    Rangers can review bonded companions and choose which one is active.
    """

    key = "companion"
    aliases = ["pet", "bond"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if character.db.brave_class != "ranger":
            self.msg("Only Rangers manage an active battle companion.")
            return

        if not self.args:
            active = dict(getattr(character, "get_active_companion", lambda: {})() or {})
            unlocked = list(getattr(character, "get_unlocked_companions", lambda: [])() or [])
            blocks = []
            for companion in unlocked:
                bond = dict(companion.get("bond", {}) or {})
                details = [
                    "Active" if companion.get("key") == active.get("key") else "Bonded",
                    companion.get("bond_label", f"Bond {bond.get('level', 1)}"),
                ]
                if bond.get("at_cap"):
                    details.append("Bond XP capped")
                else:
                    details.append(f"{bond.get('xp_to_next', 0)} XP to next bond")
                blocks.append(
                    format_entry(
                        companion.get("name", "Companion"),
                        details=details,
                        summary=companion.get("summary"),
                    )
                )
            screen = render_screen(
                "Ranger Companion",
                subtitle="Your bonded companion shapes how the hunt feels in battle.",
                sections=[("Bonded Companions", _stack_blocks(blocks) if blocks else ["  No bonded companions yet."])],
            )
            self.scene_msg(screen, view=build_sheet_view(character), panel=build_sheet_panel(character))
            return

        query = _normalize_query(self.args)
        match_key = None
        for companion in getattr(character, "get_unlocked_companions", lambda: [])():
            companion_key = _normalize_query(companion.get("key"))
            name_key = _normalize_query(companion.get("name"))
            if query in {companion_key, name_key}:
                match_key = companion.get("key")
                break
        if not match_key:
            self.msg("No bonded companion matches that name.")
            return

        ok, message = character.set_active_companion(match_key)
        self.msg(message)


class CmdOath(BraveCharacterCommand):
    """
    Review or change your active Paladin oath.

    Usage:
      oath
      oath <name>

    Paladins can review sworn oaths and choose which one currently guides their chapel vigil.
    """

    key = "oath"
    aliases = ["vow", "vigil"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if character.db.brave_class != "paladin":
            self.msg("Only Paladins keep a sworn active oath.")
            return

        if not self.args:
            active = dict(getattr(character, "get_active_oath", lambda: {})() or {})
            unlocked = list(getattr(character, "get_unlocked_oaths", lambda: [])() or [])
            blocks = []
            for oath in unlocked:
                details = ["Active" if oath.get("key") == active.get("key") else "Sworn"]
                blocks.append(
                    format_entry(
                        oath.get("name", "Oath"),
                        details=details,
                        summary=oath.get("summary"),
                    )
                )
            screen = render_screen(
                "Sacred Oath",
                subtitle="Your active oath changes how the Dawn Bell and future holy relics answer your vigil.",
                sections=[("Sworn Oaths", _stack_blocks(blocks) if blocks else ["  No sworn oaths yet."])],
            )
            self.scene_msg(screen, view=build_sheet_view(character), panel=build_sheet_panel(character))
            return

        query = _normalize_query(self.args)
        match_key = None
        for oath in getattr(character, "get_unlocked_oaths", lambda: [])():
            oath_key = _normalize_query(oath.get("key"))
            name_key = _normalize_query(oath.get("name"))
            if query in {oath_key, name_key}:
                match_key = oath.get("key")
                break
        if not match_key:
            self.msg("No sworn oath matches that name.")
            return

        ok, message = character.set_active_oath(match_key)
        self.msg(message)


class CmdQuests(BraveCharacterCommand):
    """
    View your current quest journal.

    Usage:
      quests
      quests active
      quests completed
      quests expand <quest>
      quests collapse [quest]
      quests track <quest>
      quests untrack

    Shows the starter quests and your current progress through them.
    """

    key = "quests"
    aliases = ["quest", "journal"]
    help_category = "Brave"

    def _render_journal(self, character):
        journal_mode = _get_journal_mode(character)
        tracked_key = get_tracked_quest(character)
        tutorial_state = ensure_tutorial_state(character)
        tutorial_active = tutorial_state.get("status") == "active"
        tutorial_completed = tutorial_state.get("status") == "completed"
        
        tutorial_block = _format_tutorial_screen_block(character, completed_only=(journal_mode == "completed"))

        active_blocks = {}
        completed_blocks = {}
        tracked_block = None
        for quest_key in QUEST_CONTENT.starting_quests:
            state = (character.db.brave_quests or {}).get(quest_key)
            if not state or state.get("status") == "locked":
                continue
            block = _format_quest_screen_block(character, quest_key, tracked_key=tracked_key)
            if not block:
                continue
            if not tutorial_active and quest_key == tracked_key and state.get("status") == "active":
                tracked_block = block
                continue
            region = QUEST_CONTENT.get_quest_region(quest_key)
            if state.get("status") == "completed":
                completed_blocks.setdefault(region, []).append(block)
            else:
                active_blocks.setdefault(region, []).append(block)

        if not tutorial_block and not active_blocks and not completed_blocks and not tracked_block:
            self.msg("You do not have any quests yet.")
            return

        sections = []
        if journal_mode == "active":
            if tutorial_active and tutorial_block:
                sections.append(("Tracked Quest", tutorial_block))
            elif tracked_block:
                sections.append(("Tracked Quest", tracked_block))
            for region, region_blocks in active_blocks.items():
                sections.append((region, _stack_blocks(region_blocks)))
            if not sections:
                sections.append(("Active Quests", ["  No active quests right now."]))
        else:
            if tutorial_block:
                if isinstance(tutorial_block, list):
                    for block in tutorial_block:
                        sections.append(("Tutorial", block))
                else:
                    sections.append(("Tutorial", tutorial_block))
            for region, region_blocks in completed_blocks.items():
                sections.append((region, _stack_blocks(region_blocks)))
            if not sections:
                sections.append(("Completed Quests", ["  No completed quests yet."]))

        screen = render_screen(
            "Journal",
            sections=sections,
        )
        self.scene_msg(screen, panel=build_quests_panel(character), view=build_quests_view(character))
        record_command_event(character, "quests")

    def _track(self, character, query):
        if not query:
            self.msg("Usage: quests track <quest name>")
            return

        quest_key = resolve_active_quest_query(character, query)
        if not quest_key:
            self.msg("Could not find an active quest matching that.")
            return

        set_tracked_quest(character, quest_key)
        self._render_journal(character)

    def _untrack(self, character):
        if not get_tracked_quest(character):
            self.msg("You are not currently tracking a quest.")
            return

        clear_tracked_quest(character)
        self._render_journal(character)

    def _switch_mode(self, character, mode):
        _set_journal_mode(character, mode)
        self._render_journal(character)

    def _expand_completed(self, character, query):
        if not query:
            self.msg("Usage: quests expand <completed quest name>")
            return
        quest_key = _resolve_completed_quest_query(character, query)
        if not quest_key:
            self.msg("Could not find a completed quest matching that.")
            return
        _set_journal_mode(character, "completed")
        _set_expanded_completed_quest(character, quest_key)
        self._render_journal(character)

    def _collapse_completed(self, character, query):
        if query:
            quest_key = _resolve_completed_quest_query(character, query)
            if not quest_key:
                self.msg("Could not find a completed quest matching that.")
                return
            if _get_expanded_completed_quest(character) == quest_key:
                _set_expanded_completed_quest(character, None)
        else:
            _set_expanded_completed_quest(character, None)
        _set_journal_mode(character, "completed")
        self._render_journal(character)

    def func(self):
        character = self.get_character()
        if not character:
            return

        if self.args:
            command, _, remainder = self.args.strip().partition(" ")
            token = command.lower()
            if token in {"active", "current"}:
                self._switch_mode(character, "active")
                return
            if token in {"completed", "archive", "done"}:
                self._switch_mode(character, "completed")
                return
            if token in {"expand", "open"}:
                self._expand_completed(character, remainder.strip())
                return
            if token in {"collapse", "close"}:
                self._collapse_completed(character, remainder.strip())
                return
            if token in {"track", "pin", "focus"}:
                self._track(character, remainder.strip())
                return
            if token in {"untrack", "clear", "unpin"}:
                self._untrack(character)
                return
            self.msg("Usage: quests, quests active, quests completed, quests expand <quest name>, quests collapse [quest name], quests track <quest name>, quests untrack")
            return

        self._render_journal(character)
