# Lantern Rest Arcade Plan

This document defines how the arcade cabinet in `The Lantern Rest Inn` should evolve from a simple browser minigame into a full-featured ASCII arcade experience with strong Pac-Man DNA.

It is intentionally a design document, not an implementation log.

## Goal

Turn Joss's cabinet into a game that feels:
- authentic
- readable
- replayable
- score-chaseable
- unmistakably `Brave`

The target is not "generic maze game."

The target is "this feels like a real arcade cabinet in a text-first fantasy MUD."

## Scope Rule

Do not solve this cabinet by layering novelty on top of weak fundamentals.

The priority order is:
1. movement feel
2. ghost behavior
3. scoring depth
4. presentation polish
5. Lantern Rest flavor

If the first two are wrong, the rest will not matter.

## Current State

The current live slice is a good prototype, but it is still closer to a lightweight maze chaser than to a full arcade game.

Today it has:
- one small fixed maze
- two ghosts
- simple chase behavior
- dots only
- one board-clear bonus
- a local leaderboard
- one cabinet prize

That prototype proved the loop works.

The next step is not to add random extras. The next step is to make the underlying arcade grammar feel right.

## Core Decision

The cabinet should be **ASCII-first at the gameplay surface**.

That means:
- the maze is ASCII
- the player is ASCII
- the ghosts are ASCII
- pellets, power pellets, fruit, lives, and score readouts are ASCII

Material Symbols can still be used in the surrounding `Brave` browser UI for:
- menu entries
- section headers
- action buttons
- view chrome

Material Symbols should **not** be used inside the cabinet playfield itself.

The cabinet should also have its own mobile interaction model.

It should not inherit the standard room or exploration mobile shell by default.

## Why ASCII Wins

The cabinet is strongest when it looks like:
- an old terminal machine
- a fantasy-world arcade oddity
- a black-glass score-chaser built out of text and glow

If icons replace core gameplay glyphs, the illusion weakens fast.

ASCII gives the game:
- stronger identity inside the existing webclient
- lower visual noise
- better coherence with the MUD's text-first presentation
- easier palette and animation control
- a more memorable "Joss built a weird impossible cabinet" vibe

## Material Symbols Policy

### Use Material Symbols For

- `Play`, `Scores`, `Quit`, and other action buttons outside the game field
- cabinet list and menu cards
- surrounding browser view framing
- help and metadata panels

### Do Not Use Material Symbols For

- pellets
- power pellets
- ghosts
- Pac-Man stand-in
- fruit or bonus items inside the maze
- life icons rendered in the active cabinet HUD

### Preferred Hybrid Model

Use Material Symbols for the shell.

Use ASCII for the game.

That keeps the larger `Brave` UI consistent without making the cabinet feel like a modern app widget.

## Design Pillars

### Pillar 1: Authentic Movement

The game should feel sharp, not floaty.

Requirements:
- buffered turning
- clean cornering
- fixed tile logic
- side tunnels
- predictable movement timing
- immediate read on what direction the player intends

If movement is sloppy, the game will never feel authentic no matter how good the art is.

### Pillar 2: Authentic Ghost Behavior

Ghost personality is the heart of the design.

The cabinet should move from "all enemies chase the player" to a real ghost-state system:
- chase
- scatter
- frightened
- eyes returning home
- release timing from the ghost house

Each ghost should feel different.

The game becomes memorable when the player starts recognizing behavior patterns instead of just reacting to random pursuit.

### Pillar 3: Score-Chasing Depth

The run should support arcade mastery, not just survival.

Required score sources:
- pellets
- power pellets
- frightened ghost combo chain
- fruit or bonus items
- level clear
- extra-life thresholds

Players should be able to improve because they got better, not because they got lucky.

### Pillar 4: Cabinet Theater

The cabinet should feel theatrical.

That means:
- title or attract state
- `READY!` state
- death state
- clear state
- top-score celebration
- prize-drawer drama

The cabinet should feel like an event in the room, not just a hidden browser toy.

### Pillar 5: Lantern Rest Flavor

The game should absolutely feel arcade-authentic, but the wrapping should still belong to `Brave`.

