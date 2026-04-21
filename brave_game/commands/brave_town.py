"""Town, hub, and local interaction commands extracted from Brave's main command module."""

import re

from world.browser_panels import (
    build_cook_panel,
    build_forge_panel,
    build_portals_panel,
    build_read_panel,
    build_shop_panel,
    build_talk_panel,
    build_tinker_panel,
    send_webclient_event,
)
from world.browser_views import (
    build_cook_view,
    build_forge_view,
    build_portals_view,
    build_prayer_view,
    build_read_view,
    build_shop_view,
    build_talk_list_view,
    build_talk_view,
    build_tinker_view,
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
from world.rogue_ops import attempt_theft, get_available_steal_targets
from world.screen_text import format_entry, render_screen, wrap_text
from world.tinkering import (
    build_tinkering_payload,
    describe_tinkering_recipe,
    get_tinkering_entries,
    is_tinkering_room,
    perform_tinkering,
)

CONTENT = get_content_registry()
PORTALS = CONTENT.systems.portals

from .brave import (
    BraveCharacterCommand,
    _format_context_bonus_summary,
    _normalize_token,
    _stack_blocks,
    _wrap_paragraphs,
)


_EVENNIA_MARKUP_RE = re.compile(r"\|[A-Za-z]")


def _strip_evennia_markup(text):
    """Remove lightweight Evennia color markup for browser overlay status text."""

    clean = str(text or "").replace("||", "|")
    return _EVENNIA_MARKUP_RE.sub("", clean)


def _send_tinkering_payload(command, character, payload):
    """Send a tinkering overlay payload to the current web session."""

    session = command.get_web_session()
    if not session or not payload:
        return False
    send_webclient_event(character, session=session, brave_tinkering=payload)
    return True


def _refresh_tinkering_scene(command, character, message=None, *, success=False):
    """Keep browser-based workbench actions inside the tinkering overlay."""

    if not command.get_web_session() or not is_tinkering_room(character.location):
        return False
    _send_tinkering_payload(
        command,
        character,
        build_tinkering_payload(
            character,
            status_message=_strip_evennia_markup(message),
            status_tone="good" if success else "muted",
        ),
    )
    if message:
        command.send_other_sessions(message)
    return True


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


class CmdTinker(BraveCharacterCommand):
    """
    Review or assemble workbench designs.

    Usage:
      tinker
      tinker inspect <design>
      tinker <design>

    Shows current tinkering options at a proper workbench, or builds one design if
    you have the parts and silver.
    """

    key = "tinker"
    aliases = ["tinkering"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not is_tinkering_room(character.location):
            self.msg("You need a proper workbench before you can spread out your parts and start tinkering.")
            return
        if character.get_active_encounter():
            self.msg("This is not the moment to start bench work.")
            return

        entries = get_tinkering_entries(character)
        if not self.args:
            if self.get_web_session():
                _send_tinkering_payload(self, character, build_tinkering_payload(character))
                return
            ready_blocks = []
            known_blocks = []
            locked_blocks = []
            for entry in entries:
                details = []
                if entry["base_name"]:
                    details.append(f"Base: {entry['base_name']} {entry['base_owned']}/1")
                if entry["components"]:
                    details.append(
                        "Parts: " + ", ".join(f"{row['name']} {row['owned']}/{row['required']}" for row in entry["components"])
                    )
                if entry["silver_cost"]:
                    details.append(f"Silver: {entry['silver_cost']}")
                if entry["result_bonuses"]:
                    details.append("Result: " + entry["result_bonuses"])
                block = format_entry(
                    f"{entry['name']} -> {entry['result_name']}",
                    details=details,
                    summary=entry["summary"] or entry["result_summary"],
                )
                if not entry["known"]:
                    locked_blocks.append(block)
                elif entry["ready"]:
                    ready_blocks.append(block)
                else:
                    known_blocks.append(block)

            screen = render_screen(
                "Workbench Ledger",
                subtitle="Small frontier repairs, rough bench work, and field fixes that keep a pack useful.",
                meta=[
                    f"{character.db.brave_silver or 0} silver on hand",
                    f"{sum(1 for entry in entries if entry['ready'])} ready designs",
                ],
                sections=[
                    ("Ready Now", _stack_blocks(ready_blocks) if ready_blocks else ["  Nothing is ready from your current pack."]),
                    ("Known Designs", _stack_blocks(known_blocks) if known_blocks else ["  No other known designs are close to completion."]),
                    ("Locked Designs", _stack_blocks(locked_blocks) if locked_blocks else ["  No locked tinkering designs yet."]),
                    ("How To Work", wrap_text("Use |wtinker inspect <design>|n to review one design, or |wtinker <design>|n to assemble it.", indent="  ")),
                ],
            )
            self.scene_msg(screen, panel=build_tinker_panel(character), view=build_tinker_view(character))
            return

        raw = self.args.strip()
        lowered = raw.lower()
        if lowered.startswith("inspect "):
            ok, message = describe_tinkering_recipe(character, raw[8:].strip())
            if _refresh_tinkering_scene(self, character, message, success=ok):
                return
            self.msg(message)
            return

        ok, message = perform_tinkering(character, raw)
        if _refresh_tinkering_scene(self, character, message, success=ok):
            return
        self.msg(message)


class CmdPortals(BraveCharacterCommand):
    """
    Review the current Nexus gates.

    Usage:
      portals

    Lists the current portal lineup while standing at the Nexus Gate.
    """

    key = "portals"
    aliases = ["gates", "portal list"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not character.location or not character.location.db.brave_portal_hub:
            self.msg("You need to be at the Nexus Gate before the portal routes make any sense.")
            return

        sections = []
        for status_key, section_title in (
            ("stable", "Stable Gates"),
            ("dormant", "Dormant Gates"),
            ("sealed", "Sealed Gates"),
        ):
            blocks = []
            for portal in PORTALS.values():
                if portal["status"] != status_key:
                    continue
                details = [f"Resonance: {portal['resonance'].replace('_', ' ').title()}"]
                if portal.get("travel_hint"):
                    details.append(f"Entry route: {portal['travel_hint']}")
                blocks.append(format_entry(portal["name"], details=details, summary=portal["summary"]))
            sections.append((section_title, _stack_blocks(blocks) if blocks else ["  None at the moment."]))

        screen = render_screen(
            "Nexus Gates",
            subtitle="The ring lists what Brambleford can currently reach and what still refuses to answer.",
            meta=[f"{len(PORTALS)} total gates"],
            sections=sections,
        )
        self.scene_msg(screen, panel=build_portals_panel(), view=build_portals_view(character))


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
        rite = dict(blessing.get("rite") or {})
        lines = [
            *wrap_text("The Dawn Bell answers with a steadier note than sound alone should manage.", indent="  "),
            *wrap_text(blessing.get("duration", "Until your next encounter ends."), indent="  "),
        ]
        if bonus_text:
            lines.extend(wrap_text("Bonuses: " + bonus_text, indent="  "))
        if rite.get("name"):
            lines.extend(wrap_text(f"Class rite: {rite['name']}.", indent="  "))
        if rite.get("summary"):
            lines.extend(wrap_text(rite["summary"], indent="  "))

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


class CmdSteal(BraveCharacterCommand):
    """
    Work a Rogue-only theft angle on a local NPC.

    Usage:
      steal
      steal <name>

    Lists authored local marks or works one clean lift from a nearby NPC. Each authored target can only be worked once.
    """

    key = "steal"
    aliases = ["pickpocket", "lift"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if getattr(character.db, "brave_class", None) != "rogue":
            self.msg("Only a Rogue knows how to work a clean lift here.")
            return

        encounter = self.get_encounter(character, require=False)
        if encounter and encounter.is_participant(character):
            self.msg("This is not the moment for fine finger work.")
            return

        npcs = self.get_local_entities(character, kind="npc")
        marks = get_available_steal_targets(npcs)
        theft_log = dict(getattr(character.db, "brave_rogue_theft_log", None) or {})

        if not self.args:
            if not marks:
                self.msg("No one here offers an obvious clean lift.")
                return
            mark_blocks = []
            for entity, target in marks:
                entity_id = getattr(getattr(entity, "db", None), "brave_entity_id", None)
                details = ["Already worked" if theft_log.get(entity_id) else "Open angle"]
                mark_blocks.append(format_entry(entity.key, details=details, summary=target.get("summary")))
            screen = render_screen(
                "Illicit Access",
                subtitle="You size up the room for easy hands, bad habits, and anyone carrying more than they guard.",
                meta=[f"Worked marks: {len(theft_log)}"],
                sections=[
                    ("Possible Marks", _stack_blocks(mark_blocks)),
                    ("How To Lift", wrap_text("Use |wsteal <name>|n to work one authored theft angle.", indent="  ")),
                ],
            )
            self.scene_msg(screen)
            return

        target, _npcs = self.find_local_entity(character, self.args.strip(), kind="npc")
        if isinstance(target, list):
            self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in target))
            return
        if not target:
            if marks:
                self.msg("No authored mark here matches that name. You can work: " + ", ".join(entity.key for entity, _ in marks))
            else:
                self.msg("No one here offers an obvious clean lift.")
            return

        ok, message, result = attempt_theft(character, target)
        if not ok:
            self.msg(message)
            return

        reward_lines = [message]
        rewards = list((result or {}).get("rewards", []) or [])
        if rewards:
            reward_lines.append("Take: " + ", ".join(rewards))
        screen = render_screen(
            result.get("target_name", target.key),
            subtitle="Clean Lift",
            meta=[f"Worked marks: {len(character.db.brave_rogue_theft_log or {})}"],
            sections=[("Haul", _wrap_paragraphs("\n".join(reward_lines)))],
        )
        self.scene_msg(screen)


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
