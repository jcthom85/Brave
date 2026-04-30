"""Town service and activity browser view payload builders."""

from world.activities import (
    can_borrow_fishing_tackle,
    get_available_fishing_lures,
    get_available_fishing_rods,
    get_cooking_entries,
    get_fishing_spot_summary,
)
from world.browser_context import ITEM_TEMPLATES
from world.browser_formatting import _format_context_bonus_summary, _format_restore_summary
from world.browser_ui import (
    _action,
    _chip,
    _entry,
    _make_view,
    _reactive_from_character,
    _section,
)
from world.commerce import format_shop_bonus, get_reserved_entries, get_sellable_entries, get_shop_bonus
from world.forging import get_forge_entries
from world.item_rarity import build_item_rarity_display
from world.tinkering import get_tinkering_entries

def build_shop_view(character):
    """Return a browser-first main view for the Outfitters."""

    bonus = get_shop_bonus(character)
    sellables = get_sellable_entries(character)
    reserved = get_reserved_entries(character)

    sellable_entries = []
    for entry in sellables:
        template = ITEM_TEMPLATES.get(entry["template_id"], {})
        lines = [f"{entry['unit_price']} silver each · {entry['total_price']} silver total"]
        if entry["reserved"]:
            lines.append(f"Holding {entry['reserved']} for active quest progress")
        sellable_entries.append(
            _entry(
                f"{entry['name']} x{entry['sellable']}",
                lines=lines,
                summary=template.get("summary"),
                icon="sell",
                command=f"sell {entry['name']}",
                **build_item_rarity_display(template),
                actions=[
                    _action("Sell 1", f"sell {entry['name']}", "sell")
                ] + (
                    [
                        _action(
                            "Sell All",
                            f"sell {entry['name']} = all",
                            "layers",
                            tone="danger",
                            confirm=f"Sell all available {entry['name']}?",
                        )
                    ]
                    if entry["sellable"] > 1
                    else []
                ),
            )
        )

    chips = [
        _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
    ]
    if bonus:
        chips.append(_chip(format_shop_bonus(bonus), "storefront", "good"))

    return _make_view(
        "Town Service",
        "Brambleford Outfitters",
        eyebrow_icon="storefront",
        title_icon="sell",
        subtitle="Leda buys practical finds and pays in clean town silver.",
        chips=chips,
        actions=[] if bonus else [_action("Work Shift", "shift", "front_hand", tone="accent")],
        sections=[
            _section(
                "Sell",
                "sell",
                "entries",
                items=sellable_entries or [_entry("Nothing sellable right now.", icon="inventory_2")],
            ),
            _section(
                "Reserved",
                "assignment",
                "list",
                items=[{"text": f"{entry['name']} x{entry['reserved']}", "icon": "lock"} for entry in reserved]
                or [{"text": "Nothing currently reserved.", "icon": "info"}],
            ),
        ],
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )

def build_forge_view(character):
    """Return a browser-first main view for forge orders."""

    entries = get_forge_entries(character)
    ready_entries = []
    pending_entries = []

    for entry in entries:
        material_text = ", ".join(
            f"{material['name']} {material['owned']}/{material['required']}"
            for material in entry["materials"]
        )
        lines = [
            f"{entry['slot_label']} · {entry['silver_cost']} silver",
            "Materials: " + material_text if material_text else "No extra materials needed",
        ]
        if entry["result_bonuses"]:
            lines.append("Result: " + entry["result_bonuses"])
        command = None
        confirm = None
        actions = []
        if entry["ready"]:
            command = f"forge {entry['source_name']}"
            confirm = f"Forge {entry['result_name']} for {entry['silver_cost']} silver?"
            actions.append(_action("Forge", command, "construction", tone="accent", confirm=confirm))
        formatted = _entry(
            f"{entry['source_name']} -> {entry['result_name']}",
            lines=lines,
            summary=entry.get("text", ""),
            icon="construction" if entry["ready"] else "schedule",
            command=command,
            confirm=confirm,
            actions=actions,
        )
        if entry["ready"]:
            ready_entries.append(formatted)
        else:
            pending_entries.append(formatted)

    ready_count = sum(1 for entry in entries if entry["ready"])
    chips = [
        _chip(f"{character.db.brave_silver or 0} silver", "savings", "accent"),
        _chip(f"{ready_count} ready", "task_alt", "good" if ready_count else "muted"),
    ]

    return _make_view(
        "Town Service",
        "Forge",
        eyebrow_icon="construction",
        title_icon="build",
        subtitle="Torren can rework your equipped field kit into sturdier frontier gear.",
        chips=chips,
        sections=[
            _section(
                "Ready",
                "construction",
                "entries",
                items=ready_entries or [_entry("Nothing is fully ready yet.", icon="schedule")],
            ),
            _section(
                "Needs Materials",
                "inventory",
                "entries",
                items=pending_entries or [_entry("No pending orders.", icon="task_alt")],
            ),
        ],
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )

def build_cook_view(character, *, status_message=None, status_tone="muted"):
    """Return a browser-first main view for the hearth and meal loop."""

    ready_entries = []
    known_entries = []
    locked_entries = []
    meal_entries = []

    for recipe in get_cooking_entries(character):
        missing = list(recipe["missing"])
        lines = [recipe["ingredient_text"], "Ready to cook" if recipe["ready"] else ("Missing: " + ", ".join(missing) if recipe["known"] else "Locked recipe")]
        formatted = _entry(
            recipe["name"],
            lines=lines,
            summary=recipe["summary"] if recipe["known"] else (recipe["unlock_text"] or "You have not learned this recipe yet."),
            icon="restaurant" if recipe["ready"] else ("kitchen" if recipe["known"] else "lock"),
            command=f"cook {recipe['name']}" if recipe["ready"] else None,
            actions=[_action("Cook", f"cook {recipe['name']}", "restaurant", tone="accent")] if recipe["ready"] else [],
        )
        if not recipe["known"]:
            locked_entries.append(formatted)
        elif recipe["ready"]:
            ready_entries.append(formatted)
        else:
            known_entries.append(formatted)

    for entry in (character.db.brave_inventory or []):
        template_id = entry.get("template")
        quantity = entry.get("quantity", 0)
        item = ITEM_TEMPLATES.get(template_id, {})
        if item.get("kind") != "meal" or quantity <= 0:
            continue

        restore_text = _format_restore_summary(item.get("restore", {}), character)
        bonus_text = _format_context_bonus_summary(item.get("meal_bonuses", {}), character)
        lines = [text for text in (restore_text and "Restore: " + restore_text, bonus_text and "Buff: " + bonus_text) if text]
        meal_entries.append(
            _entry(
                item.get("name", template_id) + (f" x{quantity}" if quantity > 1 else ""),
                lines=lines,
                summary=item.get("summary"),
                icon="lunch_dining",
                command=f"eat {item.get('name', template_id)}",
                actions=[_action("Eat", f"eat {item.get('name', template_id)}", "restaurant", tone="good")],
            )
        )

    chips = [
        _chip(f"{len(ready_entries)} ready", "task_alt", "good" if ready_entries else "muted"),
    ]
    if meal_entries:
        chips.append(_chip(f"{len(meal_entries)} meals packed", "lunch_dining", "accent"))

    sections = []
    if status_message:
        status_icon = "task_alt" if status_tone == "good" else "info"
        sections.append(
            _section(
                "Kitchen Notes",
                status_icon,
                "lines",
                lines=[status_message],
                span="wide",
            )
        )

    sections.extend(
        [
            _section("Ready", "restaurant", "entries", items=ready_entries or [_entry("Nothing is ready from your current ingredients.", icon="schedule")]),
            _section("Known", "grocery", "entries", items=known_entries or [_entry("No other known recipes are waiting on ingredients.", icon="task_alt")]),
            _section("Locked", "lock", "entries", items=locked_entries or [_entry("No locked recipes right now.", icon="task_alt")]),
            _section("Meals", "lunch_dining", "entries", items=meal_entries or [_entry("You are not carrying any prepared meals.", icon="backpack")]),
        ]
    )

    return _make_view(
        "Town Service",
        "Hearth",
        eyebrow_icon="restaurant",
        title_icon="soup_kitchen",
        subtitle="Simple inn recipes you can turn out without wasting the room or the pan.",
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )

