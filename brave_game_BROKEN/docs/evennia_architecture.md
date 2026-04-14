# Evennia Architecture

## Decision

`Brave` will use Evennia as the base server framework.

Reason:

- The game is a text-first multiplayer RPG
- It needs persistent rooms, characters, objects, and sessions
- It should support 1 to 4 players on the same local network from separate devices
- Evennia already provides the infrastructure we would otherwise spend weeks rebuilding

## Multiplayer Model

Target model:

- One host machine runs the Evennia server
- Each player connects from their own browser or MUD client
- In phase 1, each human has one account and one active adventurer
- Family play happens over the local network, not a shared-screen client

This is the cleanest match for Evennia's account, session, and character model.

## High-Level System Mapping

### Account

Use Evennia `Account` objects as the human login identity.

Store or associate:

- Login and permissions
- Account-level preferences
- Potential future roster of characters

### Character

Use the main `Character` typeclass as the player's adventurer.

Brave-specific character state should include:

- Race
- Class
- Level
- XP
- Primary stats
- Derived stats
- Current HP, mana, and stamina
- Learned abilities
- Equipment references
- Party membership
- Quest state references

### Room

Use Evennia `Room` typeclasses for Brambleford locations, wilderness nodes, dungeon spaces, and boss arenas.

Room state should support:

- Zone identifier
- Safe or dangerous flag
- Flavor text and landmark details
- Spawn table or encounter table references
- Quest hooks
- Travel metadata

### Exit

Use mostly standard Evennia exits for navigation between rooms.

Brave-specific exit behavior may later add:

- Zone gating by quest or level
- Temporary lockouts during encounters
- Flavor travel text

### Object

Use the base object line for:

- Equippable items
- Consumables
- Loot drops
- Containers
- Environmental interactables

For the current first slice, it is acceptable to keep starter gear and basic loot as source-controlled data
attached to character state before promoting them into full physical world objects.

### Script

Use Evennia `Script` objects for stateful timed systems.

Likely script uses:

- Encounter controllers
- Combat tick processing
- Respawn timers
- Quest or world-state timers
- Scheduled boss or zone events

## Combat Architecture

### Combat Resolution Model

Recommended phase-1 model:

- Fixed-tick encounter processing
- Basic attacks handled automatically by combat state
- Active abilities submitted as intents
- Resolution applied in a predictable per-tick order

Why this fits Evennia:

- It keeps text output readable
- It works cleanly with multiplayer sessions
- It maps naturally onto Scripts or scheduled callbacks
- It avoids turning every fight into freeform command spam

### Encounter Ownership

Each active encounter should be controlled by a dedicated encounter object or script rather than spreading combat state across many ad hoc room attributes.

That controller should own:

- Participant lists
- Initiative or action order
- Enemy AI decisions
- Cooldowns and durations
- Threat tables
- Encounter log output
- Victory and defeat cleanup

## Command Layer Strategy

Do not replace Evennia's default command set all at once.

Phase-1 approach:

- Keep core navigation and inspection commands available while building
- Add Brave-specific commands incrementally
- Prefer a small command surface with strong defaults

Likely early commands:

- `sheet`
- `gear`
- `pack`
- `party`
- `quest`
- `travel`
- `talk`
- `read`
- `attack`
- `use`
- `rest`

Inference:

Evennia's defaults give us a working baseline quickly, but a family-friendly RPG will eventually want a narrower and more curated command vocabulary.

## Content Strategy

### Version-Controlled Content First

Phase 1 should keep core content in source-controlled data rather than in manual in-game builders.

Recommended early content categories:

- Races
- Classes
- Abilities
- Enemies
- Bosses
- Loot items
- Quests
- Rooms and travel graph

### Prototypes

Use Evennia prototypes for spawnable items, enemies, and simple interactables.

Good prototype candidates:

- Weapons and armor
- Potions and trinkets
- Standard enemy variants
- Reusable environmental objects

Less ideal prototype candidates:

- Complex boss fights with custom logic
- Party combat controllers
- Systems that require substantial behavior beyond static data

## Where Brave Logic Should Live

Recommended ownership by package:

- [`brave_game/typeclasses/`](/mnt/c/Brave/brave_game/typeclasses): entity behavior and persistent object models
- [`brave_game/commands/`](/mnt/c/Brave/brave_game/commands): player command surface
- [`brave_game/world/`](/mnt/c/Brave/brave_game/world): game data, prototypes, help entries, content loaders
- [`brave_game/server/conf/`](/mnt/c/Brave/brave_game/server/conf): minimal server hooks and settings overrides
- [`brave_game/web/`](/mnt/c/Brave/brave_game/web): optional browser UI customization after the core loop works

## Persistence Rules

Prefer simple persistent state first.

Good phase-1 persistent data:

- Character progression
- Equipment
- Quest flags
- Room-level world state when needed
- Party membership when session continuity matters

Avoid early persistence of:

- Deep economy simulation
- Highly granular world simulation
- Large numbers of timed background processes with no gameplay payoff

## Web Client Strategy

Use the stock Evennia web client first.

Do not start by rebuilding the browser UI.

Only customize after:

- Character creation works
- Party movement works
- Combat output is readable
- The first zone loop is playable

The likely first useful web customization is a lightweight side pane for character sheet or party status, not a complete frontend rewrite.

## Phase-1 Technical Priorities

In Evennia terms, the recommended implementation order is:

1. Character data model
2. Zone and room graph for Brambleford plus Goblin Road
3. Item and enemy prototypes
4. Quest state model
5. Encounter controller and combat tick loop
6. Class abilities for Warrior, Cleric, and Ranger
7. First boss fight

## Explicit Non-Goals

Do not do these early:

- Replace Evennia's architecture with a custom engine inside Evennia
- Build a bespoke SPA frontend before the core loop exists
- Add many new systems to avoid learning Evennia's base model
- Store critical design data only in ad hoc database edits

## Working Rule

Use Evennia for infrastructure. Put Brave's uniqueness into combat, content, progression, and presentation, not into unnecessary framework surgery.
