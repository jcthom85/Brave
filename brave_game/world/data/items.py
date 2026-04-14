"""Starter gear and loot templates for Brave's first slice."""

EQUIPMENT_SLOTS = (
    "main_hand",
    "off_hand",
    "head",
    "chest",
    "hands",
    "legs",
    "feet",
    "ring",
    "trinket",
    "snack",
)

ITEM_TEMPLATES = {
    "militia_blade": {
        "name": "Militia Blade",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A sturdy frontier sword with just enough weight behind it.",
        "bonuses": {"attack_power": 4, "accuracy": 3},
    },
    "oakbound_shield": {
        "name": "Oakbound Shield",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A scarred but reliable shield reinforced by practical iron bands.",
        "bonuses": {"armor": 4, "max_hp": 10, "threat": 2},
    },
    "roadwarden_mail": {
        "name": "Roadwarden Mail",
        "kind": "equipment",
        "slot": "chest",
        "summary": "A patched shirt of mail that favors endurance over elegance.",
        "bonuses": {"armor": 3, "max_stamina": 6},
    },
    "ashwood_bow": {
        "name": "Ashwood Bow",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A travel bow with a quick draw and a forgiving pull.",
        "bonuses": {"attack_power": 4, "accuracy": 5},
    },
    "trail_knife": {
        "name": "Trail Knife",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A belt knife meant for camp work, skinning, and close trouble.",
        "bonuses": {"attack_power": 1, "accuracy": 2, "dodge": 1},
    },
    "field_leathers": {
        "name": "Field Leathers",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Light leather layers treated to turn rain, brush, and shallow cuts.",
        "bonuses": {"armor": 2, "dodge": 2, "max_stamina": 5},
    },
    "pilgrim_mace": {
        "name": "Pilgrim Mace",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A compact mace carried as much for certainty as ceremony.",
        "bonuses": {"attack_power": 2, "spell_power": 2, "accuracy": 2},
    },
    "sun_prayer_icon": {
        "name": "Sun Prayer Icon",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A worn devotional icon that steadies the hand and focuses the spirit.",
        "bonuses": {"spell_power": 3, "max_mana": 10},
    },
    "wayfarer_vestments": {
        "name": "Wayfarer Vestments",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Travel-ready robes stitched for mud, weather, and long prayers.",
        "bonuses": {"armor": 2, "max_hp": 6, "max_mana": 6},
    },
    "emberglass_staff": {
        "name": "Emberglass Staff",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A slim ash staff tipped with red glass that holds heat longer than it should.",
        "bonuses": {"spell_power": 5, "accuracy": 2},
    },
    "lantern_focus": {
        "name": "Lantern Focus",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A palm-sized focus crystal wrapped in brass wire from old Brambleford lanterns.",
        "bonuses": {"spell_power": 2, "max_mana": 10},
    },
    "hedgeweave_robes": {
        "name": "Hedgeweave Robes",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Practical apprentice robes lined against cold drafts and stray sparks.",
        "bonuses": {"armor": 1, "max_hp": 4, "max_mana": 10, "dodge": 1},
    },
    "hookknife_pair": {
        "name": "Hookknife Pair",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A matched set of compact hookknives made for ugly work in close quarters and quicker exits after.",
        "bonuses": {"attack_power": 4, "accuracy": 4, "precision": 1},
    },
    "parrying_dagger": {
        "name": "Parrying Dagger",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A narrow off-hand blade balanced to catch steel, hands, or attention at exactly the wrong moment for the other person.",
        "bonuses": {"attack_power": 1, "accuracy": 2, "dodge": 2},
    },
    "nightpath_leathers": {
        "name": "Nightpath Leathers",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Dark fitted leathers cut light through the shoulder and quiet through the buckle.",
        "bonuses": {"armor": 2, "dodge": 3, "max_stamina": 5},
    },
    "chapel_blade": {
        "name": "Chapel Blade",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A straight practical sword kept for road duty, oath work, and the sort of bad nights that require both.",
        "bonuses": {"attack_power": 3, "spell_power": 1, "accuracy": 2, "threat": 1},
    },
    "warded_kite": {
        "name": "Warded Kite",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A chapel-kept kite shield marked in chalk prayer and brass nailwork.",
        "bonuses": {"armor": 4, "max_hp": 8, "max_stamina": 4, "threat": 2},
    },
    "bellkeeper_mail": {
        "name": "Bellkeeper Mail",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Ring-backed mail built for patrol, prayer, and hauling frightened people behind you.",
        "bonuses": {"armor": 3, "max_hp": 8, "max_stamina": 4, "spirit": 1},
    },
    "rootwood_staff": {
        "name": "Rootwood Staff",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A living wood staff polished by use rather than ceremony, light in the hand and stubborn in the grain.",
        "bonuses": {"spell_power": 5, "accuracy": 2, "spirit": 1},
    },
    "grove_talisman": {
        "name": "Grove Talisman",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A twine-wrapped charm of seed, bone, and river-smoothed wood that steadies the breath and the will.",
        "bonuses": {"spell_power": 2, "max_mana": 10, "spirit": 1},
    },
    "mossweave_wraps": {
        "name": "Mossweave Wraps",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Soft layered wraps stitched for damp trails, hedge work, and anyone who expects weather more than applause.",
        "bonuses": {"armor": 1, "max_hp": 5, "max_mana": 8, "dodge": 1, "spirit": 1},
    },
    "ironroot_longblade": {
        "name": "Ironroot Longblade",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "Torren's reworked frontier blade, ground cleaner and balanced for harder work.",
        "bonuses": {"attack_power": 6, "accuracy": 4, "threat": 1},
    },
    "nailbound_heater": {
        "name": "Nailbound Heater",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A stout shield faced with fresh iron and the sort of confidence Torren hammers into everything.",
        "bonuses": {"armor": 6, "max_hp": 14, "threat": 3},
    },
    "rivetmail_coat": {
        "name": "Rivetmail Coat",
        "kind": "equipment",
        "slot": "chest",
        "summary": "A roadwarden coat rebuilt with better rings, firmer leather, and less patience for sharp edges.",
        "bonuses": {"armor": 5, "max_stamina": 10, "max_hp": 6},
    },
    "ironroot_recurve": {
        "name": "Ironroot Recurve",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A tightened ash bow with horn tips and a quicker, cleaner draw.",
        "bonuses": {"attack_power": 6, "accuracy": 7, "precision": 1},
    },
    "thornline_knife": {
        "name": "Thornline Knife",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A lean field knife sharpened for brush, rope, and anyone who mistakes you for easy work.",
        "bonuses": {"attack_power": 2, "accuracy": 3, "dodge": 2},
    },
    "brushrunner_leathers": {
        "name": "Brushrunner Leathers",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Close-stitched trail leathers reinforced to slide through thorn and trouble with less argument.",
        "bonuses": {"armor": 3, "dodge": 3, "max_stamina": 8, "accuracy": 1},
    },
    "dawnbell_mace": {
        "name": "Dawnbell Mace",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A tempered mace whose head carries a quiet sun-mark beneath the iron.",
        "bonuses": {"attack_power": 3, "spell_power": 4, "accuracy": 3},
    },
    "bellwarden_icon": {
        "name": "Bellwarden Icon",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A brass-braced devotional icon fitted to hold steadier light and steadier prayers.",
        "bonuses": {"spell_power": 4, "max_mana": 14, "spirit": 1},
    },
    "roadchapel_vestments": {
        "name": "Roadchapel Vestments",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Traveling vestments cut closer at the shoulder and lined to hold against cold graves and bad nights.",
        "bonuses": {"armor": 3, "max_hp": 8, "max_mana": 10, "spirit": 1},
    },
    "cinderwire_staff": {
        "name": "Cinderwire Staff",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A reworked emberglass staff bound in black wire that keeps heat like a grudge.",
        "bonuses": {"spell_power": 7, "accuracy": 3, "precision": 1},
    },
    "ember_lantern_focus": {
        "name": "Ember Lantern Focus",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A brass-caged focus crystal tuned to answer faster when power moves through it.",
        "bonuses": {"spell_power": 3, "max_mana": 14, "intellect": 1},
    },
    "lanternlined_robes": {
        "name": "Lanternlined Robes",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Apprentice robes rebuilt with better hems, hidden pockets, and enough lining to ignore sparks.",
        "bonuses": {"armor": 2, "max_hp": 6, "max_mana": 14, "dodge": 2},
    },
    "gutterfang_pair": {
        "name": "Gutterfang Pair",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "Torren refiles the hooks, lightens the draw, and sends the pair back keen enough to reward hesitation in other people.",
        "bonuses": {"attack_power": 6, "accuracy": 5, "precision": 2},
    },
    "smokeglass_dagger": {
        "name": "Smokeglass Dagger",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A darker, cleaner parrying dagger with a mirrored black edge that disappears unless it is moving.",
        "bonuses": {"attack_power": 2, "accuracy": 3, "dodge": 3, "precision": 1},
    },
    "shadowtrail_leathers": {
        "name": "Shadowtrail Leathers",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Field leathers rebuilt to move softer, turn quicker, and stop arguing every time the brush gets mean.",
        "bonuses": {"armor": 3, "dodge": 4, "max_stamina": 8, "accuracy": 1},
    },
    "sunforged_blade": {
        "name": "Sunforged Blade",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A cleaner, brighter chapel sword with a brass sun-mark hidden beneath the fuller and more certainty in the edge.",
        "bonuses": {"attack_power": 5, "spell_power": 2, "accuracy": 3, "threat": 1, "spirit": 1},
    },
    "bellguard_bastion": {
        "name": "Bellguard Bastion",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A heavier shield re-rimmed in clean iron and chapel brass, built to keep the line intact even when courage gets uneven.",
        "bonuses": {"armor": 6, "max_hp": 12, "max_stamina": 6, "threat": 3, "spirit": 1},
    },
    "wardens_cuirass": {
        "name": "Warden's Cuirass",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Road mail rebuilt for longer nights and uglier dead, with a steadier shoulder and less tolerance for panic.",
        "bonuses": {"armor": 4, "max_hp": 10, "max_stamina": 6, "spirit": 1, "attack_power": 1},
    },
    "thorncall_staff": {
        "name": "Thorncall Staff",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A rootwood staff hardened with briar heart and moonleaf resin until every strike of power feels a little more deliberate.",
        "bonuses": {"spell_power": 7, "accuracy": 3, "spirit": 1},
    },
    "wildbloom_talisman": {
        "name": "Wildbloom Talisman",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A brighter hedge charm threaded with moonleaf and silk, good for steady hands and longer breaths.",
        "bonuses": {"spell_power": 3, "max_mana": 14, "spirit": 1, "max_hp": 4},
    },
    "briarpath_raiment": {
        "name": "Briarpath Raiment",
        "kind": "equipment",
        "slot": "chest",
        "summary": "Trail wraps reinforced with silk and thorn cord, cut to move through brush like you knew it would part.",
        "bonuses": {"armor": 2, "max_hp": 8, "max_mana": 12, "dodge": 2, "spirit": 1},
    },
    "ridgebreaker_blade": {
        "name": "Ridgebreaker Blade",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A longblade reforged with tower iron and goblin chain, built to end arguments before they reach your back line.",
        "bonuses": {"attack_power": 9, "accuracy": 5, "precision": 1, "threat": 2},
    },
    "warrenspine_recurve": {
        "name": "Warrenspine Recurve",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A horn-backed recurve tuned with tower arrow stock and cave sinew for faster, nastier line shots.",
        "bonuses": {"attack_power": 8, "accuracy": 9, "precision": 2},
    },
    "sunwake_maul": {
        "name": "Sunwake Maul",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A dawn-marked war maul capped with warding brass and just enough spite for goblin kings and older things alike.",
        "bonuses": {"attack_power": 5, "spell_power": 6, "accuracy": 4, "spirit": 1},
    },
    "slagglass_rod": {
        "name": "Slagglass Rod",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A hotter, narrower casting rod carrying fused slagglass through the core and a temperament Torren claims is your problem.",
        "bonuses": {"spell_power": 10, "accuracy": 4, "precision": 2},
    },
    "kingshiv_pair": {
        "name": "Kingshiv Pair",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A matched set reforged from goblin chain and ridge steel, balanced for the sort of close work kings should fear.",
        "bonuses": {"attack_power": 8, "accuracy": 7, "precision": 3, "dodge": 1},
    },
    "locklight_blade": {
        "name": "Locklight Blade",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A sunforged sword rebuilt with drowned weir iron and hollow lensglass until it feels meant for ending stubborn lights.",
        "bonuses": {"attack_power": 7, "spell_power": 4, "accuracy": 4, "threat": 2, "spirit": 1},
    },
    "weirward_bulwark": {
        "name": "Weirward Bulwark",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A broad shield plated in old lock iron and chapel brass, heavy enough to make a promise of standing still matter.",
        "bonuses": {"armor": 8, "max_hp": 16, "max_stamina": 8, "threat": 4, "spirit": 1},
    },
    "lamplight_harness": {
        "name": "Lamplight Harness",
        "kind": "equipment",
        "slot": "chest",
        "summary": "A warden's harness cut from road mail and drowned-line salvage, meant for the sort of work towns sing about only after it is done.",
        "bonuses": {"armor": 5, "max_hp": 14, "max_stamina": 8, "spirit": 2, "attack_power": 1},
    },
    "marshsong_staff": {
        "name": "Marshsong Staff",
        "kind": "equipment",
        "slot": "main_hand",
        "summary": "A thorn staff rebuilt with fen resin and wispglass until the grain hums like water remembering moonlight.",
        "bonuses": {"spell_power": 10, "accuracy": 4, "spirit": 2, "precision": 1},
    },
    "fenlight_talisman": {
        "name": "Fenlight Talisman",
        "kind": "equipment",
        "slot": "off_hand",
        "summary": "A marsh-bright charm of glass, feather, and bound root that answers softly but never weakly.",
        "bonuses": {"spell_power": 4, "max_mana": 18, "spirit": 2, "max_hp": 6},
    },
    "reedwoven_raiment": {
        "name": "Reedwoven Raiment",
        "kind": "equipment",
        "slot": "chest",
        "summary": "A field robe strengthened with hide, resin, and reed cord, light enough for the marsh and sturdy enough for the argument after.",
        "bonuses": {"armor": 3, "max_hp": 10, "max_mana": 16, "dodge": 3, "spirit": 1},
    },
    "trail_mix_satchel": {
        "name": "Trail Mix Satchel",
        "kind": "equipment",
        "slot": "snack",
        "summary": "A waxed trail pouch packed with nuts, berries, and enough salt to pull you back into the fight.",
        "granted_ability": "trail_mix",
        "granted_ability_name": "Trail Mix",
        "cooldown_turns": 3,
    },
    "wolf_pelt": {
        "name": "Wolf Pelt",
        "kind": "loot",
        "stackable": True,
        "summary": "A rough grey pelt, useful enough to trade or keep.",
        "value": 8,
    },
    "wolf_fang": {
        "name": "Wolf Fang",
        "kind": "loot",
        "stackable": True,
        "summary": "A long fang that makes a tidy proof of the kill.",
        "value": 4,
    },
    "goblin_knife": {
        "name": "Goblin Knife",
        "kind": "loot",
        "stackable": True,
        "summary": "A mean little blade worth more as scrap than as a weapon.",
        "value": 6,
    },
    "bent_fence_nails": {
        "name": "Bent Fence Nails",
        "kind": "loot",
        "stackable": True,
        "summary": "A fistful of stolen nails and fasteners from the roadside fences.",
        "value": 5,
    },
    "road_charm": {
        "name": "Road Charm",
        "kind": "loot",
        "stackable": True,
        "summary": "A crude goblin trinket plaited from string, bone, and bad ideas.",
        "value": 9,
    },
    "thorn_rat_tail": {
        "name": "Thorn Rat Tail",
        "kind": "loot",
        "stackable": True,
        "summary": "A prickly rat tail clipped from a roadside scavenger.",
        "value": 3,
    },
    "splintered_axe_head": {
        "name": "Splintered Axe Head",
        "kind": "loot",
        "stackable": True,
        "summary": "The broken iron head of Ruk's notorious fence-cutter.",
        "value": 18,
    },
    "moonleaf_sprig": {
        "name": "Moonleaf Sprig",
        "kind": "loot",
        "stackable": True,
        "summary": "A pale herb sprig with a cool silver scent that clings to the fingers.",
        "value": 6,
    },
    "silk_bundle": {
        "name": "Silk Bundle",
        "kind": "loot",
        "stackable": True,
        "summary": "A careful coil of cave spider silk, sticky but valuable.",
        "value": 8,
    },
    "briar_heart": {
        "name": "Briar Heart",
        "kind": "loot",
        "stackable": True,
        "summary": "A hard knot of thornwood and ember sap cut from a spiteful woodland creature.",
        "value": 11,
    },
    "greymaw_pelt": {
        "name": "Greymaw Pelt",
        "kind": "loot",
        "stackable": True,
        "summary": "The heavy scarred pelt of the wolf that ruled the deep trail.",
        "value": 26,
    },
    "bramble_perch": {
        "name": "Bramble Perch",
        "kind": "ingredient",
        "stackable": True,
        "summary": "A quick silver-sided river fish common around the town wharf.",
        "value": 4,
    },
    "lantern_carp": {
        "name": "Lantern Carp",
        "kind": "ingredient",
        "stackable": True,
        "summary": "A broad amber carp that flashes gold under the lanterns.",
        "value": 6,
    },
    "mudsnout_catfish": {
        "name": "Mudsnout Catfish",
        "kind": "ingredient",
        "stackable": True,
        "summary": "An ugly whiskered bottom-feeder that still cooks up surprisingly well.",
        "value": 7,
    },
    "silver_eel": {
        "name": "Silver Eel",
        "kind": "ingredient",
        "stackable": True,
        "summary": "A slick river eel prized for rich broth and difficult handling.",
        "value": 9,
    },
    "dawnscale_trout": {
        "name": "Dawnscale Trout",
        "kind": "ingredient",
        "stackable": True,
        "summary": "A rare trout with rose-gold scales and a clean river scent.",
        "value": 14,
    },
    "crisped_perch_plate": {
        "name": "Crisped Perch Plate",
        "kind": "meal",
        "stackable": True,
        "summary": "Two pan-crisped perch with herbs and browned butter.",
        "restore": {"hp": 14, "stamina": 18},
        "meal_bonuses": {"attack_power": 2, "max_stamina": 10},
    },
    "riverlight_chowder": {
        "name": "Riverlight Chowder",
        "kind": "meal",
        "stackable": True,
        "summary": "A creamy chowder bright with carp, eel, and a peppery finish.",
        "restore": {"hp": 20, "mana": 14, "stamina": 12},
        "meal_bonuses": {"spell_power": 2, "max_hp": 8, "max_mana": 10},
    },
    "wharfside_skewers": {
        "name": "Wharfside Skewers",
        "kind": "meal",
        "stackable": True,
        "summary": "Charred fish skewers with enough smoke and salt to stiffen the spine.",
        "restore": {"hp": 12, "stamina": 24},
        "meal_bonuses": {"accuracy": 4, "dodge": 2},
    },
    "innkeepers_fishpie": {
        "name": "Innkeeper's Fish Pie",
        "kind": "meal",
        "stackable": True,
        "summary": "A deep savory pie Uncle Pib approves of on principle.",
        "restore": {"hp": 22, "mana": 10, "stamina": 20},
        "meal_bonuses": {"armor": 3, "max_hp": 14},
    },
    "field_bandage": {
        "name": "Field Bandage",
        "kind": "consumable",
        "stackable": True,
        "summary": "A clean wrap and tincture packet meant to stop the worst bleeding before it becomes the whole story.",
        "use": {
            "verb": "apply",
            "contexts": ("explore", "combat"),
            "target": "ally",
            "effect_type": "restore",
            "restore": {"hp": 18},
        },
    },
    "focus_tonic": {
        "name": "Focus Tonic",
        "kind": "consumable",
        "stackable": True,
        "summary": "A bitter vial that steadies the hands, clears the head, and puts a little fire back in the limbs.",
        "use": {
            "verb": "drink",
            "contexts": ("explore", "combat"),
            "target": "self",
            "effect_type": "restore",
            "restore": {"mana": 14, "stamina": 14},
        },
    },
    "fireflask": {
        "name": "Fire Flask",
        "kind": "consumable",
        "stackable": True,
        "summary": "A stoppered glass flask of volatile pitch and ember salts, meant to be thrown from a safe distance and nowhere near your own eyebrows.",
        "use": {
            "verb": "throw",
            "contexts": ("combat",),
            "target": "enemy",
            "effect_type": "damage",
            "damage": {"base": 16, "variance": 4},
            "extra_text": " Flames burst across the target.",
        },
    },
    "purity_salts": {
        "name": "Purity Salts",
        "kind": "consumable",
        "stackable": True,
        "summary": "A sharp-smelling packet of bitter salts and herbs used to break poison, steady the gut, and drive lesser afflictions out through sheer insult.",
        "use": {
            "verb": "apply",
            "contexts": ("combat",),
            "target": "ally",
            "effect_type": "cleanse",
            "restore": {"hp": 8},
        },
    },
    "ward_dust": {
        "name": "Ward Dust",
        "kind": "consumable",
        "stackable": True,
        "summary": "A pinch of ash-bright chapel dust that settles over skin and cloth like a quick ward against the next bad hit.",
        "use": {
            "verb": "cast",
            "contexts": ("combat",),
            "target": "ally",
            "effect_type": "guard",
            "guard": 12,
        },
    },
    "fractured_circuit": {
        "name": "Fractured Circuit",
        "kind": "loot",
        "stackable": True,
        "summary": "A cracked control wafer pried from some long-dead machine mind.",
        "value": 8,
    },
    "magnetized_scrap": {
        "name": "Magnetized Scrap",
        "kind": "loot",
        "stackable": True,
        "summary": "A plate of salvage still tugging toward anything metal with irritating enthusiasm.",
        "value": 9,
    },
    "lantern_pixel_pin": {
        "name": "Lantern Pixel Pin",
        "kind": "loot",
        "stackable": True,
        "summary": "A bright enamel pin shaped like a little maze-lantern grin. Joss only parts with them when a cabinet sings for somebody.",
        "value": 0,
    },
    "grave_dust": {
        "name": "Grave Dust",
        "kind": "loot",
        "stackable": True,
        "summary": "Cold pale dust shaken loose from old barrows and things that should have stayed in them.",
        "value": 7,
    },
    "barrow_relic": {
        "name": "Barrow Relic",
        "kind": "loot",
        "stackable": True,
        "summary": "A weathered trinket from an old burial field, carrying more history than comfort.",
        "value": 13,
    },
    "edrics_signet": {
        "name": "Edric's Signet",
        "kind": "loot",
        "stackable": True,
        "summary": "A darkened knightly signet pulled from the hand of Sir Edric the Restless.",
        "value": 30,
    },
    "bandit_mark": {
        "name": "Bandit Mark",
        "kind": "loot",
        "stackable": True,
        "summary": "A stamped lead token used by the watchtower crews to mark shares, shifts, and authority.",
        "value": 8,
    },
    "tower_arrowhead": {
        "name": "Tower Arrowhead",
        "kind": "loot",
        "stackable": True,
        "summary": "A heavy bodkin arrowhead made to punch through mail from a high perch.",
        "value": 7,
    },
    "hound_iron_collar": {
        "name": "Hound Iron Collar",
        "kind": "loot",
        "stackable": True,
        "summary": "A spiked collar ring cut from one of the watchtower's half-starved carrion hounds.",
        "value": 9,
    },
    "blackreed_longcoat": {
        "name": "Blackreed Longcoat",
        "kind": "loot",
        "stackable": True,
        "summary": "Captain Varn's weather-dark longcoat, lined with hidden pockets and the smell of wet leather and command.",
        "value": 36,
    },
    "hexbone_charm": {
        "name": "Hexbone Charm",
        "kind": "loot",
        "stackable": True,
        "summary": "A goblin charm woven from etched bone, soot cord, and the sort of confidence that should have been punished earlier.",
        "value": 12,
    },
    "batwing_bundle": {
        "name": "Batwing Bundle",
        "kind": "loot",
        "stackable": True,
        "summary": "A tied bundle of cave-bat wing leather, oily and irritatingly useful.",
        "value": 8,
    },
    "brute_chain_link": {
        "name": "Brute Chain Link",
        "kind": "loot",
        "stackable": True,
        "summary": "A heavy goblin-forged chain link cut from a brute harness or gate drag.",
        "value": 11,
    },
    "sludge_resin": {
        "name": "Sludge Resin",
        "kind": "loot",
        "stackable": True,
        "summary": "A tar-thick glob of cavern sludge that hardens into something halfway between glue and lacquer.",
        "value": 10,
    },
    "potking_ladle": {
        "name": "Pot-King Ladle",
        "kind": "loot",
        "stackable": True,
        "summary": "Grubnak's iron ladle-scepter, dented, greasy, and somehow still threatening on principle alone.",
        "value": 34,
    },
    "mire_hound_hide": {
        "name": "Mire Hound Hide",
        "kind": "loot",
        "stackable": True,
        "summary": "A swamp-stinking hide cut from a fen hound tough enough to keep the wet out and the smell in.",
        "value": 14,
    },
    "fen_resin_clot": {
        "name": "Fen Resin Clot",
        "kind": "loot",
        "stackable": True,
        "summary": "A dark clot of marsh resin and root sap that hardens into something halfway between lacquer and warning.",
        "value": 12,
    },
    "wispglass_shard": {
        "name": "Wispglass Shard",
        "kind": "loot",
        "stackable": True,
        "summary": "A pale glassy shard left where fen-light gathers too long around old water and bad memory.",
        "value": 16,
    },
    "rotcrow_pinion": {
        "name": "Rotcrow Pinion",
        "kind": "loot",
        "stackable": True,
        "summary": "A long black marsh feather with an oily sheen and the faint smell of stagnant water.",
        "value": 10,
    },
    "miretooth_fang": {
        "name": "Miretooth Fang",
        "kind": "loot",
        "stackable": True,
        "summary": "A hooked predator fang from the beast ruling the fen edge, still carrying a sick green stain near the root.",
        "value": 42,
    },
    "ward_iron_rivet": {
        "name": "Ward Iron Rivet",
        "kind": "loot",
        "stackable": True,
        "summary": "A heavy old rivet cut from drowned weir iron, still bright at the core where the wrong light kept finding it.",
        "value": 15,
    },
    "hollow_glass_shard": {
        "name": "Hollow Glass Shard",
        "kind": "loot",
        "stackable": True,
        "summary": "A pale lens shard left where drowned lampglass held bad light too long and forgot how to go dark.",
        "value": 18,
    },
    "silt_hook": {
        "name": "Silt Hook",
        "kind": "loot",
        "stackable": True,
        "summary": "A barbed marsh hook pulled from a drowned chain line or something worse that learned to use one.",
        "value": 13,
    },
    "hollow_lantern_prism": {
        "name": "Hollow Lantern Prism",
        "kind": "loot",
        "stackable": True,
        "summary": "A white-black prism from the drowned south light, cold in the hand and still too eager to catch any stray gleam.",
        "value": 48,
    },
}

