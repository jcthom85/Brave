"""Profile, build, inventory, and journal commands extracted from Brave's helper module."""

from world.browser_panels import build_build_panel, build_gear_panel, build_pack_panel, build_quests_panel, build_sheet_panel
from world.browser_views import build_gear_view, build_pack_view, build_quests_view, build_sheet_view
from world.chapel import get_active_blessing
from world.data.character_options import CLASSES, RACES, VERTICAL_SLICE_CLASSES, xp_needed_for_next_level
from world.data.items import EQUIPMENT_SLOTS, ITEM_TEMPLATES
from world.data.quests import QUESTS, STARTING_QUESTS
from world.questing import clear_tracked_quest, get_tracked_quest, resolve_active_quest_query, set_tracked_quest
from world.resonance import (
    format_ability_display,
    get_resonance_key,
    get_resonance_label,
    get_resource_label,
    get_stat_label,
)
from world.screen_text import format_entry, format_pairs, render_screen, wrap_text
from world.tutorial import record_command_event

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

        race = RACES[character.db.brave_race]
        class_data = CLASSES[character.db.brave_class]
        race_blocks = [
            format_entry(f"{race_data['name']} · {race_data['perk']}", summary=race_data["summary"])
            for race_data in RACES.values()
        ]
        class_blocks = [
            format_entry(
                f"{CLASSES[class_key]['name']} · {CLASSES[class_key]['role']}",
                summary=CLASSES[class_key]["summary"],
            )
            for class_key in VERTICAL_SLICE_CLASSES
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
        matches = [key for key, data in RACES.items() if query in (key, data["name"].lower().replace(" ", "_"))]
        if not matches:
            self.msg("Unknown race. Use |wbuild|n to see available races.")
            return

        race_key = matches[0]
        character.set_brave_race(race_key)
        self.msg(f"Your race is now |w{RACES[race_key]['name']}|n.")


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
            for class_key in VERTICAL_SLICE_CLASSES
            if query in (class_key, CLASSES[class_key]["name"].lower().replace(" ", "_"))
        ]
        if not matches:
            choices = ", ".join(CLASSES[class_key]["name"] for class_key in VERTICAL_SLICE_CLASSES)
            self.msg(f"Playable classes right now are: {choices}")
            return

        class_key = matches[0]
        character.set_brave_class(class_key)
        self.msg(f"Your class is now |w{CLASSES[class_key]['name']}|n. Your starter gear shifts to match.")


class CmdSheet(BraveCharacterCommand):
    """
    View your current adventurer sheet.

    Usage:
      sheet

    Shows your race, class, level, resources, stats, and unlocked abilities.
    """

    key = "sheet"
    aliases = ["stats", "whoami"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        race = RACES[character.db.brave_race]
        class_data = CLASSES[character.db.brave_class]
        primary = character.db.brave_primary_stats
        derived = character.db.brave_derived_stats
        resources = character.db.brave_resources
        abilities = character.get_unlocked_abilities()
        next_level_xp = xp_needed_for_next_level(character.db.brave_level)
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
                "Unlocked Abilities",
                [f"  {format_ability_display(ability, character)}" for ability in abilities]
                if abilities
                else ["  None yet"],
            ),
        ]

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


class CmdGear(BraveCharacterCommand):
    """
    View your currently equipped gear.

    Usage:
      gear

    Shows your auto-equipped starter kit and the bonuses it grants.
    """

    key = "gear"
    aliases = ["equipment", "kit"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        equipment = character.db.brave_equipment or {}
        filled_slots = [(slot, equipment.get(slot)) for slot in EQUIPMENT_SLOTS if equipment.get(slot)]
        open_slots = [slot.replace("_", " ").title() for slot in EQUIPMENT_SLOTS if not equipment.get(slot)]
        total_bonus_text = _format_context_bonus_summary(_format_equipment_totals(character), character)

        sections = [
            (
                "Equipped",
                _stack_blocks(
                    [
                        _format_equipped_item_entry(character, slot, template_id)
                        for slot, template_id in filled_slots
                    ]
                )
                if filled_slots
                else ["  Nothing equipped yet."],
            ),
        ]
        if open_slots:
            sections.append(("Open Slots", wrap_text(", ".join(open_slots), indent="  ")))
        if total_bonus_text:
            sections.append(("Current Kit Bonus", wrap_text(total_bonus_text, indent="  ")))

        screen = render_screen(
            "Equipped Gear",
            subtitle="What you are wearing right now.",
            meta=[f"{len(filled_slots)} / {len(EQUIPMENT_SLOTS)} slots filled"],
            sections=sections,
        )
        self.scene_msg(screen, panel=build_gear_panel(character), view=build_gear_view(character))
        record_command_event(character, "gear")


class CmdPack(BraveCharacterCommand):
    """
    View your carried loot and coin.

    Usage:
      pack

    Shows your current silver and any loot recovered from encounters.
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

        inventory.sort(key=lambda entry: ITEM_TEMPLATES[entry["template"]]["name"])
        for entry in inventory:
            template_id = entry["template"]
            item = ITEM_TEMPLATES[template_id]
            block = _format_inventory_entry(character, template_id, entry["quantity"])
            kind = item.get("kind")
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


class CmdQuests(BraveCharacterCommand):
    """
    View your current quest journal.

    Usage:
      quests
      quests track <quest>
      quests untrack

    Shows the starter quests and your current progress through them.
    """

    key = "quests"
    aliases = ["quest", "journal"]
    help_category = "Brave"

    def _render_journal(self, character):
        tracked_key = get_tracked_quest(character)
        tutorial_block = _format_tutorial_screen_block(character)
        active_blocks = []
        completed_blocks = []
        active_count = 0
        for quest_key in STARTING_QUESTS:
            state = (character.db.brave_quests or {}).get(quest_key)
            if not state or state.get("status") == "locked":
                continue
            block = _format_quest_screen_block(character, quest_key, tracked_key=tracked_key)
            if not block:
                continue
            if state.get("status") == "completed":
                completed_blocks.append(block)
            else:
                active_count += 1
                active_blocks.append(block)

        if not tutorial_block and not active_blocks and not completed_blocks:
            self.msg("You do not have any quests yet.")
            return

        sections = []
        if tutorial_block:
            sections.append(("Tutorial", tutorial_block))
        sections.append(("Active Quests", _stack_blocks(active_blocks) if active_blocks else ["  No active quests right now."]))
        if completed_blocks:
            sections.append(("Completed", _stack_blocks(completed_blocks)))

        screen = render_screen(
            "Quest Journal",
            subtitle="Use `quests track <name>` to pin one in exploration. Use `quests untrack` to clear it.",
            meta=[
                f"{active_count} active",
                f"{len(completed_blocks)} completed",
                f"tracked: {QUESTS[tracked_key]['title']}" if tracked_key else "no tracked quest",
            ],
            sections=sections,
        )
        self.scene_msg(screen, panel=build_quests_panel(character), view=build_quests_view(character))

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

    def func(self):
        character = self.get_character()
        if not character:
            return

        if self.args:
            command, _, remainder = self.args.strip().partition(" ")
            token = command.lower()
            if token in {"track", "pin", "focus"}:
                self._track(character, remainder.strip())
                return
            if token in {"untrack", "clear", "unpin"}:
                self._untrack(character)
                return
            self.msg("Usage: quests, quests track <quest name>, quests untrack")
            return

        self._render_journal(character)
