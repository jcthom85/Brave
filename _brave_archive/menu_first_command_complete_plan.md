# Menu-First, Command-Complete

## Goal

Brave should be fully playable through visible UI controls, menus, and pickers, while still preserving the full typed-command experience for players who want to play it like a traditional MUD.

The rule is:

- commands stay canonical
- menus and buttons should call those same commands
- normal play should not require typing
- typed commands remain available as a complete fallback

This is not a "remove the command line" plan. It is a "stop requiring syntax memory for normal play" plan.

## Product Model

### Primary Experience

Most players should interact through:

- room movement surfaces
- visible contextual actions
- compact action bars
- pickers for targets, quantities, and nearby entities
- a chat composer for player speech

### Secondary Experience

Players who want the old-school MUD feel should still be able to:

- type movement shortcuts
- type verbs directly
- play almost entirely from the command line if they prefer

The UI should sit on top of the command set, not replace it.

## Input Model

The input surface should become a two-mode composer:

- `Chat`
- `Command`

### Chat

`Chat` is the default visible mode during normal in-character play.

Behavior:

- enter sends `say <text>`
- the placeholder reads like speech, not commands
- this is primarily for talking to nearby player characters
- NPC conversations should continue to use `talk` and dialogue UI, not free-form chat parsing

### Command

`Command` is the secondary typed mode.

Behavior:

- sends raw commands exactly as the current command line does
- remains fully available for power users, debugging, and unfinished flows
- can be pinned or selected by players who want a MUD-style experience

### Escape Hatch

Even in chat mode, the client should preserve a reliable way to issue commands immediately.

Recommended rules:

- explicit `Command` mode is always available
- slash-prefixed text in chat mode may be treated as a raw command shortcut

## Interaction Primitives

To avoid one-off UI hacks, Brave needs a small set of reusable interaction patterns.

### Action Buttons

Direct one-click verbs:

- `Talk`
- `Read`
- `Attack`
- `Cook`
- `Eat`
- `Sell 1`
- `Sell All`
- `Follow`
- `Invite`

### Picker Sheet

Used when a verb needs a structured follow-up choice.

Examples:

- choose a combat target
- choose an ally target
- choose which nearby player to invite
- choose which quest to track
- choose a portal destination

### Quantity Picker

Used for stackable inventory actions.

Examples:

- sell `1 / some / all`
- use or consume stacked items

### Context Action Surface

Each major screen should answer `what can I do right now?` without requiring typed syntax.

Examples:

- room: move, talk, read, fight, map, pack, journal, party
- combat: attack, ability, target, flee
- services: buy, sell, forge, cook, pray, travel

## Screen Rules

### Exploration

Exploration should be fully no-typing.

Required:

- movement
- visible interactions
- threat engagement
- room utility access
- map, pack, quest, party access

### Combat

Combat must not rely on typed target syntax.

Required:

- basic attack buttons
- compact ability roster
- target picker when a chosen ability has multiple valid targets
- flee button

### Town Services

Town services should be entirely action-driven.

Required:

- shop selling actions
- forge actions
- cooking and eating actions
- prayer and portals

### Party

Party management should not require names to be typed in normal play.

Required:

- nearby player invite actions
- accept and decline invite buttons
- follow, stay, where, leave, kick actions

### Character Surfaces

Character screens should be navigable and informative without typing.

Required:

- sheet
- gear
- pack
- journal

## Command Coverage Policy

Every player-facing verb should be placed into one of three buckets:

### Must Be Menu-Accessible

These are core gameplay actions and should always have visible UI access.

- movement
- look
- map
- pack
- quests
- party
- talk
- read
- fight
- attack
- use
- flee
- cook
- eat
- sell
- forge
- pray
- portals

### Chat-Only Primary

These stay text-driven in normal use, but are represented as chat rather than raw commands.

- say
- later: party chat, whispers, tells if added

### Command-Fallback Only

These may stay typed-first for now.

- debug verbs
- admin verbs
- unfinished edge-case verbs
- low-frequency power-user shortcuts

## Technical Direction

### Keep Commands Canonical

The command layer remains the source of truth.

UI should:

- trigger existing commands where possible
- avoid hidden client-only gameplay logic
- prefer structured pickers that resolve into existing commands

### Expand View Payloads

Browser view payloads should support:

- direct commands
- prefill only when truly necessary
- picker payloads for target and choice selection

The current browser view pattern in `world/browser_views.py` is the correct base. It should be extended, not replaced.

### Avoid Button Explosions

Dense lists should stay dense.

Bad:

- giant ability cards with every possible target exposed all at once
- long stacks of full-width control slabs

Good:

- compact rows
- a single `Pick Target` interaction
- small action buttons
- modal or bottom-sheet pickers

## Rollout

### Phase 1: Input Split

- add `Chat` and `Command` modes to the input surface
- default to `Chat` in normal in-character play
- preserve `Command` mode for typed-first players
- keep mobile input hidden until explicitly opened

### Phase 2: Generic Picker System

- add a reusable picker sheet in the webclient
- allow browser view entries and actions to open pickers instead of relying on typed follow-up

### Phase 3: Finish Core No-Typing Loops

- combat target selection
- party invite and party management
- any remaining room interaction gaps

### Phase 4: Polish

- keyboard shortcuts
- persistent mode preference
- optional terminal-first mode
- better search/filtering for large ability and inventory lists

## Current First Slice

The first implementation slice should focus on:

- chat-first input plus command fallback
- a reusable picker mechanism
- converting high-frequency typed-heavy actions that still block normal play

That slice gives the biggest change in feel without needing a total command rewrite.