STARTER_LOADOUTS = {
    "warrior": {
        "main_hand": "militia_blade",
        "off_hand": "oakbound_shield",
        "chest": "roadwarden_mail",
    },
    "ranger": {
        "main_hand": "ashwood_bow",
        "off_hand": "trail_knife",
        "chest": "field_leathers",
    },
    "cleric": {
        "main_hand": "pilgrim_mace",
        "off_hand": "sun_prayer_icon",
        "chest": "wayfarer_vestments",
    },
    "mage": {
        "main_hand": "emberglass_staff",
        "off_hand": "lantern_focus",
        "chest": "hedgeweave_robes",
    },
    "rogue": {
        "main_hand": "hookknife_pair",
        "off_hand": "parrying_dagger",
        "chest": "nightpath_leathers",
    },
    "paladin": {
        "main_hand": "chapel_blade",
        "off_hand": "warded_kite",
        "chest": "bellkeeper_mail",
    },
    "druid": {
        "main_hand": "rootwood_staff",
        "off_hand": "grove_talisman",
        "chest": "mossweave_wraps",
    },
}

STARTER_CONSUMABLES = (
    ("field_bandage", 2),
    ("focus_tonic", 1),
    ("fireflask", 1),
    ("purity_salts", 1),
    ("ward_dust", 1),
)

