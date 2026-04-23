# Brave Audio Implementation Plan

## Goal

Add browser-side layered audio to `Brave` with a design that fits the existing Evennia webclient architecture:

- ambient layer
- music layer
- SFX layer
- future voice layer

The first pass should improve mood and feedback without forcing new creator tools, server complexity, or heavy third-party framework dependencies.

## Recommendation

Build a custom browser-side `AudioDirector` on top of the Web Audio API.

Do not adopt a large game-audio framework. Brave already has the important hard parts in place:

- browser-only OOB event delivery via `brave_game/world/browser_panels.py`
- semantic view reactivity via `brave_game/world/browser_views.py`
- centralized room refreshes via `brave_game/typeclasses/rooms.py`
- structured combat FX via `brave_game/typeclasses/scripts.py`
- custom client OOB handling via `brave_game/web/static/webclient/js/plugins/default_out.js`

The missing work is Brave-specific orchestration, not generic playback.

## Existing Integration Points

### Client

- `brave_game/web/static/webclient/js/plugins/default_out.js`
  - central OOB event router
  - current view/reactive state handling
  - menu picker and notice flows
  - best place to hand events to audio
- `brave_game/web/templates/webclient/webclient.html`
  - load point for a dedicated audio script

### Server/runtime signals already available

- `brave_view`
  - carries `reactive.scene`, `reactive.world_tone`, `reactive.source_id`, `reactive.danger`, `reactive.boss`
- `brave_scene`
  - supplemental scene data
- `brave_combat_fx`
  - structured combat FX with `kind`, `impact`, `element`, `source`, `target`, `defeat`, `lunge`
- `brave_notice`
  - quest/progress/error/feedback notices
- `brave_room_activity`
  - room activity feed and lightweight event cues

### Content/runtime metadata already available

- room/world/zone data in `brave_game/world/content/packs/core/world.json`
- world tone resolution in `brave_game/world/data/world_tones.py`
- systems content registry in `brave_game/world/content/registry.py`

## Architecture

## 1. Browser audio subsystem

Create a dedicated client module, separate from `default_out.js`:

- suggested file: `brave_game/web/static/webclient/js/brave_audio.js`

Responsibilities:

- initialize `AudioContext`
- manage autoplay unlock on first click/tap/keypress
- own bus graph and master state
- load and cache decoded assets
- expose semantic methods like:
  - `setSceneReactiveState(...)`
  - `playUiCue(...)`
  - `playCombatCue(...)`
  - `playOneShot(...)`
  - `setLayerTargets(...)`
- persist user settings
- provide a small debug surface for tests

`default_out.js` should not contain audio logic beyond calling the director.

## 2. Audio buses

Pass 1 buses:

- `master`
- `ambience`
- `music`
- `sfx`

Pass 2 bus:

- `voice`

Bus requirements:

- independent gain control
- mute support
- smooth fades
- temporary ducking

## 3. Playback model

Use semantic cue IDs, not hard-coded file paths in event handlers.

Examples:

- `ambience.brambleford.square`
- `music.explore.safe`
- `music.combat.standard`
- `music.combat.boss`
- `sfx.combat.hit.melee`
- `sfx.combat.heal.basic`
- `sfx.ui.click`
- `sfx.ui.error`
- `sfx.portal.warp`

This keeps authored mappings stable even if source files change.

## 4. Asset manifest

Pass 1 should use a static manifest file, not creator tooling.

- suggested path: `brave_game/web/static/webclient/audio/manifest.json`

Suggested shape:

```json
{
  "version": 1,
  "buses": {
    "master": { "default_volume": 1.0 },
    "ambience": { "default_volume": 0.8 },
    "music": { "default_volume": 0.7 },
    "sfx": { "default_volume": 0.9 }
  },
  "cues": {
    "music.explore.safe": {
      "bus": "music",
      "files": ["music/explore_safe_loop.ogg"],
      "loop": true
    }
  }
}
```

Asset directory:

- `brave_game/web/static/webclient/audio/music/`
- `brave_game/web/static/webclient/audio/ambience/`
- `brave_game/web/static/webclient/audio/sfx/`

Use `.ogg` as the primary format unless compatibility requirements force dual-format support.

## Event Mapping Strategy

## 1. Existing signals first

Do not add new server events until the current signal set is exhausted.

### Scene-driven layer changes

Drive ambience and music from `viewData.reactive`:

- `scene=explore`
  - music based on safe/danger/town/portal context
  - ambience based on `world_tone` and optionally `source_id`
- `scene=combat`
  - combat music
  - subdued ambience or ambience ducking
- `boss=true`
  - boss combat music or boss stinger

### Combat SFX

Map from `brave_combat_fx`:

- `kind=damage`
  - use `impact` and `element` to choose variants
- `kind=heal`
  - healing cue
- `kind=miss`
  - miss/whiff cue
- `kind=defeat`
  - defeat cue

### UI and world feedback

Map from:

