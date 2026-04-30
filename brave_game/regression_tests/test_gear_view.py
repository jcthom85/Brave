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

from world.browser_panels import build_gear_panel
from world.browser_views import build_gear_view
from typeclasses.characters import Character


class DummyCharacter:
    def __init__(self, equipment=None, inventory=None, brave_class="warrior"):
        self.key = "Dad"
        self.location = None
        self.db = SimpleNamespace(
            brave_class=brave_class,
            brave_race="human",
            brave_equipment=equipment or {},
            brave_inventory=inventory or [],
        )

    def get_equippable_inventory(self, slot=None):
        return Character.get_equippable_inventory(self, slot=slot)


class DummyEquipmentCharacter:
    def __init__(self, equipment=None, inventory=None, brave_class="warrior"):
        self.db = SimpleNamespace(
            brave_class=brave_class,
            brave_equipment=equipment or {},
            brave_inventory=inventory or [],
            brave_quests={},
        )
        self.ndb = SimpleNamespace()
        self.recalculate_calls = 0

    def msg(self, *args, **kwargs):
        return None

    def ensure_brave_character(self):
        return None

    def recalculate_stats(self):
        self.recalculate_calls += 1

    def get_inventory_quantity(self, template_id):
        return Character.get_inventory_quantity(self, template_id)

    def add_item_to_inventory(self, template_id, quantity=1, *, count_for_collection=True):
        return Character.add_item_to_inventory(self, template_id, quantity, count_for_collection=count_for_collection)

    def remove_item_from_inventory(self, template_id, quantity=1):
        return Character.remove_item_from_inventory(self, template_id, quantity)

    def get_equippable_inventory(self, slot=None):
        return Character.get_equippable_inventory(self, slot=slot)


