# Brave Creator API Runbook

## Purpose

This runbook explains how to operate the Brave Creator API with Codex CLI for content work. Use it when creating, reviewing, verifying, and publishing generated content batches.

For creative direction, read `docs/brave_act1_agent_bible.md`. For production order, read `docs/brave_act1_content_roadmap.md`. For endpoint and mutation details, read `docs/creator_agent_contract.md`.

## Default Policy

- Use Creator API Agent Runs for multi-domain content.
- Write to draft packs only.
- Keep each run small enough to review in one Creator Studio pass.
- Prefer existing rooms, NPCs, enemies, and items unless the roadmap batch calls for new ones.
- Preview every new or touched content target.
- Publish only after validation is clean and review notes exist.

## Before Starting a Run

From `brave_game`, check the current Creator context:

```bash
python scripts/creator_codex.py context
```

Confirm:

- `ok` is `true`.
- `health.validation_errors` is empty.
- The intended domains are supported by `capabilities.mutation_kinds`.
- Current readiness warnings are understood and not made worse by the planned batch.

If validation errors exist before the run, stop and fix or document them first. Do not create new content on top of invalid drafts unless the run's purpose is to repair validation.

## Choosing Run Scope

Use one of these scopes:

- Small side quest: `items`, `quests`, optional `dialogue`, optional `read`.
- NPC quest bundle: `world`, `dialogue`, `items`, `quests`.
- Encounter enrichment: `items`, `encounters`, optional `quests`, optional `dialogue`.
- Readable cleanup: `dialogue` only through `read` mutations.
- Trophy or systems polish: `systems`, optional `dialogue`, optional `read`.

Avoid mixing too many intentions. A run that adds a new NPC, a new quest, two enemies, multiple items, a boss, a trophy, and a new region is too large for routine review.

## Prompt Pattern for Future Codex Chats

Use this format when asking Codex to create content:

```text
Use the Brave Creator API in /home/jcthom85/Brave/brave_game.
Read docs/brave_act1_agent_bible.md, docs/brave_act1_content_roadmap.md, and docs/creator_agent_contract.md.
Create one Agent Run for [roadmap batch or exact content goal].
Treat live content as canon.
Write draft mutations only.
Use existing rooms unless explicitly necessary.
Do not publish until I review unless I explicitly say auto-publish clean runs.
Run validate, dry-run, apply, and verify with previews.
```

For a highly specific content request, add:

```text
Must include:
- Quest hook:
- NPC:
- Region/room:
- Items:
- Enemies or encounters:
- Prerequisite quest:
- Desired reward:
- Tone notes:
```

## Agent Run Workflow

### 1. Create the run input

Create a JSON payload with `instructions`, `scope`, `mutations`, and optional `previews`.

The mutation shape is:

```json
{
  "kind": "quest",
  "target": "stable_snake_case_id",
  "payload": {},
  "note": "Review context for humans."
}
```

### 2. Create the durable run

```bash
python scripts/creator_codex.py run-create /path/to/run.json
```

Save the returned `run_id`.

### 3. Validate

```bash
python scripts/creator_codex.py run-validate RUN_ID
```

Fix all contract errors before continuing. Contract validation catches missing targets, wrong top-level payload types, unsupported mutation kinds, and missing recipe-required fields. It is not a full content validator.

### 4. Dry-run

```bash
python scripts/creator_codex.py run-dry-run RUN_ID
```

Inspect:

- Diff scope.
- Touched domains.
- Suggested previews.
- Recipe warnings.
- Any unexpected broad rewrites.

Do not apply if the dry-run changes unrelated content.

### 5. Apply to draft

```bash
python scripts/creator_codex.py run-apply RUN_ID
```

This writes draft packs only. It should not publish live content.

### 6. Verify

```bash
python scripts/creator_codex.py run-verify RUN_ID
```

Verify should include previews for all important touched targets:

- New or touched quest ids.
- New or touched item ids.
- New or touched enemy ids.
- New or touched room encounter room ids.
- New or touched dialogue/readable entity ids.
- Any boss gate, trophy, recipe, fishing, portal, or system target.

### 7. Review in Creator Studio

Open Creator Studio and inspect the Agent Run panel.

Review:

- Instructions match the intended batch.
- Status is applied or verified.
- Touched domains are expected.
- Preview payloads find the new content.
- Draft health is clean.
- The content follows the Act 1 Agent Bible.

Add a human review note describing what was checked.

### 8. Publish

