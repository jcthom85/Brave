"""Equipment upgrade helpers for Ironroot Forge."""

from world.content import get_content_registry
from world.data.items import EQUIPMENT_SLOTS, ITEM_TEMPLATES, format_bonus_summary
from world.race_world_hooks import get_forge_silver_discount

CONTENT = get_content_registry()
SYSTEMS_CONTENT = CONTENT.systems
FORGE_ROOM_ID = SYSTEMS_CONTENT.forge_room_id
FORGE_RECIPES = SYSTEMS_CONTENT.forge_recipes


_UNUSED_FORGE_RECIPES = {
    "militia_blade": {
        "result": "ironroot_longblade",
        "silver": 20,
        "materials": {"goblin_knife": 2, "road_charm": 1},
        "text": "Torren strips the edge down, mutters about wasted iron, and sends the blade back better than it arrived.",
    },
    "oakbound_shield": {
        "result": "nailbound_heater",
        "silver": 18,
        "materials": {"bent_fence_nails": 3, "wolf_pelt": 1},
        "text": "Fresh bands, a tougher face, and a better handgrip later, the shield feels built to answer uglier hits.",
    },
    "roadwarden_mail": {
        "result": "rivetmail_coat",
        "silver": 24,
        "materials": {"wolf_pelt": 2, "goblin_knife": 1},
        "text": "Torren adds cleaner rings, tougher leather backing, and exactly one lecture about traveling light.",
    },
    "ashwood_bow": {
        "result": "ironroot_recurve",
        "silver": 22,
        "materials": {"wolf_fang": 2, "silk_bundle": 1},
        "text": "He tightens the stave, resets the grip, and leaves you with a bow that answers quicker to intent.",
    },
    "trail_knife": {
        "result": "thornline_knife",
        "silver": 16,
        "materials": {"goblin_knife": 1, "wolf_fang": 2},
        "text": "The knife comes back leaner, meaner, and sharpened past the point where bad decisions ought to stop.",
    },
    "field_leathers": {
        "result": "brushrunner_leathers",
        "silver": 22,
        "materials": {"wolf_pelt": 2, "silk_bundle": 1},
        "text": "Torren reinforces the seams and adds quieter fittings meant for brush, rain, and fast exits.",
    },
    "pilgrim_mace": {
        "result": "dawnbell_mace",
        "silver": 22,
        "materials": {"road_charm": 2, "grave_dust": 1},
        "text": "A little rebalance, a little prayer-mark, and the mace leaves the forge with a steadier authority.",
    },
    "sun_prayer_icon": {
        "result": "bellwarden_icon",
        "silver": 18,
        "materials": {"road_charm": 1, "silk_bundle": 1},
        "text": "He braces the icon in clean brass and somehow makes it feel both plainer and more dependable.",
    },
    "wayfarer_vestments": {
        "result": "roadchapel_vestments",
        "silver": 22,
        "materials": {"wolf_pelt": 1, "briar_heart": 1},
        "text": "New clasps, better lining, and a cleaner shoulder cut leave the vestments ready for longer roads.",
    },
    "emberglass_staff": {
        "result": "cinderwire_staff",
        "silver": 24,
        "materials": {"briar_heart": 2, "silk_bundle": 1},
        "text": "Torren rewraps the haft in black wire and resets the glass so the whole staff hums hotter than before.",
    },
    "lantern_focus": {
        "result": "ember_lantern_focus",
        "silver": 20,
        "materials": {"road_charm": 1, "briar_heart": 1},
        "text": "The focus returns in a brass lantern cage, tighter to the hand and brighter to the will.",
    },
    "hedgeweave_robes": {
        "result": "lanternlined_robes",
        "silver": 22,
        "materials": {"wolf_pelt": 1, "silk_bundle": 2},
        "text": "The robes come back better weighted, better lined, and far less interested in catching on bramble or spark.",
    },
    "hookknife_pair": {
        "result": "gutterfang_pair",
        "silver": 20,
        "materials": {"goblin_knife": 2, "wolf_fang": 1},
        "text": "Torren files the hooks meaner, resets the grips, and warns you not to call them pretty just because they finally deserve respect.",
    },
    "parrying_dagger": {
        "result": "smokeglass_dagger",
        "silver": 16,
        "materials": {"road_charm": 1, "silk_bundle": 1},
        "text": "The dagger comes back slimmer, darker, and much more interested in ruining someone else's rhythm.",
    },
    "nightpath_leathers": {
        "result": "shadowtrail_leathers",
        "silver": 22,
        "materials": {"wolf_pelt": 1, "silk_bundle": 1},
        "text": "He tightens the seams, darkens the fittings, and leaves the leathers quieter than your excuses.",
    },
    "chapel_blade": {
        "result": "sunforged_blade",
        "silver": 22,
        "materials": {"road_charm": 2, "grave_dust": 1},
        "text": "Torren trues the edge, sets a cleaner sun-mark into the steel, and hands back a blade that feels steadier than it has any right to.",
    },
    "warded_kite": {
        "result": "bellguard_bastion",
        "silver": 20,
        "materials": {"grave_dust": 1, "barrow_relic": 1},
        "text": "Fresh iron, cleaner rivets, and one quiet chalk mark later, the shield feels built for uglier nights than the last one.",
    },
    "bellkeeper_mail": {
        "result": "wardens_cuirass",
        "silver": 22,
        "materials": {"wolf_pelt": 1, "grave_dust": 1},
        "text": "He closes weak gaps, resets the shoulder, and leaves the mail looking less ceremonial and much more useful.",
    },
    "rootwood_staff": {
        "result": "thorncall_staff",
        "silver": 24,
        "materials": {"moonleaf_sprig": 2, "briar_heart": 1},
        "text": "Torren hardens the grain with moonleaf resin and thornwood heart until the staff answers faster to intent.",
    },
    "grove_talisman": {
        "result": "wildbloom_talisman",
        "silver": 20,
        "materials": {"moonleaf_sprig": 1, "silk_bundle": 1},
        "text": "The charm comes back brighter, better bound, and much less interested in pretending it was ever decorative.",
    },
    "mossweave_wraps": {
        "result": "briarpath_raiment",
        "silver": 22,
        "materials": {"moonleaf_sprig": 1, "silk_bundle": 2},
        "text": "He reinforces the wraps with silk and thorn cord until they feel ready for weather, roots, and the sort of fast choices a trail demands.",
    },
    "ironroot_longblade": {
        "result": "ridgebreaker_blade",
        "silver": 34,
        "materials": {"bandit_mark": 2, "brute_chain_link": 2},
        "text": "Tower steel and goblin chain go into the new edge, and the result feels less like a frontier blade than a final answer.",
    },
    "ironroot_recurve": {
        "result": "warrenspine_recurve",
        "silver": 34,
        "materials": {"tower_arrowhead": 2, "batwing_bundle": 2},
        "text": "Torren resets the limbs with ridge stock and cave leather until the bow snaps back like it owes you speed.",
    },
    "dawnbell_mace": {
        "result": "sunwake_maul",
        "silver": 34,
        "materials": {"bandit_mark": 1, "hexbone_charm": 2},
        "text": "He breaks down the old head, works in warding brass, and hands back a maul meant for uglier crowns than nails ever were.",
    },
    "cinderwire_staff": {
        "result": "slagglass_rod",
        "silver": 36,
        "materials": {"sludge_resin": 2, "hexbone_charm": 1},
        "text": "The new rod comes out of the forge hotter, cleaner, and a little too pleased with itself.",
    },
    "gutterfang_pair": {
        "result": "kingshiv_pair",
        "silver": 34,
        "materials": {"brute_chain_link": 2, "hexbone_charm": 1},
        "text": "Torren binds goblin chain into the spines, evens the pair, and tells you these are the sort of knives ambitious things deserve to meet.",
    },
    "sunforged_blade": {
        "result": "locklight_blade",
        "silver": 36,
        "materials": {"ward_iron_rivet": 2, "hollow_glass_shard": 1},
        "text": "Drowned-line iron and hollow lensglass go into the new edge, and the result feels made for ending lights that learned the wrong lesson about staying lit.",
    },
    "bellguard_bastion": {
        "result": "weirward_bulwark",
        "silver": 34,
        "materials": {"ward_iron_rivet": 2, "silt_hook": 1},
        "text": "He plates the face in old lock iron, resets the grip, and mutters that the bulwark now has the manners of a gate that expects to hold.",
    },
    "wardens_cuirass": {
        "result": "lamplight_harness",
        "silver": 34,
        "materials": {"ward_iron_rivet": 1, "hollow_glass_shard": 1},
        "text": "Torren works drowned-line salvage through the harness until it looks less like armor and more like a promise to keep standing.",
    },
    "thorncall_staff": {
        "result": "marshsong_staff",
        "silver": 36,
        "materials": {"fen_resin_clot": 2, "wispglass_shard": 1},
        "text": "Fen resin sinks into the staff grain and leaves it humming like dark water learning a tune it should not know.",
    },
    "wildbloom_talisman": {
        "result": "fenlight_talisman",
        "silver": 34,
        "materials": {"wispglass_shard": 1, "rotcrow_pinion": 2},
        "text": "The talisman comes back threaded in marsh feather and pale glass, softer in the hand and stronger in the answer.",
    },
    "briarpath_raiment": {
        "result": "reedwoven_raiment",
        "silver": 34,
        "materials": {"mire_hound_hide": 1, "fen_resin_clot": 2},
        "text": "He binds hide and reed cord through the raiment until the whole thing feels ready for wet ground, bad weather, and worse company.",
    },
}


