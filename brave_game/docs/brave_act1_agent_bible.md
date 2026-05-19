# Brave Act 1 Agent Bible

## Purpose

This document is the creative source of truth for generating Brave Act 1 content with the Creator API and Codex agent runs. It turns the current live content into explicit guidance so future quests, NPCs, rooms, enemies, items, dialogue, encounters, trophies, and systems hooks extend the same game instead of drifting into unrelated additions.

Use this alongside `docs/creator_agent_contract.md`. The contract explains how to mutate content safely. This bible explains what content should feel like, where it should fit, and how it should advance Act 1.

Current canon override: see `brave_current_canon.md`. If this bible or an archive note conflicts with that file, `brave_current_canon.md` wins.

## Act 1 Vision

Act 1 is the story of Brambleford discovering that its morning alarm is not a single problem. It is a pressure pattern around the town: roads cut, lantern lines failing, old graves waking, goblin crews organizing, bandits claiming the ridge, Blackfen pushing north, and a drowned civic system still enforcing a duty no living person understands.

The player fantasy is local courage becoming organized competence. The hero starts as a useful town hand, earns trust through practical errands, then becomes the person Brambleford sends into harder places when the ordinary watch, chapel, and road crews cannot answer the trouble alone.

The emotional arc should move from:

- "Something is wrong near town."
- "The roads and old protections are failing in connected ways."
- "Brambleford can survive if its people turn scattered fear into disciplined action."
- "The first hard chapter ends when the wrong south light is understood and extinguished, but the world beyond Brambleford is now clearly larger and stranger."

The tone is grounded frontier fantasy with civic strangeness. Brave should feel like a town with ledgers, lantern crews, fences, bells, old routes, and practical people, not like a generic prophecy machine. Magic and mystery are present, but they are usually attached to old public works, local vows, neglected roads, chapel rites, failed duties, or things people once built for good reasons.

## Core Rules

- Keep stakes local before they become mythic. A problem should threaten a road, storehouse, chapel bell, watch route, supply line, family, trade path, lantern system, or known landmark before it gestures at larger forces.
- Treat Brambleford as a working town. New content should imply jobs, habits, arguments, maintenance, fear, records, and people trying to keep each other alive.
- Let humor come from practical understatement, local personalities, and ugly little details. Do not turn threats into jokes or make NPCs speak like modern meme characters.
- Name things with concrete nouns and local texture: Dawn Bell, Fencebreaker Camp, Blackwater Lamp House, Pot-King's Court, Old Stone Path. Avoid abstract fantasy labels unless the game has earned them.
- Make each region teach the player something about the crisis. New content should clarify a threat vector, deepen a faction, introduce a tool, or pay off a prior clue.
- Prefer recoverable proof over exposition. Rewards, trophies, readable objects, and enemy drops should carry evidence back to town.
- Keep generated content playable and connected. Every new item needs placement or use; every enemy needs an encounter or loot role; every NPC needs a room and purpose; every quest needs clear prerequisites and previewable objectives.

## Canon Guardrails

- Do not add removed off-world branch content, references, rooms, enemies, items, readables, portal records, or roadmap hooks.
- Do not create a portal route or Nexus progression path in Act 1.
- The Nexus may appear only as sealed, blocked, inactive Brambleford infrastructure.
- Do not use off-world travel to explain Drowned Weir or Lower Lanternworks content.
- `bridgework_for_joss`, `signal_in_the_scrap`, and `foreman_coilback` belong to Drowned Weir / Lower Lanternworks.
- Foreman Coilback is Drowned Weir maintenance and chain-keeper evidence, not an off-world boss.

## Writing Standard

Brave should read as handcrafted frontier fantasy with a civic pulse. The prose can be lyrical, but it should stay physical: mud, lampglass, ledger ink, tool marks, chapel wax, rainwater, old stone, bad food, and practical hands doing work under pressure.

Room and readable prose should:

