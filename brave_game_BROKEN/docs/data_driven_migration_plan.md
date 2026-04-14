# Data-Driven Migration Plan

## Objective

Move Brave from Python-module content registries toward a registry-backed, tool-friendly content system without breaking the live game loop.

## Phase 1: Registry Boundary

Purpose: create a stable API between runtime code and authored content.

Tasks:

- add `world.content.registry` as the canonical content access layer
- wrap existing Python datasets behind typed registry classes
- update runtime consumers to use registry methods instead of direct module-global imports
- keep old `world.data.*` modules temporarily as storage backends only

Exit criteria:

- at least one major content domain is consumed through the registry
- runtime code no longer needs to know where that domain is stored

## Phase 2: Validation Layer

Purpose: make content safe to author outside runtime code.

Tasks:

- define canonical ids and reference rules
- add validation commands and regression tests
- detect duplicate ids, missing references, invalid prerequisites, orphaned rooms, invalid loot references, and broken dialogue targets

Exit criteria:

- content validation runs in tests before bootstrapping the world
- broken content fails fast with readable errors

## Phase 3: Pack Format

Purpose: move authored content out of Python modules.

Tasks:

- choose JSON as the primary machine-authored format
- add pack manifests and per-domain files
- teach the registry to load from pack files
- keep compatibility importers for legacy Python data during transition

Exit criteria:

- the main authored domains load from content pack files rather than `world.data.*`
- `characters`, `items`, `quests`, `world`, `encounters`, `dialogue`, and `systems` are live pack-backed domains
- `world.content.build` is the canonical validation entrypoint for local checks and CI

## Phase 4: Tooling Foundation

Purpose: provide a safe substrate for creator tools.

Tasks:

- add editor-facing CRUD APIs for rooms, exits, quests, dialogue, and encounters
- add preview helpers for map traversal, quest progression, and combat setups
- add serialization and diff helpers for content changes

Exit criteria:

- a tool can create or edit a room, quest, and NPC interaction without hand-editing runtime modules

## Recommended Domain Order

1. character content
2. items
3. world graph
4. enemies and encounters
5. quests
6. dialogue and interactions
7. activities and portals

This order keeps the early migration focused on stable catalogs first, then moves into richer authored behavior.

## Engineering Rules During Migration

- runtime code must import the registry, not raw content modules, for migrated domains
- content ids must be stable and explicit
- declarative content should be preferred over custom Python handlers
- custom scripted hooks must be bounded, named references rather than arbitrary inline code
- new creator tooling should only target registry-backed content domains

## Immediate Follow-Up Work

After this pass, the next useful steps are:

1. expand validation to cover encounter balance, orphaned references, and dialogue targets more deeply
2. add content diff/export helpers on top of the pack layout
3. build the first editor around room graph, quest authoring, encounter placement, dialogue editing, and town systems
4. add preview flows for encounter authoring, combat balancing, and shop/forge outcomes
5. split the broad systems domain into more editor-focused subdomains if the tool surface starts demanding it
