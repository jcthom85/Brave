# Tutorial And Onboarding

This document describes the current onboarding flow and the long-term design contract for Brave's newbie area.

Runtime state lives in `brave_game/world/tutorial.py`. Authored rooms and entities live in `brave_game/world/content/packs/core/world.json`. Tutorial dialogue and readables are split between `world/tutorial.py` and `world/content/packs/core/dialogue.json`.

## Core Principle

The newbie area must teach by giving the player useful things to do in context.

Do not turn the opening into a large instruction dump. The intro popup is for mood, premise, and the first clear action. It should not preview the whole tutorial, list every system, or explain mechanics that the player has not needed yet.

The preferred pattern is:

1. Put the player in a situation.
2. Give one immediate goal.
3. Let the player act.
4. Show the relevant UI or command at the moment it matters.
5. Confirm the result through world response, objective progress, or visible character feedback.

Every tutorial beat should answer, "Why would a real person in Brambleford ask me to do this right now?"

## Intro Popup Contract

The first popup should stay short. Its job is to establish:

- Brambleford is warm but under pressure.
- A south road lantern has gone dark.
- A damaged cart has reached the gate.
- Sergeant Tamsin is the first person to talk to.

The popup should not teach:

- inventory
- gear
- combat
- class abilities
- status effects
- rewards
- rest
- journal, map, or sheet details
- party systems
- the full Captain Harl handoff

Those belong inside the newbie area, at the moment the player encounters them.

Recommended default shape: three short pages at most.

1. A welcoming first image.
2. The Lanternfall incident.
3. The immediate next action: talk to Tamsin.

Additional slides are allowed only if they serve emotional pacing, not system teaching.

## Teaching Checklist

The newbie area must cover the following systems before the player graduates into Brambleford proper.

### Core Navigation

- Movement by exits and directions.
- Reading room names, descriptions, exits, and nearby entities.
- Understanding gated exits and why they are blocked.
- Returning to a previous room after being sent somewhere.

### Basic Interaction

- Talking to NPCs.
- Reading signs, boards, or posted text.
- Inspecting or using room objects where relevant.
- Recognizing clickable UI actions and typed command equivalents.
- Understanding that NPCs can advance objectives, not just provide flavor.

### Quest And Objective Awareness

- The tutorial quest is tracked by default.
- The tracked quest card shows the current purpose.
- The journal contains active objectives.
- Completed objectives update as actions happen.
- Optional objectives are visible but not blockers.
- The player cannot leave the newbie area until required objectives are done.

### Inventory And Gear

- Opening the pack/inventory.
- Understanding item quantity and basic item categories.
- Opening equipped gear.
- Equipping a specific item.
- Seeing that gear changes stats or power.
- Understanding that rewards go into inventory and may need to be equipped.

### Combat Entry

- How a fight starts.
- Tutorial combat is solo and controlled.
- Identifying allies and enemies in the combat UI.
- Selecting a target.
- Using basic attack.
- Using a class ability.
- Understanding action readiness or timing if ATB is visible.
- Understanding that combat commands and UI actions are equivalent.

### Combat Concepts

- HP bars for the player and enemy.
- Resource bars where relevant, such as stamina and mana.
- Status chips and status effects.
- Enemy readiness or enemy state if shown.
- Victory and defeat result flow.
- Loot and reward flow after victory.
- Recovery after combat.

### Class Identity

- Every class gets at least one useful combat action.
- The player uses that class action once in context.
- The lesson should make the class feel distinct, not merely say "use your ability."

### Power Feedback

- Equipping the reward visibly changes something.
- The game shows or states what improved.
- The player understands: "I am stronger because I equipped earned gear."

### Rest And Recovery

- Resting after combat.
- Understanding rest as a recovery tool.
- Knowing that rest is tied to authored rest sites.

### Passive UI Exposure

- Pack/inventory.
- Gear/equipment.
- Journal/quests.
- Map.
- Character sheet/stats.
- Nearby/activity panels if they are central to the current webclient layout.

### Social And Party Basics

- Party basics through the Family Post.
- Why the newbie combat remains solo.
- When multiplayer becomes available or relevant.
- How to recognize other players or NPCs in the area.

### World Framing

- Why the player is in Wayfarer's Yard.
- Who Tamsin, Nella, Brask, and Harl are in the first flow.
- Why Harl is the handoff into Brambleford proper.
- Why the player cannot go into town yet.
- What the first real town objective is after graduation.

