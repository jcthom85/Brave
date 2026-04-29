"""Shared trophy hall helpers for Brave."""

from world.bootstrap import get_entity
from world.content import get_content_registry

CONTENT = get_content_registry()
TROPHIES = CONTENT.systems.trophies


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
