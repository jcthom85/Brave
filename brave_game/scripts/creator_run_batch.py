"""Run a Brave Creator Codex payload through the Agent Run workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import creator_codex


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create, validate, dry-run, apply, and verify a Creator Agent Run."
    )
    parser.add_argument("source", help="JSON string or path containing instructions/scope/mutations/previews.")
    parser.add_argument("--review-note", help="Optional note to mark the run reviewed after verification.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    creator_codex._print(creator_codex.run_batch_payload(args.source, review_note=args.review_note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
