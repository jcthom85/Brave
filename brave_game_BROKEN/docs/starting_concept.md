# Brave

Markdown conversion of the original `Phase-1 Design Document` in [starting_concept.txt](/mnt/c/Brave/docs/starting_concept.txt).

## 1. High Concept

`Brave` is a small-scale, early-MMO-inspired fantasy MUD built for 1 to 4 local players. It centers on a warm, quirky frontier town called Brambleford, surrounded by increasingly dangerous wilderness, ruins, barrows, bandit strongholds, and goblin tunnels.

The tone blends:

- Heroic fantasy adventure
- Light humor and charm in town
- Grim but not horror-heavy danger in outer zones
- Co-op party combat
- Clear progression through classes, gear, abilities, quests, and bosses

The intended feel is:

- Cozy and inviting in safe areas
- Exciting and dangerous outside town
- Readable and satisfying combat
- Strong class identity
- Enough systems to feel like a real game, but not so many that development bogs down

## 2. Design Pillars

### 2.1 Early MMO Feel

The game should feel like a small, handcrafted precursor to an MMO:

- Distinct races and classes
- Town hub
- Combat zones
- Dungeon-like areas
- Quests
- Bosses
- Loot
- Party synergy
- Recognizable enemy camps and dangerous places

### 2.2 Cozy Hub, Dangerous World

Brambleford should feel:

- Warm
- Funny
- Lived-in
- Worth protecting

The outer world should feel:

- Increasingly threatening
- Mysterious
- Heroic to overcome

### 2.3 Strong Class Identity

Classes should feel immediately different:

- Warrior feels sturdy and commanding
- Cleric feels protective and restorative
- Mage feels explosive and risky
- Ranger feels mobile and tactical
- Rogue feels opportunistic and clever
- Paladin feels heroic and durable
- Druid feels versatile and nature-bound

### 2.4 Readable Combat

Combat should be:

- Clear in text
- Tactical without being exhausting
- Based on cooldowns, roles, and status effects
- Strong in 1 to 4 player parties

### 2.5 Small But Real

This should not feel like a tech demo. It should feel like a small real game.

## 3. Player Count And Party Model

- Supported party size: 1 to 4 players
- Ideal party size: 3 or 4 players

Target party roles should reward compositions like:

- Warrior + Cleric + Ranger + Mage
- Warrior + Paladin + Ranger + Mage
- Warrior + Cleric + Rogue + Mage
- Paladin + Ranger + Druid + Rogue

Balance goal:

No single class should be mandatory, but every class should contribute something distinct.

## 4. Core Game Structure

### Home Base

Brambleford is the main town hub.

### Outer Adventure Ring

Players leave town for nearby zones:

- Goblin Road
- Whispering Woods
- Old Barrow Field
- Ruined Watchtower
- Goblin Warrens
- Blackfen Approach

### Core Loop

- Get quests in town
- Travel into danger
- Fight enemies
- Gather loot, materials, and story clues
- Complete quests
- Upgrade gear and abilities
- Push deeper into harder zones

## 5. World Setting

### Brambleford

A frontier river-town at the edge of old woods and older ruins. Lantern posts line the streets and are treated almost like sacred town guardians. The people of Brambleford are resilient, funny, and practical.

### Town Mood

- Safe
- Slightly eccentric
- Colorful personalities
- Lots of small problems and bigger rumors

### Outer World Mood

- Goblin raids
- Wolves too close to town
- Old burial mounds stirring
- Bandits occupying a ruined watchtower
- Strange corruption spreading from deeper places

## 6. Races

Keep race bonuses meaningful but secondary to class.

### 6.1 Human

- Theme: flexible, ambitious, practical
- Perk: `Resolve`
- Small XP bonus or cooldown recovery bonus
- Flavor: good at anything, easy starter pick

### 6.2 Elf

- Theme: graceful, perceptive, magical
- Perk: `Keen Senses`
- Small bonus to accuracy and resistance to ambush
- Flavor: naturally suited to Ranger, Mage, Druid

### 6.3 Dwarf

