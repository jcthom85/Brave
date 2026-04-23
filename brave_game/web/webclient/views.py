"""Custom Brave webclient entrypoints."""

from django.conf import settings
from django.contrib.auth import login, logout
from django.http import Http404
from django.shortcuts import redirect

from evennia.accounts.models import AccountDB


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
