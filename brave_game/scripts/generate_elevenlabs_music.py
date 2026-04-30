"""Generate Brave music candidates with the ElevenLabs Music API."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib import error, parse, request


GAME_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = GAME_ROOT.parent
DEFAULT_PLAN = GAME_ROOT / "web/static/webclient/audio/elevenlabs_music_plan.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tmp/audio-generation/elevenlabs-music"
DEFAULT_ENV_FILE = REPO_ROOT / ".env.local"
MUSIC_URL = "https://api.elevenlabs.io/v1/music"
API_KEY_ENV = "ELEVENLABS_API_KEY"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._-").lower() or "music"


def _load_api_key(env_file: Path | None) -> str:
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if api_key or not env_file or not env_file.exists():
        return api_key
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == API_KEY_ENV:
            return value.strip().strip("\"'")
    return ""


def _load_plan(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Plan not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Plan is not valid JSON: {path}: {exc}") from exc


def _iter_tracks(plan: dict, track_ids: set[str]):
    tracks = plan.get("tracks", [])
    if not isinstance(tracks, list):
        raise SystemExit("Plan must contain a tracks list.")
    for track in tracks:
        track_id = str(track.get("id", ""))
        if track_ids and track_id not in track_ids and str(track.get("target_cue", "")) not in track_ids:
            continue
        yield track


def _request_music(api_key: str, track: dict, output_format: str | None) -> tuple[bytes, str]:
    payload = {
        "prompt": track["prompt"],
        "music_length_ms": int(track["music_length_ms"]),
        "model_id": track.get("model_id", "music_v1"),
        "force_instrumental": bool(track.get("force_instrumental", True)),
    }
    query = f"?{parse.urlencode({'output_format': output_format})}" if output_format else ""
    req = request.Request(
        MUSIC_URL + query,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
    )
    try:
        with request.urlopen(req, timeout=900) as response:
            song_id = response.headers.get("song-id", "")
            return response.read(), song_id
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs music request failed: HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"ElevenLabs music request failed: {exc}") from exc


def _write_candidate(track: dict, audio_bytes: bytes, song_id: str, output_root: Path, plan_path: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = output_root / today
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = track.get("filename") or f"{_slug(track['id'])}.mp3"
    audio_path = out_dir / filename
    metadata_path = audio_path.with_suffix(".json")
    audio_path.write_bytes(audio_bytes)
    metadata = {
        "id": track.get("id"),
        "target_cue": track.get("target_cue"),
        "provider": "ElevenLabs Music API",
        "endpoint": MUSIC_URL,
        "song_id": song_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_plan": str(plan_path),
        "output_file": str(audio_path),
        "music_length_ms": track.get("music_length_ms"),
        "model_id": track.get("model_id", "music_v1"),
        "force_instrumental": bool(track.get("force_instrumental", True)),
        "prompt": track.get("prompt"),
        "license_note": "Generated through the user's ElevenLabs account. Verify active subscription and music rights before commercial release.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return audio_path


def _print_track(track: dict) -> None:
    seconds = int(track.get("music_length_ms", 0)) // 1000
    print(f"{track['id']:<28} {seconds:>4}s -> {track.get('target_cue', '')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--track", action="append", default=[], help="Track id or target cue to generate. May be repeated.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output-format", default="", help="Optional ElevenLabs output_format query value.")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)

    plan_path = args.plan.resolve()
    plan = _load_plan(plan_path)
    selected = list(_iter_tracks(plan, set(args.track)))
    if args.limit > 0:
        selected = selected[: args.limit]
    if not selected:
        print("No matching tracks found.", file=sys.stderr)
        return 1

    if args.list:
        for track in selected:
            _print_track(track)
        return 0
    if args.dry_run:
        for track in selected:
            print(json.dumps(track, indent=2))
        return 0
    if not args.yes:
        print("Generation requires --yes. Use --dry-run first to inspect prompts.", file=sys.stderr)
        return 2

    api_key = _load_api_key(args.env_file.resolve() if args.env_file else None)
    if not api_key:
        print(f"Set {API_KEY_ENV} or add it to {args.env_file}.", file=sys.stderr)
        return 2

    output_root = args.output_root.resolve()
    for track in selected:
        print(f"Generating {track['id']} ({int(track['music_length_ms']) // 1000}s)...", flush=True)
        audio_bytes, song_id = _request_music(api_key, track, args.output_format.strip() or None)
        output_path = _write_candidate(track, audio_bytes, song_id, output_root, plan_path)
        print(f"Wrote {output_path}" + (f" song-id={song_id}" if song_id else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
