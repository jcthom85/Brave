"""Great Frontier movie-house helpers."""

from world.activities import room_supports_activity
from world.browser_ui import _action, _chip, _entry, _make_view, _meter, _picker, _picker_option, _section

MOVIE_THEATER_ACTIVITY = "movie_theater"
MOVIE_THEATER_ROOM_ID = "brambleford_frontier_picture_house"

GREAT_FRONTIER_MOVIES = (
    {
        "number": 1,
        "title": "Unpayable Debt",
        "cue_id": "music.great_frontier.unpayable_debt",
        "runtime_sec": 289,
        "cards": (
            "Alex grieves on his family farm while a mysterious man in black arrives searching for a girl.",
            "A debt marker waits on the table where dinner should be, and every quiet room feels too large.",
            "At the edge of the wheat, black cloth moves against the wind and the family dog refuses to bark.",
        ),
    },
    {
        "number": 2,
        "title": "Memories of Another Life",
        "cue_id": "music.great_frontier.memories_of_another_life",
        "runtime_sec": 338,
        "cards": (
            "Alex drifts to sleep, weighed down by memories of his late wife.",
            "Old sunlight, hospital glass, and a promise half-remembered fold together behind his eyes.",
            "When he wakes, the house is still, but the dream has left muddy footprints in the hall.",
        ),
    },
    {
        "number": 3,
        "title": "Showdown in the Rain",
        "cue_id": "music.great_frontier.showdown_in_the_rain",
        "runtime_sec": 311,
        "cards": (
            "The stranger destroys the farm. Alex finds Carly, and they escape into the rain.",
            "Gunfire cracks through the downpour while the barn roof burns like a signal nobody asked for.",
            "Carly knows the back road, Alex knows only that staying would mean dying on familiar ground.",
        ),
    },
    {
        "number": 4,
        "title": "The Road at Night",
        "cue_id": "music.great_frontier.the_road_at_night",
        "runtime_sec": 252,
        "cards": (
            "Alex and Carly drive toward town, unsure whether they are running from danger or toward it.",
            "The road signs keep changing in the headlights, naming towns Alex swears were never on the map.",
            "In the rearview mirror, one black rider keeps pace without ever touching the wet road.",
        ),
    },
    {
        "number": 5,
        "title": "The Black City",
        "cue_id": "music.great_frontier.the_black_city",
        "runtime_sec": 171,
        "cards": (
            "Alex and Carly step into town and cross into the Black City, an alien place hidden behind the familiar streets.",
            "Brick storefronts bend into iron towers, and every window reflects a sky with no moon.",
            "Carly says not to look at the bells when they ring, which makes Alex look almost at once.",
        ),
    },
    {
        "number": 6,
        "title": "Refuge",
        "cue_id": "music.great_frontier.refuge",
        "runtime_sec": 360,
        "cards": (
            "Carly leads Alex to her hideout and remembers her mother before Alex leaves for the Black City alone.",
            "The room is small, warm, and full of careful exits; Carly has survived by measuring every wall.",
            "Alex takes her map and a silence he does not know how to repay.",
        ),
    },
    {
        "number": 7,
        "title": "Reclamation",
        "cue_id": "music.great_frontier.reclamation",
        "runtime_sec": 218,
        "cards": (
            "The stranger captures Alex. Carly returns, forcing a violent confrontation inside the Black City.",
            "Chains drag over the station floor while the stranger names debts like they are family history.",
            "Carly steps from the smoke with a stolen pistol and the look of someone done being hunted.",
        ),
    },
    {
        "number": 8,
        "title": "The End of the Beginning",
        "cue_id": "music.great_frontier.the_end_of_the_beginning",
        "runtime_sec": 362,
        "cards": (
            "Alex and Carly rest after escaping the Black City and begin to trust each other.",
            "Morning finds them in a rail shed outside the impossible walls, sharing bread too stale to argue over.",
            "For the first time, the road ahead looks chosen instead of merely survived.",
        ),
    },
    {
        "number": 9,
        "title": "Reconciliation",
        "cue_id": "music.great_frontier.reconciliation",
        "runtime_sec": 343,
        "cards": (
            "Alex and Carly prepare to board a train and rescue a captive boy.",
            "The timetable is written in a dead conductor's hand, but Carly reads it like a dare.",
            "Alex checks the old revolver twice and still cannot make it feel like enough.",
        ),
    },
    {
        "number": 10,
        "title": "Shackles",
        "cue_id": "music.great_frontier.shackles",
        "runtime_sec": 299,
        "cards": (
            "Carly boards the train and commits to the rescue.",
            "Iron remembers every prisoner it has carried, and the rails sing those names under the wheels.",
            "At the last car, Alex sees the boy's lantern blink once from behind a locked door.",
        ),
    },
)


