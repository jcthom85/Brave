"""Light race-specific world interaction hooks for Brave."""

ELF_READ_INSIGHTS = {
    "dawn_bell": "To elven senses the bronze carries a second note under the first, as if old vows are still ringing where no hand can touch them.",
    "nexus_gate_plaque": "The script reads like more than language for a moment, closer to a set of routes waiting to be remembered than letters waiting to be sounded out.",
    "star_lens": "The lens etchings resolve into disciplined old sky-work, the sort of pattern an elf recognizes as intent rather than decoration.",
    "boglight_lantern": "There is structure in the wrong light, not chaos; whatever answers from the glass learned to mimic guidance on purpose.",
    "weir_keepers_plaque": "The old civic engraving still hums with the shape of ordered signal-work, even through rust, water, and whatever has gone wrong since.",
}


def _race_key(character):
    return str(getattr(getattr(character, "db", None), "brave_race", "") or "").lower()


def get_shift_sales_bonus(character):
    """Return extra merchant-bonus sales from race identity."""

    return 1 if _race_key(character) == "human" else 0


def get_forge_silver_discount(character):
    """Return any race-based forge silver discount."""

    return 2 if _race_key(character) == "dwarf" else 0


def get_extra_read_insight(character, entity_id):
    """Return one race-specific read insight line when available."""

    if _race_key(character) != "elf":
        return ""
    return ELF_READ_INSIGHTS.get(str(entity_id or "").lower(), "")


def adjust_fishing_weight(character, weight):
    """Return adjusted fishing catch weight for race identity."""

    if _race_key(character) != "mosskin":
        return weight
    return round(weight + 0.3, 1)


def get_fishing_suffix(character):
    """Return an extra fishing result line when race identity applies."""

    if _race_key(character) != "mosskin":
        return ""
    return " Fen-born patience helps you read the pull before it slips away."


def get_chapel_bonuses(character):
    """Return race-based Dawn Bell blessing adjustments."""

    if _race_key(character) != "ashborn":
        return {}
    return {"attack_power": 1, "max_stamina": 4}


def get_chapel_rite_line(character):
    """Return extra Dawn Bell rite flavor for race identity."""

    if _race_key(character) != "ashborn":
        return ""
    return "The bell answers the cinder in your blood with a harder, hotter steadiness."
