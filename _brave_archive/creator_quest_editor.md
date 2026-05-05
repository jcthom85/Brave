# Creator Quest Editor

Brave now has a first browser-based quest authoring surface at `/creator/quests/`.

## Current Scope

The editor currently supports:
- quest key, title, giver, summary, and region
- one prerequisite quest picker
- starting quest toggle
- one visit-room objective
- one optional collect-item objective
- XP, silver, and one optional reward item
- syncing structured fields into the authored JSON wrapper used by the quest mutation path
- dry-run diff and write through the creator API

## Notes

This is the first structured quest workflow, not the final one. It is intentionally constrained so the editor can stay aligned with the live registry-backed mutation path.
