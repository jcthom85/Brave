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
    borrow_fishing_tackle,
    describe_cooking_recipe,
    format_catch_log,
    get_cooking_entries,
    get_catch_log_entries,
    get_fishing_spot_summary,
    get_selected_fishing_lure,
    get_selected_fishing_rod,
    set_selected_fishing_lure,
    set_selected_fishing_rod,
)
from world.tinkering import get_tinkering_entries, perform_tinkering
from world.tinkering import describe_tinkering_recipe


class DummyRoom:
    def __init__(self, room_id, *, activities=None):
        self.key = room_id.replace("_", " ").title()
        self.db = SimpleNamespace(brave_room_id=room_id, brave_activities=list(activities or []))


class DummyCharacter:
    def __init__(self):
        self.id = 44
        self.key = "Nyra"
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


if __name__ == "__main__":
    unittest.main()
