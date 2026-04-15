"""First-pass handcrafted world data for Brave."""

ROOMS = [
    {
        "id": "brambleford_town_green",
        "key": "Brambleford Town Green",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "G",
        "safe": True,
        "desc": (
            "Lantern posts ring the green like quiet guardians, their brasswork polished by "
            "many practical hands. The square is compact but lively: muddy boots, gossip, and "
            "the reassuring clatter of a frontier town trying very hard to look unbothered."
        ),
    },
    {
        "id": "brambleford_lantern_rest_inn",
        "key": "The Lantern Rest Inn",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": -1,
        "map_y": 0,
        "map_icon": "I",
        "safe": True,
        "desc": (
            "The inn smells of stew, woodsmoke, and fresh bread. Lanternlight warms the beams, "
            "and every table seems to carry either a rumor or a complaint about wolves."
        ),
        "activities": ["cooking"],
    },
    {
        "id": "brambleford_outfitters",
        "key": "Brambleford Outfitters",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": -2,
        "map_y": 0,
        "map_icon": "U",
        "safe": True,
        "desc": (
            "Shelves of boots, rain cloaks, rope, patched travel bags, and sensible trail goods line the walls in "
            "neat practical ranks. Nothing in the room is fancy, but everything looks like it was chosen by someone "
            "who expects bad weather, muddy children, and the occasional goblin."
        ),
    },
    {
        "id": "brambleford_training_yard",
        "key": "Training Yard",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": 0,
        "map_y": 1,
        "map_icon": "Y",
        "safe": True,
        "desc": (
            "Worn posts, chopped practice dummies, and chalked sparring rings fill the yard. "
            "This is where Brambleford tries to turn willing hands into something closer to heroes."
        ),
    },
    {
        "id": "tutorial_gate_walk",
        "key": "Gate Walk",
        "zone": "Wayfarer's Yard",
        "map_region": "wayfarers_yard",
        "map_x": 0,
        "map_y": -1,
        "map_icon": "G",
        "safe": True,
        "desc": (
            "A short fenced walk climbs north away from the main yard, marked by battered signposts and a practice gate "
            "that looks built for instruction more than defense. Brambleford is close enough to feel safe, but the little annex "
            "beyond it is clearly where the town squares away new hands before turning them loose."
        ),
    },
    {
        "id": "tutorial_wayfarers_yard",
        "key": "Wayfarer's Yard",
        "zone": "Wayfarer's Yard",
        "map_region": "wayfarers_yard",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "W",
        "safe": True,
        "desc": (
            "A compact fenced yard sits just above the main training grounds, laid out with deliberate simplicity: a central post, "
            "clear lanes, and enough room to make mistakes without wandering into real danger. The whole place feels built to teach "
            "a traveler how to settle their nerves before the road starts asking harder questions."
        ),
    },
    {
        "id": "tutorial_quartermaster_shed",
        "key": "Quartermaster Shed",
        "zone": "Wayfarer's Yard",
        "map_region": "wayfarers_yard",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "Q",
        "safe": True,
        "desc": (
            "Peg racks, folded blankets, oilcloth bundles, and labeled crates line the little shed wall to wall. Nothing here is ornate, "
            "but everything has a place, and the place of every item looks chosen by someone who expects weather, mud, and avoidable mistakes."
        ),
    },
    {
        "id": "tutorial_family_post",
        "key": "Family Post",
        "zone": "Wayfarer's Yard",
        "map_region": "wayfarers_yard",
        "map_x": 0,
        "map_y": 1,
        "map_icon": "P",
        "safe": True,
        "desc": (
            "A little dispatch post overlooks the yard with chalk slates, route pegs, and a bench meant for regrouping rather than lingering. "
            "Whoever set it up understood that people travel better when somebody has bothered to think about how they find each other again."
        ),
    },
    {
        "id": "tutorial_sparring_ring",
        "key": "Sparring Ring",
        "zone": "Wayfarer's Yard",
        "map_region": "wayfarers_yard",
        "map_x": -1,
        "map_y": 0,
        "map_icon": "S",
        "safe": True,
        "desc": (
            "A chalked ring, nicked practice posts, and a weapons rail mark out the sparring ground. The place feels less like a stage for heroics "
            "and more like somewhere sensible adults teach people not to panic the first time teeth or steel point the wrong way."
        ),
    },
    {
        "id": "tutorial_vermin_pens",
        "key": "Vermin Pens",
        "zone": "Wayfarer's Yard",
        "map_region": "wayfarers_yard",
        "map_x": -1,
        "map_y": -1,
        "map_icon": "V",
        "safe": False,
        "desc": (
            "Low timber pens and rough feed bins crowd the edge of the annex, the sort of place Brambleford uses to keep troublesome yard vermin from "
            "turning into a bigger nuisance. The smell is sharp, the straw is restless, and the lesson is obvious: even small trouble still bites."
        ),
    },
    {
        "id": "brambleford_mayors_hall",
        "key": "Mayor's Hall",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": -1,
        "map_y": 1,
        "map_icon": "M",
        "safe": True,
        "desc": (
            "A practical stone hall with weather notices, petition ledgers, and a long table scarred by years of "
            "local argument. Nothing here is elegant, but everything feels used by people trying to keep the town upright."
        ),
    },
    {
        "id": "brambleford_chapel_dawn_bell",
        "key": "Chapel of the Dawn Bell",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": -2,
        "map_y": 1,
        "map_icon": "C",
        "safe": True,
        "desc": (
            "Soft lampglass, pale stone, and a brass bell frame give the little chapel a steadier kind of warmth than the "
            "inn. Prayer ribbons stir in the draft, and someone has kept every lantern trimmed as if the town's courage depends on it."
        ),
    },
    {
        "id": "brambleford_east_gate",
        "key": "East Gate",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "E",
        "safe": True,
        "desc": (
            "The eastern gate looks sturdy enough, but the road beyond it tells a less comforting "
            "story. Wagon ruts cut through the mud, and the sentries keep glancing toward the hills."
        ),
    },
    {
        "id": "brambleford_hobbyists_wharf",
        "key": "Hobbyist's Wharf",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": 0,
        "map_y": -1,
        "map_icon": "W",
        "safe": True,
        "desc": (
            "A weathered little dock juts into the Bramble River beside a rack of loaner poles, bait "
            "tins, and a bench rubbed smooth by patient elbows. The water is slow here, brown-green in "
            "the shallows and silver where the current catches lanternlight."
        ),
        "activities": ["fishing"],
    },
    {
        "id": "brambleford_ironroot_forge",
        "key": "Ironroot Forge",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": 0,
        "map_y": -2,
        "map_icon": "F",
        "safe": True,
        "desc": (
            "A broad smithy yard opens around a coal-hot forge, a quench trough, and workbenches scarred by years of practical "
            "repair. Fresh nails, bent hinges, spearheads, and half-finished buckles hang from pegs above a clean anvil block "
            "that looks capable of judging your gear on sight."
        ),
    },
    {
        "id": "brambleford_great_observatory",
        "key": "Great Observatory",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": 1,
        "map_y": 1,
        "map_icon": "O",
        "safe": True,
        "desc": (
            "The observatory crowns Brambleford's highest rise, all brass braces, stone arches, and lantern "
            "glass polished brighter than the road probably deserves. A great telescope points upward through "
            "the open dome while a lower chamber hums with stranger work below."
        ),
    },
    {
        "id": "brambleford_trophy_hall",
        "key": "Trophy Hall",
        "zone": "Brambleford",
        "map_region": "brambleford",
        "map_x": 1,
        "map_y": 2,
        "map_icon": "H",
        "safe": True,
        "desc": (
            "Wooden cases, brass plaques, and open wall-hooks fill the hall above the observatory steps. "
            "Some shelves still wait empty, but the room has been built with the confidence of people who "
            "fully intend to bring strange things home."
        ),
    },
    {
        "id": "brambleford_nexus_gate",
        "key": "Nexus Gate",
        "zone": "The Nexus",
        "map_region": "nexus_network",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "N",
        "safe": True,
        "desc": (
            "A circular chamber of old stone and newer fittings surrounds a standing ring of pale light. "
            "Brass plaques, humming anchor lines, and a floor inlaid with star charts make the place feel "
            "half observatory, half impossible harbor."
        ),
        "portal_hub": True,
    },
    {
        "id": "brambleford_rat_and_kettle_cellar",
        "key": "Rat and Kettle Cellar",
        "zone": "Brambleford",
        "map_region": "rat_and_kettle_cellar",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "C",
        "safe": False,
        "desc": (
            "The inn cellar is all stone, old barrel racks, and corners that seem designed specifically "
            "for unpleasant scratching noises. Flour dust, spilled grain, and chewed crate corners make it "
            "clear the rats have been treating it as a festival ground."
        ),
    },
    {
        "id": "junkyard_planet_landing_pad",
        "key": "Junk-Yard Landing",
        "zone": "Junk-Yard Planet",
        "world": "Junk-Yard Planet",
        "resonance": "tech",
        "map_region": "junkyard_planet",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "L",
        "safe": True,
        "desc": (
            "The return side of the gate opens onto a steel platform sunk into an ocean of salvage. Broken "
            "railcars, dish arrays, and hull plates lie under a copper sky while distant towers blink with "
            "cold practical light."
        ),
    },
    {
        "id": "junkyard_planet_scrapway",
        "key": "Scrapway Verge",
        "zone": "Junk-Yard Planet",
        "world": "Junk-Yard Planet",
        "resonance": "tech",
        "map_region": "junkyard_planet",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "S",
        "safe": False,
        "desc": (
            "A narrow path winds between knee-high drifts of stripped wire, cracked panels, and humming scrap. "
            "Motion flickers under the debris whenever the wind pushes hard enough to wake whatever still powers "
            "this place."
        ),
    },
    {
        "id": "junkyard_planet_relay_trench",
        "key": "Relay Trench",
        "zone": "Junk-Yard Planet",
        "world": "Junk-Yard Planet",
        "resonance": "tech",
        "map_region": "junkyard_planet",
        "map_x": 1,
        "map_y": 1,
        "map_icon": "R",
        "safe": False,
        "desc": (
            "A cut trench runs between salvage berms and humming cable towers, every surface striped with old "
            "hazard paint and newer scorch marks. White pulses flicker along the route glass underfoot like the "
            "ground is still trying to remember its orders."
        ),
    },
    {
        "id": "junkyard_planet_crane_grave",
        "key": "Crane Grave",
        "zone": "Junk-Yard Planet",
        "world": "Junk-Yard Planet",
        "resonance": "tech",
        "map_region": "junkyard_planet",
        "map_x": 2,
        "map_y": 0,
        "map_icon": "C",
        "safe": False,
        "desc": (
            "Collapsed yard cranes lean over the salvage field like dead metal herons. Cab glass crunches underfoot, "
            "and half-severed hook-lines sway whenever the wind crosses the pit."
        ),
    },
    {
        "id": "junkyard_planet_anchor_pit",
        "key": "Anchor Pit",
        "zone": "Junk-Yard Planet",
        "world": "Junk-Yard Planet",
        "resonance": "tech",
        "map_region": "junkyard_planet",
        "map_x": 2,
        "map_y": 1,
        "map_icon": "A",
        "safe": False,
        "desc": (
            "A broad salvage pit drops away beneath gantries and broken cranes arranged around a central beacon socket. "
            "The machinery here still obeys something, and whatever that something is has no interest in visitors."
        ),
    },
    {
        "id": "goblin_road_trailhead",
        "key": "Goblin Road Trailhead",
        "zone": "Goblin Road",
        "map_region": "goblin_road",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "T",
        "safe": False,
        "desc": (
            "The road here is still close enough to town that you can imagine help arriving quickly. "
            "Broken fence rails and muddy pawprints argue otherwise."
        ),
    },
    {
        "id": "goblin_road_old_fence_line",
        "key": "Old Fence Line",
        "zone": "Goblin Road",
        "map_region": "goblin_road",
        "map_x": 0,
        "map_y": 1,
        "map_icon": "F",
        "safe": False,
        "desc": (
            "A long stretch of smashed fence marks the edge of several hard-worked fields. "
            "Someone has dragged off planks, and something small has left knife-nicked cuts in the posts."
        ),
    },
    {
        "id": "goblin_road_wolf_turn",
        "key": "Wolf Turn",
        "zone": "Goblin Road",
        "map_region": "goblin_road",
        "map_x": 1,
        "map_y": 1,
        "map_icon": "W",
        "safe": False,
        "desc": (
            "The road bends sharply around a thorny rise, and the wind seems to carry every sound "
            "twice. Prints crisscross the mud here: boot heels, claws, and the narrow mess of goblin feet."
        ),
    },
    {
        "id": "goblin_road_fencebreaker_camp",
        "key": "Fencebreaker Camp",
        "zone": "Goblin Road",
        "map_region": "goblin_road",
        "map_x": 2,
        "map_y": 1,
        "map_icon": "C",
        "safe": False,
        "desc": (
            "Broken wagon frames and stolen fence rails have been stacked into a nasty little camp. "
            "Chopped boards litter the mud, and a chopping block near the fire bears far too many fresh cuts."
        ),
    },
    {
        "id": "whispering_woods_trailhead",
        "key": "Whispering Woods Trail",
        "zone": "Whispering Woods",
        "map_region": "whispering_woods",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "T",
        "safe": False,
        "desc": (
            "The path into the woods narrows beneath old branches and older silence. The air is cooler "
            "here, and every leaf-rustle seems to carry one word too many to be only wind."
        ),
    },
    {
        "id": "whispering_woods_old_stone_path",
        "key": "Old Stone Path",
        "zone": "Whispering Woods",
        "map_region": "whispering_woods",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "S",
        "safe": False,
        "desc": (
            "Broken standing stones lean beside the path like tired sentries. Moss has swallowed the "
            "carvings on most of them, but the woods still feel arranged rather than wild."
        ),
    },
    {
        "id": "whispering_woods_briar_glade",
        "key": "Briar Glade",
        "zone": "Whispering Woods",
        "map_region": "whispering_woods",
        "map_x": 1,
        "map_y": -1,
        "map_icon": "B",
        "safe": False,
        "desc": (
            "A low glade opens under tangled branches where pale herbs grow between thorny roots. "
            "The soil is dark, damp, and disturbed in places where something large keeps circling through."
        ),
    },
    {
        "id": "whispering_woods_greymaw_hollow",
        "key": "Greymaw's Hollow",
        "zone": "Whispering Woods",
        "map_region": "whispering_woods",
        "map_x": 2,
        "map_y": -1,
        "map_icon": "G",
        "safe": False,
        "desc": (
            "A shallow hollow lies beneath a split oak and a ring of claw-scarred stones. Bones, old "
            "fur, and torn brush mark it as a place claimed by a beast that no longer fears torches or men."
        ),
    },
    {
        "id": "old_barrow_field_causeway",
        "key": "Old Barrow Causeway",
        "zone": "Old Barrow Field",
        "map_region": "old_barrow_field",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "C",
        "safe": False,
        "desc": (
            "A stone causeway runs between low burial mounds and leaning lantern posts gone half dark. The air feels colder "
            "here than the rest of the woods, and every step sounds like it might be waking something."
        ),
    },
    {
        "id": "old_barrow_field_marker_row",
        "key": "Marker Row",
        "zone": "Old Barrow Field",
        "map_region": "old_barrow_field",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "M",
        "safe": False,
        "desc": (
            "Weathered grave markers stand shoulder to shoulder in a long uneven row, their names eaten thin by time. Crows perch "
            "where mourners once stood, and pale grit drifts over the inscriptions like breath."
        ),
    },
    {
        "id": "old_barrow_field_barrow_circle",
        "key": "Barrow Circle",
        "zone": "Old Barrow Field",
        "map_region": "old_barrow_field",
        "map_x": 1,
        "map_y": 1,
        "map_icon": "B",
        "safe": False,
        "desc": (
            "Standing stones ring an old burial center packed with broken offerings, guttered lamps, and a hush that feels observed. "
            "The ground inside the circle is trampled by feet that should not still exist."
        ),
    },
    {
        "id": "old_barrow_field_sunken_dais",
        "key": "Sunken Dais",
        "zone": "Old Barrow Field",
        "map_region": "old_barrow_field",
        "map_x": 2,
        "map_y": 1,
        "map_icon": "D",
        "safe": False,
        "desc": (
            "A broad stone platform has sunk into the earth at the oldest point of the field, its steps split and its carved borders "
            "full of rainwater and grave grass. A knight's slab lies at the center beneath the dark outline of a once-holy banner."
        ),
    },
    {
        "id": "ruined_watchtower_approach",
        "key": "Watchtower Approach",
        "zone": "Ruined Watchtower",
        "map_region": "ruined_watchtower",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "A",
        "safe": False,
        "desc": (
            "The old border road climbs into broken stone and thorn brush beneath the shadow of a ruined tower. Smoke stains the "
            "upper rock, bootprints cut through the mud, and the ground has the measured, watchful look of a place people kill from on purpose."
        ),
    },
    {
        "id": "ruined_watchtower_breach_yard",
        "key": "Breach Yard",
        "zone": "Ruined Watchtower",
        "map_region": "ruined_watchtower",
        "map_x": 0,
        "map_y": 1,
        "map_icon": "Y",
        "safe": False,
        "desc": (
            "The tower's outer yard has been half-collapsed into a jagged basin of fallen stone, broken kennels, and old cart iron. "
            "A breach in the wall has become the main entrance, which tells you everything you need to know about the current management."
        ),
    },
    {
        "id": "ruined_watchtower_archers_ledge",
        "key": "Archer's Ledge",
        "zone": "Ruined Watchtower",
        "map_region": "ruined_watchtower",
        "map_x": -1,
        "map_y": 1,
        "map_icon": "L",
        "safe": False,
        "desc": (
            "A narrow ledge of old firing stone overlooks the climb below. Arrow gouges, loose shafts, and kicked rock chips mark it "
            "as the sort of place where people stay alive by making sure someone else doesn't."
        ),
    },
    {
        "id": "ruined_watchtower_cracked_stairs",
        "key": "Cracked Tower Stairs",
        "zone": "Ruined Watchtower",
        "map_region": "ruined_watchtower",
        "map_x": 1,
        "map_y": 1,
        "map_icon": "S",
        "safe": False,
        "desc": (
            "A broken stair curls up along the surviving tower wall, its landings patched with scavenged planks and bad confidence. "
            "Every turn is tight enough for defenders and miserable enough for anyone climbing into them."
        ),
    },
    {
        "id": "ruined_watchtower_blackreed_roost",
        "key": "Blackreed's Roost",
        "zone": "Ruined Watchtower",
        "map_region": "ruined_watchtower",
        "map_x": 1,
        "map_y": 2,
        "map_icon": "R",
        "safe": False,
        "desc": (
            "The broken crown of the watchtower has been turned into a command perch of rain-dark canvas, scavenged crates, and a clear killing view over the ridge roads below. "
            "Whoever holds this height gets to decide who travels the east country in peace."
        ),
    },
    {
        "id": "goblin_warrens_sinkmouth_cut",
        "key": "Sinkmouth Cut",
        "zone": "Goblin Warrens",
        "map_region": "goblin_warrens",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "S",
        "safe": False,
        "desc": (
            "East of the old camp, the ground has slumped into a soot-dark cut where broken fencing, goblin rope ladders, and churned mud spill into the hill. "
            "Smoke breathes up from below with the smell of wet iron, bad stew, and a population that has stopped pretending it belongs on the road."
        ),
    },
    {
        "id": "goblin_warrens_torchgut_tunnel",
        "key": "Torchgut Tunnel",
        "zone": "Goblin Warrens",
        "map_region": "goblin_warrens",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "T",
        "safe": False,
        "desc": (
            "A low-bellied tunnel twists through greasy stone under smoky torch cages. The walls sweat, the floor grits underfoot, and every sound seems to travel ahead "
            "of you as if the warrens are passing word along faster than feet ought to."
        ),
    },
    {
        "id": "goblin_warrens_bone_midden",
        "key": "Bone Midden",
        "zone": "Goblin Warrens",
        "map_region": "goblin_warrens",
        "map_x": 2,
        "map_y": 0,
        "map_icon": "B",
        "safe": False,
        "desc": (
            "The tunnel opens into a refuse chamber stacked with cracked bone, gnawed cart boards, and stripped mail rings. Bats cling to the ceiling ribs while old feast "
            "fires smolder under a stink strong enough to feel like a warning all by itself."
        ),
    },
    {
        "id": "goblin_warrens_sludge_run",
        "key": "Sludge Run",
        "zone": "Goblin Warrens",
        "map_region": "goblin_warrens",
        "map_x": 1,
        "map_y": -1,
        "map_icon": "L",
        "safe": False,
        "desc": (
            "A runoff trench cuts through the lower warrens, carrying black kitchen grease, cave seep, and things that should have stayed politely dead in barrels. "
            "Boards bridge the worst of it, but most of them look chosen by goblins for confidence rather than quality."
        ),
    },
    {
        "id": "goblin_warrens_feast_hall",
        "key": "Feast Hall",
        "zone": "Goblin Warrens",
        "map_region": "goblin_warrens",
        "map_x": 2,
        "map_y": -1,
        "map_icon": "F",
        "safe": False,
        "desc": (
            "A broad cave hall has been claimed with stolen tables, hacked banners, splintered casks, and enough greasy torchlight to make everything shine in all the wrong places. "
            "Noise carries badly here, like the room remembers too many ugly celebrations and is always ready for one more."
        ),
    },
    {
        "id": "goblin_warrens_pot_kings_court",
        "key": "Pot-King's Court",
        "zone": "Goblin Warrens",
        "map_region": "goblin_warrens",
        "map_x": 3,
        "map_y": -1,
        "map_icon": "P",
        "safe": False,
        "desc": (
            "The deepest court is half throne room, half cookfire pit, built around an iron slab table and a raised stone seat crusted with soot. Pot lids, split shields, and bent "
            "utensils hang like trophies, and the whole chamber feels arranged by someone who thinks hunger is a kind of law."
        ),
    },
    {
        "id": "blackfen_approach_fenreach_track",
        "key": "Fenreach Track",
        "zone": "Blackfen Approach",
        "map_region": "blackfen_approach",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "T",
        "safe": False,
        "desc": (
            "South of the old camp the road gives up and becomes a half-drowned track through reeds, black puddles, and wind that smells like old water. "
            "Nothing in Blackfen looks fully settled, which somehow makes it feel even more claimed."
        ),
    },
    {
        "id": "blackfen_approach_reedflats",
        "key": "Reedflats",
        "zone": "Blackfen Approach",
        "map_region": "blackfen_approach",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "R",
        "safe": False,
        "desc": (
            "Broad flats of knee-high reeds spread across standing water and slick mud shelves, broken only by a few miserable boards and the occasional dead stump. "
            "The wind moves through the grass like something large trying not to sound like feet."
        ),
    },
    {
        "id": "blackfen_approach_boglight_hollow",
        "key": "Boglight Hollow",
        "zone": "Blackfen Approach",
        "map_region": "blackfen_approach",
        "map_x": 1,
        "map_y": 1,
        "map_icon": "B",
        "safe": False,
        "desc": (
            "A low basin of dark water and half-sunk root arches catches the wind and holds the light badly. Pale fen-lamps gather over the hollow as if the marsh is trying to invent stars "
            "somewhere nobody asked for them."
        ),
    },
    {
        "id": "blackfen_approach_carrion_rise",
        "key": "Carrion Rise",
        "zone": "Blackfen Approach",
        "map_region": "blackfen_approach",
        "map_x": 2,
        "map_y": 0,
        "map_icon": "C",
        "safe": False,
        "desc": (
            "A narrow rise of firmer mud shoulders up above the marsh pools, marked by picked-clean bones, black feathers, and a few broken stakes from some older attempt to claim the ground. "
            "From here the fen looks less like weather and more like intent."
        ),
    },
    {
        "id": "blackfen_approach_miretooths_wallow",
        "key": "Miretooth's Wallow",
        "zone": "Blackfen Approach",
        "map_region": "blackfen_approach",
        "map_x": 2,
        "map_y": 1,
        "map_icon": "M",
        "safe": False,
        "desc": (
            "A black-water wallow opens between drowned roots and reed berms, churned by something heavy enough to leave trenches where a smaller beast would leave prints. "
            "The marsh goes strangely still here, like it expects one name to matter more than the wind."
        ),
    },
    {
        "id": "drowned_weir_drowned_causeway",
        "key": "Drowned Causeway",
        "zone": "Drowned Weir",
        "map_region": "drowned_weir",
        "map_x": 0,
        "map_y": 0,
        "map_icon": "C",
        "safe": False,
        "desc": (
            "A half-sunk causeway of old survey stone pushes east out of the marsh edge, its coping blocks slick with black water and hung with drowned reed rope. "
            "The farther stretch is lined by dead lamp posts whose glass should be dark, but one pale line of wrong light still finds a way through them."
        ),
    },
    {
        "id": "drowned_weir_lantern_weir",
        "key": "Lantern Weir",
        "zone": "Drowned Weir",
        "map_region": "drowned_weir",
        "map_x": 1,
        "map_y": 0,
        "map_icon": "W",
        "safe": False,
        "desc": (
            "Stone spillways and drowned lamp braces divide the marsh water into dark channels that no longer answer the river cleanly. "
            "Green-white light crawls along the ironwork in slow pulses, as if the old weir is still trying to perform a duty everyone else forgot to dismiss."
        ),
    },
    {
        "id": "drowned_weir_sluice_walk",
        "key": "Sluice Walk",
        "zone": "Drowned Weir",
        "map_region": "drowned_weir",
        "map_x": 1,
        "map_y": 1,
        "map_icon": "S",
        "safe": False,
        "desc": (
            "A raised walk of iron grating and split planks runs above the drowned control channels, each step echoing through black water and old machinery below. "
            "The lamp line overhead burns too steadily for a ruin, and the sound under it is not quite current and not quite breathing."
        ),
    },
    {
        "id": "drowned_weir_sunken_lock",
        "key": "Sunken Lock",
        "zone": "Drowned Weir",
        "map_region": "drowned_weir",
        "map_x": 2,
        "map_y": 0,
        "map_icon": "L",
        "safe": False,
        "desc": (
            "The far lock chamber has collapsed into a black basin of chained gates, warped bollards, and water held too still between stone jaws. "
            "Whatever keeps the old works alive is strongest here, where the lock should have failed decades ago and somehow never quite did."
        ),
    },
    {
        "id": "drowned_weir_blackwater_lamp_house",
        "key": "Blackwater Lamp House",
        "zone": "Drowned Weir",
        "map_region": "drowned_weir",
        "map_x": 2,
        "map_y": 1,
        "map_icon": "H",
        "safe": False,
        "desc": (
            "A drowned lamp tower leans over the marsh on old stone feet, its lower floor flooded and its upper chamber lit by a cold lantern that no hand should still be trimming. "
            "Broken lens brass, wet wick frames, and black water reflections turn the whole room into the inside of a light that learned the wrong lesson from being left alone."
        ),
    },
]

