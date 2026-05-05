"""Custom Brave webclient entrypoints."""

from django.conf import settings
from django.contrib.auth import login, logout
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from evennia.accounts.models import AccountDB


@csrf_exempt
@require_POST
def webclient_logout(request):
    """Clear browser authentication after the in-game logout command."""

    logout(request)
    response = JsonResponse({"ok": True})
    response["Cache-Control"] = "no-store"
    return response


def webclient_test_login(request):
    """Log into the test account and continue into the normal webclient."""

    if not settings.WEBCLIENT_ENABLED:
        raise Http404

    try:
        account = AccountDB.objects.get(username__iexact="jctest")
    except AccountDB.DoesNotExist as exc:
        raise Http404("Test account is not configured.") from exc

    current_user = getattr(request, "user", None)
    if getattr(current_user, "is_authenticated", False) and current_user.pk != account.pk:
        logout(request)

    backend = settings.AUTHENTICATION_BACKENDS[0]
    login(request, account, backend=backend)
    request.session.save()
    return redirect("/webclient/")
