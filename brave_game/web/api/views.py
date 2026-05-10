"""JSON creator API for Brave content tooling."""

from __future__ import annotations

import json
from pathlib import Path

from django.http import HttpResponseNotAllowed, JsonResponse

from commands.brave_creator import (
    list_content_history,
    mutate_content,
    preview_content,
    publish_content,
    remove_content,
    revert_content,
)
from world.content import ContentEditor, ContentPublishValidationError, get_content_registry
from world.content.agent_runs import AgentRunStore, run_summary
from world.content.codex_contract import (
    MUTATION_KINDS as CODEX_MUTATION_KINDS,
    REFERENCE_DOMAINS as CODEX_REFERENCE_DOMAINS,
    codex_capabilities,
    codex_recipe_warnings,
    suggested_previews_for_mutations,
    touched_domains_for_mutations,
    validate_codex_mutations,
)
from world.content.health import build_draft_registry, creator_drift_payload, creator_health_payload
from world.content.registry import build_content_registry_from_payloads, reload_content_registry
from world.content.validation import validate_content_registry


DEFAULT_REFERENCE_LIMIT = 50
CODEX_PUBLISH_DOMAIN_ORDER = ("world", "items", "quests", "encounters", "dialogue", "characters", "systems")


def _has_evennia_permission(user, permstring):
    checker = getattr(user, "check_permstring", None)
    if not callable(checker):
        return False
    try:
        return bool(checker(permstring))
    except Exception:
        return False


