# Creator Access

Brave creator tools in the web interface are restricted to authenticated staff, superusers, or Evennia accounts with `Developer` permission.

## Entry Point

Start at `/creator/` for the creator landing page.

## Builders

- `/creator/world/` for rooms, exits, and entities
- `/creator/quests/` for quest content
- `/creator/dialogue/` for talk rules and readable text
- `/creator/encounters/` for encounter tables and enemy templates
- `/creator/items/` for item templates
- `/creator/characters/` for classes, races, progression, and defaults

## API

The creator API root is `/api/content`.

Primary routes:
- `GET /api/content/status`
- `GET /api/content/references/<domain>`
- `POST /api/content/preview`
- `POST /api/content/mutate`
- `POST /api/content/remove`
- `POST /api/content/validate`
- `POST /api/content/reload`

## In-Game Command

Creators with Evennia `Developer` permission can also use the `content` command in-game for preview, mutation, removal, validation, and reload operations.
