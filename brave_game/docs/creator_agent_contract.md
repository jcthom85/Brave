# Creator Agent Contract

## Purpose

The Creator Codex contract gives Codex CLI a narrow way to inspect, plan, draft, and verify Brave content changes without bypassing the existing Creator builders.

It is meant for instruction-driven content work such as "add a quest that starts in Brambleford" or "create draft loot and wire it into this enemy." It is not a publisher. Human review and the existing Creator publish flow remain separate.

## Safety Model

- Codex apply writes only to draft packs.
- Live publish remains a separate Creator action.
- Plan calls do not write files.
- Dry-run apply calls return diffs and mutation metadata without writing.
- Verify calls report draft health and optional previews.
- Mutations use the same kind, target, and payload shapes as the existing Creator mutate API.
- Mutation recipes provide shallow machine-readable validation before draft writes.
- Agent runs persist full Codex jobs separately from per-pack mutation history.

## Local CLI

Run commands from `brave_game`.

```bash
python scripts/creator_codex.py context
python scripts/creator_codex.py recipes
python scripts/creator_codex.py recipes quest
python scripts/creator_codex.py plan '{"instructions":"Create a starter quest in Brambleford.","scope":{"domains":["quests","items"]}}'
python scripts/creator_codex.py validate '{"mutations":[{"kind":"quest","target":"new_quest_key","payload":{"title":"New Quest"}}]}'
python scripts/creator_run_batch.py /path/to/run.json
python scripts/creator_codex.py verify '{"previews":[{"kind":"quest","args":["new_quest_key"]}]}'
python scripts/creator_codex.py run-create /path/to/run.json
python scripts/creator_codex.py run-list --limit 5
python scripts/creator_codex.py run-show RUN_ID
python scripts/creator_codex.py run-validate RUN_ID
python scripts/creator_codex.py run-dry-run RUN_ID
python scripts/creator_codex.py run-apply RUN_ID
python scripts/creator_codex.py run-verify RUN_ID
python scripts/creator_codex.py run-review RUN_ID --note "Ready for Creator review."
```

## HTTP API

All endpoints require Creator access: staff, superuser, or Developer permission.

`GET /api/content/codex/context`

Returns capabilities, draft health, and links to status and verify endpoints.

Capabilities include `recipes`, a mapping keyed by mutation kind. Each recipe includes target requirements, payload type, required fields, optional fields, reference hints, preview hints, and a minimal example.

`POST /api/content/codex/plan`

Input:

```json
{
  "instructions": "Create a small quest.",
  "scope": {"domains": ["quests", "items"]}
}
```

Returns a review scaffold with `write: false`, `required_review: true`, and an empty `mutations` list.

`POST /api/content/codex/apply`

Input:

```json
{
  "stage": "draft",
  "dry_run": false,
  "mutations": [
    {
      "kind": "quest",
      "target": "quest_key",
      "payload": {}
    }
  ]
}
```

Returns applied mutation metadata, diffs, and draft health. `stage` must be `draft`.

For normal Codex-authored content, prefer Agent Runs or `scripts/creator_run_batch.py`. Direct apply writes draft files but does not create an Agent Run audit card unless a `run_id` is supplied.

Responses also include:

- `touched_domains`: draft domains affected by the mutation bundle.
- `suggested_previews`: preview calls the agent should run before publish review.
- `recipe_warnings`: non-blocking review warnings, such as missing preview checks.

If `run_id` is supplied, the apply result is attached to the agent run as `dry_run` or `apply`.

`POST /api/content/codex/verify`

Input:

```json
{
  "previews": [
    {"kind": "quest", "args": ["quest_key"]}
  ]
}
```

Returns draft health plus requested previews.

If `run_id` is supplied, the verify result is attached to the agent run.

## Agent Runs

Agent run records live in `world/content/packs/core/.agent-runs/`. They are JSON records for review and audit, not live content.

Each run includes:

- `run_id`, timestamps, author, and status.
- Original instructions, scope, plan, and mutation bundle.
- Validation output, dry-run output, apply output, verify output, and review notes.
- Draft mutation history ids and paths after `run-apply`.

Run statuses are `planned`, `validated`, `dry_run`, `applied`, `verified`, `reviewed`, or `failed`.

## Mutation Shape

Each mutation entry has:

- `kind`: Creator mutation kind, such as `quest`, `item`, `room`, `enemy`, or `boss-gate`.
- `target`: Stable content id to create or update.
- `payload`: JSON object accepted by the existing Creator mutate implementation for that kind.
- `note`: Optional human-readable context for review.

The typed recipe layer rejects unknown kinds, missing required targets, missing payloads, wrong top-level payload types, and missing recipe-required fields before calling the mutator. This is not full JSON Schema validation.

## Example Bundle

```json
{
  "mutations": [
    {
      "kind": "item",
      "target": "brambleford_errand_token",
      "payload": {
        "name": "Brambleford Errand Token",
        "kind": "loot",
        "desc": "A stamped token carried by helpful townsfolk."
      }
    },
    {
      "kind": "quest",
      "target": "brambleford_first_errand",
      "payload": {
        "title": "Brambleford First Errand",
        "summary": "Help an NPC pass a small proof of trust through town.",
        "objectives": [
          {"type": "talk_to_npc", "npc_id": "brother_alden", "count": 1}
        ],
        "rewards": {
          "items": [
            {"item": "brambleford_errand_token", "quantity": 1}
          ]
        },
        "next_step": "Bring the token back to the town green and look for the next lead."
      }
    },
    {
      "kind": "dialogue",
      "target": "brother_alden",
      "payload": [
        {
          "id": "brambleford_first_errand",
          "text": "Take this token and prove you can carry a message without stirring panic."
        }
      ]
    }
  ],
  "previews": [
    {"kind": "item", "args": ["brambleford_errand_token"]},
    {"kind": "quest", "args": ["brambleford_first_errand"]},
    {"kind": "dialogue", "args": ["brother_alden"]}
  ]
}
```

## Recommended Codex Workflow

1. Read `context` and check draft health.
2. Read `recipes`, either all recipes or the specific mutation kind needed.
3. Use references and previews to ground target ids.
4. Generate a plan with clear scope and review notes.
5. Build explicit mutations.
6. Run `python scripts/creator_run_batch.py /path/to/run.json`.
7. Confirm the resulting Agent Run appears in Creator Studio.
8. Use the Creator UI to review and publish when ready.

For larger work, use the durable run workflow instead:

1. Create a run with `run-create`.
2. Validate with `run-validate`.
3. Inspect diffs with `run-dry-run`.
4. Write drafts with `run-apply`.
5. Verify previews with `run-verify`.
6. Mark human review with `run-review`.
7. Publish separately from the Creator UI.
