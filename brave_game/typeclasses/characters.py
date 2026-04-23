"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from world.content import get_content_registry
from world.chapel import get_active_blessing
from world.data.items import (
    EQUIPMENT_SLOTS,
    ITEM_TEMPLATES,
    STARTER_CONSUMABLES,
    STARTER_LOADOUTS,
    format_allowed_class_summary,
    is_equipment_allowed_for_class,
)
from world.mastery import (
    MASTERY_RESPEC_SILVER_COST,
    can_train_ability,
    mastery_points_earned,
)
from world.navigation import discover_room
from world.genders import DEFAULT_BRAVE_GENDER, get_brave_gender_label, normalize_brave_gender
from world.party import ensure_party_state
from world.paladin_oaths import DEFAULT_PALADIN_OATH, get_oath, get_oath_name
from world.questing import advance_item_collection, advance_room_visit, ensure_starter_quests
from world.ranger_companions import (
    DEFAULT_RANGER_COMPANION,
    get_companion,
    get_companion_name,
    normalize_companion_bond_state,
)
from world.tutorial import ensure_tutorial_state, handle_room_enter, is_tutorial_active

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent

CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters
COZY_BONUS = CONTENT.systems.cozy_bonus
CLASS_STARTER_ITEMS = {
    "mage": (("mirror_veil_primer", 1),),
}
LEGACY_RACE_KEYS = {
    "halfling": "mosskin",
    "half_orc": "ashborn",
}


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    default_description = "A sturdy-looking adventurer taking their first steps into danger."

    @staticmethod
    def _canonicalize_race_key(race_key):
        race_key = str(race_key or "").strip().lower()
        return LEGACY_RACE_KEYS.get(race_key, race_key)

    def at_object_creation(self):
        super().at_object_creation()
        self.ensure_brave_character()

    def at_post_move(self, source_location, move_type="move", **kwargs):
        super().at_post_move(source_location, move_type=move_type, **kwargs)
        if self.location:
            discover_room(self, self.location)
            if source_location and source_location != self.location and move_type not in {"defeat", "flee"}:
                self.ndb.brave_previous_location = source_location
            advance_room_visit(self, self.location)
            handle_room_enter(self, self.location)
            if move_type not in {"defeat", "flee"}:
                from world.party import handle_party_follow

                handle_party_follow(self, source_location, move_type=move_type)

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
        protocol = (getattr(latest_session, "protocol_key", "") or "").lower() if latest_session else ""
        if self.account:
            self.account.db._last_puppet = self
        self.ensure_brave_character()
        if not self.db.brave_seen_welcome:
            self.db.brave_seen_welcome = True
        if protocol in {"websocket", "ajax/comet", "webclient"}:
            if self.location:
                discover_room(self, self.location)
                self.location.return_appearance(self)
            return
        super().at_post_puppet(**kwargs)

    def ensure_brave_character(self):
        """Initialize Brave-specific state if missing."""

        if not self.db.brave_race:
            self.db.brave_race = CHARACTER_CONTENT.starting_race
        else:
            self.db.brave_race = self._canonicalize_race_key(self.db.brave_race)
        if not self.db.brave_class:
            self.db.brave_class = CHARACTER_CONTENT.starting_class
        normalized_gender = normalize_brave_gender(self.db.brave_gender, default=DEFAULT_BRAVE_GENDER)
        self.db.brave_gender = normalized_gender
        self.db.gender = normalized_gender
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
        if self.db.brave_known_tinkering_recipes is None:
            self.db.brave_known_tinkering_recipes = []
        if self.db.brave_known_cooking_recipes is None:
            self.db.brave_known_cooking_recipes = []
        if self.db.brave_active_fishing_rod is None:
            self.db.brave_active_fishing_rod = ""
        if self.db.brave_active_fishing_lure is None:
            self.db.brave_active_fishing_lure = ""
        if self.db.brave_chapel_blessing is None:
            self.db.brave_chapel_blessing = {}
        if self.db.brave_learned_abilities is None:
            self.db.brave_learned_abilities = []
        if getattr(self.db, "brave_ability_mastery", None) is None:
            self.db.brave_ability_mastery = {}
        if self.db.brave_class_feature_items_class is None:
            self.db.brave_class_feature_items_class = ""
        if self.db.brave_companions is None:
            self.db.brave_companions = []
        if self.db.brave_active_companion is None:
            self.db.brave_active_companion = ""
        if getattr(self.db, "brave_companion_bonds", None) is None:
            self.db.brave_companion_bonds = {}
        if self.db.brave_paladin_oaths is None:
            self.db.brave_paladin_oaths = []
        if self.db.brave_active_oath is None:
            self.db.brave_active_oath = ""
        if self.db.brave_rogue_theft_log is None:
            self.db.brave_rogue_theft_log = {}
        if getattr(self.db, "brave_discovered_rooms", None) is None:
            self.db.brave_discovered_rooms = []
        ensure_party_state(self)
        ensure_tutorial_state(self)
        if not self.db.desc:
            self.db.desc = self.default_description
        ensure_starter_quests(self)
        self.ensure_starter_loadout()
        self.ensure_starter_consumables()
        self.ensure_class_starter_items()
        self.ensure_ranger_companion()
        self.ensure_paladin_oath()
        self.recalculate_stats()

    def recalculate_stats(self, restore=False):
        """Recalculate primary and derived stats from current race/class/level."""

        race = CHARACTER_CONTENT.races[self.db.brave_race]
        class_data = CHARACTER_CONTENT.classes[self.db.brave_class]
        level = max(1, min(self.db.brave_level, CHARACTER_CONTENT.max_level))

        primary = {}
        for stat in CHARACTER_CONTENT.primary_stats:
            primary[stat] = class_data["base_stats"].get(stat, 0) + race["bonuses"].get(stat, 0)

        passive_bonuses = CHARACTER_CONTENT.get_passive_ability_bonuses(self.db.brave_class, level)
        race_perk_bonuses = dict(race.get("perk_bonuses", {}))
        for stat in CHARACTER_CONTENT.primary_stats:
            primary[stat] += passive_bonuses.get(stat, 0)
            primary[stat] += race_perk_bonuses.get(stat, 0)

        equipment_bonuses = self.get_equipment_bonuses()
        for stat in CHARACTER_CONTENT.primary_stats:
            primary[stat] += equipment_bonuses.get(stat, 0)

        meal_bonuses = self.get_active_meal_bonuses()
        for stat in CHARACTER_CONTENT.primary_stats:
            primary[stat] += meal_bonuses.get(stat, 0)

        chapel_bonuses = self.get_active_chapel_bonuses()
        for stat in CHARACTER_CONTENT.primary_stats:
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
            "healing_power": 0,
        }
        for stat, bonus in race_perk_bonuses.items():
            if stat in CHARACTER_CONTENT.primary_stats:
                continue
            derived[stat] = derived.get(stat, 0) + bonus
        for stat, bonus in passive_bonuses.items():
            if stat in CHARACTER_CONTENT.primary_stats:
                continue
            derived[stat] = derived.get(stat, 0) + bonus
        for stat, bonus in equipment_bonuses.items():
            if stat in CHARACTER_CONTENT.primary_stats:
                continue
            derived[stat] = derived.get(stat, 0) + bonus

        for stat, bonus in meal_bonuses.items():
            if stat in CHARACTER_CONTENT.primary_stats:
                continue
            derived[stat] = derived.get(stat, 0) + bonus

        for stat, bonus in chapel_bonuses.items():
            if stat in CHARACTER_CONTENT.primary_stats:
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

        while level < CHARACTER_CONTENT.max_level and self.db.brave_xp >= CHARACTER_CONTENT.xp_for_level[level + 1]:
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

        self.db.brave_race = self._canonicalize_race_key(race_key)
        self.recalculate_stats(restore=True)

    def set_brave_class(self, class_key):
        """Set a new class and rebuild derived state."""

        self.db.brave_class = class_key
        self.ensure_starter_loadout(force=True)
        self.ensure_class_starter_items(force=True)
        self.ensure_paladin_oath()
        self.recalculate_stats(restore=True)

    def set_brave_gender(self, gender_key):
        """Set the Brave gender key for this character."""

        normalized = normalize_brave_gender(gender_key, default=DEFAULT_BRAVE_GENDER)
        self.db.brave_gender = normalized
        self.db.gender = normalized
        return normalized

    def get_brave_gender_label(self):
        """Return the display label for the current Brave gender."""

        return get_brave_gender_label(self.db.brave_gender)

    def get_unlocked_abilities(self):
        """Return class abilities unlocked at the current level."""

        class_data = CHARACTER_CONTENT.classes[self.db.brave_class]
        level = self.db.brave_level
        unlocked = [ability for unlock_level, ability in class_data["progression"] if unlock_level <= level]
        seen = {CHARACTER_CONTENT.ability_key(name) for name in unlocked}
        for ability_name in self.get_learned_abilities():
            key = CHARACTER_CONTENT.ability_key(ability_name)
            if key in seen:
                continue
            seen.add(key)
            unlocked.append(ability_name)
        return unlocked

    def get_learned_abilities(self):
        """Return extra non-progression abilities learned through class systems."""

        learned = []
        for ability_key in (self.db.brave_learned_abilities or []):
            ability = CHARACTER_CONTENT.ability_library.get(str(ability_key or "").lower())
            if not ability or ability.get("class") != self.db.brave_class:
                continue
            learned.append(ability.get("name", str(ability_key)))
        return learned

    def learn_ability(self, ability_key):
        """Persist a learned ability if it matches the current class."""

        normalized = CHARACTER_CONTENT.ability_key(ability_key)
        ability = CHARACTER_CONTENT.ability_library.get(normalized)
        if not ability:
            return False, "That technique does not exist."
        if ability.get("class") != self.db.brave_class:
            return False, f"{ability.get('name', 'That ability')} does not belong to your current class."
        learned = [str(key).lower() for key in (self.db.brave_learned_abilities or [])]
        if normalized in learned:
            return False, f"You already know {ability.get('name', 'that technique')}."
        learned.append(normalized)
        self.db.brave_learned_abilities = learned
        return True, f"You learn {ability.get('name', 'a new technique')}."

    def get_unlocked_combat_abilities(self):
        """Return unlocked combat actions that can be queued with `use`."""

        actions, _passives, _unknown = CHARACTER_CONTENT.split_unlocked_abilities(self.db.brave_class, self.db.brave_level)
        return actions

    def get_ability_mastery_rank(self, ability_key):
        """Return current mastery rank for one combat ability."""

        normalized = CHARACTER_CONTENT.ability_key(ability_key)
        if not can_train_ability(self, normalized):
            return 1
        mastery = dict(getattr(self.db, "brave_ability_mastery", None) or {})
        return max(1, min(int(mastery.get(normalized, 1) or 1), 3))

    def get_ability_mastery_map(self):
        """Return normalized mastery mapping for unlocked combat abilities."""

        mastery = {}
        for ability_name in self.get_unlocked_combat_abilities():
            normalized = CHARACTER_CONTENT.ability_key(ability_name)
            mastery[normalized] = self.get_ability_mastery_rank(normalized)
        return mastery

    def get_earned_mastery_points(self):
        """Return total mastery points earned from level milestones."""

        return mastery_points_earned(self.db.brave_level)

    def get_spent_mastery_points(self):
        """Return currently spent mastery points."""

        return sum(max(0, rank - 1) for rank in self.get_ability_mastery_map().values())

    def get_available_mastery_points(self):
        """Return unspent mastery points."""

        return max(0, self.get_earned_mastery_points() - self.get_spent_mastery_points())

    def set_ability_mastery_rank(self, ability_key, rank):
        """Persist one mastery rank if the ability is trainable."""

        normalized = CHARACTER_CONTENT.ability_key(ability_key)
        if not can_train_ability(self, normalized):
            return False
        mastery = dict(getattr(self.db, "brave_ability_mastery", None) or {})
        mastery[normalized] = max(1, min(int(rank or 1), 3))
        self.db.brave_ability_mastery = mastery
        return True

    def train_ability_mastery(self, ability_key):
        """Advance one combat ability by one mastery tier."""

        normalized = CHARACTER_CONTENT.ability_key(ability_key)
        ability = CHARACTER_CONTENT.ability_library.get(normalized)
        if not ability or not can_train_ability(self, normalized):
            return False, "You cannot refine that technique right now."
        current = self.get_ability_mastery_rank(normalized)
        if current >= 3:
            return False, f"{ability.get('name', 'That ability')} is already mastered."
        if self.get_available_mastery_points() <= 0:
            return False, "You do not have an unspent mastery point."
        self.set_ability_mastery_rank(normalized, current + 1)
        return True, f"{ability.get('name', 'That ability')} rises to rank {current + 1}."

    def reset_ability_mastery(self):
        """Reset all spent ability mastery for a silver fee."""

        spent = self.get_spent_mastery_points()
        if spent <= 0:
            return False, "You have no spent mastery to reset."
        if (self.db.brave_silver or 0) < MASTERY_RESPEC_SILVER_COST:
            return False, f"You need {MASTERY_RESPEC_SILVER_COST} silver to reset your mastery."
        self.db.brave_silver = max(0, int(self.db.brave_silver or 0) - MASTERY_RESPEC_SILVER_COST)
        self.db.brave_ability_mastery = {}
        return True, "Your mastery focus is reset."

    def get_unlocked_passive_abilities(self):
        """Return unlocked passive traits that apply automatically."""

        _actions, passives, _unknown = CHARACTER_CONTENT.split_unlocked_abilities(self.db.brave_class, self.db.brave_level)
        return passives

    def ensure_starter_loadout(self, force=False):
        """Apply the class starter loadout if it has not been seeded yet."""

        class_key = self.db.brave_class or CHARACTER_CONTENT.starting_class
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

    def ensure_starter_consumables(self):
        """Seed one starter stack of practical consumables."""

        if self.db.brave_starter_consumables_seeded:
            return
        for template_id, quantity in STARTER_CONSUMABLES:
            self.add_item_to_inventory(template_id, quantity)
        self.db.brave_starter_consumables_seeded = True

    def ensure_class_starter_items(self, force=False):
        """Seed light class-specific feature items without duplicating them forever."""

        class_key = self.db.brave_class or CHARACTER_CONTENT.starting_class
        current = self.db.brave_class_feature_items_class or ""
        if not force and current == class_key:
            return
        if current and current != class_key and self.can_customize_build():
            for template_id, quantity in CLASS_STARTER_ITEMS.get(current, ()):
                self.remove_item_from_inventory(template_id, quantity)
        if not current or current != class_key or force:
            for template_id, quantity in CLASS_STARTER_ITEMS.get(class_key, ()):
                if self.get_inventory_quantity(template_id) < quantity:
                    self.add_item_to_inventory(template_id, quantity - self.get_inventory_quantity(template_id), count_for_collection=False)
        self.db.brave_class_feature_items_class = class_key

    def ensure_ranger_companion(self):
        """Seed the default ranger companion when appropriate."""

        if self.db.brave_class != "ranger":
            return
        companions = [str(key).lower() for key in (self.db.brave_companions or [])]
        if DEFAULT_RANGER_COMPANION not in companions:
            companions.append(DEFAULT_RANGER_COMPANION)
            self.db.brave_companions = companions
        Character._ensure_companion_bond(self, DEFAULT_RANGER_COMPANION)
        if not self.db.brave_active_companion:
            self.db.brave_active_companion = DEFAULT_RANGER_COMPANION

    def _ensure_companion_bond(self, companion_key):
        """Ensure one companion has persisted bond progress state."""

        companion_key = str(companion_key or "").lower()
        if not companion_key:
            return {}
        bonds = dict(getattr(self.db, "brave_companion_bonds", None) or {})
        state = normalize_companion_bond_state(bonds.get(companion_key))
        bonds[companion_key] = {"xp": state["xp"]}
        self.db.brave_companion_bonds = bonds
        return state

    def get_companion_bond_state(self, companion_key):
        """Return normalized bond progression for one companion."""

        companion_key = str(companion_key or "").lower()
        if not companion_key:
            return normalize_companion_bond_state({})
        return Character._ensure_companion_bond(self, companion_key)

    def award_companion_bond_xp(self, companion_key, amount):
        """Award companion bond XP and report any tier-ups."""

        if self.db.brave_class != "ranger":
            return []
        companion_key = str(companion_key or "").lower()
        if not companion_key:
            return []
        previous = Character.get_companion_bond_state(self, companion_key)
        bonds = dict(getattr(self.db, "brave_companion_bonds", None) or {})
        bonds[companion_key] = {"xp": previous["xp"] + max(0, int(amount or 0))}
        self.db.brave_companion_bonds = bonds
        current = Character.get_companion_bond_state(self, companion_key)
        if current["level"] <= previous["level"]:
            return []
        companion_name = get_companion_name(companion_key)
        return [f"{companion_name} reaches Bond {current['level']} ({current['title']})."]

    def get_unlocked_companions(self):
        """Return unlocked ranger companion payloads."""

        unlocked = []
        for companion_key in (self.db.brave_companions or []):
            companion = get_companion(companion_key, self.get_companion_bond_state(companion_key))
            if not companion:
                continue
            payload = dict(companion)
            payload["key"] = str(companion_key).lower()
            unlocked.append(payload)
        return unlocked

    def get_active_companion(self):
        """Return the currently active ranger companion payload."""

        companion_key = str(self.db.brave_active_companion or "").lower()
        if not companion_key:
            return {}
        companion = get_companion(companion_key, self.get_companion_bond_state(companion_key))
        if not companion:
            return {}
        payload = dict(companion)
        payload["key"] = companion_key
        return payload

    def unlock_companion(self, companion_key):
        """Unlock and optionally activate a ranger companion."""

        if self.db.brave_class != "ranger":
            return False, "Only a Ranger can bond a battle companion."
        companion_key = str(companion_key or "").lower()
        companion = get_companion(companion_key)
        if not companion:
            return False, "That companion bond is unknown."
        companions = [str(key).lower() for key in (self.db.brave_companions or [])]
        if companion_key in companions:
            return False, f"You have already bonded with {companion.get('name', 'that companion')}."
        companions.append(companion_key)
        self.db.brave_companions = companions
        Character._ensure_companion_bond(self, companion_key)
        self.db.brave_active_companion = companion_key
        return True, f"{companion.get('name', 'A new companion')} answers your bond and joins your hunt."

    def set_active_companion(self, companion_key):
        """Set the active ranger companion."""

        if self.db.brave_class != "ranger":
            return False, "Only a Ranger can call an active companion."
        companion_key = str(companion_key or "").lower()
        companions = [str(key).lower() for key in (self.db.brave_companions or [])]
        if companion_key not in companions:
            return False, "You have not bonded with that companion."
        self.db.brave_active_companion = companion_key
        return True, f"{get_companion_name(companion_key)} takes point for the next hunt."

    def ensure_paladin_oath(self):
        """Seed the default Paladin oath when appropriate."""

        if self.db.brave_class != "paladin":
            return
        oaths = [str(key).lower() for key in (self.db.brave_paladin_oaths or [])]
        if DEFAULT_PALADIN_OATH not in oaths:
            oaths.append(DEFAULT_PALADIN_OATH)
            self.db.brave_paladin_oaths = oaths
        if not self.db.brave_active_oath:
            self.db.brave_active_oath = DEFAULT_PALADIN_OATH

    def get_unlocked_oaths(self):
        """Return unlocked Paladin oath payloads."""

        unlocked = []
        for oath_key in (self.db.brave_paladin_oaths or []):
            oath = get_oath(oath_key)
            if not oath:
                continue
            payload = dict(oath)
            payload["key"] = str(oath_key).lower()
            unlocked.append(payload)
        return unlocked

    def get_active_oath(self):
        """Return the currently active Paladin oath payload."""

        oath_key = str(self.db.brave_active_oath or "").lower()
        if not oath_key:
            return {}
        oath = get_oath(oath_key)
        if not oath:
            return {}
        payload = dict(oath)
        payload["key"] = oath_key
        return payload

    def unlock_oath(self, oath_key):
        """Unlock and activate a Paladin oath."""

        if self.db.brave_class != "paladin":
            return False, "Only a Paladin can swear that vow."
        oath_key = str(oath_key or "").lower()
        oath = get_oath(oath_key)
        if not oath:
            return False, "That oath is unknown."
        oaths = [str(key).lower() for key in (self.db.brave_paladin_oaths or [])]
        if oath_key in oaths:
            return False, f"You have already sworn {oath.get('name', 'that oath')}."
        oaths.append(oath_key)
        self.db.brave_paladin_oaths = oaths
        self.db.brave_active_oath = oath_key
        self.recalculate_stats()
        return True, f"You swear {oath.get('name', 'a new oath')} and take its vigil on yourself."

    def set_active_oath(self, oath_key):
        """Set the active Paladin oath."""

        if self.db.brave_class != "paladin":
            return False, "Only a Paladin keeps an active oath."
        oath_key = str(oath_key or "").lower()
        oaths = [str(key).lower() for key in (self.db.brave_paladin_oaths or [])]
        if oath_key not in oaths:
            return False, "You have not sworn that oath."
        self.db.brave_active_oath = oath_key
        self.recalculate_stats()
        return True, f"{get_oath_name(oath_key)} now guides your vigil."

    def get_rogue_theft_log(self):
        """Return authored Rogue theft records in acquisition order."""

        theft_log = dict(self.db.brave_rogue_theft_log or {})
        entries = []
        for entity_id, payload in theft_log.items():
            record = dict(payload or {})
            record.setdefault("entity_id", entity_id)
            entries.append(record)
        return entries

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

    def unlock_cooking_recipe(self, recipe_key):
        """Learn one authored cooking recipe."""

        recipe_key = str(recipe_key or "").lower()
        recipe = CONTENT.systems.cooking_recipes.get(recipe_key)
        if not recipe:
            return False, "That recipe is unknown."
        known = [str(key).lower() for key in (self.db.brave_known_cooking_recipes or [])]
        if recipe_key in known:
            return False, f"You already know how to cook {recipe.get('name', 'that recipe')}."
        known.append(recipe_key)
        self.db.brave_known_cooking_recipes = known
        return True, f"You learn the recipe for {recipe.get('name', 'that meal')}."

    def unlock_tinkering_recipe(self, recipe_key):
        """Learn one authored tinkering design."""

        recipe_key = str(recipe_key or "").lower()
        recipe = CONTENT.systems.tinkering_recipes.get(recipe_key)
        if not recipe:
            return False, "That design is unknown."
        known = [str(key).lower() for key in (self.db.brave_known_tinkering_recipes or [])]
        if recipe_key in known:
            return False, f"You already know the {recipe.get('name', 'that design')} pattern."
        known.append(recipe_key)
        self.db.brave_known_tinkering_recipes = known
        return True, f"You learn the design for {recipe.get('name', 'that pattern')}."

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

    def get_equippable_inventory(self, slot=None):
        """Return carried equipment entries, optionally filtered to one slot."""

        items = []
        class_key = getattr(getattr(self, "db", None), "brave_class", None)
        for entry in (self.db.brave_inventory or []):
            template_id = entry.get("template")
            quantity = max(0, int(entry.get("quantity", 0) or 0))
            template = ITEM_TEMPLATES.get(template_id)
            if quantity <= 0 or not template or template.get("kind") != "equipment":
                continue
            if not is_equipment_allowed_for_class(template_id, class_key):
                continue
            item_slot = template.get("slot")
            if slot and item_slot != slot:
                continue
            items.append(
                {
                    "template": template_id,
                    "name": template.get("name", template_id.replace("_", " ").title()),
                    "slot": item_slot,
                    "quantity": quantity,
                }
            )
        items.sort(key=lambda item: (item["name"].lower(), item["template"]))
        return items

    def add_item_to_inventory(self, template_id, quantity=1, *, count_for_collection=True):
        """Add a stackable loot item to the character inventory."""

        if quantity <= 0 or template_id not in ITEM_TEMPLATES:
            return

        inventory = list(self.db.brave_inventory or [])
        for entry in inventory:
            if entry["template"] == template_id:
                entry["quantity"] += quantity
                self.db.brave_inventory = inventory
                if count_for_collection:
                    advance_item_collection(self)
                return

        inventory.append({"template": template_id, "quantity": quantity})
        self.db.brave_inventory = inventory
        if count_for_collection:
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

    def equip_inventory_item(self, template_id, slot=None):
        """Equip one carried item into its matching slot, swapping if needed."""

        self.ensure_brave_character()
        template = ITEM_TEMPLATES.get(template_id)
        if not template or template.get("kind") != "equipment":
            return False, "That item cannot be equipped."

        target_slot = template.get("slot")
        if target_slot not in EQUIPMENT_SLOTS:
            return False, "That item does not have a valid equipment slot."
        if slot and slot != target_slot:
            return False, f"{template['name']} fits in {target_slot.replace('_', ' ').title()}."
        if self.get_inventory_quantity(template_id) <= 0:
            return False, f"You are not carrying {template['name']}."
        if not is_equipment_allowed_for_class(template_id, self.db.brave_class):
            allowed_text = format_allowed_class_summary(template_id)
            if allowed_text:
                return False, f"{template['name']} is outside your training. {allowed_text}."
            return False, f"{template['name']} is outside your training."

        equipment = dict(self.db.brave_equipment or {})
        current_template_id = equipment.get(target_slot)
        if current_template_id == template_id:
            return False, f"{template['name']} is already equipped."
        if not self.remove_item_from_inventory(template_id, 1):
            return False, f"You are not carrying {template['name']}."

        if current_template_id:
            self.add_item_to_inventory(current_template_id, 1, count_for_collection=False)

        equipment[target_slot] = template_id
        self.db.brave_equipment = equipment
        self.recalculate_stats()
        return True, {
            "slot": target_slot,
            "equipped": template_id,
            "replaced": current_template_id,
        }

    def unequip_slot(self, slot):
        """Move an equipped item back into inventory from one slot."""

        self.ensure_brave_character()
        if slot not in EQUIPMENT_SLOTS:
            return False, "That is not a valid equipment slot."

        equipment = dict(self.db.brave_equipment or {})
        template_id = equipment.get(slot)
        if not template_id:
            return False, f"Nothing is equipped in {slot.replace('_', ' ').title()}."

        equipment[slot] = None
        self.db.brave_equipment = equipment
        self.add_item_to_inventory(template_id, 1, count_for_collection=False)
        self.recalculate_stats()
        return True, {
            "slot": slot,
            "unequipped": template_id,
        }
