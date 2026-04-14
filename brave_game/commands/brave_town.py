"""Town, hub, and local interaction commands extracted from Brave's main command module."""

from world.browser_panels import (
    build_cook_panel,
    build_forge_panel,
    build_read_panel,
    build_shop_panel,
    build_talk_panel,
)
from world.browser_views import (
    build_cook_view,
    build_forge_view,
    build_prayer_view,
    build_read_view,
    build_shop_view,
    build_talk_list_view,
    build_talk_view,
)
from world.activities import format_recipe_list
from world.content import get_content_registry
from world.chapel import apply_dawn_bell_blessing, get_active_blessing, is_chapel_room
from world.commerce import (
    format_shop_bonus,
    get_reserved_entries,
    get_sellable_entries,
    get_shop_bonus,
    is_outfitters_room,
    run_shop_shift,
    sell_inventory_item,
)
from world.data.items import ITEM_TEMPLATES
from world.forging import apply_forge_upgrade, get_forge_entries, is_forge_room
from world.interactions import get_entity_response
from world.screen_text import format_entry, render_screen, wrap_text

CONTENT = get_content_registry()

from .brave import (
    BraveCharacterCommand,
    _format_context_bonus_summary,
    _normalize_token,
    _stack_blocks,
    _wrap_paragraphs,
)


