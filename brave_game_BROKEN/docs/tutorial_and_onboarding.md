# Tutorial And Onboarding

## Purpose

`Brave` needs a real first-time-player path.

Right now, a new player can enter the world and start doing things, but the game does not yet teach the player how to read the room view, move with cardinal directions, use commands confidently, understand the minimap, fight, or group up with family members. That is too much friction for the kind of game `Brave` wants to be.

This document defines the recommended tutorial start place and the broader beginner experience. It is meant to become the source of truth for onboarding design.

## Design Goals

The tutorial and beginner section should:

- teach the game through play, not long explanations
- stay fully in-universe
- work for solo players and family co-op
- take about 10 to 15 minutes on a first character
- be skippable for veteran players and alt characters
- hand the player cleanly into Brambleford without feeling like a separate game

## Non-Goals

The tutorial should not:

- explain every command in the game
- become a giant prologue zone
- replace the first real town and wilderness content
- lock players into a long mandatory sequence on every new character

## Recommended Structure

`Brave` should have two connected onboarding layers:

1. A short tutorial start place for the first 10 to 15 minutes.
2. A curated beginner section covering the first hour or two of play.

The short tutorial teaches controls and expectations.

The beginner section teaches the actual game loop.

## Flow, Pacing, And Polish Rules

This section is the quality bar for implementation.

The tutorial should not just exist. It should feel good.

### Flow Rules

- Every room should answer one question for the player.
- Every mentor should point clearly to the next action.
- The next destination should almost never be ambiguous.
- The player should feel pulled forward, not left to wonder which of six commands matters.
- Every step should end with a clean handoff to the next person or place.

### Pacing Rules

The tutorial should alternate between these rhythms:

1. brief instruction
2. immediate action
3. short acknowledgement
4. next instruction

Do not stack multiple explanation-heavy beats back to back.

Recommended pacing profile:

- minute 0 to 2: orient and move
- minute 2 to 5: inspect gear, pack, and one readable
- minute 5 to 9: learn combat in one controlled burst
- minute 9 to 12: optional family-play lesson and town handoff

The player should do something new every couple of minutes.

### Polish Rules

- No room should feel like filler.
- No mentor speech should waste the player's time.
- No objective should exist only because "tutorials usually have one."
- The tutorial should never feel longer than the lesson it is teaching.
- If a player already understands a step, the game should let them clear it quickly.

### Friction Rules

Reduce avoidable friction aggressively:

- no dead-end commands in the tutorial
- no vague "figure it out" instructions
- no hidden required verbs
- no mandatory backtracking unless it is teaching orientation on purpose
- no punishments that send the player into a confusing recovery loop

### Readability Rules

- Each step should fit in the player's head immediately.
- The quest journal, mentor dialogue, room copy, and scene card should all reinforce the same current task.
- If those layers disagree, the tutorial will feel sloppy.

## Tutorial Quality Checklist

Before calling the tutorial shippable, all of these should be true:

- a brand-new player can finish it without outside help
- a child can follow the instructions without needing MUD experience
- a parent can guide from inside the game rather than by explaining the interface separately
- the tutorial does not overstay its welcome
- the transition into Training Yard feels natural
- the player leaves with enough confidence to enter the real game loop

## Tutorial Start Place

### Recommended Name

`Wayfarer's Yard`

This should be a small fenced annex attached to the north side of the existing Training Yard. It keeps the tutorial in-world, keeps Brambleford as the emotional home base, and avoids inventing a disconnected "gamey" tutorial island.

### Why This Is The Right Fit

- It matches Brambleford's frontier tone.
- It lets Captain Harl remain the handoff into the real game.
- It teaches the player just outside the main town rather than in a fake abstract tutorial room.
- It keeps the town map readable because the tutorial is a compact branch, not a second hub.

## Tutorial Map

Recommended room layout:

```text
                  [Family Post]
                       |
[Sparring Ring]-[Wayfarer's Yard]-[Quartermaster Shed]
      |
 [Vermin Pens]
                       |
                   [Gate Walk]
                       |
                  [Training Yard]
```