Use Creator Studio's Agent Run publish action or the normal Draft Workflow publish controls after review.

Publish should be blocked if draft validation fails. If publish is blocked, inspect `validation_errors`, fix the draft issue, verify again, then retry publish.

## Review Checklist

Before approving a run:

- IDs are stable, snake_case, and region-appropriate.
- Quest prerequisites preserve Act 1 progression.
- Every reward item exists.
- Every collection objective references an existing item.
- Every talk objective references an existing NPC/entity.
- Every defeat objective uses an existing enemy tag with matching enemies.
- Every new enemy appears in a room encounter or roaming party.
- Every new item has placement, use, loot, quest linkage, recipe linkage, or clear story purpose.
- Dialogue is concise and assigned to the right NPC.
- Readables add one useful clue or instruction.
- No new boss was added unless explicitly requested.
- No unrelated content was rewritten.

## Common Failure Modes

### Unknown item in quest rewards

Cause: a quest rewards an item that does not exist in live or draft items.

Fix: create the item in the same run or change the reward to an existing item.

### Unknown NPC in talk objective

Cause: `npc_id` does not exist in world entities.

Fix: create the entity in the same run, use an existing NPC, or change the objective type.

### Enemy not used by room encounter

Cause: a new enemy template exists without placement.

Fix: add it to a room encounter or roaming party in the same run.

### Orphan item readiness warning

Cause: an item exists but has no quest, loot, system, recipe, or placement linkage.

Fix: link it to a quest, enemy loot, recipe, system, trophy, readable context, or remove it if unnecessary.

### Publish blocked

Cause: draft content fails full validation.

Fix: do not bypass publish. Read validation errors, repair drafts, verify, and retry.

### Broad unexpected diff

Cause: the mutation touched a large shared payload or overwrote a list without preserving existing entries.

Fix: stop before apply, narrow the mutation, and dry-run again.

## Safe Mutation Patterns

### Existing NPC Starts a Small Quest

Use:

- `item` for the reward/proof.
- `quest` for the quest.
- `dialogue` for the NPC's active/completed lines.

Preview:

- item
- quest
- dialogue target

### New NPC in Existing Room

Use:

- `entity` with `kind: "npc"` and an existing `location`.
- `dialogue` for initial lines.
- Optional `quest` if the NPC has a playable reason to exist.

Preview:

- room containing the NPC
- dialogue target
- quest if used

### New Enemy in Existing Region

Use:

- `enemy` with local tags and loot.
- `encounters` for the room table where it appears.
- Optional `item` for new loot if needed.

Preview:

- enemy
- encounter room
- item if new

### Readable Cleanup

Use:

- `read` mutation for each readable entity.

Preview:

- readable target

Keep each readable short and concrete.

## Publish Policy Options

Default: draft review first.

- Create Agent Run.
- Validate, dry-run, apply, verify.
- Stop for human review.
- Publish from Creator Studio after review.

Auto-publish clean runs are allowed only when explicitly requested. Even then, the run must validate, dry-run, apply, verify, and record its publish result.

Draft-only runs are useful for experiments, but they should be reviewed or reverted before more content is stacked on top.

## Command Quick Reference

```bash
python scripts/creator_codex.py context
python scripts/creator_codex.py recipes
python scripts/creator_codex.py recipes quest
python scripts/creator_codex.py run-create /path/to/run.json
python scripts/creator_codex.py run-list --limit 10
python scripts/creator_codex.py run-show RUN_ID
python scripts/creator_codex.py run-validate RUN_ID
python scripts/creator_codex.py run-dry-run RUN_ID
python scripts/creator_codex.py run-apply RUN_ID
python scripts/creator_codex.py run-verify RUN_ID
python scripts/creator_codex.py run-review RUN_ID --note "Reviewed quest, item, dialogue previews and clean draft health."
```

## Studio Review Notes Template

```text
Reviewed [batch name].
Checked previews for [quest/item/dialogue/enemy/encounter/readable ids].
Confirmed draft health has no validation errors.
Confirmed content follows Act 1 Agent Bible and touches only expected domains.
Ready to publish / needs revision because [reason].
```

## When to Stop

Stop and ask for direction if:

- The requested content conflicts with `docs/brave_act1_agent_bible.md`.
- A run would need a new region, new boss, or major progression rewrite.
- Existing drafts are invalid before the run starts.
- Dry-run diffs include unrelated changes.
- Validation errors imply a schema or builder limitation rather than a content typo.
- The generated content needs product judgment, such as whether to reveal a major mystery.