## Teaching Delivery Rules

- Teach one new thing at a time.
- Keep the player acting every few lines.
- Use NPC intent instead of UI narration whenever possible.
- Use the tracked quest and journal as the source of truth for objectives.
- Use small contextual prompts or overlays only for the immediate next action.
- Keep tutorial combat solo so the combat UI can teach one player's state clearly.
- Do not add tutorial-only mechanics unless the real system is too dangerous or confusing for a first exposure.
- Do not duplicate the same objective in multiple competing UI surfaces.
- Optional lessons must be clearly optional and must not block graduation.
- If the player ignores an optional passive UI exposure, the tutorial may continue.

## Graduation Contract

A player should not enter Brambleford proper until they have:

- talked to Tamsin
- moved through the yard loop
- checked gear
- opened pack
- read the supply board
- spoken with Brask
- completed one solo combat lesson
- used a class ability in combat
- received and equipped the Wayfarer Clasp
- seen power feedback
- rested after the fight
- reached Captain Harl's handoff

The player may enter Brambleford without completing optional party basics, map viewing, sheet viewing, or journal viewing, but the tutorial should expose those surfaces before graduation.

## Current Flow

New characters start in Wayfarer's Yard. The tutorial branch gates access to Brambleford proper until the required yard lessons are complete and the player reaches Captain Harl's handoff.

The tutorial is a short in-world branch attached to Brambleford. It teaches the real commands the player will use in the first hour:

- room reading and movement
- `talk`
- `gear`
- `pack`
- `read`
- basic combat flow
- class ability usage
- HP and status-effect literacy in the combat UI
- loot and reward feedback
- equipping a small reward and seeing power improve
- `rest`
- passive exposure to `map`, `sheet`, and `quests`
- optional party basics

## Holistic Rebuild Direction

The newbie area should feel like a small emergency response route, not a tutorial island.

Keep the current room set unless a room stops serving that route:

- `Wayfarer's Yard`: hub, Tamsin, rest, gate pressure, visible emergency evidence.
- `Quartermaster Shed`: gear, pack, supply board, Nella.
- `Sparring Ring`: Brask and combat setup.
- `Vermin Pens`: solo controlled fight.
- `Gate Walk`: visible town threshold and graduation gate.
- `Family Post`: optional party basics.

Recommended required route:

`Wayfarer's Yard -> Quartermaster Shed -> Wayfarer's Yard -> Sparring Ring -> Vermin Pens -> Wayfarer's Yard -> Gate Walk -> Training Yard`

The early route should not bounce the player between the same rooms just to prove movement. Tamsin sends the player east to Nella once. Nella teaches kit checks in one visit, then the player returns west to the yard. That still teaches movement and return movement, but it keeps the fiction clean.

Content may be deleted, renamed, or rewritten if it does not serve pacing, clarity, or the Lanternfall hook. Prefer fewer stronger beats over more rooms, prompts, or repeated explanations.

## Environmental Story Requirements

The opening emergency should be visible in the world, not only described in popup text.

Use room descriptions, readables, and NPC text to reinforce:

- the bell is ringing before dawn
- a south road lantern went dark
- a damaged cart reached the gate
- harness was cut
- mud and fence splinters imply the road was hit deliberately
- adults in the yard are acting with urgency

The player should see physical evidence before Harl explains the larger problem.

## Pacing Requirements

- First minute: popup plus talk to Tamsin.
- First three minutes: move to Nella, check gear, open pack, read board.
- Middle: return to yard, go to Brask, start controlled fight.
- Combat: one readable fight that requires a class ability.
- Finish: equip reward, rest, pass Gate Walk, report to Harl.

Do not let optional party basics compete with the first path. Family Post can be visible, but the tracked objective should keep the player on the emergency route.

## Tutorial Steps

### Lanternfall

Room focus: `tutorial_wayfarers_yard` and `tutorial_quartermaster_shed`.

Player learns to talk to Sergeant Tamsin and move east to the Quartermaster Shed.

### Kit Before The Gate

Room focus: `tutorial_quartermaster_shed` and `tutorial_wayfarers_yard`.

Player talks to Quartermaster Nella, checks `gear`, opens `pack`, reads the supply board, and returns west to the yard before Brask.

