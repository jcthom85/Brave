# Chapel And Class Completion Pass

## Purpose

This document defines the next fantasy-core slice after the phase-1 capstone.

The game now has a real opening chapter, a real midgame ladder, and a clean fantasy capstone. What it still needs is a stronger town-side support loop and a full phase-1 class roster that actually lives in the game rather than only existing in data.

This pass exists to do two things:

- make the Chapel of the Dawn Bell matter as a usable town system
- make Paladin and Druid fully live classes in the current slice

## Goals

This pass should:

- keep the focus on Brambleford instead of opening another new branch
- finish the phase-1 class roster in practical play terms
- give the Chapel a real pre-run support role
- strengthen Sister Maybelle and Brother Alden as active town voices
- support solo play and family co-op equally well

## Scope

### 1. Paladin And Druid Go Fully Live

Paladin and Druid should no longer be "present in definitions, absent in feel."

That means:

- both are available through `build` and `class`
- both have full starter gear
- both have functional level-1 abilities in combat
- both have forge upgrade paths comparable to the current live classes
- both appear naturally in sheet, gear, pack, and combat UI

### 2. Chapel Loop

The Chapel of the Dawn Bell should become a meaningful support stop before harder runs.

The core loop is:

- return to town
- visit the chapel
- `pray`
- receive a modest Dawn Bell blessing for the next encounter
- head back out

The blessing should:

- feel useful without replacing food buffs or gear
- support every class
- expire after the next encounter result, win or lose
- read especially well as a pre-Barrow / pre-weir ritual even if it remains globally useful

### 3. Chapel Voice And Guidance

Brother Alden and Sister Maybelle should do more than hand off one quest and then go quiet.

They should:

- point players toward the west-side danger at the right times
- explain the Dawn Bell blessing in-world
- make the Chapel feel like part of Brambleford's defense posture
- help reinforce Paladin and Druid as naturally Brambleford-flavored classes

## Design Direction

### Paladin

Paladin should read as:

- support tank
- holy road-warden
- sturdy, protective, dependable

The class should not just be "cleric in armor."

Its first slice should emphasize:

- durable frontline presence
- protection of allies
- stronger performance into undead or cursed threats

### Druid

Druid should read as:

- hybrid support
- nature-guided control
- gentler but persistent battlefield influence

The class should not just be "mage in leaves."

Its first slice should emphasize:

- small healing
- condition relief
- root / thorn / natural pressure

## Chapel Blessing Rules

The Dawn Bell blessing should be:

- easy to use
- modest
- temporary
- readable

It should not:

- become a permanent always-on town buff
- require a resource grind
- replace `rest`, meals, or forge upgrades
- turn the Chapel into a spreadsheet service counter

## Implementation Notes

During implementation:

- add this doc before or alongside the code work
- keep the Chapel loop to one command and one blessing state
- prefer using the existing stat and buff systems over inventing a new subsystem
- update help text and live documentation when the classes become truly playable

## Done Means

This pass is done when all of the following are true:

- `build` and `class` treat Paladin and Druid as normal live options
- both classes can start, fight, level, and use their first abilities
- both classes have starter gear and forge upgrades
- `pray` works in the Chapel of the Dawn Bell
- the blessing shows up clearly in the UI and clears after the next encounter result
- Alden and Maybelle both reinforce the new loop in dialogue
- the docs describe the Chapel as a live support room, not only a lore room
