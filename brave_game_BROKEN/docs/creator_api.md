# Creator API

Brave now exposes a thin authenticated JSON API for creator tooling under `/api/content/...`.

## Access

The API allows authenticated staff, superusers, or Evennia accounts with `Developer` permission.

## Endpoints

- `GET /api/content/status`
- `GET /api/content/references/<domain>?q=<query>&limit=<n>`
- `POST /api/content/preview`
- `POST /api/content/mutate`
- `POST /api/content/validate`
- `POST /api/content/reload`

## Preview Request

```json
{
  "kind": "room",
  "args": ["brambleford_town_green"]
}
```

## Mutation Request

```json
{
  "kind": "room",
  "target": "creator_test_room",
  "payload": {
    "key": "Creator Test Room",
    "desc": "A room created through the web creator api.",
    "zone": "Testing",
    "world": "Brave"
  },
  "write": false
}
```

`write: false` returns a diff only. `write: true` persists the change, reloads the in-process registry, and returns any validation errors.
