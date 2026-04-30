# Audio Systems

Audio is a browser-client enhancement for Brave's text-first experience. It should reinforce location, action, danger, and reward without becoming required to understand the game.

## Current Audio Shape

Current assets include:

- town music
- battle music
- boss battle music
- victory fanfare
- dark-place loop
- Brambleford, forest, portal, and cavern ambience
- UI click
- weapon, magic, fire, footstep, coin, restore, and escape-style SFX

The manifest lives at `brave_game/web/static/webclient/audio/manifest.json`.

Browser behavior lives primarily in `brave_game/web/static/webclient/js/brave_audio.js`.

## Design Rules

- Text remains authoritative. Audio supports the scene; it never carries required information alone.
- Region changes should feel different quickly.
- Combat audio should make timing and impact clearer, not noisier.
- Victory and boss audio should be rare enough to feel meaningful.
- Mobile and LAN play need conservative defaults so audio does not become irritating in a shared room.

## First-Hour Audio Priorities

For the opening story pass, focus audio on the existing tutorial, cellar, road, and Ruk beats:

1. Bell or alarm sting for the Lanternfall cold open.
2. Warm Brambleford bed under Wayfarer's Yard and the inn.
3. Short danger sting when the cellar or road encounter begins.
4. Distinct boss start for Ruk.
5. Victory cue after Ruk that feels like a chapter beat, not a generic win.

## Implementation Notes

- Keep manifest entries named by gameplay purpose, not filename trivia.
- Prefer room or encounter metadata to ad hoc string checks.
- Respect user volume settings.
- Avoid autoplay assumptions that browsers will block.
- Test both websocket browser play and quiet/no-audio fallback.
- Server-triggered story beats use `send_audio_cue_event` or `send_audio_cue_once`
  from `world.browser_panels`; the webclient receives these as
  `brave_audio_cue` OOB events and plays the matching manifest cue.

## ElevenLabs Candidate Workflow

ElevenLabs generation is staged as candidates first. The generation plan lives at
`brave_game/web/static/webclient/audio/elevenlabs_plan.json`, and the helper
script lives at `brave_game/scripts/generate_elevenlabs_audio.py`.

The script reads `ELEVENLABS_API_KEY` from the local shell environment or from
a gitignored repo-root `.env.local` file. It writes generated MP3s plus JSON
provenance records under `tmp/audio-generation/elevenlabs/`. That folder is
gitignored so draft generations do not accidentally replace shipped assets.

Useful commands from `brave_game/`:

```bash
export ELEVENLABS_API_KEY="..."
# Or put ELEVENLABS_API_KEY=... in ../.env.local
python3 scripts/generate_elevenlabs_audio.py --list
python3 scripts/generate_elevenlabs_audio.py --batch first_hour --list
python3 scripts/generate_elevenlabs_audio.py --cue sfx.ui.click --dry-run
python3 scripts/generate_elevenlabs_audio.py --cue sfx.ui.click --yes
python3 scripts/generate_elevenlabs_audio.py --batch first_hour --limit 3 --yes
python3 scripts/generate_elevenlabs_audio.py --kind ambience --yes
```

After review, chosen files can be copied into `web/static/webclient/audio/sfx/`,
`web/static/webclient/audio/ambience/`, or `web/static/webclient/audio/music/`
and then wired through `manifest.json`.

Approved first-hour files currently wired into the live manifest:

- Lanternfall alarm, dead-lantern glass, cart reveal, cellar threat, road danger,
  Ruk boss start, and Ruk chapter defeat story cues.
- Brambleford alarm, Wayfarer's Yard, Rat & Kettle cellar, Goblin Road trailhead,
  and Fencebreaker Camp ambience loops.
- Regional ambience loops for Brambleford interiors, Nexus Gate, Old Barrow,
  Whispering Woods, Blackfen, Drowned Weir, Ruined Watchtower, Goblin Warrens,
  and Junkyard are live under `web/static/webclient/audio/ambience/regions/`.
- The general Brambleford ambience was regenerated as a lower, steadier town
  bed without high-pitched swelling and now replaces the earlier alarm-town loop
  for `ambience.brambleford`.
- Music theme sketches are stored under
  `web/static/webclient/audio/music/theme_sketches/` as Suno reference material.
  They are not wired into live gameplay music until final Suno tracks replace
  the temporary music cues.
- A five-track ElevenLabs Music API test pass is stored under
  `web/static/webclient/audio/music/elevenlabs_tests/`. These full music
  candidates use the shared Brave leitmotif direction and are temporarily wired
  into live gameplay for audition at conservative music gain.

Recommended production order:

1. `first_hour`: Lanternfall, tutorial, cellar, road, Ruk, and chapter victory.
2. `ui_feedback` and `combat_core`: shared interaction and combat readability.
3. `regional_ambience`: all current region and interior beds.
4. `classes`, `enemies`, and `activities`: richer reusable gameplay palettes.
5. `music_themes`: short motifs to feed into Suno for final music.