The inn and Joss should shape:
- cabinet naming
- prize rewards
- room reactions
- bonus-item theming
- secret unlocks

The core loop should be classic.

The flavor layer should be local.

## Authentic Feature Set

### Required For Version 1

- one iconic maze tuned for good pathing
- four ghosts with distinct behavior
- power pellets
- frightened mode
- frightened ghost combo scoring
- ghost house and release rules
- side tunnels
- lives
- extra life threshold
- level progression
- fruit or bonus item spawn
- start sequence
- death sequence
- board clear sequence
- local high score table

### Strongly Recommended

- attract mode demo when idle
- initials or short-name high score entry feel
- level markers
- subtle difficulty escalation tables
- a hidden hard mode or `Joss Remix`
- roomwide broadcast on a new local top score

### Optional Later

- intermission-style cabinet scenes
- variant mazes
- daily challenge board
- seasonal cabinet skins
- multiplayer relay scoring

## ASCII Presentation Rules

The cabinet must remain legible at a glance.

### Maze

Allowed approaches:
- `#` walls for maximum simplicity
- `+`, `-`, `|` wall language for cleaner geometry
- box-drawing as an optional richer presentation if there is a safe fallback

The maze should not become decorative clutter.

### Player

Preferred idea:
- directional glyphs such as `>`, `V`, `<`, `^`
- alternating mouth-open and mouth-closed frames

Alternate idea:
- `C` plus directional cue if readability is better at runtime

### Ghosts

Ghosts should have:
- distinct colors
- distinct glyph identities
- visible frightened state
- visible "eyes returning home" state

The current approach of simple letter marks is a valid base, but the full version should make each ghost readable immediately.

### Pellets

Use a tiny, stable glyph such as:
- `.`
- `*`
- centered dot presentation if rendered through HTML

Power pellets should be visibly larger or brighter than normal pellets.

### HUD

The active play HUD should stay compact and cabinet-like.

Recommended fields:
- `1UP`
- `HIGH`
- `LEVEL`
- `LIVES`
- `BONUS`
- current status line

## Mobile Touch Controls

Mobile support needs its own design rules.

A Pac-Man-style game depends on precise directional intent, buffered turns, and low-latency correction. That makes mobile control quality a core gameplay problem, not a cosmetic follow-up.

### Core Decision

Use a fixed digital D-pad as the primary mobile input.

Do not use swipe-first controls as the default control scheme.

### Why A D-Pad Wins

A D-pad is better for this game because it:
- matches four-direction arcade movement
- supports buffered turns cleanly
- avoids ambiguous diagonal or partial inputs
- reduces accidental page-scroll conflicts
- teaches the player where their thumb belongs

Swipe controls can exist later as an optional experiment, but they should not be the default.

### Mobile Arcade Mode

When the cabinet is active on mobile, the webclient should enter a dedicated arcade mode.

That mode should:
- lock out normal room-screen assumptions
- prevent accidental page scrolling during active play
- keep the playfield centered and stable
- keep controls fixed in place
- reserve a separate place for `Pause` and `Quit`

This should be treated as a focused minigame screen, not a variant of the normal exploration layout.

### Recommended Portrait Layout

Portrait should be the canonical mobile layout.

Recommended structure:
- top: compact HUD with score, lives, level, bonus, and status
- center: ASCII playfield sized to fit without horizontal scrolling
- bottom: fixed D-pad with large directional buttons
- bottom secondary row: `Pause` and `Quit`

The movement pad should always stay in the same place.

The page should not require scrolling to reach movement controls.

### Landscape Layout

Landscape can be supported later, but it should not drive the first design.

If supported, the safest structure is:
- left or center: playfield
- right: vertical HUD and utility column
- bottom or lower-right: D-pad

Landscape should still avoid turning the cabinet into a crowded dashboard.

### Input Model

Movement should work like the arcade original:
- one tap sets the next intended direction
- the character continues moving automatically
- the game buffers the requested direction until it becomes legal
- a later tap replaces the currently buffered direction

This is critical.

The player should not need to keep tapping to continue moving.

### Touch Behavior Rules

