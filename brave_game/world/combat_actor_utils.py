"""Shared combat actor helpers for character, companion, and enemy targets."""

from collections.abc import Mapping

from world.race_perks import get_incoming_damage_reduction


def _combat_target_id(target):
    """Return a stable id for combat targets backed by mappings or objects."""

    if isinstance(target, Mapping):
        return target.get("id")
    return getattr(target, "id", None)


def _combat_target_name(target, default=""):
    """Return a display name for combat targets backed by mappings or objects."""

    if isinstance(target, Mapping):
        return target.get("key", default) or default
    return getattr(target, "key", default) or default


def _combat_entry_ref(target):
    """Return the stable browser combat card ref for a character or enemy mapping."""

    if isinstance(target, Mapping):
        target_id = target.get("id")
        if target.get("kind") == "companion":
            return f"c:{target_id}" if target_id is not None else None
        return f"e:{target_id}" if target_id is not None else None
    target_id = getattr(target, "id", None)
    return f"p:{target_id}" if target_id is not None else None


def _is_companion_actor(target):
    """Return whether the allied combatant is a ranger companion mapping."""

    return isinstance(target, Mapping) and target.get("kind") == "companion"


def _ally_actor_id(target):
    """Return a stable ally actor id for characters or companion mappings."""

    return _combat_target_id(target)


def _enemy_damage_type(enemy):
    """Return a broad damage type tag for an enemy action."""

    template_key = str((enemy or {}).get("template_key") or "").lower()
    if template_key in {"tower_archer", "old_greymaw", "forest_wolf", "grave_crow", "carrion_hound", "mire_hound", "silt_stalker"}:
        return "physical"
    if template_key in {"barrow_wisp", "restless_shade", "sir_edric_restless", "hollow_wisp", "hollow_lantern"}:
        return "shadow"
    if template_key in {"fen_wisp", "bog_creeper", "miretooth"}:
        return "nature"
    if template_key in {"mag_clamp_drone", "foreman_coilback", "relay_tick"}:
        return "lightning"
    return "physical"
