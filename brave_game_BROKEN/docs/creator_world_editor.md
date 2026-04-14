# Creator World Editor

Brave now has a first browser-based creator surface at `/creator/world/`.

## Access

The page uses the same access rules as the creator API:
- authenticated staff
- superusers
- Evennia accounts with `Developer`

## Current Scope

The first editor focuses on world rooms.

It currently supports:
- loading room references from `/api/content/references/rooms`
- loading a room preview from `/api/content/preview`
- editing the authored room JSON payload
- generating a dry-run diff through `/api/content/mutate`
- persisting a room write through `/api/content/mutate`
- validating all content through `/api/content/validate`
- reloading the live registry through `/api/content/reload`

## Notes

This is intentionally a thin operator UI. It is not yet a full form-based editor with field validation, exit/entity editing panes, or reference pickers beyond the room browser.