def _get_slot_for_template(template_id):
    """Return the equipment slot for a given template id."""

    return ITEM_TEMPLATES.get(template_id, {}).get("slot")


def is_forge_room(room):
    """Return whether the given room is Ironroot Forge."""

    return getattr(room.db, "brave_room_id", None) == FORGE_ROOM_ID if room else False


def get_forge_entries(character):
    """Return current forge upgrade options for equipped gear."""

    equipment = dict(character.db.brave_equipment or {})
    entries = []

    for slot in EQUIPMENT_SLOTS:
        template_id = equipment.get(slot)
        recipe = FORGE_RECIPES.get(template_id)
        if not recipe:
            continue

        source_item = ITEM_TEMPLATES.get(template_id, {})
        result_template_id = recipe["result"]
        result_item = ITEM_TEMPLATES.get(result_template_id, {})
        materials = []
        silver_cost = max(0, int(recipe["silver"] or 0) - get_forge_silver_discount(character))
        ready = (character.db.brave_silver or 0) >= silver_cost

        for material_id, required in recipe.get("materials", {}).items():
            owned = character.get_inventory_quantity(material_id)
            materials.append(
                {
                    "template_id": material_id,
                    "name": ITEM_TEMPLATES[material_id]["name"],
                    "required": required,
                    "owned": owned,
                }
            )
            if owned < required:
                ready = False

        entries.append(
            {
                "slot": slot,
                "slot_label": slot.replace("_", " ").title(),
                "source_template_id": template_id,
                "source_name": source_item.get("name", template_id),
                "result_template_id": result_template_id,
                "result_name": result_item.get("name", result_template_id),
                "silver_cost": silver_cost,
                "silver_on_hand": character.db.brave_silver or 0,
                "materials": materials,
                "ready": ready,
                "result_bonuses": format_bonus_summary(result_item),
                "text": recipe.get("text", ""),
            }
        )

    entries.sort(key=lambda entry: EQUIPMENT_SLOTS.index(entry["slot"]))
    return entries