class CmdShop(BraveCharacterCommand):
    """
    Review current Outfitters trade options.

    Usage:
      shop

    Shows current Brambleford Outfitters trade rates, your merchant bonus, and what in your pack can be sold there.
    """

    key = "shop"
    aliases = ["browse", "market"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not is_outfitters_room(character.location):
            self.msg("You need to be at Brambleford Outfitters to review the trade board.")
            return

        bonus = get_shop_bonus(character)
        sellables = get_sellable_entries(character)
        reserved = get_reserved_entries(character)
        sellable_blocks = []
        for entry in sellables:
            template = ITEM_TEMPLATES.get(entry["template_id"], {})
            details = [
                f"{entry['unit_price']} silver each · {entry['total_price']} silver for the sellable stack",
            ]
            if entry["reserved"]:
                details.append(f"Holding {entry['reserved']} for active quest progress")
            sellable_blocks.append(
                format_entry(
                    f"{entry['name']} x{entry['sellable']}",
                    details=details,
                    summary=template.get("summary"),
                )
            )

        reserved_lines = []
        for entry in reserved:
            reserved_lines.extend(wrap_text(f"{entry['name']} x{entry['reserved']}", indent="  "))
        instruction_lines = [
            *wrap_text("Use |wsell <item>|n to sell one item.", indent="  "),
            *wrap_text("Use |wsell <item> = all|n to clear a full stack.", indent="  "),
            *wrap_text("Use |wshift|n to help at the counter and improve your next few sales.", indent="  "),
            *wrap_text("Best loop: |wrest|n in town, clear excess loot here, then check |wforge|n or |wcook|n before the next run.", indent="  "),
        ]

        screen = render_screen(
            "Brambleford Outfitters",
            subtitle="Leda buys practical finds and pays in clean town silver.",
            meta=[
                f"{character.db.brave_silver or 0} silver on hand",
                format_shop_bonus(bonus) if bonus else "No current merchant favor",
            ],
            sections=[
                ("Sellable Stock", _stack_blocks(sellable_blocks) if sellable_blocks else ["  Nothing sellable right now."]),
                ("Held For Active Quests", reserved_lines if reserved_lines else ["  Nothing currently reserved."]),
                ("Counter Tips", instruction_lines),
            ],
        )
        self.scene_msg(screen, panel=build_shop_panel(character), view=build_shop_view(character))


class CmdSell(BraveCharacterCommand):
    """
    Sell pack items at the Outfitters.

    Usage:
      sell <item>
      sell <item> = <quantity|all>

    Sells a pack item for silver while preserving active collect-quest items.
    """

    key = "sell"
    aliases = ["trade", "cashout"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not is_outfitters_room(character.location):
            self.msg("You need to be at Brambleford Outfitters to sell anything.")
            return
        if not self.args:
            self.msg("Usage: sell <item> or sell <item> = <quantity|all>")
            return

        query = self.args.strip()
        quantity = 1
        if "=" in query:
            item_query, _, quantity_text = query.partition("=")
            query = item_query.strip()
            quantity_text = quantity_text.strip().lower()
            if not query or not quantity_text:
                self.msg("Usage: sell <item> = <quantity|all>")
                return
            if quantity_text == "all":
                quantity = None
            else:
                if not quantity_text.isdigit():
                    self.msg("Quantity must be a number or |wall|n.")
                    return
                quantity = int(quantity_text)

        match, entries = self.find_inventory_item(character, query, require_value=True)
        if isinstance(match, list):
            self.msg("Be more specific. That could mean: " + ", ".join(item["name"] for _, item in match))
            return
        if not match:
            if entries:
                self.msg("No sellable pack item matches that name.")
            else:
                self.msg("You are not carrying anything the Outfitters will buy.")
            return

        template_id, item = match
        if quantity is None:
            sellables = {entry["template_id"]: entry for entry in get_sellable_entries(character)}
            quantity = sellables.get(template_id, {}).get("sellable", 0)
        ok, result = sell_inventory_item(character, template_id, quantity)
        if not ok:
            self.msg(result)
            return

        quantity_suffix = f" x{result['quantity']}" if result["quantity"] > 1 else ""
        self.msg(
            f"You sell {result['item_name']}{quantity_suffix} for |w{result['silver']}|n silver."
        )
        if result["expired_bonus"]:
            self.msg("Leda's better column closes for now. You'll need another |wshift|n to earn it back.")
        elif result["remaining_bonus"]:
            self.msg("Merchant favor remaining: " + format_shop_bonus(result["remaining_bonus"]))


class CmdShift(BraveCharacterCommand):
    """
    Work a short shift at Brambleford Outfitters.

    Usage:
      shift

    Helps at the counter and earns a temporary better sale rate on your next few transactions.
    """

    key = "shift"
    aliases = ["work", "shopshift"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not is_outfitters_room(character.location):
            self.msg("You need to be at Brambleford Outfitters to work a shift.")
            return
        if character.get_active_encounter():
            self.msg("This is not the time to step behind the counter.")
            return

        _ok, message = run_shop_shift(character)
        self.msg(message)


class CmdForge(BraveCharacterCommand):
    """
    Review or apply Ironroot Forge upgrades.

    Usage:
      forge
      forge <item>

    Shows Torren's current rework options for your equipped gear, or upgrades one piece if you have the loot and silver.
    """

    key = "forge"
    aliases = ["smith", "upgrade"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not is_forge_room(character.location):
            self.msg("You need to be at Ironroot Forge before Torren will start heating metal for you.")
            return
        if character.get_active_encounter():
            self.msg("This is not the moment to start a forge order.")
            return

        entries = get_forge_entries(character)
        if not self.args:
            if not entries:
                screen = render_screen(
                    "Ironroot Forge",
                    subtitle="Torren eyes your kit and finds nothing worth dragging onto the anvil yet.",
                    meta=[f"{character.db.brave_silver or 0} silver on hand"],
                    sections=[("Current Orders", ["  No rework options from your equipped gear."])],
                )
                self.scene_msg(screen, panel=build_forge_panel(character), view=build_forge_view(character))
                return

            ready_blocks = []
            pending_blocks = []
            for entry in entries:
                material_text = ", ".join(
                    f"{material['name']} {material['owned']}/{material['required']}"
                    for material in entry["materials"]
                )
                details = [
                    f"{entry['slot_label']} · {entry['silver_cost']} silver",
                    "Materials: " + material_text if material_text else "No extra materials needed",
                ]
                if entry["result_bonuses"]:
                    details.append("Result: " + entry["result_bonuses"])
                block = format_entry(
                    f"{entry['source_name']} -> {entry['result_name']}",
                    details=details,
                    summary=entry["text"],
                )
                if entry["ready"]:
                    ready_blocks.append(block)
                else:
                    pending_blocks.append(block)

            screen = render_screen(
                "Ironroot Forge",
                subtitle="Torren can rework your equipped field kit into sturdier frontier gear.",
                meta=[
                    f"{character.db.brave_silver or 0} silver on hand",
                    f"{sum(1 for entry in entries if entry['ready'])} ready orders",
                ],
                sections=[
                    ("Ready To Rework", _stack_blocks(ready_blocks) if ready_blocks else ["  Nothing is fully ready yet."]),
                    ("Still Missing", _stack_blocks(pending_blocks) if pending_blocks else ["  No pending orders."]),
                    ("How To Order", wrap_text("Use |wforge <item>|n to commission one listed rework.", indent="  ")),
                    (
                        "Forge Rhythm",
                        [
                            *wrap_text("Cash out unneeded loot at the Outfitters first if silver is the blocker.", indent="  "),
                            *wrap_text("Forge upgrades make more sense after a town reset than in the middle of a field push.", indent="  "),
                        ],
                    ),
                ],
            )
            self.scene_msg(screen, panel=build_forge_panel(character), view=build_forge_view(character))
            return

        query = self.args.strip()
        query_norm = _normalize_token(query)
        exact = []
        partial = []
        for entry in entries:
            names = [
                entry["source_name"],
                entry["result_name"],
                entry["slot_label"],
                entry["source_template_id"].replace("_", " "),
                entry["result_template_id"].replace("_", " "),
            ]
            tokens = [_normalize_token(name) for name in names]
            if any(query_norm == token for token in tokens):
                exact.append(entry)
            elif any(query_norm in token for token in tokens):
                partial.append(entry)

        matches = exact or partial
        if not matches:
            if entries:
                self.msg("No current forge order matches that name.")
            else:
                self.msg("Torren has nothing to rework from your currently equipped gear.")
            return
        if len(matches) > 1:
            self.msg("Be more specific. That could mean: " + ", ".join(entry["source_name"] for entry in matches))
            return

        entry = matches[0]
        ok, result = apply_forge_upgrade(character, entry["source_template_id"])
        if not ok:
            self.msg(result)
            return

        lines = []
        if result["text"]:
            lines.append(result["text"])
        bonus_suffix = f" ({result['bonus_summary']})" if result["bonus_summary"] else ""
        lines.append(
            f"Torren hands over your new |w{result['item_name']}|n{bonus_suffix}. The order cost |w{result['silver_cost']}|n silver."
        )
        self.msg("\n".join(lines))


class CmdPray(BraveCharacterCommand):
    """
    Receive the Dawn Bell blessing.

    Usage:
      pray

    At the Chapel of the Dawn Bell, this grants a modest one-encounter blessing.
    Calling it again while the blessing is active just reopens the current blessing view.
    """

    key = "pray"
    aliases = ["bless", "kneel"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not is_chapel_room(character.location):
            self.msg("You need to be at the Chapel of the Dawn Bell to do that.")
            return
        encounter = self.get_encounter(character)
        if encounter and encounter.is_participant(character):
            self.msg("This is not the moment for prayer.")
            return

        blessing = get_active_blessing(character)
        applied = False
        if not blessing:
            blessing = apply_dawn_bell_blessing(character)
            applied = True

        bonus_text = _format_context_bonus_summary(blessing.get("bonuses", {}), character)
        lines = [
            *wrap_text("The Dawn Bell answers with a steadier note than sound alone should manage.", indent="  "),
            *wrap_text(blessing.get("duration", "Until your next encounter ends."), indent="  "),
        ]
        if bonus_text:
            lines.extend(wrap_text("Bonuses: " + bonus_text, indent="  "))

        screen = render_screen(
            "Dawn Bell",
            subtitle="The chapel's blessing settles on you for the next hard road."
            if applied
            else "The chapel's blessing still rests on you.",
            sections=[("Blessing", lines)],
        )
        self.scene_msg(screen, view=build_prayer_view(character, blessing=blessing, applied=applied))


class CmdTalk(BraveCharacterCommand):
    """
    Speak with a local NPC.

    Usage:
      talk
      talk <name>

    Lists talkable NPCs in the room or gets contextual guidance from one of them.
    """

    key = "talk"
    aliases = ["speak"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        encounter = self.get_encounter(character, require=False)
        if encounter and encounter.is_participant(character):
            self.msg("This is not the moment for a calm conversation.")
            return

        if not self.args:
            npcs = self.get_local_entities(character, kind="npc")
            if not npcs:
                self.msg("No one here looks free for conversation.")
                return
            screen = render_screen(
                "Conversation",
                subtitle="Choose someone nearby to speak with.",
                sections=[("Nearby NPCs", [f"  - {npc.key}" for npc in npcs])],
            )
            self.scene_msg(screen, view=build_talk_list_view(character, npcs))
            return

        target, npcs = self.find_local_entity(character, self.args.strip(), kind="npc")
        if isinstance(target, list):
            self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in target))
            return
        if not target:
            if npcs:
                self.msg(
                    "No one here matches that name. You can talk to: "
                    + ", ".join(npc.key for npc in npcs)
                )
            else:
                self.msg("No one here looks free for conversation.")
            return

        response = get_entity_response(character, target, "talk")
        if not response:
            self.msg(f"{target.key} has nothing to say right now.")
            return

        screen = render_screen(
            target.key,
            subtitle="Conversation",
            sections=[("What They Say", _wrap_paragraphs(response))],
        )
        self.scene_msg(screen, panel=build_talk_panel(target), view=build_talk_view(target, response))


class CmdRead(BraveCharacterCommand):
    """
    Read a local sign, board, or notice.

    Usage:
      read
      read <thing>

    Lists readable objects in the room or shows their text.
    """

    key = "read"
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        readable_objects = self.get_local_entities(character, kind="readable")
        if not self.args:
            if not readable_objects:
                self.msg("There is nothing obvious to read here.")
                return
            self.msg("Readable here: " + ", ".join(obj.key for obj in readable_objects))
            return

        target, readable_objects = self.find_local_entity(character, self.args.strip(), kind="readable")
        if isinstance(target, list):
            self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in target))
            return
        if not target:
            if readable_objects:
                self.msg(
                    "Nothing readable here matches that name. You can read: "
                    + ", ".join(obj.key for obj in readable_objects)
                )
            else:
                self.msg("There is nothing obvious to read here.")
            return

        if getattr(target.db, "brave_entity_id", None) == "kitchen_hearth":
            self.scene_msg(
                format_recipe_list(character),
                panel=build_cook_panel(character),
                view=build_cook_view(character),
            )
            return

        response = get_entity_response(character, target, "read")
        if not response:
            self.msg(f"There is nothing new to make out from {target.key}.")
            return

        screen = render_screen(
            target.key,
            subtitle="Read Text",
            sections=[("Inscription", _wrap_paragraphs(response))],
        )
        self.scene_msg(screen, panel=build_read_panel(target), view=build_read_view(target, response))