- Theme: hardy, disciplined, stubborn
- Perk: `Stoneblood`
- Bonus to max HP and minor resistance to stun or bleed
- Flavor: ideal for Warrior, Paladin, Cleric

### 6.4 Halfling

- Theme: quick, lucky, underestimated
- Perk: `Fortune's Step`
- Small dodge and crit bonus
- Flavor: ideal for Rogue, Ranger, funny class and race pairings

### 6.5 Half-Orc

- Theme: fierce, intimidating, strong
- Perk: `Battle Hunger`
- Slight bonus to damage at low health
- Flavor: ideal for Warrior, Rogue, Paladin in a rough-edged heroic way

## 7. Classes

There are 7 total classes.

### 7.1 Warrior

Frontline fighter, shield wall, aggro holder, physical protector.

- Role: tank, frontline control, threat generation, party protection
- Primary stats: Vitality, Strength

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

Signature abilities:

- Defend: reduce incoming damage temporarily
- Shield Bash: damage plus stagger chance
- Battle Cry: taunt nearby enemies and boost defense
- Intercept: take a hit for an ally
- Brace: root yourself and become very hard to kill
- Last Stand: major survival cooldown

### 7.2 Ranger

Mobile physical damage dealer with traps and target control.

- Role: ranged DPS, wilderness utility, single-target pressure, light AoE
- Primary stats: Agility, Precision

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

Signature abilities:

- Mark Prey: target takes extra damage
- Snare Trap: slows or roots
- Volley: light multi-target attack
- Barbed Arrow: bleed effect
- Rain of Arrows: strong ranged AoE

### 7.3 Mage

Elemental caster with burst damage and battlefield control.

- Role: magic DPS, crowd control, elemental status effects, risky power class
- Primary stats: Intellect, Spirit

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

Signature abilities:

- Firebolt: core magic damage spell
- Frost Bind: slow or root
- Arc Spark: chaining lightning hit
- Flame Wave: close-range AoE
- Mana Shield: absorb damage with mana
- Meteor Sigil: major burst spell

### 7.4 Cleric

Holy healer and support class with anti-undead utility.

- Role: healer, support, cleanse, undead counter
- Primary stats: Spirit, Vitality

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

Signature abilities:

- Heal: single-target heal
- Smite: bonus damage vs undead or shadow enemies
- Blessing: party buff
- Renewing Light: heal over time
- Sanctuary: party damage reduction window
- Cleanse: remove poison, bleed, or curse
- Guardian Light: major emergency save ability

### 7.5 Rogue

Stealthy burst-damage class with tricks and opportunism.

- Role: burst DPS, stealth and scouting, debuffs, lock and trap flavor
- Primary stats: Agility, Precision

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

Signature abilities:

- Backstab: strong damage from an opening
- Poison Blade: applies poison
- Vanish: temporary escape or aggro drop
- Cheap Shot: stun or stagger opener
- Shadowstep: rapid reposition attack
- Eviscerate: high-damage finisher

### 7.6 Paladin

Holy armored fighter blending survivability, support, and smiting.

- Role: off-tank, support tank, holy bruiser, protection
- Primary stats: Vitality, Spirit, Strength

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

Signature abilities:

- Holy Strike: weapon hit infused with holy damage
- Guarding Aura: small group defense aura
- Judgement: marked holy damage attack
- Hand of Mercy: minor heal or support
- Consecrate: holy ground AoE
- Shield of Dawn: absorb and reflect some damage
- Avenging Light: dramatic holy burst cooldown

### 7.7 Druid

Nature caster blending healing, control, and wild magic.

- Role: hybrid support, healer or off-healer, control caster, nature damage
- Primary stats: Spirit, Intellect

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

Signature abilities:

- Thorn Lash: nature damage attack
- Minor Mend: light heal
- Entangling Roots: enemy control
- Moonfire: damage over time
- Barkskin: defensive buff
- Swarm: multi-target pressure
- Rejuvenation Grove: group healing area
- Wrath of the Grove: big hybrid damage and support spell

## 8. Phase-1 Class Recommendation

Build order:

1. Warrior
2. Cleric
3. Ranger
4. Mage
5. Rogue
6. Paladin
7. Druid

That gives the classic fantasy core first.

