"""Curated browser theme metadata for Brave."""


def _normalize_theme_query(value):
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


THEMES = [
    {
        "key": "hearth",
        "name": "Brave Classic",
        "icon": "local_fire_department",
        "summary": "The default Brave look: warm, lantern-lit, and frontier-focused.",
        "font_key": "redhat",
        "font_name": "Red Hat Mono",
        "font_scale": "1.0",
        "notes": [
            "The intended default presentation for Brave.",
            "Best match for the game's tone, world reactivity, and overall feel.",
        ],
        "aliases": ["default", "brave", "classic", "standard", "house", "lantern", "hearthfire"],
    },
]

THEME_BY_KEY = {theme["key"]: theme for theme in THEMES}
THEME_ALIASES = {
    theme["key"]: {
        _normalize_theme_query(theme["key"]),
        _normalize_theme_query(theme["name"]),
        *[_normalize_theme_query(alias) for alias in theme.get("aliases", [])],
    }
    for theme in THEMES
}


def normalize_theme_key(value, default="hearth"):
    normalized = _normalize_theme_query(value)
    if not normalized:
        return default
    for key, aliases in THEME_ALIASES.items():
        if normalized in aliases:
            return key
    return default
