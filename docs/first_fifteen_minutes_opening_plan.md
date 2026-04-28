# First Fifteen Minutes Opening Plan

This document focuses on the first-time player experience for `Brave`, from new-character entry through the first real town job. It is a design and pacing plan only; it does not prescribe code changes yet.

## Current Evaluation

The intended content direction is already strong: `Lanternfall` gives Brave an urgent first image, Wayfarer's Yard teaches the actual verbs, and the first road chapter can connect the cellar, cut fences, dead lantern, and Ruk into one coherent opening.

The problem is presentation and sequencing.

A new player should not feel like they have been dropped into `Training Yard` with a quest list and no reason to care. They need an immediate event, a person addressing them, and a clear first action. If the first visible goal is `Rats in the Kettle`, the game risks feeling like a generic RPG chore before it has earned the player's attention.

The current live logic appears to distinguish two cases:

- First-account characters start in `Wayfarer's Yard` with tutorial state active.
- Later characters on an account that has completed the tutorial start in `Training Yard`.

That second case explains the bad experience: a new character can still feel like a new player moment, but the game treats them as tutorial-skipped and gives them a quiet handoff. Even if the account has seen the tutorial before, the character still needs a dramatic first beat.

Quest state also needs sharper staging. `Practice Makes Heroes` should be the visible opening objective. `Rats in the Kettle` can be the first town job, but it should not read as the character's starting premise. The rat cellar should be framed as consequence: the alarm has stirred the stores, the road may be cut, and food now matters.

## Opening Goal

The first fifteen minutes should make the player think:

- "Something happened before I arrived."
- "Brambleford is warm, specific, and worth protecting."
- "I know what to do next."
- "The tutorial is part of the emergency, not separate from the game."
- "The first combat and first rat job are connected to a bigger first-chapter problem."

The opening should be fast, readable, and playable. Brave should not front-load lore. It should front-load a situation.

## Recommended Shape

Use `Lanternfall` as the universal new-character opening, including tutorial-skipped characters.

The first screen should show:

1. A bell before dawn.
2. A south road lantern gone black.
3. A damaged cart dragged through the gate.
4. Sergeant Tamsin or Captain Harl giving the player one concrete action.

The first action should be personal and immediate: talk to the person in front of you, check your kit, or report in. The player should never have to infer the call to action from a room description alone.

## First Fifteen Minute Beat Sheet

### 0:00 To 1:00 - The Hook

The player starts on an authored opening beat, not a neutral room.

Required first impression:

- The town bell is ringing.
- The road is damaged.
- The south lantern is out.
- Someone is speaking directly to the player.

Suggested first prompt:

`Talk to Sergeant Tamsin` for first-account tutorial characters.

`Talk to Captain Harl` for tutorial-skipped characters starting in Training Yard.

Do not show `Rats in the Kettle` as the primary opening hook. If the journal exists immediately, its tracked entry should be `Lanternfall` or `Practice Makes Heroes`, with language about reporting in after the alarm.

### 1:00 To 4:00 - Orientation Under Pressure

The player learns movement, talk, and room reading because the yard is organizing after the alarm.

This should feel like triage:

- Tamsin sends the player to the shed.
- The shed shows field preparation, not abstract inventory teaching.
- The player returns with a sense that the town is mobilizing.

The player should act every few lines. Avoid long speeches.

### 4:00 To 8:00 - Kit And Identity

The player checks gear, pack, and class identity.

This is where Brave should start showing why character choice matters:

- Nella checks whether the player has usable gear.
- Brask names the player's class trick in plain language.
- The UI or text should make the player feel they are a specific hero, not a generic trainee.

The teaching is still practical: know your gear, know your pack, know your class move.

### 8:00 To 11:00 - First Controlled Fight

The vermin pen fight should stay small, but it should not feel random.

Frame it as a symptom:

- The same wrong pulse that hit the road has rattled the pens.
- The player is proving they can handle a live problem while Brask watches.
- The goal is confidence, not danger.

This is the first combat promise: Brave is tactical but readable. The player should learn target reading, basic attack, class ability, victory, and recovery.

