# Reactive UI And Theming Plan

This document defines how `Brave` should make the browser UI feel more alive and more in-universe without sacrificing readability or turning the game into noisy web chrome.

It is intentionally a design document, not an implementation log.

## Goal

Make the UI react to:
- where the player is
- what state the player is in
- what just happened

Do that in a way that:
- preserves the text-first MUD identity
- keeps the main text legible
- lets players customize the presentation
- prevents the interface from becoming visually chaotic

## Core Decision

Themes should become **style systems**, not full color systems.

The game world should control most of the color mood.

That means the browser presentation should be made from four layers:

1. **Style Theme**
   Defines typography feel, panel geometry, border language, glow/shadow treatment, icon style, and motion personality.

2. **World Tone**
   Defines the local color mood of the current area, zone, or portal world.

3. **State Tone**
   Defines safe/danger, combat, boss, low-health, or other gameplay state overlays.

4. **Event FX**
   Defines short-lived effects like hit shake, heal pulse, victory flare, or portal distortion.

These layers must remain separate.

## Design Rules

### Rule 1: Text Stays Primary

The main text pane remains the authoritative surface for:
- room description
- narration
- dialogue
- combat log
- readable text

UI enhancement can support the text, but must not overwhelm it.

### Rule 2: Reactivity Must Be Semantic

The browser should react to game meaning, not arbitrary styling triggers.

Good triggers:
- entering `Whispering Woods`
- starting combat
- taking a heavy hit
- winning a boss fight
- entering a portal world

Bad triggers:
- random animations for decoration
- constant pulsing
- purely cosmetic motion unrelated to game state

### Rule 3: The World Owns Color

`Brambleford`, `Old Barrow`, `Junk-Yard Planet`, and `Drowned Weir` should each feel different even if the player keeps the same chosen theme.

Themes change the lens.
The world changes the mood.

### Rule 4: Motion Must Be Controlled

Use motion as punctuation, not wallpaper.

### Rule 5: Accessibility Wins

Every reactive effect needs a reduced-motion path and must keep contrast/readability intact.

### Rule 6: Themes Must Not Reassign Meaning

Themes may change:
- neutral background surfaces
- panel material
- typography
- border and shadow treatment
- texture and motion character

Themes must not change:
- what the current region hue means
- what danger/safety means
- what combat, victory, or status hues mean

The right model is:
- the game owns semantic color
- the theme owns the rendering of that color

## Theme Redesign

The current themes should be reinterpreted as presentation styles.

### `Lantern Hearth`

The house style for `Brave`.

Characteristics:
- rounded frontier panels
- soft lantern-glow depth
- rich depth
- medium motion intensity

### `Signalglass`

Old terminal / MUD cabinet feel.

Characteristics:
- black-glass surfaces
- squarer panel treatment
- subtle scanline and glow flavor
- slightly harsher digital motion

### `Campfire CRT`

Warmer vintage terminal variation.

Characteristics:
- softer phosphor feel
- softer than `Signalglass`
- old-computer atmosphere without looking hostile

### `Field Journal`

Bookish and literary.

Characteristics:
- ink-first emphasis
- quieter borders
- lower glow
- restrained motion

### `Atlas Slate`

Modern, clean, clarity-first.

Characteristics:
- cool slate surfaces
- sharper edges
- restrained ornament
- most neutral presentation

## What Themes Should Control

Themes should control:
- font pairing defaults
- neutral background/surface color
- corner radius
- border weight
- panel opacity
- shadow vs glow bias
- icon sharpness and emphasis
- action-button character
- motion personality
- background texture treatment

Themes should not control:
- region identity
- portal-world identity
- combat danger color by itself
- quest importance
- narrative emphasis

## Fixed Vs Flexible Color

### Fixed Across All Themes

These should stay semantically stable:
- area accent hue family
- safe/danger hue family
- combat pressure and boss emphasis
- victory / reward emphasis
- portal-world identity hue

### Flexible Per Theme

These can shift theme by theme:
- neutral canvas
- surface lightness or darkness
- text contrast profile
- texture intensity
- how strongly world hue is allowed to tint framing

## World Tone System

Every major area should have a world-tone profile.

Each profile should define:
- `accent`
- `accent_soft`
- `ambient_top`
- `ambient_bottom`
- `surface_tint`
- `highlight`
- `danger_variant`
- `safe_variant`
- `motion_bias`
- `fx_profile`

### Initial Tone Targets

#### `Brambleford`
- warm amber
- hearth calm
- grounded, inviting, safe

#### `Goblin Road`
- dry ochre
- dusty red-brown
- slightly harsher edge contrast

#### `Whispering Woods`
- moonlit green-blue
- faint mist
- soft eerie shimmer

#### `Old Barrow`
- cold ash, bone, iron
- low saturation
- dead stillness

#### `Ruined Watchtower`
- weathered brown, faded red, steel
- wind-scoured, exposed

#### `Goblin Warrens`
- torch-smoke orange, grime, sickly yellow-green
- cramped and ugly

#### `Blackfen`
- marsh green
- stagnant dampness
- murky organic glow

