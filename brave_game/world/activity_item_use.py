"""Item-use execution helpers for Brave activities and combat."""

from collections.abc import Mapping
from random import randint

from world.activities import (
    CHARACTER_CONTENT,
    ITEM_TEMPLATES,
    format_bonus_summary,
    get_item_use_profile,
    room_supports_activity,
)


def _consume_item_by_template(character, template_id, *, context="explore", cozy=None, target=None, encounter=None):
    """Consume an item template and apply its current use profile."""

    item = ITEM_TEMPLATES.get(template_id)
    use = get_item_use_profile(item, context=context)
    if not item or not use:
        return False, "That item can't be used that way right now.", None

    effect_type = use.get("effect_type")
    restore = dict(use.get("restore", {}))
    buffs = dict(use.get("buffs", {}))
    cleanse_result = None
    guard_amount = 0
    restore_total = 0
    learned_ability_name = None
    target_type = use.get("target", "self")
    if target_type == "enemy":
        resolved_target = target if isinstance(target, Mapping) else None
    elif target_type in {"ally", "self"}:
        resolved_target = target or character
    else:
        resolved_target = target

    if cozy is None:
        cozy = False
        if effect_type == "meal" and room_supports_activity(character.location, "cooking") and character.db.brave_party_id:
            from world.party import get_present_party_members

            cozy = len(get_present_party_members(character)) >= 2

    if effect_type == "damage" and (not encounter or not isinstance(resolved_target, Mapping)):
        return False, "That item can't be used meaningfully here right now.", None

    if effect_type == "teach_spell":
        required_class = str(use.get("required_class") or "mage").lower()
        if str(getattr(getattr(character, "db", None), "brave_class", "") or "").lower() != required_class:
            return False, f"Only a {required_class.title()} can make sense of that spellbook.", None
        ability_key = CHARACTER_CONTENT.ability_key(use.get("learn_ability"))
        ability = CHARACTER_CONTENT.ability_library.get(ability_key) or {}
        if not ability:
            return False, "The spellbook's notation is incomplete.", None
        learn = getattr(character, "learn_ability", None)
        if callable(learn):
            ok, learn_message = learn(ability_key)
            if not ok:
                return False, learn_message, None
        else:
            learned = [str(key).lower() for key in (getattr(getattr(character, "db", None), "brave_learned_abilities", None) or [])]
            if ability_key in learned:
                return False, f"You already know {ability.get('name', 'that technique')}.", None
            learned.append(ability_key)
            character.db.brave_learned_abilities = learned
        learned_ability_name = ability.get("name", ability_key.replace("_", " ").title())

    if effect_type == "unlock_companion":
        required_class = str(use.get("required_class") or "ranger").lower()
        if str(getattr(getattr(character, "db", None), "brave_class", "") or "").lower() != required_class:
            return False, f"Only a {required_class.title()} can forge that companion bond.", None
        companion_key = str(use.get("unlock_companion") or "").lower()
        unlock = getattr(character, "unlock_companion", None)
        if callable(unlock):
            ok, unlock_message = unlock(companion_key)
            if not ok:
                return False, unlock_message, None
            learned_ability_name = unlock_message
        else:
            return False, "That bond cannot be formed right now.", None

    if effect_type == "unlock_oath":
        required_class = str(use.get("required_class") or "paladin").lower()
        if str(getattr(getattr(character, "db", None), "brave_class", "") or "").lower() != required_class:
            return False, f"Only a {required_class.title()} can swear that oath.", None
        oath_key = str(use.get("unlock_oath") or "").lower()
        unlock = getattr(character, "unlock_oath", None)
        if callable(unlock):
            ok, unlock_message = unlock(oath_key)
            if not ok:
                return False, unlock_message, None
            learned_ability_name = unlock_message
        else:
            return False, "That vow cannot be taken right now.", None

    if effect_type == "unlock_recipe":
        recipe_domain = str(use.get("recipe_domain") or "cooking").lower()
        recipe_key = str(use.get("unlock_recipe") or "").lower()
        if recipe_domain == "cooking":
            unlock = getattr(character, "unlock_cooking_recipe", None)
        elif recipe_domain == "tinkering":
            unlock = getattr(character, "unlock_tinkering_recipe", None)
        else:
            unlock = None
        if callable(unlock):
            ok, unlock_message = unlock(recipe_key)
            if not ok:
                return False, unlock_message, None
            learned_ability_name = unlock_message
        else:
            return False, "That pattern cannot be learned right now.", None

    if target_type == "self" and resolved_target != character:
        return False, "That item can only be used on yourself.", None

    ensure_target = getattr(resolved_target, "ensure_brave_character", None)
    if callable(ensure_target):
        ensure_target()
    if hasattr(resolved_target, "location"):
        if resolved_target != character and getattr(resolved_target, "location", None) != getattr(character, "location", None):
            return False, "That target is not here with you.", None

    if effect_type == "cleanse":
        if not encounter or not hasattr(resolved_target, "db"):
            return False, "That item needs an ally in combat to be useful.", None
        cleanse_result = encounter._clear_one_harmful_effect(resolved_target)
        if not cleanse_result:
            target_name = getattr(resolved_target, "key", character.key)
            return False, f"{target_name} has no harmful effect to clear.", None

    if effect_type == "guard":
        if not encounter or not hasattr(resolved_target, "db"):
            return False, "That item needs an ally in combat to be useful.", None
        guard_amount = max(1, int(use.get("guard", 0) or 0))

    if not character.remove_item_from_inventory(template_id, 1):
        return False, "You can't find that item in your pack anymore.", None

    if effect_type == "meal":
        character.apply_meal_buff(template_id, cozy=bool(cozy))

    if effect_type in {"meal", "restore", "cleanse"} and restore:
        target_character = resolved_target if hasattr(resolved_target, "db") else character
        derived = target_character.db.brave_derived_stats or {}
        resources = dict(target_character.db.brave_resources or {})
        for pool in ("hp", "mana", "stamina"):
            cap = derived.get(f"max_{pool}", 0)
            before = resources.get(pool, 0)
            resources[pool] = min(cap, resources.get(pool, 0) + restore.get(pool, 0))
            restore_total += max(0, resources[pool] - before)
        target_character.db.brave_resources = resources

    if effect_type == "guard":
        state = encounter._get_participant_state(resolved_target)
        state["guard"] = max(int(state.get("guard", 0) or 0), guard_amount)
        encounter._save_participant_state(resolved_target, state)

    if effect_type == "damage":
        damage_spec = dict(use.get("damage", {}))
        base = int(damage_spec.get("base", 0) or 0)
        variance = max(0, int(damage_spec.get("variance", 0) or 0))
        damage = max(1, base + randint(0, variance))
        encounter._damage_enemy(character, resolved_target, damage, extra_text=use.get("extra_text", ""))

    verb = use.get("verb", "use")
    active_bonuses = character.get_active_meal_bonuses() if effect_type == "meal" else buffs
    bonus_text = format_bonus_summary({"bonuses": active_bonuses})
    if verb == "eat":
        player_message = f"You eat the |w{item['name']}|n and feel steadier."
        public_message = f"{character.key} snatches a moment to eat {item['name']}."
    elif verb == "drink":
        player_message = f"You drink the |w{item['name']}|n."
        public_message = f"{character.key} downs {item['name']}."
    elif verb == "apply":
        target_name = getattr(resolved_target, "key", character.key)
        if resolved_target and getattr(resolved_target, "id", None) != character.id:
            player_message = f"You apply the |w{item['name']}|n to {target_name}."
            public_message = f"{character.key} applies {item['name']} to {target_name}."
        else:
            player_message = f"You apply the |w{item['name']}|n."
            public_message = f"{character.key} applies {item['name']}."
    elif verb == "throw":
        target_name = resolved_target.get("key", "the target") if isinstance(resolved_target, Mapping) else "the target"
        player_message = f"You hurl the |w{item['name']}|n at {target_name}."
        public_message = None
    elif verb == "cast":
        target_name = getattr(resolved_target, "key", character.key)
        if resolved_target and getattr(resolved_target, "id", None) != character.id:
            player_message = f"You cast the |w{item['name']}|n over {target_name}."
            public_message = f"{character.key} casts {item['name']} over {target_name}."
        else:
            player_message = f"You cast the |w{item['name']}|n over yourself."
            public_message = f"{character.key} casts {item['name']} over themselves."
    else:
        player_message = f"You use the |w{item['name']}|n."
        public_message = f"{character.key} uses {item['name']}."
    if bonus_text:
        player_message += f" Bonus: {bonus_text}."
    if effect_type in {"unlock_companion", "unlock_oath"}:
        player_message += " " + learned_ability_name
    elif learned_ability_name:
        player_message += f" You commit |w{learned_ability_name}|n to memory."
    if cleanse_result:
        player_message += f" It clears {cleanse_result}."
    if guard_amount:
        player_message += f" Guard rises by {guard_amount}."
    if cozy:
        player_message += " Sharing a warm meal in company leaves you with a lingering |wCozy|n feeling."

    return True, player_message, {
        "template_id": template_id,
        "item": item,
        "use": use,
        "public_message": public_message,
        "cleanse_result": cleanse_result,
        "guard_amount": guard_amount,
        "learned_ability_name": learned_ability_name,
        "restore_total": restore_total,
    }
