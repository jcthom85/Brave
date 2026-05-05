# Creator World Editor

Brave now has a first browser-based creator surface at `/creator/world/`.

## Access

The page uses the same access rules as the creator API:
- authenticated staff
- superusers
- Evennia accounts with `Developer`

## Current Scope

The world builder edits authored room, exit, and room-entity content.

It currently supports:
- loading room and exit references from `/api/content/references`
- browsing rooms by list and map region
- editing from a sticky inspector with Room, Exits, and Entities tabs
- dragging room coordinates and writing position changes explicitly
- staging new room drafts from the map or the New Room action
- staging exit drafts from connect mode or active-room direction handles
- editing room, exit, and entity fields while preserving advanced JSON fields
- editing common entity metadata such as aliases, descriptions, and NPC gender
- previewing diffs through `/api/content/mutate`
- persisting room, exit, and entity writes through `/api/content/mutate`
- validating all content through `/api/content/validate`
- reloading the live registry through `/api/content/reload`

## Safety Notes

- Graph connection actions stage drafts; they do not write exits directly.
- New room drafts must be saved before exits or room objects can be saved against them.
- The preview API returns full exit and entity payloads so form saves do not drop authored fields such as aliases, labels, descriptions, or NPC metadata.
- Validation errors are displayed in the activity panel instead of being treated as transport failures.