## 9. Core Stats

Primary stats:

- Strength
- Agility
- Intellect
- Spirit
- Vitality

Derived stats:

- Max HP
- Max Mana
- Max Stamina
- Attack Power
- Spell Power
- Armor
- Accuracy
- Crit Chance
- Dodge
- Threat
- Resistances

## 10. Resource Model

Stamina classes:

- Warrior
- Ranger
- Rogue
- Paladin

Mana classes:

- Mage
- Cleric
- Druid

Paladin could go either way, but for simplicity in phase 1 it stays stamina-based.

## 11. Gear Model

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

## 12. Combat Model

Combat goals:

- Tactical
- Party-friendly
- Fast enough to stay fun
- Clear in text
- Class-driven

Core mechanics:

- Auto or basic attacks
- Active abilities with cooldowns
- Stamina or mana costs
- Aggro and threat
- Status effects
- Enemy special abilities
- Bosses with readable patterns

Status effects:

- Bleed
- Burn
- Poison
- Slow
- Root
- Stagger
- Curse
- Holy Mark
- Weakness

Enemy roles:

- Skirmisher
- Brute
- Caster
- Support
- Elite
- Boss

## 13. Town: Brambleford

Description:

A lantern-lit frontier town built beside an old river crossing. It is full of practical townsfolk, minor squabbles, warmth, gossip, and signs that something is going wrong just beyond the boundaries.

Key locations:

- The Lantern Rest Inn
- Ironroot Forge
- Brambleford Outfitters
- Chapel of the Dawn Bell
- Town Green
- Training Yard
- Mayor's Hall
- East Gate
- West Market Lane
- Rat and Kettle Tavern Cellar

Key NPCs:

- Mayor Elric Thorne: practical, burdened, decent
- Sister Maybelle: warm, sharp, dependable
- Torren Ironroot: gruff dwarf blacksmith with dry humor
- Mira Fenleaf: elven hunter and wilderness guide
- Uncle Pib Underbough: halfling inn cook and comic relief quest source
- Joss Veller: town lamplighter who knows more than he admits
- Captain Harl Rowan: town militia veteran and Warrior trainer
- Brother Alden: assistant cleric and slightly anxious lore source

## 14. Zones

### 14.1 Goblin Road

- Tone: adventurous, lively, lightly dangerous
- Enemies: Thorn Rat, Road Wolf, Goblin Sneak, Goblin Cutter
- Boss: Ruk the Fence-Cutter

### 14.2 Whispering Woods

- Tone: mysterious, layered, slightly eerie
- Enemies: Forest Wolf, Cave Spider, Briar Imp, Mossling
- Boss: Old Greymaw

### 14.3 Old Barrow Field

- Tone: solemn, dangerous, darker than earlier zones
- Enemies: Skeletal Soldier, Restless Shade, Grave Crow, Barrow Wisp
- Boss: Sir Edric the Restless

### 14.4 Ruined Watchtower

- Tone: grounded fantasy danger, tactical, heroism through siege-like encounters
- Enemies: Bandit Scout, Bandit Raider, Tower Archer, Carrion Hound
- Boss: Captain Varn Blackreed

### 14.5 Goblin Warrens

- Tone: ugly, mean, energetic dungeon zone
- Enemies: Goblin Hexer, Goblin Brute, Cave Bat Swarm, Sludge Slime
- Boss: Grubnak the Pot-King

### 14.6 Blackfen Approach

- Tone: grim, windswept, serious, not yet fully conquered
- Enemies: Mire Hound, Bog Creeper, Fen Wisp, Rot Crow
- Elite: Miretooth

This zone helps foreshadow phase 2.

## 15. Core Bestiary

Phase-1 core monsters:

- Thorn Rat
- Road Wolf
- Goblin Sneak
- Goblin Cutter
- Forest Wolf
- Cave Spider
- Briar Imp
- Mossling
- Skeletal Soldier
- Restless Shade
- Bandit Scout
- Bandit Raider
- Goblin Brute
- Goblin Hexer
- Mire Hound
- Fen Wisp

## 16. Bosses And Named Elites

### Ruk the Fence-Cutter