### Room Roles

#### Wayfarer's Yard

- New character spawn room.
- First explanation of how to read the room view.
- First movement lesson.
- First exposure to minimap, exits, and `look`.
- NPC: `Sergeant Tamsin Vale`

#### Quartermaster Shed

- Teaches `gear` and `pack`.
- Gives a starter consumable or utility item if needed.
- Introduces the idea that classes start with different gear, but avoids deep build talk.
- NPC: `Quartermaster Nella Cobb`

#### Family Post

- Optional side lesson for `party`, `party invite`, `party accept`, `party follow`, and `party where`.
- Contains a readable sign for solo players so they can understand the feature without needing another person present.
- Should never block tutorial completion if the player is alone.
- NPC: `Courier Peep Marrow`

#### Sparring Ring

- First guided combat explanation.
- Teaches `fight`, `enemies`, `attack`, and one class skill via `use`.
- Uses a safe controlled encounter first.
- NPC: `Ringhand Brask`

#### Vermin Pens

- First real low-risk fight.
- Small live enemies, not training dummies.
- Teaches that danger exists outside the yard, but in a forgiving way.
- No harsh death penalty here.

#### Gate Walk

- Handoff room before the player enters the live town flow.
- Teaches `quests`, `rest`, and the difference between safe rooms and dangerous rooms.
- Gives one clear next step: go south to the Training Yard and speak to Captain Harl.
- NPC presence: Sergeant Tamsin can appear here for the final send-off, but this does not need a separate permanent NPC if the room copy and quest beat handle it cleanly.

#### Training Yard

- Not part of the tutorial itself.
- This is the handoff room into the real game.
- Captain Harl becomes the first "real world" mentor after the guided sequence ends.

## NPC-Led Tutorial Philosophy

This is mandatory.

The tutorial should be taught primarily by people in the world, not by detached UI popups and not by a sterile command reference.

If the player learns a command, it should usually happen because a character asked them to do something and gave them a believable reason to do it.

### Core Rule

Every tutorial step should have:

- a named speaker
- a clear in-world instruction
- one immediate action for the player
- a short acknowledgement when the player succeeds

### Delivery Priorities

Use this order:

1. NPC speech
2. short quest text
3. room description or readable object
4. scene-card suggestion
5. fallback reminder if the player stalls

That keeps the game feeling like a MUD instead of a software tutorial.

### What To Avoid

- giant info dumps
- abstract system popups as the primary teacher
- showing five commands at once
- making the player guess which exact verb matters when an NPC is supposedly instructing them

If Sergeant Tamsin wants the player to move east, she should effectively say so.

## Tutorial Cast And Teaching Roles

The tutorial should have a small cast with clear jobs.

### Sergeant Tamsin Vale

Role:

- primary onboarding mentor
- first voice the player trusts
- teaches movement, room reading, `look`, and `quests`

Behavior:

- practical, calm, slightly dry
- speaks in short frontier-military instructions
- should react when the player returns from each early task

### Quartermaster Nella Cobb

Role:

- teaches `gear`, `pack`, class loadout awareness, and `read`

Behavior:

- brisk, competent, mildly amused
- explains equipment through practical frontier talk, not abstract stats lecture

### Courier Peep Marrow

Role:

- teaches party basics and family play expectations
- explains that `Brave` is meant to be more fun together, without punishing solo players

Behavior:

- friendly, fast-talking, encouraging
- should explicitly mention how to regroup if players get separated

### Ringhand Brask

Role:

- teaches `fight`, `enemies`, `attack`, and one class ability
- reinforces that combat text is readable and turn pressure is manageable

Behavior:

- blunt, good-natured, confident
- explains one combat idea at a time

### Captain Harl Rowan

Role:

- receives the player at the end of the tutorial
- confirms that training is over and real town life begins now
- points the player toward Town Green, the board, and the first live tasks

Behavior:

- authoritative but warm
- should feel like the bridge between guided play and the real game

## Dialogue Style Rules

Tutorial dialogue should sound like people, not tooltips.

### Required Style

- one instruction at a time
- short sentences
- specific verbs
- practical tone
- immediate acknowledgement after success

### Command Reveal Rule

When the game needs the player to learn a verb, the NPC should say the verb plainly inside the fiction.

Examples:

- "Head east to the shed and then come right back."
- "Check your gear, then open your pack."
- "Start the fight when you're ready. Then hit the vermin before it hits you again."

Do not hide the command behind coy prose if the player is expected to type it.

### Confirmation Rule

When the player completes a tutorial beat, the mentor should notice.

Examples:

- "There you are. Good. You can find your way back."
- "That kit will do. No sense dying with a full pack and no idea what's in it."
- "Better. You kept your feet and finished the job."

The player should feel seen, not like they triggered an invisible state machine.

## Sample Tutorial Beats

These are not final lines, but they establish the right shape.

### Wayfarer's Yard Opening

Sergeant Tamsin:

> "Easy now. You're in Brambleford, not the ditch outside it. First thing: get your bearings. Head east, have a look around, then come back and report."

What this teaches:

- the world has a voice
- movement is explicit
- the player has a simple first task

### Quartermaster Shed

Quartermaster Nella:

> "Before you go wandering, know what you're carrying. Check your gear. Then open your pack and make sure nothing in there surprises you."

What this teaches:

- the game will tell the player the verbs they need
- inventory is a practical concern, not a menu puzzle

### Family Post

Courier Peep:

> "If you're traveling with kin, don't drift apart and hope for the best. Form a party first. Makes finding each other a lot less foolish."

What this teaches:

- grouping matters
- the game expects co-op
- the lesson can still be optional

### Sparring Ring

Ringhand Brask:

> "Don't mash at shadows. Start the fight, check what's in front of you, then pick a target and commit."

What this teaches:

- `fight`
- `enemies`
- `attack`

### Gate Walk Send-Off

Sergeant Tamsin:

> "That's enough hand-holding. South takes you to Captain Harl and the rest of town. Check your quests if you lose the thread."

What this teaches:

- the tutorial is ending
- `quests` matters
- the player has a clear next destination

## Tutorial Quest Flow

The tutorial should be quest-driven, not menu-driven.

Recommended quest sequence:

### 1. First Steps In Brambleford

Teaches:

- `look`
- cardinal movement
- how to read exits
- how to notice the minimap

Objectives:

- talk to Sergeant Tamsin
- move to Quartermaster Shed
- return to Wayfarer's Yard

NPC behavior:

- Tamsin should greet the player, give the first move instruction, and explicitly acknowledge when they return.
- If the player stalls, Tamsin should repeat a shorter version rather than dump new text.

### 2. Pack Before You Walk

Teaches:

- `gear`
- `pack`
- `read`
- `talk`

Objectives:

- visit Quartermaster Shed
- inspect equipped gear
- inspect inventory
- read the supply board

NPC behavior:

- Nella should deliver the instruction in two beats, not all at once: first `gear`, then `pack`.
- If the player already completed one of the steps before talking to her, she should recognize that instead of acting blind.

### 3. Stand Your Ground

Teaches:

- `fight`
- `enemies`
- `attack`
- one class ability with `use`

Objectives:

- spar once
- enter Vermin Pens
- win one real encounter

NPC behavior:

- Brask should explain the next combat verb only when it becomes relevant.
- He should name the player's starter class skill directly so the player sees one concrete `use` example.
- After the first live win, he should explicitly tell the player they are ready to leave the ring behind.

### 4. Better Together

Optional lesson.

Teaches:

- `party`
- `party invite`
- `party accept`
- `party follow`

Objectives:

- read the Family Post sign
- if another player is nearby, optionally form a party

This should give completion credit through a solo-safe fallback so the player is never stuck.

NPC behavior:

- Peep should adapt to whether another player is present.
- If the player is alone, Peep explains the commands and signs off.
- If another player is nearby, Peep should actively suggest inviting them by name.

### 5. Through The Gate

Teaches:

- `quests`
- `rest`
- how the town will guide progression

Objectives:

- talk to Sergeant Tamsin one last time
- move south to Training Yard
- speak with Captain Harl

Completion result:

- mark tutorial complete
- unlock normal Brambleford progression

NPC behavior:

- Tamsin should make the handoff feel earned.
- Captain Harl should greet the player as someone who has already finished the basics, not as if they are brand new and helpless again.

## What The Tutorial Must Teach

A player leaving the tutorial should understand all of the following:

- how to move with `n`, `e`, `s`, `w`, `u`, `d`
- that `look` redraws the current scene
- that the minimap gives local orientation
- how to talk to NPCs and read objects
- how to check quests
- how to inspect gear and inventory
- how to start a fight and use a basic skill
- that grouping is supported, even if they did not use it yet

If a player reaches Training Yard without understanding those basics, the tutorial failed.

## Beginner Section Definition

The tutorial is only the first layer.

After the tutorial, `Brave` should guide the player through a broader beginner section covering levels 1 to 3 and the first 60 to 90 minutes of play.

### Beginner Section Scope

The beginner section should be:

- Wayfarer's Yard tutorial branch
- Training Yard
- Town Green
- Lantern Rest Inn
- Rat and Kettle Cellar
- East Gate
- Goblin Road Trailhead
- the first one or two Goblin Road rooms

### Why This Should Be Treated As One Cohesive Section

This is the true "learn the game" band.

Players are not just learning controls here. They are learning the rhythm of `Brave`:

- safe town to dangerous field
- short quest text to action
- readables and NPC hints instead of giant exposition
- class identity through simple encounters
- party play in small readable spaces

## Beginner Section Teaching Order

Recommended order:

1. Tutorial branch: controls, scene reading, first fight
2. Training Yard: class identity and combat reminder
3. Town Green: board, orientation, social meeting point
4. Inn: recovery, flavor, first safe hub behavior
5. Cellar: first contained group dungeon
6. East Gate: wilderness launch point
7. Goblin Road: first outdoor pressure and first real adventure path

Do not front-load the Observatory, Nexus, Forge complexity, or deeper side systems into the player's first minutes. Those should feel like discoveries after basic literacy is established.

## Beginner Quest Ladder

The first real chapter after the tutorial should unlock in a narrow, readable sequence.

Recommended order:

1. `Practice Makes Heroes`
2. `Rats in the Kettle`
3. `Roadside Howls`
4. `Fencebreakers`
5. `Ruk the Fence-Cutter`

### Ladder Rules

- New players should not receive all beginner quests at once.
- The next quest should unlock only after the current teaching beat is resolved.
- NPC dialogue, the board, and the scene card should all point at the same next quest.
- The portal branch should stay out of the way until the player has finished the early road arc.

This keeps the early game feeling paced, intentional, and teachable.

## Co-Op Requirements

The tutorial must work cleanly for family play.

### Required Behavior

- New players can see each other in the tutorial rooms.
- Party commands work in the tutorial.
- Tutorial combat scales gently for 1 to 4 players.
- Quest completion is individual, but grouped players can progress side by side.
- If one player is ahead by a room or two, the layout should make regrouping easy.

### Recommended Co-Op Touches

- Family Post should explicitly acknowledge that the game is meant to be played together.
- If two tutorial players are nearby, Sergeant Tamsin should mention grouping.
- The first live encounter should be readable and forgiving in duo play.

## Skip And Replay Rules

The tutorial should be respectful of repeat players.

### Recommended Rules

- First character on an account: tutorial strongly recommended.
- Additional characters on the same account: offer a clear skip option.
- Returning players should be able to choose:
  - start in Wayfarer's Yard
  - skip directly to Training Yard
- The game should support a replay path later through Captain Harl or a `tutorial` command.

### Skip Philosophy

