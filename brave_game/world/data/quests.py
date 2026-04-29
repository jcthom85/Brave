"""Quest definitions for the first Brave slice."""

STARTING_QUESTS = [
    "practice_makes_heroes",
    "rats_in_the_kettle",
    "roadside_howls",
    "fencebreakers",
    "ruk_the_fence_cutter",
    "what_whispers_in_the_wood",
    "herbs_for_sister_maybelle",
    "greymaws_trail",
    "bridgework_for_joss",
    "signal_in_the_scrap",
    "foreman_coilback",
    "lanterns_at_dusk",
    "do_not_disturb_the_dead",
    "the_knight_without_rest",
    "smoke_on_the_ridge",
    "loose_arrows",
    "captain_varn_blackreed",
    "below_the_fencebreakers",
    "gutters_and_hexes",
    "the_pot_kings_feast",
    "bogwater_rumors",
    "lights_in_the_reeds",
    "miretooths_claim",
    "the_south_light",
    "locks_under_blackwater",
    "the_hollow_lantern",
]

QUEST_REGIONS = {
    "practice_makes_heroes": "Brambleford",
    "rats_in_the_kettle": "Brambleford",
    "roadside_howls": "Goblin Road",
    "fencebreakers": "Goblin Road",
    "ruk_the_fence_cutter": "Goblin Road",
    "bridgework_for_joss": "Junk-Yard Planet",
    "signal_in_the_scrap": "Junk-Yard Planet",
    "foreman_coilback": "Junk-Yard Planet",
    "what_whispers_in_the_wood": "Whispering Woods",
    "herbs_for_sister_maybelle": "Whispering Woods",
    "greymaws_trail": "Whispering Woods",
    "lanterns_at_dusk": "Old Barrow Field",
    "do_not_disturb_the_dead": "Old Barrow Field",
    "the_knight_without_rest": "Old Barrow Field",
    "smoke_on_the_ridge": "Ruined Watchtower",
    "loose_arrows": "Ruined Watchtower",
    "captain_varn_blackreed": "Ruined Watchtower",
    "below_the_fencebreakers": "Goblin Warrens",
    "gutters_and_hexes": "Goblin Warrens",
    "the_pot_kings_feast": "Goblin Warrens",
    "bogwater_rumors": "Blackfen",
    "lights_in_the_reeds": "Blackfen",
    "miretooths_claim": "Blackfen",
    "the_south_light": "Drowned Weir",
    "locks_under_blackwater": "Drowned Weir",
    "the_hollow_lantern": "Drowned Weir",
}


def get_quest_region(quest_key):
    """Return the broad region label for a quest."""

    return QUEST_REGIONS.get(quest_key, "Other Fronts")


def group_quest_keys_by_region(quest_keys):
    """Group quest keys by region while preserving first-seen order."""

    grouped = []
    buckets = {}
    for quest_key in quest_keys:
        region = get_quest_region(quest_key)
        if region not in buckets:
            buckets[region] = []
            grouped.append((region, buckets[region]))
        buckets[region].append(quest_key)
    return grouped


