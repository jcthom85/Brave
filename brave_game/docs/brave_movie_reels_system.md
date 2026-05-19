# Brave Design Doc: Collectible Movie Reels

## Objective
The Frontier Picture House in Brambleford provides an atmospheric side-activity where players can "watch" Great Frontier movies (audio-driven narrative scenes). To integrate this into the core game loop, movies must be discovered as "Movie Reels" throughout the world.

## The Repair Quest
Initially, the Frontier Picture House is inaccessible. The projector is broken.
- **Quest:** *Repair the Picture House*
- **Objective:** Find the **Brass Focus Gear** (located in the Lower Lanternworks) and return it to Joss Veller.
- **Payoff:** Once completed, the Picture House is unlocked, and **Episode 1: Unpayable Debt** is available by default.

## Unlocking New Movies
Movies 2 through 10 are locked and do not appear in the "Watch" menu until their corresponding **Movie Reel** is found and "used" at the Picture House.

### Mechanics
- **Unlocks:** Tracked via `character.db.brave_unlocked_movies` (a list of episode numbers).
- **Default State:** After the repair quest, `[1]` is added to this list if empty.
- **Finding Reels:** Reels are high-value collectible items found in:
    - **Boss Loot:** e.g., Blackreed drops Episode 4 (The Road at Night).
    - **Quest Rewards:** e.g., "The Pot-King's Feast" rewards Episode 3 (Showdown in the Rain).
    - **Hidden Search:** e.g., Hidden in a chest in the Ruined Watchtower.

## Technical Implementation
- `world/movies.py`: `build_movie_picker(character)` filters `GREAT_FRONTIER_MOVIES` against the character's unlocked list.
- `commands/brave_town.py`: `CmdMovie` enforces the repair quest requirement and handles the "movie" command logic.
- `world/browser_room_helpers.py`: Room interaction menu shows "Projector broken" until the repair quest is finished.

## Future Expansion
This system allows for "Seasonal" reels or specialized content to be added as limited-time loot or exploration rewards.
