# Core Systems

## Player Count And Party Model

- Supported players: 1 to 4 local players
- Ideal party size: 3 or 4
- Design goal: no single class is mandatory, but each class should contribute something distinct

Recommended early reference parties:

- Warrior, Cleric, Ranger, Mage
- Warrior, Paladin, Ranger, Mage
- Warrior, Cleric, Rogue, Mage
- Paladin, Ranger, Druid, Rogue

## Character Creation

Recommended phase-1 flow:

1. Choose player name
2. Choose race
3. Choose class
4. Receive starter kit and two level-1 abilities
5. Spawn in Brambleford with the starter quest line available

Keep race bonuses meaningful but smaller than class identity.

## Races

### Human

- Theme: flexible, ambitious, practical
- Perk: `Resolve`
- Mechanical direction: small XP bonus or cooldown recovery bonus

### Elf

- Theme: graceful, perceptive, magical
- Perk: `Keen Senses`
- Mechanical direction: small accuracy bonus and resistance to ambush

### Dwarf

- Theme: hardy, disciplined, stubborn
- Perk: `Stoneblood`
- Mechanical direction: bonus max HP and minor stun or bleed resistance

### Halfling

- Theme: quick, lucky, underestimated
- Perk: `Fortune's Step`
- Mechanical direction: small dodge and crit bonus

### Half-Orc

- Theme: fierce, intimidating, strong
- Perk: `Battle Hunger`
- Mechanical direction: increased damage at low health

## Classes

### Warrior

- Role: tank, frontline control, threat generation, party protection
- Primary stats: Vitality, Strength
- Combat identity: durable anchor that stabilizes dangerous fights

Level progression:

- Level 1: Strike, Defend
- Level 2: Shield Bash
- Level 3: Passive: Iron Will
- Level 4: Battle Cry
- Level 5: Intercept
- Level 6: Passive: Thick Hide
- Level 7: Taunting Blow
- Level 8: Brace
- Level 9: Passive: Bulwark
- Level 10: Last Stand

### Ranger

- Role: ranged DPS, wilderness utility, single-target pressure, light AoE
- Primary stats: Agility
- Combat focus: Precision, target marking, ranged control
- Combat identity: safe damage, setup utility, and target control

Level progression:

- Level 1: Quick Shot, Mark Prey
- Level 2: Aimed Shot
- Level 3: Passive: Trailwise
- Level 4: Snare Trap
- Level 5: Volley
- Level 6: Passive: Predator's Eye
- Level 7: Evasive Roll
- Level 8: Barbed Arrow
- Level 9: Passive: Deadly Rhythm
- Level 10: Rain of Arrows

### Mage

- Role: magic DPS, crowd control, elemental status effects
- Primary stats: Intellect, Spirit
- Combat identity: high payoff, higher risk, strongest burst windows

Level progression:

- Level 1: Firebolt, Frost Bind
- Level 2: Arc Spark
- Level 3: Passive: Deep Focus
- Level 4: Flame Wave
- Level 5: Mana Shield
- Level 6: Passive: Spell Echo
- Level 7: Static Field
- Level 8: Ice Lance
- Level 9: Passive: Elemental Attunement
- Level 10: Meteor Sigil

### Cleric

- Role: healer, support, cleanse, undead counter
- Primary stats: Spirit, Vitality
- Combat identity: primary sustain and party stabilization

Level progression:

- Level 1: Heal, Smite
- Level 2: Blessing
- Level 3: Passive: Serene Soul
- Level 4: Renewing Light
- Level 5: Sanctuary
- Level 6: Passive: Purity
- Level 7: Cleanse
- Level 8: Radiant Burst
- Level 9: Passive: Graceful Hands
- Level 10: Guardian Light

### Rogue

- Role: burst DPS, scouting, debuffs, trick play
- Primary stats: Agility
- Combat focus: Precision, burst windows, repositioning
- Combat identity: opportunistic damage, repositioning, and threat drops

Level progression:

- Level 1: Stab, Feint
- Level 2: Backstab
- Level 3: Passive: Light Feet
- Level 4: Poison Blade
- Level 5: Vanish
- Level 6: Passive: Ruthless Timing
- Level 7: Cheap Shot
- Level 8: Shadowstep
- Level 9: Passive: Killer's Focus
- Level 10: Eviscerate

### Paladin

- Role: off-tank, support tank, holy bruiser, protection
- Primary stats: Vitality, Spirit, Strength
- Combat identity: durable hybrid that blends weapon pressure, defense, and light support

