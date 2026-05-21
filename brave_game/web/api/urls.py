"""API routes for Brave creator tooling."""

from django.urls import path

from . import views

urlpatterns = [
    path("content/status", views.content_status, name="content-status"),
    path("content/health", views.content_health, name="content-health"),
    path("content/drift", views.content_drift, name="content-drift"),
    path("content/reports", views.content_reports, name="content-reports"),
    path("content/references/<str:domain>", views.content_references, name="content-references"),
    path("content/preview", views.content_preview, name="content-preview"),
    path("content/mutate", views.content_mutate, name="content-mutate"),
    path("content/remove", views.content_remove, name="content-remove"),
    path("content/history", views.content_history, name="content-history"),
    path("content/revert", views.content_revert, name="content-revert"),
    path("content/publish", views.content_publish, name="content-publish"),
    path("content/validate", views.content_validate, name="content-validate"),
    path("content/reload", views.content_reload, name="content-reload"),
    path("content/codex/context", views.codex_context, name="content-codex-context"),
    path("content/codex/plan", views.codex_plan, name="content-codex-plan"),
    path("content/codex/apply", views.codex_apply, name="content-codex-apply"),
    path("content/codex/verify", views.codex_verify, name="content-codex-verify"),
    path("content/codex/runs", views.codex_runs, name="content-codex-runs"),
    path("content/codex/runs/<str:run_id>/review", views.codex_run_review, name="content-codex-run-review"),
    path("content/codex/runs/<str:run_id>/publish", views.codex_run_publish, name="content-codex-run-publish"),
    path("content/codex/runs/<str:run_id>", views.codex_run_detail, name="content-codex-run-detail"),
    path("content/codex/inspire", views.codex_inspire, name="content-codex-inspire"),
    path("content/codex/ghost", views.codex_ghost, name="content-codex-ghost"),
]
