# World And Content

This document reflects the current core content pack in `brave_game/world/content/packs/core/`. If this file disagrees with the JSON pack, the pack wins.

## Live Shape

`Brave` is currently a cozy fantasy MUD with a complete first fantasy ladder, one portal branch, and a town hub built for local family co-op.

The present live structure is:

- Onboarding: Wayfarer's Yard.
- Hub: Brambleford.
- First road chapter: Goblin Road through Ruk the Fence-Cutter.
- Optional early branch after Ruk: Junk-Yard Planet.
- Fantasy continuation: Whispering Woods, Old Barrow Field, Ruined Watchtower, Goblin Warrens, Blackfen Approach.
- Fantasy capstone: Drowned Weir and The Hollow Lantern.

## Brambleford

Brambleford is a lantern-lit frontier town beside an old river crossing. It should feel practical, warm, a little funny, and worth protecting.

Current town rooms:

- `brambleford_town_green`: central hub and notice board.
- `brambleford_lantern_rest_inn`: social hub, cooking, arcade cabinet, Great Catch log, Uncle Pib, Sister Maybelle.
- `brambleford_rat_and_kettle_cellar`: first live town combat space.
- `brambleford_outfitters`: shopkeeping loop and Leda Thornwick.
- `brambleford_training_yard`: Captain Harl handoff after tutorial.
- `brambleford_mastery_hall`: mastery refinement with Mistress Elira Thorne.
- `brambleford_mayors_hall`: Mayor Elric and civic quest framing.
- `brambleford_chapel_dawn_bell`: Dawn Bell blessing, chapel lore, Brother Alden.
- `brambleford_east_gate`: Mira Fenleaf and the road handoff.
- `brambleford_hobbyists_wharf`: fishing.
- `brambleford_ironroot_forge`: forging and Torren Ironroot.
- `brambleford_menders_shed`: tinkering and Mender Veska Flint.
- `brambleford_great_observatory`: Joss Veller and portal framing.
- `brambleford_trophy_hall`: family trophy display.
- `brambleford_nexus_gate`: portal departure chamber.

## Tutorial Area

Wayfarer's Yard is the current first-time-player onboarding branch. It is not a detached training island; it sits beside Brambleford's training grounds.

Current tutorial rooms:

- `tutorial_wayfarers_yard`: start, Tamsin, rest point.
- `tutorial_quartermaster_shed`: Nella, gear, pack, supply board.
- `tutorial_family_post`: optional party basics.
- `tutorial_sparring_ring`: Brask and class-skill instruction.
- `tutorial_vermin_pens`: controlled first fight.
- `tutorial_gate_walk`: bridge back to Brambleford.

## Live Quest Ladder

The current starting quest chain is:

1. `practice_makes_heroes`
2. `rats_in_the_kettle`
3. `roadside_howls`
4. `fencebreakers`
5. `ruk_the_fence_cutter`
6. `what_whispers_in_the_wood`
7. `herbs_for_sister_maybelle`
8. `greymaws_trail`
9. `bridgework_for_joss`
10. `signal_in_the_scrap`
11. `foreman_coilback`
12. `lanterns_at_dusk`
13. `do_not_disturb_the_dead`
14. `the_knight_without_rest`
15. `smoke_on_the_ridge`
16. `loose_arrows`
17. `captain_varn_blackreed`
18. `below_the_fencebreakers`
19. `gutters_and_hexes`
20. `the_pot_kings_feast`
21. `bogwater_rumors`
22. `lights_in_the_reeds`
23. `miretooths_claim`
24. `the_south_light`
25. `locks_under_blackwater`
26. `the_hollow_lantern`

The first-hour spine is the first five quests after tutorial:

`Practice Makes Heroes` -> `Rats in the Kettle` -> `Roadside Howls` -> `Fencebreakers` -> `Ruk the Fence-Cutter`.

## Zone Roles

### Goblin Road

Rooms: Trailhead, Old Fence Line, Wolf Turn, Fencebreaker Camp.

Purpose: first real adventure space. It teaches room-by-room pushing, light outdoor fights, road pressure, and the first named boss.

Boss: Ruk the Fence-Cutter.

### Whispering Woods

Rooms: Whispering Woods Trail, Old Stone Path, Briar Glade, Greymaw's Hollow.

Purpose: moves the game from practical road danger into unease, roots, old warnings, and creature-haunted wilderness.

Boss: Old Greymaw.

### Junk-Yard Planet

Rooms: Junk-Yard Landing, Scrapway Verge, Relay Trench, Crane Grave, Anchor Pit.

Purpose: first portal branch and genre shift. It proves that Brave can keep the same character core while changing world tone and enemy texture.

Boss: Foreman Coilback.

### Old Barrow Field

Rooms: Old Barrow Causeway, Marker Row, Barrow Circle, Sunken Dais.

Purpose: undead escalation, chapel value, memory, old oaths, and the first heavier emotional note.

Boss: Sir Edric the Restless.

### Ruined Watchtower

Rooms: Watchtower Approach, Archer's Ledge, Breach Yard, Cracked Tower Stairs, Blackreed's Roost.

Purpose: tactical mortal threat. Bandits understand sightlines, pressure, dogs, archers, and road control.

Boss: Captain Varn Blackreed.

### Goblin Warrens

Rooms: Sinkmouth Cut, Bone Midden, Feast Hall, Sludge Run, Torchgut Tunnel, Pot-King's Court.

Purpose: reveals that Ruk was not the whole goblin problem. The road cutters were connected to a deeper, uglier power center.

Boss: Grubnak the Pot-King.

### Blackfen Approach

Rooms: Fenreach Track, Reedflats, Carrion Rise, Boglight Hollow, Miretooth's Wallow.

Purpose: pivots from bandits and goblins to the wrong south light. The marsh should feel patient, misleading, and old enough to make Brambleford look small.

Elite: Miretooth.

### Drowned Weir

Rooms: Drowned Causeway, Sluice Walk, Sunken Lock, Lantern Weir, Blackwater Lamp House.

Purpose: phase-1 fantasy capstone. The wrong light becomes physical, answerable, and dangerous.

Boss: The Hollow Lantern.

## Story Arc

The current fantasy arc works because it widens in layers:

1. The town has ordinary problems that still matter.
2. The road is being cut apart by something organized.
3. The woods and barrows show that the local world is older and less stable than Brambleford wants to admit.
4. Mortal opportunists seize the ruined tower.
5. The warrens reveal a deeper goblin infrastructure.
6. Blackfen shows the road problem was only one symptom.
7. Drowned Weir turns the south-light thread into a chapter-ending answer.

## Writing Rules

- Story should travel through rooms, NPC reactions, quest handoffs, readable objects, encounter intros, and trophy payoffs.
- Keep exposition short. A player should understand the current problem before they understand the whole backstory.
- Make every zone teach one new mood and one new play pattern.
- Let Brambleford react to completed bosses. The town is the emotional scoreboard.
- Do not add random chores to the first hour. Every task should either teach play or sharpen the road-to-Ruk story.
