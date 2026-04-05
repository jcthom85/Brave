# Data-Driven Content Architecture

## Goal

Brave should separate runtime code from authored game content so that future creator tools can build and edit the game without requiring direct Python edits.

The target model is:

- `engine`: Evennia objects, persistence, combat execution, quest progression, browser payload builders, and other runtime systems.
- `content registry`: typed access layer that loads game content, validates it, resolves references, and exposes stable lookup APIs to runtime code.
- `content packs`: source-controlled definitions for classes, races, abilities, items, rooms, quests, enemies, encounters, dialogue, activities, portals, and other authored content.
- `tooling`: validators, import/export helpers, preview runtime, and editor-facing APIs.

## Current State

Brave already stores a large amount of content in version-controlled data, but that content is still shaped as Python module globals under `brave_game/world/data/`.

That has two limits:

1. Runtime code imports individual constants directly, which couples engine behavior to storage format.
2. Creator tools cannot safely treat the current data layer as a stable authoring API.

Examples of this coupling:

- `world/chargen.py` imports class and race registries directly.
- `typeclasses/characters.py` imports progression and stat data directly.
- `world/questing.py` imports raw quest dictionaries directly.
- `typeclasses/scripts.py` imports encounter and enemy registries directly.
- `world/interactions.py` imports dialogue tables and supplements them with Python handlers.

## Target Architecture

### 1. Runtime / Content Boundary

Runtime code must stop depending on the storage details of content.

Instead of importing module globals such as `QUESTS` or `ABILITY_LIBRARY`, runtime code should ask the content registry for definitions by id or by collection.

Examples:

- `content.characters.get_class("warrior")`
- `content.characters.get_race("elf")`
- `content.quests.get("practice_makes_heroes")`
- `content.items.get("militia_blade")`
- `content.world.rooms()`

This boundary is the core enabling move for creator tooling.

### 2. Content Registry

The registry owns:

- loading source content
- exposing typed lookup methods
- cross-reference validation
- migration compatibility while old Python data still exists
- eventual support for JSON or YAML content packs

The registry should be the only place that knows whether content came from Python modules, JSON files, YAML files, or a future editor export.

### 3. Content Packs

Content should eventually live under a pack-oriented directory such as:

```text
brave_game/world/content/packs/
  core/
    races.json
    classes.json
    abilities.json
    items.json
    rooms.json
    exits.json
    entities.json
    quests.json
    enemies.json
    encounters.json
    dialogue.json
    activities.json
    portals.json
```

This shape is better for creator tools because it is declarative, serializable, diffable, and can be validated independently from runtime code.

### 4. Rule Language

A creator-friendly game cannot rely on arbitrary custom Python for common content behaviors.

Brave needs a small declarative rule model for:

- conditions: `quest_active`, `quest_completed`, `in_room`, `has_item`, `level_at_least`, `resource_below_max`
- effects: `grant_xp`, `grant_item`, `advance_objective`, `unlock_quest`, `start_encounter`, `set_flag`, `teleport`
- references: ids for rooms, items, quests, enemies, dialogue nodes, and scripted hook names

Where content cannot be expressed declaratively yet, content may point to a bounded engine hook such as `boss.greymaw_phase_shift` rather than embedding freeform code.

## Content Domains

The intended ownership split is:

### Engine-Owned

- Evennia typeclasses and persistence lifecycle
- combat tick loop and resolution sequencing
- quest state machine execution
- browser view composition
- inventory mutation, targeting rules, and stat recalculation algorithms
- validation framework and preview runtime

### Content-Owned

- world graph, map metadata, rooms, exits, zone tags
- NPCs, readables, vendors, interactables, trophies, portals
- races, classes, progression tracks, starter loadouts
- abilities, passive traits, enemies, encounter groups, loot tables
- quests, prerequisites, objectives, rewards, leads
- dialogue text and branching conversation data
- activities, recipes, and authored reward tables

## Creator Tool Requirements

Creator tools should target the registry and pack layer, not raw runtime modules.

The minimum tooling surface should include:

1. content validation
2. reference resolution
3. map editing
4. quest and dialogue editing
5. encounter preview
6. progression preview
7. safe export/import of content packs

Without validation and preview, creator tools will produce invalid content faster than code can absorb it.

## Migration Strategy

Brave should migrate in stages:

1. Introduce a registry that wraps current Python content.
2. Refactor runtime code to depend on the registry instead of direct module imports.
3. Add validation and reporting around content ids and references.
4. Move content domain by domain from Python modules to declarative pack files.
5. Build creator tooling against the registry-backed pack format.

This keeps the game playable during migration while steadily improving architecture.

## Current Implemented Seams

Brave now has live registry-backed seams for the core authored domains:

- `characters`
- `items`
- `quests`
- `world`
- `encounters`
- `dialogue`
- `systems`

Those domains now load from JSON pack files under `world/content/packs/core/` and are validated through `python -m world.content.build`.

The character registry currently wraps:

- races
- classes
- ability library
- implemented ability keys
- passive ability bonuses
- progression helper queries

This gives creator tooling a stable read model for progression, inventory, quest, world-graph, encounter, dialogue, and town-system authoring behind a single content boundary.
