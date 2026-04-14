"""Helpers for world resonance, portal listings, and ability skinning."""

from world.content import get_content_registry

CONTENT = get_content_registry()
SYSTEMS_CONTENT = CONTENT.systems
PORTALS = SYSTEMS_CONTENT.portals
PORTAL_STATUS_LABELS = SYSTEMS_CONTENT.portal_status_labels


def _normalize_token(value):
    return "".join(char for char in (value or "").lower() if char.isalnum())


RESONANCE_PROFILES = {
    "fantasy": {
        "label": "Fantasy Resonance",
        "world_label": "Home World",
        "color_primary": "|y",    # Yellow highlight
        "color_secondary": "|w",  # White
        "color_border": "|x",     # Gutter
        "primary_labels": {
            "strength": "Strength",
            "agility": "Agility",
            "intellect": "Intellect",
            "spirit": "Spirit",
            "vitality": "Vitality",
        },
        "derived_labels": {
            "max_hp": "HP",
            "max_mana": "Mana",
            "max_stamina": "Stamina",
            "attack_power": "Attack",
            "spell_power": "Spell",
            "armor": "Armor",
            "accuracy": "Accuracy",
            "precision": "Precision",
            "crit_chance": "Crit",
            "dodge": "Dodge",
            "threat": "Threat",
        },
        "resource_labels": {
            "hp": "HP",
            "mana": "Mana",
            "stamina": "Stamina",
        },
        "ability_names": {},
    },
    "tech": {
        "label": "Tech Resonance",
        "world_label": "Guest World",
        "color_primary": "|c",    # Cyan highlight
        "color_secondary": "|C",  # Light cyan text
        "color_border": "|x",
        "primary_labels": {
            "strength": "Physical Might",
            "agility": "Reflexes",
            "intellect": "Tech Skill",
            "spirit": "Energy",
            "vitality": "Durability",
        },
        "derived_labels": {
            "max_hp": "Integrity",
            "max_mana": "Energy",
            "max_stamina": "Drive",
            "attack_power": "Output",
            "spell_power": "Tech",
            "armor": "Plating",
            "accuracy": "Targeting",
            "precision": "Lock",
            "crit_chance": "Crit",
            "dodge": "Evasion",
            "threat": "Signal",
        },
        "resource_labels": {
            "hp": "Integrity",
            "mana": "Energy",
            "stamina": "Drive",
        },
        "ability_names": {
            "Strike": "Impact Driver",
            "Defend": "Brace Field",
            "Quick Shot": "Pulse Shot",
            "Mark Prey": "Target Lock",
            "Heal": "Repair Pulse",
            "Smite": "Arc Lash",
            "Firebolt": "Plasma Bolt",
            "Frost Bind": "Stasis Net",
            "Stab": "Shiv Drive",
            "Feint": "False Signal",
            "Holy Strike": "Breach Strike",
            "Guarding Aura": "Guard Field",
            "Thorn Lash": "Cable Lash",
            "Minor Mend": "Patch Bloom",
        },
    },
    "martial": {
        "label": "Ki Resonance",
        "world_label": "Guest World",
        "color_primary": "|r",    # Red highlight
        "color_secondary": "|R",  # Muted red text
        "color_border": "|x",
        "primary_labels": {
            "strength": "Martial Power",
            "agility": "Speed",
            "intellect": "Focus",
            "spirit": "Ki",
            "vitality": "Endurance",
        },
        "derived_labels": {
            "max_hp": "Endurance",
            "max_mana": "Ki",
            "max_stamina": "Drive",
            "attack_power": "Pressure",
            "spell_power": "Ki Power",
            "armor": "Guard",
            "accuracy": "Timing",
            "precision": "Form",
            "crit_chance": "Break",
            "dodge": "Step",
            "threat": "Presence",
        },
        "resource_labels": {
            "hp": "Endurance",
            "mana": "Ki",
            "stamina": "Drive",
        },
        "ability_names": {},
    },
    "sandbox": {
        "label": "Draft Resonance",
        "world_label": "Builder Space",
        "color_primary": "|w",
        "color_secondary": "|x",
        "color_border": "|x",
        "primary_labels": {
            "strength": "Strength",
            "agility": "Agility",
            "intellect": "Intellect",
            "spirit": "Spirit",
            "vitality": "Vitality",
        },
        "derived_labels": {
            "max_hp": "HP",
            "max_mana": "Mana",
            "max_stamina": "Stamina",
            "attack_power": "Attack",
            "spell_power": "Spell",
            "armor": "Armor",
            "accuracy": "Accuracy",
            "precision": "Precision",
            "crit_chance": "Crit",
            "dodge": "Dodge",
            "threat": "Threat",
        },
        "resource_labels": {
            "hp": "HP",
            "mana": "Mana",
            "stamina": "Stamina",
        },
        "ability_names": {},
    },
}


