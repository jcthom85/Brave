# Creator Tools And Combat Overhaul Plan

## Purpose

This document is the working handoff for the current Brave build as of April 4, 2026. It records what has already been built for creator tooling, what is still missing on the authoring side, and how that work should feed directly into the next major effort: replacing the current queued combat slice with a more expressive ATB-driven combat experience and a stronger combat UI.

The intent is to preserve momentum. Creator tooling should keep reducing content-authoring friction while combat moves from a functional vertical slice into a system that is clearer, more reactive, and better suited to long-term tuning.

## Current Snapshot

Brave already has:

- A data-driven content registry and JSON pack build flow.
- Browser creator editors for world, quests, dialogue, encounters, items, and character data.
- A creator command surface in-game through `content`.
- An authenticated creator API under `/api/content/...`.
- A live combat slice with class abilities, consumable use, combat browser views, and encounter-side execution handlers.

The main shift completed in the latest creator pass is that content mutation is no longer just "overwrite the pack and hope." There is now a content-layer safety seam for staged writes and operational recovery.

## What Has Been Completed

### 1. Data-Driven Creator Foundation

The content system is now centered on pack-based mutation rather than ad hoc edits. The current creator surface covers these domains:

- `world`: rooms, exits, entities
- `quests`
- `dialogue`: talk rules and static read responses
- `encounters`: enemies and room encounter tables
- `items`
- `characters`: races, classes, and character config
- `systems`: portals and forge recipes

This gives Brave a practical authoring path for the core fantasy ladder and future portal content without hardcoding every content change directly into Python modules.

### 2. Browser Creator Editors

The repo now contains browser editors and shared creator JS for:

- creator index
- world editor
- quest editor
- dialogue editor
- encounter editor
- item editor
- character editor

These editors already support browsing references, staging structured JSON payloads, previewing content, and writing through the shared API surface.

### 3. Command And API Surfaces

Brave now exposes two operator paths into the same content mutation layer:

- In-game command surface via `content`
- Web API under `/api/content/...`

Current command support includes:

- preview
- upsert
- remove
- history
- revert
- publish
- validate
- reload

Current API support includes:

- `GET /api/content/status`
- `GET /api/content/references/<domain>`
- `POST /api/content/preview`
- `POST /api/content/mutate`
- `POST /api/content/remove`
- `GET /api/content/history`
- `POST /api/content/revert`
- `POST /api/content/publish`
- `POST /api/content/validate`
- `POST /api/content/reload`

### 4. Operational Safety Layer

The most important recent improvement is the new content safety layer in `world.content.editor` and `world.content.history`.

Completed capabilities:

- Author-stamped writes through `_meta`.
- Per-write history snapshots stored as JSON entries.
- Stage-aware writes to `live` or `draft`.
- Revert by history entry ID.
- Publish from `draft` packs to `live` packs.

This is the correct seam for further creator expansion because it centralizes safety guarantees instead of pushing history/publish logic into each editor separately.

### 5. Validation And Regression Coverage

The creator stack already has focused regression coverage for:

- content command behavior
- creator API behavior
- content preview
- content registry
- content validation
- browser creator editors

That matters because the next phase will keep changing mutation surfaces. The contract is now testable.

## What Still Needs To Be Finished On Creator Tools

The creator layer is usable, but it is not done. The remaining work is mostly about making the tooling safer, easier, and more production-ready for content-heavy development.

### 1. Draft Workflow Needs A Real Operator Experience

The underlying draft/live seam exists, but the user-facing workflow is still thin.

Still needed:

- Clear visual draft/live indicators in every creator editor.
- A domain-level "dirty draft" status view.
- Diff presentation that is readable in-browser, not just raw unified diff output.
- Publish confirmation flow with validation summary before live write.
- Better draft cleanup rules after publish or abandon.

### 2. History Needs Better Inspection Tools

History exists as raw JSON snapshots, which is enough for recovery but not enough for smooth daily use.

Still needed:

- A browser history screen with filters by domain, stage, author, and target.
- Snapshot comparison tools.
- "Show me what this revert would do" preview in the web UI.
- Human-readable change summaries on top of raw diffs.
- Retention and archival rules so history does not become unmanaged noise.

### 3. Access Control Needs To Keep Getting Sharper

The browser and API gate now require an authenticated staff, superuser, or `Developer`-authorized account, which closes the biggest early exposure in the creator stack.

Still needed:

- Align API auth with documented creator access rules.
- Distinguish read-only access from write/publish/revert permissions.
- Log author, action, and stage consistently for auditability.

### 4. Editor Polish And Coverage Gaps

The current editors are functional, but they still behave like first-generation tools.

Still needed:

- Better field validation before raw JSON generation.
- Stronger schema guidance and helper text for complex payloads.
- Shared affordances for clone, duplicate, and create-from-template flows.
- Safer delete UX.
- A full systems editor pass for portal and forge content.
- Better support for cross-domain authoring tasks such as "create room + encounter + quest hook" without jumping through multiple screens manually.

### 5. Content Build Integration

The mutation layer can write packs, validate them, and reload the in-process registry, but the long-term workflow should be more explicit.

Still needed:

- A standard draft-to-build-to-publish checklist.
- A visible warning when live data and draft data diverge.
- Better handling of build failures or cross-domain validation failures after publish attempts.
- A documented backup/recovery path for pack corruption or bad live publishes.

## Current Combat Baseline

The current combat slice is working, but it is still a first-generation system.

### What Exists Now

The existing combat model already has:

- `fight`, `attack`, `use`, and `flee` command surfaces.
- Encounter scripts that manage participants and enemy state.
- Implemented class-ability execution handlers in `world/combat_execution.py`.
- Browser action payloads in `world/combat_actions.py`.
- A sticky combat browser view in `world/browser_views.py`.
- A companion combat panel in `world/browser_panels.py`.
- Regression coverage around combat view and panel behavior.

### How It Currently Behaves

The current flow is effectively a queued round model:

- The player joins or starts a room encounter.
- Actions are queued by command or browser buttons.
- The UI exposes abilities, items, party state, enemies, and flee.
- Combat text and state updates are handled through the encounter script plus execution helpers.

This is good enough for a vertical slice, but it still has several structural limitations:

- Combat pacing is discrete and blunt rather than fluid.
- Urgency and turn pressure are mostly implied rather than felt.
- Targeting and feedback are readable, but not yet dramatic or high-signal.
- Encounter state is present, but the UI is not yet centered on timing windows, cast pressure, or battlefield momentum.

## Why ATB Is The Right Next Combat Step

The combat docs already point toward short-tick, party-friendly, timing-driven combat. ATB is a good fit for Brave because it can preserve readability while making class timing, interrupts, support windows, and enemy pressure feel more alive.

ATB is the right next step if it is implemented with restraint:

- It should create pressure, not chaos.
- It should improve class identity, not bury it.
- It should make support and control more rewarding.
- It should remain legible in text and browser UI.

The goal is not "real-time for its own sake." The goal is a combat rhythm where players feel windows opening and closing, especially in co-op.

## Combat Overhaul Goals

The combat overhaul should target four outcomes at once:

### 1. Better Simulation Rhythm

- Move from queued round feel to short-tick ATB pressure.
- Give every actor a visible readiness or action timeline.
- Support interruption, stagger, haste, slow, recovery, and windup effects cleanly.

### 2. Stronger Class Identity

- Warrior should own interception, guard timing, and threat control.
- Cleric and Druid should feel predictive and reactive, not just "heal when HP is low."
- Ranger, Rogue, and Mage should live on timing windows, target setup, and burst moments.
- Paladin should bridge defense and support with visible tempo impact.

### 3. Better Encounter Design Space

- Enemy roles should differ by timing pattern, not just stats.
- Elites and bosses should telegraph meaningful actions.
- Support and caster enemies should create must-answer moments.
- Encounter difficulty should come from pressure shape and coordination load, not spam.

### 4. Better Combat UX

- The main combat view should communicate urgency immediately.
- Important enemy windups and ally danger states must be impossible to miss.
- Action choice must be fast on desktop and mobile.
- The output log and the browser UI must reinforce each other instead of competing.

## Proposed ATB Implementation Plan

This should be built in phases. Do not try to jump directly from the current combat slice to a fully cinematic boss engine.

### Phase 1. Establish The ATB Core

Build the simulation layer first.

Scope:

- Add per-actor ATB gauges or readiness values.
- Advance gauges on a short server tick.
- Define action states such as ready, winding_up, resolving, recovering, interrupted.
- Move basic attacks, abilities, and items onto the same timing model.
- Preserve deterministic-enough state transitions for tests.

Definition of done:

- A simple fight can run entirely through ATB timing.
- Actors can become ready at different speeds.
- Slow, haste, stagger, and interruption have a stable technical model.

### Phase 2. Port Existing Ability Logic

Once ATB exists, migrate current ability handlers onto it.

Scope:

- Keep the existing class ability list as the starting content set.
- Add timing metadata to abilities: cast time, recovery time, interruptibility, cooldown behavior, readiness effects.
- Update enemy behavior to select actions with timing awareness.
- Keep damage/heal formulas readable while timing is changing.

Definition of done:

- Existing class kits still function.
- Ability timing is now visible and meaningful.
- Encounters can be won and tested end-to-end under ATB.

### Phase 3. Add Telegraphs And Reaction Windows

This is the layer that makes ATB feel good rather than merely different.

Scope:

- Telegraph enemy specials before they resolve.
- Surface interruptible casts, guard windows, and protect/taunt opportunities.
- Add visible recovery windows after heavy actions.
- Support boss and elite patterns built around readable timing tells.

Definition of done:

- Players can react to specific enemy actions instead of only watching HP bars.
- Control and support tools gain real tactical value.

### Phase 4. Rebuild The Combat UI Around Timing

The current combat view is a solid baseline, but it is still a list-first command launcher. The ATB system needs a timing-first interface.

Scope:

- Add a visible timeline or readiness rail for allies and enemies.
- Promote enemy telegraphs and imminent ally danger into top-priority UI space.
- Separate "ready now" actions from "currently unavailable" actions more clearly.
- Improve target selection UX for multi-target encounters.
- Make the combat panel and the main combat view tell one coherent story.
- Ensure the same model works on mobile without burying critical timing data.

Definition of done:

- A player can understand who is about to act, who is in danger, and what they can do next at a glance.
- The combat UI feels faster and clearer than typed-command-only combat.

### Phase 5. Combat Experience And Presentation Pass

After mechanics and UI stabilize, improve feel and readability.

Scope:

- Rewrite combat log output around key moments and result clarity.
- Add stronger scene messaging for telegraphs, interrupts, guard saves, crits, and finishing blows.
- Improve transition states for fight start, victory, defeat, and flee.
- Tune sound/reactive UI hooks around combat state.
- Reduce noise and repetition in long fights.

Definition of done:

- Combat is easier to follow in 1-player and family co-op sessions.
- The system feels deliberate, not merely technical.

## Combat UI And Experience Overhaul Priorities

This work should not wait until ATB is fully complete. Some UX improvements can start early as long as they align with the timing-first target.

Priority list:

1. Introduce a combat information hierarchy.
   Most urgent events first: incoming dangerous action, ally at risk, your ready action, encounter outcome shift.

2. Redesign the action deck.
   Actions should show readiness, cost, cast/recovery, target rules, and disabled reasons clearly.

3. Add timeline-focused combat chrome.
   The player needs to see who is charging, who is recovering, and when their own window opens.

4. Upgrade target readability.
   Enemy priority, marked targets, vulnerable targets, and interrupt targets should be visually distinct.

5. Improve mobile combat ergonomics.
   ATB on mobile will fail if action choice, target choice, and threat awareness require too much scrolling.

6. Tighten combat text.
   The log should support the UI by emphasizing action, target, and result with minimal filler.

## Dependencies Between Creator Work And Combat Work

These projects are linked.

Creator tooling needs to keep moving because the combat overhaul will increase content volume and tuning complexity:

- Abilities will need richer metadata.
- Enemies will need timing profiles, telegraphs, and behavior data.
- Encounters will need more authored structure than simple room enemy lists.
- Bosses will need explicit scripted beats without returning to hardcoded chaos.

That means the creator roadmap should prepare for combat authoring, not just static world content.

Creator-side work that specifically supports combat overhaul:

- Extend character content editing for richer ability metadata.
- Extend encounter editing for telegraphs, behavior patterns, and timing tags.
- Add better enemy authoring support for role, speed, cast profile, and interrupt rules.
- Add preview/debug tools for combat data before live publish.

## Recommended Next Sequence

The order below keeps momentum while protecting the live slice.

### Immediate

- Tighten creator API authorization.
- Finish draft/live visibility and publish UX.
- Add history inspection and diff usability in the browser.
- Define the ATB data model before touching too many combat handlers.

### Near-Term

- Implement ATB simulation primitives and tests.
- Port current combat actions onto the new timing system.
- Add encounter telegraph support.
- Extend creator data structures needed for combat timing metadata.

### After ATB Is Stable

- Rebuild the combat browser experience around timing and reaction windows.
- Tune class kits around timing identity rather than just effect lists.
- Upgrade encounter authoring for elites, bosses, and portal combat variants.
- Run a readability and pacing pass on combat logs, mobile interaction, and co-op flow.

## Working Rules For The Next Phase

- Do not discard the current combat slice until the ATB path is playable end-to-end.
- Keep combat simulation and presentation separated so the UI can evolve quickly.
- Keep creator safety guarantees at the content layer, not duplicated in each editor.
- Prefer data-driven timing and enemy behavior over hardcoded one-off boss logic.
- Treat combat readability as a core feature, not a final polish task.
- Keep family co-op as the bar for success: readable, reactive, and not exhausting.

## End State To Aim For

When this plan is complete, Brave should have:

- A stable creator workflow with draft, history, revert, publish, and strong validation.
- Enough browser editing coverage to author and tune most phase-1 content without raw file surgery.
- An ATB combat engine that supports readable timing pressure and meaningful class response windows.
- A combat UI that is fast, dramatic, and legible on both desktop and mobile.
- A combat experience strong enough to justify the larger progression, portal, and boss overhaul that comes after it.
