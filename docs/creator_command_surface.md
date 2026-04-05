# Creator Command Surface

Brave now exposes a first operator-facing authoring surface directly in Evennia through `content`.

## Access

`content` is locked to `perm(Developer)` and is intended for live authoring, preview, and validation work while the broader creator UI is still being built.

## Preview

Use previews to inspect authored packs without touching disk:

```text
content preview room brambleford_town_green
content preview quest practice_makes_heroes
content preview encounter goblin_road_wolf_turn wolf_turn_pack
content preview forge militia_blade
content preview portal junkyard_planet
```

## Dry-Run Mutations

Without `/write`, `content upsert` only returns a diff.

```text
content upsert room creator_test_room = {"key":"Creator Test Room","desc":"...","zone":"Testing","world":"Brave"}
content upsert quest creator_test_quest = {"quest":{"title":"Creator Test Quest","objectives":[{"type":"visit_room","room_id":"brambleford_town_green","count":1}],"rewards":{"items":[]}},"region":"Testing","add_starting":true}
content upsert portal creator_test_portal = {"name":"Creator Test Portal","status":"stable","resonance":"fantasy","summary":"...","travel_hint":"north","entry_room":"brambleford_town_green"}
```

## Persisting Changes

Add `/write` to persist the mutation, reload the in-process content registry, and run validation immediately:

```text
content upsert/write room creator_test_room = {"key":"Creator Test Room","desc":"...","zone":"Testing","world":"Brave"}
content upsert/write portal creator_test_portal = {"name":"Creator Test Portal","status":"stable","resonance":"fantasy","summary":"...","travel_hint":"north","entry_room":"brambleford_town_green"}
```

## Validation And Reload

```text
content validate
content reload
```

`content validate` rebuilds the live registry and runs the cross-domain content checks. `content reload` only refreshes the process-wide registry from disk.
