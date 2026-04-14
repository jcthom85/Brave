"""API routes for Brave creator tooling."""

from django.urls import path

from . import views

urlpatterns = [
    path("content/status", views.content_status, name="content-status"),
    path("content/references/<str:domain>", views.content_references, name="content-references"),
    path("content/preview", views.content_preview, name="content-preview"),
    path("content/mutate", views.content_mutate, name="content-mutate"),
    path("content/remove", views.content_remove, name="content-remove"),
    path("content/history", views.content_history, name="content-history"),
    path("content/revert", views.content_revert, name="content-revert"),
    path("content/publish", views.content_publish, name="content-publish"),
    path("content/validate", views.content_validate, name="content-validate"),
    path("content/reload", views.content_reload, name="content-reload"),
]
