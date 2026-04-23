# Balance Readiness Report

Date: April 22, 2026

This is a prep pass for later tuning. It describes the current balance model and the gaps that make tuning expensive today.

## Current damage formula

Player and companion attacks resolve in `typeclasses/scripts.py`.

- Hit chance: `max(35, min(95, 55 + accuracy - dodge))`
- Weapon damage: `max(1, attack_power // 2 + random.randint(2, 6) + bonus - armor // 4)`
- Spell damage: `max(1, spell_power // 2 + random.randint(3, 7) + bonus - armor // 5)`
- Healing: `base + spell_power // divisor + healing_power + random.randint(0, variance)`

There are many additive per-ability bonuses layered on top in `world/combat_execution.py`, plus mark, bleed, poison, guard, reaction, and class-specific condition bonuses.

## Current player stat baseline

Player derived stats are built in `typeclasses/characters.py`.

- `max_hp = 55 + vitality * 10 + level * 8`
- `max_mana = 12 + (intellect + spirit) * 5 + level * 4`
- `max_stamina = 24 + (strength + agility + vitality) * 3 + level * 5`
- `attack_power = strength * 2 + agility + level * 2`
- `spell_power = intellect * 2 + spirit + level * 2`
- `armor = vitality * 2 + strength + level`
- `accuracy = 65 + agility * 2 + level`
- `dodge = 3 + agility + level // 2`

Equipment, meals, chapel effects, race perks, passive class bonuses, and temporary combat states modify these further.

## Current enemy HP and damage ranges

Enemy templates live in `world/data/encounters.py` and are mirrored into `world/content/packs/core/encounters.json`.

Template ranges right now:

- Normal enemies: `18-114 HP`, `5-24 attack_power`, `5-27 spell_power`
- Elite enemies: only one current authored elite template (`goblin_cutter`): `34 HP`, `10 attack_power`
- Boss enemies: `84-292 HP`, `14-29 attack_power`, `14-31 spell_power`

This means the elite tier is currently under-authored compared with normal and boss coverage.

## Current elite and boss mechanics

Enemy rank metadata comes from tags and XP in `world/data/encounters.py`.

- Bosses are identified directly by the `boss` tag.
- Elite status for UI/rank purposes comes from tags like `elite`, `captain`, or `commander`, or a high derived rank.

Mechanical distinction is uneven:

- Bosses have bespoke script logic in `_handle_enemy_specials` in `typeclasses/scripts.py`.
- Named bosses commonly gain one or more of:
  - add spawns at HP thresholds
  - enrage stat bumps
  - reposition / stealth windows
  - temporary shielding
  - telegraphed named ATB actions with longer windups
- The current elite example, `goblin_cutter`, is mostly just a stronger template. There is no general elite behavior layer comparable to bosses.

That means elite is currently more of a template/stat label than a real mechanical tier.

## Current companion contribution

Ranger companions are not passive riders. They enter combat as separate ATB actors.

Companion spawn math in `typeclasses/scripts.py`:

- HP scales from owner `max_hp` by companion `hp_ratio`
- Attack scales from owner `attack_power` by `attack_ratio`
- Armor scales from owner `armor` by `armor_ratio`
- Accuracy and dodge get additive companion bonuses
- Fill rate starts at `92 + fill_rate_bonus`

Current authored companion baselines in `world/ranger_companions.py`:

- Marsh Hound: `0.55 hp_ratio`, `0.62 attack_ratio`, `0.7 armor_ratio`, `+8 fill_rate`
- Ash Hawk: `0.42 hp_ratio`, `0.48 attack_ratio`, `0.45 armor_ratio`, `+16 fill_rate`
- Briar Boar: `0.72 hp_ratio`, `0.58 attack_ratio`, `1.0 armor_ratio`, `+4 fill_rate`

Bond levels add further ratio and stat bonuses, and companion turns add real action-economy pressure because they resolve on their own ATB track.

## Current party scaling

Encounter scaling is applied when enemies spawn in `typeclasses/scripts.py`.

- Solo: `hp 0.88`, `power 0.88`, `accuracy -3`, `xp 1.0`
- Duo: `hp 0.94`, `power 0.95`, `accuracy -1`, `xp 1.0`
- Trio: `hp 1.08`, `power 1.02`, `accuracy +1`, `xp 1.03`
- Four-player: `hp 1.22`, `power 1.10`, `accuracy +3`, `xp 1.08`

This is a flat enemy-side multiplier. It does not change behavior mix, target count, spawn count, or turn logic by party size. Rewards also scale off weighted contribution, not a simple equal split.

## Current obvious balance risks

- Elite tier is thin. There is effectively one elite template and no generic elite behavior layer.
- Party scaling is shallow. It only adjusts HP, power, accuracy, and XP, so large differences in action economy may still dominate.
- Ranger companions materially improve action economy, but the current tuning tools do not quantify how much.
- Bosses are script-authored one by one, so their balance is likely to drift encounter by encounter.
- Damage has a lot of additive bonuses across class logic, condition logic, race logic, mastery, and companion hooks. That makes intuition unreliable.
- Reward splits depend on weighted contribution and meaningful actions, which is good for participation fairness but harder to reason about without logs.

## What telemetry or simulation should come next

The next useful step is a deterministic combat simulation harness, not manual number tweaks.

It should record at least:

- encounter id
- party size
- class mix
- companion present or absent
- turns or ticks to victory
- remaining HP by participant
- outgoing damage by source
- healing by source
- mitigation by source
- wipes / near-wipes
- boss interrupt and telegraph outcomes

Recommended immediate follow-up:

1. Add a deterministic simulation runner for authored encounters.
2. Batch-run solo, duo, trio, and four-player cases.
3. Split reports by normal, elite, and boss encounters.
4. Add a specific companion-on versus companion-off comparison for ranger parties.
