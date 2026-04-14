# Creator Dialogue Editor

Brave now has a browser-based dialogue authoring surface at `/creator/dialogue/`.

## Current Scope

The editor currently supports:
- browsing authored world entities
- loading NPC talk rules through a dialogue preview
- loading readable text through a readable preview
- selecting, adding, and removing staged talk rules for an entity
- editing quest, room, and resonance gates for each staged talk rule
- editing static readable text
- syncing the full authored talk-rule list into the JSON payload used by the dialogue mutation path
- dry-run diff and write through the creator API

## Notes

This page now covers multi-rule dialogue authoring for the current static rule model. The next expansion should be richer rule conditions/effects and better branching-conversation authoring once the interaction model is widened.
