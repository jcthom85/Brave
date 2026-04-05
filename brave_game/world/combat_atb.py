"""ATB timing profiles for Brave combat actions.

This module is intentionally pure and side-effect free. It defines how
abilities and combat items should describe their timing semantics before
the encounter loop itself is migrated from round-queue resolution to a
short-tick ATB model.
"""

from __future__ import annotations

import time


DEFAULT_ATB_PROFILE = {
    "gauge_cost": 100,
    "windup_ticks": 1,
    "recovery_ticks": 1,
    "cooldown_ticks": 0,
    "interruptible": True,
    "telegraph": False,
    "target_locked": True,
}

ATB_TIMING_SCALE = 1
DEFAULT_ATB_TICK_MS = 1000


def _clamped_tick(value, *, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _now_ms():
    return int(round(time.time() * 1000))


def _charging_duration_ms(start_gauge, ready_gauge, fill_rate, tick_ms):
    remaining = max(0, ready_gauge - start_gauge)
    if remaining <= 0:
        return 0
    return max(1, int(round((remaining / max(1, fill_rate)) * max(1, tick_ms))))


def create_atb_state(
    *,
    fill_rate=100,
    gauge=0,
    phase="charging",
    ticks_remaining=0,
    current_action=None,
    timing=None,
    ready_gauge=100,
    phase_started_at_ms=None,
    phase_duration_ms=None,
    phase_start_gauge=None,
    tick_ms=DEFAULT_ATB_TICK_MS,
):
    """Return a normalized actor ATB state mapping."""

    fill_rate = max(1, _clamped_tick(fill_rate, default=100))
    gauge = max(0, _clamped_tick(gauge))
    ready_gauge = max(1, _clamped_tick(ready_gauge, default=100))
    phase = phase or "charging"
    started_at = _clamped_tick(phase_started_at_ms, default=_now_ms())
    start_gauge = max(0, min(ready_gauge, _clamped_tick(phase_start_gauge, default=gauge)))
    duration_ms = _clamped_tick(phase_duration_ms)
    if phase == "charging" and duration_ms <= 0:
        duration_ms = _charging_duration_ms(start_gauge, ready_gauge, fill_rate, tick_ms)
    elif phase in {"winding", "recovering", "cooldown"} and duration_ms <= 0:
        duration_ms = max(0, _clamped_tick(ticks_remaining) * max(1, tick_ms))

    return {
        "fill_rate": fill_rate,
        "gauge": gauge,
        "ready_gauge": ready_gauge,
        "phase": phase,
        "ticks_remaining": max(0, _clamped_tick(ticks_remaining)),
        "current_action": current_action,
        "timing": timing if isinstance(timing, dict) else None,
        "phase_started_at_ms": started_at,
        "phase_duration_ms": duration_ms,
        "phase_start_gauge": start_gauge,
    }


def render_atb_state(state, *, tick_ms=DEFAULT_ATB_TICK_MS, now_ms=None):
    """Return a display-safe ATB state projected to the current time.

    This keeps the actor in the same phase while updating gauge and remaining
    ticks so UI refreshes do not fall back to the last persisted snapshot.
    """

    now_ms = _clamped_tick(now_ms, default=_now_ms())
    normalized = dict(state or {})
    normalized.setdefault("ready_gauge", 400)
    if normalized.get("phase_started_at_ms") is None:
        normalized["phase_started_at_ms"] = now_ms
    state = create_atb_state(**normalized, tick_ms=tick_ms)
    phase = state["phase"]

    if phase == "charging":
        duration_ms = max(0, int(state.get("phase_duration_ms", 0) or 0))
        started_at = int(state.get("phase_started_at_ms", now_ms) or now_ms)
        start_gauge = max(0, min(state["ready_gauge"], int(state.get("phase_start_gauge", state["gauge"]) or 0)))
        max_charging_gauge = max(0, state["ready_gauge"] - 1)
        if duration_ms <= 0 or now_ms - started_at >= duration_ms:
            state["gauge"] = max_charging_gauge
            state["ticks_remaining"] = 1 if state["ready_gauge"] > 0 else 0
        else:
            progress = max(0.0, min(1.0, (now_ms - started_at) / float(duration_ms)))
            projected_gauge = int(round(start_gauge + ((state["ready_gauge"] - start_gauge) * progress)))
            state["gauge"] = min(max_charging_gauge, projected_gauge)
            remaining_ms = max(0, duration_ms - (now_ms - started_at))
            state["ticks_remaining"] = max(1, int((remaining_ms + max(1, tick_ms) - 1) // max(1, tick_ms)))
        return state

    if phase in {"winding", "recovering", "cooldown"}:
        duration_ms = max(0, int(state.get("phase_duration_ms", 0) or 0))
        started_at = int(state.get("phase_started_at_ms", now_ms) or now_ms)
        if duration_ms <= 0 or now_ms - started_at >= duration_ms:
            state["ticks_remaining"] = 0
        else:
            remaining_ms = max(0, duration_ms - (now_ms - started_at))
            state["ticks_remaining"] = max(1, int((remaining_ms + max(1, tick_ms) - 1) // max(1, tick_ms)))
        if phase in {"recovering", "cooldown"}:
            state["gauge"] = 0
        return state

    if phase in {"ready", "resolving"}:
        state["gauge"] = state["ready_gauge"]
        state["ticks_remaining"] = 0
    return state


def normalize_atb_profile(raw_profile=None, *, base_profile=None):
    """Return a normalized ATB timing profile."""

    profile = dict(DEFAULT_ATB_PROFILE)
    if base_profile:
        profile.update(base_profile)
    raw_profile = dict(raw_profile or {})
    profile.update(
        {
            "gauge_cost": _clamped_tick(raw_profile.get("gauge_cost"), default=profile["gauge_cost"]),
            "windup_ticks": _clamped_tick(raw_profile.get("windup_ticks"), default=profile["windup_ticks"]) * ATB_TIMING_SCALE,
            "recovery_ticks": _clamped_tick(raw_profile.get("recovery_ticks"), default=profile["recovery_ticks"]) * ATB_TIMING_SCALE,
            "cooldown_ticks": _clamped_tick(raw_profile.get("cooldown_ticks"), default=profile["cooldown_ticks"]) * ATB_TIMING_SCALE,
            "interruptible": bool(raw_profile.get("interruptible", profile["interruptible"])),
            "telegraph": bool(raw_profile.get("telegraph", profile["telegraph"])),
            "target_locked": bool(raw_profile.get("target_locked", profile["target_locked"])),
        }
    )
    if profile["windup_ticks"] <= 0:
        profile["interruptible"] = False
    return profile


def tick_atb_state(state, *, tick_ms=DEFAULT_ATB_TICK_MS, now_ms=None):
    """Advance one actor ATB state by one encounter tick."""

    state = create_atb_state(**dict(state or {}), tick_ms=tick_ms)
    phase = state["phase"]
    now_ms = _clamped_tick(now_ms, default=_now_ms())

    if phase == "charging":
        fill_rate = max(1, int(state.get("fill_rate", 1) or 1))
        next_gauge = min(state["ready_gauge"], int(state.get("gauge", 0) or 0) + fill_rate)
        if next_gauge >= state["ready_gauge"]:
            state["gauge"] = state["ready_gauge"]
            state["phase"] = "ready"
            state["ticks_remaining"] = 0
            state["phase_started_at_ms"] = now_ms
            state["phase_duration_ms"] = 0
            state["phase_start_gauge"] = state["ready_gauge"]
        else:
            remaining = max(0, state["ready_gauge"] - next_gauge)
            state["gauge"] = next_gauge
            state["ticks_remaining"] = max(1, (remaining + fill_rate - 1) // fill_rate)
            state["phase_started_at_ms"] = now_ms
            state["phase_duration_ms"] = _charging_duration_ms(next_gauge, state["ready_gauge"], fill_rate, tick_ms)
            state["phase_start_gauge"] = next_gauge
        return state

    if phase in {"winding", "recovering", "cooldown"}:
        remaining = max(0, int(state.get("ticks_remaining", 0) or 0))
        if remaining > 1:
            state["ticks_remaining"] = remaining - 1
            state["phase_started_at_ms"] = now_ms
            state["phase_duration_ms"] = max(1, state["ticks_remaining"] * max(1, tick_ms))
        else:
            if phase == "winding":
                state["phase"] = "resolving"
                state["ticks_remaining"] = 0
                state["phase_started_at_ms"] = now_ms
                state["phase_duration_ms"] = 0
            else:
                state["phase"] = "charging"
                state["gauge"] = 0
                state["current_action"] = None
                state["timing"] = None
                state["ticks_remaining"] = 0
                state["phase_start_gauge"] = 0
                state["phase_started_at_ms"] = now_ms
                state["phase_duration_ms"] = _charging_duration_ms(0, state["ready_gauge"], state["fill_rate"], tick_ms)
        return state

    return state


def start_atb_action(state, action, timing, *, tick_ms=DEFAULT_ATB_TICK_MS, now_ms=None):
    """Move an ATB state from ready into winding or resolving."""

    state = create_atb_state(**dict(state or {}), tick_ms=tick_ms)
    timing = normalize_atb_profile(timing)
    now_ms = _clamped_tick(now_ms, default=_now_ms())
    state["gauge"] = 0
    state["phase_start_gauge"] = 0
    state["current_action"] = dict(action or {})
    state["timing"] = timing
    if timing["windup_ticks"] > 0:
        state["phase"] = "winding"
        state["ticks_remaining"] = timing["windup_ticks"]
        state["phase_started_at_ms"] = now_ms
        state["phase_duration_ms"] = timing["windup_ticks"] * max(1, tick_ms)
    else:
        state["phase"] = "resolving"
        state["ticks_remaining"] = 0
        state["phase_started_at_ms"] = now_ms
        state["phase_duration_ms"] = 0
    return state


def finish_atb_action(state, *, tick_ms=DEFAULT_ATB_TICK_MS, now_ms=None):
    """Move an ATB state from resolving into cooldown or recovery."""

    state = create_atb_state(**dict(state or {}), tick_ms=tick_ms)
    timing = normalize_atb_profile((state.get("timing") or {}))
    cooldown = max(0, timing.get("cooldown_ticks", 0))
    recovery = max(0, timing.get("recovery_ticks", 0))
    now_ms = _clamped_tick(now_ms, default=_now_ms())

    if cooldown > 0:
        state["phase"] = "cooldown"
        state["ticks_remaining"] = cooldown
        state["phase_started_at_ms"] = now_ms
        state["phase_duration_ms"] = cooldown * max(1, tick_ms)
    elif recovery > 0:
        state["phase"] = "recovering"
        state["ticks_remaining"] = recovery
        state["phase_started_at_ms"] = now_ms
        state["phase_duration_ms"] = recovery * max(1, tick_ms)
    else:
        state["phase"] = "charging"
        state["ticks_remaining"] = 0
        state["current_action"] = None
        state["timing"] = None
        state["gauge"] = 0
        state["phase_start_gauge"] = 0
        state["phase_started_at_ms"] = now_ms
        state["phase_duration_ms"] = _charging_duration_ms(0, state["ready_gauge"], state["fill_rate"], tick_ms)
    return state


def _default_ability_atb_profile(ability):
    cost = int((ability or {}).get("cost", 0) or 0)
    target = (ability or {}).get("target", "self")
    class_key = (ability or {}).get("class", "")
    resource = (ability or {}).get("resource", "")

    profile = dict(DEFAULT_ATB_PROFILE)
    profile["gauge_cost"] = 100 + max(0, cost - 8) * 4
    profile["recovery_ticks"] = 1 if cost < 12 else 2

    if target == "self":
        profile["windup_ticks"] = 0
        profile["target_locked"] = False
    elif target == "ally":
        profile["windup_ticks"] = 0 if cost <= 10 else 1
        profile["target_locked"] = False
    elif target == "none":
        profile["windup_ticks"] = 1 if cost < 14 else 2
        profile["telegraph"] = True
    else:
        profile["windup_ticks"] = 1 if cost < 16 else 2

    if resource == "mana" and target != "self":
        profile["windup_ticks"] = max(profile["windup_ticks"], 1)

    if class_key in {"mage", "cleric", "druid"} and target in {"enemy", "none"} and cost >= 12:
        profile["telegraph"] = True
    if class_key == "rogue" and target == "enemy" and cost <= 10:
        profile["windup_ticks"] = 0
        profile["recovery_ticks"] = 1
    if class_key in {"warrior", "paladin"} and target in {"self", "ally"}:
        profile["windup_ticks"] = 0
        profile["interruptible"] = False

    if cost >= 16:
        profile["cooldown_ticks"] = 1

    if profile["windup_ticks"] <= 0:
        profile["interruptible"] = False

    return profile


def get_ability_atb_profile(ability_key, ability):
    """Return normalized ATB timing metadata for an ability definition."""

    del ability_key  # Reserved for future keyed overrides.
    ability = dict(ability or {})
    return normalize_atb_profile(ability.get("atb"), base_profile=_default_ability_atb_profile(ability))


def _default_item_atb_profile(use_profile):
    use_profile = dict(use_profile or {})
    target = use_profile.get("target", "self")
    damage_spec = dict(use_profile.get("damage", {}) or {})

    profile = dict(DEFAULT_ATB_PROFILE)
    profile["gauge_cost"] = 92
    profile["cooldown_ticks"] = _clamped_tick(use_profile.get("cooldown_turns"))

    if target in {"self", "ally"}:
        profile["windup_ticks"] = 0
        profile["interruptible"] = False
        profile["target_locked"] = False
    elif target == "enemy":
        profile["windup_ticks"] = 1 if damage_spec.get("base") else 0
        profile["interruptible"] = profile["windup_ticks"] > 0
    elif target == "none":
        profile["windup_ticks"] = 1
        profile["telegraph"] = True

    return profile


def get_item_atb_profile(template_id, use_profile):
    """Return normalized ATB timing metadata for a combat consumable."""

    del template_id  # Reserved for future keyed overrides.
    use_profile = dict(use_profile or {})
    return normalize_atb_profile(use_profile.get("atb"), base_profile=_default_item_atb_profile(use_profile))