### 11:00 To 13:00 - Report To Harl

Harl should convert the tutorial into chapter purpose.

The message should be:

- You can stand.
- The town needs hands.
- The cellar is first because food matters if the road is cut.
- The road comes next.
- The black lantern remains the question.

This handoff is where `Practice Makes Heroes` completes and the first real job unlocks.

### 13:00 To 15:00 - First Town Job Setup

Only now should `Rats in the Kettle` become the tracked focus.

The rat cellar should be sold as a Brambleford problem, not a starter MMO chore:

- Uncle Pib is funny, but not frivolous.
- The rats threaten grain and flour.
- The road problem makes supplies strategic.
- The cellar fight proves the alarm has consequences inside the walls.

The first fifteen minutes can end with the player entering the inn/cellar or winning the cellar fight, depending on pace. Either is acceptable if the player understands why it matters.

## Quest Presentation Rules

- The player starts with a clear opening objective, not a bundle of future quests.
- `Rats in the Kettle` should be locked, hidden, or visually secondary until `Practice Makes Heroes` is resolved.
- If locked quests are visible in the journal, they should not look like current assignments.
- The tracked quest should always answer "what should I do now?"
- The next lead should name a person and place, not just a system verb.

Recommended visible sequence:

1. `Lanternfall` or `Practice Makes Heroes`: talk to Tamsin/Harl and report after the alarm.
2. `Rats in the Kettle`: help Uncle Pib protect food stores.
3. `Roadside Howls`: meet Mira at East Gate and inspect the road.
4. `Fencebreakers`: stop the cutters.
5. `Ruk the Fence-Cutter`: confront the first named culprit.

## New Character Versus New Player

Brave should treat every new character as deserving a strong opening, even when the account has completed the tutorial.

First-account character:

- Full Wayfarer's Yard onboarding.
- Lanternfall intro pages or equivalent terminal text.
- Tamsin is the first face.

Later character on same account:

- Short Lanternfall recap.
- Spawn can remain Training Yard if desired.
- Harl must immediately provide exposition and a call to action.
- The player should not silently appear in the yard.

This avoids forcing repeated tutorials while preserving drama.

## Rat Quest Decision

`Rats in the Kettle` should remain in the first fifteen minutes, but it should not be the starting premise.

Keep it because:

- It gives a safe first real combat space after the controlled fight.
- It protects Brambleford's cozy tone.
- It makes the town's practical needs visible.
- It creates a good tonal contrast before the road opens.

Fix its framing because:

- "Kill rats" is a weak first promise.
- The player has not yet learned why the town matters.
- It can feel disconnected from the dead lantern unless Harl and Pib explicitly connect supplies, alarm, and road damage.

The cellar should feel like the first consequence of Lanternfall, not a random errand.

## Quality Bar

The first fifteen minutes are working when:

- The first screen has a memorable event.
- The first NPC gives a direct action.
- The player understands movement, talk, inventory, basic combat, class ability, and rest.
- The player knows Brambleford is under pressure.
- The rat cellar feels connected to the road alarm.
- The player reaches Mira's road lead with curiosity instead of checklist fatigue.

## Open Questions

- Should `Lanternfall` become a formal quest, or remain tutorial/opening presentation around `Practice Makes Heroes`?
- Should tutorial-skipped characters get a one-screen recap modal, a Harl monologue, or both?
- Should locked future quests be hidden from fresh journals until their prerequisites are close?
- Should the first fifteen minutes include a small visual/audio sting for the bell and dead lantern in the web client?
- Should `Practice Makes Heroes` be renamed to something less tutorial-coded, such as `After The Bell` or `Lanternfall`?

## Next Design Pass

The next pass should turn this into implementation-ready requirements:

- exact first-screen copy for first-account characters
- exact first-screen copy for tutorial-skipped new characters
- quest visibility rules for fresh journals
- Harl, Tamsin, Nella, Brask, and Pib dialogue revisions
- acceptance tests for first spawn, tutorial-skipped spawn, tracked quest, and rat quest unlock timing
