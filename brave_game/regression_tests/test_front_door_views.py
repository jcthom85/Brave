import os
import sys
import types
import unittest
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda state: (
    "menunode_choose_race"
    if not state.get("race")
    else "menunode_choose_class"
    if not state.get("class")
    else "menunode_choose_name"
    if not state.get("name") or not state.get("gender")
    else "menunode_confirm"
)
chargen_stub.has_chargen_progress = lambda account, *args, **kwargs: bool(getattr(account.db, "brave_chargen", None))
sys.modules["world.chargen"] = chargen_stub

from world.browser_views import build_account_view, build_chargen_view, build_connection_view
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from web.webclient.views import webclient_test_login


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class _DummySessions:
    def __init__(self, connected=False):
        self._connected = connected

    def all(self):
        return [object()] if self._connected else []


class DummyCharacter:
    def __init__(self, key, race="human", char_class="warrior", level=1, location=None):
        self.key = key
        self.id = abs(hash(key)) % 10000 or 1
        self.location = location
        self.db = types.SimpleNamespace(
            brave_race=race,
            brave_class=char_class,
            brave_level=level,
        )
        self.sessions = _DummySessions(False)

    def ensure_brave_character(self):
        return self


class DummyCharacters:
    def __init__(self, characters):
        self._characters = list(characters)

    def all(self):
        return list(self._characters)


class DummyAccount:
    def __init__(self, characters=None, draft=None, last_played=None):
        self.characters = DummyCharacters(characters or [])
        self.db = types.SimpleNamespace(_last_puppet=last_played, brave_chargen=draft)
        self.key = "Tester"

    def get_available_character_slots(self):
        return 2

    def get_character_slots(self):
        return 3


class ConnectionViewTests(unittest.TestCase):
    def test_create_screen_has_password_confirmation_and_error(self):
        view = build_connection_view(
            screen="create",
            error="Password confirmation did not match.",
            username="Aria",
        )

        self.assertEqual("connection", view.get("variant"))
        issue = _section(view, "Issue")
        self.assertIn("Password confirmation did not match.", issue.get("lines", []))
        form = _section(view, "Create Account")
        fields = form.get("fields", [])
        self.assertEqual(["username", "password", "password_confirm"], [field.get("field_name") for field in fields])
        self.assertEqual("Aria", fields[0].get("value"))

    def test_menu_screen_stays_minimal(self):
        view = build_connection_view(screen="menu")

        self.assertEqual("connection", view.get("variant"))
        self.assertEqual([], view.get("chips", []))
        section_labels = [section.get("label") for section in view.get("sections", [])]
        self.assertEqual(["Enter Brave"], section_labels)


class AccountViewTests(unittest.TestCase):
    def test_account_view_keeps_character_row_focused_on_delete(self):
        character = DummyCharacter("Aria")
        account = DummyAccount(characters=[character], last_played=character)

        view = build_account_view(account)

        action_labels = [action.get("label") for action in view.get("actions", [])]
        self.assertEqual([], view.get("chips", []))
        self.assertEqual(["Logout"], action_labels)

        roster = view.get("sections", [])[0]
        entry = next(item for item in roster.get("items", []) if item.get("title") == "Aria")
        self.assertIsNone(entry.get("meta"))
        commands = [action.get("command") for action in entry.get("actions", [])]
        self.assertEqual(["delete 1 --force"], commands)


class ChargenViewTests(unittest.TestCase):
    def test_welcome_step_now_points_to_race_first(self):
        view = build_chargen_view(DummyAccount(), {"step": "menunode_welcome"})

        next_step = _section(view, "Next Step")
        entry = next_step.get("items", [])[0]
        self.assertEqual("Choose Race", entry.get("title"))
        self.assertEqual("Step 1", entry.get("meta"))

    def test_confirm_step_offers_create_and_play(self):
        view = build_chargen_view(
            DummyAccount(),
            {
                "step": "menunode_confirm",
                "name": "Aria",
                "race": "human",
                "class": "warrior",
            },
        )

        action_commands = [action.get("command") for action in view.get("actions", [])]
        self.assertIn("finish play", action_commands)
        ready = _section(view, "Begin Your Journey")
        titles = [entry.get("title") for entry in ready.get("items", [])]
        self.assertIn("Begin Your Journey", titles)
        self.assertNotIn("Fastest Start", [entry.get("meta") for entry in ready.get("items", [])])
        self.assertNotIn(
            "Recommended",
            [chip.get("label") for entry in ready.get("items", []) for chip in entry.get("chips", [])],
        )

    def test_class_step_adds_playstyle_chips_without_extra_guide_card(self):
        view = build_chargen_view(
            DummyAccount(),
            {
                "step": "menunode_choose_class",
                "name": "Aria",
            },
        )

        classes = _section(view, "Classes")
        warrior = next(entry for entry in classes.get("items", []) if entry.get("title") == "Warrior")
        chip_labels = [chip.get("label") for chip in warrior.get("chips", [])]
        self.assertIn("Low upkeep", chip_labels)
        self.assertIn("Frontline anchor", chip_labels)
        section_labels = [section.get("label") for section in view.get("sections", [])]
        self.assertNotIn("Class Picking Guide", section_labels)

    def test_name_step_is_last_before_confirm(self):
        view = build_chargen_view(
            DummyAccount(),
            {
                "step": "menunode_choose_name",
                "race": "human",
                "class": "warrior",
            },
        )

        chip_labels = [chip.get("label") for chip in view.get("chips", [])]
        self.assertIn("Step 4 / 5", chip_labels)
        section_labels = [section.get("label") for section in view.get("sections", [])]
        self.assertNotIn("Gender", section_labels)

    def test_confirm_step_includes_gender_identity(self):
        view = build_chargen_view(
            DummyAccount(),
            {
                "step": "menunode_confirm",
                "name": "Aria",
                "gender": "female",
                "race": "human",
                "class": "warrior",
            },
        )

        highlights = _section(view, "Highlights")
        titles = [entry.get("title") for entry in highlights.get("items", [])]
        self.assertIn("Female", titles)


class WebclientTestLoginViewTests(unittest.TestCase):
    def test_webclient_test_logs_into_jctest_and_redirects(self):
        factory = RequestFactory()
        request = factory.get("/webclient/test")
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save = lambda *args, **kwargs: None
        request.user = types.SimpleNamespace(is_authenticated=False)
        account = types.SimpleNamespace(pk=7)

        with patch("web.webclient.views.AccountDB.objects.get", return_value=account) as get_account:
            with patch("web.webclient.views.login") as login_mock:
                response = webclient_test_login(request)

        get_account.assert_called_once_with(username__iexact="jctest")
        login_mock.assert_called_once()
        self.assertEqual(302, response.status_code)
        self.assertEqual("/webclient/", response.url)


if __name__ == "__main__":
    unittest.main()
