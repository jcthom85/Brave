# Brambleford Town Plan

This is the canonical plan for Brambleford's layout. It exists to stop the town from growing ad hoc.

Right now, the project already had high-level Brambleford intent in [world_and_content.md](world_and_content.md), but not a strict room-by-room town spec. This document is now the source of truth for:

- what rooms Brambleford has now
- what rooms are planned next
- what systems belong in which rooms
- which ideas should stay as objects inside existing rooms instead of becoming new rooms

## Town Role

Brambleford is the family's home base. It is not just a quest dispenser. It must support four different jobs at once:

- onboarding and recovery
- social hanging out
- low-stakes town activities
- launch points into danger and the Nexus

The town should feel compact, readable, and worth returning to between runs.

## Layout Rules

These rules are now fixed unless the docs are updated first.

- Brambleford uses cardinal-first navigation.
- The surface town should stay readable as one ASCII map region.
- Every new town room needs a clear gameplay reason, not just flavor.
- If a feature works as an object in an existing room, prefer that over adding another room.
- The east side of town is the adventure launch side.
- The observatory hill is the portal side.
- The inn remains the social and recovery side.
- The town green remains the respawn and meetup anchor.

## Current Live Footprint

This is the current live Brambleford map region in the game:

```text
              [H]
                |
[C]-----[M]-----[Y]-----[O]
 |          |         |
[U]-----[I]-----[G]-----[E]
                    |
                  [W]
                    |
                  [F]
```

Legend:

- `G` = Brambleford Town Green
- `I` = The Lantern Rest Inn
- `U` = Brambleford Outfitters
- `Y` = Training Yard
- `M` = Mayor's Hall
- `C` = Chapel of the Dawn Bell
- `E` = East Gate
- `W` = Hobbyist's Wharf
- `F` = Ironroot Forge
- `O` = Great Observatory
- `H` = Trophy Hall

Attached rooms not shown on the town surface map:

- `down` from the inn: Rat and Kettle Cellar
- `north` from the training yard: Wayfarer's Yard tutorial branch
- `east` from the observatory: Nexus Gate

## Canonical Room List

### Live Now

#### Brambleford Town Green

- Status: live
- Coordinates: `(0, 0)`
- Purpose: main meetup point, defeat return point, and town traffic hub
- Connected to: Inn west, Training Yard north, East Gate east, Wharf south
- Systems here: notice board, party meetup, map anchor
- Design note: keep this readable and uncluttered; it should always be the easiest room in town to understand

#### The Lantern Rest Inn

- Status: live
- Coordinates: `(-1, 0)`
- Purpose: social hub, recovery room, cooking room, light quest room
- Connected to: Town Green east, Mayor's Hall north, Cellar down
- Systems here: cooking, meal buffs, Great Catch Log, Uncle Pib, Sister Maybelle
- Design note: this is intentionally multi-purpose; do not split it into separate kitchen, tavern, and clinic rooms in phase 1

#### Brambleford Outfitters

- Status: live
- Coordinates: `(-2, 0)`
- Purpose: town commerce room and first merchant loop
- Connected to: Inn east, Chapel north
- Systems here: loot selling, shift bonus loop, Leda Thornwick, trade board
- Design note: this is a practical frontier store, not a generic fantasy item mall

#### Rat and Kettle Cellar

- Status: live
- Coordinates: attached interior below the inn
- Purpose: first dungeon and low-risk co-op combat space
- Connected to: Inn up
- Systems here: cellar encounter slice, early quest combat
- Design note: keep it small and readable; this is the family's first group-combat test bed

#### Training Yard

- Status: live
- Coordinates: `(0, 1)`
- Purpose: onboarding, class identity, combat literacy
- Connected to: Town Green south, Mayor's Hall west, Great Observatory east, Gate Walk north
- Systems here: Captain Harl Rowan, early guidance
- Design note: this is now the handoff room from the Wayfarer's Yard tutorial branch into the main town. See [tutorial_and_onboarding.md](tutorial_and_onboarding.md).

#### Gate Walk

