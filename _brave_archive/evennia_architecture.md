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
- Each human can have an account and character roster
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

Current model:

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

Current approach:

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

Core content lives in source-controlled JSON packs, with creator tooling editing those packs through validated mutation paths.

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

- [`brave_game/typeclasses/`](../brave_game/typeclasses): entity behavior and persistent object models
- [`brave_game/commands/`](../brave_game/commands): player command surface
- [`brave_game/world/`](../brave_game/world): content registry, game systems, combat, quests, tutorial, and browser view payloads
- [`brave_game/server/conf/`](../brave_game/server/conf): server hooks, settings, web plugins, and connection screens
- [`brave_game/web/`](../brave_game/web): web routes, templates, API, static assets, audio hooks, and browser client customization

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

The stock Evennia client has been extended with Brave-specific panels, browser views, audio hooks, and mobile-oriented layout work. Commands remain canonical; browser controls should send the same commands instead of creating a second gameplay API.

## Current Technical Priorities

In Evennia terms, the useful next work is:

1. Keep JSON content validation strict.
2. Preserve command behavior as the canonical gameplay path.
3. Strengthen browser views where they clarify current state or remove typing friction.
4. Tighten the first-hour flow before adding new world breadth.
5. Keep combat output readable for both solo and family-party sessions.

## Explicit Non-Goals

Do not do these early:

- Replace Evennia's architecture with a custom engine inside Evennia
- Build a bespoke SPA frontend before the core loop exists
- Add many new systems to avoid learning Evennia's base model
- Store critical design data only in ad hoc database edits

## Working Rule

Use Evennia for infrastructure. Put Brave's uniqueness into combat, content, progression, and presentation, not into unnecessary framework surgery.