- use concrete objects before abstract mood.
- vary sentence length so the line has a spoken rhythm: a long image can land harder when followed by a short sentence with weight.
- give each region one dominant pressure: Brambleford is organized fear, Goblin Road is sabotage, Whispering Woods is arranged silence, Old Barrow Field is disturbed memory, Ruined Watchtower is human control, Goblin Warrens is hungry logistics, Blackfen is misleading water, and Drowned Weir is civic machinery still obeying a dead rule.
- avoid leaning too often on the same abstract construction, especially "feels like," "looks like," "as if," and places that "think," "remember," or "intend." Those moves are allowed, but they should feel earned.
- let the poetic quality come from cadence, image, and compression rather than rhyme, ornate diction, or vague mysticism.

Dialogue should:

- reveal what the speaker notices first.
- carry the speaker's job, worry, and private bias.
- stay playable and concise; the player should know what changed and what to do.
- make different people disagree through emphasis, not through random contradiction. Harl sees tactics, Alden sees mercy, Joss sees mechanisms, Elric sees public consequence, Maybelle sees harm and recovery, Mira sees route truth.

Major Act 1 voice anchors:

- Harl: clipped, tactical, dry, protective through discipline.
- Alden: earnest, moral, brave after fear, attentive to names and mercy.
- Joss: precise, technical, anxious to name truth correctly.
- Elric: restrained civic consequence, ledgers, public risk, controlled worry.
- Maybelle: care, recovery, grief, preventable harm, practical tenderness.
- Mira: routes, weather, tracks, field signs, danger without drama.
- Pib: food, stores, hospitality, jokes that reveal worry instead of hiding it.
- Leda: gear, weather, fair trade, practical judgment.
- Torren: repair, metal, earned usefulness, blunt assessment.
- Veska: mechanisms, clamps, traps, argument-by-evidence.
- Elira: discipline, pattern recognition, patience with standards.
- Tamsin: triage, training, command voice under alarm.
- Nella: supplies, preparedness, sharp inventory sense.
- Peep: errands, routes, quick observation, nervous competence.
- Brask: fight lessons, timing, rough patience.

## Act 1 Progression

### 1. Brambleford and Wayfarer's Yard

Role: tutorial, town trust, first alarm response.

Current anchors:

- `practice_makes_heroes`
- `bell_before_the_road`
- `rats_in_the_kettle`
- Wayfarer's Yard, Mastery Hall, Lantern Rest Inn, Chapel of the Dawn Bell, East Gate, Town Green, Town Hall, Great Observatory, Lower Lanternworks
- Captain Harl Rowan, Brother Alden, Mayor Elric Thorne, Joss Veller, Sister Maybelle, Mira Fenleaf, Mender Veska Flint, Uncle Pib Underbough

What this region establishes:

- Brambleford is competent but stretched.
- The player earns trust by handling immediate, visible problems.
- The chapel, watch, observatory, inn, and town hall each see the crisis through a different practical lens.
- The road and lantern systems matter before the player understands why.

Allowed new content:

- Small civic errands that teach a mechanic or introduce a character.
- Follow-up dialogue for existing NPCs reacting to published quest progress.
- Minor items that represent town trust, emergency supplies, tools, notices, tokens, or keepsakes.
- Short cellar, yard, town, or training encounters only if they support the opening alarm.

Avoid:

- Large hidden villains inside Brambleford.
- New global lore dumps.
- New town NPCs who duplicate the roles of Harl, Alden, Elric, Joss, Maybelle, Mira, Veska, or Pib without a distinct civic function.

### 2. Goblin Road

Role: first road threat, visible sabotage, transition from nuisance to organized danger.

Current anchors:

- `roadside_howls`
- `fencebreakers`
- `ruk_the_fence_cutter`
- East Gate, Trailhead, Old Fence Line, Wolf Turn, Fencebreaker Camp
- Ruk the Fence-Cutter boss gate

What this region establishes:

- The road is being physically damaged.
- Goblin crews are not random raiders; they are cutting infrastructure.
- Beast and goblin pressure overlap, showing that the town's protections are weakening in more than one way.

