import os
import sys
import types
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda *args, **kwargs: None
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules.setdefault("world.chargen", chargen_stub)

from typeclasses.characters import Character
from world.activities import (
    _consume_item_by_template,
    build_cooking_payload,
    build_fishing_setup_payload,
    borrow_fishing_tackle,
    describe_cooking_recipe,
    format_recipe_list,
    format_catch_log,
    get_cooking_entries,
    get_catch_log_entries,
    get_fishing_spot_summary,
    get_selected_fishing_lure,
    get_selected_fishing_rod,
    resolve_fishing_minigame,
    set_selected_fishing_lure,
    set_selected_fishing_rod,
    start_fishing_minigame,
)
from commands.brave_explore import _refresh_cook_scene, _refresh_fishing_scene
from world.browser_views import build_fishing_view
from world.screen_text import render_screen
from world.tinkering import build_tinkering_payload, get_tinkering_entries, perform_tinkering
from world.tinkering import describe_tinkering_recipe


class DummyRoom:
    def __init__(self, room_id, *, activities=None):
        self.key = room_id.replace("_", " ").title()
        self.db = SimpleNamespace(brave_room_id=room_id, brave_activities=list(activities or []))


class DummyCharacter:
    def __init__(self):
        self.id = 44
        self.key = "Nyra"
        self.account = None
        self.location = None
        self.db = SimpleNamespace(
            brave_inventory=[],
            brave_quests={},
            brave_silver=12,
            brave_active_fishing_rod="",
            brave_active_fishing_lure="",
            brave_known_cooking_recipes=[],
            brave_known_tinkering_recipes=[],
        )
        self.ndb = SimpleNamespace()

    def get_inventory_quantity(self, template_id):
        return Character.get_inventory_quantity(self, template_id)

    def add_item_to_inventory(self, template_id, quantity=1, *, count_for_collection=True):
        return Character.add_item_to_inventory(self, template_id, quantity, count_for_collection=count_for_collection)

    def remove_item_from_inventory(self, template_id, quantity=1):
        return Character.remove_item_from_inventory(self, template_id, quantity)

    def get_active_encounter(self):
        return None

    def unlock_cooking_recipe(self, recipe_key):
        return Character.unlock_cooking_recipe(self, recipe_key)

    def unlock_tinkering_recipe(self, recipe_key):
        return Character.unlock_tinkering_recipe(self, recipe_key)


