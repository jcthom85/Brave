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
