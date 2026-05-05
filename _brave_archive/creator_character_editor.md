# Creator Character Editor

Brave now has a browser-based character-content authoring surface at `/creator/characters/`.

## Current Scope

The editor currently supports:
- browsing authored classes and races
- loading live class previews with progression classification
- loading live race previews
- editing class metadata, base stats, and progression lists
- editing race metadata and racial bonus payloads
- editing global character-config values including defaults, primary stats, vertical-slice classes, and XP thresholds
- staging new class and race drafts directly in the browser
- syncing structured form fields into the raw JSON payloads used by the mutation path
- dry-run diff and write through the creator API

## Notes

This page covers the main authored character foundation for Brave. The next expansion should add friendlier ability-library and passive-trait editors so class progression authoring does not rely on raw JSON references alone.