- Status: live
- Coordinates: attached tutorial branch south of Wayfarer's Yard, north of Training Yard
- Purpose: tutorial handoff and orientation threshold
- Connected to: Training Yard south, Wayfarer's Yard north
- Systems here: final tutorial send-off
- Design note: keep this simple; it exists to make the transition from guided play into the real town feel intentional

#### Wayfarer's Yard

- Status: live
- Coordinates: tutorial branch hub
- Purpose: first-time-player spawn room and tutorial anchor
- Connected to: Gate Walk south, Family Post north, Quartermaster Shed east, Sparring Ring west
- Systems here: Sergeant Tamsin Vale, first movement lesson, minimap literacy, scene-reading onboarding
- Design note: this room should stay clean, calm, and readable; it is where the game proves to a brand-new player that it can teach itself

#### Quartermaster Shed

- Status: live
- Coordinates: attached tutorial branch east of Wayfarer's Yard
- Purpose: starter-kit and inventory literacy room
- Connected to: Wayfarer's Yard west
- Systems here: Quartermaster Nella Cobb, supply board, `gear`, `pack`, and `read` onboarding
- Design note: this room should feel practical, not menu-like

#### Family Post

- Status: live
- Coordinates: attached tutorial branch north of Wayfarer's Yard
- Purpose: optional co-op and regrouping literacy
- Connected to: Wayfarer's Yard south
- Systems here: Courier Peep Marrow, family post sign, `party` onboarding
- Design note: this room teaches family play without making solo players feel blocked

#### Sparring Ring

- Status: live
- Coordinates: attached tutorial branch west of Wayfarer's Yard
- Purpose: first combat instruction room
- Connected to: Wayfarer's Yard east, Vermin Pens south
- Systems here: Ringhand Brask, `fight` / `enemies` / `attack` / `use` instruction
- Design note: Brask should teach one combat idea at a time

#### Vermin Pens

- Status: live
- Coordinates: attached tutorial branch south of Sparring Ring
- Purpose: first forgiving live encounter
- Connected to: Sparring Ring north
- Systems here: first tutorial combat win
- Design note: this is the smallest meaningful danger room in the game and should stay that way

#### Mayor's Hall

- Status: live
- Coordinates: `(-1, 1)`
- Purpose: civic quest hub and town problem board
- Connected to: Inn south, Training Yard east, Chapel west
- Systems here: Mayor Elric Thorne, mayor's ledger, progression handoff into town-level threats
- Design note: this is the administrative quest anchor for Brambleford itself

#### Chapel of the Dawn Bell

- Status: live
- Coordinates: `(-2, 1)`
- Purpose: spiritual, healing, and undead-lore anchor
- Connected to: Mayor's Hall east
- Systems here: Brother Alden, Dawn Bell, `pray`, Dawn Bell blessing, barrow quest support
- Design note: this room carries tone more than traffic; it should feel still and intentional

#### East Gate

- Status: live
- Coordinates: `(1, 0)`
- Purpose: wilderness launch point
- Connected to: Town Green west, Goblin Road east, Whispering Woods south
- Systems here: Mira Fenleaf, outdoor quest routing
- Design note: the gate is where Brambleford stops being cozy and starts being watchful

#### Hobbyist's Wharf

- Status: live
- Coordinates: `(0, -1)`
- Purpose: relaxed side activity loop
- Connected to: Town Green north
- Systems here: fishing, loaner pole rack
- Design note: keep this calm; it exists to give the family something to do together besides fighting

#### Ironroot Forge

- Status: live
- Coordinates: `(0, -2)`
- Purpose: equipment upgrade room and blacksmith anchor
- Connected to: Hobbyist's Wharf north
- Systems here: Torren Ironroot, forge order board, `forge` equipment upgrades
- Design note: this is a practical working smithy for field kit, not a giant crafting spreadsheet in room form

#### Great Observatory

- Status: live
- Coordinates: `(1, 1)`
- Purpose: portal-center foyer and strange-town-energy room
- Connected to: Training Yard west, Trophy Hall north, Nexus Gate east
- Systems here: Joss Veller, star lens, portal introduction
- Design note: this is the in-universe portal center and should stay that way

#### Trophy Hall

