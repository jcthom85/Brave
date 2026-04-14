# Combat And Encounters

## Combat Goals

Combat should feel:

- Tactical
- Party-friendly
- Fast enough to stay fun
- Clear in text
- Strongly class-driven

## Recommended Combat Model

Recommended phase-1 default:

- Real-time combat resolved on a short fixed tick
- Basic attacks handled automatically
- Player power expressed through timed abilities, target choices, and party coordination
- Cooldowns and resource costs used to limit spam

This preserves early-MMO energy while staying manageable in a text-first interface.

## Core Combat Loop

1. Players engage an enemy group
2. Tanks or durable frontliners establish threat
3. DPS classes focus priority targets or set up control windows
4. Support classes manage survival, cleanse, and recovery
5. Encounter pressure escalates through adds, status effects, or elite mechanics
6. Players win through coordination, resource discipline, and target priority

## Action Types

Phase-1 action buckets:

- Basic attack
- Active damage ability
- Active defensive ability
- Heal or support ability
- Control ability
- Passive effect

Keep the number of action types small so combat output stays legible.

## Threat Model

Threat is important because the game is party-oriented.

Recommended default behavior:

- Warriors generate the highest baseline threat
- Paladins generate moderate threat through melee plus holy utility
- Healing generates some threat, but less than intentional tank tools
- Burst damage can briefly pull aggro if tanks are not actively managing it
- Threat resets and forced swaps should be rare outside bosses

## Status Effects

Use a short status catalog with clear meanings:

- `Bleed`: physical damage over time
- `Burn`: magic damage over time
- `Poison`: damage over time plus healing pressure
- `Slow`: reduces action speed or movement freedom
- `Root`: prevents repositioning
- `Stagger`: interrupts or delays the next action
- `Curse`: hostile magical debuff, often tied to undead or bosses
- `Holy Mark`: increases holy damage taken or unlocks follow-up effects
- `Weakness`: lowers offense or defense for a short window

Status stacking should be conservative in phase 1. Prefer duration refreshes over large stack counts.

## Enemy Roles

- `Skirmisher`: fragile, mobile, pressures backline targets
- `Brute`: durable melee threat with slow, heavy attacks
- `Caster`: ranged pressure, debuffs, or battlefield control
- `Support`: buffs allies, heals, or summons
- `Elite`: stronger single-unit encounter with one defining mechanic
- `Boss`: multi-phase or multi-pattern encounter with clear reads

## Encounter Design Rules

Use these rules to keep encounters readable:

- Most normal fights should feature 2 to 4 enemies
- Each pack should have one obvious priority target when possible
- Do not combine too many crowd-control sources in the same pull
- Early zones should introduce one mechanic at a time
- Elite and boss fights should reinforce class roles rather than invalidate them

## Boss Design Rules

Each boss should have:

- A strong visual or thematic hook in text
- Two to three core mechanics
- A readable escalation point
- One moment that rewards preparation or party coordination

Avoid phase-1 bosses that require puzzle logic, hidden counters, or perfect execution.

## Class Combat Identity Summary

- Warrior: controls enemy attention and smooths incoming damage
- Ranger: safely pressures priority targets and adds soft control
- Mage: creates burst windows and area pressure
- Cleric: keeps the party alive and removes dangerous effects
- Rogue: punishes openings and high-value targets
- Paladin: protects allies while contributing frontline damage
- Druid: supplies flexible healing and battlefield control

## Encounter Difficulty Curve

Recommended zone pressure:

- Levels 1 to 2: introduce baseline combat, targeting, and healing
- Levels 3 to 4: introduce crowd control and enemy synergy
- Levels 5 to 7: add elites, split-role packs, and light boss phases
- Levels 8 to 10: test resource management, cleanse timing, and party coordination

## Text Readability Rules

Combat text should prioritize:

- Who acted
- What they used
- Who it affected
- The most important result

Good examples of key combat output:

- `Warrior uses Shield Bash on Goblin Brute. 18 damage. Goblin Brute is staggered.`
- `Cleric casts Renewing Light on Ranger. Ranger will recover 8 HP for 3 ticks.`
- `Sir Edric raises his shield. Damage taken reduced until the adds are cleared.`

Avoid noisy low-value spam in the main log if it obscures status changes or boss tells.