def _get_room(source):
    if not source:
        return None
    if hasattr(source, "db") and getattr(source.db, "brave_resonance", None) is not None:
        return source
    return getattr(source, "location", None)


def get_resonance_key(source):
    """Return the active resonance key for a room or character."""

    room = _get_room(source)
    if not room:
        return "fantasy"
    return getattr(room.db, "brave_resonance", None) or "fantasy"


def get_resonance_profile(source):
    """Return the resonance profile for the current context."""

    return RESONANCE_PROFILES.get(get_resonance_key(source), RESONANCE_PROFILES["fantasy"])


def get_resonance_label(source):
    """Return the current resonance label."""

    return get_resonance_profile(source)["label"]


def get_world_label(source):
    """Return the current world type label."""

    return get_resonance_profile(source)["world_label"]


def get_stat_label(key, source):
    """Return a resonance-aware stat label."""

    profile = get_resonance_profile(source)
    return profile["primary_labels"].get(
        key, profile["derived_labels"].get(key, key.replace("_", " ").title())
    )


def get_resource_label(key, source):
    """Return a resonance-aware resource label."""

    profile = get_resonance_profile(source)
    return profile["resource_labels"].get(key, key.replace("_", " ").title())


def get_ability_display_name(ability_name, source):
    """Return the display name for an ability in the current resonance."""

    profile = get_resonance_profile(source)
    return profile["ability_names"].get(ability_name, ability_name)


def format_ability_display(ability_name, source):
    """Return a readable display string for an ability."""

    display_name = get_ability_display_name(ability_name, source)
    if display_name == ability_name:
        return ability_name
    return f"{display_name} [{ability_name}]"


def resolve_ability_query(character, raw_ability):
    """Resolve fantasy or resonance-skinned ability names to canonical keys."""

    query = _normalize_token(raw_ability)
    if not query:
        return None

    exact = {}
    partial = {}
    for ability_name in character.get_unlocked_abilities():
        canonical_key = _normalize_token(ability_name)
        aliases = {
            canonical_key,
            _normalize_token(ability_name),
            _normalize_token(get_ability_display_name(ability_name, character)),
        }
        if query in aliases:
            exact[canonical_key] = ability_name
        for alias in aliases:
            if query and query in alias:
                partial[canonical_key] = ability_name

    if len(exact) == 1:
        return next(iter(exact))
    if len(exact) > 1:
        return list(exact)
    if len(partial) == 1:
        return next(iter(partial))
    if len(partial) > 1:
        return list(partial)
    return None


def format_portal_list():
    """Return a readable summary of current Nexus gates."""

    lines = ["|wNexus Gates|n"]
    for portal_key, portal in PORTALS.items():
        status_label = PORTAL_STATUS_LABELS.get(portal["status"], portal["status"].title())
        resonance_label = RESONANCE_PROFILES.get(portal["resonance"], RESONANCE_PROFILES["fantasy"])[
            "label"
        ]
        lines.append(f"  {portal['name']} [{status_label}] - {resonance_label}")
        lines.append(f"    {portal['summary']}")
        if portal.get("travel_hint"):
            lines.append(f"    Enter via: {portal['travel_hint']}")
    return "\n".join(lines)


def format_portal_plaque_text():
    """Return the readable plaque text for the Nexus Gate."""

    lines = [
        "A brass plate is set into the ring dais, each gate name etched beside a narrow groove of colored glass.",
        "",
        "Stable gates answer the ring. Dormant gates need more work. Sealed gates are not yet safe to bridge.",
        "",
    ]
    for portal in PORTALS.values():
        status_label = PORTAL_STATUS_LABELS.get(portal["status"], portal["status"].title())
        resonance_label = RESONANCE_PROFILES.get(portal["resonance"], RESONANCE_PROFILES["fantasy"])[
            "label"
        ]
        lines.append(f"- {portal['name']}: {status_label} / {resonance_label}")
    return "\n".join(lines)