#### `Drowned Weir`
- deep blue-black
- drowned teal
- lantern gold

#### `Nexus Gate`
- astral blue
- brass energy
- faint resonance shimmer

#### `Junk-Yard Planet`
- sodium orange
- industrial cyan
- scrapyard grit and glitch

## State Tone System

These are not full theme changes. They are overlays.

### `Safe`
- softer edge contrast
- calmer prompt tone
- gentler panel emphasis

### `Danger`
- sharper accents
- more contrast in active controls
- slightly more severe border/emphasis treatment

### `Combat`
- exploration chrome gives way to combat chrome
- enemy actions and ally support become clearer
- room tone remains visible underneath

### `Boss`
- stronger contrast
- special event FX enabled
- victory/defeat states become more dramatic

### `Low Health`
- restrained warning treatment
- no giant flashing UI
- should feel tense, not obnoxious

## Event FX System

Event FX should be transient browser events, not permanent CSS states.

### Candidate Effects

#### Hit Reactions
- `light hit`: tiny nudge or flash
- `heavy hit`: noticeable shake
- `boss slam`: strongest short shake

#### Recovery Reactions
- `heal`: soft pulse
- `ward`: shield shimmer
- `buff`: subtle accent flare

#### Status Reactions
- `poison`: sickly flicker
- `bleed`: short red pulse
- `bind`: constriction cue
- `mark`: target accent

#### Progress Reactions
- `quest complete`: clean reward flash
- `level up`: bright celebratory surge
- `chapter complete`: strongest non-combat reward treatment

#### World Reactions
- `portal jump`: distortion / wash / settle
- `boss phase shift`: surge and recover
- `new region entered`: tone settle-in

## Motion Budget

The game should have a motion budget.

### Default Motion Guidance
- room-enter settle: subtle
- hit shake: brief
- heavy hit shake: medium
- boss slam shake: stronger, still short
- portal transfer: slightly longer than combat effects
- chapter win: celebratory but contained

### Anti-Slop Rules
- no constant bobbing
- no infinite looping glows on major surfaces
- no screen shake for every trivial event
- no generic “game UI particles”

## Exploration UI Reactivity

Exploration should react through:
- region tone
- minimap framing
- room-title treatment
- tracked-quest tint
- subtle safe/danger surface changes

The `Ways Forward` dock should not change shape or motion constantly.
It should inherit mood through color/tone only.

The minimap should be one of the clearest places where world tone shows up.

## Combat UI Reactivity

Combat should be the richest reactive surface in the game.

Needed behaviors:
- party and enemy sections inherit local world tone
- hit/heal/status effects feel immediate
- boss phase changes feel materially different
- victory screens react to encounter importance

This must be driven by semantic events from combat, not by log parsing.

## Read / Literary UI

`Read` screens are an especially good place for style themes to shine.

The literary and journal themes should feel strongest there, but:
- readable text must stay easy to scan
- motion should be minimal
- world tone should still tint the framing lightly

## Account / Chargen UI

These screens should mostly use style theme only.

They are system-facing screens, not world-facing screens.
They should feel elegant and coherent, but not heavily region-reactive.

## Technical Direction

The implementation should stay close to the current browser architecture.

### Existing Strengths

The current client already has:
- browser-native main views
- CSS variable theming
- per-browser theme persistence
- explicit browser events

That means the right direction is to extend the current system, not replace it.

### Needed Additions

#### 1. Style Theme Tokens

Current theme tokens should be re-scoped so they describe style behavior, not full world mood.

#### 2. World Tone Registry

Add a registry for all major current areas and worlds.

#### 3. Scene-State Attributes

The client should gain semantic browser state like:
- `data-brave-theme`
- `data-brave-region`
- `data-brave-world`
- `data-brave-scene`
- `data-brave-danger`
- `data-brave-combat`

#### 4. FX Event Layer

Add a transient event/effect channel for:
- hits
- heals
- status procs
- phase changes
- portal jumps
- victory/level/chapter rewards

#### 5. Accessibility Controls

Add:
- `fx off`
- `fx low`
- `fx full`

and honor reduced-motion browser settings.

## Implementation Phases

### Phase 1: Theme Refactor
- convert themes into style-first systems
- stop using themes as the main source of world color identity

### Phase 2: World Tone Profiles
- define tone profiles for all current live regions
- route room/browser views through those profiles

### Phase 3: Exploration Reactivity
- minimap, room header, nav dock, tracked quest, safe/danger treatment

### Phase 4: Combat FX
- hit/heal/status/phase/victory/defeat reactions

### Phase 5: Service Screens
- forge, cook, shop, portals, map, journal refinements

### Phase 6: Accessibility + Tuning
- reduce noise
- add intensity settings
- test on desktop and family-use devices

## Success Criteria

This system is working if:
- `Brambleford` and `Drowned Weir` feel meaningfully different without changing layout
- a player can keep one preferred theme while still feeling local area identity
- combat feels more physical and immediate
- the UI remains readable and calm
- literary themes still feel strong on `read` screens
- nothing important depends on animation to be understood

## Working Rule

The goal is not to make the UI flashy.

The goal is to make the UI feel like the world is present.