BONUS_LABELS = {
    "strength": "Strength",
    "agility": "Agility",
    "intellect": "Intellect",
    "spirit": "Spirit",
    "vitality": "Vitality",
    "max_hp": "HP",
    "max_mana": "Mana",
    "max_stamina": "Stamina",
    "attack_power": "Attack",
    "spell_power": "Spell",
    "armor": "Armor",
    "accuracy": "Accuracy",
    "precision": "Precision",
    "crit_chance": "Crit",
    "dodge": "Dodge",
    "threat": "Threat",
}


def _normalize_item_token(value):
    """Normalize free-text item queries for fuzzy matching."""

    return "".join(char for char in (value or "").lower() if char.isalnum())


def get_item(template_id):
    """Return an item template by id."""

    return ITEM_TEMPLATES.get(template_id)


def get_item_category(item_or_template):
    """Return the inventory category an item should be grouped under."""

    item = item_or_template if isinstance(item_or_template, dict) else get_item(item_or_template)
    if not item:
        return None
    category = item.get("category")
    if category:
        return category
    if item.get("kind") == "meal":
        return "consumable"
    return item.get("kind")


def get_item_use_profile(item_or_template, *, context=None):
    """Return normalized use metadata for a consumable item."""

    item = item_or_template if isinstance(item_or_template, dict) else get_item(item_or_template)
    if not item:
        return None

    use = dict(item.get("use") or {})
    if item.get("kind") == "meal":
        use.setdefault("verb", "eat")
        use.setdefault("contexts", ("explore", "combat"))
        use.setdefault("target", "self")
        use.setdefault("effect_type", "meal")
        if item.get("restore"):
            use.setdefault("restore", dict(item.get("restore", {})))
        if item.get("meal_bonuses"):
            use.setdefault("buffs", dict(item.get("meal_bonuses", {})))

    contexts = tuple(use.get("contexts") or ())
    if context and contexts and context not in contexts:
        return None
    if not use:
        return None
    use["contexts"] = contexts
    return use


