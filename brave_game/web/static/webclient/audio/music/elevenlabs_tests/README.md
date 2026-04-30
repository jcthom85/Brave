# ElevenLabs Music Test Pass

These are full-music candidates generated through the ElevenLabs Music API.
They are currently wired into `manifest.json` for in-game audition.

Shared motif direction:

- Rising perfect fourth.
- Held warm note.
- Gentle three-note stepwise fall.
- Same contour transformed by context: title, town, road danger, combat, and Ruk.

Files:

- `title_test.mp3` -> `music.title` / 90 seconds
- `brambleford_safe_test.mp3` -> `music.explore.safe` / 90 seconds
- `goblin_road_test.mp3` -> `music.region.goblin_road` / 90 seconds
- `combat_standard_test.mp3` -> `music.combat.standard` / 75 seconds
- `boss_ruk_test.mp3` -> `music.combat.boss` / 90 seconds
- `victory_stinger_test.mp3` -> `music.victory` / 18 seconds

Source metadata for each generated file is stored under
`tmp/audio-generation/elevenlabs-music/20260430/`.

Audition notes:

- Music cue gain is intentionally conservative so ambience and SFX remain clear.
- These are not final approvals; replace or regenerate any track that clashes
  with ambience, combat readability, or loop behavior.