def _normalize_movie_query(value):
    return "".join(char for char in str(value or "").lower() if char.isalnum())


def is_movie_theater_room(room):
    """Return whether the room supports Great Frontier movie playback."""

    return room_supports_activity(room, MOVIE_THEATER_ACTIVITY)


def movie_label(movie):
    """Return the player-facing label for a movie entry."""

    return str(movie.get("title") or "").strip()


def movie_cards(movie):
    """Return authored title-card lines for a movie entry."""

    return [str(line).strip() for line in (movie.get("cards") or ()) if str(line).strip()]


def build_movie_audio_payload(movie):
    """Return the browser payload for starting one private movie showing."""

    return {
        "action": "play",
        "cue_id": movie["cue_id"],
        "title": movie_label(movie),
        "cards": movie_cards(movie),
        "runtime_sec": int(movie.get("runtime_sec") or 0),
        "program_command": "movie",
        "stop_command": "movie stop",
    }


def build_movie_view(movie):
    """Build the main browser view shown while a Great Frontier movie plays."""

    cards = movie_cards(movie)
    runtime = int(movie.get("runtime_sec") or 0)
    minutes, seconds = divmod(runtime, 60)
    runtime_label = f"{minutes}:{seconds:02d}" if runtime else "Now playing"
    title = movie_label(movie)
    title_card_entries = [
        _entry(
            f"Title Card {index}",
            meta=title,
            lines=[card],
            icon="subtitles",
            background_icon="movie",
        )
        for index, card in enumerate(cards, start=1)
    ]
    return {
        **_make_view(
            "Frontier Picture House",
            title,
            eyebrow_icon="theaters",
            title_icon="movie",
            subtitle="The room goes dark, the brass speaker wakes, and the picture house fills in the rest.",
            chips=[
                _chip("Great Frontier", "local_movies", "accent"),
                _chip(runtime_label, "schedule", "muted"),
                _chip("Audio Showing", "volume_up", "good"),
            ],
            sections=[
                _section(
                    "Screen",
                    "slideshow",
                    "entries",
                    items=title_card_entries,
                    span="wide",
                    variant="movie-cards",
                ),
                _section(
                    "Showing",
                    "equalizer",
                    "pairs",
                    items=[
                        {"label": "Feature", "value": title, "icon": "movie"},
                        {"label": "Format", "value": "Great Frontier sound reel", "icon": "graphic_eq"},
                        {"label": "Runtime", "value": runtime_label, "icon": "schedule"},
                    ],
                    span="compact",
                    variant="movie-meta",
                ),
                _section(
                    "Progress",
                    "timelapse",
                    "entries",
                    items=[
                        _entry(
                            "Reel In Motion",
                            meta="Private showing",
                            lines=["The lantern glass flickers in time with the music."],
                            icon="play_circle",
                            meters=[_meter("Opening reel", 1, max(1, len(cards)), tone="accent", value="playing")],
                        )
                    ],
                    span="compact",
                    variant="movie-progress",
                ),
            ],
            actions=[
                _action("Stop Movie", "movie stop", "stop_circle", tone="danger"),
                _action("Program", "movie", "list", tone="muted"),
                _action("Look Around", "look", "visibility", tone="muted"),
            ],
            reactive={"scene": "movie", "world_tone": "safe"},
        ),
        "variant": "movie",
        "tone": "safe",
    }


