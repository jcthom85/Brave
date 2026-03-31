"""Data definitions for Brave's first town activities."""

FISHING_SPOTS = {
    "brambleford_hobbyists_wharf": {
        "name": "Hobbyist's Wharf",
        "cast_text": (
            "You cast a line into the Bramble River and settle in to watch the surface."
        ),
        "bite_delay": (3, 6),
        "reaction_window": 6,
        "fish": [
            {
                "item": "bramble_perch",
                "chance": 38,
                "weight": (1.1, 3.6),
                "hook_chance": 0.9,
            },
            {
                "item": "lantern_carp",
                "chance": 26,
                "weight": (2.5, 6.8),
                "hook_chance": 0.82,
            },
            {
                "item": "mudsnout_catfish",
                "chance": 18,
                "weight": (3.2, 8.4),
                "hook_chance": 0.78,
            },
            {
                "item": "silver_eel",
                "chance": 12,
                "weight": (1.8, 5.2),
                "hook_chance": 0.7,
            },
            {
                "item": "dawnscale_trout",
                "chance": 6,
                "weight": (4.4, 9.8),
                "hook_chance": 0.6,
            },
        ],
    }
}

COOKING_RECIPES = {
    "crisped_perch_plate": {
        "name": "Crisped Perch Plate",
        "result": "crisped_perch_plate",
        "ingredients": {"bramble_perch": 2},
        "summary": "A simple, filling plate that makes long walks and harder swings feel easier.",
    },
    "riverlight_chowder": {
        "name": "Riverlight Chowder",
        "result": "riverlight_chowder",
        "ingredients": {"lantern_carp": 1, "silver_eel": 1},
        "summary": "A rich chowder that steadies the nerves and wakes up the mind.",
    },
    "wharfside_skewers": {
        "name": "Wharfside Skewers",
        "result": "wharfside_skewers",
        "ingredients": {"bramble_perch": 1, "mudsnout_catfish": 1},
        "summary": "Smoky skewers that reward quick hands and lighter feet.",
    },
    "innkeepers_fishpie": {
        "name": "Innkeeper's Fish Pie",
        "result": "innkeepers_fishpie",
        "ingredients": {"lantern_carp": 1, "mudsnout_catfish": 1},
        "summary": "A sturdy inn pie that leaves you feeling well-patched and harder to rattle.",
    },
}

COZY_BONUS = {
    "max_hp": 6,
    "max_mana": 6,
    "max_stamina": 6,
}


def format_ingredient_list(ingredients, item_lookup):
    """Return a readable ingredient summary."""

    parts = []
    for template_id, quantity in ingredients.items():
        item_name = item_lookup[template_id]["name"]
        parts.append(f"{item_name} x{quantity}")
    return ", ".join(parts)