Allowed new content:

- Road patrol side quests, fence repair hooks, scouting readable signs, lost wagon evidence.
- Goblin tools, cut rails, road charms, stolen supplies, rough field trophies.
- Enemies with `goblin`, `raider`, `wolf`, `skirmisher`, or `brute` tags.

Avoid:

- Making Ruk more important than a regional boss. He is a hard local answer, not the Act 1 mastermind.
- Adding another boss in this region unless it is clearly optional and smaller than Ruk.

### 3. Whispering Woods

Role: old local unease, natural danger, the west path into deeper Act 1 trouble.

Current anchors:

- `what_whispers_in_the_wood`
- `herbs_for_sister_maybelle`
- `greymaws_trail`
- Trailhead, Old Stone Path, Briar Glade, Greymaw's Hollow

What this region establishes:

- The old stones and woods are arranged, not merely wild.
- Brambleford depends on the woods for medicine and routes, so fear here becomes a supply problem.
- The trouble west of town points toward barrows and older vows.

Allowed new content:

- Herb gathering, wardstone investigation, missing trail markers, Maybelle/Mira follow-ups.
- Beasts, spiders, mosslings, briar imps, old protective charms, poultice ingredients.
- Readables or environmental clues that point to the barrow field without overexplaining it.

Avoid:

- Turning the woods into a separate fae campaign.
- Introducing a forest court or major faction that competes with Act 1's civic-lantern crisis.

### 4. Old Barrow Field

Role: old duty, chapel fear, proof that neglected vows can wake.

Current anchors:

- `lanterns_at_dusk`
- `do_not_disturb_the_dead`
- `the_knight_without_rest`
- Causeway, Marker Row, Barrow Circle, Sunken Dais
- Brother Alden and Sir Edric

What this region establishes:

- Brambleford's protections include memory, prayer, names, and burial respect.
- The dead are not random monsters; they are failed rest, unfinished duty, or broken warding.
- The chapel has useful courage but incomplete answers.

Allowed new content:

- Marker stone readings, chapel rites, recovered names, votive items, grave-light enemy variants.
- Side quests that ask the player to confirm, carry, restore, or return proof.
- Enemies with `undead`, `wisp`, `shade`, `skeleton`, `knight`, or `support` tags.

Avoid:

- Necromancer explanations unless they remain local and evidence-based.
- Reusing Sir Edric's role for another fallen knight in Act 1.

### 5. Ruined Watchtower

Role: human ambition, road control, proof that ordinary people can exploit supernatural panic.

Current anchors:

- `smoke_on_the_ridge`
- `loose_arrows`
- `captain_varn_blackreed`
- Watchtower Approach, Archer's Ledge, Breach Yard, Cracked Stairs, Blackreed's Roost

What this region establishes:

- Not every Act 1 threat is ancient or magical.
- The road crisis creates opportunity for bandits and commanders.
- Brambleford's border structures can be repurposed against it.

Allowed new content:

- Bandit supply ledgers, captured road signs, watchtower history, prisoner or scout hooks.
- Enemies with `bandit`, `blackreed`, `archer`, `scout`, `commander`, or `hound` tags.
- Items that feel like road-war trophies, arrows, blackreed marks, ledgers, stolen cargo, or signal tools.

Avoid:

- Making Blackreed a national army.
- Turning the watchtower into a second town hub during Act 1.

### 6. Goblin Warrens

Role: escalation below the road, hunger as social order, ugly organized pressure.

Current anchors:

- `below_the_fencebreakers`
- `gutters_and_hexes`
- `the_pot_kings_feast`
- Sinkmouth Cut, Torchgut Tunnel, Sludge Run, Bone Midden, Feast Hall, Pot-King's Court

What this region establishes:

- Ruk's road crew was only the surface of a larger goblin ecology.
- The warrens are domestic, gross, and organized by appetite.
- Grubnak is a regional capstone threat whose defeat makes the road safer but does not solve Act 1.

Allowed new content:

- Tunnel cleanup, stolen food, crude recipes, hex tokens, prisoner scraps, goblin logistics.
- Enemies with `goblin`, `warren`, `hexer`, `bat`, `slime`, `brute`, or `potking` tags.
- Food-adjacent rewards, crafting notes, charms, battered tools, and ugly trophies.

Avoid:

- Over-polishing goblin culture. It should be vivid and functional, not noble or elaborate.
- Introducing a deeper goblin king beyond Grubnak in Act 1.

### 7. Blackfen

Role: southern pressure, marsh ecology, evidence that the wrong light has moved beyond town.

Current anchors:

- `bogwater_rumors`
- `lights_in_the_reeds`
- `miretooths_claim`
- Fenreach Track, Reedflats, Carrion Rise, Boglight Hollow, Miretooth's Wallow

What this region establishes:

- The crisis has seeped into land and water.
- Blackfen threats are predatory, patient, and hard to map.
- Miretooth is a biological warning sign before the player reaches civic machinery again.

Allowed new content:

- Survey markers, marsh guide hooks, carrion clues, boglight misdirection, Joss/Mira field notes.
- Enemies with `blackfen`, `hound`, `mire`, `crow`, `plant`, `spirit`, or `beast` tags.
- Items made of resin, jawbone, reed marks, silt hooks, marsh roots, fenlight, or old survey tools.

Avoid:

- Making the marsh purely spooky. It should remain wet, physical, hungry, and navigationally hostile.
- Introducing another apex predator that competes with Miretooth.

### 8. Drowned Weir and Lower Lanternworks

Role: Act 1 revelation and capstone, old public works enforcing a broken duty.

Current anchors:

- `bridgework_for_joss`
- `signal_in_the_scrap`
- `foreman_coilback`
- `the_south_light`
- `locks_under_blackwater`
- `the_hollow_lantern`
- Lower Lanternworks, Drowned Causeway, Lantern Weir, Sluice Walk, Sunken Lock, Blackwater Lamp House

What this region establishes:

- Brambleford's road-light system is old civic infrastructure, not just decoration.
- The wrong south light is tied to a failed or abandoned maintenance duty.
- Act 1 resolves when the player exposes and extinguishes the Hollow Lantern, closing Brambleford's first hard chapter.

Allowed new content:

- Lensglass recovery, maintenance maps, broken ward clamps, blackwater mechanisms, Joss investigations.
- Enemies with `weir`, `construct`, `undead`, `warder`, `chainkeeper`, `spirit`, or `wisp` tags.
- Story items, trophies, and proof objects that connect machinery to civic records.

Avoid:

- Revealing the entire cosmology behind the lanternworks in Act 1.
- Making the Hollow Lantern a portal, Nexus route, or handoff to a new campaign.

## NPC and Faction Guide

Use existing NPCs as anchors instead of creating unnecessary replacements.

- Captain Harl Rowan: watch discipline, combat priorities, road security, practical orders.
- Brother Alden: chapel courage, fear managed through ritual, local memory, brave uncertainty.
- Mayor Elric Thorne: civic accountability, public morale, town-scale consequences.
- Joss Veller: observatory, lanternwork records, technical curiosity, south-line investigation.
- Sister Maybelle: medicine, recovery, compassion with practical limits.
- Mira Fenleaf: woods and marsh knowledge, trail warnings, fieldcraft.
- Mender Veska Flint: repair, forge, mechanisms, practical object logic.
- Uncle Pib Underbough: small trades, comic warmth, fishing and town odd jobs.
- Mistress Elira Thorne: inn, supplies, gossip filtered through hospitality and local pressure.

New NPC rules:

- Give each new NPC a civic function: courier, lamplighter, ledger clerk, retired road hand, chapel helper, ferryman, apprentice, quartermaster, scout, mason, cook, salvage worker.
- Place them in a specific existing room unless adding a new room is part of the approved content batch.
- Give them a reason to care about at least one existing region or quest chain.
- Dialogue should be short, grounded, and actionable. One good line is better than a lore speech.
- If the NPC starts a quest, their quest should affect their room, job, or known relationships.

