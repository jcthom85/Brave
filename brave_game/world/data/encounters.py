"""Encounter and enemy data for Brave's first combat slice."""

ENEMY_TEMPLATES = {
    "thorn_rat": {
        "name": "Thorn Rat",
        "tags": ["beast", "rat"],
        "max_hp": 18,
        "attack_power": 5,
        "armor": 0,
        "accuracy": 74,
        "dodge": 12,
        "xp": 12,
        "desc": "A large roadside rat with burrs and thorns snarled into its hide.",
        "silver": (0, 1),
        "loot": [{"item": "thorn_rat_tail", "chance": 0.8}],
    },
    "road_wolf": {
        "name": "Road Wolf",
        "tags": ["wolf", "beast"],
        "max_hp": 30,
        "attack_power": 8,
        "armor": 2,
        "accuracy": 68,
        "dodge": 8,
        "xp": 18,
        "desc": "A lean wolf made bold by hunger and too many easy roads.",
        "silver": (1, 3),
        "loot": [
            {"item": "wolf_pelt", "chance": 0.75},
            {"item": "wolf_fang", "chance": 0.45},
        ],
    },
    "goblin_sneak": {
        "name": "Goblin Sneak",
        "tags": ["goblin", "skirmisher"],
        "max_hp": 26,
        "attack_power": 7,
        "armor": 1,
        "accuracy": 70,
        "dodge": 10,
        "xp": 18,
        "desc": "A wiry goblin with quick hands and ugly road-cutting habits.",
        "silver": (2, 4),
        "loot": [
            {"item": "goblin_knife", "chance": 0.65},
            {"item": "road_charm", "chance": 0.35},
        ],
    },
    "goblin_cutter": {
        "name": "Goblin Cutter",
        "tags": ["goblin", "raider"],
        "max_hp": 34,
        "attack_power": 10,
        "armor": 3,
        "accuracy": 66,
        "dodge": 6,
        "xp": 22,
        "desc": "A thicker-set goblin raider gripping a nicked blade and stolen work gear.",
        "silver": (3, 6),
        "loot": [
            {"item": "goblin_knife", "chance": 0.75},
            {"item": "bent_fence_nails", "chance": 0.6},
            {"item": "road_charm", "chance": 0.25},
        ],
    },
    "goblin_slinger": {
        "name": "Goblin Slinger",
        "tags": ["goblin", "skirmisher", "ranged"],
        "max_hp": 24,
        "attack_power": 8,
        "armor": 1,
        "accuracy": 72,
        "dodge": 8,
        "xp": 20,
        "desc": "A goblin skirmisher with a leather sling and a pouch full of stolen stones.",
        "silver": (2, 5),
        "loot": [
            {"item": "goblin_knife", "chance": 0.35},
            {"item": "road_charm", "chance": 0.45},
        ],
    },
    "ruk_fence_cutter": {
        "name": "Ruk the Fence-Cutter",
        "tags": ["goblin", "boss", "ruk", "raider"],
        "max_hp": 84,
        "attack_power": 14,
        "armor": 4,
        "accuracy": 72,
        "dodge": 8,
        "xp": 90,
        "desc": "A broad goblin brute in stolen harness, gripping the jagged axe that gave him his name.",
        "silver": (10, 14),
        "loot": [
            {"item": "splintered_axe_head", "chance": 1.0},
            {"item": "bent_fence_nails", "chance": 1.0, "min": 1, "max": 2},
        ],
    },
    "forest_wolf": {
        "name": "Forest Wolf",
        "tags": ["wolf", "beast", "forest"],
        "max_hp": 40,
        "attack_power": 11,
        "armor": 2,
        "accuracy": 72,
        "dodge": 10,
        "xp": 28,
        "desc": "A heavier woodland wolf with burrs in its coat and an unsettling calm.",
        "silver": (2, 4),
        "loot": [
            {"item": "wolf_pelt", "chance": 0.8},
            {"item": "wolf_fang", "chance": 0.5},
        ],
        "target_strategy": "lowest_hp",
        "special": "lunge",
    },
    "cave_spider": {
        "name": "Cave Spider",
        "tags": ["spider", "beast", "web"],
        "max_hp": 36,
        "attack_power": 9,
        "armor": 2,
        "accuracy": 70,
        "dodge": 11,
        "xp": 26,
        "desc": "A thick-legged spider that has grown too comfortable in the roots and stones.",
        "silver": (1, 3),
        "loot": [
            {"item": "silk_bundle", "chance": 0.72},
            {"item": "moonleaf_sprig", "chance": 0.2},
        ],
        "special": "web",
    },
    "briar_imp": {
        "name": "Briar Imp",
        "tags": ["imp", "fey", "ranged", "caster"],
        "max_hp": 31,
        "attack_power": 6,
        "spell_power": 15,
        "armor": 1,
        "accuracy": 75,
        "dodge": 12,
        "xp": 30,
        "desc": "A thorn-limbed little horror with ember eyes and a voice like twigs snapping.",
        "silver": (3, 6),
        "loot": [
            {"item": "briar_heart", "chance": 0.55},
            {"item": "moonleaf_sprig", "chance": 0.35},
        ],
        "attack_kind": "spell",
        "target_strategy": "lowest_hp",
        "special": "curse",
    },
    "mossling": {
        "name": "Mossling",
        "tags": ["plant", "support", "moss"],
        "max_hp": 44,
        "attack_power": 7,
        "spell_power": 12,
        "armor": 4,
        "accuracy": 67,
        "dodge": 5,
        "xp": 28,
        "desc": "A squat knot of wet bark and roots that moves with patient, herbal malice.",
        "silver": (2, 5),
        "loot": [
            {"item": "moonleaf_sprig", "chance": 0.85},
            {"item": "briar_heart", "chance": 0.2},
        ],
        "attack_kind": "spell",
        "special": "mend",
    },
    "old_greymaw": {
        "name": "Old Greymaw",
        "tags": ["wolf", "beast", "boss", "greymaw"],
        "max_hp": 118,
        "attack_power": 17,
        "armor": 5,
        "accuracy": 76,
        "dodge": 12,
        "xp": 130,
        "desc": "A scarred apex wolf with old iron snapped off in one shoulder and too much cunning in its eyes.",
        "silver": (12, 16),
        "loot": [
            {"item": "greymaw_pelt", "chance": 1.0},
            {"item": "wolf_fang", "chance": 1.0, "min": 1, "max": 2},
        ],
        "target_strategy": "lowest_hp",
        "special": "greymaw",
    },
    "skeletal_soldier": {
        "name": "Skeletal Soldier",
        "tags": ["undead", "skeleton", "soldier", "brute"],
        "max_hp": 54,
        "attack_power": 13,
        "armor": 4,
        "accuracy": 69,
        "dodge": 4,
        "xp": 34,
        "desc": "An old soldier's bones held together by stubborn malice and older oaths.",
        "silver": (3, 5),
        "loot": [
            {"item": "grave_dust", "chance": 0.8},
            {"item": "barrow_relic", "chance": 0.35},
        ],
    },
    "restless_shade": {
        "name": "Restless Shade",
        "tags": ["undead", "shade", "caster"],
        "max_hp": 42,
        "attack_power": 8,
        "spell_power": 17,
        "armor": 2,
        "accuracy": 75,
        "dodge": 10,
        "xp": 38,
        "desc": "A dim human outline full of grief, bad memory, and enough spite to stay dangerous.",
        "silver": (4, 6),
        "loot": [
            {"item": "grave_dust", "chance": 0.65},
            {"item": "barrow_relic", "chance": 0.5},
        ],
        "attack_kind": "spell",
        "target_strategy": "lowest_hp",
    },
    "grave_crow": {
        "name": "Grave Crow",
        "tags": ["undead", "crow", "skirmisher"],
        "max_hp": 34,
        "attack_power": 11,
        "armor": 1,
        "accuracy": 78,
        "dodge": 12,
        "xp": 30,
        "desc": "A black carrion bird with pale eye-fire and a beak too eager for the living.",
        "silver": (2, 4),
        "loot": [
            {"item": "grave_dust", "chance": 0.55},
            {"item": "barrow_relic", "chance": 0.25},
        ],
        "target_strategy": "lowest_hp",
    },
    "barrow_wisp": {
        "name": "Barrow Wisp",
        "tags": ["undead", "wisp", "support", "caster"],
        "max_hp": 40,
        "attack_power": 7,
        "spell_power": 16,
        "armor": 2,
        "accuracy": 74,
        "dodge": 9,
        "xp": 36,
        "desc": "A grave-light drifting above the stones, beautiful right up until it starts hating you.",
        "silver": (3, 6),
        "loot": [
            {"item": "grave_dust", "chance": 0.45},
            {"item": "barrow_relic", "chance": 0.7},
        ],
        "attack_kind": "spell",
        "target_strategy": "lowest_hp",
    },
    "sir_edric_restless": {
        "name": "Sir Edric the Restless",
        "tags": ["undead", "boss", "edric", "knight"],
        "max_hp": 168,
        "attack_power": 19,
        "spell_power": 18,
        "armor": 7,
        "accuracy": 76,
        "dodge": 7,
        "xp": 190,
        "desc": "A long-dead knight risen in dim mail and torn surcoat, still carrying command like a wound that never closed.",
        "silver": (14, 18),
        "loot": [
            {"item": "edrics_signet", "chance": 1.0},
            {"item": "barrow_relic", "chance": 1.0, "min": 1, "max": 2},
        ],
        "attack_kind": "spell",
        "special": "edric",
    },
    "bandit_scout": {
        "name": "Bandit Scout",
        "tags": ["bandit", "scout", "skirmisher"],
        "max_hp": 58,
        "attack_power": 14,
        "armor": 3,
        "accuracy": 78,
        "dodge": 11,
        "xp": 42,
        "desc": "A lean ridge-runner with a short blade, quick eyes, and no love for fair odds.",
        "silver": (5, 8),
        "loot": [
            {"item": "bandit_mark", "chance": 0.7},
            {"item": "tower_arrowhead", "chance": 0.3},
        ],
        "target_strategy": "lowest_hp",
    },
    "bandit_raider": {
        "name": "Bandit Raider",
        "tags": ["bandit", "raider", "brute"],
        "max_hp": 74,
        "attack_power": 18,
        "armor": 6,
        "accuracy": 72,
        "dodge": 6,
        "xp": 50,
        "desc": "A hard-looking tower raider in pieced mail, built to break a line and hold the breach.",
        "silver": (6, 10),
        "loot": [
            {"item": "bandit_mark", "chance": 0.85},
            {"item": "hound_iron_collar", "chance": 0.2},
        ],
    },
    "tower_archer": {
        "name": "Tower Archer",
        "tags": ["bandit", "archer", "ranged"],
        "max_hp": 52,
        "attack_power": 17,
        "armor": 3,
        "accuracy": 83,
        "dodge": 10,
        "xp": 46,
        "desc": "A ridge archer with a tower bow, a cold eye, and a bad habit of aiming where the mail parts.",
        "silver": (6, 10),
        "loot": [
            {"item": "tower_arrowhead", "chance": 0.85},
            {"item": "bandit_mark", "chance": 0.45},
        ],
        "target_strategy": "lowest_hp",
    },
    "carrion_hound": {
        "name": "Carrion Hound",
        "tags": ["beast", "hound", "carrion"],
        "max_hp": 68,
        "attack_power": 17,
        "armor": 4,
        "accuracy": 75,
        "dodge": 8,
        "xp": 44,
        "desc": "A kennel-starved hound bred lean, mean, and far too used to the smell of the dead.",
        "silver": (4, 8),
        "loot": [
            {"item": "hound_iron_collar", "chance": 0.7},
            {"item": "tower_arrowhead", "chance": 0.25},
        ],
        "target_strategy": "lowest_hp",
    },
    "captain_varn_blackreed": {
        "name": "Captain Varn Blackreed",
        "tags": ["bandit", "boss", "blackreed", "commander"],
        "max_hp": 188,
        "attack_power": 22,
        "armor": 7,
        "accuracy": 81,
        "dodge": 9,
        "xp": 240,
        "desc": "A disciplined bandit captain in a rain-dark coat, moving like he expects every fight to become his line if he wants it badly enough.",
        "silver": (18, 24),
        "loot": [
            {"item": "blackreed_longcoat", "chance": 1.0},
            {"item": "bandit_mark", "chance": 1.0, "min": 1, "max": 2},
        ],
        "target_strategy": "lowest_hp",
        "special": "blackreed",
    },
    "goblin_hexer": {
        "name": "Goblin Hexer",
        "tags": ["goblin", "warren", "hexer", "caster"],
        "max_hp": 60,
        "attack_power": 10,
        "spell_power": 22,
        "armor": 3,
        "accuracy": 79,
        "dodge": 10,
        "xp": 56,
        "desc": "A soot-daubed goblin muttering over bone charms and filthy thread, all hungry grin and mean little rituals.",
        "silver": (6, 10),
        "loot": [
            {"item": "hexbone_charm", "chance": 0.8},
            {"item": "goblin_knife", "chance": 0.35},
        ],
        "attack_kind": "spell",
        "target_strategy": "lowest_hp",
    },
    "goblin_brute": {
        "name": "Goblin Brute",
        "tags": ["goblin", "warren", "brute"],
        "max_hp": 86,
        "attack_power": 21,
        "armor": 7,
        "accuracy": 74,
        "dodge": 5,
        "xp": 58,
        "desc": "A thick-necked tunnel bully dragging chain, iron, and enough bad temper to make the cave itself feel narrower.",
        "silver": (7, 11),
        "loot": [
            {"item": "brute_chain_link", "chance": 0.8},
            {"item": "goblin_knife", "chance": 0.5},
        ],
    },
    "cave_bat_swarm": {
        "name": "Cave Bat Swarm",
        "tags": ["beast", "bat", "warren", "swarm"],
        "max_hp": 50,
        "attack_power": 17,
        "armor": 2,
        "accuracy": 81,
        "dodge": 14,
        "xp": 52,
        "desc": "A screaming knot of cave bats that has learned the taste of cook smoke, bad meat, and exposed faces.",
        "silver": (4, 8),
        "loot": [{"item": "batwing_bundle", "chance": 0.85}],
        "target_strategy": "lowest_hp",
    },
    "sludge_slime": {
        "name": "Sludge Slime",
        "tags": ["ooze", "slime", "warren"],
        "max_hp": 94,
        "attack_power": 14,
        "spell_power": 20,
        "armor": 8,
        "accuracy": 73,
        "dodge": 4,
        "xp": 54,
        "desc": "A crawl of grease-thick cave sludge pulling itself along with bits of bone, ash, and goblin kitchen ruin half dissolved inside it.",
        "silver": (5, 9),
        "loot": [{"item": "sludge_resin", "chance": 0.8}],
        "attack_kind": "spell",
    },
    "grubnak_the_pot_king": {
        "name": "Grubnak the Pot-King",
        "tags": ["goblin", "warren", "boss", "potking", "brute"],
        "max_hp": 226,
        "attack_power": 26,
        "spell_power": 20,
        "armor": 9,
        "accuracy": 80,
        "dodge": 6,
        "xp": 320,
        "desc": "An oversized goblin tyrant wearing a battered pot lid like a crown and carrying a black iron ladle like a scepter.",
        "silver": (22, 28),
        "loot": [
            {"item": "potking_ladle", "chance": 1.0},
            {"item": "brute_chain_link", "chance": 1.0, "min": 1, "max": 2},
            {"item": "hexbone_charm", "chance": 1.0},
        ],
        "special": "potking",
    },
    "mire_hound": {
        "name": "Mire Hound",
        "tags": ["beast", "hound", "blackfen", "mire"],
        "max_hp": 92,
        "attack_power": 22,
        "armor": 5,
        "accuracy": 79,
        "dodge": 8,
        "xp": 66,
        "desc": "A marsh-bred hound with reed-matted hide, yellow eyes, and the sort of patience wet country teaches predators.",
        "silver": (8, 12),
        "loot": [
            {"item": "mire_hound_hide", "chance": 0.8},
            {"item": "fen_resin_clot", "chance": 0.25},
        ],
        "target_strategy": "lowest_hp",
    },
    "bog_creeper": {
        "name": "Bog Creeper",
        "tags": ["plant", "blackfen", "creeper", "brute"],
        "max_hp": 104,
        "attack_power": 18,
        "spell_power": 21,
        "armor": 9,
        "accuracy": 74,
        "dodge": 4,
        "xp": 68,
        "desc": "A root-thick marsh horror pulling itself through the reeds with mud, vine, and old water bound into one bad decision.",
        "silver": (7, 11),
        "loot": [{"item": "fen_resin_clot", "chance": 0.85}],
        "attack_kind": "spell",
    },
    "fen_wisp": {
        "name": "Fen Wisp",
        "tags": ["spirit", "blackfen", "wisp", "caster", "support"],
        "max_hp": 62,
        "attack_power": 12,
        "spell_power": 24,
        "armor": 3,
        "accuracy": 80,
        "dodge": 12,
        "xp": 70,
        "desc": "A pale bog-light drifting just above the waterline, bright enough to follow and wrong enough to regret it immediately.",
        "silver": (8, 12),
        "loot": [{"item": "wispglass_shard", "chance": 0.8}],
        "attack_kind": "spell",
        "target_strategy": "lowest_hp",
    },
    "rot_crow": {
        "name": "Rot Crow",
        "tags": ["beast", "crow", "blackfen", "skirmisher"],
        "max_hp": 58,
        "attack_power": 19,
        "armor": 2,
        "accuracy": 84,
        "dodge": 15,
        "xp": 64,
        "desc": "A long-winged marsh crow with bone-white eyes and a talent for circling anything about to stop moving.",
        "silver": (6, 10),
        "loot": [
            {"item": "rotcrow_pinion", "chance": 0.85},
            {"item": "wispglass_shard", "chance": 0.25},
        ],
        "target_strategy": "lowest_hp",
    },
    "miretooth": {
        "name": "Miretooth",
        "tags": ["beast", "blackfen", "boss", "miretooth", "hound"],
        "max_hp": 252,
        "attack_power": 29,
        "armor": 9,
        "accuracy": 82,
        "dodge": 10,
        "xp": 380,
        "desc": "A fen-born apex predator with a scarred muzzle, reed-dark hide, and a gait that makes the marsh itself look like it is stalking with him.",
        "silver": (24, 30),
        "loot": [
            {"item": "miretooth_fang", "chance": 1.0},
            {"item": "mire_hound_hide", "chance": 1.0, "min": 1, "max": 2},
            {"item": "wispglass_shard", "chance": 1.0},
        ],
        "target_strategy": "lowest_hp",
        "special": "miretooth",
    },
    "drowned_warder": {
        "name": "Drowned Warder",
        "tags": ["undead", "weir", "warder", "brute"],
        "max_hp": 114,
        "attack_power": 24,
        "armor": 7,
        "accuracy": 78,
        "dodge": 5,
        "xp": 74,
        "desc": "A drowned lock-keeper shape in old oilskins and iron braces, still carrying out a duty the marsh should have taken from it years ago.",
        "silver": (8, 12),
        "loot": [
            {"item": "ward_iron_rivet", "chance": 0.85},
            {"item": "silt_hook", "chance": 0.35},
        ],
    },
    "hollow_wisp": {
        "name": "Hollow Wisp",
        "tags": ["spirit", "weir", "wisp", "caster", "support"],
        "max_hp": 72,
        "attack_power": 12,
        "spell_power": 27,
        "armor": 3,
        "accuracy": 82,
        "dodge": 12,
        "xp": 76,
        "desc": "A white drowned lamp-glow drifting just above the black water, bright enough to follow and empty enough to regret.",
        "silver": (8, 12),
        "loot": [
            {"item": "hollow_glass_shard", "chance": 0.85},
            {"item": "ward_iron_rivet", "chance": 0.2},
        ],
        "attack_kind": "spell",
        "target_strategy": "lowest_hp",
    },
    "silt_stalker": {
        "name": "Silt Stalker",
        "tags": ["beast", "weir", "stalker", "skirmisher"],
        "max_hp": 90,
        "attack_power": 23,
        "armor": 4,
        "accuracy": 83,
        "dodge": 13,
        "xp": 72,
        "desc": "A long-limbed marsh hunter slipping through the flooded stonework on claws and bad patience.",
        "silver": (7, 11),
        "loot": [
            {"item": "silt_hook", "chance": 0.8},
            {"item": "hollow_glass_shard", "chance": 0.25},
        ],
        "target_strategy": "lowest_hp",
    },
    "hollow_lantern": {
        "name": "The Hollow Lantern",
        "tags": ["spirit", "weir", "boss", "hollowlantern", "caster"],
        "max_hp": 292,
        "attack_power": 18,
        "spell_power": 31,
        "armor": 10,
        "accuracy": 84,
        "dodge": 9,
        "xp": 460,
        "desc": "A drowned lamp-spirit gathered around an old civic light, all blackwater reflection, white fire, and the certainty that duty outlived mercy.",
        "silver": (28, 34),
        "loot": [
            {"item": "hollow_lantern_prism", "chance": 1.0},
            {"item": "hollow_glass_shard", "chance": 1.0, "min": 1, "max": 2},
            {"item": "ward_iron_rivet", "chance": 1.0, "min": 1, "max": 2},
        ],
        "attack_kind": "spell",
        "special": "hollowlantern",
    },
}

