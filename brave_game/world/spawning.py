"""Character spawn helpers for Brave accounts."""

from world.bootstrap import ensure_brave_world, get_room
from world.questing import reset_opening_quests_for_new_character
from world.tutorial import begin_tutorial, ensure_tutorial_state, get_tutorial_start_room, should_start_tutorial


def place_new_brave_character(account, character):
    """Create/repair Brave's world and move a character to the right start room."""

    ensure_brave_world()
    if hasattr(character, "db"):
        reset_opening_quests_for_new_character(character)
    if should_start_tutorial(account):
        begin_tutorial(character)
        start_room = (
            get_tutorial_start_room()
            or get_room("brambleford_training_yard")
            or get_room("brambleford_town_green")
        )
    else:
        start_room = get_room("brambleford_training_yard") or get_room("brambleford_town_green")

    if not start_room:
        return None

    character.home = start_room
    if character.location != start_room:
        character.move_to(start_room, quiet=True, move_type="spawn")
    return start_room


def _has_tutorial_progress(character):
    state = ensure_tutorial_state(character)
    flags = state.get("flags") or {}
    return any(bool(value) for value in flags.values())


def _has_left_opening(character):
    quests = getattr(character.db, "brave_quests", None) or {}
    if getattr(character.db, "brave_harl_cellar_job_assigned", False):
        return True
    rat_job = quests.get("rats_in_the_kettle") or {}
    if rat_job.get("status") in {"active", "completed"}:
        return True
    if int(getattr(character.db, "brave_level", 1) or 1) > 1:
        return True
    if int(getattr(character.db, "brave_xp", 0) or 0) > 0:
        return True
    return False


def ensure_newbie_area_on_puppet(account, character):
    """Repair unstarted/tutorial-active characters into the newbie area on play."""

    ensure_brave_world()
    state = ensure_tutorial_state(character)
    if state.get("status") == "completed":
        return False

    if state.get("status") == "inactive":
        if _has_tutorial_progress(character) or _has_left_opening(character):
            return False
        begin_tutorial(character)

    start_room = get_tutorial_start_room() or get_room("brambleford_training_yard")
    if not start_room:
        return False

    character.home = start_room
    if character.location != start_room:
        character.move_to(start_room, quiet=True, move_type="spawn")
        return True
    return False


def is_brave_room(room):
    """Return whether a room is part of Brave's authored world."""

    return bool(getattr(getattr(room, "db", None), "brave_room_id", None))