## Quest Design Rules

Act 1 quests should usually be one of these shapes:

- Civic errand: help a person or town function under pressure.
- Scout and report: inspect a room or route, then return with proof.
- Thin the threat: defeat enemies that block a route or threaten a supply line.
- Recover proof: bring back an item that confirms what happened.
- Capstone: enter the deepest room of a region and defeat the named threat.
- Bridge quest: connect one region's answer to the next region's question.

Quest payload guidance:

- Use stable snake_case ids that name the local action or threat.
- Always include `title`, `summary`, and a clear `next_step`.
- Use `prerequisites` to preserve Act 1 progression unless the quest is deliberately a side quest.
- Use `region` or quest region mapping that matches the playable geography.
- Prefer objectives that preview well: `talk_to_npc`, `visit_room`, `collect_item`, `defeat_enemy`.
- Rewards should include XP and silver when appropriate, plus at most one primary item unless the quest is a capstone.
- New quest reward items must be created in the same Agent Run or already exist.

Do not create:

- Orphan side quests with no region purpose.
- Multiple new starting quests without a clear reason.
- Objectives requiring content that the Creator API cannot preview or validate.
- Quest text that announces hidden lore the player has not earned.

## Enemy and Encounter Rules

Enemies are part of an ecology. They need a region, a role, and a reason to be fought.

Use existing tag families when possible:

- Road and goblins: `goblin`, `raider`, `wolf`, `skirmisher`, `brute`
- Woods: `beast`, `forest`, `spider`, `plant`, `fey`, `support`
- Barrows: `undead`, `wisp`, `shade`, `skeleton`, `knight`
- Watchtower: `bandit`, `blackreed`, `archer`, `scout`, `commander`
- Warrens: `goblin`, `warren`, `hexer`, `bat`, `slime`, `potking`
- Blackfen: `blackfen`, `hound`, `mire`, `crow`, `plant`, `spirit`
- Weir: `weir`, `construct`, `undead`, `warder`, `chainkeeper`, `wisp`

Enemy design rules:

- Every new enemy must be used in a room encounter or roaming party in the same content batch.
- Loot should be local and useful: claws, charms, scraps, lensglass, roots, notes, tools, marked tokens.
- Bosses should be rare. Act 1 already has Ruk, Old Greymaw, Sir Edric, Captain Varn, Grubnak, Miretooth, Foreman Coilback, and Hollow Lantern.
- Do not create a new Act 1 boss unless the batch explicitly adds an optional side capstone below those anchors.

Encounter design rules:

- Room encounters should match the room's region and story purpose.
- Encounter titles should be concrete and sensory.
- Intros should describe immediate positioning or danger, not backstory.
- Avoid mixing unrelated enemies just for variety. Mixed encounters need a local reason.

## Item and Reward Rules

Items should act as proof, tools, trophies, materials, or keepsakes.

Good Act 1 item categories:

- Story proof: signets, standards, lantern prisms, cores, jawbones, ledgers.
- Civic tools: repair clamps, field tokens, road marks, chapel candles, survey tags.
- Craft materials: glass shards, rivets, resin clots, roots, thread, scraps, hooks.
- Modest gear: town-made weapons, repaired armor, charms, practical consumables.
- Trophies: capstone proof mounted in the Trophy Hall or referenced by systems.

Reward rules:

- Use `rarity: story` for proof objects that should matter narratively.
- Use common/uncommon loot for repeatable drops.
- Keep values modest in early Brambleford content.
- Avoid powerful gear from small errands.
- If an item is only a quest reward, make its summary explain why the town values it.
- Avoid orphaned items. If a new item is not used by a quest, enemy loot, recipe, fishing system, trophy, or starting equipment, it needs an intentional placement note.

## Dialogue and Readable Rules

Dialogue should help the player understand what to do, why it matters locally, and how the speaker sees the crisis.

Dialogue rules:

- Keep lines compact. Most talk rules should be one paragraph.
- Use conditional entries tied to active or completed quests when possible.
- Let NPC personality change word choice, not the facts of the world.
- Harl is direct; Alden is earnest; Joss is precise; Elric thinks in town consequences; Maybelle thinks in recovery; Mira thinks in routes and weathered warnings.
- Do not have every NPC explain the main plot. Most people only know their job and what went wrong near it.

Readable rules:

- Readables should be environmental proof: plaques, notices, ledgers, maps, stones, warning signs, labels.
- They should be short enough to reward reading in play.
- They should add one concrete fact, warning, or clue.

## Creator API Generation Checklist

Before creating a multi-domain Agent Run:

1. Run `python scripts/creator_codex.py context` and confirm draft health has no validation errors.
2. Inspect references for rooms, entities, quests, items, enemies, and enemy tags relevant to the target region.
3. Choose a narrow Act 1 purpose: civic errand, bridge quest, side proof, encounter enrichment, or region follow-up.
4. Build explicit mutations. For a full content bundle, use only the domains needed: `world`, `items`, `quests`, `dialogue`, `encounters`, and optional `systems`.
5. Include previews for every new quest, item, enemy, encounter room, dialogue target, and boss gate/trophy if used.
6. Dry-run first. Inspect diffs for accidental rewrites, duplicate ids, orphaned content, missing references, and progression breaks.
7. Apply to draft only.
8. Verify draft health and previews.
9. Review the Agent Run in Creator Studio.
10. Publish only after validation is clean and the run has human review notes.

Recommended prompt shape for future Codex runs:

```text
Use docs/brave_act1_agent_bible.md and docs/creator_agent_contract.md.
Create one Brave Act 1 Creator API Agent Run for [region/purpose].
Treat live content as canon.
Write draft mutations only.
Include [quest/NPC/items/enemies/encounters/dialogue] as needed.
Use existing rooms unless explicitly adding new rooms.
Keep the content connected to [specific current quest or NPC].
Run validate, dry-run, apply, and verify with previews.
Stop for Creator Studio review before publish unless instructed otherwise.
```

## Content Batch Templates

### Small Side Quest

Use when adding one focused piece of playable content to an existing region.

- 1 quest
- 0-1 new NPC or existing NPC dialogue
- 1 reward item or proof item
- Optional readable
- Optional one room encounter update

Best for: Brambleford errands, woods herbs, road repairs, chapel follow-ups, observatory records.

### Region Enrichment

Use when a region needs more texture but not a new capstone.

- 1 bridge or side quest
- 1-2 enemies or one new encounter composition
- 1-3 loot/material items
- 1 readable or dialogue update
- Room encounter placement for every enemy

Best for: Goblin Road, Whispering Woods, Blackfen, Drowned Weir approach.

### Capstone Support

Use when strengthening the lead-up to an existing boss.

- 1 prerequisite or optional setup quest
- 1 proof item
- 1 dialogue update for the relevant town anchor
- 1 encounter update near the boss route
- No new boss unless specifically approved

Best for: Ruk, Greymaw, Sir Edric, Captain Varn, Grubnak, Miretooth, Foreman Coilback, Hollow Lantern.

## Current Canon Snapshot

Act 1 live content currently includes:

- 27 quests across Brambleford, Goblin Road, Whispering Woods, Old Barrow Field, Ruined Watchtower, Goblin Warrens, Blackfen, and Drowned Weir.
- 55 rooms, with major hubs in Brambleford and Wayfarer's Yard.
- 42 enemy templates and room encounter tables across the major regions.
- 9 dialogue entities.
- 134 item templates.
- One formal boss gate: `ruk_fence_cutter`.
- Trophy hooks for Blackreed, Blackwater Beacon Core, Hollow Lantern Prism, Miretooth, and Pot-King.

Draft health was clean when this bible was created, with readiness notes still identifying some non-blocking content polish opportunities such as missing reverse paths, unused enemies, orphaned items, and readable entities without text. Future Creator API work should avoid adding more of those issues.
