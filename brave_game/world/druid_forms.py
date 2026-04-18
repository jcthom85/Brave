"""Authored druid form helpers."""

DRUID_FORM_DETAILS = {
    "wolf": {
        "name": "Wolf Form",
        "summary": "Swift hunting form built to exploit rooted and exposed targets.",
    },
    "bear": {
        "name": "Bear Form",
        "summary": "Heavy primal form for contesting space and surviving pressure.",
    },
    "crow": {
        "name": "Crow Form",
        "summary": "Light evasive form for sharper control, cleaner spell placement, and quick battlefield reads.",
    },
    "serpent": {
        "name": "Serpent Form",
        "summary": "Low stalking form that turns established control into lingering venom and attrition pressure.",
    },
}


def get_druid_form(form_key):
    """Return one authored druid form entry."""

    return dict(DRUID_FORM_DETAILS.get(str(form_key or "").lower(), {}))