def is_consumable_item(item_or_template, *, context=None):
    """Whether an item exposes consumable-use metadata."""

    return get_item_use_profile(item_or_template, context=context) is not None


def match_inventory_item(character, query, *, context=None, category=None, verb=None):
    """Find a carried inventory item by template id or fuzzy display name."""

    if not query:
        return None

    token = _normalize_item_token(query)
    matches = []
    for entry in (character.db.brave_inventory or []):
        template_id = entry.get("template")
        quantity = int(entry.get("quantity", 0) or 0)
        item = get_item(template_id)
        if not item or quantity <= 0:
            continue
        if category and get_item_category(item) != category:
            continue
        use = get_item_use_profile(item, context=context)
        if verb and (not use or use.get("verb") != verb):
            continue
        if context and not use:
            continue
        names = [template_id, item.get("name", "")]
        if any(token == _normalize_item_token(name) or token in _normalize_item_token(name) for name in names):
            matches.append(template_id)
    if not matches:
        return None
    return matches[0] if len(matches) == 1 else matches


def format_bonus_summary(item_data):
    """Return a compact bonus string for an item template."""

    bonuses = item_data.get("bonuses", {})
    if not bonuses:
        return ""

    parts = []
    for key, value in bonuses.items():
        label = BONUS_LABELS.get(key, key.replace("_", " ").title())
        sign = "+" if value >= 0 else ""
        parts.append(f"{label} {sign}{value}")
    return ", ".join(parts)
