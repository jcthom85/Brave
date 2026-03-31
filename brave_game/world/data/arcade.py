"""Arcade game definitions shared by all cabinet instances."""

ARCADE_GAMES = {
    "maze_runner": {
        "name": "Maze Runner",
        "aliases": ["maze", "runner", "maze runner"],
        "summary": "An all-out ASCII maze chase with four ghosts, power pellets, fruit spawns, and escalating rounds.",
        "instructions": [
            "Use arrow keys or WASD to move.",
            "On touch screens, use the cabinet D-pad at the bottom of the screen.",
            "Power pellets let you turn the ghosts and chain bigger scores.",
            "Fruit spawns mid-round and levels get faster as the board resets.",
            "You get multiple lives. Press P to pause and Q if you want to leave early.",
        ],
        "score_summary": "Dots, power pellets, frightened ghost chains, fruit, and round clears all build score.",
    },
}


def get_arcade_game(game_key):
    """Return one arcade game definition by key."""

    return ARCADE_GAMES.get(game_key)
