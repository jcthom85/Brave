"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls starting with `webclient/`
(the `webclient/` part should not be included again here).

"""

from django.urls import path

from evennia.web.webclient.urls import urlpatterns as evennia_webclient_urlpatterns
from .views import webclient_test_login

# add patterns here
urlpatterns = [
    path("test", webclient_test_login),
]

# read by Django
urlpatterns = urlpatterns + evennia_webclient_urlpatterns
