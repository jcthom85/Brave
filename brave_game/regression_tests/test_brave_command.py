import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.brave import BraveCharacterCommand
from commands.brave_explore import CmdRest
from commands.brave_town import CmdMovie
from world.browser_panels import format_speech_activity
from world.browser_room_helpers import _format_room_context_action_items
from world.movies import GREAT_FRONTIER_MOVIES, build_movie_picker, build_movie_view, resolve_movie


class _DummySessions:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def get(self):
        return list(self._sessions)


class BraveCharacterCommandTests(unittest.TestCase):
    def test_format_speech_activity_matches_room_voice_parser(self):
        self.assertEqual(
            'Captain Harl Rowan says, "Talk to me."',
            format_speech_activity("Captain Harl Rowan", "Talk to me."),
        )

    def test_send_room_emote_uses_gendered_head_phrase(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        character = SimpleNamespace(key="Jackson", location=room, db=SimpleNamespace(brave_gender="male"))
        character.ensure_brave_character = lambda: character
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        recorded = []
        from world import browser_panels
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None: recorded.append((location, line, exclude, cls))
        try:
            ok = command.send_room_emote("shake head")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertEqual("Jackson shakes his head.", recorded[0][1])
        self.assertEqual(("You shake your head.",), sent[0]["args"])

    def test_send_room_emote_uses_their_for_nonbinary_character(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        character = SimpleNamespace(key="Ash", location=room, db=SimpleNamespace(brave_gender="nonbinary"))
        character.ensure_brave_character = lambda: character
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        from world import browser_panels
        recorded = []
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None: recorded.append((location, line, exclude, cls))
        try:
            ok = command.send_room_emote("shrug")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertEqual("Ash shrugs their shoulders.", recorded[0][1])
        self.assertEqual(("You shrug.",), sent[0]["args"])

    def test_send_room_emote_targets_present_npc(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        npc = SimpleNamespace(
            key="Uncle Pib Underbough",
            db=SimpleNamespace(brave_entity_kind="npc", brave_entity_id="uncle_pib_underbough"),
        )
        character = SimpleNamespace(key="Ash", location=room, db=SimpleNamespace(brave_gender="nonbinary"))
        character.ensure_brave_character = lambda: character
        character.location = SimpleNamespace(contents=[character, npc])
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        from world import browser_panels

        recorded = []
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None, category=None: recorded.append((location, line, exclude, cls, category))
        try:
            ok = command.send_room_emote("smiles at Uncle Pib Underbough")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertTrue(any("Ash smiles at Uncle Pib Underbough." == line for _location, line, _exclude, _cls, _category in recorded))
        self.assertEqual(("You smile at Uncle Pib Underbough.",), sent[0]["args"])

    def test_send_room_emote_can_target_enemy_in_combat(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(BraveCharacterCommand)
        room = object()
        enemy = {"id": "e1", "key": "Bandit Raider", "template_key": "bandit_raider", "hp": 12, "max_hp": 12}
        encounter = SimpleNamespace(
            is_participant=lambda _character: True,
            get_active_enemies=lambda: [enemy],
            react_to_emote=lambda _character, _enemy, _text: "The bandit raider spits back a dirty glare.",
        )
        character = SimpleNamespace(key="Ash", location=room, db=SimpleNamespace(brave_gender="nonbinary"))
        character.ensure_brave_character = lambda: character
        character.get_active_encounter = lambda: encounter
        command.session = web_session
        command.caller = character

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        from world import browser_panels

        recorded = []
        original = browser_panels.broadcast_room_activity
        browser_panels.broadcast_room_activity = lambda location, line, exclude=None, cls=None, category=None: recorded.append((location, line, exclude, cls, category))
        try:
            ok = command.send_room_emote("taunts the Bandit Raider")
        finally:
            browser_panels.broadcast_room_activity = original

        self.assertTrue(ok)
        self.assertTrue(any("The bandit raider spits back a dirty glare." == line for _location, line, _exclude, _cls, _category in recorded))
        self.assertTrue(any("Ash taunts the Bandit Raider." == line for _location, line, _exclude, _cls, _category in recorded))
        self.assertEqual(("You taunt the Bandit Raider.",), sent[0]["args"])

    def test_scene_msg_skips_browser_clear_when_view_is_present(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        other_session = SimpleNamespace(protocol_key="telnet")
        command = object.__new__(BraveCharacterCommand)
        command.session = web_session
        command.caller = SimpleNamespace(sessions=_DummySessions([web_session, other_session]))

        sent = []

        def _record(*args, **kwargs):
            sent.append({"args": args, "kwargs": kwargs})

        command.msg = _record

        view = {"variant": "combat", "sticky": True}
        command.scene_msg("snapshot", view=view)

        self.assertFalse(any("brave_clear" in event["kwargs"] for event in sent))
        self.assertEqual(
            [event["kwargs"].get("brave_view") for event in sent if "brave_view" in event["kwargs"]],
            [view],
        )
        self.assertEqual(
            [event["kwargs"].get("session") for event in sent if event["args"] == ("snapshot",)],
            [[other_session]],
        )

    def test_scene_msg_sends_browser_picker_without_clearing_scene(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        other_session = SimpleNamespace(protocol_key="telnet")
        command = object.__new__(BraveCharacterCommand)
        command.session = web_session
        command.caller = SimpleNamespace(sessions=_DummySessions([web_session, other_session]))

        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})

        picker = {"title": "Field Bandage", "body": ["Restore: HP+18"]}
        command.scene_msg("inspect", picker=picker)

        self.assertFalse(any("brave_clear" in event["kwargs"] for event in sent))
        self.assertEqual(
            [event["kwargs"].get("brave_picker") for event in sent if "brave_picker" in event["kwargs"]],
            [picker],
        )
        self.assertEqual(
            [event["kwargs"].get("session") for event in sent if event["args"] == ("inspect",)],
            [[other_session]],
        )

    def test_rest_requires_authored_rest_site(self):
        command = object.__new__(CmdRest)
        room = SimpleNamespace(db=SimpleNamespace(brave_room_id="brambleford_town_green", brave_safe=True, brave_rest_allowed=False))
        character = SimpleNamespace(key="Dad", location=room, db=SimpleNamespace())
        character.ensure_brave_character = lambda: character
        character.restore_resources = lambda: None
        command.caller = character
        command.get_encounter = lambda *_args, **_kwargs: None

        sent = []
        command.msg = lambda message, **_kwargs: sent.append(str(message))

        command.func()

        self.assertEqual(["You need a proper rest spot before you can recover. Try the Lantern Rest Inn or another marked resting place."], sent)

    def test_rest_restores_at_authored_rest_site(self):
        command = object.__new__(CmdRest)
        room = SimpleNamespace(key="Wayfarer's Yard", db=SimpleNamespace(brave_room_id="tutorial_wayfarers_yard", brave_safe=True, brave_rest_allowed=True))
        character = SimpleNamespace(
            key="Dad",
            location=room,
            db=SimpleNamespace(
                brave_tutorial={
                    "status": "active",
                    "step": "catch_your_breath",
                    "flags": {"won_vermin_fight": True},
                },
                brave_tutorial_current_step="catch_your_breath",
            ),
        )
        character.ensure_brave_character = lambda: character
        restored = []
        character.restore_resources = lambda: restored.append(True)
        command.caller = character
        command.get_encounter = lambda *_args, **_kwargs: None

        sent = []
        command.msg = lambda message, **_kwargs: sent.append(str(message))

        with patch("commands.brave_explore.send_rest_event") as send_rest_event, patch("commands.brave_explore.broadcast_room_activity") as broadcast_room_activity:
            command.func()

        self.assertEqual([True], restored)
        send_rest_event.assert_called_once_with(character, location_name="Wayfarer's Yard")
        broadcast_room_activity.assert_called_once_with(
            room,
            "Dad takes a moment to rest and recover.",
            exclude=[character],
            cls="out",
            category="rest",
        )
        self.assertEqual(["You take a moment to recover your strength."], sent)
        self.assertTrue(character.db.brave_tutorial["flags"]["rested_after_fight"])

    def test_movie_query_resolves_numbers_and_titles(self):
        movie, matches = resolve_movie("1")
        self.assertEqual("music.great_frontier.unpayable_debt", movie["cue_id"])
        self.assertEqual([], matches)

        movie, matches = resolve_movie("shackles")
        self.assertEqual("music.great_frontier.shackles", movie["cue_id"])
        self.assertEqual([], matches)

    def test_every_movie_has_title_cards_and_runtime(self):
        for movie in GREAT_FRONTIER_MOVIES:
            self.assertGreaterEqual(movie.get("runtime_sec", 0), 120, msg=movie["title"])
            self.assertGreaterEqual(len(movie.get("cards", ())), 3, msg=movie["title"])

    def test_movie_picker_lists_program_and_stop_action(self):
        picker = build_movie_picker()
        labels = [option["label"] for option in picker["options"]]
        self.assertIn("Unpayable Debt", labels)
        self.assertIn("Shackles", labels)
        self.assertNotIn("10 - Great Frontier - Shackles", labels)
        self.assertEqual("Stop Movie", labels[-1])

    def test_movie_view_renders_visible_title_cards(self):
        movie = GREAT_FRONTIER_MOVIES[-1]
        view = build_movie_view(movie)

        self.assertEqual("movie", view["variant"])
        self.assertEqual("Shackles", view["title"])
        self.assertTrue(any(section.get("variant") == "movie-cards" for section in view["sections"]))
        self.assertTrue(
            any(
                "Iron remembers" in " ".join(entry.get("lines", []))
                for section in view["sections"]
                for entry in section.get("items", [])
            )
        )
        self.assertIn("Stop Movie", [action["label"] for action in view["actions"]])

    def test_movie_theater_room_action_opens_picker(self):
        room = SimpleNamespace(
            contents=[],
            db=SimpleNamespace(brave_activities=["movie_theater"], brave_rest_allowed=False, brave_room_id="brambleford_frontier_picture_house"),
        )
        viewer = SimpleNamespace(location=room, db=SimpleNamespace(), ndb=SimpleNamespace())

        actions = _format_room_context_action_items(room, viewer)
        movie_action = next(action for action in actions if action["text"] == "Watch Movies")

        self.assertEqual("theaters", movie_action["icon"])
        self.assertEqual("Great Frontier", movie_action["picker"]["title"])

    def test_movie_command_requires_picture_house(self):
        command = object.__new__(CmdMovie)
        room = SimpleNamespace(db=SimpleNamespace(brave_activities=[]))
        character = SimpleNamespace(key="Dad", location=room, db=SimpleNamespace())
        character.ensure_brave_character = lambda: character
        command.caller = character
        command.args = "1"
        command.get_encounter = lambda *_args, **_kwargs: None

        sent = []
        command.msg = lambda message=None, **_kwargs: sent.append(str(message))

        command.func()

        self.assertEqual(["You need to be in Brambleford's Frontier Picture House to watch Great Frontier movies."], sent)

    def test_movie_command_sends_private_browser_audio_event(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(CmdMovie)
        room = SimpleNamespace(db=SimpleNamespace(brave_activities=["movie_theater"]))
        sent_to_character = []
        character = SimpleNamespace(key="Dad", location=room, db=SimpleNamespace(), sessions=_DummySessions([web_session]))
        character.ensure_brave_character = lambda: character
        character.msg = lambda *args, **kwargs: sent_to_character.append({"args": args, "kwargs": kwargs})
        command.session = web_session
        command.caller = character
        command.args = "shackles"
        command.get_encounter = lambda *_args, **_kwargs: None

        command_sent = []
        command.msg = lambda message=None, **_kwargs: command_sent.append(str(message))

        command.func()

        self.assertEqual(
            ["music.great_frontier.shackles"],
            [
                event["kwargs"]["brave_movie_audio"]["cue_id"]
                for event in sent_to_character
                if "brave_movie_audio" in event["kwargs"]
            ],
        )
        payload = next(event["kwargs"]["brave_movie_audio"] for event in sent_to_character if "brave_movie_audio" in event["kwargs"])
        self.assertEqual("play", payload["action"])
        self.assertEqual("Shackles", payload["title"])
        self.assertGreaterEqual(payload["runtime_sec"], 120)
        self.assertGreaterEqual(len(payload["cards"]), 3)
        self.assertEqual("movie", payload["program_command"])
        self.assertEqual("movie stop", payload["stop_command"])
        self.assertEqual([web_session], [event["kwargs"]["session"] for event in sent_to_character if "brave_movie_audio" in event["kwargs"]])
        self.assertEqual(
            [payload],
            [event["kwargs"]["brave_movie_overlay"] for event in sent_to_character if "brave_movie_overlay" in event["kwargs"]],
        )
        views = [event["kwargs"]["brave_view"] for event in sent_to_character if "brave_view" in event["kwargs"]]
        self.assertEqual(["movie"], [view["variant"] for view in views])
        self.assertEqual(["Shackles"], [view["title"] for view in views])
        self.assertEqual(["You start Shackles."], command_sent)

    def test_movie_command_text_client_shows_title_cards(self):
        command = object.__new__(CmdMovie)
        room = SimpleNamespace(db=SimpleNamespace(brave_activities=["movie_theater"]))
        character = SimpleNamespace(key="Dad", location=room, db=SimpleNamespace())
        character.ensure_brave_character = lambda: character
        command.session = None
        command.caller = character
        command.args = "shackles"
        command.get_encounter = lambda *_args, **_kwargs: None

        sent = []
        command.msg = lambda message=None, **_kwargs: sent.append(str(message))

        command.func()

        self.assertIn("Now showing: Shackles", sent[0])
        self.assertIn("Iron remembers", sent[0])

    def test_movie_stop_sends_stop_event(self):
        web_session = SimpleNamespace(protocol_key="websocket")
        command = object.__new__(CmdMovie)
        room = SimpleNamespace(db=SimpleNamespace(brave_activities=["movie_theater"]))
        sent_to_character = []
        character = SimpleNamespace(key="Dad", location=room, db=SimpleNamespace(), sessions=_DummySessions([web_session]))
        character.ensure_brave_character = lambda: character
        character.msg = lambda *args, **kwargs: sent_to_character.append({"args": args, "kwargs": kwargs})
        command.session = web_session
        command.caller = character
        command.args = "stop"
        command.get_encounter = lambda *_args, **_kwargs: None

        command_sent = []
        command.msg = lambda message=None, **_kwargs: command_sent.append(str(message))

        command.func()

        self.assertEqual(
            [{"action": "stop"}],
            [event["kwargs"]["brave_movie_audio"] for event in sent_to_character if "brave_movie_audio" in event["kwargs"]],
        )
        self.assertEqual(
            [{"action": "stop"}],
            [event["kwargs"]["brave_movie_overlay"] for event in sent_to_character if "brave_movie_overlay" in event["kwargs"]],
        )
        self.assertEqual(["You stop the picture-house speaker."], command_sent)
