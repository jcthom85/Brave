"""Mobile companion payload builders for the room browser view."""

from world.browser_context import (
    CLASSES,
    ITEM_TEMPLATES,
    QUESTS,
    RACES,
    STARTING_QUESTS,
    get_item_category,
    get_quest_region,
)
from world.browser_inventory_views import PACK_KIND_LABELS, PACK_KIND_ORDER, _pack_item_subtitle
from world.browser_journal_views import _format_objective_progress
from world.chapel import get_active_blessing
from world.class_features import get_class_features
from world.party import get_character_by_id, get_follow_target, get_party_leader, get_party_members
from world.questing import get_tracked_quest
from world.resonance import get_resource_label, get_stat_label

def _build_mobile_pack_payload(character):
    inventory = list(character.db.brave_inventory or [])
    inventory.sort(key=lambda entry: ITEM_TEMPLATES.get(entry.get("template"), {}).get("name", entry.get("template", "")))
    item_types = 0
    consumables = 0
    ingredients = 0
    preview = []
    grouped = {kind: [] for kind in PACK_KIND_ORDER}
    other_items = []

    for entry in inventory:
        template_id = entry.get("template")
        if not template_id:
            continue
        item_types += 1
        quantity = max(0, int(entry.get("quantity", 0) or 0))
        template = ITEM_TEMPLATES.get(template_id, {})
        kind = template.get("kind")
        category = get_item_category(template)
        if category == "consumable":
            consumables += quantity
        elif kind == "ingredient":
            ingredients += quantity

        if kind == "equipment":
            icon_name = "shield"
        elif kind == "meal":
            icon_name = "lunch_dining"
        elif category == "consumable":
            icon_name = "restaurant"
        elif category == "ingredient":
            icon_name = "kitchen"
        elif category == "loot":
            icon_name = "category"
        else:
            icon_name = "backpack"

        if item_types <= 60:
            preview.append(
                {
                    "label": template.get("name", template_id.replace("_", " ").title()),
                    "quantity": quantity,
                    "icon": icon_name,
                }
            )
        packed_item = {
            "label": template.get("name", template_id.replace("_", " ").title()),
            "quantity": quantity,
            "icon": icon_name,
            "meta": _pack_item_subtitle(template),
        }
        if category in grouped:
            grouped[category].append(packed_item)
        else:
            other_items.append(packed_item)

    sections = []
    for kind in PACK_KIND_ORDER:
        if grouped[kind]:
            label, icon = PACK_KIND_LABELS[kind]
            sections.append(
                {
                    "label": label,
                    "icon": icon,
                    "count": sum(item["quantity"] for item in grouped[kind]),
                    "items": grouped[kind][:8],
                    "overflow": max(0, len(grouped[kind]) - 8),
                }
            )
    if other_items:
        sections.append(
            {
                "label": "Other",
                "icon": "backpack",
                "count": sum(item["quantity"] for item in other_items),
                "items": other_items[:8],
                "overflow": max(0, len(other_items) - 8),
            }
        )

    return {
        "silver": character.db.brave_silver or 0,
        "item_types": item_types,
        "consumables": consumables,
        "ingredients": ingredients,
        "preview": [{"label": entry["label"], "quantity": entry["quantity"]} for entry in preview[:4]],
        "items": preview,
        "overflow": max(0, item_types - len(preview)),
        "sections": sections,
    }

def _build_mobile_character_payload(character):
    race_key = str(getattr(character.db, "brave_race", "human") or "human").lower()
    class_key = str(getattr(character.db, "brave_class", "warrior") or "warrior").lower()
    race = RACES.get(race_key, RACES["human"])
    class_data = CLASSES.get(class_key, CLASSES["warrior"])
    level = int(getattr(character.db, "brave_level", 1) or 1)
    primary = getattr(character.db, "brave_primary_stats", None) or {}
    derived = getattr(character.db, "brave_derived_stats", None) or {}
    resources = getattr(character.db, "brave_resources", None) or {}
    blessing = get_active_blessing(character)
    features = list(get_class_features(class_key) or [])

    stats = [
        {"label": get_stat_label("attack_power", character), "value": str(derived.get("attack_power", 0))},
        {"label": get_stat_label("armor", character), "value": str(derived.get("armor", 0))},
        {"label": get_stat_label("accuracy", character), "value": str(derived.get("accuracy", 0))},
        {"label": get_stat_label("dodge", character), "value": str(derived.get("dodge", 0))},
    ]
    if derived.get("spell_power", 0):
        stats.insert(1, {"label": get_stat_label("spell_power", character), "value": str(derived.get("spell_power", 0))})

    effects = []
    if blessing:
        effects.append(blessing.get("name", "Blessing"))
    if race.get("perk"):
        effects.append(race["perk"])

    return {
        "name": character.key,
        "identity": f"{race['name']} {class_data['name']} · Level {level}",
        "summary": class_data["summary"],
        "resources": [
            {"label": get_resource_label("hp", character), "value": f"{resources.get('hp', 0)} / {derived.get('max_hp', 0)}"},
            {"label": get_resource_label("mana", character), "value": f"{resources.get('mana', 0)} / {derived.get('max_mana', 0)}"},
            {"label": get_resource_label("stamina", character), "value": f"{resources.get('stamina', 0)} / {derived.get('max_stamina', 0)}"},
        ],
        "attributes": [
            {"label": get_stat_label("strength", character), "value": str(primary.get("strength", 0))},
            {"label": get_stat_label("agility", character), "value": str(primary.get("agility", 0))},
            {"label": get_stat_label("intellect", character), "value": str(primary.get("intellect", 0))},
            {"label": get_stat_label("spirit", character), "value": str(primary.get("spirit", 0))},
            {"label": get_stat_label("vitality", character), "value": str(primary.get("vitality", 0))},
        ],
        "stats": stats,
        "feature": (features[0] if features else {}),
        "effects": effects,
    }