- `brave_notice`
  - success, warning, danger, quest progress, error
- `brave_room_activity`
  - arrival, threat, loot, speech pings where appropriate
- click handlers in the webclient
  - menu open, button press, invalid action

## 2. Add explicit `brave_audio` later

Only add a dedicated OOB event for cases current events do not express cleanly:

- portal warp stingers
- authored one-off location stingers
- narrated read-aloud playback
- enemy/NPC signature one-shots
- future voice content

## First-Pass Content Scope

Keep the MVP small enough to finish.

### Ambience

- Brambleford
- Goblin Road
- Whispering Woods
- Old Barrow Field

### Music

- safe explore / town
- hostile explore
- combat
- boss combat or portal

### SFX

- UI click
- UI error
- travel / room transition
- loot / reward
- melee hit
- miss
- heal
- fire / magic hit
- defeat
- portal warp
- quest / notice success

## Settings UX

Add an Audio settings screen into the existing browser menu flow.

Likely entry point:

- extend the menu picker in `brave_game/web/static/webclient/js/plugins/default_out.js`

Pass 1 settings:

- master volume
- ambience volume
- music volume
- SFX volume
- mute all
- reduce repeated SFX

Persistence:

- `localStorage`

Use the same client-side persistence pattern already used for theme/input settings.

## Autoplay Unlock

Browser autoplay restrictions are a hard requirement, not a polish item.

Plan:

- initialize the audio system in a suspended state
- unlock/resume on first trusted interaction
- show a non-blocking prompt if audio is enabled but still locked
- do not spam prompts after the first successful unlock

## Testing Strategy

Use the existing Playwright harness rather than trying to test sound output directly.

Add tests for:

- manifest loading
- audio unlock state transitions
- bus volume persistence
- scene-driven cue selection
- combat cue mapping from `brave_combat_fx`
- crossfade behavior at the state-machine level
- mute/repeat-reduction behavior

Recommended approach:

- expose a small debug object on `window` in test/dev mode
- assert selected cue IDs, active buses, target gains, and last-triggered events
- continue avoiding hardware-dependent audio assertions

## Implementation Phases

## Phase 1: Foundation

- add `brave_audio.js`
- add audio manifest and asset directory structure
- load audio module from webclient template
- implement `AudioContext`, buses, cache, fades, one-shots, loop control
- implement autoplay unlock
- implement local settings persistence

Definition of done:

- the client can load, unlock, and change bus volumes with no game-specific cue logic yet

## Phase 2: Brave signal integration

- connect `default_out.js` OOB handlers to `AudioDirector`
- map reactive scene data to ambience/music
- map `brave_combat_fx` to combat SFX
- map notices and UI interaction to lightweight cues

Definition of done:

- entering explore/combat/boss states changes layers correctly
- core combat and UI actions emit audio reliably

## Phase 3: Settings UI

- add Audio entry to menu
- build browser-first settings view or picker
- wire sliders/toggles to the director

Definition of done:

- users can control audio without leaving the current session

## Phase 4: Asset/content expansion

- add more zone variants
- add portal-world palettes
- add authored stingers
- evaluate data-driven pack integration

Definition of done:

- the audio system covers the first playable slice with distinct mood by region

## Phase 5: Explicit authored audio events

- add `brave_audio` OOB event where needed
- support custom voice and recorded content
- consider systems pack or dedicated audio pack integration

Definition of done:

- special events and creator-authored audio no longer need to piggyback on generic state

## File Touchpoints For Build Start

Initial implementation should likely touch:

- `brave_game/web/templates/webclient/webclient.html`
- `brave_game/web/static/webclient/js/brave_audio.js`
- `brave_game/web/static/webclient/js/plugins/default_out.js`
- `brave_game/web/static/webclient/audio/manifest.json`
- `brave_game/regression_tests/playwright_ui_harness.py`
- one or more new regression tests for client audio state

Server changes should be deferred unless Phase 2 exposes signal gaps.

## Recommended Order Of Work

1. Build `AudioDirector` and manifest loading.
2. Add autoplay unlock and bus settings persistence.
3. Hook scene reactivity into ambience/music transitions.
4. Hook combat FX into SFX playback.
5. Add audio settings UI.
6. Add tests.
7. Expand assets.
8. Introduce explicit `brave_audio` only where existing signals fail.

## Non-Goals For Pass 1

- no creator/editor UI for audio authoring
- no server-side audio processing
- no large third-party audio framework
- no voice recording pipeline
- no attempt to score every single command or line of text

## Open Questions

- Should room transitions always trigger a travel cue, or only when `source_id` changes across world-tone groups?
- Should combat music fully replace ambience, or should ambience duck underneath?
- Should notice tones map directly to audio categories, or should quest/progression notices get their own semantic cue family?
- Do we want a visible first-run "Enable Audio" affordance, or silent unlock-on-interaction only?
- When assets are ready, should authored cue mappings live in `systems.json` or in a dedicated audio pack?