class TinkeringAndFishingTests(unittest.TestCase):
    def test_can_select_fishing_rod_and_lure(self):
        character = DummyCharacter()
        character.db.brave_quests = {
            "rats_in_the_kettle": {"status": "completed", "objectives": []},
            "lights_in_the_reeds": {"status": "completed", "objectives": []},
        }

        ok, _message = set_selected_fishing_rod(character, "ashwood")
        self.assertTrue(ok)
        ok, _message = set_selected_fishing_lure(character, "feather")
        self.assertTrue(ok)

        self.assertEqual("ashwood_rod", get_selected_fishing_rod(character)["key"])
        self.assertEqual("feather_jig", get_selected_fishing_lure(character)["key"])

    def test_drowned_causeway_summary_surfaces_new_zone_catches(self):
        character = DummyCharacter()
        character.location = DummyRoom("drowned_weir_drowned_causeway", activities=["fishing"])
        character.db.brave_quests = {
            "the_south_light": {"status": "completed", "objectives": []},
        }

        ok, _message = set_selected_fishing_lure(character, "glass")
        self.assertTrue(ok)

        summary = get_fishing_spot_summary(character)
        catches = {entry["item"]: entry for entry in summary["catches"]}

        self.assertEqual("Drowned Causeway", summary["spot"].get("name"))
        self.assertIn("lockfin_pike", catches)
        self.assertIn("weirglass_eel", catches)
        self.assertTrue(catches["lockfin_pike"]["boosted"] or catches["weirglass_eel"]["boosted"])

    def test_borrow_fishing_kit_sets_starter_tackle_at_wharf(self):
        character = DummyCharacter()
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])

        ok, message = borrow_fishing_tackle(character, "kit")

        self.assertTrue(ok)
        self.assertIn("Loaner Pole", message)
        self.assertEqual("loaner_pole", character.db.brave_active_fishing_rod)
        self.assertEqual("plain_hook", character.db.brave_active_fishing_lure)

    def test_locked_tackle_stays_unavailable_until_required_quest_is_done(self):
        character = DummyCharacter()

        ok, message = set_selected_fishing_rod(character, "riversteel")
        self.assertFalse(ok)
        self.assertIn("No fishing rod matches", message)

        character.db.brave_quests = {
            "captain_varn_blackreed": {"status": "completed", "objectives": []},
            "the_south_light": {"status": "completed", "objectives": []},
        }

        ok, _message = set_selected_fishing_rod(character, "riversteel")
        self.assertTrue(ok)
        ok, _message = set_selected_fishing_lure(character, "glass")
        self.assertTrue(ok)

    def test_fishing_view_marks_only_active_rod_and_lure_selected(self):
        character = DummyCharacter()
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])
        character.db.brave_quests = {
            "rats_in_the_kettle": {"status": "completed", "objectives": []},
            "lights_in_the_reeds": {"status": "completed", "objectives": []},
        }
        character.db.brave_active_fishing_rod = "ashwood_rod"
        character.db.brave_active_fishing_lure = "feather_jig"

        view = build_fishing_view(character)
        sections = {section["label"]: section for section in view["sections"]}
        section_labels = list(sections)
        selected_rods = [entry["title"] for entry in sections["Rods"]["items"] if entry.get("badge") == "Selected"]
        selected_lures = [entry["title"] for entry in sections["Lures"]["items"] if entry.get("badge") == "Selected"]

        self.assertEqual("Fishing", view["title"])
        self.assertNotIn("Likely Catches", section_labels)
        self.assertNotIn("Great Catch Log", section_labels)
        self.assertEqual(["Ashwood Rod"], selected_rods)
        self.assertEqual(["Feather Jig"], selected_lures)

    def test_fishing_view_promotes_cast_or_reel_action(self):
        character = DummyCharacter()
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])

        idle_view = build_fishing_view(character)
        self.assertIn("fish cast", [action.get("command") for action in idle_view["actions"]])

        character.ndb.brave_fishing = {"phase": "bite"}
        bite_view = build_fishing_view(character)
        self.assertIn("reel", [action.get("command") for action in bite_view["actions"]])
        self.assertNotIn("fish cast", [action.get("command") for action in bite_view["actions"]])

        character.ndb.brave_fishing = {"phase": "minigame"}
        minigame_view = build_fishing_view(character)
        self.assertNotIn("fish cast", [action.get("command") for action in minigame_view["actions"]])

    def test_fishing_setup_payload_drives_browser_overlay(self):
        character = DummyCharacter()
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])
        character.db.brave_quests = {
            "rats_in_the_kettle": {"status": "completed", "objectives": []},
            "lights_in_the_reeds": {"status": "completed", "objectives": []},
        }
        character.db.brave_active_fishing_rod = "ashwood_rod"
        character.db.brave_active_fishing_lure = "feather_jig"

        payload = build_fishing_setup_payload(character, status_message="Ready.", status_tone="good")
        selected_rods = [entry["name"] for entry in payload["rods"] if entry["selected"]]
        selected_lures = [entry["name"] for entry in payload["lures"] if entry["selected"]]

        self.assertEqual("setup", payload["phase"])
        self.assertTrue(payload["can_cast"])
        self.assertTrue(payload["can_borrow"])
        self.assertEqual("Ready.", payload["message"])
        self.assertEqual(["Ashwood Rod"], selected_rods)
        self.assertEqual(["Feather Jig"], selected_lures)
        self.assertNotIn("catches", payload)

    def test_start_fishing_minigame_sets_browser_encounter_payload(self):
        character = DummyCharacter()
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])

        ok, message, payload = start_fishing_minigame(character)

        self.assertTrue(ok)
        self.assertIn("Bramble River", message)
        self.assertEqual("minigame", character.ndb.brave_fishing["phase"])
        self.assertEqual(character.ndb.brave_fishing["encounter_id"], payload["encounter_id"])
        self.assertIn(payload["behavior"]["pattern"], {"sine", "linear", "burst", "dart", "drag", "snag"})
        self.assertGreaterEqual(payload["wait_ms"], 900)
        self.assertIn("power", payload["rod"])

    def test_resolve_fishing_minigame_awards_success_and_clears_state(self):
        from unittest.mock import patch

        character = DummyCharacter()
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])
        character.ndb.brave_fishing = {
            "phase": "minigame",
            "room_id": "brambleford_hobbyists_wharf",
            "encounter_id": "run-1",
            "expires_at": 9999999999,
            "fish": {
                "item": "bramble_perch",
                "rarity": "common",
                "weight": [1.0, 1.0],
                "behavior_id": "gentle_wobble",
            },
            "rod_key": "loaner_pole",
            "lure_key": "plain_hook",
        }

        with patch("world.activities.get_entity", return_value=None):
            ok, message, payload = resolve_fishing_minigame(character, "run-1", "success")

        self.assertTrue(ok)
        self.assertIn("Bramble Perch", message)
        self.assertTrue(payload["success"])
        self.assertFalse(hasattr(character.ndb, "brave_fishing"))
        self.assertEqual(1, character.get_inventory_quantity("bramble_perch"))

    def test_refresh_fishing_scene_keeps_web_feedback_in_overlay(self):
        class DummyCommand:
            def __init__(self):
                self.sent = []
                self.other = []
                self.cleared = False

            def get_web_session(self):
                return object()

            def clear_scene(self):
                self.cleared = True

            def send_browser_view(self, view):
                self.sent.append(view)

            def msg(self, message):
                self.sent.append(("terminal", message))

            def send_other_sessions(self, message):
                self.other.append(message)

        from unittest.mock import patch

        character = DummyCharacter()
        character.location = DummyRoom("brambleford_hobbyists_wharf", activities=["fishing"])
        command = DummyCommand()

        with patch("commands.brave_explore.send_webclient_event") as send_event:
            refreshed = _refresh_fishing_scene(command, character, "You borrow a Loaner Pole.", success=True)

        self.assertTrue(refreshed)
        self.assertFalse(command.cleared)
        self.assertEqual(["You borrow a Loaner Pole."], command.other)
        self.assertFalse(any(entry == ("terminal", "You borrow a Loaner Pole.") for entry in command.sent))
        payload = send_event.call_args.kwargs["brave_fishing"]
        self.assertEqual("setup", payload["phase"])
        self.assertEqual("You borrow a Loaner Pole.", payload["message"])

    def test_cooking_payload_categorizes_recipes_and_meals(self):
        character = DummyCharacter()
        character.location = DummyRoom("lantern_rest_hearth", activities=["cooking"])
        character.add_item_to_inventory("hedge_mushroom", 1)
        character.add_item_to_inventory("marsh_root", 1)
        character.add_item_to_inventory("hedgeroot_hash", 2)

        payload = build_cooking_payload(character, status_message="Ready.", status_tone="good")
        ready = {entry["key"]: entry for entry in payload["ready"]}
        meals = {entry["template"]: entry for entry in payload["meals"]}
        locked = {entry["key"] for entry in payload["locked"]}

        self.assertEqual("setup", payload["phase"])
        self.assertEqual("Ready.", payload["message"])
        self.assertIn("hedgeroot_hash", ready)
        self.assertEqual("cook Hedgeroot Hash", ready["hedgeroot_hash"]["command"])
        self.assertIn("moonleaf_eel_skillet", locked)
        self.assertEqual("eat Hedgeroot Hash", meals["hedgeroot_hash"]["command"])

    def test_refresh_cook_scene_keeps_web_feedback_in_overlay(self):
        class DummyCommand:
            def __init__(self):
                self.sent = []
                self.other = []
                self.cleared = False

            def get_web_session(self):
                return object()

            def clear_scene(self):
                self.cleared = True

            def send_browser_view(self, view):
                self.sent.append(view)

            def msg(self, message):
                self.sent.append(("terminal", message))

            def send_other_sessions(self, message):
                self.other.append(message)

        from unittest.mock import patch

        character = DummyCharacter()
        character.location = DummyRoom("lantern_rest_hearth", activities=["cooking"])
        command = DummyCommand()

        with patch("commands.brave_explore.send_webclient_event") as send_event:
            refreshed = _refresh_cook_scene(command, character, "You cook a meal.", success=True)

        self.assertTrue(refreshed)
        self.assertFalse(command.cleared)
        self.assertEqual(["You cook a meal."], command.other)
        self.assertFalse(any(entry == ("terminal", "You cook a meal.") for entry in command.sent))
        payload = send_event.call_args.kwargs["brave_cooking"]
        self.assertEqual("setup", payload["phase"])
        self.assertEqual("You cook a meal.", payload["message"])

    def test_catch_log_entries_sort_heaviest_first(self):
        class DummyBoard:
            def __init__(self):
                self.db = SimpleNamespace(
                    brave_catch_records={
                        "BrambleHouse": {"account": "BrambleHouse", "character": "Nyra", "fish": "Lockfin Pike", "weight": 7.4},
                        "AshClan": {"account": "AshClan", "character": "Tor", "fish": "Dawnscale Trout", "weight": 9.8},
                    }
                )

        from unittest.mock import patch

        with patch("world.activities.get_entity", return_value=DummyBoard()):
            entries = get_catch_log_entries()
            text = format_catch_log()

        self.assertEqual("AshClan", entries[0]["account"])
        self.assertIn("Town best: Dawnscale Trout", text)

    def test_tinkering_consumes_parts_and_creates_result(self):
        character = DummyCharacter()
        character.location = DummyRoom("brambleford_menders_shed", activities=["tinkering"])
        character.add_item_to_inventory("silk_bundle", 1)
        character.add_item_to_inventory("moonleaf_sprig", 1)

        ok, message = perform_tinkering(character, "field bandage")

        self.assertTrue(ok)
        self.assertIn("Field Bandage", message)
        self.assertEqual(0, character.get_inventory_quantity("silk_bundle"))
        self.assertEqual(0, character.get_inventory_quantity("moonleaf_sprig"))
        self.assertEqual(2, character.get_inventory_quantity("field_bandage"))
        self.assertEqual(10, character.db.brave_silver)

    def test_tinkering_entries_mark_ready_designs(self):
        character = DummyCharacter()
        character.add_item_to_inventory("sludge_resin", 1)
        character.add_item_to_inventory("hexbone_charm", 1)

        entries = get_tinkering_entries(character)
        locked = {entry["key"] for entry in entries if not entry["known"]}
        self.assertIn("pitchfire_flask", locked)

        character.add_item_to_inventory("veskas_pitchfire_pattern", 1, count_for_collection=False)
        _ok, _message, _result = _consume_item_by_template(character, "veskas_pitchfire_pattern")
        entries = get_tinkering_entries(character)
        ready = {entry["key"] for entry in entries if entry["ready"]}

        self.assertIn("pitchfire_flask", ready)

    def test_tinkering_payload_categorizes_designs_for_overlay(self):
        character = DummyCharacter()
        character.location = DummyRoom("brambleford_menders_shed", activities=["tinkering"])
        character.add_item_to_inventory("silk_bundle", 1)
        character.add_item_to_inventory("moonleaf_sprig", 1)

        payload = build_tinkering_payload(character, status_message="Bench ready.", status_tone="good")
        ready = {entry["key"]: entry for entry in payload["ready"]}
        locked = {entry["key"] for entry in payload["locked"]}

        self.assertEqual("setup", payload["phase"])
        self.assertEqual("Bench ready.", payload["message"])
        self.assertIn("field_bandage_roll", ready)
        self.assertEqual("tinker Field Bandage Roll", ready["field_bandage_roll"]["command"])
        self.assertIn("pitchfire_flask", locked)

    def test_new_tinkering_entries_cover_auto_and_manual_progression(self):
        character = DummyCharacter()
        character.add_item_to_inventory("fen_resin_clot", 1)
        character.add_item_to_inventory("hedge_mushroom", 1)
        character.add_item_to_inventory("bent_fence_nails", 1)
        character.add_item_to_inventory("road_charm", 1)

        entries = get_tinkering_entries(character)
        ready = {entry["key"] for entry in entries if entry["ready"]}
        locked = {entry["key"] for entry in entries if not entry["known"]}
        self.assertIn("stitchleaf_salve_jar", ready)
        self.assertIn("latchwire_ward_bundle", locked)

        character.add_item_to_inventory("latchwire_ward_pattern", 1, count_for_collection=False)
        _ok, _message, _result = _consume_item_by_template(character, "latchwire_ward_pattern")
        entries = get_tinkering_entries(character)
        ready = {entry["key"] for entry in entries if entry["ready"]}
        self.assertIn("latchwire_ward_bundle", ready)

    def test_fenlight_talisman_pattern_unlocks_higher_end_tinkering_design(self):
        character = DummyCharacter()
        character.add_item_to_inventory("hollow_glass_shard", 1)
        character.add_item_to_inventory("ward_iron_rivet", 1)

        entries = get_tinkering_entries(character)
        locked = {entry["key"] for entry in entries if not entry["known"]}
        self.assertIn("fenlight_talisman_setting", locked)

        character.add_item_to_inventory("fenlight_talisman_pattern", 1, count_for_collection=False)
        _ok, _message, _result = _consume_item_by_template(character, "fenlight_talisman_pattern")
        entries = get_tinkering_entries(character)
        ready = {entry["key"] for entry in entries if entry["ready"]}
        self.assertIn("fenlight_talisman_setting", ready)

    def test_describe_tinkering_recipe_shows_locked_status_and_result_bonus(self):
        character = DummyCharacter()

        ok, message = describe_tinkering_recipe(character, "fenlight talisman")
        self.assertTrue(ok)
        self.assertIn("Fenlight Talisman Setting", message)
        self.assertIn("Locked design", message)
        self.assertIn("Result bonus:", message)

    def test_recipe_note_unlocks_locked_cooking_recipe(self):
        character = DummyCharacter()
        entries = get_cooking_entries(character)
        locked = {entry["key"] for entry in entries if not entry["known"]}
        self.assertIn("moonleaf_eel_skillet", locked)

        character.add_item_to_inventory("grease_stained_supper_note", 1, count_for_collection=False)
        ok, message, _result = _consume_item_by_template(character, "grease_stained_supper_note")

        self.assertTrue(ok)
        self.assertIn("commit", message.lower())
        entries = get_cooking_entries(character)
        known = {entry["key"] for entry in entries if entry["known"]}
        self.assertIn("moonleaf_eel_skillet", known)

    def test_lockfin_note_unlocks_weir_recipe(self):
        character = DummyCharacter()
        entries = get_cooking_entries(character)
        locked = {entry["key"] for entry in entries if not entry["known"]}
        self.assertIn("lockfin_skillet", locked)

        character.add_item_to_inventory("lockfin_skillet_note", 1, count_for_collection=False)
        ok, message, _result = _consume_item_by_template(character, "lockfin_skillet_note")

        self.assertTrue(ok)
        self.assertIn("lockfin skillet", message.lower())
        entries = get_cooking_entries(character)
        known = {entry["key"] for entry in entries if entry["known"]}
        self.assertIn("lockfin_skillet", known)

    def test_describe_cooking_recipe_shows_locked_status_and_bonuses(self):
        character = DummyCharacter()

        ok, message = describe_cooking_recipe(character, "lockfin skillet")
        self.assertTrue(ok)
        self.assertIn("Lockfin Skillet", message)
        self.assertIn("Locked recipe", message)
        self.assertIn("Meal bonus:", message)

    def test_forage_ingredients_open_non_fish_cooking_options(self):
        character = DummyCharacter()
        character.add_item_to_inventory("hedge_mushroom", 1)
        character.add_item_to_inventory("marsh_root", 1)
        character.add_item_to_inventory("moonleaf_sprig", 1)

        entries = get_cooking_entries(character)
        ready = {entry["key"] for entry in entries if entry["ready"]}

        self.assertIn("hedgeroot_hash", ready)
        self.assertIn("moonleaf_root_broth", ready)

    def test_format_recipe_list_returns_screen_text(self):
        character = DummyCharacter()

        text = format_recipe_list(character)

        self.assertIsInstance(text, str)
        self.assertIn("Kitchen Hearth", text)

    def test_render_screen_flattens_nested_block_lists(self):
        text = render_screen(
            "Nested Screen",
            sections=[
                (
                    "Nested",
                    [
                        ["  First block", "    detail"],
                        ["  Second block"],
                    ],
                )
            ],
        )

        self.assertIn("First block", text)
        self.assertIn("Second block", text)


if __name__ == "__main__":
    unittest.main()
