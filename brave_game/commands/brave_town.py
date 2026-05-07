"""Town, hub, and local interaction commands extracted from Brave's main command module."""

import re

from world.browser_panels import (
    build_cook_panel,
    build_forge_panel,
    build_shop_panel,
    build_tinker_panel,
    send_webclient_event,
)
from world.browser_views import (
    build_cook_view,
    build_forge_view,
    build_prayer_view,
    build_shop_view,
    build_tinker_view,
)
from world.activities import format_recipe_list
from world.content import get_content_registry
from world.chapel import apply_dawn_bell_blessing, get_active_blessing, is_chapel_room
from world.commerce import (
    buy_shop_item,
    get_buyable_entries,
    get_reserved_entries,
    get_sellable_entries,
    get_shop_for_room,
    is_shop_room,
    run_shop_shift,
    sell_inventory_item,
)
from world.data.items import ITEM_TEMPLATES
from world.forging import apply_forge_upgrade, get_forge_entries, is_forge_room
from world.interactions import get_entity_response
from world.movies import (
    GREAT_FRONTIER_MOVIES,
    build_movie_audio_payload,
    build_movie_picker,
    build_movie_view,
    build_now_showing_picker,
    is_movie_theater_room,
    movie_cards,
    movie_label,
    resolve_movie,
)
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


def _refresh_shop_scene(command, character, message=None, *, success=False, title=None):
    """Keep browser shop actions inside the shop view with popup feedback."""

    if not command.get_web_session() or not is_shop_room(character.location):
        return False
    plain = _strip_evennia_markup(message) if message else None
    command.send_browser_view(
        build_shop_view(
            character,
            status_message=plain,
            status_tone="good" if success else "muted",
        )
    )
    command.send_browser_panel(build_shop_panel(character))
    if plain:
        command.send_browser_notice(
            title or ("Shop Updated" if success else "Shop Notice"),
            lines=[plain],
            tone="good" if success else "danger",
            icon="task_alt" if success else "error",
            duration_ms=3600 if success else 5200,
        )
        command.send_other_sessions(message)
    return True


class CmdShop(BraveCharacterCommand):
    """
    Review current shop trade options.

    Usage:
      shop

    Shows current shop stock, sale rates, merchant bonus, and what in your pack can be sold there.
    """

    key = "shop"
    aliases = ["browse", "market"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        shop_id, shop = get_shop_for_room(character.location)
        if not shop:
            if not self.deliver_browser_notice("You need to be at a shop to review the trade board.", title="No Shop", tone="danger", icon="storefront"):
                self.msg("You need to be at a shop to review the trade board.")
            return

        buyables = get_buyable_entries(character, shop=shop)
        sellables = get_sellable_entries(character, shop=shop, shop_id=shop_id)
        reserved = get_reserved_entries(character)
        buyable_blocks = []
        for entry in buyables:
            template = ITEM_TEMPLATES.get(entry["template_id"], {})
            details = [f"{entry['price']} silver"]
            if entry["locked"]:
                details.append("Locked until: " + ", ".join(entry["unlock_completed_quests"]))
            buyable_blocks.append(
                format_entry(
                    entry["name"],
                    details=details,
                    summary=template.get("summary"),
                )
            )
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
            *wrap_text("Use |wbuy <item>|n to buy one stocked item.", indent="  "),
            *wrap_text("Use |wbuy <item> = <quantity>|n to buy several.", indent="  "),
            *wrap_text("Use |wsell <item>|n to sell one item.", indent="  "),
            *wrap_text("Use |wsell <item> = all|n to clear a full stack.", indent="  "),
        ]

        screen = render_screen(
            shop.get("name", "Shop"),
            subtitle=shop.get("summary", "A practical place to trade."),
            meta=[
                f"{character.db.brave_silver or 0} silver on hand",
            ],
            sections=[
                ("Stock", _stack_blocks(buyable_blocks) if buyable_blocks else ["  Nothing for sale right now."]),
                ("Sellable Stock", _stack_blocks(sellable_blocks) if sellable_blocks else ["  Nothing sellable right now."]),
                ("Held For Active Quests", reserved_lines if reserved_lines else ["  Nothing currently reserved."]),
                ("Counter Tips", instruction_lines),
            ],
        )
        self.scene_msg(screen, panel=build_shop_panel(character), view=build_shop_view(character))