def _build_mobile_quests_payload(character):
    quest_state = getattr(character.db, "brave_quests", None) or {}
    tracked_key = get_tracked_quest(character)
    active_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if quest_state.get(quest_key, {}).get("status") == "active"
    ]
    completed_keys = [
        quest_key
        for quest_key in STARTING_QUESTS
        if quest_state.get(quest_key, {}).get("status") == "completed"
    ]

    def summarize(quest_key):
        definition = QUESTS.get(quest_key, {})
        state = quest_state.get(quest_key, {})
        objectives = list(state.get("objectives", []))
        remaining = [objective for objective in objectives if not objective.get("completed")]
        next_objective = remaining[0] if remaining else None
        return {
            "title": definition.get("title", quest_key.replace("_", " ").title()),
            "meta": f"{get_quest_region(quest_key)} · {definition.get('giver', '')}".strip(" ·"),
            "line": _format_objective_progress(next_objective) if next_objective else definition.get("summary", ""),
        }

    tracked = summarize(tracked_key) if tracked_key else None
    if tracked:
        tracked["objectives"] = [
            {
                "text": _format_objective_progress(objective),
                "completed": bool(objective.get("completed")),
            }
            for objective in list(quest_state.get(tracked_key, {}).get("objectives", []))[:5]
        ]

    return {
        "tracked": tracked,
        "active_count": len(active_keys),
        "completed_count": len(completed_keys),
        "active": [summarize(quest_key) for quest_key in active_keys[:5]],
        "completed": [summarize(quest_key) for quest_key in completed_keys[:3]],
    }

def _build_mobile_party_payload(character):
    try:
        members = list(get_party_members(character) or [])
        leader = get_party_leader(character)
        follow_target = get_follow_target(character)
        invites = [
            leader_obj
            for leader_obj in (
                get_character_by_id(invite_id) for invite_id in (getattr(character.db, "brave_party_invites", None) or [])
            )
            if leader_obj
        ]
    except Exception:
        members = []
        leader = None
        follow_target = None
        invites = []

    member_entries = []
    for member in members[:5]:
        resources = member.db.brave_resources or {}
        derived = member.db.brave_derived_stats or {}
        member_entries.append(
            {
                "name": member.key,
                "meta": "Leader" if leader and member.id == leader.id else "Member",
                "line": member.location.key if member.location else "Nowhere",
                "resource": f"HP {resources.get('hp', 0)} / {derived.get('max_hp', 0)}",
            }
        )

    return {
        "in_party": bool(members),
        "leader_name": getattr(leader, "key", "") if leader else "",
        "member_count": len(members),
        "follow_target": getattr(follow_target, "key", "") if follow_target else "",
        "members": member_entries,
        "invites": [invite.key for invite in invites[:4]],
    }

def _build_mobile_room_payload(room, looker, nav_items, vertical_exits, special_exits, vicinity_items, room_action_items):
    route_items = []
    for entry in list(nav_items) + list(vertical_exits):
        route_items.append(
            {
                "label": entry.get("label") or entry.get("direction", "").title(),
                "badge": entry.get("badge", ""),
                "command": entry.get("command"),
            }
        )
    for entry in special_exits[:6]:
        route_items.append(
            {
                "label": entry.get("text", ""),
                "badge": entry.get("badge", ""),
                "command": entry.get("command"),
            }
        )

    vicinity = []
    for item in vicinity_items[:8]:
        vicinity.append(
            {
                "text": item.get("text", ""),
                "detail": item.get("detail", ""),
                "badge": item.get("badge", ""),
                "icon": item.get("marker_icon") or item.get("icon") or "chevron_right",
                "command": item.get("command"),
            }
        )

    return {
        "title": room.key,
        "description": room.db.desc or "A place of mystery and potential.",
        "status_label": "Danger" if not room.db.brave_safe else "Safe",
        "status_copy": "Stay ready for a fight." if not room.db.brave_safe else "No immediate threats nearby.",
        "route_count": len(route_items),
        "routes": route_items,
        "vicinity": vicinity,
        "actions": [
            {
                "label": action.get("label", ""),
                "command": action.get("command"),
                "icon": action.get("icon") or "chevron_right",
            }
            for action in room_action_items[:6]
            if action.get("command")
        ],
        "character": _build_mobile_character_payload(looker),
        "pack": _build_mobile_pack_payload(looker),
        "quests": _build_mobile_quests_payload(looker),
        "party": _build_mobile_party_payload(looker),
    }