EXITS = [
    {
        "id": "town_green_to_inn",
        "source": "brambleford_town_green",
        "destination": "brambleford_lantern_rest_inn",
        "key": "west",
        "direction": "west",
        "label": "Lantern Rest Inn",
        "aliases": ["w", "inn", "lantern rest", "lantern rest inn"],
    },
    {
        "id": "inn_to_town_green",
        "source": "brambleford_lantern_rest_inn",
        "destination": "brambleford_town_green",
        "key": "east",
        "direction": "east",
        "label": "Town Green",
        "aliases": ["e", "green", "town green"],
    },
    {
        "id": "inn_to_outfitters",
        "source": "brambleford_lantern_rest_inn",
        "destination": "brambleford_outfitters",
        "key": "west",
        "direction": "west",
        "label": "Brambleford Outfitters",
        "aliases": ["w", "outfitters", "shop", "brambleford outfitters"],
    },
    {
        "id": "inn_to_cellar",
        "source": "brambleford_lantern_rest_inn",
        "destination": "brambleford_rat_and_kettle_cellar",
        "key": "down",
        "direction": "down",
        "label": "Rat and Kettle Cellar",
        "aliases": ["d", "cellar", "basement", "rat and kettle cellar"],
    },
    {
        "id": "inn_to_mayors_hall",
        "source": "brambleford_lantern_rest_inn",
        "destination": "brambleford_mayors_hall",
        "key": "north",
        "direction": "north",
        "label": "Mayor's Hall",
        "aliases": ["n", "hall", "mayor", "mayor's hall", "mayors hall"],
    },
    {
        "id": "outfitters_to_inn",
        "source": "brambleford_outfitters",
        "destination": "brambleford_lantern_rest_inn",
        "key": "east",
        "direction": "east",
        "label": "Lantern Rest Inn",
        "aliases": ["e", "inn", "lantern rest", "lantern rest inn"],
    },
    {
        "id": "outfitters_to_chapel",
        "source": "brambleford_outfitters",
        "destination": "brambleford_chapel_dawn_bell",
        "key": "north",
        "direction": "north",
        "label": "Chapel of the Dawn Bell",
        "aliases": ["n", "chapel", "dawn bell", "chapel of the dawn bell"],
    },
    {
        "id": "mayors_hall_to_inn",
        "source": "brambleford_mayors_hall",
        "destination": "brambleford_lantern_rest_inn",
        "key": "south",
        "direction": "south",
        "label": "Lantern Rest Inn",
        "aliases": ["s", "inn", "lantern rest", "lantern rest inn"],
    },
    {
        "id": "cellar_to_inn",
        "source": "brambleford_rat_and_kettle_cellar",
        "destination": "brambleford_lantern_rest_inn",
        "key": "up",
        "direction": "up",
        "label": "Lantern Rest Inn",
        "aliases": ["u", "inn", "lantern rest", "lantern rest inn"],
    },
    {
        "id": "town_green_to_training_yard",
        "source": "brambleford_town_green",
        "destination": "brambleford_training_yard",
        "key": "north",
        "direction": "north",
        "label": "Training Yard",
        "aliases": ["n", "yard", "training yard"],
    },
    {
        "id": "training_yard_to_gate_walk",
        "source": "brambleford_training_yard",
        "destination": "tutorial_gate_walk",
        "key": "north",
        "direction": "north",
        "label": "Gate Walk",
        "aliases": ["n", "gate walk", "annex", "tutorial yard", "wayfarers yard", "wayfarer's yard"],
    },
    {
        "id": "gate_walk_to_training_yard",
        "source": "tutorial_gate_walk",
        "destination": "brambleford_training_yard",
        "key": "south",
        "direction": "south",
        "label": "Training Yard",
        "aliases": ["s", "yard", "training yard", "town"],
    },
    {
        "id": "gate_walk_to_wayfarers_yard",
        "source": "tutorial_gate_walk",
        "destination": "tutorial_wayfarers_yard",
        "key": "north",
        "direction": "north",
        "label": "Wayfarer's Yard",
        "aliases": ["n", "yard", "wayfarers yard", "wayfarer's yard"],
    },
    {
        "id": "wayfarers_yard_to_gate_walk",
        "source": "tutorial_wayfarers_yard",
        "destination": "tutorial_gate_walk",
        "key": "south",
        "direction": "south",
        "label": "Gate Walk",
        "aliases": ["s", "gate", "gate walk", "training yard"],
    },
    {
        "id": "wayfarers_yard_to_quartermaster_shed",
        "source": "tutorial_wayfarers_yard",
        "destination": "tutorial_quartermaster_shed",
        "key": "east",
        "direction": "east",
        "label": "Quartermaster Shed",
        "aliases": ["e", "shed", "quartermaster", "quartermaster shed"],
    },
    {
        "id": "quartermaster_shed_to_wayfarers_yard",
        "source": "tutorial_quartermaster_shed",
        "destination": "tutorial_wayfarers_yard",
        "key": "west",
        "direction": "west",
        "label": "Wayfarer's Yard",
        "aliases": ["w", "yard", "wayfarers yard", "wayfarer's yard"],
    },
    {
        "id": "wayfarers_yard_to_family_post",
        "source": "tutorial_wayfarers_yard",
        "destination": "tutorial_family_post",
        "key": "north",
        "direction": "north",
        "label": "Family Post",
        "aliases": ["n", "family post", "post"],
    },
    {
        "id": "family_post_to_wayfarers_yard",
        "source": "tutorial_family_post",
        "destination": "tutorial_wayfarers_yard",
        "key": "south",
        "direction": "south",
        "label": "Wayfarer's Yard",
        "aliases": ["s", "yard", "wayfarers yard", "wayfarer's yard"],
    },
    {
        "id": "wayfarers_yard_to_sparring_ring",
        "source": "tutorial_wayfarers_yard",
        "destination": "tutorial_sparring_ring",
        "key": "west",
        "direction": "west",
        "label": "Sparring Ring",
        "aliases": ["w", "ring", "sparring ring"],
    },
    {
        "id": "sparring_ring_to_wayfarers_yard",
        "source": "tutorial_sparring_ring",
        "destination": "tutorial_wayfarers_yard",
        "key": "east",
        "direction": "east",
        "label": "Wayfarer's Yard",
        "aliases": ["e", "yard", "wayfarers yard", "wayfarer's yard"],
    },
    {
        "id": "sparring_ring_to_vermin_pens",
        "source": "tutorial_sparring_ring",
        "destination": "tutorial_vermin_pens",
        "key": "south",
        "direction": "south",
        "label": "Vermin Pens",
        "aliases": ["s", "pens", "vermin", "vermin pens"],
    },
    {
        "id": "vermin_pens_to_sparring_ring",
        "source": "tutorial_vermin_pens",
        "destination": "tutorial_sparring_ring",
        "key": "north",
        "direction": "north",
        "label": "Sparring Ring",
        "aliases": ["n", "ring", "sparring ring"],
    },
    {
        "id": "training_yard_to_mayors_hall",
        "source": "brambleford_training_yard",
        "destination": "brambleford_mayors_hall",
        "key": "west",
        "direction": "west",
        "label": "Mayor's Hall",
        "aliases": ["w", "hall", "mayor", "mayor's hall", "mayors hall"],
    },
    {
        "id": "mayors_hall_to_training_yard",
        "source": "brambleford_mayors_hall",
        "destination": "brambleford_training_yard",
        "key": "east",
        "direction": "east",
        "label": "Training Yard",
        "aliases": ["e", "yard", "training yard"],
    },
    {
        "id": "mayors_hall_to_chapel",
        "source": "brambleford_mayors_hall",
        "destination": "brambleford_chapel_dawn_bell",
        "key": "west",
        "direction": "west",
        "label": "Chapel of the Dawn Bell",
        "aliases": ["w", "chapel", "dawn bell", "chapel of the dawn bell"],
    },
    {
        "id": "chapel_to_mayors_hall",
        "source": "brambleford_chapel_dawn_bell",
        "destination": "brambleford_mayors_hall",
        "key": "east",
        "direction": "east",
        "label": "Mayor's Hall",
        "aliases": ["e", "hall", "mayor", "mayor's hall", "mayors hall"],
    },
    {
        "id": "chapel_to_outfitters",
        "source": "brambleford_chapel_dawn_bell",
        "destination": "brambleford_outfitters",
        "key": "south",
        "direction": "south",
        "label": "Brambleford Outfitters",
        "aliases": ["s", "outfitters", "shop", "brambleford outfitters"],
    },
    {
        "id": "training_yard_to_town_green",
        "source": "brambleford_training_yard",
        "destination": "brambleford_town_green",
        "key": "south",
        "direction": "south",
        "label": "Town Green",
        "aliases": ["s", "green", "town green"],
    },
    {
        "id": "town_green_to_east_gate",
        "source": "brambleford_town_green",
        "destination": "brambleford_east_gate",
        "key": "east",
        "direction": "east",
        "label": "East Gate",
        "aliases": ["e", "gate", "east gate"],
    },
    {
        "id": "town_green_to_wharf",
        "source": "brambleford_town_green",
        "destination": "brambleford_hobbyists_wharf",
        "key": "south",
        "direction": "south",
        "label": "Hobbyist's Wharf",
        "aliases": ["s", "wharf", "dock", "hobbyist's wharf", "hobbyists wharf"],
    },
    {
        "id": "town_green_to_observatory",
        "source": "brambleford_training_yard",
        "destination": "brambleford_great_observatory",
        "key": "east",
        "direction": "east",
        "label": "Great Observatory",
        "aliases": ["e", "observatory", "hill", "great observatory", "nexus hill"],
    },
    {
        "id": "east_gate_to_town_green",
        "source": "brambleford_east_gate",
        "destination": "brambleford_town_green",
        "key": "west",
        "direction": "west",
        "label": "Town Green",
        "aliases": ["w", "green", "town green"],
    },
    {
        "id": "observatory_to_town_green",
        "source": "brambleford_great_observatory",
        "destination": "brambleford_training_yard",
        "key": "west",
        "direction": "west",
        "label": "Training Yard",
        "aliases": ["w", "yard", "training yard", "downhill"],
    },
    {
        "id": "observatory_to_nexus_gate",
        "source": "brambleford_great_observatory",
        "destination": "brambleford_nexus_gate",
        "key": "east",
        "direction": "east",
        "label": "Nexus Gate",
        "aliases": ["e", "nexus", "gate", "ring", "nexus gate"],
    },
    {
        "id": "observatory_to_trophy_hall",
        "source": "brambleford_great_observatory",
        "destination": "brambleford_trophy_hall",
        "key": "north",
        "direction": "north",
        "label": "Trophy Hall",
        "aliases": ["n", "hall", "trophy hall", "gallery"],
    },
    {
        "id": "trophy_hall_to_observatory",
        "source": "brambleford_trophy_hall",
        "destination": "brambleford_great_observatory",
        "key": "south",
        "direction": "south",
        "label": "Great Observatory",
        "aliases": ["s", "observatory", "great observatory", "stairs"],
    },
    {
        "id": "nexus_gate_to_observatory",
        "source": "brambleford_nexus_gate",
        "destination": "brambleford_great_observatory",
        "key": "west",
        "direction": "west",
        "label": "Great Observatory",
        "aliases": ["w", "observatory", "stairs", "great observatory"],
    },
    {
        "id": "nexus_gate_to_junkyard",
        "source": "brambleford_nexus_gate",
        "destination": "junkyard_planet_landing_pad",
        "key": "east",
        "direction": "east",
        "label": "Junk-Yard Planet",
        "aliases": ["e", "junkyard", "planet", "junk-yard planet", "junk yard planet", "test gate"],
    },
    {
        "id": "junkyard_to_nexus_gate",
        "source": "junkyard_planet_landing_pad",
        "destination": "brambleford_nexus_gate",
        "key": "west",
        "direction": "west",
        "label": "Nexus Gate",
        "aliases": ["w", "return", "anchor", "gate", "home", "nexus", "nexus gate"],
    },
    {
        "id": "landing_to_scrapway",
        "source": "junkyard_planet_landing_pad",
        "destination": "junkyard_planet_scrapway",
        "key": "east",
        "direction": "east",
        "label": "Scrapway Verge",
        "aliases": ["e", "scrapway", "verge", "out"],
    },
    {
        "id": "scrapway_to_landing",
        "source": "junkyard_planet_scrapway",
        "destination": "junkyard_planet_landing_pad",
        "key": "west",
        "direction": "west",
        "label": "Junk-Yard Landing",
        "aliases": ["w", "landing", "return", "back", "junk-yard landing", "junk yard landing"],
    },
    {
        "id": "scrapway_to_relay_trench",
        "source": "junkyard_planet_scrapway",
        "destination": "junkyard_planet_relay_trench",
        "key": "north",
        "direction": "north",
        "label": "Relay Trench",
        "aliases": ["n", "relay", "trench", "relay trench"],
    },
    {
        "id": "relay_trench_to_scrapway",
        "source": "junkyard_planet_relay_trench",
        "destination": "junkyard_planet_scrapway",
        "key": "south",
        "direction": "south",
        "label": "Scrapway Verge",
        "aliases": ["s", "scrapway", "verge"],
    },
    {
        "id": "scrapway_to_crane_grave",
        "source": "junkyard_planet_scrapway",
        "destination": "junkyard_planet_crane_grave",
        "key": "east",
        "direction": "east",
        "label": "Crane Grave",
        "aliases": ["e", "crane", "grave", "crane grave"],
    },
    {
        "id": "crane_grave_to_scrapway",
        "source": "junkyard_planet_crane_grave",
        "destination": "junkyard_planet_scrapway",
        "key": "west",
        "direction": "west",
        "label": "Scrapway Verge",
        "aliases": ["w", "scrapway", "verge"],
    },
    {
        "id": "relay_trench_to_anchor_pit",
        "source": "junkyard_planet_relay_trench",
        "destination": "junkyard_planet_anchor_pit",
        "key": "east",
        "direction": "east",
        "label": "Anchor Pit",
        "aliases": ["e", "anchor", "pit", "anchor pit"],
    },
    {
        "id": "anchor_pit_to_relay_trench",
        "source": "junkyard_planet_anchor_pit",
        "destination": "junkyard_planet_relay_trench",
        "key": "west",
        "direction": "west",
        "label": "Relay Trench",
        "aliases": ["w", "relay", "trench", "relay trench"],
    },
    {
        "id": "crane_grave_to_anchor_pit",
        "source": "junkyard_planet_crane_grave",
        "destination": "junkyard_planet_anchor_pit",
        "key": "north",
        "direction": "north",
        "label": "Anchor Pit",
        "aliases": ["n", "anchor", "pit", "anchor pit"],
    },
    {
        "id": "anchor_pit_to_crane_grave",
        "source": "junkyard_planet_anchor_pit",
        "destination": "junkyard_planet_crane_grave",
        "key": "south",
        "direction": "south",
        "label": "Crane Grave",
        "aliases": ["s", "crane", "grave", "crane grave"],
    },
    {
        "id": "wharf_to_town_green",
        "source": "brambleford_hobbyists_wharf",
        "destination": "brambleford_town_green",
        "key": "north",
        "direction": "north",
        "label": "Town Green",
        "aliases": ["n", "green", "town green"],
    },
    {
        "id": "wharf_to_forge",
        "source": "brambleford_hobbyists_wharf",
        "destination": "brambleford_ironroot_forge",
        "key": "south",
        "direction": "south",
        "label": "Ironroot Forge",
        "aliases": ["s", "forge", "smithy", "ironroot forge"],
    },
    {
        "id": "forge_to_wharf",
        "source": "brambleford_ironroot_forge",
        "destination": "brambleford_hobbyists_wharf",
        "key": "north",
        "direction": "north",
        "label": "Hobbyist's Wharf",
        "aliases": ["n", "wharf", "dock", "hobbyist's wharf", "hobbyists wharf"],
    },
    {
        "id": "east_gate_to_trailhead",
        "source": "brambleford_east_gate",
        "destination": "goblin_road_trailhead",
        "key": "east",
        "direction": "east",
        "label": "Goblin Road Trailhead",
        "aliases": ["e", "road", "trailhead", "goblin road", "out"],
    },
    {
        "id": "east_gate_to_whispering_woods",
        "source": "brambleford_east_gate",
        "destination": "whispering_woods_trailhead",
        "key": "south",
        "direction": "south",
        "label": "Whispering Woods Trail",
        "aliases": ["s", "woods", "trail", "whispering woods", "whispering woods trail"],
    },
    {
        "id": "trailhead_to_east_gate",
        "source": "goblin_road_trailhead",
        "destination": "brambleford_east_gate",
        "key": "west",
        "direction": "west",
        "label": "East Gate",
        "aliases": ["w", "gate", "town", "east gate"],
    },
    {
        "id": "whispering_woods_to_east_gate",
        "source": "whispering_woods_trailhead",
        "destination": "brambleford_east_gate",
        "key": "north",
        "direction": "north",
        "label": "East Gate",
        "aliases": ["n", "gate", "town", "east gate"],
    },
    {
        "id": "trailhead_to_old_fence_line",
        "source": "goblin_road_trailhead",
        "destination": "goblin_road_old_fence_line",
        "key": "north",
        "direction": "north",
        "label": "Old Fence Line",
        "aliases": ["n", "fence", "old fence line"],
    },
    {
        "id": "old_fence_line_to_trailhead",
        "source": "goblin_road_old_fence_line",
        "destination": "goblin_road_trailhead",
        "key": "south",
        "direction": "south",
        "label": "Goblin Road Trailhead",
        "aliases": ["s", "trailhead", "goblin road", "goblin road trailhead"],
    },
    {
        "id": "old_fence_line_to_wolf_turn",
        "source": "goblin_road_old_fence_line",
        "destination": "goblin_road_wolf_turn",
        "key": "east",
        "direction": "east",
        "label": "Wolf Turn",
        "aliases": ["e", "turn", "wolf turn"],
    },
    {
        "id": "wolf_turn_to_old_fence_line",
        "source": "goblin_road_wolf_turn",
        "destination": "goblin_road_old_fence_line",
        "key": "west",
        "direction": "west",
        "label": "Old Fence Line",
        "aliases": ["w", "fence", "old fence line"],
    },
    {
        "id": "wolf_turn_to_fencebreaker_camp",
        "source": "goblin_road_wolf_turn",
        "destination": "goblin_road_fencebreaker_camp",
        "key": "east",
        "direction": "east",
        "label": "Fencebreaker Camp",
        "aliases": ["e", "camp", "fencebreaker camp"],
    },
    {
        "id": "fencebreaker_camp_to_wolf_turn",
        "source": "goblin_road_fencebreaker_camp",
        "destination": "goblin_road_wolf_turn",
        "key": "west",
        "direction": "west",
        "label": "Wolf Turn",
        "aliases": ["w", "turn", "wolf turn"],
    },
    {
        "id": "fencebreaker_camp_to_watchtower",
        "source": "goblin_road_fencebreaker_camp",
        "destination": "ruined_watchtower_approach",
        "key": "north",
        "direction": "north",
        "label": "Watchtower Approach",
        "aliases": ["n", "watchtower", "tower", "ruined watchtower", "approach"],
    },
    {
        "id": "watchtower_to_fencebreaker_camp",
        "source": "ruined_watchtower_approach",
        "destination": "goblin_road_fencebreaker_camp",
        "key": "south",
        "direction": "south",
        "label": "Fencebreaker Camp",
        "aliases": ["s", "camp", "fencebreaker camp", "goblin road"],
    },
    {
        "id": "fencebreaker_camp_to_blackfen",
        "source": "goblin_road_fencebreaker_camp",
        "destination": "blackfen_approach_fenreach_track",
        "key": "south",
        "direction": "south",
        "label": "Fenreach Track",
        "aliases": ["s", "blackfen", "fen", "track", "fenreach track"],
    },
    {
        "id": "blackfen_to_fencebreaker_camp",
        "source": "blackfen_approach_fenreach_track",
        "destination": "goblin_road_fencebreaker_camp",
        "key": "north",
        "direction": "north",
        "label": "Fencebreaker Camp",
        "aliases": ["n", "camp", "fencebreaker camp", "road"],
    },
    {
        "id": "watchtower_approach_to_breach_yard",
        "source": "ruined_watchtower_approach",
        "destination": "ruined_watchtower_breach_yard",
        "key": "north",
        "direction": "north",
        "label": "Breach Yard",
        "aliases": ["n", "yard", "breach", "breach yard"],
    },
    {
        "id": "breach_yard_to_watchtower_approach",
        "source": "ruined_watchtower_breach_yard",
        "destination": "ruined_watchtower_approach",
        "key": "south",
        "direction": "south",
        "label": "Watchtower Approach",
        "aliases": ["s", "approach", "watchtower approach"],
    },
    {
        "id": "breach_yard_to_archers_ledge",
        "source": "ruined_watchtower_breach_yard",
        "destination": "ruined_watchtower_archers_ledge",
        "key": "west",
        "direction": "west",
        "label": "Archer's Ledge",
        "aliases": ["w", "ledge", "archers ledge", "archer ledge"],
    },
    {
        "id": "archers_ledge_to_breach_yard",
        "source": "ruined_watchtower_archers_ledge",
        "destination": "ruined_watchtower_breach_yard",
        "key": "east",
        "direction": "east",
        "label": "Breach Yard",
        "aliases": ["e", "yard", "breach", "breach yard"],
    },
    {
        "id": "breach_yard_to_cracked_stairs",
        "source": "ruined_watchtower_breach_yard",
        "destination": "ruined_watchtower_cracked_stairs",
        "key": "east",
        "direction": "east",
        "label": "Cracked Tower Stairs",
        "aliases": ["e", "stairs", "tower stairs", "cracked tower stairs"],
    },
    {
        "id": "cracked_stairs_to_breach_yard",
        "source": "ruined_watchtower_cracked_stairs",
        "destination": "ruined_watchtower_breach_yard",
        "key": "west",
        "direction": "west",
        "label": "Breach Yard",
        "aliases": ["w", "yard", "breach", "breach yard"],
    },
    {
        "id": "cracked_stairs_to_blackreed_roost",
        "source": "ruined_watchtower_cracked_stairs",
        "destination": "ruined_watchtower_blackreed_roost",
        "key": "north",
        "direction": "north",
        "label": "Blackreed's Roost",
        "aliases": ["n", "roost", "blackreed", "blackreeds roost", "top"],
    },
    {
        "id": "blackreed_roost_to_cracked_stairs",
        "source": "ruined_watchtower_blackreed_roost",
        "destination": "ruined_watchtower_cracked_stairs",
        "key": "south",
        "direction": "south",
        "label": "Cracked Tower Stairs",
        "aliases": ["s", "stairs", "tower stairs", "cracked tower stairs"],
    },
    {
        "id": "fencebreaker_camp_to_sinkmouth_cut",
        "source": "goblin_road_fencebreaker_camp",
        "destination": "goblin_warrens_sinkmouth_cut",
        "key": "east",
        "direction": "east",
        "label": "Sinkmouth Cut",
        "aliases": ["e", "sinkmouth", "cut", "goblin warrens", "warrens"],
    },
    {
        "id": "sinkmouth_cut_to_fencebreaker_camp",
        "source": "goblin_warrens_sinkmouth_cut",
        "destination": "goblin_road_fencebreaker_camp",
        "key": "west",
        "direction": "west",
        "label": "Fencebreaker Camp",
        "aliases": ["w", "camp", "fencebreaker camp", "road"],
    },
    {
        "id": "sinkmouth_cut_to_torchgut_tunnel",
        "source": "goblin_warrens_sinkmouth_cut",
        "destination": "goblin_warrens_torchgut_tunnel",
        "key": "east",
        "direction": "east",
        "label": "Torchgut Tunnel",
        "aliases": ["e", "tunnel", "torchgut", "torchgut tunnel"],
    },
    {
        "id": "torchgut_tunnel_to_sinkmouth_cut",
        "source": "goblin_warrens_torchgut_tunnel",
        "destination": "goblin_warrens_sinkmouth_cut",
        "key": "west",
        "direction": "west",
        "label": "Sinkmouth Cut",
        "aliases": ["w", "sinkmouth", "cut", "sinkmouth cut"],
    },
    {
        "id": "torchgut_tunnel_to_bone_midden",
        "source": "goblin_warrens_torchgut_tunnel",
        "destination": "goblin_warrens_bone_midden",
        "key": "east",
        "direction": "east",
        "label": "Bone Midden",
        "aliases": ["e", "midden", "bone midden"],
    },
    {
        "id": "bone_midden_to_torchgut_tunnel",
        "source": "goblin_warrens_bone_midden",
        "destination": "goblin_warrens_torchgut_tunnel",
        "key": "west",
        "direction": "west",
        "label": "Torchgut Tunnel",
        "aliases": ["w", "tunnel", "torchgut", "torchgut tunnel"],
    },
    {
        "id": "torchgut_tunnel_to_sludge_run",
        "source": "goblin_warrens_torchgut_tunnel",
        "destination": "goblin_warrens_sludge_run",
        "key": "south",
        "direction": "south",
        "label": "Sludge Run",
        "aliases": ["s", "sludge", "run", "sludge run"],
    },
    {
        "id": "sludge_run_to_torchgut_tunnel",
        "source": "goblin_warrens_sludge_run",
        "destination": "goblin_warrens_torchgut_tunnel",
        "key": "north",
        "direction": "north",
        "label": "Torchgut Tunnel",
        "aliases": ["n", "tunnel", "torchgut", "torchgut tunnel"],
    },
    {
        "id": "sludge_run_to_feast_hall",
        "source": "goblin_warrens_sludge_run",
        "destination": "goblin_warrens_feast_hall",
        "key": "east",
        "direction": "east",
        "label": "Feast Hall",
        "aliases": ["e", "hall", "feast hall", "feast"],
    },
    {
        "id": "feast_hall_to_sludge_run",
        "source": "goblin_warrens_feast_hall",
        "destination": "goblin_warrens_sludge_run",
        "key": "west",
        "direction": "west",
        "label": "Sludge Run",
        "aliases": ["w", "sludge", "run", "sludge run"],
    },
    {
        "id": "bone_midden_to_feast_hall",
        "source": "goblin_warrens_bone_midden",
        "destination": "goblin_warrens_feast_hall",
        "key": "south",
        "direction": "south",
        "label": "Feast Hall",
        "aliases": ["s", "hall", "feast hall", "feast"],
    },
    {
        "id": "feast_hall_to_bone_midden",
        "source": "goblin_warrens_feast_hall",
        "destination": "goblin_warrens_bone_midden",
        "key": "north",
        "direction": "north",
        "label": "Bone Midden",
        "aliases": ["n", "midden", "bone midden"],
    },
    {
        "id": "feast_hall_to_pot_kings_court",
        "source": "goblin_warrens_feast_hall",
        "destination": "goblin_warrens_pot_kings_court",
        "key": "east",
        "direction": "east",
        "label": "Pot-King's Court",
        "aliases": ["e", "court", "pot king", "pot kings court", "throne"],
    },
    {
        "id": "pot_kings_court_to_feast_hall",
        "source": "goblin_warrens_pot_kings_court",
        "destination": "goblin_warrens_feast_hall",
        "key": "west",
        "direction": "west",
        "label": "Feast Hall",
        "aliases": ["w", "hall", "feast hall", "feast"],
    },
    {
        "id": "fenreach_track_to_reedflats",
        "source": "blackfen_approach_fenreach_track",
        "destination": "blackfen_approach_reedflats",
        "key": "east",
        "direction": "east",
        "label": "Reedflats",
        "aliases": ["e", "reedflats", "reeds", "flats"],
    },
    {
        "id": "reedflats_to_fenreach_track",
        "source": "blackfen_approach_reedflats",
        "destination": "blackfen_approach_fenreach_track",
        "key": "west",
        "direction": "west",
        "label": "Fenreach Track",
        "aliases": ["w", "track", "fenreach", "fenreach track"],
    },
    {
        "id": "reedflats_to_boglight_hollow",
        "source": "blackfen_approach_reedflats",
        "destination": "blackfen_approach_boglight_hollow",
        "key": "north",
        "direction": "north",
        "label": "Boglight Hollow",
        "aliases": ["n", "boglight", "hollow", "boglight hollow"],
    },
    {
        "id": "boglight_hollow_to_reedflats",
        "source": "blackfen_approach_boglight_hollow",
        "destination": "blackfen_approach_reedflats",
        "key": "south",
        "direction": "south",
        "label": "Reedflats",
        "aliases": ["s", "reedflats", "reeds", "flats"],
    },
    {
        "id": "reedflats_to_carrion_rise",
        "source": "blackfen_approach_reedflats",
        "destination": "blackfen_approach_carrion_rise",
        "key": "east",
        "direction": "east",
        "label": "Carrion Rise",
        "aliases": ["e", "rise", "carrion rise"],
    },
    {
        "id": "carrion_rise_to_reedflats",
        "source": "blackfen_approach_carrion_rise",
        "destination": "blackfen_approach_reedflats",
        "key": "west",
        "direction": "west",
        "label": "Reedflats",
        "aliases": ["w", "reedflats", "reeds", "flats"],
    },
    {
        "id": "boglight_hollow_to_miretooths_wallow",
        "source": "blackfen_approach_boglight_hollow",
        "destination": "blackfen_approach_miretooths_wallow",
        "key": "east",
        "direction": "east",
        "label": "Miretooth's Wallow",
        "aliases": ["e", "wallow", "miretooth", "miretooths wallow"],
    },
    {
        "id": "miretooths_wallow_to_boglight_hollow",
        "source": "blackfen_approach_miretooths_wallow",
        "destination": "blackfen_approach_boglight_hollow",
        "key": "west",
        "direction": "west",
        "label": "Boglight Hollow",
        "aliases": ["w", "boglight", "hollow", "boglight hollow"],
    },
    {
        "id": "carrion_rise_to_miretooths_wallow",
        "source": "blackfen_approach_carrion_rise",
        "destination": "blackfen_approach_miretooths_wallow",
        "key": "north",
        "direction": "north",
        "label": "Miretooth's Wallow",
        "aliases": ["n", "wallow", "miretooth", "miretooths wallow"],
    },
    {
        "id": "miretooths_wallow_to_carrion_rise",
        "source": "blackfen_approach_miretooths_wallow",
        "destination": "blackfen_approach_carrion_rise",
        "key": "south",
        "direction": "south",
        "label": "Carrion Rise",
        "aliases": ["s", "rise", "carrion rise"],
    },
    {
        "id": "miretooths_wallow_to_drowned_causeway",
        "source": "blackfen_approach_miretooths_wallow",
        "destination": "drowned_weir_drowned_causeway",
        "key": "east",
        "direction": "east",
        "label": "Drowned Causeway",
        "aliases": ["e", "causeway", "drowned causeway", "drowned weir", "weir"],
    },
    {
        "id": "drowned_causeway_to_miretooths_wallow",
        "source": "drowned_weir_drowned_causeway",
        "destination": "blackfen_approach_miretooths_wallow",
        "key": "west",
        "direction": "west",
        "label": "Miretooth's Wallow",
        "aliases": ["w", "wallow", "miretooth", "miretooths wallow", "blackfen"],
    },
    {
        "id": "drowned_causeway_to_lantern_weir",
        "source": "drowned_weir_drowned_causeway",
        "destination": "drowned_weir_lantern_weir",
        "key": "east",
        "direction": "east",
        "label": "Lantern Weir",
        "aliases": ["e", "weir", "lantern weir", "spillway"],
    },
    {
        "id": "lantern_weir_to_drowned_causeway",
        "source": "drowned_weir_lantern_weir",
        "destination": "drowned_weir_drowned_causeway",
        "key": "west",
        "direction": "west",
        "label": "Drowned Causeway",
        "aliases": ["w", "causeway", "drowned causeway"],
    },
    {
        "id": "lantern_weir_to_sluice_walk",
        "source": "drowned_weir_lantern_weir",
        "destination": "drowned_weir_sluice_walk",
        "key": "north",
        "direction": "north",
        "label": "Sluice Walk",
        "aliases": ["n", "sluice", "walk", "sluice walk"],
    },
    {
        "id": "sluice_walk_to_lantern_weir",
        "source": "drowned_weir_sluice_walk",
        "destination": "drowned_weir_lantern_weir",
        "key": "south",
        "direction": "south",
        "label": "Lantern Weir",
        "aliases": ["s", "weir", "lantern weir"],
    },
    {
        "id": "lantern_weir_to_sunken_lock",
        "source": "drowned_weir_lantern_weir",
        "destination": "drowned_weir_sunken_lock",
        "key": "east",
        "direction": "east",
        "label": "Sunken Lock",
        "aliases": ["e", "lock", "sunken lock"],
    },
    {
        "id": "sunken_lock_to_lantern_weir",
        "source": "drowned_weir_sunken_lock",
        "destination": "drowned_weir_lantern_weir",
        "key": "west",
        "direction": "west",
        "label": "Lantern Weir",
        "aliases": ["w", "weir", "lantern weir"],
    },
    {
        "id": "sluice_walk_to_blackwater_lamp_house",
        "source": "drowned_weir_sluice_walk",
        "destination": "drowned_weir_blackwater_lamp_house",
        "key": "east",
        "direction": "east",
        "label": "Blackwater Lamp House",
        "aliases": ["e", "lamp house", "lamp", "blackwater lamp house"],
    },
    {
        "id": "blackwater_lamp_house_to_sluice_walk",
        "source": "drowned_weir_blackwater_lamp_house",
        "destination": "drowned_weir_sluice_walk",
        "key": "west",
        "direction": "west",
        "label": "Sluice Walk",
        "aliases": ["w", "sluice", "walk", "sluice walk"],
    },
    {
        "id": "sunken_lock_to_blackwater_lamp_house",
        "source": "drowned_weir_sunken_lock",
        "destination": "drowned_weir_blackwater_lamp_house",
        "key": "north",
        "direction": "north",
        "label": "Blackwater Lamp House",
        "aliases": ["n", "lamp house", "lamp", "blackwater lamp house"],
    },
    {
        "id": "blackwater_lamp_house_to_sunken_lock",
        "source": "drowned_weir_blackwater_lamp_house",
        "destination": "drowned_weir_sunken_lock",
        "key": "south",
        "direction": "south",
        "label": "Sunken Lock",
        "aliases": ["s", "lock", "sunken lock"],
    },
    {
        "id": "woods_trail_to_old_stone_path",
        "source": "whispering_woods_trailhead",
        "destination": "whispering_woods_old_stone_path",
        "key": "east",
        "direction": "east",
        "label": "Old Stone Path",
        "aliases": ["e", "path", "old stone path"],
    },
    {
        "id": "old_stone_path_to_woods_trail",
        "source": "whispering_woods_old_stone_path",
        "destination": "whispering_woods_trailhead",
        "key": "west",
        "direction": "west",
        "label": "Whispering Woods Trail",
        "aliases": ["w", "trail", "whispering woods trail", "whispering woods"],
    },
    {
        "id": "old_stone_path_to_briar_glade",
        "source": "whispering_woods_old_stone_path",
        "destination": "whispering_woods_briar_glade",
        "key": "south",
        "direction": "south",
        "label": "Briar Glade",
        "aliases": ["s", "glade", "briar glade"],
    },
    {
        "id": "old_stone_path_to_old_barrow",
        "source": "whispering_woods_old_stone_path",
        "destination": "old_barrow_field_causeway",
        "key": "east",
        "direction": "east",
        "label": "Old Barrow Causeway",
        "aliases": ["e", "barrow", "causeway", "old barrow", "old barrow causeway"],
    },
    {
        "id": "old_barrow_to_old_stone_path",
        "source": "old_barrow_field_causeway",
        "destination": "whispering_woods_old_stone_path",
        "key": "west",
        "direction": "west",
        "label": "Old Stone Path",
        "aliases": ["w", "path", "woods", "old stone path", "whispering woods"],
    },
    {
        "id": "old_barrow_causeway_to_marker_row",
        "source": "old_barrow_field_causeway",
        "destination": "old_barrow_field_marker_row",
        "key": "east",
        "direction": "east",
        "label": "Marker Row",
        "aliases": ["e", "markers", "marker row"],
    },
    {
        "id": "marker_row_to_old_barrow_causeway",
        "source": "old_barrow_field_marker_row",
        "destination": "old_barrow_field_causeway",
        "key": "west",
        "direction": "west",
        "label": "Old Barrow Causeway",
        "aliases": ["w", "causeway", "old barrow causeway", "old barrow"],
    },
    {
        "id": "marker_row_to_barrow_circle",
        "source": "old_barrow_field_marker_row",
        "destination": "old_barrow_field_barrow_circle",
        "key": "north",
        "direction": "north",
        "label": "Barrow Circle",
        "aliases": ["n", "circle", "barrow circle"],
    },
    {
        "id": "barrow_circle_to_marker_row",
        "source": "old_barrow_field_barrow_circle",
        "destination": "old_barrow_field_marker_row",
        "key": "south",
        "direction": "south",
        "label": "Marker Row",
        "aliases": ["s", "markers", "marker row"],
    },
    {
        "id": "barrow_circle_to_sunken_dais",
        "source": "old_barrow_field_barrow_circle",
        "destination": "old_barrow_field_sunken_dais",
        "key": "east",
        "direction": "east",
        "label": "Sunken Dais",
        "aliases": ["e", "dais", "sunken dais"],
    },
    {
        "id": "sunken_dais_to_barrow_circle",
        "source": "old_barrow_field_sunken_dais",
        "destination": "old_barrow_field_barrow_circle",
        "key": "west",
        "direction": "west",
        "label": "Barrow Circle",
        "aliases": ["w", "circle", "barrow circle"],
    },
    {
        "id": "briar_glade_to_old_stone_path",
        "source": "whispering_woods_briar_glade",
        "destination": "whispering_woods_old_stone_path",
        "key": "north",
        "direction": "north",
        "label": "Old Stone Path",
        "aliases": ["n", "path", "old stone path"],
    },
    {
        "id": "briar_glade_to_greymaw_hollow",
        "source": "whispering_woods_briar_glade",
        "destination": "whispering_woods_greymaw_hollow",
        "key": "east",
        "direction": "east",
        "label": "Greymaw's Hollow",
        "aliases": ["e", "hollow", "den", "greymaw's hollow", "greymaws hollow"],
    },
    {
        "id": "greymaw_hollow_to_briar_glade",
        "source": "whispering_woods_greymaw_hollow",
        "destination": "whispering_woods_briar_glade",
        "key": "west",
        "direction": "west",
        "label": "Briar Glade",
        "aliases": ["w", "glade", "briar glade"],
    },
]