def send_movie_stop_event(character):
    """Stop any private movie playback for a character's web sessions."""

    from world.browser_panels import send_webclient_event

    send_webclient_event(character, brave_movie_audio={"action": "stop"})
    send_webclient_event(character, brave_movie_overlay={"action": "stop"})



def resolve_movie(query, pool=None):
    """Resolve a number or title query to one movie entry."""

    raw = str(query or "").strip()
    if not raw:
        return None, []
        
    if pool is None:
        pool = GREAT_FRONTIER_MOVIES
        
    if raw.isdigit():
        number = int(raw)
        for movie in pool:
            if movie["number"] == number:
                return movie, []
        return None, []

    normalized = _normalize_movie_query(raw)
    matches = []
    for movie in pool:
        candidates = {
            _normalize_movie_query(movie["title"]),
            _normalize_movie_query(movie_label(movie)),
            _normalize_movie_query(f"Great Frontier {movie['title']}"),
            _normalize_movie_query(f"Great Frontier - {movie['title']}"),
        }
        if normalized in candidates:
            return movie, []
        if any(normalized and normalized in candidate for candidate in candidates):
            matches.append(movie)
    return (matches[0], []) if len(matches) == 1 else (None, matches)


def get_unlocked_movie_numbers(character):
    """Return the list of movie episode numbers unlocked for a character."""

    if character is None:
        return [movie["number"] for movie in GREAT_FRONTIER_MOVIES]

    unlocked = list(getattr(character.db, "brave_unlocked_movies", []) or [])

    quest_log = getattr(character.db, "brave_quests", {})
    if quest_log.get("repair_the_picture_house", {}).get("status") == "completed":
        if 1 not in unlocked:
            unlocked.append(1)
            character.db.brave_unlocked_movies = unlocked
            
    return unlocked


def get_available_movies(character=None):
    """Return the subset of GREAT_FRONTIER_MOVIES available to the character."""

    unlocked_numbers = set(get_unlocked_movie_numbers(character))
    return [movie for movie in GREAT_FRONTIER_MOVIES if movie["number"] in unlocked_numbers]


def unlock_movie(character, number):
    """Permanently unlock a movie for a character."""

    unlocked = list(get_unlocked_movie_numbers(character))
    if number not in unlocked:
        unlocked.append(number)
        unlocked.sort()
        character.db.brave_unlocked_movies = unlocked
        return True
    return False


def build_now_showing_picker(movie):
    """Build a standard browser picker that shows the current movie's story cards."""

    return _picker(
        movie_label(movie),
        subtitle="Great Frontier · Now Showing",
        title_icon="movie",
        body=movie_cards(movie),
        options=[
            _picker_option("Stop Movie", command="movie stop", icon="stop_circle", tone="danger"),
            _picker_option("Close Program", command="look", icon="close", tone="muted"),
        ],
        picker_kind="movie-showing",
        movie={
            "title": movie_label(movie),
            "cards": movie_cards(movie),
            "runtime_sec": int(movie.get("runtime_sec") or 0),
        },
    )


def build_movie_picker(character=None):
    """Build the browser picker used by the movie-house room action."""

    available = get_available_movies(character)
    options = [
        _picker_option(
            movie_label(movie),
            command=f"movie {movie['number']}",
            icon="movie",
            tone="accent",
        )
        for movie in available
    ]
    options.append(_picker_option("Stop Movie", command="movie stop", icon="stop_circle", tone="muted"))
    return _picker(
        "Great Frontier",
        subtitle="Choose a picture-house showing.",
        title_icon="movie",
        body=[
            "The brass speaker will play the selected Great Frontier reel for you. There are no projected images yet; Brambleford is doing its best.",
        ],
        options=options,
    )
