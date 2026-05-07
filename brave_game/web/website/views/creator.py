"""Website views for Brave creator tooling."""

from pathlib import Path

from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.template import Context, Template
from django.views.decorators.csrf import ensure_csrf_cookie

from web.api.views import _is_creator_authorized


_TEMPLATE_ROOT = "website/"


def _render_creator_template(request, template_name, context):
    return render(request, f"{_TEMPLATE_ROOT}{template_name}", context)


def _check_creator_access(request):
    """
    Check if the user is authorized for Creator access.
    Returns None if authorized, or a redirect response if not.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return redirect(f"/creator/login/?next={request.path}")
    if not _is_creator_authorized(user):
        username = getattr(user, "username", getattr(user, "key", str(user)))
        response = _render_creator_template(
            request,
            "creator_login.html",
            {
                "page_title": "Brave Creator: Access Required",
                "access_denied": True,
                "current_user": username,
            },
        )
        response.status_code = 403
        return response
    return None


@ensure_csrf_cookie
def creator_login(request):
    """Handle login specifically for the Creator Studio."""
    from django.contrib.auth import logout
    if request.GET.get("logout"):
        logout(request)
        return redirect("/creator/login/")

    user = getattr(request, "user", None)
    next_url = request.GET.get("next", "/creator/")
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect(next_url)
        else:
            error = "Invalid username or password."

    # If already logged in and authorized, just go to the next page
    if user and user.is_authenticated and _is_creator_authorized(user):
        return redirect(next_url)

    current_username = None
    if user and user.is_authenticated:
        current_username = getattr(user, "username", getattr(user, "key", str(user)))

    return _render_creator_template(
        request,
        "creator_login.html",
        {
            "page_title": "Brave Creator: Sign In",
            "next": next_url,
            "error": error,
            "access_denied": user.is_authenticated if user else False,
            "current_user": current_username,
        },
    )


@ensure_csrf_cookie
def creator_index(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_index.html",
        {
            "api_root": "/api/content",
            "page_title": "Brave Creator",
        },
    )


@ensure_csrf_cookie
def creator_world_editor(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_world_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "rooms",
            "page_title": "Brave Creator: World Builder",
        },
    )


@ensure_csrf_cookie
def creator_quest_editor(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_quest_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "quests",
            "page_title": "Brave Creator: Quest Builder",
        },
    )


@ensure_csrf_cookie
def creator_dialogue_editor(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_dialogue_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "entities",
            "page_title": "Brave Creator: Dialogue Builder",
        },
    )


@ensure_csrf_cookie
def creator_encounter_editor(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_encounter_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "encounters",
            "page_title": "Brave Creator: Encounter Builder",
        },
    )


@ensure_csrf_cookie
def creator_item_editor(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_item_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "items",
            "page_title": "Brave Creator: Item Builder",
        },
    )


@ensure_csrf_cookie
def creator_character_editor(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_character_editor.html",
        {
            "api_root": "/api/content",
            "reference_domain": "classes",
            "page_title": "Brave Creator: Character Builder",
        },
    )


@ensure_csrf_cookie
def creator_systems_editor(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_systems_editor.html",
        {
            "api_root": "/api/content",
            "page_title": "Brave Creator: Systems Builder",
        },
    )


@ensure_csrf_cookie
def creator_boss_composer(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_boss_composer.html",
        {
            "api_root": "/api/content",
            "page_title": "Brave Creator: Boss Composer",
        },
    )


@ensure_csrf_cookie
def creator_recipe_composer(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_recipe_composer.html",
        {
            "api_root": "/api/content",
            "page_title": "Brave Creator: Recipe Composer",
        },
    )


@ensure_csrf_cookie
def creator_fishing_composer(request):
    access_redirect = _check_creator_access(request)
    if access_redirect:
        return access_redirect

    return _render_creator_template(
        request,
        "creator_fishing_composer.html",
        {
            "api_root": "/api/content",
            "page_title": "Brave Creator: Fishing Composer",
        },
    )
