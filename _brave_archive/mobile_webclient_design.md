# Mobile Webclient Design

## Purpose

This document defines how `Brave` should look and behave on phones and other narrow touch devices.

The goal is not to "shrink desktop until it fits." The goal is to give mobile its own composition while preserving the existing desktop experience.

## Hard Rule

Desktop stays as it is.

This mobile design is an additive layer that activates only for smaller viewports and touch-oriented layouts. The current desktop experience remains the canonical full-browser presentation.

## Design Goals

- keep the current desktop UI intact
- remove right-rail awkwardness on narrow screens
- reduce scrolling and nested scrolling
- make movement, interaction, and combat comfortable with thumbs
- keep the game text-first and command-first even when clickability is present
- preserve theme identity and world-reactive tone on mobile

## Non-Goals

- no separate mobile game client
- no hidden-gesture-only navigation
- no app-style tab bar full of systems
- no duplicate desktop-and-mobile screen logic where one can be adapted cleanly

## Breakpoint Model

### Desktop

`1100px+`

Keep the current desktop shell exactly as it is now.

### Compact Desktop / Tablet Landscape

`901px-1099px`

Keep the current compact-desktop behavior. This range can continue to use the desktop mental model with some trimmed spacing, but it should not switch to the full phone layout.

### Mobile / Tablet Portrait

`900px and below`

This is the real mobile layout. The right rail disappears as a persistent column and the game becomes a single-column experience with one primary scroll surface.

### Short Viewport Exception

If height is very limited, especially on phone landscape, the mobile layout should collapse even harder:

- smaller hero block
- tracked quest reduced to a single line
- minimap reduced to an icon/button that opens the full map
- navigation dock remains fixed

## Mobile Layout Doctrine

There should be one main scrollable content surface and one fixed action zone.

That means:

- the center content scrolls
- the bottom command bar stays fixed
- the movement dock stays fixed when in exploration
- the minimap is not a permanent floating rail
- no panel should push content under the command bar

## Core Mobile Shell

On mobile, the screen should be organized as:

1. top scene header
2. central content column
3. fixed bottom navigation dock when exploring
4. fixed command bar at the very bottom

The persistent desktop right rail should not exist on mobile.

## Exploration Layout

Exploration is the most important mobile screen, so it should be designed first and everything else should follow its logic.

### Top Scene Header

The top of the screen should contain a compact room header:

- region overline
- room title
- short room description
- one compact utility row beneath it

This utility row should contain:

- a tappable minimap tile
- a tappable tracked quest chip if one is active
- possibly one very small contextual chip if truly needed

This is where the minimap and tracked quest move on mobile. They stop being a right rail and become part of the top scene context.

### Minimap on Mobile

The minimap should not remain a full-size persistent desktop card.

Instead:

- show a compact square minimap tile in the top utility row
- keep it clearly tappable
- tapping it opens the full `map` screen

The minimap should stay square, readable, and world-reactive, but it should not occupy a permanent side column on a phone.

### Tracked Quest on Mobile

Tracked quest should become a compact card or chip under the hero area, not a full-height side panel.

Rules:

- if no quest is tracked, it does not show
- if a quest is tracked, show title plus a short objective line
- tapping it opens `quests`
- the full objective list belongs in the journal, not in the exploration shell

### Visible Here

`Visible Here` should be the main scrollable body section on mobile.

Rows should be:

- large enough for touch
- full width
- action-first
- lightly styled, not busy

The row itself should remain the primary action target.

Examples:

- NPC row taps to `talk`
- readable row taps to `read`
- player row exposes party actions cleanly

### Ways Forward

`Ways Forward` should become a fixed bottom dock on mobile.

This is the biggest structural difference from desktop.

Instead of living as a mid-page section, it should sit above the command bar like a movement controller.

Rules:

- fixed footprint
- always anchored at the bottom during exploration
- NSEW keep stable positions
- `Up` and `Down` sit in a secondary row
- non-cardinal exits appear as small route chips above or beside the dock
- the dock never changes height based on content

This makes movement feel stable and thumb-friendly.

### Exploration Scroll Strategy

When exploring on mobile:

- the room header and utility row stay at the top
- `Visible Here` is the main scroll area
- the movement dock stays fixed above the command bar

This prevents the player from scrolling past movement controls or losing them under content.

## Command Screens on Mobile

All browser-native screens like `Journal`, `Gear`, `Pack`, `Shop`, `Forge`, `Party`, `Talk`, `Read`, and `Map` should follow one shared mobile structure.

### Shared Structure

1. sticky top bar with `Back` and title
2. one vertically scrolling content column
3. primary actions inline with the content
4. fixed command bar at bottom

There should be no mobile side card and no desktop-style split composition on these screens.

### Section Treatment

On mobile, sections should be stacked vertically with generous hit areas and less decorative chrome than desktop.

The mobile version should favor:

- concise section headings
- taller row targets
- reduced chip clutter
- fewer side-by-side metrics

