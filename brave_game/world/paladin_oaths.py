"""Authored Paladin oath definitions and helpers."""

DEFAULT_PALADIN_OATH = "oath_of_the_bell"

PALADIN_OATHS = {
    "oath_of_the_bell": {
        "name": "Oath Of The Bell",
        "summary": "A warding vow sworn to hold the line when the town rings for help, favoring guard, armor, and refusal to yield.",
        "lines": [
            "The bell calls you to stand between danger and the people who cannot outrun it.",
            "This oath strengthens the Dawn Bell blessing toward protection, threat, and staying power.",
        ],
        "blessing_bonuses": {"max_hp": 6, "armor": 1, "threat": 2},
    },
    "oath_of_mercy": {
        "name": "Oath Of Mercy",
        "summary": "A compassionate vow that turns sacred defense toward relief, triage, and keeping battered allies on their feet.",
        "lines": [
            "Mercy does not soften your resolve; it decides who must still be standing when the dust settles.",
            "This oath bends the Dawn Bell blessing toward healing power, mana, and steadier holy support.",
        ],
        "blessing_bonuses": {"healing_power": 4, "max_mana": 8, "spell_power": 1},
    },
    "oath_of_cinders": {
        "name": "Oath Of Cinders",
        "summary": "A harsher vigil sworn against darkness and ruin, channeling sacred force into punishment, pursuit, and avenging pressure.",
        "lines": [
            "You swear that what threatens the helpless will leave marked, broken, or burning for the attempt.",
            "This oath sharpens the Dawn Bell blessing toward attack, stamina, and cleaner retaliation.",
        ],
        "blessing_bonuses": {"attack_power": 2, "max_stamina": 6, "accuracy": 2},
    },
}


def get_oath(oath_key):
    """Return authored payload for one Paladin oath."""

    return dict(PALADIN_OATHS.get(str(oath_key or "").lower(), {}))


def get_oath_name(oath_key):
    """Return display name for one oath key."""

    oath = get_oath(oath_key)
    return oath.get("name", str(oath_key or "").replace("_", " ").title())