def _is_creator_authorized(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    return _has_evennia_permission(user, "Developer")


def _author_from_user(user):
    if not user:
        return "system"
    getter = getattr(user, "get_username", None)
    if callable(getter):
        value = getter()
        if value:
            return value
    for attr in ("username", "key", "name"):
        value = getattr(user, attr, None)
        if value:
            return str(value)
    return "system"


def _unauthorized_response():
    return JsonResponse(
        {
            "ok": False,
            "error": "Creator access required. Use a staff, superuser, or Developer-authorized account.",
        },
        status=403,
    )


def _json_error(message, *, status=400):
    return JsonResponse({"ok": False, "error": str(message)}, status=status)


def _load_json_body(request):
    try:
        raw = request.body.decode("utf-8") if request.body else "{}"
        return json.loads(raw or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc


def _match_query(value, query):
    if not query:
        return True
    token = str(query).strip().lower()
    return token in str(value or "").lower()


def _reference_entries(domain, registry):
    if domain == "rooms":
        return [
            {
                "id": room.get("id"),
                "label": room.get("key"),
                "meta": room.get("zone"),
                "zone": room.get("zone"),
                "map_region": room.get("map_region") or room.get("zone"),
                "map_x": room.get("map_x", 0),
                "map_y": room.get("map_y", 0),
            }
            for room in registry.world.rooms
        ]
    if domain == "exits":
        return [
            {
                "id": exit_data.get("id"),
                "label": exit_data.get("key"),
                "meta": f"{exit_data.get('source')} -> {exit_data.get('destination')}",
                "key": exit_data.get("key"),
                "source": exit_data.get("source"),
                "destination": exit_data.get("destination"),
            }
            for exit_data in registry.world.exits
        ]
    if domain == "entities":
        return [{"id": entity.get("id"), "label": entity.get("key"), "meta": entity.get("kind"), "room_id": entity.get("location")} for entity in registry.world.entities]
    if domain == "items":
        return [{"id": template_id, "label": item.get("name"), "meta": item.get("kind"), "rarity": item.get("rarity", "common")} for template_id, item in registry.items.item_templates.items()]
    if domain == "classes":
        return [{"id": class_id, "label": class_data.get("name"), "meta": class_data.get("role")} for class_id, class_data in registry.characters.classes.items()]
    if domain == "races":
        return [{"id": race_id, "label": race_data.get("name"), "meta": race_data.get("perk")} for race_id, race_data in registry.characters.races.items()]
    if domain == "quests":
        starting = set(registry.quests.starting_quests)
        return [
            {
                "id": quest_id,
                "label": quest.get("title"),
                "meta": registry.quests.get_quest_region(quest_id),
                "region": registry.quests.get_quest_region(quest_id),
                "starting": quest_id in starting,
                "objective_count": len(quest.get("objectives", [])),
                "reward_count": len(quest.get("rewards", {}).get("items", [])),
            }
            for quest_id, quest in registry.quests.quests.items()
        ]
    if domain == "enemies":
        return [{"id": template_id, "label": template.get("name"), "meta": template.get("xp", 0)} for template_id, template in registry.encounters.enemy_templates.items()]
    if domain == "enemy-tags":
        tags = {}
        for template_id, template in registry.encounters.enemy_templates.items():
            for tag in template.get("tags", []):
                tag_key = str(tag or "").strip().lower()
                if not tag_key:
                    continue
                tags[tag_key] = tags.get(tag_key, 0) + 1
        return [{"id": tag, "label": tag.replace("_", " ").title(), "meta": count} for tag, count in tags.items()]
    if domain == "roaming-parties":
        return [
            {
                "id": party_key,
                "label": (party.get("encounter") or {}).get("title") or party_key,
                "meta": party.get("region"),
                "region": party.get("region"),
                "start_room": party.get("start_room"),
                "interval": party.get("interval", 0),
                "respawn_delay": party.get("respawn_delay", 0),
            }
            for party_key, party in registry.encounters.roaming_parties.items()
        ]
    if domain == "portals":
        return [{"id": portal_id, "label": portal.get("name"), "meta": portal.get("status")} for portal_id, portal in registry.systems.portals.items()]
    if domain == "forge":
        return [{"id": source_id, "label": (registry.items.get(source_id) or {}).get("name", source_id), "meta": recipe.get("result")} for source_id, recipe in registry.systems.forge_recipes.items()]
    if domain == "cooking-recipes":
        return [{"id": recipe_id, "label": recipe.get("name"), "meta": recipe.get("result")} for recipe_id, recipe in registry.systems.cooking_recipes.items()]
    if domain == "tinkering-recipes":
        return [{"id": recipe_id, "label": recipe.get("name"), "meta": recipe.get("result")} for recipe_id, recipe in registry.systems.tinkering_recipes.items()]
    if domain == "fishing-spots":
        return [
            {
                "id": room_id,
                "label": spot.get("name") or (registry.world.get_room(room_id) or {}).get("key"),
                "meta": f"{len(spot.get('fish', []))} fish",
                "room_id": room_id,
            }
            for room_id, spot in registry.systems.fishing_spots.items()
        ]
    if domain == "fishing-rods":
        return [{"id": rod_id, "label": rod.get("name"), "meta": rod.get("power", 0)} for rod_id, rod in registry.systems.fishing_rods.items()]
    if domain == "fishing-lures":
        return [{"id": lure_id, "label": lure.get("name"), "meta": len(lure.get("attracts", []))} for lure_id, lure in registry.systems.fishing_lures.items()]
    if domain == "fish-behaviors":
        return [{"id": behavior_id, "label": behavior_id.replace("_", " ").title(), "meta": behavior.get("pattern")} for behavior_id, behavior in registry.systems.fishing_behaviors.items()]
    if domain == "boss-gates":
        return [{"id": gate_id, "label": gate.get("name"), "meta": gate.get("trigger_room_id")} for gate_id, gate in registry.systems.boss_gates.items()]
    if domain == "trophies":
        return [{"id": trophy_id, "label": trophy.get("name"), "meta": trophy.get("world")} for trophy_id, trophy in registry.systems.trophies.items()]
    if domain == "shops":
        return [
            {
                "id": shop_id,
                "label": shop.get("name"),
                "meta": shop.get("room_id"),
                "room_id": shop.get("room_id"),
                "keeper_entity_id": shop.get("keeper_entity_id"),
                "stock_count": len(shop.get("stock", []) or []),
            }
            for shop_id, shop in registry.systems.shops.items()
        ]
    if domain == "atmosphere-profiles":
        from world.room_atmosphere import list_atmosphere_profiles

        return [
            {
                "id": profile["id"],
                "label": profile["label"],
                "meta": f"{profile['intensity']} · {', '.join(profile['layers'])}".strip(" ·"),
                "intensity": profile["intensity"],
                "layers": profile["layers"],
            }
            for profile in list_atmosphere_profiles()
        ]
    raise KeyError(domain)


def _build_editor():
    return ContentEditor()


def _mutation_payload(mutation, *, kind=None, write=None):
    return {
        "kind": kind,
        "domain": mutation.domain,
        "path": mutation.path,
        "write": write,
        "stage": mutation.stage,
        "diff": mutation.diff,
        "entry_id": mutation.entry_id,
        "history_path": mutation.history_path,
    }


def _publish_payload(mutations):
    registry = reload_content_registry()
    return {
        "ok": True,
        "published": [
            {"domain": mutation.domain, "path": mutation.path, "entry_id": mutation.entry_id, "history_path": mutation.history_path, "diff": mutation.diff}
            for mutation in mutations
        ],
        "validation_errors": validate_content_registry(registry),
    }


def _codex_run_publish_domains(run, requested_domains=None):
    domains = requested_domains or run_summary(run).get("touched_domains") or []
    normalized = []
    for domain in domains:
        value = str(domain or "").strip().lower()
        if value and value not in normalized:
            normalized.append(value)
    return sorted(normalized, key=lambda value: CODEX_PUBLISH_DOMAIN_ORDER.index(value) if value in CODEX_PUBLISH_DOMAIN_ORDER else len(CODEX_PUBLISH_DOMAIN_ORDER))


def _codex_capabilities():
    return codex_capabilities()


def _codex_plan_from_payload(payload):
    instructions = str(payload.get("instructions") or "").strip()
    scope = payload.get("scope") or {}
    domains = scope.get("domains") or []
    if not isinstance(domains, list):
        domains = []
    if not instructions:
        raise ValueError("Codex plan requires instructions.")
    return {
        "instructions": instructions,
        "scope": {"domains": [str(domain) for domain in domains]},
        "write": False,
        "required_review": True,
        "mutations": [],
        "notes": [
            "This endpoint returns a review scaffold only; build explicit mutations before applying.",
            "Use /api/content/codex/context and previews/references to ground target ids before applying.",
            "Use /api/content/codex/apply with explicit mutations to write draft packs.",
        ],
        "next_steps": [
            "Inspect references and previews for affected content.",
            "Create explicit mutation entries with kind, target, and payload.",
            "Apply to draft, then verify draft validation/readiness.",
        ],
    }


def _codex_preview_entries(entries):
    previews = []
    registry, _draft_domains = build_draft_registry()
    for entry in entries or []:
        kind = entry.get("kind")
        args = entry.get("args") or []
        preview = preview_content(kind, args, registry=registry)
        previews.append({"kind": kind, "args": args, "found": preview is not None, "preview": preview})
    return previews


def content_status(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    registry = get_content_registry()
    editor = _build_editor()
    payload = {
        "ok": True,
        "domains": {
            "characters": {"source": registry.characters.source_path, "draft": str(editor._path_for("characters", stage="draft")), "races": len(registry.characters.races), "classes": len(registry.characters.classes)},
            "items": {"source": registry.items.source_path, "draft": str(editor._path_for("items", stage="draft")), "items": len(registry.items.item_templates)},
            "quests": {"source": registry.quests.source_path, "draft": str(editor._path_for("quests", stage="draft")), "quests": len(registry.quests.quests)},
            "world": {"source": registry.world.source_path, "draft": str(editor._path_for("world", stage="draft")), "rooms": len(registry.world.rooms), "entities": len(registry.world.entities), "exits": len(registry.world.exits)},
            "encounters": {"source": registry.encounters.source_path, "draft": str(editor._path_for("encounters", stage="draft")), "enemies": len(registry.encounters.enemy_templates), "rooms": len(registry.encounters.room_encounters)},
            "dialogue": {"source": registry.dialogue.source_path, "draft": str(editor._path_for("dialogue", stage="draft")), "talk_entities": len(registry.dialogue.talk_rules), "readables": len(registry.dialogue.static_read_responses)},
            "systems": {
                "source": registry.systems.source_path,
                "draft": str(editor._path_for("systems", stage="draft")),
                "portals": len(registry.systems.portals),
                "forge_recipes": len(registry.systems.forge_recipes),
                "cooking_recipes": len(registry.systems.cooking_recipes),
                "tinkering_recipes": len(registry.systems.tinkering_recipes),
                "fishing_spots": len(registry.systems.fishing_spots),
                "fishing_rods": len(registry.systems.fishing_rods),
                "fishing_lures": len(registry.systems.fishing_lures),
                "fish_behaviors": len(registry.systems.fishing_behaviors),
                "boss_gates": len(registry.systems.boss_gates),
                "trophies": len(registry.systems.trophies),
                "shops": len(registry.systems.shops),
            },
        },
    }
    return JsonResponse(payload)


def content_health(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    stage = str(request.GET.get("stage") or "draft").strip().lower()
    if stage not in {"draft", "live"}:
        return _json_error(f"Unknown health stage: {stage}")
    return JsonResponse(creator_health_payload(stage=stage))


def content_drift(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    return JsonResponse(creator_drift_payload())


def content_reports(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    report_root = Path(__file__).resolve().parents[3] / "tmp" / "combat-simulation"
    reports = []
    for key, filename, label in (
        ("act1_spine", "act1_spine.md", "Act 1 Spine"),
        ("prose_voice", "prose_voice.md", "Prose and Voice"),
        ("item_rarity", "item_rarity.md", "Item Rarity"),
        ("combat_summary", "summary.md", "Combat Summary"),
        ("resource_economy", "resource_economy.md", "Resource Economy"),
    ):
        path = report_root / filename
        exists = path.exists()
        reports.append(
            {
                "key": key,
                "label": label,
                "path": str(path),
                "exists": exists,
                "modified_at": path.stat().st_mtime if exists else None,
                "content": path.read_text(encoding="utf-8")[:12000] if exists else "",
            }
        )
    return JsonResponse({"ok": True, "reports": reports})


def content_references(request, domain):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    registry = get_content_registry()
    try:
        entries = _reference_entries(domain, registry)
    except KeyError:
        return _json_error(f"Unknown reference domain: {domain}", status=404)

    query = request.GET.get("q", "")
    limit = max(1, min(1000, int(request.GET.get("limit", DEFAULT_REFERENCE_LIMIT) or DEFAULT_REFERENCE_LIMIT)))
    filtered = [entry for entry in entries if _match_query(entry.get("id"), query) or _match_query(entry.get("label"), query) or _match_query(entry.get("meta"), query) or _match_query(entry.get("rarity"), query)]
    filtered.sort(key=lambda entry: (str(entry.get("label") or ""), str(entry.get("id") or "")))
    return JsonResponse({"ok": True, "domain": domain, "count": len(filtered), "results": filtered[:limit]})


def content_preview(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        kind = payload.get("kind")
        args = payload.get("args") or []
        preview = preview_content(kind, args, registry=get_content_registry())
    except ValueError as exc:
        return _json_error(exc)

    if preview is None:
        return _json_error("Preview target not found.", status=404)
    return JsonResponse({"ok": True, "kind": kind, "preview": preview})


def content_mutate(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        kind = payload.get("kind")
        target = payload.get("target", "")
        mutation_payload = json.dumps(payload.get("payload"))
        write = bool(payload.get("write"))
        stage = payload.get("stage") or "draft"
        mutation = mutate_content(kind, target, mutation_payload, write=write, stage=stage, author=_author_from_user(getattr(request, "user", None)))
    except ValueError as exc:
        return _json_error(exc)

    response = {"ok": True, "kind": kind, "domain": mutation.domain, "path": mutation.path, "write": write, "stage": mutation.stage, "diff": mutation.diff, "entry_id": mutation.entry_id, "history_path": mutation.history_path}
    if write and mutation.stage == "live":
        registry = reload_content_registry()
        response["validation_errors"] = validate_content_registry(registry)
    return JsonResponse(response)


def content_remove(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        kind = payload.get("kind")
        target = payload.get("target", "")
        write = bool(payload.get("write"))
        stage = payload.get("stage") or "draft"
        mutation = remove_content(kind, target, write=write, stage=stage, author=_author_from_user(getattr(request, "user", None)))
    except ValueError as exc:
        return _json_error(exc)

    response = {"ok": True, "kind": kind, "domain": mutation.domain, "path": mutation.path, "write": write, "stage": mutation.stage, "diff": mutation.diff, "entry_id": mutation.entry_id, "history_path": mutation.history_path}
    if write and mutation.stage == "live":
        registry = reload_content_registry()
        response["validation_errors"] = validate_content_registry(registry)
    return JsonResponse(response)


def content_history(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    domain = request.GET.get("domain") or None
    stage = request.GET.get("stage") or None
    limit = max(1, min(100, int(request.GET.get("limit", 20) or 20)))
    try:
        entries = list_content_history(domain=domain, stage=stage, limit=limit)
    except ValueError as exc:
        return _json_error(exc)
    return JsonResponse({"ok": True, "entries": entries})


def content_revert(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        entry_id = payload.get("entry_id")
        write = bool(payload.get("write"))
        stage = payload.get("stage") or "draft"
        mutation = revert_content(entry_id, write=write, stage=stage, author=_author_from_user(getattr(request, "user", None)))
    except (ValueError, KeyError) as exc:
        return _json_error(exc)

    response = {"ok": True, "domain": mutation.domain, "path": mutation.path, "write": write, "stage": mutation.stage, "diff": mutation.diff, "entry_id": mutation.entry_id, "history_path": mutation.history_path}
    if write and mutation.stage == "live":
        registry = reload_content_registry()
        response["validation_errors"] = validate_content_registry(registry)
    return JsonResponse(response)


def content_publish(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        mutations = publish_content(payload.get("domain"), author=_author_from_user(getattr(request, "user", None)))
    except ContentPublishValidationError as exc:
        return JsonResponse(
            {
                "ok": False,
                "published": [],
                "validation_errors": exc.errors,
                "domains": exc.domains,
                "error": "Draft content failed validation. Nothing was published.",
            },
            status=400,
        )
    except ValueError as exc:
        return _json_error(exc)

    return JsonResponse(_publish_payload(mutations))


def content_validate(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
    except ValueError as exc:
        return _json_error(exc)
    stage = str(payload.get("stage") or "live").strip().lower()
    if stage == "draft":
        editor = _build_editor()
        payloads = {}
        source_paths = {}
        for domain in editor.pack_paths:
            draft_path = editor._path_for(domain, stage="draft")
            live_path = editor._path_for(domain, stage="live")
            source_path = draft_path if draft_path.exists() else live_path
            with source_path.open("r", encoding="utf-8") as handle:
                payloads[domain] = json.load(handle)
            source_paths[domain] = source_path
        registry = build_content_registry_from_payloads(payloads, source_paths=source_paths)
    else:
        registry = reload_content_registry()
    errors = validate_content_registry(registry)
    return JsonResponse({"ok": not errors, "stage": stage, "errors": errors})


def content_reload(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    registry = reload_content_registry()
    return JsonResponse({"ok": True, "sources": {"characters": registry.characters.source_path, "items": registry.items.source_path, "quests": registry.quests.source_path, "world": registry.world.source_path, "encounters": registry.encounters.source_path, "dialogue": registry.dialogue.source_path, "systems": registry.systems.source_path}})


def codex_context(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    return JsonResponse({
        "ok": True,
        "api": "brave-creator-codex",
        "capabilities": _codex_capabilities(),
        "health": creator_health_payload(stage="draft"),
        "status_url": "/api/content/status",
        "verify_url": "/api/content/codex/verify",
    })


def codex_plan(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        plan = _codex_plan_from_payload(payload)
    except ValueError as exc:
        return _json_error(exc)
    return JsonResponse({"ok": True, "plan": plan, "capabilities": _codex_capabilities()})


def codex_apply(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        dry_run = bool(payload.get("dry_run"))
        stage = str(payload.get("stage") or "draft").strip().lower()
        if stage != "draft":
            raise ValueError("Codex apply only supports draft stage.")
        mutations = validate_codex_mutations(payload.get("mutations") or [])
        author = _author_from_user(getattr(request, "user", None))
        results = []
        for index, entry in enumerate(mutations, start=1):
            kind = entry.get("kind")
            target = entry.get("target", "")
            mutation = mutate_content(kind, target, json.dumps(entry.get("payload")), write=not dry_run, stage="draft", author=author)
            results.append(_mutation_payload(mutation, kind=kind, write=not dry_run))
    except ValueError as exc:
        return _json_error(exc)

    response_payload = {
        "ok": True,
        "stage": "draft",
        "write": not dry_run,
        "applied": results,
        "touched_domains": touched_domains_for_mutations(mutations),
        "suggested_previews": suggested_previews_for_mutations(mutations),
        "recipe_warnings": codex_recipe_warnings(mutations, payload.get("previews") or []),
        "health": creator_health_payload(stage="draft") if not dry_run else None,
    }
    run_id = str(payload.get("run_id") or "").strip()
    if run_id:
        try:
            field = "dry_run" if dry_run else "apply"
            status = "dry_run" if dry_run else "applied"
            AgentRunStore().update(run_id, status=status, **{field: response_payload})
            response_payload["run_id"] = run_id
        except (KeyError, ValueError) as exc:
            return _json_error(exc, status=404)
    return JsonResponse(response_payload)


def codex_verify(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        previews = _codex_preview_entries(payload.get("previews") or [])
    except ValueError as exc:
        return _json_error(exc)
    health = creator_health_payload(stage="draft")
    response_payload = {
        "ok": health["ok"],
        "stage": "draft",
        "health": health,
        "previews": previews,
    }
    run_id = str(payload.get("run_id") or "").strip()
    if run_id:
        try:
            verify_payload = dict(response_payload)
            verify_payload["requested_previews"] = payload.get("previews") or []
            AgentRunStore().update(run_id, status="verified", verify=verify_payload)
            response_payload["run_id"] = run_id
        except (KeyError, ValueError) as exc:
            return _json_error(exc, status=404)
    return JsonResponse(response_payload)


def codex_runs(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        limit = max(1, min(100, int(request.GET.get("limit", 20) or 20)))
        runs = AgentRunStore().list(limit=limit)
    except ValueError as exc:
        return _json_error(exc)
    return JsonResponse({"ok": True, "runs": [run_summary(run) for run in runs]})


def codex_run_detail(request, run_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        run = AgentRunStore().get(run_id)
    except KeyError as exc:
        return _json_error(exc, status=404)
    return JsonResponse({"ok": True, "run": run})


def codex_run_review(request, run_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        note = str(payload.get("note") or "").strip()
        if not note:
            raise ValueError("Review note is required.")
        run = AgentRunStore().append_review_note(run_id, note, author=_author_from_user(getattr(request, "user", None)))
    except KeyError as exc:
        return _json_error(exc, status=404)
    except ValueError as exc:
        return _json_error(exc)
    return JsonResponse({"ok": True, "run": run})


def codex_run_publish(request, run_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    store = AgentRunStore()
    try:
        payload = _load_json_body(request)
        run = store.get(run_id)
        domains = _codex_run_publish_domains(run, payload.get("domains") or None)
        if not domains:
            raise ValueError("Agent run has no touched draft domains to publish.")
        publish_result = _publish_payload(publish_content(domains, author=_author_from_user(getattr(request, "user", None))))
        run = store.update(run_id, status="published", publish={**publish_result, "domains": domains})
    except ContentPublishValidationError as exc:
        publish_result = {
            "ok": False,
            "published": [],
            "validation_errors": exc.errors,
            "domains": exc.domains,
            "error": "Draft content failed validation. Nothing was published.",
        }
        try:
            run = store.update(run_id, status="publish_blocked", publish=publish_result)
        except (KeyError, ValueError):
            run = None
        return JsonResponse({**publish_result, "run": run}, status=400)
    except KeyError as exc:
        return _json_error(exc, status=404)
    except ValueError as exc:
        return _json_error(exc)
    return JsonResponse({**publish_result, "run": run})
