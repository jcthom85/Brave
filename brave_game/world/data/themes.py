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
    {
        "key": "signalglass",
        "name": "Signalglass",
        "icon": "terminal",
        "summary": "A sharp, high-contrast terminal theme.",
        "font_key": "sharetech",
        "font_name": "Share Tech Mono",
        "font_scale": "1.0",
        "notes": [
            "The sternest MUD lens in the set.",
            "Built for focused text-heavy play.",
        ],
        "aliases": ["crt", "sharp", "green", "phosphor", "glass", "signal"],
    },
    {
        "key": "terminal",
        "name": "Bare Terminal",
        "icon": "computer",
        "summary": "A stripped-down browser MUD presentation.",
        "font_key": "dejavu",
        "font_name": "DejaVu Sans Mono",
        "font_scale": "1.0",
        "notes": [
            "Keeps the current layout but strips the app chrome away.",
            "Best fit if you want Brave to read like a true browser MUD.",
        ],
        "aliases": ["mud", "bare", "ghost", "plain", "textonly", "tty"],
    },
    {
        "key": "campfire",
        "name": "Campfire CRT",
        "icon": "tv",
        "summary": "A softer retro terminal with a cozy CRT feel.",
        "font_key": "vt323",
        "font_name": "VT323 Pixel",
        "font_scale": "1.1",
        "notes": [
            "The most nostalgic theme in the set.",
            "Feels like an old family computer instead of a hard terminal.",
        ],
        "aliases": ["soft", "amber", "retro", "vintage", "cozy"],
    },
    {
        "key": "journal",
        "name": "Field Journal",
        "icon": "menu_book",
        "summary": "A calm paper-and-ink reading theme.",
        "font_key": "anonymous",
        "font_name": "Anonymous Pro",
        "font_scale": "1.0",
        "notes": [
            "Best for readables, dialogue, and a more authored adventure feel.",
            "The calmest and most bookish presentation.",
        ],
        "aliases": ["paper", "ledger", "infocom", "book", "literary", "cream"],
    },
    {
        "key": "atlas",
        "name": "Atlas Slate",
        "icon": "dashboard",
        "summary": "A clean, modern, tactical text theme.",
        "font_key": "space",
        "font_name": "Space Mono",
        "font_scale": "1.0",
        "notes": [
            "Most clarity-first and contemporary.",
            "Feels precise without turning Brave into a generic app.",
        ],
        "aliases": ["slate", "modern", "clean", "atlas", "minimal"],
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