def apply_forge_upgrade(character, source_template_id):
    """Apply one forge recipe to the currently equipped item."""

    recipe = FORGE_RECIPES.get(source_template_id)
    if not recipe:
        return False, "Torren doesn't have a standing upgrade plan for that piece."

    slot = _get_slot_for_template(source_template_id)
    equipped = (character.db.brave_equipment or {}).get(slot)
    if equipped != source_template_id:
        return False, "You need to be wearing the piece you want Torren to rework."

    silver_cost = max(0, int(recipe["silver"] or 0) - get_forge_silver_discount(character))
    if (character.db.brave_silver or 0) < silver_cost:
        return False, f"You need {silver_cost} silver for that rework."

    missing = []
    for material_id, required in recipe.get("materials", {}).items():
        owned = character.get_inventory_quantity(material_id)
        if owned < required:
            missing.append(f"{ITEM_TEMPLATES[material_id]['name']} {owned}/{required}")

    if missing:
        return False, "You are still short on: " + ", ".join(missing)

    for material_id, required in recipe.get("materials", {}).items():
        if not character.remove_item_from_inventory(material_id, required):
            return False, "Torren pauses. Your pack contents no longer match the order."

    character.db.brave_silver = max(0, (character.db.brave_silver or 0) - silver_cost)
    equipment = dict(character.db.brave_equipment or {})
    equipment[slot] = recipe["result"]
    character.db.brave_equipment = equipment
    character.recalculate_stats()

    result_item = ITEM_TEMPLATES[recipe["result"]]
    result = {
        "slot": slot,
        "slot_label": slot.replace("_", " ").title(),
        "item_name": result_item["name"],
        "bonus_summary": format_bonus_summary(result_item),
        "silver_cost": silver_cost,
        "text": recipe.get("text", ""),
    }
    return True, result