def build_fishing_view(character, *, status_message=None, status_tone="muted"):
    """Return a browser-first main view for fishing tackle setup."""

    summary = get_fishing_spot_summary(character)
    spot = summary["spot"] or {}
    current_rod = summary["rod"] or {}
    current_lure = summary["lure"] or {}
    room = getattr(character, "location", None)
    fishing_state = getattr(getattr(character, "ndb", None), "brave_fishing", None) or {}
    fishing_phase = fishing_state.get("phase")
    active_rod_key = current_rod.get("key")
    active_lure_key = current_lure.get("key")

    rod_entries = []
    for rod_data in get_available_fishing_rods(character, include_locked=True):
        rod_key = rod_data["key"]
        selected = rod_key == active_rod_key
        rod_entries.append(
            _entry(
                rod_data.get("name", rod_key.replace("_", " ").title()),
                lines=[
                    f"Power {int(rod_data.get('power', 0) or 0)}",
                    f"Stability {rod_data.get('stability', 0)}",
                ],
                summary=rod_data.get("summary") if rod_data.get("available", True) else (rod_data.get("unlock_text") or "Locked until you prove yourself further."),
                icon="straighten",
                command=None if selected or not rod_data.get("available", True) else f"fish rod {rod_data.get('name', rod_key)}",
                actions=[] if selected or not rod_data.get("available", True) else [_action("Select", f"fish rod {rod_data.get('name', rod_key)}", "straighten", tone="accent")],
                badge="Selected" if selected else (None if rod_data.get("available", True) else "Locked"),
                selected=selected,
            )
        )

    lure_entries = []
    for lure_data in get_available_fishing_lures(character, include_locked=True):
        lure_key = lure_data["key"]
        selected = lure_key == active_lure_key
        favored = ", ".join(ITEM_TEMPLATES[item_id]["name"] for item_id in lure_data.get("attracts", []) if item_id in ITEM_TEMPLATES)
        lines = []
        if favored:
            lines.append("Favored: " + favored)
        zone_bonus = (lure_data.get("zone_bonus", {}) or {}).get(getattr(getattr(room, "db", None), "brave_room_id", None), 0)
        if zone_bonus:
            lines.append(f"Water bonus {zone_bonus}")
        lure_entries.append(
            _entry(
                lure_data.get("name", lure_key.replace("_", " ").title()),
                lines=lines,
                summary=lure_data.get("summary") if lure_data.get("available", True) else (lure_data.get("unlock_text") or "Locked until you prove yourself further."),
                icon="tune",
                command=None if selected or not lure_data.get("available", True) else f"fish lure {lure_data.get('name', lure_key)}",
                actions=[] if selected or not lure_data.get("available", True) else [_action("Select", f"fish lure {lure_data.get('name', lure_key)}", "tune", tone="accent")],
                badge="Selected" if selected else (None if lure_data.get("available", True) else "Locked"),
                selected=selected,
            )
        )

    chips = []
    if current_rod:
        chips.append(_chip(current_rod.get("name", "Rod"), "straighten", "accent"))
    if current_lure:
        chips.append(_chip(current_lure.get("name", "Lure"), "tune", "muted"))
    if fishing_phase == "waiting":
        chips.append(_chip("Line In Water", "waves", "good"))
    elif fishing_phase == "bite":
        chips.append(_chip("Bite", "phishing", "warn"))
    elif fishing_phase == "minigame":
        chips.append(_chip("Line Active", "phishing", "good"))

    actions = []
    if can_borrow_fishing_tackle(character):
        actions.append(_action("Borrow Kit", "fish borrow kit", "inventory_2", tone="muted"))
    if fishing_phase == "bite":
        actions.append(_action("Reel", "reel", "phishing", tone="accent"))
    elif fishing_phase not in {"waiting", "minigame"}:
        actions.append(_action("Cast Line", "fish cast", "phishing", tone="accent"))

    water_lines = [spot.get("cast_text", "The water looks workable.")]
    if fishing_phase == "waiting":
        water_lines.append("Your line is in the water. Wait for a real bite.")
    elif fishing_phase == "bite":
        water_lines.append("Something is on the line. Reel now.")
    elif fishing_phase == "minigame":
        water_lines.append("Your line is active. Work the fishing popup to land it.")

    sections = []
    if status_message:
        sections.append(
            _section(
                "River Notes",
                "task_alt" if status_tone == "good" else "info",
                "lines",
                lines=[status_message],
                span="wide",
            )
        )
    sections.append(
        _section(
            "Current Water",
            "waves",
            "entries",
            items=[
                _entry(
                    spot.get("name", room.key if room else "Fishing Water"),
                    lines=water_lines,
                    icon="waves",
                    actions=(
                        ([_action("Borrow Kit", "fish borrow kit", "inventory_2", tone="muted")] if can_borrow_fishing_tackle(character) else [])
                        + ([_action("Reel", "reel", "phishing", tone="accent")] if fishing_phase == "bite" else [])
                        + ([_action("Cast", "fish cast", "phishing", tone="accent")] if fishing_phase not in {"waiting", "bite", "minigame"} else [])
                    ),
                )
            ],
        )
    )
    sections.append(
        _section(
            "Active Tackle",
            "inventory_2",
            "entries",
            items=[
                _entry(
                    current_rod.get("name", "No rod selected"),
                    meta="Rod",
                    lines=[current_rod.get("summary", "")],
                    icon="straighten",
                ),
                _entry(
                    current_lure.get("name", "No lure selected"),
                    meta="Lure",
                    lines=[current_lure.get("summary", "")],
                    icon="tune",
                ),
            ],
        )
    )
    sections.append(_section("Rods", "straighten", "entries", items=rod_entries or [_entry("No rods are available.", icon="block")]))
    sections.append(_section("Lures", "tune", "entries", items=lure_entries or [_entry("No lures are available.", icon="block")]))

    return _make_view(
        "Town Activity",
        "Fishing",
        eyebrow_icon="phishing",
        title_icon="waves",
        subtitle="Cast a line, read the water, and swap tackle when the catch calls for it.",
        chips=chips,
        sections=sections,
        actions=actions,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )

def build_tinker_view(character, *, status_message=None, status_tone="muted"):
    """Return a browser-first main view for tinkering recipes."""

    ready_entries = []
    known_entries = []
    locked_entries = []
    for entry in get_tinkering_entries(character):
        lines = []
        if entry["base_name"]:
            lines.append(f"Base: {entry['base_name']} {entry['base_owned']}/1")
        if entry["components"]:
            lines.append(
                "Parts: "
                + ", ".join(f"{row['name']} {row['owned']}/{row['required']}" for row in entry["components"])
            )
        if entry["silver_cost"]:
            lines.append(f"Silver: {entry['silver_cost']}")
        if entry["result_bonuses"]:
            lines.append("Result: " + entry["result_bonuses"])
        payload = _entry(
            entry["name"],
            lines=lines,
            summary=entry["summary"] or entry["result_summary"],
            icon="handyman" if entry["ready"] else "inventory_2",
            command=f"tinker {entry['name']}" if entry["ready"] else None,
            actions=[_action("Build", f"tinker {entry['name']}", "build", tone="accent")] if entry["ready"] else [],
            badge="Ready" if entry["ready"] else ("Known" if entry["known"] else "Locked"),
        )
        if not entry["known"]:
            locked_entries.append(payload)
        elif entry["ready"]:
            ready_entries.append(payload)
        else:
            known_entries.append(payload)

    chips = [_chip(f"{character.db.brave_silver or 0} silver", "payments", "muted")]
    if ready_entries:
        chips.append(_chip(f"{len(ready_entries)} ready", "task_alt", "good"))

    sections = []
    if status_message:
        sections.append(_section("Bench Notes", "task_alt" if status_tone == "good" else "info", "lines", lines=[status_message], span="wide"))
    sections.extend(
        [
            _section("Ready Now", "build", "entries", items=ready_entries or [_entry("Nothing is ready from your current pack.", icon="schedule")]),
            _section("Known Designs", "inventory_2", "entries", items=known_entries or [_entry("No other known designs are close to completion.", icon="construction")]),
            _section("Locked Designs", "lock", "entries", items=locked_entries or [_entry("No locked tinkering designs yet.", icon="task_alt")]),
        ]
    )

    return _make_view(
        "Town Service",
        "Workbench Ledger",
        eyebrow_icon="build",
        title_icon="handyman",
        subtitle="Small frontier repairs, field fixes, and rough bench work that keeps a pack useful.",
        chips=chips,
        sections=sections,
        back=True,
        reactive=_reactive_from_character(character, scene="service"),
    )