- Status: live
- Coordinates: `(1, 2)`
- Purpose: shared family accomplishment room
- Connected to: Great Observatory south
- Systems here: trophy display, visible progress markers
- Design note: this is a social memory room, not just a storage room

#### Nexus Gate

- Status: live
- Coordinates: separate `nexus_network` region, attached east of the observatory
- Purpose: multiverse gateway room
- Connected to: Great Observatory west, guest worlds east
- Systems here: gate plaque, portal list, resonance transition
- Design note: physically town-accessible, but not counted as part of the surface Brambleford map

### Planned Next

These rooms are planned and reserved. Do not add different town rooms before these are resolved.

#### Common Project Yard

- Status: planned
- Proposed coordinates: `(1, -2)`
- Proposed connections: Ironroot Forge west
- Purpose: town project board, upgrade sink, garden/build loop
- Why it exists: the docs call for town upgrades and shared building; this keeps that system grounded in Brambleford instead of scattering it

## Reserved Expansion Footprint

This is the intended town shape once the planned phase-1 Brambleford rooms are in:

```text
              [H]
                |
[C]-----[M]-----[Y]-----[O]
 |                    |
[U]-----[I]-----[G]-----[E]
                    |
                  [W]
                    |
               [F]-----[P]
```

Legend for reserved rooms:

- `P` = Common Project Yard

## Features That Should Stay Inside Existing Rooms

Not every feature needs a new room. These should remain objects or sub-features inside existing spaces unless a later system proves otherwise.

- The Family Chronicle should live in the inn or Trophy Hall, not as a separate archive building in phase 1.
- Cooking stays in the inn hearth, not a separate kitchen room.
- Fishing stays at the wharf, not a separate boathouse room.
- Town notices stay on the Town Green board, not in a separate council chamber.
- Portal administration stays in the observatory and Nexus, not in a second portal office elsewhere in town.

## Current NPC Ownership

This is the intended room ownership for Brambleford's current named NPCs.

- Captain Harl Rowan: Training Yard
- Sergeant Tamsin Vale: Wayfarer's Yard
- Quartermaster Nella Cobb: Quartermaster Shed
- Courier Peep Marrow: Family Post
- Ringhand Brask: Sparring Ring
- Mayor Elric Thorne: Mayor's Hall
- Brother Alden: Chapel of the Dawn Bell
- Uncle Pib Underbough: Lantern Rest Inn
- Sister Maybelle: Lantern Rest Inn
- Mira Fenleaf: East Gate
- Torren Ironroot: Ironroot Forge
- Joss Veller: Great Observatory

This matters because the town should teach the player where to go by habit:

- training and first instructions at the yard
- comfort and recovery at the inn
- civic escalation at the hall
- spiritual and undead escalation at the chapel
- wilderness launches at the gate
- odd multiverse work on the hill

## Current Progression Through Town

The intended phase-1 flow through Brambleford is:

1. Wayfarer's Yard branch: learn movement, room reading, gear, pack, combat basics, and optional party literacy
2. Training Yard: receive the handoff into the real town
3. Town Green: read the board and get bearings
4. Inn and Cellar: finish the first low-risk combat and recovery loop
5. East Gate: launch into Goblin Road and Whispering Woods
6. Mayor's Hall and Chapel: escalate into town-scale and undead threats
7. Observatory and Nexus: open the first guest world branch
8. Trophy Hall: celebrate shared progress and make the town feel persistent

## Town Design Decisions Already Settled

These are not open questions anymore.

- Brambleford is compact, not sprawling.
- The portal center is the observatory and Nexus complex.
- The town uses mostly cardinal movement and map coordinates.
- The inn is deliberately overloaded with social functions because that makes family play easier.
- The East Gate is the main outdoor branching point for both Goblin Road and Whispering Woods.
- Trophy display belongs near the observatory, not in the town square.

## Guardrails For Future Additions

Before adding any new Brambleford room, answer all of these:

1. What gameplay loop does this room unlock that cannot live in an existing room?
2. What coordinate and cardinal connection does it take on the town map?
3. Which named NPC or readable object owns the room?
4. Does it improve the family play loop, or is it just flavor sprawl?
5. Has this document been updated first?

If the answer to question 1 is weak, do not add the room.