QUESTS = {
    "practice_makes_heroes": {
        "title": "Practice Makes Heroes",
        "giver": "Captain Harl Rowan",
        "summary": "Report to Captain Harl after the alarm and get pointed at the first town problem.",
        "next_step": "Go south to Town Green, read the fresh notice if you need direction, then head west to the inn and speak with Uncle Pib Underbough.",
        "objectives": [
            {
                "type": "talk_to_npc",
                "npc_id": "captain_harl_rowan",
                "description": "Report to Captain Harl Rowan in the Training Yard.",
            }
        ],
        "rewards": {"xp": 20, "silver": 6},
    },
    "rats_in_the_kettle": {
        "title": "Rats in the Kettle",
        "giver": "Uncle Pib Underbough",
        "summary": "Drive the alarm-spooked thorn rats out of the inn cellar before they chew through supplies the town may need.",
        "prerequisites": ["practice_makes_heroes"],
        "next_step": "Go east to the East Gate and speak with Mira Fenleaf about the cut road.",
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "brambleford_rat_and_kettle_cellar",
                "description": "Head down into the Rat and Kettle Cellar beneath the inn.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "rat",
                "count": 3,
                "description": "Defeat 3 thorn rats before they ruin more stores.",
            },
        ],
        "rewards": {"xp": 35, "silver": 8, "items": [{"item": "innkeepers_fishpie", "quantity": 1}]},
    },
    "roadside_howls": {
        "title": "Roadside Howls",
        "giver": "Mira Fenleaf",
        "summary": "Scout the eastern road, read the tracks, and learn whether the dead lantern and cut fences are connected.",
        "prerequisites": ["rats_in_the_kettle"],
        "next_step": "Follow the cut fences east and thin the goblin cutters still working along Goblin Road.",
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "brambleford_east_gate",
                "description": "Check in with Mira at the East Gate.",
            },
            {
                "type": "visit_room",
                "room_id": "goblin_road_old_fence_line",
                "description": "Reach the Old Fence Line and inspect the cut rails.",
            },
            {
                "type": "visit_room",
                "room_id": "goblin_road_wolf_turn",
                "description": "Push as far as Wolf Turn and follow the damage toward its source.",
            },
        ],
        "rewards": {"xp": 25, "silver": 10, "items": [{"item": "wharfside_skewers", "quantity": 1}]},
    },
    "fencebreakers": {
        "title": "Fencebreakers",
        "giver": "Mira Fenleaf",
        "summary": "Stop the goblin cutters stripping fence rails and look for the pattern behind the road damage.",
        "prerequisites": ["roadside_howls"],
        "next_step": "Push through Wolf Turn to Fencebreaker Camp and find the brute ordering the road cut.",
        "objectives": [
            {
                "type": "defeat_enemy",
                "enemy_tag": "goblin",
                "count": 2,
                "description": "Defeat 2 goblin cutters or raiders working the fence line.",
            }
        ],
        "rewards": {"xp": 30, "silver": 12},
    },
    "ruk_the_fence_cutter": {
        "title": "Ruk the Fence-Cutter",
        "giver": "Mira Fenleaf",
        "summary": "Track down the goblin brute leading the fence raids and find out how much of the morning alarm belongs to him.",
        "prerequisites": ["fencebreakers"],
        "next_step": "After Ruk falls, check in with Mira, Sister Maybelle, or Joss. The road is safer, but the black lantern is still unanswered.",
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "goblin_road_fencebreaker_camp",
                "description": "Find the Fencebreaker Camp beyond Wolf Turn.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "ruk",
                "description": "Defeat Ruk the Fence-Cutter and break the first road threat.",
            },
        ],
        "rewards": {"xp": 40, "silver": 18},
    },
    "bridgework_for_joss": {
        "title": "Bridgework for Joss",
        "giver": "Joss Veller",
        "summary": "Help Joss steady the Junk-Yard bridge by reaching the relay trench and bringing back a live flux coil.",
        "prerequisites": ["ruk_the_fence_cutter"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "junkyard_planet_relay_trench",
                "description": "Reach the Relay Trench beyond the first salvage drifts.",
            },
            {
                "type": "collect_item",
                "item_id": "flux_coil",
                "count": 1,
                "description": "Recover a live Flux Coil from Junk-Yard salvage machines.",
            },
        ],
        "rewards": {"xp": 130, "silver": 12},
    },
    "signal_in_the_scrap": {
        "title": "Signal in the Scrap",
        "giver": "Joss Veller",
        "summary": "Push deeper into the scrapfield, chart the crane grave, and recover a shard of anchor glass for the observatory lens.",
        "prerequisites": ["bridgework_for_joss"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "junkyard_planet_crane_grave",
                "description": "Reach the Crane Grave deeper in Junk-Yard Planet.",
            },
            {
                "type": "collect_item",
                "item_id": "anchor_glass_shard",
                "count": 1,
                "description": "Recover an Anchor Glass Shard from the relay swarm.",
            },
        ],
        "rewards": {"xp": 150, "silver": 16},
    },
    "foreman_coilback": {
        "title": "Foreman Coilback",
        "giver": "Joss Veller",
        "summary": "Descend into the Anchor Pit and destroy the salvage foreman that keeps the Junk-Yard bridge violent and unstable.",
        "prerequisites": ["signal_in_the_scrap"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "junkyard_planet_anchor_pit",
                "description": "Find the Anchor Pit at the heart of the salvage field.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "coilback",
                "description": "Defeat Foreman Coilback.",
            },
        ],
        "rewards": {
            "xp": 190,
            "silver": 24,
            "trophies": ["junkyard_beacon_core"],
        },
    },
    "what_whispers_in_the_wood": {
        "title": "What Whispers in the Wood",
        "giver": "Sister Maybelle",
        "summary": "Scout the first reaches of Whispering Woods and find where the old unease is thickest.",
        "prerequisites": ["ruk_the_fence_cutter"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "whispering_woods_trailhead",
                "description": "Enter Whispering Woods by the old trail.",
            },
            {
                "type": "visit_room",
                "room_id": "whispering_woods_briar_glade",
                "description": "Reach the Briar Glade deeper in the woods.",
            },
        ],
        "rewards": {"xp": 100},
    },
    "herbs_for_sister_maybelle": {
        "title": "Herbs for Sister Maybelle",
        "giver": "Sister Maybelle",
        "summary": "Gather enough moonleaf from the whispering glades to keep Brambleford supplied with poultices.",
        "prerequisites": ["what_whispers_in_the_wood"],
        "objectives": [
            {
                "type": "collect_item",
                "item_id": "moonleaf_sprig",
                "count": 3,
                "description": "Gather 3 Moonleaf Sprigs in Whispering Woods.",
            }
        ],
        "rewards": {"xp": 110},
    },
    "greymaws_trail": {
        "title": "Greymaw's Trail",
        "giver": "Mira Fenleaf",
        "summary": "Track the scarred wolf haunting the deep trail and break its hold on the woods.",
        "prerequisites": ["what_whispers_in_the_wood"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "whispering_woods_greymaw_hollow",
                "description": "Find Greymaw's Hollow beneath the split oak.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "greymaw",
                "description": "Defeat Old Greymaw.",
            },
        ],
        "rewards": {"xp": 140},
    },
    "lanterns_at_dusk": {
        "title": "Lanterns at Dusk",
        "giver": "Mayor Elric Thorne",
        "summary": "Meet with the mayor and the chapel, then inspect the barrow causeway where the town's western lanterns have started going out.",
        "prerequisites": ["greymaws_trail"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "brambleford_mayors_hall",
                "description": "Report to Mayor Elric Thorne in Mayor's Hall.",
            },
            {
                "type": "visit_room",
                "room_id": "brambleford_chapel_dawn_bell",
                "description": "Speak with Brother Alden at the Chapel of the Dawn Bell.",
            },
            {
                "type": "visit_room",
                "room_id": "old_barrow_field_causeway",
                "description": "Inspect the Old Barrow causeway beyond the woods.",
            },
        ],
        "rewards": {"xp": 140, "silver": 10},
    },
    "do_not_disturb_the_dead": {
        "title": "Do Not Disturb the Dead",
        "giver": "Brother Alden",
        "summary": "Push into Old Barrow Field and cut down the first dead things that have started walking there.",
        "prerequisites": ["lanterns_at_dusk"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "old_barrow_field_barrow_circle",
                "description": "Reach the Barrow Circle deeper in the field.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "undead",
                "count": 4,
                "description": "Defeat 4 undead in Old Barrow Field.",
            },
        ],
        "rewards": {"xp": 160, "silver": 12},
    },
    "the_knight_without_rest": {
        "title": "The Knight Without Rest",
        "giver": "Brother Alden",
        "summary": "Find the fallen knight haunting the deepest barrow and lay Sir Edric to rest.",
        "prerequisites": ["do_not_disturb_the_dead"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "old_barrow_field_sunken_dais",
                "description": "Find the Sunken Dais at the heart of Old Barrow Field.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "edric",
                "description": "Defeat Sir Edric the Restless.",
            },
        ],
        "rewards": {"xp": 220, "silver": 20},
    },
    "smoke_on_the_ridge": {
        "title": "Smoke on the Ridge",
        "giver": "Captain Harl Rowan",
        "summary": "Push beyond the old goblin camp and confirm whether the ruined border tower has fallen fully into bandit hands.",
        "prerequisites": ["the_knight_without_rest"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "ruined_watchtower_approach",
                "description": "Reach the Watchtower Approach beyond Fencebreaker Camp.",
            },
            {
                "type": "visit_room",
                "room_id": "ruined_watchtower_breach_yard",
                "description": "Push into the ruined outer yard and confirm the tower is occupied.",
            },
        ],
        "rewards": {"xp": 180, "silver": 14},
    },
    "loose_arrows": {
        "title": "Loose Arrows",
        "giver": "Captain Harl Rowan",
        "summary": "Break the tower's forward line, clear the ledge, and thin the bandits before they can lock the climb down completely.",
        "prerequisites": ["smoke_on_the_ridge"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "ruined_watchtower_archers_ledge",
                "description": "Reach Archer's Ledge beside the tower yard.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "bandit",
                "count": 5,
                "description": "Defeat 5 bandits at the Ruined Watchtower.",
            },
        ],
        "rewards": {"xp": 210, "silver": 16},
    },
    "captain_varn_blackreed": {
        "title": "Captain Varn Blackreed",
        "giver": "Captain Harl Rowan",
        "summary": "Climb to the broken crown of the tower and bring down the bandit captain before he turns the ridge into a permanent noose over Brambleford's road.",
        "prerequisites": ["loose_arrows"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "ruined_watchtower_blackreed_roost",
                "description": "Reach Blackreed's Roost at the top of the tower.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "blackreed",
                "description": "Defeat Captain Varn Blackreed.",
            },
        ],
        "rewards": {
            "xp": 260,
            "silver": 28,
            "trophies": ["blackreed_battle_standard"],
        },
    },
    "below_the_fencebreakers": {
        "title": "Below the Fencebreakers",
        "giver": "Mira Fenleaf",
        "summary": "Follow the goblin retreat east of Ruk's old camp and confirm where the road-cutters have really been nesting.",
        "prerequisites": ["captain_varn_blackreed"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "goblin_warrens_sinkmouth_cut",
                "description": "Find the hidden Sinkmouth Cut east of Fencebreaker Camp.",
            },
            {
                "type": "visit_room",
                "room_id": "goblin_warrens_feast_hall",
                "description": "Push as far as the goblins' Feast Hall beneath the ridge.",
            },
        ],
        "rewards": {"xp": 240, "silver": 16},
    },
    "gutters_and_hexes": {
        "title": "Gutters and Hexes",
        "giver": "Mira Fenleaf",
        "summary": "Thin the warrens before the goblins can spill back onto the road with hexers, cave bats, and tunnel brutes in tow.",
        "prerequisites": ["below_the_fencebreakers"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "goblin_warrens_sludge_run",
                "description": "Reach the Sludge Run deeper in the warrens.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "warren",
                "count": 6,
                "description": "Defeat 6 warrens enemies beneath the ridge.",
            },
        ],
        "rewards": {"xp": 270, "silver": 20},
    },
    "the_pot_kings_feast": {
        "title": "The Pot-King's Feast",
        "giver": "Mira Fenleaf",
        "summary": "Reach the goblin feast court and bring down Grubnak before his warrens become the next thing chewing at Brambleford's road.",
        "prerequisites": ["gutters_and_hexes"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "goblin_warrens_pot_kings_court",
                "description": "Reach the Pot-King's Court at the heart of the warrens.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "potking",
                "description": "Defeat Grubnak the Pot-King.",
            },
        ],
        "rewards": {
            "xp": 320,
            "silver": 34,
            "trophies": ["potking_battered_lid"],
        },
    },
    "bogwater_rumors": {
        "title": "Bogwater Rumors",
        "giver": "Mira Fenleaf",
        "summary": "Follow the bad trail south of the old goblin camp and confirm what has been moving through the Blackfen edge beyond the road country.",
        "prerequisites": ["the_pot_kings_feast"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "blackfen_approach_fenreach_track",
                "description": "Take the south trail from Fencebreaker Camp into Blackfen.",
            },
            {
                "type": "visit_room",
                "room_id": "blackfen_approach_boglight_hollow",
                "description": "Reach Boglight Hollow where the fen lamps start burning wrong.",
            },
        ],
        "rewards": {"xp": 320, "silver": 22},
    },
    "lights_in_the_reeds": {
        "title": "Lights in the Reeds",
        "giver": "Mira Fenleaf",
        "summary": "Push deeper into Blackfen, chart the crow rise, and cut down enough marsh-born threats that the trail stops feeling claimed.",
        "prerequisites": ["bogwater_rumors"],
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "blackfen_approach_carrion_rise",
                "description": "Reach Carrion Rise at the far side of the fen track.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "blackfen",
                "count": 6,
                "description": "Defeat 6 Blackfen threats in the marsh approaches.",
            },
        ],
        "rewards": {"xp": 350, "silver": 30},
    },
    "miretooths_claim": {
        "title": "Miretooth's Claim",
        "giver": "Mira Fenleaf",
        "summary": "Find the predator ruling the Blackfen edge and bring down Miretooth before whatever follows it decides Brambleford is simply the next shoreline.",
        "prerequisites": ["lights_in_the_reeds"],
        "next_step": "Return to Brambleford and speak with Joss Veller at the observatory about the wrong south light beyond the wallow.",
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "blackfen_approach_miretooths_wallow",
                "description": "Reach Miretooth's Wallow beyond the far reeds.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "miretooth",
                "description": "Defeat Miretooth.",
            },
        ],
        "rewards": {
            "xp": 420,
            "silver": 40,
            "trophies": ["miretooth_fen_jaw"],
        },
    },
    "the_south_light": {
        "title": "The South Light",
        "giver": "Joss Veller",
        "summary": "Follow the wrong marsh light beyond Miretooth's Wallow and confirm whether an old drowned lamp line is still feeding whatever has started answering from the fen edge.",
        "prerequisites": ["miretooths_claim"],
        "next_step": "Push through the Sluice Walk and the Sunken Lock, then break the blackwater line before it decides Brambleford belongs on its route.",
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "drowned_weir_drowned_causeway",
                "description": "Cross into the Drowned Causeway beyond Miretooth's Wallow.",
            },
            {
                "type": "visit_room",
                "room_id": "drowned_weir_lantern_weir",
                "description": "Reach Lantern Weir where the wrong south light starts burning in earnest.",
            },
        ],
        "rewards": {"xp": 360, "silver": 26},
    },
    "locks_under_blackwater": {
        "title": "Locks Under Blackwater",
        "giver": "Joss Veller",
        "summary": "Push deeper into the drowned works, reach the inner lock line, and tear through enough of the blackwater ward to expose whatever is still keeping the old lamp burning wrong.",
        "prerequisites": ["the_south_light"],
        "next_step": "Climb to the Blackwater Lamp House and put down the thing wearing the south light.",
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "drowned_weir_sluice_walk",
                "description": "Reach the Sluice Walk above the drowned lock run.",
            },
            {
                "type": "visit_room",
                "room_id": "drowned_weir_sunken_lock",
                "description": "Reach the Sunken Lock at the far side of the drowned works.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "weir",
                "count": 5,
                "description": "Defeat 5 Drowned Weir threats beyond the wallow.",
            },
        ],
        "rewards": {"xp": 390, "silver": 32},
    },
    "the_hollow_lantern": {
        "title": "The Hollow Lantern",
        "giver": "Joss Veller",
        "summary": "Reach the drowned lamp house at the edge of Blackfen and extinguish the thing inside it before the wrong south light grows into the town's next standing problem.",
        "prerequisites": ["locks_under_blackwater"],
        "chapter_complete": "Brambleford's First Hard Chapter",
        "next_step": "Return to Joss, Mayor Elric, or the Trophy Hall and take the win for what it is: the end of Brambleford's first hard chapter.",
        "objectives": [
            {
                "type": "visit_room",
                "room_id": "drowned_weir_blackwater_lamp_house",
                "description": "Reach the Blackwater Lamp House beyond the drowned lock line.",
            },
            {
                "type": "defeat_enemy",
                "enemy_tag": "hollowlantern",
                "description": "Defeat the Hollow Lantern.",
            },
        ],
        "rewards": {
            "xp": 520,
            "silver": 48,
            "trophies": ["hollow_lantern_prism"],
        },
    },
}


# Compatibility exports for older runtime imports. Quest definitions and
# regions are registry-backed so JSON packs remain authoritative.
from world.content.registry import get_content_registry

_QUEST_CONTENT = get_content_registry().quests
STARTING_QUESTS = _QUEST_CONTENT.starting_quests
QUEST_REGIONS = _QUEST_CONTENT.quest_regions
QUESTS = _QUEST_CONTENT.quests
