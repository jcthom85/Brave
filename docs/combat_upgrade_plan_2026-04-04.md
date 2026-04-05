# Combat Upgrade Plan

## Purpose

This document is the dedicated handoff for Brave's combat-system upgrade path as of April 4, 2026. It exists so a future chat can pick up the combat work directly without reconstructing context from scattered commits, status messages, or broader creator-tool planning docs.

This is the canonical answer to:

- what the old combat model was
- what has already been upgraded
- what is currently live
- what should be built next
- what order the remaining combat work should happen in

## Design Target

Brave is moving from a simple queued-round combat slice into a short-tick ATB combat model with:

- readable timing pressure
- class-specific reaction windows
- explicit enemy telegraphs
- stronger party coordination
- a browser combat UI that shows urgency clearly

The goal is not speed for its own sake. The goal is readable, dramatic, family-playable combat where timing matters and the player can understand what is happening at a glance.

## Old Combat Baseline

Before the current upgrade pass, Brave combat behaved like this:

- `fight`, `attack`, `use`, and `flee` fed intent into `pending_actions`
- the encounter script advanced on a fixed repeat
- each cycle resolved player actions in order
- then enemies acted
- the combat UI showed actions, party, enemies, and consumables
- timing pressure was mostly implied, not mechanically explicit

That model was good enough for a vertical slice, but it had clear limits:

- no real readiness pacing
- no meaningful windup/recovery state
- no explicit telegraphed enemy pressure
- no visible reaction windows
- UI showed choices, but not tempo

## What Is Already Completed

### 1. ATB Timing Profile Layer

Completed in [combat_atb.py](/home/jcthom85/Brave/brave_game/world/combat_atb.py).

This layer now provides:

- normalized ATB profiles for abilities
- normalized ATB profiles for combat items
- default timing fields like:
  - `gauge_cost`
  - `windup_ticks`
  - `recovery_ticks`
  - `cooldown_ticks`
  - `interruptible`
  - `telegraph`
  - `target_locked`
- pure helper functions for state progression:
  - create state
  - tick state
  - start action
  - finish action

This module is intentionally pure so combat timing can be tested without dragging the full encounter script into every test.

### 2. Combat Payload Timing Metadata

Completed in [combat_actions.py](/home/jcthom85/Brave/brave_game/world/combat_actions.py).

Combat actions now carry timing metadata for:

- abilities
- combat consumables

That means the browser layer can reason about action timing without hardcoding ability-by-ability timing rules inside the UI.

### 3. Encounter-Level ATB State

Completed in [scripts.py](/home/jcthom85/Brave/brave_game/typeclasses/scripts.py).

`BraveEncounter` now maintains per-actor ATB state for:

- player participants
- enemies

The encounter now tracks timing phases such as:

- charging
- ready
- winding
- resolving
- recovering
- cooldown

Important behavior change:

- `pending_actions` is no longer the whole combat state
- `pending_actions` is now intent storage that gets consumed when the actor becomes ready

This is the key architectural shift from round queue to timing engine.

### 4. Enemy ATB Participation

Completed in [scripts.py](/home/jcthom85/Brave/brave_game/typeclasses/scripts.py).

Enemies now also move through ATB timing instead of acting automatically every encounter cycle. That means enemy pressure is no longer just "all enemies go now." It can now be shaped by fill rate, windup, recovery, and named telegraphs.

### 5. Combat UI Timing Surface

Completed in:

- [browser_views.py](/home/jcthom85/Brave/brave_game/world/browser_views.py)
- [browser_panels.py](/home/jcthom85/Brave/brave_game/world/browser_panels.py)

The combat browser UI now exposes:

- ATB meters for party members
- ATB meters for enemies
- timing chips such as ready, winding, recovering, cooldown
- better enemy pressure language in card text
- compact ATB badges in the companion rail panel

This means the player can now see tempo rather than only infer it from action output.

### 6. Named Enemy Telegraphs

Completed in [scripts.py](/home/jcthom85/Brave/brave_game/typeclasses/scripts.py) and surfaced in [browser_views.py](/home/jcthom85/Brave/brave_game/world/browser_views.py).

Selected enemies and bosses now have named windup actions such as:

- `Brush Pounce`
- `Reed Ambush`
- `Aimed Shot`
- `Clamp Burst`
- `Funeral Charge`
- `Overcharge Arc`
- `Execution Cut`
- `Cauldron Rush`
- `Blackwater Flare`

These telegraphs currently do two things:

- emit a visible combat message when windup starts
- show the named telegraph in the enemy card while winding