- Goblin raider chief with stolen farm gear
- Mechanics: bleed, add summoning, low-health enrage

### Old Greymaw

- Massive scarred wolf of the woods
- Mechanics: lunges, bleed, vanishing reposition

### Sir Edric the Restless

- Ancient knight risen from the barrows
- Mechanics: shielded phases, undead adds, curse aura

### Captain Varn Blackreed

- Bandit leader in the watchtower
- Mechanics: ranged orders, add coordination, punishes weak targets

### Grubnak the Pot-King

- Huge goblin boss in the warrens
- Mechanics: boiling stew throws, goblin waves, stagger slam

### Miretooth

- Predatory fen beast stalking Blackfen
- Mechanics: poison, ambush, fear flavor

## 17. Quest Structure

Quest types:

- Kill quests
- Collection quests
- Delivery quests
- Exploration quests
- Boss hunts
- Story quests
- Funny town quests

Phase-1 starter quests:

Town quests:

- Rats in the Kettle
- A Blade Needs a Hand
- Lanterns at Dusk
- The Baker's Missing Flour
- Practice Makes Heroes

Goblin Road quests:

- Fencebreakers
- Roadside Howls
- The Stolen Satchel

Whispering Woods quests:

- Herbs for Sister Maybelle
- What Whispers in the Wood
- Greymaw's Trail

Barrow quests:

- Do Not Disturb the Dead
- The Knight Without Rest

Watchtower and dungeon quests:

- Signals Gone Dark
- The Pot-King's Feast

Optional extras:

- Bogwater Rumors
- A Ring in the Mud
- The Lamplighter's Secret

## 18. Story Arc

### Act 1: Small Local Problems

Goblins raid fences, wolves prowl too close, lanterns are being sabotaged.

### Act 2: The Woods Are Wrong

The forest feels uneasy, trails shift, and strange whispers are heard among old stones.

### Act 3: The Dead Stir

The barrows awaken and ancient protections begin to fail.

### Act 4: Mortal Opportunists

Bandits in the Ruined Watchtower capitalize on the chaos.

### Act 5: The Goblin Power Center

The Goblin Warrens reveal organization, arming, and hints of outside influence.

### Act 6: Something Beyond

Blackfen Approach suggests the threat reaches beyond goblins and bandits.

## 19. Party Synergy

Example 4-player classic party:

- Warrior
- Cleric
- Ranger
- Mage

Other party setups:

Holy frontline:

- Warrior
- Paladin
- Cleric
- Ranger

Aggressive burst team:

- Warrior
- Rogue
- Mage
- Cleric

Nature and skirmish team:

- Paladin
- Ranger
- Druid
- Rogue

Durable adventure party:

- Warrior
- Paladin
- Cleric
- Mage

## 20. Progression Model

- Phase-1 cap: level 10
- Players start with 2 abilities
- Progression should grant new active abilities, passive traits, gear upgrades, and stronger zone access
- Every level should feel meaningful
- Suggested leveling pace: fast early levels, moderate midgame
- Level 10 should be reached around the end of the phase-1 story arc

## 21. Phase-1 Implementation Priorities

Systems first:

- Character creation
- Races
- Classes
- Stats and resources
- Inventory and equipment
- Combat engine
- Enemy AI
- Quests
- Loot tables
- Room and zone content

Content order:

1. Brambleford
2. Goblin Road
3. Whispering Woods
4. Old Barrow Field
5. Ruined Watchtower
6. Goblin Warrens
7. Blackfen Approach

Class order:

1. Warrior
2. Cleric
3. Ranger
4. Mage
5. Rogue
6. Paladin
7. Druid

That gets the most recognizable fun in place early.

## 23. Final Phase-1 Summary

Working title: `Brave`

Phase-1 scope:

- 1 town hub
- 6 outer zones
- 7 classes
- 5 races
- 16 core monster types
- 6 bosses or elites
- Level cap 10
- 15 to 18 starter quests
- 1 to 4 player local co-op design

Core fantasy:

A warm little town and a dangerous world beyond it, where a family party of fantasy adventurers grows stronger through quests, gear, class abilities, and boss fights.