ROOM_ENCOUNTERS = {
    "tutorial_vermin_pens": [
        {
            "key": "yard_scuttle",
            "title": "Yard Scuttle",
            "intro": "Straw erupts under the rail and a thorn rat bolts straight at the nearest warm ankle.",
            "enemies": ["thorn_rat"],
        },
        {
            "key": "bin_raider",
            "title": "Bin Raider",
            "intro": "A burr-matted rat launches itself out of a feed bin with all the confidence of a creature that has never once paid for grain.",
            "enemies": ["thorn_rat"],
        },
    ],
    "brambleford_rat_and_kettle_cellar": [
        {
            "key": "cellar_scuttle",
            "title": "Cellar Scuttle",
            "intro": "Barrels rattle, sacks split, and a pair of thorn rats come boiling out of the dark.",
            "enemies": ["thorn_rat", "thorn_rat"],
        },
        {
            "key": "grain_raiders",
            "title": "Grain Raiders",
            "intro": "Three cellar rats burst from behind the feed sacks like they own the place.",
            "enemies": ["thorn_rat", "thorn_rat", "thorn_rat"],
        },
    ],
    "ruined_watchtower_approach": [
        {
            "key": "ridge_shadows",
            "title": "Ridge Shadows",
            "intro": "Shapes move between the broken stones above the road. Bandits have already measured this approach and decided they like the angle.",
            "enemies": ["bandit_scout", "bandit_scout"],
        },
        {
            "key": "hound_run",
            "title": "Hound Run",
            "intro": "A kennel hound tears down the slope while a scout cuts in behind it with a knife already out.",
            "enemies": ["carrion_hound", "bandit_scout"],
        },
        {
            "key": "watchfire_raiders",
            "title": "Watchfire Raiders",
            "intro": "A raider and lookout break from the shattered watchfire line and try to catch you in the narrow ground below.",
            "enemies": ["bandit_raider", "bandit_scout"],
        },
    ],
    "ruined_watchtower_breach_yard": [
        {
            "key": "yard_press",
            "title": "Breach Yard Press",
            "intro": "Bandits pour through the broken outer yard, one holding the front while the other probes for an opening.",
            "enemies": ["bandit_raider", "bandit_scout"],
        },
        {
            "key": "arrow_and_hide",
            "title": "Arrow And Hide",
            "intro": "An archer takes the line from broken stone while a hound ranges below, trying to flush you into the shot.",
            "enemies": ["tower_archer", "carrion_hound"],
        },
        {
            "key": "broken_muster",
            "title": "Broken Muster",
            "intro": "The yard wakes all at once: a tower archer barks a range, then raiders close from either side of the breach.",
            "enemies": ["tower_archer", "bandit_raider"],
        },
    ],
    "ruined_watchtower_archers_ledge": [
        {
            "key": "ledge_line",
            "title": "Ledge Line",
            "intro": "Boot scrape above, bowstring below. The ledge is already occupied and none of them are in a sharing mood.",
            "enemies": ["tower_archer", "tower_archer"],
        },
        {
            "key": "spotter_pair",
            "title": "Spotter Pair",
            "intro": "A scout darts low across the ledge while an archer works the height behind him.",
            "enemies": ["bandit_scout", "tower_archer"],
        },
        {
            "key": "kennel_ledge",
            "title": "Kennel Ledge",
            "intro": "A hound comes off the chain just as a bowstring snaps tight from the rocks above.",
            "enemies": ["carrion_hound", "tower_archer"],
        },
    ],
    "ruined_watchtower_cracked_stairs": [
        {
            "key": "stairs_hold",
            "title": "Stairs Hold",
            "intro": "Raiders hammer down the cracked stairs while an archer leans over the turn to rake the climb.",
            "enemies": ["bandit_raider", "tower_archer"],
        },
        {
            "key": "broken_shieldwall",
            "title": "Broken Shieldwall",
            "intro": "Two hard cases block the stair curve with enough steel and bad intent to make the climb expensive.",
            "enemies": ["bandit_raider", "bandit_raider"],
        },
        {
            "key": "upper_kennel",
            "title": "Upper Kennel",
            "intro": "A hound hits first, then the raider behind it tries to use the chaos of the stairs as cover.",
            "enemies": ["carrion_hound", "bandit_raider"],
        },
    ],
    "ruined_watchtower_blackreed_roost": [
        {
            "key": "blackreeds_line",
            "title": "Captain Varn Blackreed",
            "intro": "At the broken tower crown, Captain Varn Blackreed turns from the parapet and draws steel like he has already counted where each of you will fall.",
            "enemies": ["captain_varn_blackreed"],
        },
    ],
    "goblin_warrens_sinkmouth_cut": [
        {
            "key": "sinkmouth_watch",
            "title": "Sinkmouth Watch",
            "intro": "Torchlight jerks through the cut and a pair of goblin tunnel guards rush to keep the surface where it belongs: above them.",
            "enemies": ["goblin_hexer", "goblin_brute"],
        },
        {
            "key": "batdrop_cut",
            "title": "Batdrop Cut",
            "intro": "Something shrieks from the ceiling just as tunnel brutes come grinding up through the soot and mud.",
            "enemies": ["cave_bat_swarm", "goblin_brute"],
        },
        {
            "key": "filth_watch",
            "title": "Filth Watch",
            "intro": "A sludge shape peels off the wall while a hexer starts spitting curses from behind it.",
            "enemies": ["sludge_slime", "goblin_hexer"],
        },
    ],
    "goblin_warrens_torchgut_tunnel": [
        {
            "key": "torchgut_press",
            "title": "Torchgut Press",
            "intro": "The tunnel narrows at exactly the wrong moment and the goblins on the far side mean to keep it that way.",
            "enemies": ["goblin_brute", "goblin_brute"],
        },
        {
            "key": "hex_and_fang",
            "title": "Hex and Fang",
            "intro": "A hexer spits soot over the torchline while cave bats tear loose from the black stone above it.",
            "enemies": ["goblin_hexer", "cave_bat_swarm"],
        },
        {
            "key": "slime_turn",
            "title": "Slime Turn",
            "intro": "A tunnel brute drives forward while something wet and hungry slides around the torchbend behind it.",
            "enemies": ["goblin_brute", "sludge_slime"],
        },
    ],
    "goblin_warrens_bone_midden": [
        {
            "key": "midden_raze",
            "title": "Midden Raze",
            "intro": "The bone heap collapses in a flutter of wings and filthy laughter as the midden defenders throw themselves at you.",
            "enemies": ["cave_bat_swarm", "cave_bat_swarm", "goblin_hexer"],
        },
        {
            "key": "brute_heap",
            "title": "Brute Heap",
            "intro": "Chain drags across cracked bone as two goblin brutes stomp up through the midden with room-rattling confidence.",
            "enemies": ["goblin_brute", "goblin_brute"],
        },
        {
            "key": "sour_heap",
            "title": "Sour Heap",
            "intro": "A slime oozes through the midden while a hexer works a curse line behind it and bats begin to wake overhead.",
            "enemies": ["sludge_slime", "goblin_hexer", "cave_bat_swarm"],
        },
    ],
    "goblin_warrens_sludge_run": [
        {
            "key": "runoff_pull",
            "title": "Runoff Pull",
            "intro": "The channel slurps, shifts, and suddenly develops teeth in more places than a channel should.",
            "enemies": ["sludge_slime", "sludge_slime"],
        },
        {
            "key": "slop_bats",
            "title": "Slop Bats",
            "intro": "The runoff stirs underfoot just as cave bats dive low through the steam and greasy torch smoke.",
            "enemies": ["sludge_slime", "cave_bat_swarm"],
        },
        {
            "key": "run_hex",
            "title": "Run Hex",
            "intro": "A hexer holds the far bank while the sludge between you answers to every ugly word it knows.",
            "enemies": ["goblin_hexer", "sludge_slime"],
        },
    ],
    "goblin_warrens_feast_hall": [
        {
            "key": "hall_carvers",
            "title": "Hall Carvers",
            "intro": "The feast hall erupts in noise. One brute shoves forward, a hexer starts chanting, and the ceiling seems far too interested in joining.",
            "enemies": ["goblin_brute", "goblin_hexer", "cave_bat_swarm"],
        },
        {
            "key": "grease_line",
            "title": "Grease Line",
            "intro": "Hot stink, slick stone, and a goblin line that thinks it owns the floor. It would prefer not to share.",
            "enemies": ["goblin_brute", "sludge_slime", "goblin_hexer"],
        },
        {
            "key": "hall_press",
            "title": "Hall Press",
            "intro": "The warrens answer all at once: chain, curses, wings, and enough tunnel confidence to make the hall itself feel mean.",
            "enemies": ["goblin_brute", "goblin_brute", "cave_bat_swarm"],
        },
    ],
    "goblin_warrens_pot_kings_court": [
        {
            "key": "potkings_feast",
            "title": "Grubnak the Pot-King",
            "intro": "At the far court, Grubnak lurches up from his iron seat, pot lid crown ringing as he slams his ladle across the stones and calls the whole hall to supper.",
            "enemies": ["grubnak_the_pot_king"],
        },
    ],
    "blackfen_approach_fenreach_track": [
        {
            "key": "reed_hunt",
            "title": "Reed Hunt",
            "intro": "The reeds part low and fast. Whatever owns this trail has already decided you count as movement first and people second.",
            "enemies": ["mire_hound", "rot_crow"],
        },
        {
            "key": "bog_pull",
            "title": "Bog Pull",
            "intro": "Mud shifts underfoot as a root mass heaves up through the water while bad fen-light starts drifting in from the side.",
            "enemies": ["bog_creeper", "fen_wisp"],
        },
        {
            "key": "wet_line",
            "title": "Wet Line",
            "intro": "A marsh hound ranges the track while a second shape circles overhead, already measuring what part of you it wants later.",
            "enemies": ["mire_hound", "rot_crow"],
        },
    ],
    "blackfen_approach_reedflats": [
        {
            "key": "reed_press",
            "title": "Reed Press",
            "intro": "The flats come alive all at once: one hound low through the reeds while a creeper drags itself out of the standing water behind it.",
            "enemies": ["mire_hound", "bog_creeper"],
        },
        {
            "key": "false_lanterns",
            "title": "False Lanterns",
            "intro": "A fen-light glides ahead like a promise and the marsh punishes you for noticing it.",
            "enemies": ["fen_wisp", "rot_crow"],
        },
        {
            "key": "marsh_line",
            "title": "Marsh Line",
            "intro": "A creeper blocks the path while rot crows rake across the top of the reeds looking for weakness.",
            "enemies": ["bog_creeper", "rot_crow"],
        },
    ],
    "blackfen_approach_boglight_hollow": [
        {
            "key": "hollow_lights",
            "title": "Hollow Lights",
            "intro": "Bog-light gathers in the hollow just long enough to show you how many bad shapes were waiting in it.",
            "enemies": ["fen_wisp", "fen_wisp"],
        },
        {
            "key": "root_and_glass",
            "title": "Root and Glass",
            "intro": "A creeper churns up through the black water while a wisp hangs back, bright and hateful over the pool.",
            "enemies": ["bog_creeper", "fen_wisp"],
        },
        {
            "key": "hollow_carrion",
            "title": "Hollow Carrion",
            "intro": "Rot crows break from the dead trees just as marsh light starts drifting around your ankles.",
            "enemies": ["rot_crow", "rot_crow", "fen_wisp"],
        },
    ],
    "blackfen_approach_carrion_rise": [
        {
            "key": "rise_watch",
            "title": "Rise Watch",
            "intro": "The high mudbank gives just enough footing for the local killers to enjoy the angle.",
            "enemies": ["rot_crow", "mire_hound"],
        },
        {
            "key": "rise_blight",
            "title": "Rise Blight",
            "intro": "A creeper heaves out of the mud shelf while crows start cutting low over the rise like they want the first claim.",
            "enemies": ["bog_creeper", "rot_crow"],
        },
        {
            "key": "bad_tide",
            "title": "Bad Tide",
            "intro": "The rise goes cold, then bright, then violent: marsh light ahead, teeth below, wings behind.",
            "enemies": ["fen_wisp", "mire_hound", "rot_crow"],
        },
    ],
    "blackfen_approach_miretooths_wallow": [
        {
            "key": "fen_king",
            "title": "Miretooth",
            "intro": "At the far black pool, Miretooth rises out of the reeds in one smooth hateful line, as if the whole fen has simply decided on a shape.",
            "enemies": ["miretooth"],
        },
    ],
    "drowned_weir_drowned_causeway": [
        {
            "key": "floodline_watch",
            "title": "Floodline Watch",
            "intro": "Black water slaps the stone line and something old answers from the drowned causeway with the confidence of a post that never got relieved.",
            "enemies": ["drowned_warder", "silt_stalker"],
        },
        {
            "key": "wrong_lanterns",
            "title": "Wrong Lanterns",
            "intro": "The dead lamp posts along the causeway light up one by one, and the things under them start moving as if the signal finally reached them.",
            "enemies": ["hollow_wisp", "drowned_warder"],
        },
        {
            "key": "blackwater_pull",
            "title": "Blackwater Pull",
            "intro": "Silt boils up at the stone edge while a pale marsh light drifts in behind it, already looking for the weakest footing in the party.",
            "enemies": ["silt_stalker", "hollow_wisp"],
        },
    ],
    "drowned_weir_lantern_weir": [
        {
            "key": "weir_hold",
            "title": "Weir Hold",
            "intro": "Old spillway iron starts glowing in sick pulses and the drowned warders beneath it take that as permission rather than warning.",
            "enemies": ["drowned_warder", "drowned_warder"],
        },
        {
            "key": "spillway_lights",
            "title": "Spillway Lights",
            "intro": "Light gathers over the drowned iron ribs just long enough to show you what was waiting in the channels underneath.",
            "enemies": ["hollow_wisp", "hollow_wisp", "silt_stalker"],
        },
        {
            "key": "keeper_line",
            "title": "Keeper Line",
            "intro": "One blackwater keeper steps into the path while something quicker circles the flooded stone just out of clean sight.",
            "enemies": ["drowned_warder", "silt_stalker"],
        },
    ],
    "drowned_weir_sluice_walk": [
        {
            "key": "sluice_press",
            "title": "Sluice Press",
            "intro": "The raised walk turns mean all at once: old warders below, a pale light above, and no room for brave footwork in between.",
            "enemies": ["drowned_warder", "hollow_wisp"],
        },
        {
            "key": "grating_hunt",
            "title": "Grating Hunt",
            "intro": "Something fast claws across the iron grating while the drowned light overhead starts leaning toward you like it knows what comes next.",
            "enemies": ["silt_stalker", "hollow_wisp"],
        },
        {
            "key": "high_walk_claim",
            "title": "High Walk Claim",
            "intro": "The upper walk belongs to the wrong line now, and it has enough bodies left to enforce that opinion.",
            "enemies": ["drowned_warder", "silt_stalker", "hollow_wisp"],
        },
    ],
    "drowned_weir_sunken_lock": [
        {
            "key": "lock_blackwater",
            "title": "Lock Blackwater",
            "intro": "The drowned lock wakes like a held breath finally deciding it has company, and the things guarding it rise with the chain noise.",
            "enemies": ["drowned_warder", "drowned_warder", "hollow_wisp"],
        },
        {
            "key": "chain_line",
            "title": "Chain Line",
            "intro": "A stalker slips through the chained gates while the warders behind it hold the chamber like they expect the town to apologize for coming back.",
            "enemies": ["silt_stalker", "drowned_warder", "drowned_warder"],
        },
        {
            "key": "lock_surge",
            "title": "Lock Surge",
            "intro": "Black water heaves in the chamber and the whole lock answers at once: iron, claws, and that same white drowned light that does not know how to stop.",
            "enemies": ["silt_stalker", "hollow_wisp", "drowned_warder"],
        },
    ],
    "drowned_weir_blackwater_lamp_house": [
        {
            "key": "the_hollow_lantern",
            "title": "The Hollow Lantern",
            "intro": "At the drowned lamp house, the south light folds inward and stands up in the shape that has been wearing it all along.",
            "enemies": ["hollow_lantern"],
        },
    ],
    "goblin_road_trailhead": [
        {
            "key": "trailhead_wolf",
            "title": "A Roadside Wolf",
            "intro": "A road wolf slips from the brush and tests your nerve.",
            "enemies": ["road_wolf"],
        },
        {
            "key": "trailhead_rats",
            "title": "Thorn Rat Scatter",
            "intro": "A pair of thorn rats spill out from a ditch, all teeth and burr-matted fur.",
            "enemies": ["thorn_rat", "thorn_rat"],
        },
        {
            "key": "trailhead_goblin",
            "title": "Goblin Harrier",
            "intro": "A goblin darts out from a ditch, knife-first and badly overconfident.",
            "enemies": ["goblin_sneak"],
        },
    ],
    "goblin_road_old_fence_line": [
        {
            "key": "fencebreakers",
            "title": "Fencebreakers",
            "intro": "Two goblins are still at the fence line, hacking loose boards for spite or firewood.",
            "enemies": ["goblin_sneak", "goblin_cutter"],
        },
        {
            "key": "wolf_and_raider",
            "title": "Mud and Teeth",
            "intro": "A goblin raider and a hungry wolf have both decided this stretch of road belongs to them.",
            "enemies": ["road_wolf", "goblin_cutter"],
        },
        {
            "key": "stone_and_knife",
            "title": "Stone and Knife",
            "intro": "A goblin slinger peppers the road with stolen stones while a cutter rushes in behind him.",
            "enemies": ["goblin_slinger", "goblin_cutter"],
        },
    ],
    "goblin_road_wolf_turn": [
        {
            "key": "wolf_turn_pack",
            "title": "Wolf Turn Pack",
            "intro": "Shapes move in the bend ahead. The wolves are no longer pretending to fear the road.",
            "enemies": ["road_wolf", "road_wolf"],
        },
        {
            "key": "ambush_turn",
            "title": "Turn Ambush",
            "intro": "A goblin pair lunges out as you round the bend, one high and one low.",
            "enemies": ["goblin_slinger", "goblin_cutter"],
        },
    ],
    "goblin_road_fencebreaker_camp": [
        {
            "key": "ruks_stand",
            "title": "Ruk the Fence-Cutter",
            "intro": "A heavy goblin rises from behind the chopped rails and drags a jagged axe through the dirt.",
            "enemies": ["ruk_fence_cutter"],
        }
    ],
    "whispering_woods_trailhead": [
        {
            "key": "woods_wolf",
            "title": "Silent Prowler",
            "intro": "A forest wolf slips between the trunks and comes in low, testing your line.",
            "enemies": ["forest_wolf"],
        },
        {
            "key": "web_and_rot",
            "title": "Web and Rot",
            "intro": "A cave spider descends from the roots while a mossling stirs awake in the damp brush.",
            "enemies": ["cave_spider", "mossling"],
        },
        {
            "key": "embers_in_the_brush",
            "title": "Embers in the Brush",
            "intro": "A briar imp crackles somewhere ahead while a forest wolf circles to cut off retreat.",
            "enemies": ["briar_imp", "forest_wolf"],
        },
    ],
    "whispering_woods_old_stone_path": [
        {
            "key": "stone_path_spiders",
            "title": "Stone Path Web",
            "intro": "Fresh webbing hangs between the leaning stones, and the spiders behind it are not shy.",
            "enemies": ["cave_spider", "cave_spider"],
        },
        {
            "key": "whispering_hex",
            "title": "Whispering Hex",
            "intro": "A briar imp capers between the stones while a mossling anchors the glade with wet roots.",
            "enemies": ["briar_imp", "mossling"],
        },
        {
            "key": "wolf_on_the_path",
            "title": "Rootside Pounce",
            "intro": "A forest wolf darts across the path just as a spider drops behind you.",
            "enemies": ["forest_wolf", "cave_spider"],
        },
    ],
    "whispering_woods_briar_glade": [
        {
            "key": "glade_guardians",
            "title": "Glade Guardians",
            "intro": "The briars stir. One imp laughs, and the moss beneath it rises into a shape with claws.",
            "enemies": ["briar_imp", "mossling"],
        },
        {
            "key": "grey_trail",
            "title": "Grey Trail",
            "intro": "The glade goes quiet except for a low growl somewhere nearby and the crackle of thorn-fire.",
            "enemies": ["forest_wolf", "briar_imp"],
        },
        {
            "key": "snare_roots",
            "title": "Snare Roots",
            "intro": "Root webs and pale silk overlap here, watched by patient things that know this ground.",
            "enemies": ["cave_spider", "mossling"],
        },
    ],
    "whispering_woods_greymaw_hollow": [
        {
            "key": "greymaws_stand",
            "title": "Old Greymaw",
            "intro": "A massive scarred wolf rises from the hollow, vanishes into the brush, and begins to circle.",
            "enemies": ["old_greymaw"],
        }
    ],
    "old_barrow_field_causeway": [
        {
            "key": "causeway_rattle",
            "title": "Causeway Rattle",
            "intro": "Something clatters under the old stones and a skeletal soldier hauls itself upright in the lantern gloom.",
            "enemies": ["skeletal_soldier"],
        },
        {
            "key": "crow_pass",
            "title": "Crow Pass",
            "intro": "A grave crow dives from a marker post just as bones start knocking together in the ditch below.",
            "enemies": ["grave_crow", "skeletal_soldier"],
        },
    ],
    "old_barrow_field_marker_row": [
        {
            "key": "shade_between_stones",
            "title": "Shade Between Stones",
            "intro": "A restless shade unthreads itself from the marker row while a crow wheels low over your shoulder.",
            "enemies": ["restless_shade", "grave_crow"],
        },
        {
            "key": "old_watch",
            "title": "Old Watch",
            "intro": "The line of old markers wakes all at once: bone, black wings, and a low pale light in the grass.",
            "enemies": ["skeletal_soldier", "grave_crow", "barrow_wisp"],
        },
    ],
    "old_barrow_field_barrow_circle": [
        {
            "key": "circle_guard",
            "title": "Circle Guard",
            "intro": "At the center stones, old burial lights gather around whatever still remembers being posted here.",
            "enemies": ["skeletal_soldier", "restless_shade", "barrow_wisp"],
        },
        {
            "key": "mourners_knot",
            "title": "Mourners' Knot",
            "intro": "A hush falls over the circle before shades and dead lights roll toward you from three sides.",
            "enemies": ["restless_shade", "restless_shade", "barrow_wisp"],
        },
    ],
    "old_barrow_field_sunken_dais": [
        {
            "key": "edrics_vigil",
            "title": "Sir Edric the Restless",
            "intro": "Armor shifts on the sunken dais. A dead knight lifts his head, draws a ruined blade, and remembers command.",
            "enemies": ["sir_edric_restless"],
        }
    ],
}