If a section gets too dense, the solution should be accordion-style collapse or a summary row, not another column.

## Map Screen on Mobile

The full `map` screen should feel like a dedicated tool screen.

### Mobile Map Rules

- `Back` stays sticky at top
- the ASCII map gets the widest central space possible
- legend and route details collapse underneath it
- the map block can scroll inside its own bounded area if needed
- tapping the minimap tile from exploration should land here directly

The map should not try to coexist with side panels on mobile.

## Journal Screen on Mobile

The journal should be especially clean on mobile.

Recommended treatment:

- `Back` + `Journal` at top
- tracked quest, if any, pinned near the top as a compact summary
- `Active`, `Completed`, and other sections stacked vertically
- row tap expands details
- `Track` / `Untrack` stays obvious

No extra explanatory copy should be shown unless it is truly useful to the player in the moment.

## Talk and Read Screens on Mobile

These should lean into readability.

### Talk

- sticky `Back`
- NPC name and context at top
- dialogue large enough to breathe
- quoted and italic treatment preserved
- actions below, not beside

### Read

- reading surface gets generous horizontal use
- narrower internal measure than the full viewport
- good top/bottom breathing room
- low chrome

These are good places for the more literary themes to shine on mobile.

## Combat on Mobile

Combat should become more action-centered than exploration.

### Combat Structure

1. sticky combat summary bar
2. scrollable target list
3. quick-action tray above the command bar
4. command bar at bottom

### Sticky Combat Summary

Show only the most important state:

- encounter name or threat state
- player HP/resource
- enemy count
- current turn or queued-state hint

This should be much tighter than the desktop combat header.

### Targets and Abilities

- enemies become large tap targets
- ally support targets become separate rows
- self abilities live in a horizontal quick-action tray above input
- target-specific abilities remain attached to target rows

The fight log should continue below, but it should not crowd the controls.

## Account and Character Screens on Mobile

The OOC/account, character list, and chargen flows should be treated as vertical mobile screens.

### Account Screen

- character rows full width
- `Play` on row tap
- `Create` as large primary action
- `Delete` kept secondary and confirmed

### Chargen

- one decision section visible at a time
- race/class choices as stacked touch cards
- sticky `Back` and `Confirm`

No desktop-style multi-panel layout should survive onto mobile here.

## Command Bar on Mobile

The command bar should be smaller and more obviously single-line than desktop.

### Rules

- fixed at bottom
- safe-area aware
- one-line by default
- expands only if the player truly types beyond one line
- send button stays mounted and aligned cleanly

The prompt line should be minimal on mobile. It should not consume vertical space unless it is carrying useful contextual text.

## Touch Rules

### Hit Targets

- minimum target size should feel like `44px-48px`
- rows should be easier to tap than tiny action pills
- primary action should always be the row tap where possible

### Gestures

Do not make critical flows depend on gestures.

Allowed:

- optional pull/settle polish
- optional swipe-right `Back` if it is additive

Not allowed:

- hidden swipe-only map/journal/navigation access

## Scroll Rules

Mobile should avoid layered scrolling.

Rules:

- one main scroll surface at a time
- fixed bottom controls never overlap content
- full-screen views open scrolled to top
- exploration should not open midway down the room view

This matters because the current desktop layout can survive some scroll complexity that will feel bad immediately on a phone.

## Theme Rules on Mobile

Themes should keep their identity on mobile, but mobile should reduce ornamental weight.

That means:

- same fonts
- same material language
- same world-reactive color model
- reduced padding, shadow, and ornament where necessary

Mobile should not invent new themes. It should render the same themes more compactly.

## World-Reactive Tone on Mobile

World tone should still be visible on mobile.

It should show up through:

- room header
- minimap tile
- tracked quest chip
- navigation dock accents
- command bar edge treatment
- screen section accents

It should not rely on one single hero card carrying all of the mood.

## Implementation Approach

### Phase 1: Structure

- keep desktop CSS untouched
- add a mobile-only shell mode at `900px and below`
- remove persistent right rail on mobile
- move minimap and tracked quest into the top scene utility row
- move `Ways Forward` into a fixed bottom exploration dock

### Phase 2: Screen Conversion

- convert exploration first
- then mobile account/chargen
- then map/journal/read/talk
- then combat

### Phase 3: Polish

- safe-area tuning
- theme-specific mobile reductions
- short-viewport tuning
- touch target audit

## Success Criteria

The mobile design is successful when:

- desktop still looks exactly like desktop does now
- the player never wonders where movement went
- the minimap and quest remain accessible without eating the screen
- exploration does not require constant scrolling just to move
- command screens feel intentional, not like squeezed desktop panels
- the game still feels like `Brave`, not like a generic responsive web app

## Recommended Default Mobile Mental Model

For mobile, the game should feel like:

- story and scene at the top
- people and objects in the middle
- movement and command at the bottom

That is the cleanest way to preserve the soul of the current UI while making it actually good on a phone.