Skipping should bypass the tutorial, not punish the player.

Do not hide core systems behind tutorial-exclusive rewards. The reward for doing the tutorial is clarity, not power.

## Failure And Recovery Rules

The tutorial must be generous.

- No item loss.
- No harsh defeat penalty.
- If the player loses in Vermin Pens, return them to Wayfarer's Yard or Gate Walk with a short explanation.
- Restoring HP/resources in the tutorial should be quick and obvious.
- The tutorial should never create permanent failure states.

## Text Delivery Rules

This matters as much as the room plan.

### Use Short Guidance

- one clear instruction at a time
- no giant walls of text
- no more than two or three commands in a single hint

### Teach By Context

- room text should imply what kind of interaction matters there
- NPC dialogue should point to the next action
- quest text should reinforce the lesson without becoming a manual

### Keep The Tone In-World

Even when teaching commands, the voice should stay like `Brave`, not like a software wizard.

Bad:

- "Press this key to continue."

Good:

- "Tamsin taps the signpost. Try heading east and then back again."

## Reactive Tutorial Rules

The tutorial should respond to player behavior.

### If The Player Wanders

- the mentor should gently restate the current task
- the quest text should stay specific
- the game should avoid sounding annoyed

### If The Player Already Knows The Game

- the dialogue should stay brief
- success acknowledgements should fire quickly
- skip options should remain obvious

### If The Player Uses The Wrong Command

- the relevant mentor should nudge them toward the right verb in plain language
- do not punish experimentation
- do not dump the whole help system into the log

### If The Player Is In A Group

- tutorial speech should still make sense when heard by multiple nearby players
- the party lesson should feel like a natural extension, not a separate rules lecture
- combat instruction should assume that more than one person may act

## UI Recommendations For The Tutorial

The tutorial should take advantage of the current client, but it should not require custom heavy UI.

Recommended support:

- the right-rail scene card should highlight suggested actions in tutorial rooms
- minimap should be especially stable and readable in the tutorial branch
- room descriptions in the tutorial should be slightly more explicit than later content
- tutorial rooms should avoid cluttered visible-objects lists

## Implementation Notes

When this is built, it should be done with existing game structures where possible:

- normal rooms
- normal quests
- normal NPC interactions
- normal command verbs
- lightweight account or character flags for tutorial state

Recommended flags:

- `tutorial_started`
- `tutorial_completed`
- `tutorial_skipped`
- `tutorial_current_step`

Recommended spawn behavior:

- new character with no tutorial completion flag starts in Wayfarer's Yard
- skipped or completed characters start in Training Yard

Recommended implementation detail:

- each tutorial quest beat should have a matching mentor dialogue state
- NPC responses should branch based on the player's current tutorial step
- the scene card can reinforce the current instruction, but it should never replace the speaking mentor
- reminder dialogue should trigger on room entry, quest advancement, or explicit `talk`, not as constant spam

## Suggested Build Order

### Phase 1

- create tutorial room branch
- add mentor NPCs and readables
- build the five-step tutorial quest flow
- route new characters there

### Phase 2

- add co-op tuning
- add skip and replay behavior
- tighten room copy and scene-card suggestions

### Phase 3

- audit the wider beginner section so the Inn, Cellar, East Gate, and Goblin Road all reinforce the same onboarding philosophy

## Success Criteria

This design is successful when:

- a brand-new player can start a character and reach Brambleford without outside help
- the player understands movement, talk, read, quests, gear, pack, and basic combat
- a parent can bring in a child and progress side by side without confusion
- repeat players can skip the tutorial cleanly
- the tutorial feels like part of the world instead of a detached training sim

## Relationship To Existing Docs

This document should guide future updates to:

- [brambleford_town_plan.md](brambleford_town_plan.md)
- [world_and_content.md](world_and_content.md)
- [implementation_plan.md](implementation_plan.md)

When implemented, the Training Yard should stop being described as the literal first stop after the title flow. It should become the handoff point from the tutorial branch into the main town progression.