WORLD_OBJECTS = [
    {
        "id": "town_notice_board",
        "key": "town notice board",
        "aliases": ["board", "notice board", "notices"],
        "kind": "readable",
        "location": "brambleford_town_green",
        "desc": (
            "Pinned notices mention goblin-cut fences, missing flour, and wolves too bold for comfort. "
            "The notes are practical rather than dramatic, which somehow makes them more convincing."
        ),
    },
    {
        "id": "captain_harl_rowan",
        "key": "Captain Harl Rowan",
        "aliases": ["captain", "harl", "rowan"],
        "kind": "npc",
        "location": "brambleford_training_yard",
        "desc": (
            "The old militia captain watches everything with the calm patience of a man who has seen "
            "too many panicked recruits and intends to keep you alive through sheer refusal."
        ),
    },
    {
        "id": "sergeant_tamsin_vale",
        "key": "Sergeant Tamsin Vale",
        "aliases": ["tamsin", "sergeant", "vale"],
        "kind": "npc",
        "location": "tutorial_wayfarers_yard",
        "desc": (
            "Sergeant Tamsin stands like someone who has spent years turning frightened travelers into steadier versions of themselves. "
            "Her voice looks ready to be blunt, but not unkind."
        ),
    },
    {
        "id": "quartermaster_nella_cobb",
        "key": "Quartermaster Nella Cobb",
        "aliases": ["nella", "quartermaster", "cobb"],
        "kind": "npc",
        "location": "tutorial_quartermaster_shed",
        "desc": (
            "Nella looks like a woman who could judge a traveler's preparedness from twenty paces and improve it from ten. "
            "Her hands never stop finding straps to straighten or bundles to square."
        ),
    },
    {
        "id": "tutorial_supply_board",
        "key": "supply board",
        "aliases": ["board", "supply board", "chalk board", "chalkboard"],
        "kind": "readable",
        "location": "tutorial_quartermaster_shed",
        "desc": (
            "A square slate board hangs beside the crate stacks, its lettering neat enough to suggest that sloppy people are corrected here as quickly as sloppy packs."
        ),
    },
    {
        "id": "courier_peep_marrow",
        "key": "Courier Peep Marrow",
        "aliases": ["peep", "courier", "marrow"],
        "kind": "npc",
        "location": "tutorial_family_post",
        "desc": (
            "Peep has chalk on one sleeve, route twine around one wrist, and the sort of quick expression that suggests he is always halfway through three errands at once."
        ),
    },
    {
        "id": "family_post_sign",
        "key": "family post sign",
        "aliases": ["sign", "post sign", "family sign"],
        "kind": "readable",
        "location": "tutorial_family_post",
        "desc": (
            "A weatherproof sign hangs beside the route pegs, written in the thick practical strokes of someone tired of people getting separated in avoidable ways."
        ),
    },
    {
        "id": "ringhand_brask",
        "key": "Ringhand Brask",
        "aliases": ["brask", "ringhand"],
        "kind": "npc",
        "location": "tutorial_sparring_ring",
        "desc": (
            "Brask leans on the rail like a man who has watched enough bad first fights to know exactly when to bark and when to let a lesson land on its own."
        ),
    },
    {
        "id": "mayor_elric_thorne",
        "key": "Mayor Elric Thorne",
        "aliases": ["mayor", "elric", "thorne"],
        "kind": "npc",
        "location": "brambleford_mayors_hall",
        "desc": (
            "Mayor Elric looks like a man held together by lists, weather reports, and a refusal to waste words. "
            "He carries the town's worry with practiced economy."
        ),
    },
    {
        "id": "brother_alden",
        "key": "Brother Alden",
        "aliases": ["alden", "brother", "acolyte"],
        "kind": "npc",
        "location": "brambleford_chapel_dawn_bell",
        "desc": (
            "Brother Alden has the look of an earnest assistant cleric who keeps doing brave things only after he has "
            "finished being nervous about them."
        ),
    },
    {
        "id": "uncle_pib_underbough",
        "key": "Uncle Pib Underbough",
        "aliases": ["uncle pib", "pib", "innkeeper"],
        "kind": "npc",
        "location": "brambleford_lantern_rest_inn",
        "desc": (
            "Uncle Pib moves between kettles and tables with practiced ease. He looks like the sort of "
            "man who could solve a crisis with a ladle, a joke, or both."
        ),
    },
    {
        "id": "leda_thornwick",
        "key": "Leda Thornwick",
        "aliases": ["leda", "thornwick", "outfitter", "shopkeeper"],
        "kind": "npc",
        "location": "brambleford_outfitters",
        "desc": (
            "Leda has measuring cord around one wrist, chalk on one sleeve, and the sharp practical eyes of someone "
            "who can tell whether a pair of boots will fail before the road does."
        ),
    },
    {
        "id": "great_catch_log",
        "key": "Great Catch Log",
        "aliases": ["catch log", "log", "ledger", "record book"],
        "kind": "readable",
        "location": "brambleford_lantern_rest_inn",
        "desc": (
            "A stout ledger sits open on a little stand near the hearth, its pages full of proud fish "
            "weights, terrible handwriting, and at least one sketch of a trout wearing a crown."
        ),
    },
    {
        "id": "kitchen_hearth",
        "key": "kitchen hearth",
        "aliases": ["hearth", "firepot", "cookfire", "stove"],
        "kind": "readable",
        "location": "brambleford_lantern_rest_inn",
        "desc": (
            "A broad iron hearth glows behind the common room, fitted with blackened pans and an old "
            "firepot Uncle Pib swears can rescue almost any meal from bad judgment."
        ),
    },
    {
        "id": "lantern_rest_arcade_cabinet",
        "key": "Joss's Arcade Cabinet",
        "display_name": "Joss's Arcade Cabinet",
        "aliases": [
            "cabinet",
            "arcade cabinet",
            "arcade",
            "machine",
            "flashing cabinet",
            "game cabinet",
            "joss's flashing cabinet",
            "joss flashing cabinet",
        ],
        "kind": "arcade",
        "typeclass": "typeclasses.objects.ArcadeCabinet",
        "location": "brambleford_lantern_rest_inn",
        "arcade_games": ["maze_runner"],
        "arcade_price": 1,
        "arcade_rewards": {
            "maze_runner": {"threshold": 2000, "item": "lantern_pixel_pin"},
        },
        "desc": (
            "A humming black-glass arcade cabinet squats near the inn wall, all bright dots, sharp corners, and a speaker "
            "that crackles like a tiny storm. A painted card reads MAZE RUNNER. Beneath it, somebody has added in "
            "grease pencil: Beat 2,000 and Joss owes you a proper prize."
        ),
    },
    {
        "id": "outfitters_chalkboard",
        "key": "outfitters chalkboard",
        "aliases": ["chalkboard", "price board", "sale board", "board"],
        "kind": "readable",
        "location": "brambleford_outfitters",
        "desc": (
            "A chalkboard near the counter lists current trade notes, repair promises, and a large underlined reminder "
            "that muddy boots cost extra if they are set on the display rugs."
        ),
    },
    {
        "id": "cellar_warning_slate",
        "key": "cellar warning slate",
        "aliases": ["slate", "warning slate", "chalk slate"],
        "kind": "readable",
        "location": "brambleford_rat_and_kettle_cellar",
        "desc": (
            "A slate has been nailed to a post beside the stair, listing inventory losses, rude sketches of "
            "rats, and a fresh line from Uncle Pib promising soup to anyone who clears the place out."
        ),
    },
    {
        "id": "sister_maybelle",
        "key": "Sister Maybelle",
        "aliases": ["maybelle", "sister", "healer"],
        "kind": "npc",
        "location": "brambleford_lantern_rest_inn",
        "desc": (
            "Sister Maybelle keeps a satchel of herbs, bandages, and dried roots within easy reach. "
            "She looks soft-spoken until someone mentions preventable injury."
        ),
    },
    {
        "id": "mira_fenleaf",
        "key": "Mira Fenleaf",
        "aliases": ["mira", "fenleaf", "hunter"],
        "kind": "npc",
        "location": "brambleford_east_gate",
        "desc": (
            "Mira studies the road with a hunter's stillness. She has the look of someone who notices "
            "every broken branch and trusts almost none of them."
        ),
    },
    {
        "id": "loaner_pole_rack",
        "key": "loaner pole rack",
        "aliases": ["pole rack", "poles", "rack", "rods"],
        "kind": "readable",
        "location": "brambleford_hobbyists_wharf",
        "desc": (
            "A simple rack holds town-owned poles, patched line, and a note reminding everyone that lost "
            "hooks still count as debt even when the river clearly started it."
        ),
    },
    {
        "id": "torren_ironroot",
        "key": "Torren Ironroot",
        "aliases": ["torren", "ironroot", "smith", "blacksmith"],
        "kind": "npc",
        "location": "brambleford_ironroot_forge",
        "desc": (
            "Torren is a broad-shouldered dwarf with soot in his beard, forearms like split oak, and the calm expression of a "
            "man who has already decided whether your gear deserves saving."
        ),
    },
    {
        "id": "forge_order_board",
        "key": "forge order board",
        "aliases": ["order board", "forge board", "orders", "board"],
        "kind": "readable",
        "location": "brambleford_ironroot_forge",
        "desc": (
            "A broad slate board hangs beside the workbench, listing nail orders, hinge repairs, and a smaller section marked "
            "'field kit improvements' in blocky chalk."
        ),
    },
    {
        "id": "joss_veller",
        "key": "Joss Veller",
        "aliases": ["joss", "veller", "lamplighter"],
        "kind": "npc",
        "location": "brambleford_great_observatory",
        "desc": (
            "Joss wears a lamplighter's coat patched with brass tabs, soot marks, and tools that definitely do "
            "not belong on an ordinary ladder. He watches the telescope and the lower chamber with the look of "
            "someone quietly keeping two kinds of town lit at once."
        ),
    },
    {
        "id": "star_lens",
        "key": "star lens",
        "aliases": ["lens", "telescope", "great lens"],
        "kind": "readable",
        "location": "brambleford_great_observatory",
        "desc": (
            "The observatory's great lens turns with an almost living smoothness. Constellations are etched "
            "along its brass rings beside stranger marks that look more like routes than stars."
        ),
    },
    {
        "id": "mayors_ledger",
        "key": "mayor's ledger",
        "aliases": ["ledger", "civic ledger", "petition book"],
        "kind": "readable",
        "location": "brambleford_mayors_hall",
        "desc": (
            "A wide ledger lies open to a page of fence repairs, flour shortages, dim lantern reports, and a fresh line "
            "underlined twice: BARROW LIGHTS FAILING AFTER DUSK."
        ),
    },
    {
        "id": "dawn_bell",
        "key": "dawn bell",
        "aliases": ["bell", "chapel bell", "brass bell"],
        "kind": "readable",
        "location": "brambleford_chapel_dawn_bell",
        "desc": (
            "The bell hangs above the little altar in a brass frame polished by careful hands. Its tone is meant to greet "
            "the morning, though right now it feels more like a promise against the dark."
        ),
    },
    {
        "id": "trophy_vitrine",
        "key": "family trophy vitrine",
        "aliases": ["vitrine", "trophies", "trophy case", "display"],
        "kind": "readable",
        "location": "brambleford_trophy_hall",
        "desc": (
            "Glass-fronted cases and labeled plinths wait for proof that Brambleford's little family can come back "
            "from strange places carrying stranger victories."
        ),
    },
    {
        "id": "nexus_gate_plaque",
        "key": "nexus gate plaque",
        "aliases": ["plaque", "gate plaque", "brass plaque", "gates"],
        "kind": "readable",
        "location": "brambleford_nexus_gate",
        "desc": (
            "A polished brass plaque is riveted into the gate dais, each portal name engraved beside a thin "
            "glass strip that glows or stays dark depending on the gate's condition."
        ),
    },
    {
        "id": "salvage_beacon",
        "key": "salvage beacon",
        "aliases": ["beacon", "signal", "tower"],
        "kind": "readable",
        "location": "junkyard_planet_landing_pad",
        "desc": (
            "A waist-high beacon blinks in clipped pulses through the scrap haze, anchoring the return gate to "
            "something on this world that still remembers how to answer."
        ),
    },
    {
        "id": "relay_route_mast",
        "key": "relay route mast",
        "aliases": ["mast", "relay mast", "route mast"],
        "kind": "readable",
        "location": "junkyard_planet_relay_trench",
        "desc": (
            "A metal mast rises from the trench with route glass still threaded through its ribs. Static ticks across "
            "it like rain on wire."
        ),
    },
    {
        "id": "crane_gantry",
        "key": "collapsed crane gantry",
        "aliases": ["gantry", "crane gantry", "crane"],
        "kind": "readable",
        "location": "junkyard_planet_crane_grave",
        "desc": (
            "The gantry lies folded across the yard, cab glass burst outward and old work orders sealed under layers "
            "of rust dust and magnet grit."
        ),
    },
    {
        "id": "barrow_marker_stone",
        "key": "weathered marker stone",
        "aliases": ["marker stone", "marker", "stone"],
        "kind": "readable",
        "location": "old_barrow_field_marker_row",
        "desc": (
            "A lichen-streaked stone lists half-legible names beneath a carved sunburst. The oldest letters have been "
            "scratched at from the inside rather than worn away from weather."
        ),
    },
    {
        "id": "edrics_slab",
        "key": "Edric's slab",
        "aliases": ["slab", "knight slab", "edric", "sir edric"],
        "kind": "readable",
        "location": "old_barrow_field_sunken_dais",
        "desc": (
            "The carved slab shows a knight at prayer beneath a rising sun, though the stone around the hands is worn "
            "smooth as if someone has gripped it many times after burial."
        ),
    },
    {
        "id": "watchtower_warning_post",
        "key": "watchtower warning post",
        "aliases": ["warning post", "post", "stake"],
        "kind": "readable",
        "location": "ruined_watchtower_approach",
        "desc": (
            "An old militia warning post leans beside the climb, the original carving half-cut away by newer knife marks and weather."
        ),
    },
    {
        "id": "signal_brazier",
        "key": "signal brazier",
        "aliases": ["brazier", "signal fire", "watchfire"],
        "kind": "readable",
        "location": "ruined_watchtower_breach_yard",
        "desc": (
            "A broad iron brazier sits in the broken yard with fresh soot in it and a rack of damp kindling stacked close at hand."
        ),
    },
    {
        "id": "blackreed_standard",
        "key": "Blackreed standard",
        "aliases": ["standard", "banner", "flag", "blackreed banner"],
        "kind": "readable",
        "location": "ruined_watchtower_blackreed_roost",
        "desc": (
            "A dark standard whips from an iron hook at the tower crown, its cloth patched but carefully kept so the symbol still reads at distance."
        ),
    },
    {
        "id": "sinkmouth_scratch_map",
        "key": "scratch-map slate",
        "aliases": ["slate", "map", "scratch map", "scratch-map"],
        "kind": "readable",
        "location": "goblin_warrens_sinkmouth_cut",
        "desc": (
            "A broken roofing slate has been scratched over with goblin route marks, stew counts, and a crude crown symbol deeper in the hill."
        ),
    },
    {
        "id": "midden_bone_totem",
        "key": "midden bone totem",
        "aliases": ["totem", "bone totem", "idol"],
        "kind": "readable",
        "location": "goblin_warrens_bone_midden",
        "desc": (
            "Ribs, jawbones, and bent cutlery have been wired into a hanging goblin totem with a pot lid nailed where a face ought to be."
        ),
    },
    {
        "id": "feast_hall_cauldron",
        "key": "blackiron cauldron",
        "aliases": ["cauldron", "pot", "stew pot", "blackiron cauldron"],
        "kind": "readable",
        "location": "goblin_warrens_feast_hall",
        "desc": (
            "A blackened cauldron bubbles over a trench fire, full of something too thick to slosh cleanly and too busy to welcome questions."
        ),
    },
    {
        "id": "potking_lid_throne",
        "key": "lid-throne",
        "aliases": ["throne", "lid throne", "seat", "crown seat"],
        "kind": "readable",
        "location": "goblin_warrens_pot_kings_court",
        "desc": (
            "The court seat is a rough-backed stone chair plated in bent lid metal, split shields, and enough grease-dark polish to suggest regular use by something proud and disgusting."
        ),
    },
    {
        "id": "fenreach_waypost",
        "key": "fenreach waypost",
        "aliases": ["waypost", "post", "fen post", "trail post"],
        "kind": "readable",
        "location": "blackfen_approach_fenreach_track",
        "desc": (
            "A half-sunk road post leans over the wet track, its old route marks mostly hidden beneath reed scratches and a newer charcoal warning."
        ),
    },
    {
        "id": "boglight_lantern",
        "key": "boglight lantern",
        "aliases": ["lantern", "bog lantern", "fen lantern"],
        "kind": "readable",
        "location": "blackfen_approach_boglight_hollow",
        "desc": (
            "A drowned lantern cage hangs from a bent willow root above the hollow, green glass panes clouded from the inside as if the light went bad before it went out."
        ),
    },
    {
        "id": "carrion_stake_circle",
        "key": "carrion stake circle",
        "aliases": ["stakes", "stake circle", "circle"],
        "kind": "readable",
        "location": "blackfen_approach_carrion_rise",
        "desc": (
            "Old watch stakes and bird bones have been driven into the mudbank in a rough circle, less a defense than a record of how many times the marsh has already ignored warnings."
        ),
    },
    {
        "id": "miretooth_shed_skull",
        "key": "shed marsh skull",
        "aliases": ["skull", "marsh skull", "shed skull"],
        "kind": "readable",
        "location": "blackfen_approach_miretooths_wallow",
        "desc": (
            "A half-sunk skull lies near the black pool, too broad through the jaw to belong to any hound Brambleford would call normal."
        ),
    },
    {
        "id": "drowned_survey_marker",
        "key": "drowned survey marker",
        "aliases": ["marker", "survey marker", "stake"],
        "kind": "readable",
        "location": "drowned_weir_drowned_causeway",
        "desc": (
            "A stone survey marker leans out of the black water with old civic cuts still visible beneath layers of silt and marsh rot."
        ),
    },
    {
        "id": "weir_keepers_plaque",
        "key": "weir-keeper's plaque",
        "aliases": ["plaque", "weir plaque", "keepers plaque", "keeper's plaque"],
        "kind": "readable",
        "location": "drowned_weir_lantern_weir",
        "desc": (
            "A brass plaque hangs crooked on the drowned ironwork, greened by bad water and lit from below by a line of light that should not still be in service."
        ),
    },
    {
        "id": "sunken_lock_chain",
        "key": "sunken lock chain",
        "aliases": ["chain", "lock chain", "gate chain"],
        "kind": "readable",
        "location": "drowned_weir_sunken_lock",
        "desc": (
            "A gate chain the thickness of a forearm runs from the drowned lock wall into black water below, drawn tight enough to hum when the wrong light pulses through the chamber."
        ),
    },
    {
        "id": "blackwater_lens_frame",
        "key": "blackwater lens frame",
        "aliases": ["lens", "lens frame", "lamp lens", "frame"],
        "kind": "readable",
        "location": "drowned_weir_blackwater_lamp_house",
        "desc": (
            "A broken lamp lens frame stands around the cold white heart of the room, its brass ribs warped as if the light inside learned to lean back."
        ),
    },
    {
        "id": "ruks_chopping_block",
        "key": "Ruk's chopping block",
        "aliases": ["block", "chopping block", "ruks block"],
        "kind": "readable",
        "location": "goblin_road_fencebreaker_camp",
        "desc": (
            "A hacked-up stump serves as a work block for ruined fence rails. Deep blade scores suggest "
            "whoever uses it values force over craft."
        ),
    },
    {
        "id": "woods_wardstone",
        "key": "old wardstone",
        "aliases": ["wardstone", "stone", "waystone"],
        "kind": "readable",
        "location": "whispering_woods_trailhead",
        "desc": (
            "A weathered standing stone has been ringed with old wax and newer chalk marks. Someone has "
            "been trying to keep the woods civil with whatever protection they still remember."
        ),
    },
    {
        "id": "hunters_warning_post",
        "key": "hunter's warning post",
        "aliases": ["post", "warning", "warning post", "stake"],
        "kind": "readable",
        "location": "whispering_woods_old_stone_path",
        "desc": (
            "A split cedar post has been driven into the earth beside the stones. Knife-scored marks "
            "and a strip of grey fur hang from it as a warning to anyone pressing deeper."
        ),
    },
]
