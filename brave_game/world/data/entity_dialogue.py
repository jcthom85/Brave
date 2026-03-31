"""Data-driven NPC and readable text for Brave interactions."""


def _rule(text, **conditions):
    rule = {"text": text}
    for key, value in conditions.items():
        if value is not None:
            rule[key] = value
    return rule


TALK_RULES = {
    "captain_harl_rowan": [
        _rule(
            "Then this one is about finishing the line, not scouting it. Joss has the drowned works in his head better than I do, but if that lamp thing starts leaning on lesser bodies, clear those first and break its footing before you try to end the room.",
            active="the_hollow_lantern",
        ),
        _rule(
            "Good. Short route, bad footing, wrong light. That's a capstone if I've ever heard one. Clear the drowned lock crews, keep the party inside shouting distance, and don't let the place split you for the sake of one clever angle.",
            active="locks_under_blackwater",
        ),
        _rule(
            "Miretooth was teeth. If Joss says the south light itself is wrong, believe the part where the problem got less animal and more deliberate. Hit the weir cleanly and report back with something final.",
            active="the_south_light",
        ),
        _rule(
            "Good. First real work stays inside town walls. Head south, read the board if you like things written twice, then go west to the inn and talk to Uncle Pib. Clear his cellar before you go looking for a grander kind of trouble.",
            active="rats_in_the_kettle",
        ),
        _rule(
            "Then end it. If Mira says the fen beast has started treating the marsh like a border, believe her. Hit hard, stay together, and don't chase anything that disappears into reeds unless the whole party means it.",
            active="miretooths_claim",
        ),
        _rule(
            "Good. The south fen path is real trouble, not rumor. Chart the rise, thin whatever's hunting that marsh edge, and come back with a cleaner count than the crows would leave.",
            active="lights_in_the_reeds",
        ),
        _rule(
            "South of the old camp the ground turns into bad marsh and worse visibility. Get eyes on it for Mira and don't let the first quiet stretch convince you the fen's empty.",
            active="bogwater_rumors",
        ),
        _rule(
            "Then finish the warrens cleanly. The feast hall is where goblins get loud, but the crown room beyond it is where Grubnak keeps their nerve from leaking out. Hit the court hard and don't give his helpers time to turn the cave into a dogpile.",
            active="the_pot_kings_feast",
        ),
        _rule(
            "The road problem wasn't just bandits. The goblins have a whole filth hole under Ruk's old camp. Thin the warrens crews before they remember how close Brambleford sits.",
            active="gutters_and_hexes",
        ),
        _rule(
            "Blackreed's papers and Mira's tracks point to a sink cut east of the old camp. Find it, get eyes on how deep the warrens run, and don't let the first tunnel fool you into thinking the goblins are disorganized down there.",
            active="below_the_fencebreakers",
        ),
        _rule(
            "Blackreed wins by seeing weakness before decent folk do. Take the climb, clear the line around him, and don't let him pick off whoever looks closest to folding.",
            active="captain_varn_blackreed",
        ),
        _rule(
            "The ledge and the stairs are the real fight. Push north from Ruk's old camp, clear the archers first if they start ruling the pace, and don't let the hounds split the party.",
            active="loose_arrows",
        ),
        _rule(
            "The old tower sits north of Fencebreaker Camp. Get eyes on the approach and the breach yard, then come back if you somehow discover they are polite visitors.",
            active="smoke_on_the_ridge",
        ),
        _rule(
            "There you are. Before you run after trouble, settle your build with `race` and `class`, then check `sheet` and `gear`. Once you have your feet under you, the inn has the first honest job waiting.",
            active="practice_makes_heroes",
        ),
        _rule(
            "Ruk is the sort of brute who punishes anyone foolish enough to face him alone. Use `party invite <name>` if you need to gather the family, then hit him together.",
            active="ruk_the_fence_cutter",
            completed="fencebreakers",
        ),
        _rule(
            "Town's done teaching you what it can. Head east, keep the party together, and use `map` if you want the local layout before you push farther out.",
            active="roadside_howls",
        ),
        _rule(
            "If the goblins are still at the fences, press to the Old Fence Line and Wolf Turn. A farmer with walls beats a hero with a pretty story.",
            active="fencebreakers",
        ),
        _rule(
            "That's a chapter's worth of trouble dealt with. Goblins, graves, ridge crews, warrens, fen, and now the wrong south light itself. Good. Let the town breathe a little before we decide what deserves the next hard answer.",
            completed="the_hollow_lantern",
        ),
        _rule(
            "You look steadier now. Let the toughest one take the first hit, let the sharpest one pick the target, and come back alive enough for supper."
        ),
    ],
    "uncle_pib_underbough": [
        _rule(
            "If you're looking for work that smells worse but hurts less than Goblin Road, head west into the inn and then `down` to the cellar. Clear it out with `fight`, then come back upstairs once the scratching stops.",
            active="rats_in_the_kettle",
        ),
        _rule(
            "Good. The cellar's fit for flour again. If you want your next bruise outdoors, Mira's waiting at the East Gate. Check `quests` if you want the road written plain before you go.",
            active="roadside_howls",
        ),
        _rule(
            "You look chewed on. Sit down, eat something warm, and `rest` before you volunteer for another heroic misunderstanding.",
            resource_below_max="hp",
        ),
        _rule(
            "First days are for getting your bearings. If the town feels wide, check `quests`. If the road feels wider, come back here and `rest`. If you want something calmer, the wharf south of the green is open and the hearth here will take anything decent you catch.",
            xp_eq=0,
        ),
        _rule(
            "If the road has had enough of you for one evening, `cook` something honest and `eat` before you head back out. The Great Catch Log's right here too, if you feel like proving the river wrong.",
            room_id="brambleford_lantern_rest_inn",
        ),
        _rule(
            "The inn's still safe ground. Patch up here, empty your `pack` if it rattles too much, then go bother something meaner than you. Or don't. Some evenings are for the wharf and supper."
        ),
    ],
    "mira_fenleaf": [
        _rule(
            "The drowned lamp house sits beyond the lock line at the far east of the weir. If the light shields itself with lesser things, cut them down first. What followed Miretooth this far isn't an animal anymore.",
            active="the_hollow_lantern",
        ),
        _rule(
            "The Sluice Walk and the Sunken Lock are the heart of it. Clear enough of the drowned crews that the lamp house has to show itself properly, then finish the climb with the whole party still breathing.",
            active="locks_under_blackwater",
        ),
        _rule(
            "Miretooth was guarding the edge, not causing it. Joss says the wrong light east of the wallow belongs to an old drowned weir. Go through the causeway and the lamp line and see what still thinks it has authority out there.",
            active="the_south_light",
        ),
        _rule(
            "Miretooth holds the far wallow where the water goes black and the reeds stop moving like wind. If he vanishes, don't spread out. He comes back for whoever looks easiest to finish.",
            active="miretooths_claim",
        ),
        _rule(
            "Push through the Reedflats and Carrion Rise. Kill enough Blackfen things that the trail stops feeling measured, and keep an eye on the bog lights. The wrong ones drift against the wind.",
            active="lights_in_the_reeds",
        ),
        _rule(
            "South of Fencebreaker Camp the ground turns mean and wet fast. Take the Fenreach Track, then work east until you hit the hollow with the bad lights. That's where the marsh starts admitting what lives in it.",
            active="bogwater_rumors",
        ),
        _rule(
            "Grubnak sits east of the Feast Hall in the court he built out of lids, shields, and stolen road junk. Expect brutes first, hexers second, and a king mean enough to treat supper like strategy.",
            active="the_pot_kings_feast",
        ),
        _rule(
            "Don't just sprint the warrens. Hit the Sludge Run, the midden, and the hall hard enough that the hexers stop sending anything organized back toward the road.",
            active="gutters_and_hexes",
        ),
        _rule(
            "East of Ruk's old camp the hill breaks open into a goblin sink cut. Take that breach, follow the smoke into the Torchgut tunnel, and see how far the road-cutters really run below us.",
            active="below_the_fencebreakers",
        ),
        _rule(
            "Ruk's old camp is just the gate now. Push east along Goblin Road, north at the camp, then keep the tower wall on your left until you reach Blackreed's perch. If anyone looks shaky, he'll see it before you do.",
            active="captain_varn_blackreed",
        ),
        _rule(
            "Bandits took the old ridge tower while everyone watched the woods and barrows. Go east from here, keep to Goblin Road until Fencebreaker Camp, then head north into the climb.",
            active_any=("loose_arrows", "smoke_on_the_ridge"),
        ),
        _rule(
            "The west side's the trouble now. Follow the old stone path through the woods until it opens onto the barrow causeway. If the dead are already walking, don't stand where the crows can measure you.",
            active_any=("lanterns_at_dusk", "do_not_disturb_the_dead"),
        ),
        _rule(
            "Edric's dais sits past the barrow circle. If the chapel's right and he's wrapped in grave-light, cut down whatever answers his call before you try to finish him.",
            active="the_knight_without_rest",
        ),
        _rule(
            "Greymaw's hollow lies beyond the Briar Glade. If he vanishes into the brush, hold your nerve. He likes to lunge for anyone who looks ready to break.",
            active="greymaws_trail",
        ),
        _rule(
            "Ruk's camp is just beyond Wolf Turn. Bring a `party`, keep pressure on him when he starts bellowing for help, and don't ignore the bleeding cuts from that axe.",
            active="ruk_the_fence_cutter",
            completed="fencebreakers",
        ),
        _rule(
            "The woods trail starts just south of the gate. Watch for briar imps and the bigger wolf tracks. If a fight looks ugly, use `enemies` before you commit.",
            active_any=("what_whispers_in_the_wood", "herbs_for_sister_maybelle"),
        ),
        _rule(
            "The south edge is quieter now. Still wet, still mean, still full of marsh ideas I'd rather not adopt, but quieter. That's enough of a win for one frontier town.",
            completed="the_hollow_lantern",
        ),
        _rule(
            "Goblin Road can breathe again, but the woods have gone strange. Sister Maybelle's been asking after moonleaf, and I've seen wolf sign deeper than I like.",
            completed="ruk_the_fence_cutter",
        ),
        _rule(
            "Start at the gate, then push to the Old Fence Line and Wolf Turn. If you want to gauge the road before committing, use `enemies` and then `fight` when you're ready.",
            active="roadside_howls",
        ),
        _rule(
            "Goblins count. Wolves don't. Clear the cutters anywhere along Goblin Road and keep an eye out for stolen fence scrap in your `pack`.",
            active="fencebreakers",
        ),
        _rule(
            "The road's quieter than it was. Not safe. Just quieter. Stay sharp and assume every bend is trying to embarrass you."
        ),
    ],
    "sister_maybelle": [
        _rule(
            "If you have not settled your calling yet, do it before you go collecting scars for one that does not suit you. The chapel turns out capable paladins, the woods turn out capable druids, and both make themselves useful faster than boasters do.",
            can_customize_build=True,
        ),
        _rule(
            "Brother Alden has taken over the chapel watch for now. If the mayor has you walking west, listen to the bell before you cross the barrows. It is never good when iron sounds tired. If you want the chapel at your back first, |wpray|n there before you go.",
            active_any=("lanterns_at_dusk", "do_not_disturb_the_dead"),
        ),
        _rule(
            "The old graves have a way of holding onto duty too long. Brother Alden will know the rites. You bring the part that lands harder.",
            active="the_knight_without_rest",
        ),
        _rule(
            "Moonleaf likes cold shade and bad company. Check your `pack` as you go. Once you have three sprigs, that will keep me in poultices for a little while.",
            active="herbs_for_sister_maybelle",
        ),
        _rule(
            "Whatever is wrong in the woods seems to gather around Greymaw. If he falls, the herbs may settle and the smaller things may remember fear.",
            active="greymaws_trail",
        ),
        _rule(
            "The trail south of the gate used to be calmer than Goblin Road. Now the roots feel restless and even the moonleaf has started growing where it shouldn't.",
            active="what_whispers_in_the_wood",
        ),
        _rule(
            "The moonleaf has stopped curling in on itself. That is the kind of good sign I trust more than speeches.",
            completed="greymaws_trail",
        ),
        _rule(
            "Ruk is done, thank the lanterns. Now the woods need looking after. Speak to Mira, or head south if you've already decided trouble deserves a personal visit.",
            completed="ruk_the_fence_cutter",
        ),
        _rule(
            "If you insist on being heroic, at least try not to bleed on the floorboards. The town still needs hands steady enough to gather herbs and carry the wounded."
        ),
    ],
    "joss_veller": [
        _rule(
            "The lamp house is the crown of the drowned line. If the thing inside calls up a ward, cut down whatever answered it first. The light will weaken once the support keeping it honest stops existing.",
            active="the_hollow_lantern",
        ),
        _rule(
            "Good. The line runs through the Sluice Walk and the Sunken Lock. Break enough of the drowned crew that the lamp house has to carry its own weight, then keep climbing while the light still thinks it has the initiative.",
            active="locks_under_blackwater",
        ),
        _rule(
            "Miretooth wasn't the source. He was just the teeth on the edge of a larger circuit. Follow the causeway east, confirm the old lantern weir is still somehow lit, and come back with proof before the mayor starts calling me dramatic in public.",
            active="the_south_light",
        ),
        _rule(
            "Coilback sits in the Anchor Pit like a bad idea nobody managed to turn off. Hit the pit from the relay trench or the crane grave, keep moving when the clamps come down, and don't let that foreman decide the bridge belongs to him.",
            active="foreman_coilback",
        ),
        _rule(
            "Good. The trench route still answers. Now chart the Crane Grave and bring me one clean shard of anchor glass so I can tune the lens without guessing.",
            active="signal_in_the_scrap",
        ),
        _rule(
            "The first trench east of the landing still carries a route pulse. Reach it, then bring back a live flux coil. Preferably one that isn't trying to bite through your gloves by the time you return.",
            active="bridgework_for_joss",
        ),
        _rule(
            "The south line is dark again. Properly dark, not waiting-to-be-clever dark. That's worth more than a tidy lens report. If you haven't looked upstairs yet, the Trophy Hall has a frame waiting for the prism.",
            completed="the_hollow_lantern",
        ),
        _rule(
            "There. Hear that? The gate's hum is cleaner now. The Trophy Hall upstairs has a place for the Beacon Core because some wins ought to stay where the whole family can point at them.",
            completed="foreman_coilback",
        ),
        _rule(
            "Every gate needs an anchor or you stop calling it travel and start calling it loss. The ring below is holding one stable bridge for now. Use `portals` to review the lineup, then go `east` when you're ready to test your nerve somewhere stranger.",
            room_id="brambleford_nexus_gate",
        ),
        _rule(
            "Different sky, same bones. The world here skins your instincts as tech. `sheet` will show the local names, and the return gate will always answer while I keep the bridge lit.",
            resonance="tech",
        ),
        _rule(
            "Most folk think I light lamps. True enough. They just forget a gate is another sort of lamp if you know what to feed it. The observatory's the town's portal center, whether the mayor likes the phrase or not."
        ),
    ],
    "mayor_elric_thorne": [
        _rule(
            "Then finish it. A wrong light in a drowned public works line is exactly the kind of sentence I would prefer to stop using. End the lamp house, come back alive, and I'll call that a proper frontier result.",
            active="the_hollow_lantern",
        ),
        _rule(
            "A drowned weir still running by bad intention alone is the sort of problem towns regret underestimating. Clear the lock line, prove the thing can be reached, and then end it before we have to start naming watch shifts after it.",
            active="locks_under_blackwater",
        ),
        _rule(
            "So the marsh was not merely growing a large predator. Fine. If Joss is right about the drowned weir, confirm it, map it, and tell me whether Brambleford needs to fear an old civic failure with a mean streak.",
            active="the_south_light",
        ),
        _rule(
            "Then finish Blackfen cleanly enough that the town can start saying south road again without sounding foolish. If the marsh truly has one ruling beast, bring that sentence to an end.",
            active="miretooths_claim",
        ),
        _rule(
            "Bandits, goblins, now the marsh edge. Every solved problem seems to uncover a less sociable one underneath it. Fine. Confirm what Blackfen is growing and make sure it stays south of our map.",
            active_any=("lights_in_the_reeds", "bogwater_rumors"),
        ),
        _rule(
            "Then finish it. The ridge tower was built to keep trouble out, not to tax every honest wagon trying to reach Brambleford alive. Bring Blackreed down and we'll have one less ambitious problem on the map.",
            active="captain_varn_blackreed",
        ),
        _rule(
            "The old tower is occupied, then. Good. Clear answers are easier to hate properly. Rowan knows the sort of fight this will become. Work with him and make the ridge expensive for bandits again.",
            active_any=("loose_arrows", "smoke_on_the_ridge"),
        ),
        _rule(
            "Brother Alden says the old knight has fully risen. Then finish it. Reach the Sunken Dais, end Sir Edric, and bring back whatever signet or proof he still clutches so I can tell the town this chapter is closed.",
            active="the_knight_without_rest",
        ),
        _rule(
            "So the causeway was not imagination. Good. I prefer confirmed bad news to rumors. Push on to the Barrow Circle, cut down the first dead things you find, and leave the chapel the harder question of why they woke.",
            active="do_not_disturb_the_dead",
        ),
        _rule(
            "Our western lanterns are failing one by one, and the watch swears something moves around the old stones after dusk. Speak with Brother Alden at the chapel, then follow the old stone path to the barrow causeway and tell me whether this is fear or fact.",
            active="lanterns_at_dusk",
        ),
        _rule(
            "The town sleeps easier when old promises stay buried. Now the eastern ridge needs the same sort of firm answer. Rowan's been muttering about smoke from the ruined watchtower.",
            completed="the_knight_without_rest",
        ),
        _rule(
            "Good. Then phase one of this town's current bad luck is closed: road, woods, barrows, ridge, warrens, fen, and now the drowned light beyond it. Brambleford will find a way to make more trouble eventually, but for one evening the board may stay quieter.",
            completed="the_hollow_lantern",
        ),
        _rule(
            "You've done enough on the southern trail that I trust your eyes. The chapel has been asking for steady boots, and the west lantern watch could use someone who doesn't startle easy.",
            completed="greymaws_trail",
        ),
        _rule(
            "A mayor mostly counts damage, grain, and who still owes whom after the rain. Lately I have also been counting how many people think the old barrows are somebody else's problem."
        ),
    ],
    "brother_alden": [
        _rule(
            "Sir Edric lies at the Sunken Dais, but not quietly enough. When grave-lights answer him, cut those lesser spirits down first. The ward around him should fail once the dead he leans on are gone. Ring the Dawn Bell and |wpray|n before you cross if you want steadier hands.",
            active="the_knight_without_rest",
        ),
        _rule(
            "The causeway is fouled and the circle beyond it is waking. Go into Old Barrow Field, put down four of the restless dead, and return only if the silence starts to sound honest again. Take the bell's blessing with you first if you have any sense.",
            active="do_not_disturb_the_dead",
        ),
        _rule(
            "The Dawn Bell has started answering with a thin, wrong note at dusk. Cross the causeway and see whether the field itself is stirring. If the air turns cold and the crows stop making natural noises, trust that instinct. And if you mean to go, |wpray|n before you leave the chapel.",
            active="lanterns_at_dusk",
        ),
        _rule(
            "The bell rings clean again. That is not peace, exactly, but it is close enough for town sleep and chapel thanks.",
            completed="the_knight_without_rest",
        ),
        _rule(
            "The chapel keeps records, candles, and the sort of silence people only notice when they lose it. If you need the Dawn Bell at your back before a hard road, ring your courage true and |wpray|n here before you leave."
        ),
    ],
}


