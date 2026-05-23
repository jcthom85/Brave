"""Room atmosphere hints for browser exploration views."""


ATMOSPHERE_PROFILES = {
    "blackfen_rain_fog": {
        "key": "blackfen_rain_fog",
        "layers": ["rain", "fog", "boglight"],
        "intensity": "medium",
    },
    "drowned_wrong_light": {
        "key": "drowned_wrong_light",
        "layers": ["wrong_light", "waterline", "flicker"],
        "intensity": "high",
    },
    "barrow_darkness": {
        "key": "barrow_darkness",
        "layers": ["vignette", "grave_mist", "cold_dust"],
        "intensity": "medium",
    },
    "chapel_lamplight": {
        "key": "chapel_lamplight",
        "layers": ["lamplight", "dust_motes"],
        "intensity": "low",
    },
    "observatory_lampwork": {
        "key": "observatory_lampwork",
        "layers": ["lens_glow", "brass_sweep"],
        "intensity": "low",
    },
    "lanternworks_glow": {
        "key": "lanternworks_glow",
        "layers": ["floor_glow", "southline_pulse"],
        "intensity": "medium",
    },
    "lantern_rest_hearth": {
        "key": "lantern_rest_hearth",
        "layers": ["hearth_flicker", "cozy_shadows"],
        "intensity": "low",
    },
}


def list_atmosphere_profiles():
    """Return authorable browser atmosphere profile summaries."""

    return [
        {
            "id": key,
            "label": key.replace("_", " ").title(),
            "layers": list(profile.get("layers", [])),
            "intensity": profile.get("intensity", ""),
        }
        for key, profile in sorted(ATMOSPHERE_PROFILES.items())
    ]


def _normal(value):
    return str(value or "").strip().lower()


def get_room_atmosphere(room):
    """Return browser atmosphere metadata for an Act 1 room, if any."""

    room_db = getattr(room, "db", None)
    if not room_db:
        return None

    override = getattr(room_db, "brave_atmosphere", None)
    if override is False:
        return None
    if isinstance(override, str) and override:
        profile = ATMOSPHERE_PROFILES.get(override.strip().lower())
        return dict(profile) if profile else None

    room_id = _normal(getattr(room_db, "brave_room_id", ""))
    map_region = _normal(getattr(room_db, "brave_map_region", ""))
    zone = _normal(getattr(room_db, "brave_zone", ""))
    room_key = _normal(getattr(room, "key", ""))
    combined = " ".join(part for part in (room_id, map_region, zone, room_key) if part)

    if room_id == "brambleford_lantern_rest_inn" or "lantern rest inn" in combined:
        return dict(ATMOSPHERE_PROFILES["lantern_rest_hearth"])
    if room_id == "brambleford_lower_lanternworks":
        return dict(ATMOSPHERE_PROFILES["lanternworks_glow"])
    if room_id == "brambleford_great_observatory":
        return dict(ATMOSPHERE_PROFILES["observatory_lampwork"])
    if room_id == "brambleford_chapel_dawn_bell":
        return dict(ATMOSPHERE_PROFILES["chapel_lamplight"])
    if room_id.startswith("drowned_weir_") or "drowned weir" in combined:
        return dict(ATMOSPHERE_PROFILES["drowned_wrong_light"])
    if room_id.startswith("blackfen_") or "blackfen" in combined:
        return dict(ATMOSPHERE_PROFILES["blackfen_rain_fog"])
    if room_id.startswith("old_barrow_") or "barrow" in combined:
        return dict(ATMOSPHERE_PROFILES["barrow_darkness"])

    return None