ENEMY_TEMPERAMENT_OVERRIDES = {
    "thorn_rat": "wary",
    "road_wolf": "wary",
    "forest_wolf": "wary",
    "old_greymaw": "relentless",
    "ruk_fence_cutter": "relentless",
    "captain_varn_blackreed": "relentless",
    "grubnak_the_pot_king": "relentless",
    "miretooth": "relentless",
    "hollow_lantern": "relentless",
    "sir_edric_restless": "relentless",
}

TEMPERAMENT_LABELS = {
    "passive": "Passive",
    "wary": "Wary",
    "territorial": "Territorial",
    "aggressive": "Aggressive",
    "relentless": "Relentless",
}


def get_enemy_temperament(template_key, template=None):
    """Return the baseline temperament for an enemy template."""

    template = template or ENEMY_TEMPLATES[template_key]
    if template_key in ENEMY_TEMPERAMENT_OVERRIDES:
        return ENEMY_TEMPERAMENT_OVERRIDES[template_key]

    tags = set(template.get("tags") or [])
    if "boss" in tags:
        return "relentless"
    if tags.intersection({"goblin", "bandit", "raider", "soldier", "undead"}):
        return "aggressive"
    if tags.intersection({"spider", "plant", "web", "moss", "fey"}):
        return "territorial"
    if tags.intersection({"wolf", "rat", "beast", "crow"}):
        return "wary"
    return "aggressive"


def get_enemy_temperament_label(temperament):
    """Return the player-facing label for a temperament key."""

    return TEMPERAMENT_LABELS.get(temperament, str(temperament or "").title() or "Aggressive")


def get_enemy_rank(template_key, template=None):
    """Return a coarse encounter-rank used for room threat evaluation."""

    template = template or ENEMY_TEMPLATES[template_key]
    xp_value = max(1, int(template.get("xp", 1)))
    tags = set(template.get("tags") or [])
    rank = max(1, int(round((xp_value + 10) / 25.0)))
    if "boss" in tags:
        rank += 1
    return rank


def get_relative_threat_label(enemy_rank, effective_party_level):
    """Return a MUD-style threat read for this enemy against the current party."""

    delta = float(effective_party_level or 1) - float(enemy_rank or 1)
    if delta >= 2.5:
        return "Trivial"
    if delta >= 1.0:
        return "Fair"
    if delta >= -0.5:
        return "Dangerous"
    return "Deadly"
