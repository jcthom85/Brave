# Implementation Plan

## Build Strategy

Build `Brave` as a small, data-driven game with a playable vertical slice early. Do not wait for every class and every zone before making the core loop playable.

## System Boundaries

Recommended phase-1 systems:

- Character creation
- Race and class definitions
- Stats and resource calculation
- Inventory and equipment
- Combat engine
- Enemy AI behavior rules
- Loot tables
- Quest tracking
- Room and zone content
- Save and load for local progression

Recommended content data types:

- Races
- Classes
- Abilities
- Enemies
- Bosses
- Items
- Quests
- Rooms or nodes
- NPCs
- Dialogue snippets

## Architectural Guidance

Keep the implementation engine-agnostic unless a code stack has already been chosen. Regardless of language, prefer:

- Data-first content definitions over hardcoded encounter logic
- Small composable combat effects instead of one-off scripted abilities
- Clear separation between simulation state and text presentation
- Deterministic combat resolution where practical for testing and tuning

## Recommended Milestones

### Milestone 0: Foundation

Ship the minimum framework for:

- Player creation
- Save data
- Room traversal
- Basic enemy definitions
- Basic attack flow
- Ability and cooldown framework
- Combat log output

### Milestone 1: First Playable Slice (The Family Hub)

Target content:
- Brambleford hub with basic fishing and cooking.
- Audio foundation (Ambience for town, basic SFX).
- Warrior, Cleric, Ranger.
- Warrior's training yard for practicing reading and controls.

Exit criteria:
- A family can sit together, catch fish, cook a meal, and finish the "Rats in the Cellar" quest with sound effects.

### Milestone 2: Core Combat & The First Portal

Target content:
- Whispering Woods.
- Mage and Rogue.
- The Nexus: **Junk-Yard Planet** (First Sci-Fi Portal).
- First "Lore Highlights" in room descriptions.

Exit criteria:
- Players can "step through the portal" to the Junk-Yard Planet and see their stats/abilities change to Sci-Fi skins.
- Audio transitions smoothly between fantasy and sci-fi themes.

### Milestone 3: Creative Expansion (Building Tools)

Target content:
- Old Barrow Field.
- First set of `/build` tools for Sandbox Portals.
- "Lore Card" system (`/lore`) for highlighted text.

Exit criteria:
- A player can successfully describe and name a new room in their personal portal.
- The Lore system provides extra flavor text for world-building.

### Milestone 4: Full Phase-1 Breadth

Target content:
- Ruined Watchtower and Goblin Warrens.
- Paladin and Druid.
- "Shopkeeper's Shift" minigame.
- Recorded "Voiceover" for the game's finale.

Exit criteria:
- The entire zone ladder is playable, including the first community-built portal world.
- A player can run the Outfitters for a 10-minute shift, interacting with NPCs.

### Milestone 5: Polish & Family Balance

Target focus:
- Tuning for 4-player co-op.
- "Social" features (Trophy Hall, shared logs).
- Finalizing the audio soundscape.
- Quest cleanup and loot pass.
- Class pacing and log clarity.

Exit criteria:
- The family can play for a full 2-hour session across multiple worlds and activities without friction.
- A fresh party can finish phase 1 without major dead ends or unreadable combat output.

## Content Production Order

Recommended order:

1. **Brambleford Hub** (Home Base, Wharf, Inn, Observatory)
2. **Goblin Road** (First Combat)
3. **The Junk-Yard Planet** (First Portal / Genre Swap)
4. **Whispering Woods** (Environmental Tension)
5. **Old Barrow Field** (The "Apprentice Architect" Sandbox)
6. **Ruined Watchtower** (Tactical Boss Fight)
7. **Goblin Warrens** (Dungeon Crawl)
8. **The Training Island** (Second Portal / Ki Combat)
9. **Blackfen Approach** (End-of-Phase Challenge)

Recommended class order:

1. Warrior
2. Cleric
3. Ranger
4. Mage
5. Rogue
6. Paladin
7. Druid

## Definition Of Done For Phase 1

Phase 1 should be considered complete when all of the following are true:

- All seven classes are playable
- All five races are selectable
- Brambleford and six outer zones are implemented
- Core quest line can be completed from start to finish
- Loot progression supports the full level range
- Bosses are beatable with multiple party compositions
- Combat logs remain understandable in 4-player sessions
- Save or session progression is stable enough for repeat play

## Practical Rules During Development

- Prefer reusable status effects over custom boss-only mechanics
- Do not add a new system when a content tweak would solve the problem
- Finish one zone to shippable quality before starting three more
- Treat readability as a feature, not polish
- Protect the vertical slice from scope creep
