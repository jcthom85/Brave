"""Shared Brave gender helpers."""

VALID_BRAVE_GENDERS = ("male", "female", "nonbinary")
DEFAULT_BRAVE_GENDER = "nonbinary"

BRAVE_GENDER_LABELS = {
    "male": "Male",
    "female": "Female",
    "nonbinary": "Non-binary",
}

BRAVE_GENDER_ALIASES = {
    "male": "male",
    "man": "male",
    "m": "male",
    "female": "female",
    "woman": "female",
    "f": "female",
    "nonbinary": "nonbinary",
    "non-binary": "nonbinary",
    "non binary": "nonbinary",
    "nb": "nonbinary",
    "they": "nonbinary",
}

BRAVE_GENDER_PRONOUNS = {
    "male": {
        "subject": "he",
        "object": "him",
        "possessive_adjective": "his",
        "possessive_pronoun": "his",
        "reflexive": "himself",
    },
    "female": {
        "subject": "she",
        "object": "her",
        "possessive_adjective": "her",
        "possessive_pronoun": "hers",
        "reflexive": "herself",
    },
    "nonbinary": {
        "subject": "they",
        "object": "them",
        "possessive_adjective": "their",
        "possessive_pronoun": "theirs",
        "reflexive": "themself",
    },
}


def normalize_brave_gender(value, *, default=None):
    """Return the canonical Brave gender key or a default."""

    token = str(value or "").strip().lower()
    if not token:
        return default
    token = BRAVE_GENDER_ALIASES.get(token, token.replace("_", "").replace("-", ""))
    if token in VALID_BRAVE_GENDERS:
        return token
    return default


def get_brave_gender_label(value, *, default="Not set"):
    """Return the display label for one Brave gender key."""

    normalized = normalize_brave_gender(value)
    if not normalized:
        return default
    return BRAVE_GENDER_LABELS.get(normalized, default)


def resolve_brave_gender(value, *, default=DEFAULT_BRAVE_GENDER):
    """Resolve one Brave gender key from raw values, mappings, or objects."""

    normalized = normalize_brave_gender(value)
    if normalized:
        return normalized

    if value is None:
        return default

    if isinstance(value, dict):
        normalized = normalize_brave_gender(
            value.get("brave_gender") or value.get("gender"),
            default=default,
        )
        return normalized or default

    db = getattr(value, "db", None)
    normalized = normalize_brave_gender(
        getattr(db, "brave_gender", None) or getattr(db, "gender", None),
        default=default,
    )
    if normalized:
        return normalized
    return default


def get_brave_gender_pronouns(value, *, default=DEFAULT_BRAVE_GENDER):
    """Return the pronoun bundle for one Brave gender source."""

    gender = resolve_brave_gender(value, default=default)
    return dict(BRAVE_GENDER_PRONOUNS.get(gender, BRAVE_GENDER_PRONOUNS[DEFAULT_BRAVE_GENDER]))


def get_brave_pronoun(value, form, *, default=DEFAULT_BRAVE_GENDER):
    """Return one pronoun form for a Brave gender source."""

    return get_brave_gender_pronouns(value, default=default).get(form, "")
