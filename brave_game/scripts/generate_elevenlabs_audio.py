"""Generate Brave audio candidates with the ElevenLabs API.

This script is intentionally non-destructive: it writes generated candidates and
provenance records into a working directory and never edits the live audio
manifest or overwrites existing shipped assets.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib import error, request


GAME_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = GAME_ROOT.parent
DEFAULT_PLAN = GAME_ROOT / "web/static/webclient/audio/elevenlabs_plan.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tmp/audio-generation/elevenlabs"
DEFAULT_ENV_FILE = REPO_ROOT / ".env.local"
SOUND_GENERATION_URL = "https://api.elevenlabs.io/v1/sound-generation"
API_KEY_ENV = "ELEVENLABS_API_KEY"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._-").lower() or "audio"


def _load_plan(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Plan not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Plan is not valid JSON: {path}: {exc}") from exc


def _load_api_key(env_file: Path | None) -> str:
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if api_key or not env_file:
        return api_key
    if not env_file.exists():
        return ""
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == API_KEY_ENV:
            return value.strip().strip("\"'")
    return ""


def _iter_assets(plan: dict, cue_ids: set[str], kinds: set[str], batches: set[str]):
    assets = plan.get("assets", [])
    if not isinstance(assets, list):
        raise SystemExit("Plan must contain an assets list.")
    for asset in assets:
        asset_id = str(asset.get("id", ""))
        kind = str(asset.get("kind", ""))
        batch = str(asset.get("batch", ""))
        if (
            cue_ids
            and asset_id not in cue_ids
            and str(asset.get("target_cue", "")) not in cue_ids
            and str(asset.get("proposed_cue", "")) not in cue_ids
        ):
            continue
        if kinds and kind not in kinds:
            continue
        if batches and batch not in batches:
            continue
        yield asset


def _request_sound_effect(api_key: str, asset: dict) -> bytes:
    payload = {
        "text": asset["prompt"],
        "loop": bool(asset.get("loop")),
        "duration_seconds": asset.get("duration_seconds"),
        "prompt_influence": asset.get("prompt_influence", 0.5),
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        SOUND_GENERATION_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
    )
    try:
        with request.urlopen(req, timeout=180) as response:
            return response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs request failed: HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"ElevenLabs request failed: {exc}") from exc


def _write_candidate(asset: dict, audio_bytes: bytes, output_root: Path, plan_path: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    asset_dir = output_root / today
    asset_dir.mkdir(parents=True, exist_ok=True)

    asset_id = str(asset["id"])
    base_name = _slug(asset_id)
    audio_path = asset_dir / f"{base_name}.mp3"
    metadata_path = asset_dir / f"{base_name}.json"

    audio_path.write_bytes(audio_bytes)
    metadata = {
        "id": asset_id,
        "kind": asset.get("kind"),
        "target_cue": asset.get("target_cue"),
        "proposed_cue": asset.get("proposed_cue"),
        "provider": "ElevenLabs",
        "endpoint": SOUND_GENERATION_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_plan": str(plan_path),
        "output_file": str(audio_path),
        "duration_seconds": asset.get("duration_seconds"),
        "prompt_influence": asset.get("prompt_influence"),
        "loop": asset.get("loop", False),
        "prompt": asset.get("prompt"),
        "license_note": "Generated through the user's ElevenLabs account. Verify the active subscription and endpoint terms before commercial release.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return audio_path


def _print_asset(asset: dict) -> None:
    duration = asset.get("duration_seconds", "auto")
    loop = "loop" if asset.get("loop") else "one-shot"
    batch = asset.get("batch", "")
    target = asset.get("target_cue") or asset.get("proposed_cue") or ""
    print(f"{asset['id']:<36} {batch:<18} {asset.get('kind', ''):<13} {duration!s:<5} {loop:<8} -> {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--cue", action="append", default=[], help="Asset id or target cue to generate. May be repeated.")
    parser.add_argument("--kind", action="append", default=[], help="Filter by kind, such as sfx, ambience, or music_theme.")
    parser.add_argument("--batch", action="append", default=[], help="Filter by production batch. May be repeated.")
    parser.add_argument("--limit", type=int, default=0, help="Generate at most this many matching assets.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip assets already generated in today's output folder.")
    parser.add_argument("--list", action="store_true", help="List matching plan entries and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print matching prompts without calling ElevenLabs.")
    parser.add_argument("--yes", action="store_true", help="Allow generation. Required unless --list or --dry-run is used.")
    args = parser.parse_args(argv)

    plan_path = args.plan.resolve()
    plan = _load_plan(plan_path)
    selected = list(_iter_assets(plan, set(args.cue), set(args.kind), set(args.batch)))
    if args.limit > 0:
        selected = selected[: args.limit]
    if not selected:
        print("No matching assets found.", file=sys.stderr)
        return 1

    if args.list:
        for asset in selected:
            _print_asset(asset)
        return 0

    if args.dry_run:
        for asset in selected:
            print(json.dumps(asset, indent=2))
        return 0

    if not args.yes:
        print("Generation requires --yes. Use --dry-run first to inspect prompts.", file=sys.stderr)
        return 2

    api_key = _load_api_key(args.env_file.resolve() if args.env_file else None)
    if not api_key:
        print(f"Set {API_KEY_ENV} or add it to {args.env_file}.", file=sys.stderr)
        return 2

    output_root = args.output_root.resolve()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for asset in selected:
        expected_path = output_root / today / f"{_slug(str(asset['id']))}.mp3"
        if args.skip_existing and expected_path.exists():
            print(f"Skipping {asset['id']} because {expected_path} already exists.")
            continue
        print(f"Generating {asset['id']}...", flush=True)
        audio_bytes = _request_sound_effect(api_key, asset)
        output_path = _write_candidate(asset, audio_bytes, output_root, plan_path)
        print(f"Wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