This is the first real reaction seam in the system.

### 7. Regression Coverage

Focused regression coverage now exists for:

- ATB timing profile helpers
- ATB state progression
- encounter loop ATB advancement
- combat actions
- combat browser view
- combat panel
- flee behavior

Relevant files include:

- [test_combat_atb.py](/home/jcthom85/Brave/brave_game/regression_tests/test_combat_atb.py)
- [test_combat_atb_loop.py](/home/jcthom85/Brave/brave_game/regression_tests/test_combat_atb_loop.py)
- [test_combat_actions.py](/home/jcthom85/Brave/brave_game/regression_tests/test_combat_actions.py)
- [test_combat_view.py](/home/jcthom85/Brave/brave_game/regression_tests/test_combat_view.py)
- [test_combat_panel.py](/home/jcthom85/Brave/brave_game/regression_tests/test_combat_panel.py)
- [test_combat_flee.py](/home/jcthom85/Brave/brave_game/regression_tests/test_combat_flee.py)

## What Is Live Right Now

As of this document:

- combat is no longer conceptually round-only
- ATB state exists in the encounter loop
- player intent is resolved when the actor becomes ready
- enemies can wind up named actions
- the browser UI exposes readiness and telegraph state

What is not yet true:

- telegraphed enemy actions are not meaningfully countered by player mechanics yet
- player abilities do not yet interrupt, redirect, or soften enemy windups in a dedicated ATB reaction model
- timing-aware balance and encounter tuning have barely started
- the combat UX is improved, but not yet restructured around reaction windows as a first-class play pattern

## Current Combat Architecture

### Core Runtime Pieces

- [scripts.py](/home/jcthom85/Brave/brave_game/typeclasses/scripts.py)
  Main encounter loop, ATB state, enemy execution, player resolution.

- [combat_atb.py](/home/jcthom85/Brave/brave_game/world/combat_atb.py)
  Pure timing profiles and ATB state helpers.

- [combat_actions.py](/home/jcthom85/Brave/brave_game/world/combat_actions.py)
  Browser-facing combat action payloads, now with timing metadata.

- [combat_execution.py](/home/jcthom85/Brave/brave_game/world/combat_execution.py)
  Class ability execution handlers.

- [browser_views.py](/home/jcthom85/Brave/brave_game/world/browser_views.py)
  Main combat browser view.

- [browser_panels.py](/home/jcthom85/Brave/brave_game/world/browser_panels.py)
  Companion panel / rail summary.

### Important Current Constraint

The system is mid-migration.

That means:

- parts of combat still reflect the old queue model
- parts now reflect the new ATB model
- the next work should continue migrating behavior to timing-aware reactions without trying to rewrite everything at once

## Immediate Next Phase

The next high-value step is:

## Phase A: Reaction Mechanics

Telegraphs matter only if players can answer them.

This phase should add real responses to enemy windups.

### Goals

- let specific player tools respond to telegraphs
- make timing choices tactically meaningful
- reward role identity through reactions

### Planned Mechanics

#### Interrupts

Add the ability for certain actions to cancel or degrade enemy windups.

Likely early candidates:

- `Shield Bash`
- `Cheap Shot`
- `Frost Bind`
- `Entangling Roots`

Desired outcomes:

- interruptible telegraphs can be stopped if answered in time
- failed or late responses still leave useful partial value when appropriate

#### Guard / Intercept Reactions

Allow defensive tools to answer incoming telegraphs by redirecting or reducing them.

Likely early candidates:

- `Intercept`
- `Defend`
- `Brace`
- `Guarding Aura`
- `Shield of Dawn`

Desired outcomes:

- tanks and protectors can respond to visible danger windows
- not every answer needs to be “cancel the cast”; some should be “survive the hit cleanly”

#### Cleanse / Safety Windows

Some telegraphed attacks should apply effects that support classes can anticipate and answer.

Likely early candidates:

- `Cleanse`
- `Renewing Light`
- `Blessing`
- `Living Current`

Desired outcomes:

- support play becomes predictive instead of purely reactive HP topping
- telegraphs create party coordination decisions

### Definition Of Done

This phase is done when:

- at least a few player actions can meaningfully answer enemy windups
- enemy telegraphs are no longer just cosmetic
- the encounter loop can apply at least:
  - interrupted
  - mitigated
  - redirected
  - unanswered
  outcomes to telegraphed actions

## Phase B: Enemy Telegraph Expansion

Once the reaction seam exists, extend telegraphs beyond the first named set.

### Goals

- give more enemies meaningful timing identities
- make elites and bosses more readable and more distinct

