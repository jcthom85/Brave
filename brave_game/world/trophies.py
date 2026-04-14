"""Shared trophy hall helpers for Brave."""

from world.bootstrap import get_entity
from world.content import get_content_registry

CONTENT = get_content_registry()
TROPHIES = CONTENT.systems.trophies


_UNUSED_TROPHIES = {
    "blackreed_battle_standard": {
        "name": "Blackreed Battle Standard",
        "world": "Ruined Watchtower",
        "summary": "The rain-dark standard Captain Varn flew over the tower, hung now as proof the ridge does not belong to him anymore.",
        "placeholder": "A wall hook waits for whatever proof finally comes down from the old watchtower.",
    },
    "potking_battered_lid": {
        "name": "Pot-King's Battered Lid",
        "world": "Goblin Warrens",
        "summary": "The dented iron lid Grubnak treated like a crown, hung now as proof the warrens no longer rule the road below.",
        "placeholder": "An empty bracket waits for whatever ugly prize finally comes up from the goblin warrens.",
    },
    "miretooth_fen_jaw": {
        "name": "Miretooth's Fen Jaw",
        "world": "Blackfen Approach",
        "summary": "The hooked lower jaw of the marsh predator stalking Blackfen, mounted now as proof the bog edge does not answer only to hunger.",
        "placeholder": "A narrow iron cradle waits for whatever proof finally comes back from the Blackfen edge.",
    },
    "hollow_lantern_prism": {
        "name": "Hollow Lantern Prism",
        "world": "Drowned Weir",
        "summary": "The pale prism taken from the wrong south light at the drowned weir, hung now as proof Brambleford's first hard chapter ended with the lamp finally dark.",
        "placeholder": "A black-brass frame waits for whatever finally comes back from the drowned weir beyond Blackfen.",
    },
}


def _get_vitrine():
    return get_entity("trophy_vitrine")


def _ensure_trophy_log(vitrine):
    if not vitrine:
        return []
    log = list(vitrine.db.brave_trophies or [])
    vitrine.db.brave_trophies = log
    return log


def unlock_trophy(trophy_key, awarded_to=None):
    """Record a shared family trophy if it is not already present."""

    if trophy_key not in TROPHIES:
        return False

    vitrine = _get_vitrine()
    if not vitrine:
        return False

    log = _ensure_trophy_log(vitrine)
    for entry in log:
        if entry.get("key") == trophy_key:
            return False

    log.append({"key": trophy_key, "awarded_to": awarded_to or ""})
    vitrine.db.brave_trophies = log
    return True


def format_trophy_case_text():
    """Render the current shared trophy hall display."""

    vitrine = _get_vitrine()
    log = _ensure_trophy_log(vitrine)
    unlocked = {entry.get("key"): entry for entry in log}

    lines = [
        "The hall has been arranged like a promise: room for victories already won and stranger ones still ahead.",
        "",
    ]

    for trophy_key, trophy in TROPHIES.items():
        entry = unlocked.get(trophy_key)
        if entry:
            line = f"- {trophy['world']}: {trophy['name']}."
            if entry.get("awarded_to"):
                line += f" First hung by {entry['awarded_to']}."
            lines.append(line)
            lines.append(f"  {trophy['summary']}")
        else:
            lines.append(f"- {trophy['placeholder']}")

    if not unlocked:
        lines.extend(
            [
                "",
                "For now the glass mostly reflects empty hooks, polished brass, and ambition.",
            ]
        )

    return "\n".join(lines)
