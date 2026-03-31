"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from world.data.character_options import (
    CLASSES,
    MAX_LEVEL,
    PRIMARY_STATS,
    RACES,
    STARTING_CLASS,
    STARTING_RACE,
    XP_FOR_LEVEL,
)
from world.chapel import get_active_blessing
from world.data.activities import COZY_BONUS
from world.data.items import EQUIPMENT_SLOTS, ITEM_TEMPLATES, STARTER_LOADOUTS
from world.party import ensure_party_state
from world.questing import advance_item_collection, advance_room_visit, ensure_starter_quests
from world.tutorial import ensure_tutorial_state, handle_room_enter, is_tutorial_active

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    default_description = "A sturdy-looking adventurer taking their first steps into danger."

    def at_object_creation(self):
        super().at_object_creation()
        self.ensure_brave_character()

    def at_post_move(self, source_location, move_type="move", **kwargs):
        super().at_post_move(source_location, move_type=move_type, **kwargs)
        if self.location:
            if source_location and source_location != self.location and move_type not in {"defeat", "flee"}:
                self.ndb.brave_previous_location = source_location
            advance_room_visit(self, self.location)
            handle_room_enter(self, self.location)
            if move_type not in {"defeat", "flee"}:
                from world.party import handle_party_follow
                from typeclasses.scripts import BraveEncounter

                handle_party_follow(self, source_location, move_type=move_type)
                BraveEncounter.maybe_auto_aggro(self)

    def at_pre_move(self, destination, **kwargs):
        if kwargs.get("move_type") not in {"defeat", "flee"}:
            encounter = self.get_active_encounter()
            if encounter and encounter.is_participant(self):
                self.msg("You can't leave in the middle of a fight.")
                return False
        return super().at_pre_move(destination, **kwargs)

    def at_post_puppet(self, **kwargs):
        sessions = self.sessions.get()
        latest_session = sessions[-1] if sessions else None
        self.msg(brave_clear={}, session=latest_session)
        super().at_post_puppet(**kwargs)
        self.ensure_brave_character()
        if not self.db.brave_seen_welcome:
            if is_tutorial_active(self):
                self.msg(
                    "|yWelcome to Brave.|n Sergeant Tamsin is ready to square you away. "
                    "Use |wtalk tamsin|n to begin, |wquests|n to keep the lesson in view, and cardinal movement "
                    "with |wn|n, |we|n, |ws|n, |ww|n, |wu|n, and |wd|n to move around the yard."
                )
            else:
                self.msg(
                    "|yWelcome to Brave.|n Use |wsheet|n to view your adventurer, "
                    "|wgear|n to inspect your kit, |wquests|n to check objectives, and "
                    "|wmap|n to see the local layout. Cardinal movement works with |wn|n, |we|n, "
                    "|ws|n, |ww|n, |wu|n, and |wd|n. Named |wtravel|n still works as a fallback. "
                    "Use |wparty where|n to find family and |wparty follow|n to stay together. "
                    "Brambleford's wharf supports |wfish|n and the inn hearth supports |wcook|n."
                )
            self.db.brave_seen_welcome = True

    def ensure_brave_character(self):
        """Initialize Brave-specific state if missing."""

        if not self.db.brave_race:
            self.db.brave_race = STARTING_RACE
        if not self.db.brave_class:
            self.db.brave_class = STARTING_CLASS
        if not self.db.brave_level:
            self.db.brave_level = 1
        if self.db.brave_xp is None:
            self.db.brave_xp = 0
        equipment = dict(self.db.brave_equipment or {})
        if not equipment:
            equipment = {slot: None for slot in EQUIPMENT_SLOTS}
        else:
            for slot in EQUIPMENT_SLOTS:
                equipment.setdefault(slot, None)
        self.db.brave_equipment = equipment
        if self.db.brave_inventory is None:
            self.db.brave_inventory = []
        if self.db.brave_silver is None:
            self.db.brave_silver = 0
        if self.db.brave_shop_bonus is None:
            self.db.brave_shop_bonus = {}
        if self.db.brave_meal_buff is None:
            self.db.brave_meal_buff = {}
        if self.db.brave_chapel_blessing is None:
            self.db.brave_chapel_blessing = {}
        ensure_party_state(self)
        ensure_tutorial_state(self)
        if not self.db.desc:
            self.db.desc = self.default_description
        ensure_starter_quests(self)
        self.ensure_starter_loadout()
        self.recalculate_stats()

    def recalculate_stats(self, restore=False):
        """Recalculate primary and derived stats from current race/class/level."""

        race = RACES[self.db.brave_race]
        class_data = CLASSES[self.db.brave_class]
        level = max(1, min(self.db.brave_level, MAX_LEVEL))

        primary = {}
        for stat in PRIMARY_STATS:
            primary[stat] = class_data["base_stats"].get(stat, 0) + race["bonuses"].get(stat, 0)

        equipment_bonuses = self.get_equipment_bonuses()
        for stat in PRIMARY_STATS:
            primary[stat] += equipment_bonuses.get(stat, 0)

        meal_bonuses = self.get_active_meal_bonuses()
        for stat in PRIMARY_STATS:
            primary[stat] += meal_bonuses.get(stat, 0)

        chapel_bonuses = self.get_active_chapel_bonuses()
        for stat in PRIMARY_STATS:
            primary[stat] += chapel_bonuses.get(stat, 0)

        derived = {
            "max_hp": 55 + (primary["vitality"] * 10) + (level * 8),
            "max_mana": 12 + (primary["intellect"] + primary["spirit"]) * 5 + (level * 4),
            "max_stamina": 24 + (primary["strength"] + primary["agility"] + primary["vitality"]) * 3 + (level * 5),
            "attack_power": primary["strength"] * 2 + primary["agility"] + (level * 2),
            "spell_power": primary["intellect"] * 2 + primary["spirit"] + (level * 2),
            "armor": primary["vitality"] * 2 + primary["strength"] + level,
            "accuracy": 65 + primary["agility"] * 2 + level,
            "precision": primary["agility"] * 2 + (level // 2),
            "crit_chance": 5 + (primary["agility"] // 2),
            "dodge": 3 + primary["agility"] + (level // 2),
            "threat": 5 + primary["vitality"] + (5 if self.db.brave_class in ("warrior", "paladin") else 0),
        }
        for stat, bonus in equipment_bonuses.items():
            if stat in PRIMARY_STATS:
                continue
            derived[stat] = derived.get(stat, 0) + bonus

        for stat, bonus in meal_bonuses.items():
            if stat in PRIMARY_STATS:
                continue
            derived[stat] = derived.get(stat, 0) + bonus

        for stat, bonus in chapel_bonuses.items():
            if stat in PRIMARY_STATS:
                continue
            derived[stat] = derived.get(stat, 0) + bonus

        self.db.brave_primary_stats = primary
        self.db.brave_derived_stats = derived

        resource_pool = self.db.brave_resources or {}
        resources = {
            "hp": min(resource_pool.get("hp", derived["max_hp"]), derived["max_hp"]),
            "mana": min(resource_pool.get("mana", derived["max_mana"]), derived["max_mana"]),
            "stamina": min(resource_pool.get("stamina", derived["max_stamina"]), derived["max_stamina"]),
        }
        if restore or not resource_pool:
            resources = {
                "hp": derived["max_hp"],
                "mana": derived["max_mana"],
                "stamina": derived["max_stamina"],
            }
        self.db.brave_resources = resources
        return primary, derived

    def grant_xp(self, amount):
        """Grant XP and return any level-up messages."""

        self.ensure_brave_character()
        self.db.brave_xp = max(0, self.db.brave_xp + amount)
        messages = []
        level = self.db.brave_level

        while level < MAX_LEVEL and self.db.brave_xp >= XP_FOR_LEVEL[level + 1]:
            level += 1
            self.db.brave_level = level
            messages.append(f"|gYou are now level |w{level}|n!")

        if messages:
            self.recalculate_stats(restore=True)

        return messages

    def restore_resources(self):
        """Restore HP, mana, and stamina to full."""

        self.ensure_brave_character()
        derived = self.db.brave_derived_stats
        self.db.brave_resources = {
            "hp": derived["max_hp"],
            "mana": derived["max_mana"],
            "stamina": derived["max_stamina"],
        }

    def get_active_encounter(self):
        """Return the current room encounter, if any."""

        if not self.location:
            return None

        from typeclasses.scripts import BraveEncounter

        return BraveEncounter.get_for_room(self.location)

    def can_customize_build(self):
        """Whether the character can still change race/class freely."""

        return (
            self.db.brave_level == 1
            and self.db.brave_xp == 0
            and not self.get_active_encounter()
        )

    def set_brave_race(self, race_key):
        """Set a new race and rebuild derived state."""

        self.db.brave_race = race_key
        self.recalculate_stats(restore=True)

    def set_brave_class(self, class_key):
        """Set a new class and rebuild derived state."""

        self.db.brave_class = class_key
        self.ensure_starter_loadout(force=True)
        self.recalculate_stats(restore=True)

    def get_unlocked_abilities(self):
        """Return class abilities unlocked at the current level."""

        class_data = CLASSES[self.db.brave_class]
        level = self.db.brave_level
        return [ability for unlock_level, ability in class_data["progression"] if unlock_level <= level]

    def ensure_starter_loadout(self, force=False):
        """Apply the class starter loadout if it has not been seeded yet."""

        class_key = self.db.brave_class or STARTING_CLASS
        current = self.db.brave_starter_loadout_class
        should_refresh = force or not current
        if current and current != class_key and self.can_customize_build():
            should_refresh = True
        if not should_refresh:
            return

        equipment = {slot: None for slot in EQUIPMENT_SLOTS}
        equipment.update(STARTER_LOADOUTS.get(class_key, {}))
        self.db.brave_equipment = equipment
        self.db.brave_starter_loadout_class = class_key

    def get_equipment_bonuses(self):
        """Return cumulative bonuses from equipped gear."""

        totals = {}
        for template_id in (self.db.brave_equipment or {}).values():
            template = ITEM_TEMPLATES.get(template_id)
            if not template:
                continue
            for stat, value in template.get("bonuses", {}).items():
                totals[stat] = totals.get(stat, 0) + value
        return totals

    def get_active_meal_bonuses(self):
        """Return bonuses from the current active meal buff, if any."""

        meal_buff = dict(self.db.brave_meal_buff or {})
        totals = dict(meal_buff.get("bonuses", {}))
        if meal_buff.get("cozy"):
            for stat, value in COZY_BONUS.items():
                totals[stat] = totals.get(stat, 0) + value
        return totals

    def get_active_chapel_bonuses(self):
        """Return bonuses from the current Dawn Bell blessing, if any."""

        blessing = get_active_blessing(self)
        return dict(blessing.get("bonuses", {}))

    def apply_meal_buff(self, template_id, cozy=False):
        """Apply a persistent meal bonus from a cooked item."""

        template = ITEM_TEMPLATES.get(template_id)
        if not template:
            return {}

        self.db.brave_meal_buff = {
            "template": template_id,
            "name": template["name"],
            "bonuses": dict(template.get("meal_bonuses", {})),
            "cozy": bool(cozy),
        }
        self.recalculate_stats()
        return self.db.brave_meal_buff

    def clear_chapel_blessing(self):
        """Clear the active chapel blessing if present."""

        if not (self.db.brave_chapel_blessing or {}):
            return False
        self.db.brave_chapel_blessing = {}
        self.recalculate_stats()
        return True

    def get_inventory_quantity(self, template_id):
        """Return how many of an item the character currently carries."""

        return sum(
            entry.get("quantity", 0)
            for entry in (self.db.brave_inventory or [])
            if entry.get("template") == template_id
        )

    def add_item_to_inventory(self, template_id, quantity=1):
        """Add a stackable loot item to the character inventory."""

        if quantity <= 0 or template_id not in ITEM_TEMPLATES:
            return

        inventory = list(self.db.brave_inventory or [])
        for entry in inventory:
            if entry["template"] == template_id:
                entry["quantity"] += quantity
                self.db.brave_inventory = inventory
                advance_item_collection(self)
                return

        inventory.append({"template": template_id, "quantity": quantity})
        self.db.brave_inventory = inventory
        advance_item_collection(self)

    def remove_item_from_inventory(self, template_id, quantity=1):
        """Remove a stackable item from inventory if enough are present."""

        if quantity <= 0:
            return False

        inventory = list(self.db.brave_inventory or [])
        for entry in inventory:
            if entry.get("template") != template_id:
                continue
            if entry.get("quantity", 0) < quantity:
                return False
            entry["quantity"] -= quantity
            if entry["quantity"] <= 0:
                inventory.remove(entry)
            self.db.brave_inventory = inventory
            advance_item_collection(self)
            return True
        return False
