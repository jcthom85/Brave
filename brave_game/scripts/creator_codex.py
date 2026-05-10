"""Local Codex-facing wrapper for Brave Creator content tools."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import django


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()


def _load_json(path_or_text):
    text = str(path_or_text)
    if not text.lstrip().startswith(("{", "[")):
        path = Path(text)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(text)


def _print(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def _run_store():
    from world.content.agent_runs import AgentRunStore

    return AgentRunStore()


def _source_from_run(run):
    return json.dumps({"mutations": run.get("mutations") or [], "previews": ((run.get("verify") or {}).get("requested_previews") or [])})


def context_payload():
    from world.content.codex_contract import codex_capabilities
    from world.content.health import creator_health_payload

    return {
        "ok": True,
        "api": "brave-creator-codex",
        "capabilities": codex_capabilities(),
        "health": creator_health_payload(stage="draft"),
    }


def drift_payload():
    from world.content.health import creator_drift_payload

    return creator_drift_payload()


def preview_payload(kind, args):
    from commands.brave_creator import preview_content

    preview = preview_content(kind, args)
    return {"ok": preview is not None, "kind": kind, "args": args, "preview": preview}


def plan_payload(source):
    from web.api.views import _codex_plan_from_payload
    from world.content.codex_contract import codex_capabilities

    return {"ok": True, "plan": _codex_plan_from_payload(_load_json(source)), "capabilities": codex_capabilities()}


def recipes_payload(kind=None):
    from world.content.codex_contract import codex_recipes

    return {"ok": True, "recipes": codex_recipes(kind)}


def validate_payload(source):
    from world.content.codex_contract import suggested_previews_for_mutations, touched_domains_for_mutations, validate_codex_mutations

    payload = _load_json(source)
    mutations = validate_codex_mutations(payload.get("mutations") or [])
    return {
        "ok": True,
        "mutations": mutations,
        "touched_domains": touched_domains_for_mutations(mutations),
        "suggested_previews": suggested_previews_for_mutations(mutations),
    }


def apply_payload(source, *, dry_run=False):
    from commands.brave_creator import mutate_content
    from world.content.codex_contract import codex_recipe_warnings, suggested_previews_for_mutations, touched_domains_for_mutations, validate_codex_mutations
    from world.content.health import creator_health_payload

    payload = _load_json(source)
    try:
        mutations = validate_codex_mutations(payload.get("mutations") or [])
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    results = []
    for entry in mutations:
        kind = entry.get("kind")
        target = entry.get("target", "")
        mutation = mutate_content(
            kind,
            target,
            json.dumps(entry.get("payload")),
            write=not dry_run,
            stage="draft",
            author="codex-cli",
        )
        results.append({
            "kind": kind,
            "domain": mutation.domain,
            "path": mutation.path,
            "write": not dry_run,
            "stage": mutation.stage,
            "diff": mutation.diff,
            "entry_id": mutation.entry_id,
            "history_path": mutation.history_path,
        })
    return {
        "ok": True,
        "stage": "draft",
        "write": not dry_run,
        "applied": results,
        "touched_domains": touched_domains_for_mutations(mutations),
        "suggested_previews": suggested_previews_for_mutations(mutations),
        "recipe_warnings": codex_recipe_warnings(mutations, payload.get("previews") or []),
        "health": None if dry_run else creator_health_payload(stage="draft"),
    }


def verify_payload(source=None):
    from commands.brave_creator import preview_content
    from world.content.health import build_draft_registry, creator_health_payload

    payload = _load_json(source) if source else {}
    registry, _draft_domains = build_draft_registry()
    previews = []
    for entry in payload.get("previews") or []:
        kind = entry.get("kind")
        args = entry.get("args") or []
        preview = preview_content(kind, args, registry=registry)
        previews.append({"kind": kind, "args": args, "found": preview is not None, "preview": preview})
    health = creator_health_payload(stage="draft")
    return {"ok": health["ok"], "stage": "draft", "health": health, "previews": previews}


def run_create_payload(source):
    from web.api.views import _codex_plan_from_payload

    payload = _load_json(source)
    plan = _codex_plan_from_payload(payload) if payload.get("instructions") else {}
    run = _run_store().create(
        instructions=payload.get("instructions") or plan.get("instructions"),
        scope=payload.get("scope") or plan.get("scope") or {},
        mutations=payload.get("mutations") or plan.get("mutations") or [],
        plan=plan,
    )
    return {"ok": True, "run": run}


def run_list_payload(limit=20):
    from world.content.agent_runs import run_summary

    runs = _run_store().list(limit=limit)
    return {"ok": True, "runs": [run_summary(run) for run in runs]}


def run_show_payload(run_id):
    return {"ok": True, "run": _run_store().get(run_id)}


def run_validate_payload(run_id):
    store = _run_store()
    run = store.get(run_id)
    validation = validate_payload(_source_from_run(run))
    updated = store.update(run_id, status="validated", validation=validation, mutations=validation["mutations"])
    return {"ok": True, "run": updated}


def run_dry_run_payload(run_id):
    store = _run_store()
    run = store.get(run_id)
    dry_run = apply_payload(_source_from_run(run), dry_run=True)
    updated = store.update(run_id, status="dry_run", dry_run=dry_run)
    return {"ok": True, "run": updated}


def run_apply_payload(run_id):
    store = _run_store()
    run = store.get(run_id)
    apply = apply_payload(_source_from_run(run), dry_run=False)
    updated = store.update(run_id, status="applied", apply=apply)
    return {"ok": True, "run": updated}


def run_verify_payload(run_id, source=None):
    store = _run_store()
    run = store.get(run_id)
    if source:
        verify_source = source
    else:
        previews = ((run.get("apply") or {}).get("suggested_previews") or (run.get("dry_run") or {}).get("suggested_previews") or (run.get("validation") or {}).get("suggested_previews") or [])
        verify_source = json.dumps({"previews": previews})
    verify = verify_payload(verify_source)
    verify["requested_previews"] = _load_json(verify_source).get("previews") if verify_source else []
    updated = store.update(run_id, status="verified", verify=verify)
    return {"ok": True, "run": updated}


def run_review_payload(run_id, note):
    if not str(note or "").strip():
        raise SystemExit("Review note is required.")
    run = _run_store().append_review_note(run_id, note)
    return {"ok": True, "run": run}


def build_parser():
    parser = argparse.ArgumentParser(description="Use Brave Creator draft tools from Codex CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("context")
    subparsers.add_parser("drift")

    recipes = subparsers.add_parser("recipes")
    recipes.add_argument("kind", nargs="?", help="Optional mutation kind to print.")

    preview = subparsers.add_parser("preview")
    preview.add_argument("kind")
    preview.add_argument("args", nargs="*")

    plan = subparsers.add_parser("plan")
    plan.add_argument("source", help="JSON string or path containing instructions/scope.")

    validate = subparsers.add_parser("validate")
    validate.add_argument("source", help="JSON string or path containing explicit mutations.")

    apply = subparsers.add_parser("apply")
    apply.add_argument("source", help="JSON string or path containing explicit mutations.")
    apply.add_argument("--dry-run", action="store_true")

    verify = subparsers.add_parser("verify")
    verify.add_argument("source", nargs="?", help="Optional JSON string or path with previews.")

    run_create = subparsers.add_parser("run-create")
    run_create.add_argument("source", help="JSON string or path containing instructions/scope/mutations.")

    run_list = subparsers.add_parser("run-list")
    run_list.add_argument("--limit", type=int, default=20)

    run_show = subparsers.add_parser("run-show")
    run_show.add_argument("run_id")

    run_validate = subparsers.add_parser("run-validate")
    run_validate.add_argument("run_id")

    run_dry_run = subparsers.add_parser("run-dry-run")
    run_dry_run.add_argument("run_id")

    run_apply = subparsers.add_parser("run-apply")
    run_apply.add_argument("run_id")

    run_verify = subparsers.add_parser("run-verify")
    run_verify.add_argument("run_id")
    run_verify.add_argument("source", nargs="?", help="Optional JSON string or path with previews.")

    run_review = subparsers.add_parser("run-review")
    run_review.add_argument("run_id")
    run_review.add_argument("--note", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "context":
        _print(context_payload())
    elif args.command == "drift":
        _print(drift_payload())
    elif args.command == "recipes":
        _print(recipes_payload(args.kind))
    elif args.command == "preview":
        _print(preview_payload(args.kind, args.args))
    elif args.command == "plan":
        _print(plan_payload(args.source))
    elif args.command == "validate":
        _print(validate_payload(args.source))
    elif args.command == "apply":
        _print(apply_payload(args.source, dry_run=args.dry_run))
    elif args.command == "verify":
        _print(verify_payload(args.source))
    elif args.command == "run-create":
        _print(run_create_payload(args.source))
    elif args.command == "run-list":
        _print(run_list_payload(limit=args.limit))
    elif args.command == "run-show":
        _print(run_show_payload(args.run_id))
    elif args.command == "run-validate":
        _print(run_validate_payload(args.run_id))
    elif args.command == "run-dry-run":
        _print(run_dry_run_payload(args.run_id))
    elif args.command == "run-apply":
        _print(run_apply_payload(args.run_id))
    elif args.command == "run-verify":
        _print(run_verify_payload(args.run_id, args.source))
    elif args.command == "run-review":
        _print(run_review_payload(args.run_id, args.note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