### Planned Work

- add more named telegraphs for enemy specials
- separate normal basic attacks from high-pressure telegraphed actions
- give support/caster enemies clearer timing patterns
- ensure bosses use repeated readable motifs instead of random spikes

### Definition Of Done

- every important elite and boss has at least one real telegraphed action
- enemy timing patterns are recognizable after a few turns

## Phase C: Player Ability Timing Pass

Right now the timing profiles exist, but class kits have not been deeply tuned around them.

### Goals

- make classes feel different in rhythm, not only in effects
- make “fast”, “heavy”, “setup”, and “save” actions legible

### Planned Work

- revisit ability windup, recovery, and cooldown values
- define which abilities are:
  - instant
  - telegraphed
  - interruptible
  - setup tools
  - payoff tools
- shape class tempo identities:
  - Warrior: control and interception tempo
  - Cleric: save windows and answer timing
  - Ranger: steady pressure with occasional setup shots
  - Mage: telegraphed burst and field pressure
  - Rogue: fast punish windows
  - Paladin: protect-and-answer hybrid
  - Druid: flexible control and sustain timing

### Definition Of Done

- each class has a visible combat rhythm
- timing choices are part of class identity, not just damage tuning

## Phase D: Encounter And Boss Tuning

After reactions and class timing exist, tune real encounters around them.

### Goals

- make fights readable and satisfying
- make bosses teach counterplay instead of relying on raw stat inflation

### Planned Work

- revisit first-hour encounters
- tune enemy fill rates and telegraph lengths
- define “must answer”, “can soak”, and “can race” mechanics intentionally
- make boss patterns support role expression

### Priority Targets

- Old Greymaw
- Sir Edric Restless
- Foreman Coilback
- Captain Varn Blackreed
- Grubnak the Pot King
- Hollow Lantern
- Miretooth

### Definition Of Done

- boss fights feel authored around timing windows
- telegraphs are readable
- player counterplay matters

## Phase E: Combat UI Rebuild

The current UI now exposes timing data, but it still largely uses the old list-first layout.

### Goals

- make timing the visual center of combat
- reduce scanning cost
- improve clarity on desktop and mobile

### Planned Work

- add a clearer combat timeline/readiness rail
- distinguish telegraphs, recoveries, and safe windows visually
- group high-priority alerts above routine data
- improve target highlighting for imminent threats
- make reaction actions easier to access during pressure
- keep typed command compatibility intact

### Definition Of Done

- a player can identify the next important event immediately
- reaction opportunities are obvious
- the combat screen feels built around tempo instead of retrofitted with tempo

## Phase F: Creator Support For Combat Authoring

Combat upgrades will increase tuning data and authored behavior needs.

### Goals

- let creator tools support timing-aware combat data

### Planned Work

- expose combat timing metadata in character editor surfaces
- extend encounter authoring for telegraphs, timing rules, and enemy behavior tags
- add safer preview tools for combat data changes
- ensure combat content remains data-driven rather than moving back toward one-off Python hardcoding

### Definition Of Done

- future combat tuning does not require manual file surgery for common timing changes

## Recommended Execution Order

If another chat picks this up, the recommended order is:

1. Implement reaction mechanics for telegraphs.
2. Expand enemy telegraphs and classify which are interruptible vs mitigatable.
3. Run the player ability timing pass.
4. Tune key encounters and bosses around timing.
5. Rebuild the combat UI around reaction windows and priority alerts.
6. Extend creator tooling to support richer combat authoring data.

## Practical Rules

- Do not rip out typed command support.
- Do not rewrite every ability at once.
- Do not convert every enemy into a boss-style mechanic pile.
- Prefer a few strong reaction patterns over many weak gimmicks.
- Keep ATB readable in 4-player family sessions.
- Treat combat readability as a feature, not polish.

## Current Risks

- Mid-migration hybrid state can create confusing edge cases if round-era assumptions remain in old helper code.
- Telegraphs without counters will feel theatrical but shallow.
- Too many telegraphs too quickly will create noise instead of tactics.
- UI work can drift into decoration if it stops being anchored to real encounter logic.

## Good Next Prompt For Another Chat

If you want another chat to continue this work, use something close to:

> Continue the Brave combat upgrade plan from `docs/combat_upgrade_plan_2026-04-04.md`. The current system already has ATB timing profiles, encounter-level ATB state, combat UI ATB meters/chips, and named enemy telegraphs. The next task is Phase A: implement real reaction mechanics for telegraphed enemy actions, starting with interrupts and guard/intercept responses, while preserving the current command surface and regression coverage.
