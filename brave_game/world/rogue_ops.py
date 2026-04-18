"""Rogue-exclusive theft and illicit-access helpers."""

from world.data.items import ITEM_TEMPLATES

STEAL_TARGETS = {
    "courier_peep_marrow": {
        "summary": "Peep keeps route tags, spare twine, and the sort of quick pocket clutter couriers stop noticing.",
        "silver": 5,
        "items": (("bandit_mark", 1),),
        "success_text": "You lift a route token and a little travel silver before Peep notices anything missing.",
    },
    "uncle_pib_underbough": {
        "summary": "The innkeeper's apron is a shifting ecosystem of ladles, chalk, and a few loose counter coins.",
        "silver": 4,
        "items": (("field_bandage", 1),),
        "success_text": "You slip a few coins and a neatly folded bandage packet from Pib's clutter without slowing the kitchen.",
    },
    "leda_thornwick": {
        "summary": "Leda's counter is too well-run for a full pinch, but sample stock and margin chalk still move through her sleeves.",
        "silver": 6,
        "items": (("bent_fence_nails", 1),),
        "success_text": "You ghost away with a handful of silver and a useful bit of stock while Leda is busy measuring someone else for disappointment.",
    },
    "joss_veller": {
        "summary": "Joss carries lens scraps, route notes, and whatever odd salvage he has not decided is important yet.",
        "silver": 3,
        "items": (("anchor_glass_shard", 1),),
        "success_text": "You palm a bright route-glass shard and a few forgotten coins while Joss is arguing with the sky.",
    },
    "torren_ironroot": {
        "summary": "Torren's forge apron is all rivets, chalk stubs, and little pieces of metal too practical to leave lying around.",
        "silver": 4,
        "items": (("ward_iron_rivet", 1),),
        "success_text": "You come away with a useful rivet and some hard silver while Torren is more interested in the anvil than his apron.",
    },
}


def get_steal_target(entity_id):
    """Return authored theft data for one entity."""

    return dict(STEAL_TARGETS.get(str(entity_id or "").lower(), {}))


def get_available_steal_targets(entities):
    """Filter a local entity list down to authored theft targets."""

    available = []
    for entity in entities or []:
        entity_id = getattr(getattr(entity, "db", None), "brave_entity_id", None)
        target = get_steal_target(entity_id)
        if target:
            available.append((entity, target))
    return available


def attempt_theft(character, entity):
    """Attempt one authored theft interaction from a local NPC."""

    if getattr(getattr(character, "db", None), "brave_class", None) != "rogue":
        return False, "Only a Rogue knows how to make that kind of lift cleanly.", None

    entity_id = getattr(getattr(entity, "db", None), "brave_entity_id", None)
    target = get_steal_target(entity_id)
    if not target:
        return False, f"{getattr(entity, 'key', 'That target')} offers no obvious clean lift.", None

    theft_log = dict(getattr(getattr(character, "db", None), "brave_rogue_theft_log", None) or {})
    if theft_log.get(entity_id):
        return False, f"You have already worked that angle on {getattr(entity, 'key', 'that target')}.", None

    rewards = []
    silver = int(target.get("silver", 0) or 0)
    if silver > 0:
        character.db.brave_silver = int(getattr(character.db, "brave_silver", 0) or 0) + silver
        rewards.append(f"{silver} silver")

    for template_id, quantity in target.get("items", ()):
        if template_id in ITEM_TEMPLATES and quantity > 0:
            character.add_item_to_inventory(template_id, quantity, count_for_collection=False)
            item_name = ITEM_TEMPLATES[template_id]["name"]
            rewards.append(item_name + (f" x{quantity}" if quantity > 1 else ""))

    theft_log[entity_id] = {
        "target": getattr(entity, "key", entity_id),
        "rewards": rewards,
    }
    character.db.brave_rogue_theft_log = theft_log

    result = {
        "entity_id": entity_id,
        "target_name": getattr(entity, "key", entity_id),
        "rewards": rewards,
        "silver": silver,
        "items": list(target.get("items", ())),
        "summary": target.get("summary", ""),
        "success_text": target.get("success_text", ""),
    }
    return True, target.get("success_text", "You make a clean lift."), result