Level progression:

- Level 1: Holy Strike, Guarding Aura
- Level 2: Judgement
- Level 3: Passive: Steadfast Faith
- Level 4: Hand of Mercy
- Level 5: Consecrate
- Level 6: Passive: Blessed Armor
- Level 7: Shield of Dawn
- Level 8: Rebuke Evil
- Level 9: Passive: Beacon Soul
- Level 10: Avenging Light

### Druid

- Role: hybrid support, off-healer, control caster, nature damage
- Primary stats: Spirit, Intellect
- Combat identity: flexible support with roots, healing zones, and damage-over-time pressure

Level progression:

- Level 1: Thorn Lash, Minor Mend
- Level 2: Entangling Roots
- Level 3: Passive: Wild Grace
- Level 4: Moonfire
- Level 5: Barkskin
- Level 6: Passive: Living Current
- Level 7: Swarm
- Level 8: Rejuvenation Grove
- Level 9: Passive: Nature's Memory
- Level 10: Wrath of the Grove

## Class Implementation Order

Use this order unless a later technical decision forces a change:

1. Warrior
2. Cleric
3. Ranger
4. Mage
5. Rogue
6. Paladin
7. Druid

This delivers the clearest fantasy RPG core first.

## Multiverse Resonance (Genre Scaling)

To support portals (Star Wars, Dragonball, etc.), the core stats map to genre-specific "skins."

| Core Stat | Fantasy (Default) | Sci-Fi / Tech | Martial / Ki |
| --- | --- | --- | --- |
| **Strength** | Strength | Physical Might | Martial Power |
| **Agility** | Agility | Reflexes | Speed |
| **Intellect** | Intellect | Tech Skill | Focus |
| **Spirit** | Spirit | Force / Energy | Ki Level |
| **Vitality** | Vitality | Durability | Endurance |

## Minigame Hooks

The engine supports "Activity Modes" that swap the standard combat commands for minigame-specific ones.

- **Fishing Mode:** Swaps `attack` for `cast`, `reel`, and `jig`.
- **Shop Mode:** Swaps `attack` for `appraise`, `haggle`, and `sell`.
- **Cooking Mode:** Swaps `attack` for `stir`, `season`, and `plate`.

## Audio & Visual Triggers

Every room and action can send an "OOB" (Out-of-Band) message to the webclient to trigger:
- **Ambient Loops:** Background soundscapes.
- **Event SFX:** One-shot sounds for combat or interaction.
- **Visual Effects:** Text shaking, color flashes, or CSS-based "Glows" for high-impact moments.

## Stats

Primary stats:

- Strength
- Agility
- Intellect
- Spirit
- Vitality

Derived stats:

- Max HP
- Max Mana / Energy / Ki
- Max Stamina
- Attack Power
- Spell / Force / Ki Power
- Armor
- Accuracy
- Precision
- Crit Chance
- Dodge
- Threat
- Resistances

Phase-1 stat resolution:

- Keep five primary stats for implementation simplicity
- Treat `Precision` as a derived offensive stat driven mainly by Agility, gear, and class passives

## Resource Model

Stamina classes:

- Warrior
- Ranger
- Rogue
- Paladin

Mana classes:

- Mage
- Cleric
- Druid

Phase-1 default: keep Paladin stamina-based for simplicity, with holy effort abstracted into stamina costs.

## Gear Model

Gear slots:

- Main Hand
- Off Hand or Shield
- Head
- Chest
- Hands
- Legs
- Feet
- Ring
- Trinket

Item rarities:

- Common
- Uncommon
- Rare
- Named

Sample item names:

- Goblin-Cracked Buckler
- Lanternwood Bow
- Gravebell Ring
- Watchcaptain's Blade
- Dawn Bell Charm
- Mossrunner Boots
- Blackreed Longcoat
- Sainted Band
- Greymaw Pelt Mantle

## Progression Model

- Phase-1 level cap: 10
- Players begin with two class abilities
- Each level should grant a meaningful reward, either active, passive, or access-driven
- Early levels should arrive quickly
- Midgame should slow slightly
- Level 10 should align with completion of the phase-1 story arc

## System Boundaries

Keep phase-1 progression focused on:

- Levels
- Ability unlocks
- Equipment upgrades
- Quest completion
- Zone access

Avoid adding secondary progression systems until the core loop is proven.
