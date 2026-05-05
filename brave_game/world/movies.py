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
            "The road opens on a debt no honest coin can settle.",
            "A lantern burns low over a ledger written in favors, promises, and weathered names.",
            "Somewhere beyond Brambleford, a rider learns that owing the frontier means being called back by it.",
            "The last page turns before the bargain is finished.",
        ),
    },
    {
        "number": 2,
        "title": "Memories of Another Life",
        "cue_id": "music.great_frontier.memories_of_another_life",
        "runtime_sec": 338,
        "cards": (
            "A face in a rain-streaked window remembers a life that may never have happened.",
            "Old rooms drift past like towns seen from a moving wagon.",
            "The frontier keeps what people bury, then hums it back when the night gets quiet.",
            "One memory refuses to stay behind the door where it was left.",
        ),
    },
    {
        "number": 3,
        "title": "Showdown in the Rain",
        "cue_id": "music.great_frontier.showdown_in_the_rain",
        "runtime_sec": 311,
        "cards": (
            "Rain turns the street silver, and every bootstep sounds like a verdict.",
            "Two silhouettes face each other beneath a lamp that should have gone out.",
            "No one reaches for steel quickly. The frontier has waited long enough to enjoy the pause.",
            "Thunder speaks first. The rest is answered by nerve.",
        ),
    },
    {
        "number": 4,
        "title": "The Road at Night",
        "cue_id": "music.great_frontier.the_road_at_night",
        "runtime_sec": 252,
        "cards": (
            "The road after dusk is not empty. It is listening.",
            "Lantern posts lean into the dark like tired witnesses.",
            "Wagon tracks vanish under mist, but something keeps pace beyond the ditch grass.",
            "The safest light is the one you carry without trusting too much.",
        ),
    },
    {
        "number": 5,
        "title": "The Black City",
        "cue_id": "music.great_frontier.the_black_city",
        "runtime_sec": 171,
        "cards": (
            "At the edge of the map, a city rises where no road admits to leading.",
            "Its towers drink moonlight and return only shadow.",
            "Every gate stands open. That is how the warning begins.",
            "The frontier does not end at the walls. It changes its name.",
        ),
    },
    {
        "number": 6,
        "title": "Refuge",
        "cue_id": "music.great_frontier.refuge",
        "runtime_sec": 360,
        "cards": (
            "A door opens before the storm can ask permission.",
            "Inside, strangers make room on benches polished by every kind of weather.",
            "Soup steams, boots dry, and the worst news waits outside with the rain.",
            "For one song, survival sounds almost like home.",
        ),
    },
    {
        "number": 7,
        "title": "Reclamation",
        "cue_id": "music.great_frontier.reclamation",
        "runtime_sec": 218,
        "cards": (
            "Morning finds the broken fence first, then the hands willing to mend it.",
            "Fields remember footsteps. So do ruins.",
            "A town takes back one stone, one name, one lantern at a time.",
            "What was lost does not return unchanged, but it returns.",
        ),
    },
    {
        "number": 8,
        "title": "The End of the Beginning",
        "cue_id": "music.great_frontier.the_end_of_the_beginning",
        "runtime_sec": 362,
        "cards": (
            "The first chapter closes with dust on the boots and smoke behind the hills.",
            "No one cheers too loudly. The frontier dislikes arrogance.",
            "A child pins a new notice over an old warning and calls it progress.",
            "The road ahead is wider now, which is not the same as kinder.",
        ),
    },
    {
        "number": 9,
        "title": "Reconciliation",
        "cue_id": "music.great_frontier.reconciliation",
        "runtime_sec": 343,
        "cards": (
            "Two chairs face the same cold hearth until someone finally sits down.",
            "Forgiveness arrives without ceremony, carrying mud on its hem.",
            "The hard words are not erased. They are set where both hands can reach them.",
            "Outside, the frontier waits for people who have remembered how to stand together.",
        ),
    },
    {
        "number": 10,
        "title": "Shackles",
        "cue_id": "music.great_frontier.shackles",
        "runtime_sec": 299,
        "cards": (
            "Iron remembers every wrist it was made to close around.",
            "A prisoner counts lantern flashes through a crack in the black door.",
            "Chains are loudest just before someone decides they are not permanent.",
            "When the lock gives, the whole frontier hears it.",
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



def resolve_movie(query):
    """Resolve a number or title query to one movie entry."""

    raw = str(query or "").strip()
    if not raw:
        return None, []
    if raw.isdigit():
        number = int(raw)
        for movie in GREAT_FRONTIER_MOVIES:
            if movie["number"] == number:
                return movie, []
        return None, []

    normalized = _normalize_movie_query(raw)
    matches = []
    for movie in GREAT_FRONTIER_MOVIES:
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


def build_now_showing_picker(movie):
    """Build a standard browser picker that shows the current movie's story cards."""

    return _picker(
        movie_label(movie),
        subtitle="Great Frontier · Now Showing",
        title_icon="theaters",
        body=movie_cards(movie),
        options=[
            _picker_option("Stop Movie", command="movie stop", icon="stop_circle", tone="danger"),
            _picker_option("Close Program", command="look", icon="close", tone="muted"),
        ],
    )


def build_movie_picker():
    """Build the browser picker used by the movie-house room action."""

    options = [
        _picker_option(
            movie_label(movie),
            command=f"movie {movie['number']}",
            icon="movie",
            tone="accent",
        )
        for movie in GREAT_FRONTIER_MOVIES
    ]
    options.append(_picker_option("Stop Movie", command="movie stop", icon="stop_circle", tone="muted"))
    return _picker(
        "Great Frontier",
        subtitle="Choose a picture-house showing.",
        title_icon="theaters",
        body=[
            "The brass speaker will play the selected Great Frontier reel for you. There are no projected images yet; Brambleford is doing its best.",
        ],
        options=options,
    )
