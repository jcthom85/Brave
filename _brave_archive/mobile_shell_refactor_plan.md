# Mobile Shell Refactor Plan

## Purpose

This document defines the next-generation mobile UI shell for `Brave`.

It does not replace the desktop UI.
It defines how the phone-sized experience should look, what should always be visible, and what should move into sheets or overflow surfaces.

The guiding rule is:

- mobile should feel like a game client
- desktop can keep the richer browser dashboard

## Core Product Rule

The mobile screen should answer these questions immediately:

1. Where am I?
2. What can I do right now?
3. What is the fastest way to do it?

Everything else should be one tap away, not permanently on-screen.

## Mobile Doctrine

Mobile should not mirror desktop.

The phone layout should have:

- one main scroll surface
- one persistent control deck
- one utility sheet
- one chat / command entry path

It should not have:

- a persistent desktop-style right rail
- always-on utility cards for every system
- gesture-only navigation
- a requirement to type for normal play

## Always-Available Access

### Must Be Visible In Exploration

- current room name
- danger state
- movement
- nearby threats
- visible interactables
- access to chat
- access to utility systems

### Must Be One Tap Away

- full map
- pack
- quests
- party
- sheet
- gear
- command console

## Mobile Shell

The shell should be organized as:

1. top scene header
2. main room content
3. contextual action strip when relevant
4. bottom control deck
5. modal sheets for utility and pickers

## Exploration Layout

### Top Header

The exploration header should be compact and glanceable.

It should contain:

- zone / room title
- short room description
- a micromap
- one or two glance surfaces for quest or room state

### Micromap

The micromap is not a tiny full minimap card.

Its job is only to show:

- your current position
- nearby structure
- open local space at a glance

Rules:

- keep it very small
- keep the player marker obvious
- do not cram labels into it
- tapping it should open the `Map` utility view

This should be treated as an orientation widget, not a secondary panel.

### Main Body

The room body should stay focused on:

- `Threats Here`
- `Visible Here`
- current contextual interactions

`Ways Forward` should not dominate the room body on mobile.
Movement belongs in the fixed control deck.

### Contextual Action Strip

When the room offers a high-priority action, it should be surfaced explicitly.

Examples:

- `Talk Tamsin`
- `Read Board`
- `Fight`
- `Cook`
- `Pray`

This strip should remain short and context-sensitive.

## Bottom Control Deck

### Exploration Deck

The exploration deck should be the one persistent gameplay control surface on mobile.

It should contain:

- a directional movement cluster for `N / E / S / W`
- a center stack for `Up / Down` when available
- utility buttons for non-movement actions

### Utility Buttons

The deck should expose:

- `Chat`
- `Pack`
- `Quests`
- `More`

The micromap in the header already provides fast access to `Map`, so `Map` does not need equal permanent weight in the deck.

## Utility Sheet

The utility sheet should be the main home for secondary information.

Recommended tabs:

- `Map`
- `Pack`
- `Quests`
- `More`

### More Tab

`More` should gather lower-frequency but still important systems:

- `Party`
- `Sheet`
- `Gear`
- `Command`

This keeps the main room screen clean while preserving fast access to core systems.

## Chat And Commands

Mobile should stay chat-first and command-complete.

Rules:

- `Chat` is the default visible text entry path
- `Command` stays available from overflow
- typed commands are still supported exactly as they are now
- normal play should not require typing

## Combat Shell

Combat should use the same mobile shell logic, but with a different deck.

Visible:

- encounter title
- enemy state
- party state
- compact combat log context

Bottom deck:

- `Attack`
- `Abilities`
- `Items`
- `Flee`

Target choice should always use pickers instead of typed syntax.

## Service Screens

Town and service screens should not reuse the exploration movement deck.

They should use a simpler task bar:

- `Back`
- primary action for the screen
- `Chat`
- `More`

Examples:

- shop
- forge
- cook
- portals
- prayer

## Rollout Order

### Phase 1: Mobile Exploration Foundation

- compact top header
- micromap
- cleaned-up exploration deck
- utility sheet with `More`

### Phase 2: Contextual Interaction Pass

- room action strip
- better talk/read/interact surfacing
- reduced dependence on typed verbs

### Phase 3: Mobile Combat Shell

- dedicated combat deck
- picker-first targeting

### Phase 4: Service Screens

- shop / forge / cook / portals / prayer mobile task bars

## Immediate Build Slice

The first implementation slice should deliver:

- a micromap in the exploration header
- a smaller mobile room glance area instead of bulky utility cards
- a clearer utility-sheet structure with `More`
- explicit movement buttons in the exploration deck instead of swipe navigation

That gives the mobile UI a cleaner visual hierarchy without requiring a risky full rewrite in one pass.