class GearViewTests(unittest.TestCase):
    def test_gear_view_lists_every_slot_in_order(self):
        character = DummyCharacter(
            equipment={
                "main_hand": "militia_blade",
                "off_hand": "oakbound_shield",
                "chest": "roadwarden_mail",
            },
            inventory=[
                {"template": "ironroot_longblade", "quantity": 1},
                {"template": "field_leathers", "quantity": 1},
                {"template": "trail_mix_satchel", "quantity": 1},
            ],
        )

        view = build_gear_view(character)

        self.assertEqual("gear", view.get("variant"))
        self.assertEqual("", view.get("eyebrow"))
        self.assertEqual("Gear", view.get("title"))
        self.assertEqual("Close", view.get("back_action", {}).get("label"))
        self.assertEqual([], view.get("chips"))
        self.assertEqual("shield", view.get("title_icon"))

        slots = view.get("sections", [])[0]
        self.assertEqual("slots", slots.get("variant"))
        self.assertTrue(slots.get("hide_label"))
        self.assertEqual("wide", slots.get("span"))
        self.assertEqual(
            ["Main Hand", "Off Hand", "Head", "Chest", "Hands", "Legs", "Feet", "Ring", "Trinket", "Snack"],
            [item.get("title") for item in slots.get("items", [])],
        )
        self.assertEqual(
            ["Militia Blade", "Oakbound Shield", "Empty", "Roadwarden Mail", "Empty", "Empty", "Empty", "Empty", "Empty", "Empty"],
            [item.get("meta") for item in slots.get("items", [])],
        )
        self.assertEqual("Rare", slots.get("items", [])[0].get("rarity_label"))
        self.assertEqual("meta", slots.get("items", [])[0].get("rarity_target"))
        self.assertEqual("Uncommon", slots.get("items", [])[3].get("rarity_label"))
        self.assertEqual("rarity-uncommon", slots.get("items", [])[3].get("rarity_tone"))
        self.assertNotIn("chips", slots.get("items", [])[3])
        main_hand_picker = slots.get("items", [])[0].get("picker", {})
        self.assertEqual("Main Hand", main_hand_picker.get("title"))
        self.assertEqual("Militia Blade", main_hand_picker.get("subtitle"))
        self.assertEqual("Rare", main_hand_picker.get("chips", [])[0].get("label"))
        self.assertEqual("subtitle", main_hand_picker.get("rarity_target"))
        self.assertEqual("rarity-rare", main_hand_picker.get("rarity_tone"))
        self.assertNotIn("Rarity: Rare", main_hand_picker.get("body", []))
        self.assertEqual(
            ["Unequip Militia Blade", "Ironroot Longblade"],
            [option.get("label") for option in main_hand_picker.get("options", [])],
        )
        self.assertIn("Main Hand", slots.get("items", [])[0].get("tooltip", ""))
        chest_picker = slots.get("items", [])[3].get("picker", {})
        self.assertEqual(
            ["Unequip Roadwarden Mail", "Field Leathers"],
            [option.get("label") for option in chest_picker.get("options", [])],
        )
        head_picker = slots.get("items", [])[2].get("picker", {})
        self.assertEqual("Head", head_picker.get("title"))
        self.assertEqual("Empty", head_picker.get("subtitle"))
        self.assertEqual([], head_picker.get("options", []))
        self.assertEqual([], slots.get("items", [])[2].get("lines", []))
        snack_picker = slots.get("items", [])[9].get("picker", {})
        self.assertEqual("Snack", snack_picker.get("title"))
        self.assertEqual("Empty", snack_picker.get("subtitle"))
        self.assertEqual(["Trail Mix Satchel"], [option.get("label") for option in snack_picker.get("options", [])])

    def test_gear_panel_lists_every_slot(self):
        character = DummyCharacter(
            equipment={
                "main_hand": "militia_blade",
                "off_hand": "oakbound_shield",
                "chest": "roadwarden_mail",
            }
        )

        panel = build_gear_panel(character)

        self.assertEqual("", panel.get("eyebrow"))
        self.assertEqual("Gear", panel.get("title"))
        self.assertEqual([], panel.get("chips"))
        self.assertEqual("shield", panel.get("title_icon"))
        self.assertEqual("Slots", panel.get("sections", [])[0].get("label"))
        self.assertEqual(
            [
                "Main Hand · Militia Blade",
                "Off Hand · Oakbound Shield",
                "Head · Empty",
                "Chest · Roadwarden Mail",
                "Hands · Empty",
                "Legs · Empty",
                "Feet · Empty",
                "Ring · Empty",
                "Trinket · Empty",
                "Snack · Empty",
            ],
            [item.get("text") for item in panel.get("sections", [])[0].get("items", [])],
        )
        self.assertEqual("Rare", panel.get("sections", [])[0].get("items", [])[0].get("rarity_label"))
        self.assertEqual("Epic", panel.get("sections", [])[0].get("items", [])[1].get("rarity_label"))

    def test_character_equips_inventory_item_and_stows_previous_one(self):
        character = DummyEquipmentCharacter(
            equipment={"main_hand": "militia_blade"},
            inventory=[{"template": "ironroot_longblade", "quantity": 1}],
        )

        success, result = Character.equip_inventory_item(character, "ironroot_longblade", slot="main_hand")

        self.assertTrue(success)
        self.assertEqual("ironroot_longblade", character.db.brave_equipment.get("main_hand"))
        self.assertEqual("militia_blade", result.get("replaced"))
        self.assertEqual(1, character.recalculate_calls)
        self.assertEqual(0, Character.get_inventory_quantity(character, "ironroot_longblade"))
        self.assertEqual(1, Character.get_inventory_quantity(character, "militia_blade"))

    def test_character_unequips_slot_into_inventory(self):
        character = DummyEquipmentCharacter(
            equipment={"chest": "roadwarden_mail"},
            inventory=[],
        )

        success, result = Character.unequip_slot(character, "chest")

        self.assertTrue(success)
        self.assertIsNone(character.db.brave_equipment.get("chest"))
        self.assertEqual("roadwarden_mail", result.get("unequipped"))
        self.assertEqual(1, character.recalculate_calls)
        self.assertEqual(1, Character.get_inventory_quantity(character, "roadwarden_mail"))

    def test_non_warrior_cannot_equip_out_of_class_weapon(self):
        character = DummyEquipmentCharacter(
            equipment={},
            inventory=[{"template": "militia_blade", "quantity": 1}],
            brave_class="mage",
        )

        success, result = Character.equip_inventory_item(character, "militia_blade", slot="main_hand")

        self.assertFalse(success)
        self.assertIn("outside your training", result)
        self.assertEqual(1, Character.get_inventory_quantity(character, "militia_blade"))

    def test_warrior_can_equip_other_class_weapon(self):
        character = DummyEquipmentCharacter(
            equipment={},
            inventory=[{"template": "cinderwire_staff", "quantity": 1}],
            brave_class="warrior",
        )

        success, result = Character.equip_inventory_item(character, "cinderwire_staff", slot="main_hand")

        self.assertTrue(success)
        self.assertEqual("cinderwire_staff", result.get("equipped"))
        self.assertEqual("cinderwire_staff", character.db.brave_equipment.get("main_hand"))

    def test_gear_view_filters_incompatible_items_from_picker(self):
        character = DummyCharacter(
            inventory=[
                {"template": "militia_blade", "quantity": 1},
                {"template": "cinderwire_staff", "quantity": 1},
            ],
            brave_class="mage",
        )

        view = build_gear_view(character)
        slots = view.get("sections", [])[0]
        main_hand_picker = slots.get("items", [])[0].get("picker", {})

        self.assertEqual(["Cinderwire Staff"], [option.get("label") for option in main_hand_picker.get("options", [])])


if __name__ == "__main__":
    unittest.main()
