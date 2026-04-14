# First Hour Chapter Plan

## Purpose

This document defines the intended first-hour play experience for `Brave`.

The game now has enough rooms, quests, and systems that the opening chapter needs to be treated as one authored experience instead of a loose collection of early content. This document is the source of truth for how the tutorial, Brambleford, and the first road content should hand off into each other.

## Design Goals

The first hour should:

- feel like one coherent chapter
- teach the real game loop without overexplaining it
- work for solo players and local family co-op
- reward progress often enough that the opening does not feel dry
- move the player from town confidence into the first real boss payoff
- leave the player clearly ready for the next branch after `Ruk the Fence-Cutter`

## First Hour Ladder

The intended first-hour chapter is:

1. `Wayfarer's Yard`
2. `Practice Makes Heroes`
3. `Rats in the Kettle`
4. `Roadside Howls`
5. `Fencebreakers`
6. `Ruk the Fence-Cutter`

This is the core spine. Fishing, cooking, the Outfitters shift, and the Family Post are good optional flavor during this window, but they should not interrupt the main ladder.

## Target Flow

### 0 to 12 Minutes: Tutorial Branch

Goals:

- cardinal movement
- reading the room view
- `gear`
- `pack`
- `read`
- one controlled fight
- optional party basics

Exit condition:

- the player reports to Captain Harl and is sent into Brambleford proper

### 12 to 22 Minutes: First Real Town Job

Quest:

- `Practice Makes Heroes`
- `Rats in the Kettle`

Goals:

- move from Training Yard to Town Green to the inn
- understand that town jobs are real content, not filler
- fight one easy live encounter in a safe, recoverable environment
- get the first satisfying quest completion payout

Required feeling:

- "I understand how Brave works."

### 22 to 40 Minutes: First Road Push

Quest:

- `Roadside Howls`
- `Fencebreakers`

Goals:

- meet Mira at the East Gate
- read Goblin Road as the first real adventure space
- understand that the player can push room by room rather than rushing
- fight several light outdoor encounters

Required feeling:

- "Town is behind me and the game has opened up."

### 40 to 60 Minutes: First Boss Payoff

Quest:

- `Ruk the Fence-Cutter`

Goals:

- reach Fencebreaker Camp
- understand that party play makes hard encounters smoother
- defeat the first named boss
- receive a clear branch handoff afterward

Required feeling:

- "We finished a real chapter."

## Co-op Expectations

The first hour must work well for:

- one player learning alone
- a parent and child playing together
- a small party of family members joining partway through

That means:

- early solo encounters must be forgiving
- group play must not slow down quest progress
- boss fights should feel better with a party, not mandatory for a party
- the tutorial should not require another player to complete

## Reward Cadence

The first hour should reward the player frequently enough to keep momentum:

- tutorial completion should feel like a clean graduation
- town cellar completion should provide the first "real adventurer" payout
- early road quests should provide visible silver and practical rewards
- the player should have enough silver and loot by `Ruk` to care about `shop`, `pack`, and early `forge` planning

## Handoff Rules

Each quest should hand the player directly to the next mentor or place.

The intended handoffs are:

- `Practice Makes Heroes` -> Uncle Pib at the inn
- `Rats in the Kettle` -> Mira at the East Gate
- `Roadside Howls` -> continue working Goblin Road
- `Fencebreakers` -> push to Fencebreaker Camp
- `Ruk the Fence-Cutter` -> choose between woods, town loops, or the later fantasy branches

If a quest completes and the player still has to guess what to do next, the chapter is under-authored.

## Polish Targets

The first-hour implementation should provide:

- stronger completion messaging
- stronger unlock messaging
- a useful tracked quest by default unless the player explicitly clears it
- better reward text in the journal
- no dead-end period after the tutorial or after a major quest completion

## Current Development Focus

The immediate implementation pass should focus on:

- documenting this chapter as a canonical flow
- tuning the early quest rewards and messaging
- ensuring tracked quest behavior supports the opening ladder
- keeping co-op progression friction low through `Ruk`
