# Creator Encounter Editor

Brave now has a browser-based encounter authoring surface at `/creator/encounters/`.

## Current Scope

The editor currently supports:
- browsing rooms and enemy templates
- loading room encounter-table previews
- loading enemy template previews
- selecting, adding, and removing staged encounter entries for a room
- editing up to four enemies per staged encounter entry
- editing one enemy template with core combat stats and tags
- staging new enemy drafts directly in the editor
- syncing the full room encounter list and enemy payloads into the authored JSON used by the encounter mutation path
- dry-run diff and write through the creator API

## Notes

This page now covers multi-entry encounter-table authoring for the current combat content model. The next expansion should be richer enemy data such as loot, abilities, and behavior tuning before the combat overhaul starts.
