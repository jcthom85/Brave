"""Shared arcade helpers for cabinet lookup, scores, and rewards."""

from world.data.arcade import ARCADE_GAMES
from world.data.items import ITEM_TEMPLATES


LEADERBOARD_LIMIT = 5


def _normalize_token(value):
    return "".join(char for char in str(value or "").lower() if char.isalnum())


def format_arcade_score(score):
    """Return a compact score string."""

    try:
        return f"{max(0, int(score)):,}"
    except (TypeError, ValueError):
        return "0"


def resolve_arcade_game_query(query, available_games):
    """Resolve a game query against the cabinet's configured games."""

    options = [game_key for game_key in (available_games or []) if game_key in ARCADE_GAMES]
    if not query:
        return None, options

    query_norm = _normalize_token(query)
    matches = []
    for game_key in options:
        definition = ARCADE_GAMES[game_key]
        names = [game_key, definition.get("name", "")]
        names.extend(definition.get("aliases", []))
        if any(query_norm == _normalize_token(name) for name in names):
            matches.append(game_key)
    if matches:
        return matches[0] if len(matches) == 1 else matches, options

    matches = []
    for game_key in options:
        definition = ARCADE_GAMES[game_key]
        names = [game_key, definition.get("name", "")]
        names.extend(definition.get("aliases", []))
        if any(query_norm in _normalize_token(name) for name in names):
            matches.append(game_key)

    if not matches:
        return None, options
    return matches[0] if len(matches) == 1 else matches, options


def get_arcade_progress_key(cabinet, game_key):
    """Return a stable progress key for one cabinet/game pair."""

    cabinet_key = getattr(getattr(cabinet, "db", None), "brave_entity_id", None) or str(getattr(cabinet, "id", "arcade"))
    return f"{cabinet_key}:{game_key}"


def get_personal_best(character, cabinet, game_key):
    """Return the character's best known score for one cabinet/game pair."""

    scores = dict(getattr(character.db, "brave_arcade_best_scores", {}) or {})
    try:
        return max(0, int(scores.get(get_arcade_progress_key(cabinet, game_key), 0) or 0))
    except (TypeError, ValueError):
        return 0


def record_personal_best(character, cabinet, game_key, score):
    """Update and return the character's best known score for one cabinet/game pair."""

    safe_score = max(0, int(score or 0))
    progress_key = get_arcade_progress_key(cabinet, game_key)
    scores = dict(getattr(character.db, "brave_arcade_best_scores", {}) or {})
    previous = 0
    try:
        previous = max(0, int(scores.get(progress_key, 0) or 0))
    except (TypeError, ValueError):
        previous = 0
    if safe_score > previous:
        scores[progress_key] = safe_score
        character.db.brave_arcade_best_scores = scores
        return safe_score, True
    return previous, False


def get_reward_definition(cabinet, game_key):
    """Return one cabinet-specific reward definition, enriched with item info."""

    rewards = dict(getattr(getattr(cabinet, "db", None), "brave_arcade_rewards", {}) or {})
    reward = dict(rewards.get(game_key) or {})
    try:
        reward["threshold"] = max(0, int(reward.get("threshold") or 0))
    except (TypeError, ValueError):
        reward["threshold"] = 0
    template_id = reward.get("item")
    template = ITEM_TEMPLATES.get(template_id) if template_id else None
    if template:
        reward["item_name"] = template["name"]
    return reward


def has_arcade_reward(character, cabinet, game_key):
    """Whether the character has already claimed this cabinet's prize."""

    claims = dict(getattr(character.db, "brave_arcade_claims", {}) or {})
    return get_arcade_progress_key(cabinet, game_key) in claims


def maybe_award_arcade_reward(character, cabinet, game_key, score):
    """Grant a one-time reward item if the cabinet threshold was met."""

    reward = get_reward_definition(cabinet, game_key)
    threshold = reward.get("threshold", 0)
    template_id = reward.get("item")
    if not threshold or not template_id or score < threshold or has_arcade_reward(character, cabinet, game_key):
        return None

    character.add_item_to_inventory(template_id, 1)
    claims = dict(getattr(character.db, "brave_arcade_claims", {}) or {})
    claims[get_arcade_progress_key(cabinet, game_key)] = {
        "item": template_id,
        "score": max(0, int(score or 0)),
    }
    character.db.brave_arcade_claims = claims
    reward["score"] = max(0, int(score or 0))
    return reward


