"""Race perk helpers for Brave."""

from world.content import get_content_registry


CONTENT = get_content_registry()
CHARACTER_CONTENT = CONTENT.characters


def get_race_data(character=None, race_key=None):
    """Return the authored race definition for a character or key."""

    resolved_key = race_key
    if character is not None:
        resolved_key = getattr(getattr(character, "db", None), "brave_race", None)
    return dict(CHARACTER_CONTENT.races.get(str(resolved_key or "").strip().lower(), {}) or {})


def get_race_perk_effects(character=None, race_key=None):
    """Return authored race perk effects."""

    return dict(get_race_data(character=character, race_key=race_key).get("perk_effects", {}) or {})


def get_race_perk_effect(character=None, key=None, default=0, race_key=None):
    """Return one scalar race perk effect value."""

    effects = get_race_perk_effects(character=character, race_key=race_key)
    return effects.get(key, default)


def adjust_effect_turns(character, effect_name, turns):
    """Return effect turns after race perk mitigation."""

    reduction = int(get_race_perk_effect(character, f"{effect_name}_turn_reduction", 0) or 0)
    reduction += int(get_race_perk_effect(character, "harmful_effect_turn_reduction", 0) or 0)
    return max(0, int(turns or 0) - reduction)


def adjust_effect_damage(character, effect_name, damage):
    """Return effect damage after race perk mitigation."""

    reduction = int(get_race_perk_effect(character, f"{effect_name}_damage_reduction", 0) or 0)
    return max(0, int(damage or 0) - reduction)


def adjust_effect_penalty(character, effect_name, penalty_name, value):
    """Return effect penalty magnitude after race perk mitigation."""

    reduction = int(get_race_perk_effect(character, f"{effect_name}_{penalty_name}_reduction", 0) or 0)
    reduction += int(get_race_perk_effect(character, f"{penalty_name}_reduction", 0) or 0)
    return max(0, int(value or 0) - reduction)


def get_atb_fill_rate_bonus(character):
    """Return ATB fill-rate bonus from race perks."""

    return int(get_race_perk_effect(character, "atb_fill_rate", 0) or 0)


def get_wounded_damage_bonus(character):
    """Return bonus damage granted while wounded."""

    effects = get_race_perk_effects(character=character)
    bonus = int(effects.get("wounded_damage_bonus", 0) or 0)
    return bonus if is_wounded(character) else 0


def get_wounded_atb_fill_rate_bonus(character):
    """Return bonus ATB fill-rate granted while wounded."""

    effects = get_race_perk_effects(character=character)
    bonus = int(effects.get("wounded_atb_fill_rate", 0) or 0)
    return bonus if is_wounded(character) else 0


def is_wounded(character):
    """Return whether the character is below their perk-defined wounded threshold."""

    effects = get_race_perk_effects(character=character)
    resources = dict(getattr(getattr(character, "db", None), "brave_resources", {}) or {})
    derived = dict(getattr(getattr(character, "db", None), "brave_derived_stats", {}) or {})
    current_hp = int(resources.get("hp", 0) or 0)
    max_hp = max(1, int(derived.get("max_hp", 1) or 1))
    threshold = float(effects.get("wounded_threshold", 0.5) or 0.5)
    return current_hp <= int(max_hp * threshold)


def get_flee_chance_bonus(character):
    """Return flee chance bonus from race perks."""

    return int(get_race_perk_effect(character, "flee_chance", 0) or 0)


def get_interrupt_recovery_bonus(character):
    """Return extra recovery ticks applied after an interrupt."""

    return int(get_race_perk_effect(character, "interrupt_recovery_ticks", 0) or 0)


def get_incoming_damage_reduction(character):
    """Return flat incoming damage reduction from race perks."""

    return int(get_race_perk_effect(character, "incoming_damage_reduction", 0) or 0)