STATIC_READ_RESPONSES = {
    "mayors_ledger": (
        "The open ledger carries three fresh entries in the mayor's square hand: LANTERN OIL SHORT BY TWO CRATES. "
        "WEST WATCH REPORTS LIGHT LOSS AT DUSK. CHAPEL REQUESTS ADDITIONAL VOLUNTEERS WITH STEADY NERVES."
    ),
    "dawn_bell": (
        "The bell's bronze lip is etched with a prayer worn soft by generations of hands: LET MORNING FIND US, "
        "LET MEMORY REST, LET THE LOST HEAR THE WAY HOME. Those who kneel beneath it before a hard road still say the chapel answers. Use |wpray|n if you mean to test that."
    ),
    "outfitters_chalkboard": (
        "Leda's chalk hand is spare and direct: WE BUY PELTS, HERBS, SALVAGE, ROAD SCRAP, AND OTHER SENSIBLE FINDS. "
        "FAIR PRICES FOR FAIR HANDS. ASK ABOUT A SHIFT IF YOU WANT TO EARN THE BETTER COLUMN."
    ),
    "forge_order_board": (
        "Torren's board reads: NAIL KEGS FOR SOUTH FARM. HINGE SET FOR MAYOR'S HALL. TWO SPEAR TIPS FOR THE WATCH. "
        "Below that, in heavier chalk: FIELD KIT IMPROVEMENTS DONE TO ORDER. WEAR IT IN. BRING SCRAP. PAY SILVER. "
        "ASK WITH |wforge|n, NOT WITH STORIES."
    ),
    "watchtower_warning_post": (
        "The old carving reads: BORDER WATCH POST THREE. KEEP FIRE LOW. SIGNAL SOUTH IF THE RIDGE MOVES. "
        "Someone newer has cut a reply beneath it: TOO LATE FOR THAT."
    ),
    "signal_brazier": (
        "Fresh soot rims the iron pan, and the stacked wood beside it has been sorted into quick-burn bundles. "
        "The tower crew means to signal far and fast if the ridge turns ugly."
    ),
    "blackreed_standard": (
        "The standard shows a black marsh reed stitched over a split road line. It is less a heraldic symbol "
        "than a very direct threat about who gets to pass beneath this hill."
    ),
    "sinkmouth_scratch_map": (
        "The slate shows a goblin scratch map: CAMP crossed out, then arrows leading east into a crown mark over a grease-slick room. One soot-smeared note is clearer than the rest: POT-KING EATS FIRST."
    ),
    "midden_bone_totem": (
        "The totem has been wired together from feast scraps and threats. Three scratched signs repeat around the lid-face: KING, POT, ROAD. None of them improve under repetition."
    ),
    "feast_hall_cauldron": (
        "The cauldron holds a stew thick with bone broth, scavenged roots, and the sort of meat nobody decent should identify after the first guess."
    ),
    "potking_lid_throne": (
        "The throne is less built than accumulated. Pot lids, road shields, and dented signboards have all been hammered together into a seat meant to look richer than the cave deserves."
    ),
    "fenreach_waypost": (
        "The old road mark once pointed to a survey line no one in Brambleford still uses. A newer charcoal warning cuts across it in Mira's hand: BLACKFEN SOUTH. KEEP TO THE HARD GROUND UNTIL THE MARSH STOPS LYING."
    ),
    "boglight_lantern": (
        "The lantern cage is cold, but something pale still clings to the green glass from the inside. One scratched note on the hook reads: IF IT LOOKS LIKE A GUIDE LIGHT, IT ISN'T."
    ),
    "carrion_stake_circle": (
        "Most of the stakes were hammered by anxious human hands. The newer cuts across them were not. A crow skull has been tied to the tallest one with reed cord and black bog thread."
    ),
    "miretooth_shed_skull": (
        "The skull is too heavy through the jaw and too narrow through the eyes to belong to anything Brambleford would name kindly. Deep score marks along the bone suggest the beast that shed it grew into something even worse."
    ),
    "drowned_survey_marker": (
        "The old survey cut reads: SOUTH WEIR LINE / BLACKWATER FEED / LAMP HOUSE EAST. A newer scratch over it is less official and more useful: IF THE LIGHT IS STILL BURNING, TURN IT WRONGER OR TURN IT OFF."
    ),
    "weir_keepers_plaque": (
        "The greened plaque reads: KEEP SOUTH LIGHT TRIMMED. HOLD THE LOCK LINE. MAINTAIN NIGHT SIGNAL FOR BRAMBLEFORD APPROACH. Whatever used to count as maintenance here has become something much less cooperative."
    ),
    "sunken_lock_chain": (
        "The chain hums through the black water in time with the wrong light overhead. Someone once stamped the nearest link with a warning that still survives the rust: DO NOT DRAW FULL LINE WITHOUT LAMP-HOUSE ORDER."
    ),
    "blackwater_lens_frame": (
        "The lens frame is bent around a cold white core like the brass tried to hold the light in place and learned too late that it was the part being reshaped instead."
    ),
    "barrow_marker_stone": (
        "The lichen-sunk stone reads: HERE KEEP FAITH WITH THE OLD FIELD. DISTURB NOTHING. LIGHT YOUR LANTERN. LEAVE BEFORE THE LAST BELL."
    ),
    "edrics_slab": (
        "The cracked slab still carries a knightly carving beneath the moss: SIR EDRIC VALE, WHO HELD THE LINE UNTIL THE LINE OUTLIVED HIM."
    ),
    "star_lens": (
        "The etched brass rings mark stars, routes, and a handful of names that are definitely not villages anywhere near Brambleford. One line is picked out brighter than the rest: JUNK-YARD PLANET."
    ),
    "salvage_beacon": (
        "A clipped scrolling line repeats across the beacon housing in a script your eyes somehow decide they understand: ANCHOR STABLE. RETURN VECTOR CLEAN. LOCAL SALVAGE FIELD ACTIVE."
    ),
    "relay_route_mast": (
        "The mast flashes a repeating route code through the trench glass: RELAY / YARD / PIT. Someone has etched a newer note beneath it in softer metal: IF IT HUMS BACK, DUCK."
    ),
    "crane_gantry": (
        "A dead foreman schedule still clings to the cab wall, every shift crossed out except one line left legible in angry strokes: COILBACK CLAIMS PIT AUTHORITY."
    ),
    "cellar_warning_slate": (
        "Uncle Pib's chalk scrawl reads: IF YOU ARE HOLDING THIS SLATE, THE RATS HAVE NOT EATEN YOU. GOOD. CLEAR THEM OUT AND I'LL CALL IT HEROISM."
    ),
    "ruks_chopping_block": (
        "Fresh cuts score the block in harsh, uneven lines. One gouge has been hacked deep enough to lodge a shred of wagon paint, and a goblin hand has scratched nearby: RUK KEEPS THIS ROAD."
    ),
    "woods_wardstone": (
        "The chalk marks are fresh enough to smear under a thumb. A careful hand has written one warning into the moss-dark side of the stone: DO NOT FOLLOW THE QUIET."
    ),
    "hunters_warning_post": (
        "Three deep knife-cuts have been carved into the cedar, then crossed out beneath a newer line: GREYMAW TOOK THE OUTER TRAIL. STAY IN NUMBERS."
    ),
}
