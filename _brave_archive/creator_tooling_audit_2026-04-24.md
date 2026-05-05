# Brave Creator Tooling Audit - 2026-04-24

## Overall Findings

The creator surfaces are useful, but most still expose the underlying pack format too directly. They were built around safe mutation and validation first, so they lean on raw payloads, diff output, and "sync to JSON" language. Brave now has richer systems: room maps, roaming parties, activities, fishing, tinkering, cooking, class abilities, passive icons, dialogue gates, portals, and encounter metadata. The tools need to become builder-first editors with advanced source available only when needed.

Common updates needed across all editors:

- Replace "JSON", "payload", "dry-run", "registry", and "domain" language in primary UI with creator-facing terms.
- Hide raw source behind an explicit advanced section.
- Keep change previews available, but do not make diffs the main screen.
- Add save-preview-validation flow that reads like content authoring, not API testing.
- Add richer pickers for cross-content references instead of requiring typed ids.
- Add summaries of what changed and what validation found.
- Split large all-in-one pages into focused work areas or tabs.
- Add browser-level smoke tests for each creator surface.

## World Editor

Current state:

- Has a room graph with region filter, drag positioning, connect mode, and visual issue reporting.
- Now has builder-first room fields and advanced source hidden by default.
- Still uses a single large page for rooms, exits, entities, graph, activity, and source.

Needed next:

- Add true "new room" creation from the graph.
- Add two-way exit creation and direction-pair controls.
- Add bulk move and multi-select for region reshaping.
- Add templates for common room/entity types.
- Add richer entity fields: gender, dialogue target, vendor data, portal target, readable text link.
- Add graph overlays for encounters, quest objectives, vendors, readables, portals, and roaming parties.

## Quest Editor

Current state:

- Has structured fields for a limited quest shape.
- Still shows raw quest payload as a first-class panel.
- Only covers a small number of objective/reward patterns cleanly.

Data drift and gaps:

- Quest flow now depends heavily on prerequisites, starting quest membership, region grouping, item rewards, and room objectives.
- The editor should support all objective types in the live pack, not only the initial common path.
- It needs better prerequisite visualization and quest-chain ordering.

Needed updates:

- Add a quest-chain view by region.
- Replace raw objective editing with repeatable objective cards.
- Add objective type-specific forms for visit room, collect item, talk/read/activity/combat-style objectives as supported by content.
- Add reward cards for items, silver, flags, trophies, recipes, and unlocks if present in current systems.
- Hide raw quest source behind advanced mode.

## Dialogue Editor

Current state:

- Edits talk rules and readable responses for entities.
- Uses entity picker and room/quest gates, but still requires syncing lists to source.

Data drift and gaps:

- NPCs now rely on gender validation, resonance, quest activity, room gates, readable signs, and stronger narrative branching.
- The editor does not clearly separate NPC dialogue from readable text authoring.

Needed updates:

- Split into "NPC Lines" and "Readable Text" modes.
- Add ordered rule cards with condition labels.
- Add preview of which rule would fire for selected quest/room/resonance state.
- Add entity-kind guardrails so readable tools do not appear for NPCs and talk tools do not appear for readables unless intentionally overridden.
- Hide raw rule arrays behind advanced mode.

## Encounter Editor

Current state:

- Edits room encounter tables and enemy templates.
- Does not expose roaming parties or newer encounter metadata as a first-class workflow.

Data drift and gaps:

- Encounters now include room tables, enemy templates, temperament labels/overrides, roaming parties, loot, rank, tags, gender, XP, and region consistency.
- The editor cannot create or review roaming party behavior.

Needed updates:

- Add tabs for Room Encounters, Enemy Templates, Roaming Parties, and Temperaments.
- Add enemy stat cards instead of raw stat/loot fields.
- Add loot item picker and drop-rate controls.
- Add encounter balance preview: enemy count, total XP, rank spread, likely temperament.
- Add region/start-room validation inline for roaming parties.

## Item Editor

Current state:

- Has common fields for item templates but still exposes bonuses, restore, meal bonuses, and use profile as raw JSON textareas.

Data drift and gaps:

- Items now drive equipment, meals, forge/cooking/tinkering unlocks, fishing gear, class-gated study/bond/vow behavior, restore effects, buffs, starter loadouts, and quest links.
- The editor cannot comfortably author those uses without knowing the schema.

Needed updates:

- Replace JSON bonus editors with stat rows.
- Add use-profile templates: consumable, meal, recipe unlock, class unlock, fishing tool, equipment.
- Add class/race/item/recipe pickers where use profiles reference other systems.
- Add starter loadout and starter consumable editing or link to a dedicated loadout view.
- Hide advanced source by default.

## Character Editor

Current state:

- Edits classes, races, and character config.
- Progression, stats, race bonuses, perk effects, primary stats, vertical-slice classes, and XP ladder are still raw JSON fields.

Data drift and gaps:

- Character content now includes implemented abilities, passive bonuses, icon roles, ability classifications, class progression, race perks, defaults, starter loadouts, and level caps.
- The current editor does not help creators understand whether a progression entry is an action, passive, or unknown.

Needed updates:

- Add progression rows with level, ability, resolved type, and validation state.
- Add ability library/passive editor or at least a linked inspector.
- Add stat controls for base stats and race bonuses.
- Add icon-role picker using allowed roles from validation.
- Add XP ladder controls and vertical-slice class picker.
- Hide raw class/race/config source by default.

## Creator Index

Current state:

- Lists editor links.

Needed updates:

- Add status cards showing validation state, last content reload, and changed domains.
- Rename sections into creator language: World Builder, Quest Lines, Conversations, Encounters, Items, Characters.
- Add direct links to docs only as secondary help, not primary workflow.

## Recommended Order

1. Finish World Builder: new rooms, two-way exits, entity authoring, graph overlays.
2. Update Item Builder: remove raw bonus/use JSON from default workflow.
3. Update Encounter Builder: add roaming parties and enemy template cards.
4. Update Quest Builder: objective/reward cards and chain view.
5. Update Dialogue Builder: rule cards and firing preview.
6. Update Character Builder: progression rows and ability/passive awareness.
7. Polish creator index and shared language.
