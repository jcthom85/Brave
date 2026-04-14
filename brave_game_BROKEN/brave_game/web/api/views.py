"""JSON creator API for Brave content tooling."""

from __future__ import annotations

import json

from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from commands.brave_creator import (
    list_content_history,
    mutate_content,
    preview_content,
    publish_content,
    remove_content,
    revert_content,
)
from world.content import ContentEditor, get_content_registry
from world.content.registry import reload_content_registry
from world.content.validation import validate_content_registry


DEFAULT_REFERENCE_LIMIT = 50


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
        return [{"id": room.get("id"), "label": room.get("key"), "meta": room.get("zone")} for room in registry.world.rooms]
    if domain == "entities":
        return [{"id": entity.get("id"), "label": entity.get("key"), "meta": entity.get("kind"), "room_id": entity.get("location")} for entity in registry.world.entities]
    if domain == "items":
        return [{"id": template_id, "label": item.get("name"), "meta": item.get("kind")} for template_id, item in registry.items.item_templates.items()]
    if domain == "classes":
        return [{"id": class_id, "label": class_data.get("name"), "meta": class_data.get("role")} for class_id, class_data in registry.characters.classes.items()]
    if domain == "races":
        return [{"id": race_id, "label": race_data.get("name"), "meta": race_data.get("perk")} for race_id, race_data in registry.characters.races.items()]
    if domain == "quests":
        return [{"id": quest_id, "label": quest.get("title"), "meta": registry.quests.get_quest_region(quest_id)} for quest_id, quest in registry.quests.quests.items()]
    if domain == "enemies":
        return [{"id": template_id, "label": template.get("name"), "meta": template.get("xp", 0)} for template_id, template in registry.encounters.enemy_templates.items()]
    if domain == "portals":
        return [{"id": portal_id, "label": portal.get("name"), "meta": portal.get("status")} for portal_id, portal in registry.systems.portals.items()]
    if domain == "forge":
        return [{"id": source_id, "label": (registry.items.get(source_id) or {}).get("name", source_id), "meta": recipe.get("result")} for source_id, recipe in registry.systems.forge_recipes.items()]
    raise KeyError(domain)


def _build_editor():
    return ContentEditor()


@csrf_exempt
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
            "systems": {"source": registry.systems.source_path, "draft": str(editor._path_for("systems", stage="draft")), "portals": len(registry.systems.portals), "forge_recipes": len(registry.systems.forge_recipes)},
        },
    }
    return JsonResponse(payload)


@csrf_exempt
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
    limit = max(1, min(250, int(request.GET.get("limit", DEFAULT_REFERENCE_LIMIT) or DEFAULT_REFERENCE_LIMIT)))
    filtered = [entry for entry in entries if _match_query(entry.get("id"), query) or _match_query(entry.get("label"), query) or _match_query(entry.get("meta"), query)]
    filtered.sort(key=lambda entry: (str(entry.get("label") or ""), str(entry.get("id") or "")))
    return JsonResponse({"ok": True, "domain": domain, "count": len(filtered), "results": filtered[:limit]})


@csrf_exempt
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


@csrf_exempt
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
        stage = payload.get("stage") or "live"
        mutation = mutate_content(kind, target, mutation_payload, write=write, stage=stage, author=_author_from_user(getattr(request, "user", None)))
    except ValueError as exc:
        return _json_error(exc)

    response = {"ok": True, "kind": kind, "domain": mutation.domain, "path": mutation.path, "write": write, "stage": mutation.stage, "diff": mutation.diff, "entry_id": mutation.entry_id, "history_path": mutation.history_path}
    if write and mutation.stage == "live":
        registry = reload_content_registry()
        response["validation_errors"] = validate_content_registry(registry)
    return JsonResponse(response)


@csrf_exempt
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
        stage = payload.get("stage") or "live"
        mutation = remove_content(kind, target, write=write, stage=stage, author=_author_from_user(getattr(request, "user", None)))
    except ValueError as exc:
        return _json_error(exc)

    response = {"ok": True, "kind": kind, "domain": mutation.domain, "path": mutation.path, "write": write, "stage": mutation.stage, "diff": mutation.diff, "entry_id": mutation.entry_id, "history_path": mutation.history_path}
    if write and mutation.stage == "live":
        registry = reload_content_registry()
        response["validation_errors"] = validate_content_registry(registry)
    return JsonResponse(response)


@csrf_exempt
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


@csrf_exempt
def content_revert(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        entry_id = payload.get("entry_id")
        write = bool(payload.get("write"))
        stage = payload.get("stage")
        mutation = revert_content(entry_id, write=write, stage=stage, author=_author_from_user(getattr(request, "user", None)))
    except (ValueError, KeyError) as exc:
        return _json_error(exc)

    response = {"ok": True, "domain": mutation.domain, "path": mutation.path, "write": write, "stage": mutation.stage, "diff": mutation.diff, "entry_id": mutation.entry_id, "history_path": mutation.history_path}
    if write and mutation.stage == "live":
        registry = reload_content_registry()
        response["validation_errors"] = validate_content_registry(registry)
    return JsonResponse(response)


@csrf_exempt
def content_publish(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    try:
        payload = _load_json_body(request)
        mutations = publish_content(payload.get("domain"), author=_author_from_user(getattr(request, "user", None)))
    except ValueError as exc:
        return _json_error(exc)

    registry = reload_content_registry()
    return JsonResponse({
        "ok": True,
        "published": [
            {"domain": mutation.domain, "path": mutation.path, "entry_id": mutation.entry_id, "history_path": mutation.history_path, "diff": mutation.diff}
            for mutation in mutations
        ],
        "validation_errors": validate_content_registry(registry),
    })


@csrf_exempt
def content_validate(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    registry = reload_content_registry()
    errors = validate_content_registry(registry)
    return JsonResponse({"ok": not errors, "errors": errors})


@csrf_exempt
def content_reload(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _is_creator_authorized(getattr(request, "user", None)):
        return _unauthorized_response()

    registry = reload_content_registry()
    return JsonResponse({"ok": True, "sources": {"characters": registry.characters.source_path, "items": registry.items.source_path, "quests": registry.quests.source_path, "world": registry.world.source_path, "encounters": registry.encounters.source_path, "dialogue": registry.dialogue.source_path, "systems": registry.systems.source_path}})