def merge_arcade_leaderboard(entries, player_name, score, limit=LEADERBOARD_LIMIT):
    """Merge one score into a leaderboard, keeping each player's best result."""

    safe_score = max(0, int(score or 0))
    cleaned = []
    by_player = {}
    player_token = _normalize_token(player_name)

    for entry in entries or []:
        name = str((entry or {}).get("name") or "").strip()
        if not name:
            continue
        try:
            entry_score = max(0, int((entry or {}).get("score", 0) or 0))
        except (TypeError, ValueError):
            continue
        cleaned.append({"name": name, "score": entry_score})

    cleaned.sort(key=lambda entry: (-entry["score"], entry["name"].lower()))
    previous_top = cleaned[0]["score"] if cleaned else None

    for entry in cleaned:
        token = _normalize_token(entry["name"])
        current = by_player.get(token)
        if not current or entry["score"] > current["score"]:
            by_player[token] = dict(entry)

    previous_best = by_player.get(player_token, {}).get("score", 0)
    improved_personal_best = safe_score > previous_best
    if improved_personal_best or player_token not in by_player:
        by_player[player_token] = {"name": player_name, "score": safe_score}

    full_leaderboard = sorted(by_player.values(), key=lambda entry: (-entry["score"], entry["name"].lower()))
    updated = full_leaderboard[:limit]
    rank = None
    for index, entry in enumerate(full_leaderboard, start=1):
        if _normalize_token(entry["name"]) == player_token:
            rank = index
            break

    was_top_owner = bool(cleaned and _normalize_token(cleaned[0]["name"]) == player_token)
    became_top = bool(updated and _normalize_token(updated[0]["name"]) == player_token)
    new_top_score = False
    if became_top and improved_personal_best:
        if previous_top is None or safe_score > previous_top:
            new_top_score = True
        elif was_top_owner and safe_score > cleaned[0]["score"]:
            new_top_score = True

    return updated, {
        "rank": rank,
        "score": safe_score,
        "leaderboard_limit": max(1, int(limit or LEADERBOARD_LIMIT)),
        "improved_personal_best": improved_personal_best,
        "new_top_score": new_top_score,
    }


def submit_arcade_score(character, cabinet, game_key, score):
    """Record a finished arcade run and resolve personal-best/prize state."""

    safe_score = max(0, int(score or 0))
    score_log = dict(getattr(cabinet.db, "brave_arcade_scores", {}) or {})
    updated_entries, details = merge_arcade_leaderboard(score_log.get(game_key, []), character.key, safe_score)
    score_log[game_key] = updated_entries
    cabinet.db.brave_arcade_scores = score_log

    best_score, improved_personal_best = record_personal_best(character, cabinet, game_key, safe_score)
    reward = maybe_award_arcade_reward(character, cabinet, game_key, safe_score)

    details["entries"] = updated_entries
    details["best_score"] = best_score
    details["improved_personal_best"] = improved_personal_best
    details["player_name"] = character.key
    details["reward"] = reward
    return details


def build_arcade_result_payload(cabinet, game_key, score, details):
    """Return a browser-friendly result payload for one finished arcade run."""

    safe_score = max(0, int(score or 0))
    details = details or {}
    entries = list(details.get("entries") or [])
    limit = max(1, int(details.get("leaderboard_limit") or LEADERBOARD_LIMIT))
    current_name = str(details.get("player_name") or "").strip()
    current_token = _normalize_token(current_name)
    high_score = 0
    if entries:
        try:
            high_score = max(0, int((entries[0] or {}).get("score", 0) or 0))
        except (TypeError, ValueError):
            high_score = 0
    rank = details.get("rank")
    rank_value = f"#{rank}" if rank else "Off Board"

    leaderboard = []
    for index, entry in enumerate(entries[:limit], start=1):
        name = str((entry or {}).get("name") or "").strip() or "Unknown"
        try:
            entry_score = max(0, int((entry or {}).get("score", 0) or 0))
        except (TypeError, ValueError):
            entry_score = 0
        name_token = _normalize_token(name)
        leaderboard.append(
            {
                "rank": index,
                "name": name,
                "score": format_arcade_score(entry_score),
                "is_current": bool(current_token and name_token == current_token),
                "is_top": index == 1,
            }
        )

    player_row = None
    if rank and rank > limit:
        player_row = {
            "rank": rank,
            "name": current_name or "Unknown",
            "score": format_arcade_score(safe_score),
            "is_current": True,
        }

    notes = []
    if details.get("new_top_score"):
        notes.append({"tone": "record", "text": "New cabinet record."})
    elif details.get("improved_personal_best"):
        notes.append({"tone": "personal", "text": "New personal best on this cabinet."})
    if details.get("reward") and details["reward"].get("item_name"):
        notes.append({"tone": "reward", "text": f"Prize drawer opens: {details['reward']['item_name']}."})

    if details.get("new_top_score"):
        headline = "NEW HIGH SCORE"
    elif details.get("reward"):
        headline = "PRIZE UNLOCKED"
    elif details.get("improved_personal_best"):
        headline = "PERSONAL BEST"
    else:
        headline = "RUN COMPLETE"

    tone = "good" if (details.get("new_top_score") or details.get("improved_personal_best") or details.get("reward")) else "muted"
    return {
        "cabinet": getattr(cabinet, "key", "Arcade Cabinet"),
        "title": ARCADE_GAMES.get(game_key, {}).get("name", "Arcade"),
        "headline": headline,
        "tone": tone,
        "summary_stats": [
            {"label": "Your Score", "value": format_arcade_score(safe_score), "accent": "score"},
            {"label": "Your Rank", "value": rank_value, "accent": "rank"},
            {"label": "High Score", "value": format_arcade_score(high_score), "accent": "high"},
        ],
        "leaderboard_title": "Local Leaderboard",
        "limit": limit,
        "leaderboard": leaderboard,
        "player_row": player_row,
        "notes": notes,
        "stats": [
            {"label": "Your Score", "value": format_arcade_score(safe_score)},
            {"label": "Your Rank", "value": rank_value},
            {"label": "High Score", "value": format_arcade_score(high_score)},
        ],
        "lines": [note["text"] for note in notes],
    }