### Stand Your Ground

Room focus: `tutorial_sparring_ring`.

Player talks to Ringhand Brask and receives explicit combat syntax for `fight`, `enemies`, `attack e1`, and class skill use.

### Clear The Pens

Room focus: `tutorial_vermin_pens`.

Player starts a controlled fight, uses a class ability, and wins one small encounter.

The tutorial pens are solo by design. Party members are not auto-added and a second player cannot join the same newbie fight. This lets the combat UI teach one player's HP, enemy HP, status chips, action pickers, and target labels without another player advancing the lesson out from under them.

### Fit Your Clasp

Room focus: `tutorial_vermin_pens`, `tutorial_sparring_ring`, and `tutorial_wayfarers_yard`.

The first tutorial victory grants a guaranteed `Wayfarer Clasp`. The player equips it with `gear equip trinket clasp`, gets immediate stat feedback, and is nudged toward `sheet`, `map`, and `quests` before reporting in.

### Catch Your Breath

Room focus: `tutorial_wayfarers_yard`.

Player returns to the yard and uses `rest`. This matters because the wider game now requires authored rest sites instead of letting the player recover anywhere.

### Through The Gate

Room focus: `brambleford_training_yard`.

Player reports to Captain Harl. Tutorial completion sets the account completion flag, moves the character's home to Brambleford Town Green, and hands the player into `Practice Makes Heroes` and the first town job.

## Optional Party Beat

`tutorial_family_post` teaches party commands without blocking solo completion.

It should remain optional. The tutorial must work for one player, two players joining at different times, and a family group moving through together.

## Current Strengths

- The flow is coherent and recoverable.
- It teaches the actual command surface instead of fake tutorial-only controls.
- The first fight is low-risk and readable.
- The journal and scene-card focus prompts already point at the next practical action.
- The handoff to Captain Harl and Uncle Pib gives the player a real next job.

## Current Weakness

The tutorial is useful, but it has two risks:

- It can open too quietly.
- It can overcorrect by explaining too much up front.

The fix is not to skip onboarding. The fix is to put onboarding inside an emergency.

The player should not feel like they spawned into a lesson. They should feel like they woke up as the town bell started ringing, and the lesson is what competent Brambleford people do when things go wrong.

The intro popup may create the first emotional beat, but it must not carry the whole teaching burden. If the popup explains kit, combat, rewards, rest, map, journal, sheet, party basics, and Harl before the player has acted, the tutorial has become a lecture. Move those lessons back into rooms, NPCs, objectives, combat overlays, rewards, and normal UI feedback.

## Recommended Story Reframe

Keep the same tutorial commands and rooms, but change the dramatic framing:

1. The first connection or first room text should establish that a south lantern has gone dark and something hit the road before dawn.
2. Tamsin's first line should sound like triage, not classroom instruction.
3. Nella's kit check should be framed as "take what keeps you alive," not "learn inventory."
4. Brask's vermin fight should be framed as yard trouble stirred by the same pulse that rattled the road.
5. Harl should not merely welcome the player. He should connect the cellar, the road, and the cut fences into one first chapter.

This preserves the current tutorial implementation while making the opening feel like story, not paperwork.

## Implementation Guardrails

- Do not lengthen the tutorial to create drama. Add urgency to the existing beats.
- Do not make the emergency a fake failure state. New players still need safety and time to learn.
- Do not reveal the whole phase-1 plot up front. The opening only needs one sharp question: "Who hit the road, and why did the lantern go out?"
- Keep every instruction diegetic. The NPC should ask for an action because the town needs it, not because the UI needs it.
- Keep the intro popup short. Use it to establish premise and the first action, not to teach the full system list.
- Prefer show-then-confirm over tell-then-explain. Let the player open gear before describing gear. Let them earn loot before explaining rewards.
- Keep the optional party beat optional. Co-op should improve the mood, not gate the lesson.

## Quality Bar

A first-time player leaving Wayfarer's Yard should be able to say:

- "I know how to move, talk, check my stuff, fight, use a class skill, equip a reward, and rest."
- "Brambleford is under pressure."
- "Captain Harl and Uncle Pib are sending me into the first real problem."
- "The road matters."

If they only learn the controls, the tutorial is functional. If they learn the controls while feeling the town take its first hit, the tutorial is doing story work.
