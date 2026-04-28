"""Website views for Brave creator tooling."""

from pathlib import Path

from django.http import HttpResponse, HttpResponseForbidden
from django.template import Context, Template

from web.api.views import _is_creator_authorized


_TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "templates" / "website"


def _render_creator_template(template_name, context):
    template = Template((_TEMPLATE_ROOT / template_name).read_text(encoding="utf-8"))
    return HttpResponse(template.render(Context(context)))


def creator_index(request):
    user = getattr(request, "user", None)
    if not _is_creator_authorized(user):
        return HttpResponseForbidden("Creator access required.")

    return _render_creator_template(
        "creator_index.html",
        {
            "api_root": "/api/content",
            "page_title": "Brave Creator",
        },
    )


def creator_world_editor(request):
    user = getattr(request, "user", None)
    if not _is_creator_authorized(user):
        return HttpResponseForbidden("Creator access required.")

    return _render_creator_template(
        "creator_world_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "rooms",
            "page_title": "Brave Creator: World Builder",
        },
    )


def creator_quest_editor(request):
    user = getattr(request, "user", None)
    if not _is_creator_authorized(user):
        return HttpResponseForbidden("Creator access required.")

    return _render_creator_template(
        "creator_quest_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "quests",
            "page_title": "Brave Creator: Quest Builder",
        },
    )


def creator_dialogue_editor(request):
    user = getattr(request, "user", None)
    if not _is_creator_authorized(user):
        return HttpResponseForbidden("Creator access required.")

    return _render_creator_template(
        "creator_dialogue_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "entities",
            "page_title": "Brave Creator: Dialogue Builder",
        },
    )


def creator_encounter_editor(request):
    user = getattr(request, "user", None)
    if not _is_creator_authorized(user):
        return HttpResponseForbidden("Creator access required.")

    return _render_creator_template(
        "creator_encounter_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "encounters",
            "page_title": "Brave Creator: Encounter Builder",
        },
    )


def creator_item_editor(request):
    user = getattr(request, "user", None)
    if not _is_creator_authorized(user):
        return HttpResponseForbidden("Creator access required.")

    return _render_creator_template(
        "creator_item_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "items",
            "page_title": "Brave Creator: Item Builder",
        },
    )


def creator_character_editor(request):
    user = getattr(request, "user", None)
    if not _is_creator_authorized(user):
        return HttpResponseForbidden("Creator access required.")

    return _render_creator_template(
        "creator_character_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "classes",
            "page_title": "Brave Creator: Character Builder",
        },
    )
