# Brave: Documentation

Welcome to the documentation for **Brave**, a family-focused, multi-genre MUD (Multi-User Dungeon) built for cooperative play, creative storytelling, and world-building.

## Project Vision

`Brave` is designed as a digital hangout for a family of four. It blends a cozy, "early-MMO" fantasy core with a vast "Nexus" of portal worlds, allowing the family to jump between genres (like Star Wars or Dragonball) while maintaining their progress.

### Core Pillars
- **Family First:** A safe, warm, and cooperative experience.
- **Multiverse Creativity:** Portals to infinite worlds, serving as a sandbox for building new experiences.
- **Varied Gameplay:** Combat balanced with activities like fishing, cooking, and shopkeeping.
- **Immersive Audio:** A rich soundscape that makes the text-based world feel alive.

## Document Map

### High-Level Vision
- [**Vision and Scope**](vision_and_scope.md): The "big picture" of what the game is and who it's for.
- [**Starting Concept**](starting_concept.md): The original fantasy design document.

### Systems & Mechanics
- [**Core Systems**](core_systems.md): The engine's DNA—stats, resonance (genre scaling), and audio triggers.
- [**Reactive UI & Theming Plan**](reactive_ui_and_theming_plan.md): How style themes, world tone, and reactive browser FX should work together.
- [**Mobile Webclient Design**](mobile_webclient_design.md): The dedicated phone/tablet layout plan that preserves the current desktop UI.
- [**Mobile Shell Refactor Plan**](mobile_shell_refactor_plan.md): The current mobile-shell target for exploration, micromap, utility access, and bottom-deck controls.
- [**Menu-First, Command-Complete**](menu_first_command_complete_plan.md): The UI interaction plan for making normal play button-first and menu-first while preserving full typed-command support.
- [**Lantern Rest Arcade Plan**](lantern_rest_arcade_plan.md): The target design for turning Joss's cabinet into a full-featured ASCII arcade game with authentic Pac-Man feel.
- [**Tutorial & Onboarding**](tutorial_and_onboarding.md): The recommended first-time-player flow, tutorial start place, and beginner section plan.
- [**First Hour Chapter Plan**](first_hour_chapter_plan.md): The canonical opening ladder from tutorial through Goblin Road and the first boss payoff.
- [**First-Hour Co-op Pass**](first_hour_coop_pass.md): The family-play tuning rules for the tutorial, cellar, Goblin Road, and the first boss.
- [**Chapel And Class Completion Pass**](chapel_and_class_completion_pass.md): The Dawn Bell support loop and the Paladin/Druid completion slice.
- [**Phase-1 Capstone Plan**](phase1_capstone_plan.md): The canonical final zone, quest chain, and chapter-ending boss for the current fantasy ladder.
- [**Multiverse & Portals**](multiverse_and_portals.md): How the Nexus works and how different genres are handled.
- [**Minigames & Activities**](minigames_and_activities.md): Details on fishing, cooking, shopkeeping, and town building.
- [**Audio Systems**](audio_systems.md): The soundscape, reactive SFX, and custom voiceover systems.
- [**Combat & Encounters**](combat_and_encounters.md): Detailed rules for tactical, party-based combat.

### Creative & Storytelling
- [**Creative Systems & Building**](creative_systems_and_building.md): Tools for world-building, lore, and "Dungeon Master" style play.
- [**World and Content**](world_and_content.md): Detailed descriptions of Brambleford, its NPCs, and the first portal worlds.
- [**Brambleford Town Plan**](brambleford_town_plan.md): Canonical room-by-room plan for the town hub, including live and reserved rooms.

### Project Management
- [**Implementation Plan**](implementation_plan.md): Recommended build order, milestone plan, and phase-1 definition of done.
- [**Open Questions**](open_questions.md): Tracking unresolved design and technical decisions.
- [**Evennia Setup**](evennia_setup.md): Technical instructions for the Evennia engine.
- [**Evennia Architecture**](evennia_architecture.md): How the game maps to Evennia's technical structures.

## Phase-1 Snapshot

Phase 1 establishes the "Home Base" and the first steps into the Multiverse:
- **Brambleford Hub:** The primary safe zone and family hangout.
- **Classic RPG Loop:** Level 1-10 progression in the "Brave" fantasy setting.
- **The First Portal:** A small, themed "Guest World" (Junk-Yard Planet).
- **The Hobbyist's Kit:** Basic fishing and cooking minigames.
- **Audio Foundation:** Ambient loops for all major zones and basic combat SFX.

## Current Live Slice

The current playable build includes:
- **Classes:** Warrior, Cleric, Ranger, Mage, Rogue, Paladin, Druid.
- **Onboarding:** Wayfarer's Yard tutorial branch feeding into the Training Yard.
- **Hub:** Brambleford, Outfitters, Ironroot Forge, Trophy Hall, Observatory, and Nexus Gate.
- **Fantasy progression:** Goblin Road, Whispering Woods, Old Barrow Field, Ruined Watchtower, Goblin Warrens, Blackfen Approach.
- **Fantasy capstone:** Drowned Weir.
- **Portal progression:** Junk-Yard Planet.
- **Town loops:** fishing, cooking, shopkeeping shift, forge upgrades, chapel blessings, shared trophies, and local-family co-op party play.

## Working Rule

Keep the game small, readable, and shippable. When in doubt, prefer fewer systems with clearer class identity and stronger content reuse, but never sacrifice the "Fun" or "Family" pillars.