- direction buttons should be large and forgiving
- touch feedback should be immediate
- the active or queued direction should be visibly indicated
- controls should work cleanly with one thumb
- `Pause` and `Quit` should never sit inside the D-pad cluster

### Optional Enhancements

- drag across the D-pad to replace the queued direction, while keeping the underlying input digital
- light haptic feedback for pellet milestones, ghost captures, death, and extra life
- left-handed layout option if the control shell becomes more elaborate later
- touch-control theme variant with slightly larger HUD spacing

### Do Not Do This

- swipe-anywhere as the only input method
- analog thumbsticks or virtual joysticks
- repeated tap-to-step movement
- tiny corner buttons
- overlaying controls on top of the maze
- putting `Quit` close enough to movement to be mis-tapped during panic play
- letting the page scroll while the player is steering

### Mobile Visual Treatment

The same presentation rule still applies on touch devices:
- ASCII in the playfield
- normal UI controls outside the playfield

The D-pad itself should be simple and high-contrast.

It does not need to look like a modern gamepad. It needs to feel reliable.

## Animation Policy

Yes, the cabinet should use animation.

It should just use **arcade animation**, not app animation.

### Good Animation

- two-frame or three-frame player chomp
- frightened ghost blink before recovery
- fruit spawn shimmer
- `READY!` flash
- death burst or collapse
- board-clear pulse
- top-score flare
- subtle CRT shimmer or scanline drift

### Bad Animation

- constant panel bobbing
- springy UI easing inside the cabinet
- decorative looping motion unrelated to gameplay
- oversized glow pulses on every entity
- modern mobile-game juice layered over every action

The motion should feel:
- economical
- readable
- deliberate
- cabinet-like

## Motion Intensity Rule

Motion should mostly serve one of four purposes:
- communicate state
- sell impact
- confirm timing
- heighten celebration

If an animation does none of those, it probably should not exist.

## Reduced Motion

The arcade view should support a reduced-motion path.

That path should:
- keep gameplay timing identical
- remove or reduce cosmetic flicker
- reduce large flashes
- keep state clarity intact

Gameplay readability always outranks presentation flourish.

Reduced motion should not weaken touch clarity.

Any mobile button feedback removed for reduced motion should still preserve:
- a strong pressed state
- a clear queued-direction state
- readable pause and failure states

## Bonus Item Direction

For authenticity, bonus items should appear on a schedule like classic arcade fruit.

For `Brave`, the actual items can be themed around the inn and town:
- pie slice
- brass key
- lantern charm
- bottle cap
- star lens shard
- pixel pin

The rule is:
- classic spawn behavior
- local-world item flavor

## Naming And Identity

The machine can absolutely lean into Pac-Man feel without becoming a literal clone.

The safe direction is:
- preserve the arcade grammar
- preserve the score-chase structure
- preserve the ghost-state feel
- preserve the movement feel
- avoid copying exact iconic content one-for-one when a house version can do the job

`Maze Runner` is already a workable house title.

The stronger version is not "rename it to Pac-Man."

The stronger version is "make Maze Runner feel as disciplined and iconic as Pac-Man."

## Technical Direction

If the cabinet becomes important for real competition, the score system should not remain purely client-trusting.

Options:
- server-authoritative simulation
- replay validation from input history
- deterministic run verification from seeded state plus submitted inputs

For a toy prototype, client score submit is fine.

For a full leaderboard cabinet, integrity matters.

## Recommended Build Order

1. Rebuild the maze rules, movement feel, and four-ghost logic.
2. Build the dedicated mobile arcade layout and fixed touch controls.
3. Add power pellets, frightened mode, lives, fruit, and level progression.
4. Add cabinet states, attract mode, and score-table polish.
5. Add Lantern Rest flavor, Joss reactions, prizes, and secret variants.

## Final Recommendation

Keep the cabinet itself ASCII.

Keep Material Symbols in the surrounding `Brave` UI.

Use a fixed D-pad for mobile.

Use animation, but keep it tight, retro, and state-driven.

If the implementation stays disciplined on those four rules, the cabinet can feel both more authentic and more unique than a direct copy.