class CmdBuy(BraveCharacterCommand):
    """
    Buy stocked items at the current shop.

    Usage:
      buy <item>
      buy <item> = <quantity>
    """

    key = "buy"
    aliases = ["purchase"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        shop_id, shop = get_shop_for_room(character.location)
        if not shop:
            message = "You need to be at a shop to buy anything."
            if not self.deliver_browser_notice(message, title="No Shop", tone="danger", icon="storefront"):
                self.msg(message)
            return
        if not self.args:
            message = "Choose an item from the shop list."
            if not _refresh_shop_scene(self, character, message, success=False, title="Choose Stock"):
                self.msg("Usage: buy <item> or buy <item> = <quantity>")
            return

        query = self.args.strip()
        quantity = 1
        if "=" in query:
            item_query, _, quantity_text = query.partition("=")
            query = item_query.strip()
            quantity_text = quantity_text.strip().lower()
            if not query or not quantity_text:
                message = "Choose an item and quantity from the shop list."
                if not _refresh_shop_scene(self, character, message, success=False, title="Choose Stock"):
                    self.msg("Usage: buy <item> = <quantity>")
                return
            if not quantity_text.isdigit():
                message = "Quantity must be a number."
                if not _refresh_shop_scene(self, character, message, success=False, title="Invalid Quantity"):
                    self.msg(message)
                return
            quantity = int(quantity_text)

        entries = get_buyable_entries(character, shop=shop)
        token = _normalize_token(query)
        matches = [
            entry
            for entry in entries
            if token in _normalize_token(entry["name"]) or token in _normalize_token(entry["template_id"])
        ]
        if len(matches) > 1:
            message = "Be more specific. That could mean: " + ", ".join(entry["name"] for entry in matches)
            if not _refresh_shop_scene(self, character, message, success=False, title="Multiple Matches"):
                self.msg(message)
            return
        if not matches:
            message = f"{shop.get('name', 'This shop')} does not stock that."
            if not _refresh_shop_scene(self, character, message, success=False, title="Not Stocked"):
                self.msg(message)
            return

        ok, result = buy_shop_item(character, matches[0]["template_id"], quantity)
        if not ok:
            if not _refresh_shop_scene(self, character, result, success=False, title="Can't Buy"):
                self.msg(result)
            return
        quantity_suffix = f" x{result['quantity']}" if result["quantity"] > 1 else ""
        message = f"Bought {result['item_name']}{quantity_suffix} for {result['silver']} silver."
        if not _refresh_shop_scene(self, character, message, success=True, title="Purchase Complete"):
            self.msg(f"You buy {result['item_name']}{quantity_suffix} for |w{result['silver']}|n silver.")


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
        shop_id, shop = get_shop_for_room(character.location)
        if not shop:
            message = "You need to be at a shop to sell anything."
            if not self.deliver_browser_notice(message, title="No Shop", tone="danger", icon="storefront"):
                self.msg(message)
            return
        if not self.args:
            message = "Choose an item from your sell list."
            if not _refresh_shop_scene(self, character, message, success=False, title="Choose Item"):
                self.msg("Usage: sell <item> or sell <item> = <quantity|all>")
            return

        query = self.args.strip()
        quantity = 1
        if "=" in query:
            item_query, _, quantity_text = query.partition("=")
            query = item_query.strip()
            quantity_text = quantity_text.strip().lower()
            if not query or not quantity_text:
                message = "Choose an item and quantity from your sell list."
                if not _refresh_shop_scene(self, character, message, success=False, title="Choose Item"):
                    self.msg("Usage: sell <item> = <quantity|all>")
                return
            if quantity_text == "all":
                quantity = None
            else:
                if not quantity_text.isdigit():
                    message = "Quantity must be a number."
                    if not _refresh_shop_scene(self, character, message, success=False, title="Invalid Quantity"):
                        self.msg("Quantity must be a number or |wall|n.")
                    return
                quantity = int(quantity_text)

        match, entries = self.find_inventory_item(character, query, require_value=True)
        if isinstance(match, list):
            message = "Be more specific. That could mean: " + ", ".join(item["name"] for _, item in match)
            if not _refresh_shop_scene(self, character, message, success=False, title="Multiple Matches"):
                self.msg(message)
            return
        if not match:
            if entries:
                message = "No sellable pack item matches that name."
            else:
                message = "You are not carrying anything this shop will buy."
            if not _refresh_shop_scene(self, character, message, success=False, title="Nothing To Sell"):
                self.msg(message)
            return

        template_id, item = match
        if quantity is None:
            sellables = {entry["template_id"]: entry for entry in get_sellable_entries(character, shop=shop, shop_id=shop_id)}
            quantity = sellables.get(template_id, {}).get("sellable", 0)
        ok, result = sell_inventory_item(character, template_id, quantity)
        if not ok:
            if not _refresh_shop_scene(self, character, result, success=False, title="Can't Sell"):
                self.msg(result)
            return

        quantity_suffix = f" x{result['quantity']}" if result["quantity"] > 1 else ""
        message = f"Sold {result['item_name']}{quantity_suffix} for {result['silver']} silver."
        if not _refresh_shop_scene(self, character, message, success=True, title="Sale Complete"):
            self.msg(f"You sell {result['item_name']}{quantity_suffix} for |w{result['silver']}|n silver.")


class CmdShift(BraveCharacterCommand):
    """
    Help at a shop counter if that shop supports it.

    Usage:
      shift

    Shop counter work is not currently a supported activity.
    """

    key = "shift"
    aliases = ["work", "shopshift"]
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not is_shop_room(character.location):
            message = "You need to be at a shop to help at the counter."
            if not self.deliver_browser_notice(message, title="No Shop", tone="danger", icon="storefront"):
                self.msg(message)
            return
        if character.get_active_encounter():
            message = "This is not the time to step behind the counter."
            if not _refresh_shop_scene(self, character, message, success=False, title="Not Now"):
                self.msg(message)
            return

        _ok, message = run_shop_shift(character)
        if not _refresh_shop_scene(self, character, message, success=False, title="Shop Help Unavailable"):
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
      talk <name>

    Opens the interaction menu for a nearby NPC.
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
            self.msg("Who do you want to talk to?")
            return

        target, npcs = self.find_local_entity(character, self.args.strip(), kind="npc")
        if isinstance(target, list):
            self.msg("Be more specific. That could mean: " + ", ".join(obj.key for obj in target))
            return
        if not target:
            if npcs:
                self.msg("No one here matches that name. You can talk to: " + ", ".join(npc.key for npc in npcs))
            else:
                self.msg("No one here looks free for conversation.")
            return

        from world.browser_views import _build_world_interaction_picker

        self.scene_msg(None, picker=_build_world_interaction_picker(character, target))
        get_entity_response(character, target, "talk", is_action=True)


class CmdBravePopup(BraveCharacterCommand):
    """
    Run lightweight interaction side effects for browser popups.

    Usage:
      _bravepopup talk <name>
      _bravepopup read <name>
    """

    key = "_bravepopup"
    locks = "cmd:all()"
    help_category = "Brave"
    auto_help = False

    def func(self):
        character = self.get_character()
        if not character:
            return

        args = str(self.args or "").strip()
        verb, _, target_name = args.partition(" ")
        verb = verb.lower()
        if verb not in {"talk", "read"} or not target_name.strip():
            return

        kind = "npc" if verb == "talk" else "readable"
        target, _candidates = self.find_local_entity(character, target_name.strip(), kind=kind)
        if not target or isinstance(target, list):
            return

        get_entity_response(character, target, verb, is_action=True)


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
      read <thing>

    Opens the interaction menu for a nearby readable object.
    """

    key = "read"
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return

        if not self.args:
            readable_objects = self.get_local_entities(character, kind="readable")
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
                self.msg("Nothing readable here matches that name. You can read: " + ", ".join(obj.key for obj in readable_objects))
            else:
                self.msg("There is nothing obvious to read here.")
            return

        from world.browser_views import _build_world_interaction_picker

        self.scene_msg(None, picker=_build_world_interaction_picker(character, target))
        get_entity_response(character, target, "read", is_action=True)


class CmdMovie(BraveCharacterCommand):
    """
    Play a Great Frontier movie in the Frontier Picture House.

    Usage:
      movie
      movie <number or title>
      movie stop
    """

    key = "movie"
    aliases = ["watch"]
    help_category = "Brave"

    def _send_movie_audio(self, character, payload):
        session = self.get_web_session()
        print(f"DEBUG: CmdMovie._send_movie_audio - session={session} payload_action={payload.get('action')}")
        if not session:
            return False
        # The brave_movie_audio OOB command in default_out handles both audio and overlay rendering.
        send_webclient_event(character, session=session, brave_movie_audio=payload)
        return True

    def func(self):
        character = self.get_character()
        print(f"DEBUG: CmdMovie.func - character={character} args={self.args}")
        if not character:
            return

        encounter = self.get_encounter(character, require=False)
        if encounter and encounter.is_participant(character):
            self.msg("This is not the moment to watch a movie.")
            return

        if not is_movie_theater_room(character.location):
            self.msg("You need to be in Brambleford's Frontier Picture House to watch Great Frontier movies.")
            return

        query = str(self.args or "").strip()
        if not query:
            if self.get_web_session():
                self.scene_msg(self._movie_list_text(), picker=build_movie_picker())
            else:
                self.msg(self._movie_list_text())
            return

        if query.lower() in {"stop", "off", "quiet", "silence"}:
            self._send_movie_audio(character, {"action": "stop"})
            return

        movie, matches = resolve_movie(query)
        if matches:
            self.msg("Be more specific. That could mean: " + ", ".join(movie_label(entry) for entry in matches))
            return
        if not movie:
            self.msg("No Great Frontier movie matches that. Use |wmovie|n to see the program.")
            return

        sent = self._send_movie_audio(character, build_movie_audio_payload(movie))
        if sent:
            self.msg(brave_picker=build_now_showing_picker(movie))
        else:
            lines = [f"Now showing: {movie_label(movie)}"]
            lines.extend(f"  {card}" for card in movie_cards(movie))
            self.msg("\n".join(lines))
