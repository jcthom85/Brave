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

from world.browser_panels import build_pack_panel
from world.browser_views import build_pack_view


def _section(view_or_panel, label):
    for section in view_or_panel.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyCharacter:
    def __init__(self, *, char_id=1, key="Dad", location=None, party_id=None, inventory=None, silver=29):
        self.id = char_id
        self.key = key
        self.location = location
        self.db = SimpleNamespace(
            brave_silver=silver,
            brave_party_id=party_id,
            brave_inventory=list(
                inventory
                if inventory is not None
                else [
                    {"template": "field_bandage", "quantity": 2},
                    {"template": "bramble_perch", "quantity": 3},
                    {"template": "wolf_pelt", "quantity": 2},
                    {"template": "roadwarden_mail", "quantity": 1},
                    {"template": "trail_mix_satchel", "quantity": 1},
                ]
            ),
        )

    def ensure_brave_character(self):
        return None


class DummyRoomCharacter:
    def __init__(self, *, char_id, key="Rook", location=None, party_id=None):
        self.id = char_id
        self.key = key
        self.location = location
        self.db = SimpleNamespace(
            brave_party_id=party_id,
            brave_resources={"hp": 20, "mana": 10, "stamina": 10},
            brave_derived_stats={"max_hp": 24, "max_mana": 10, "max_stamina": 10},
        )

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


class DummyRoom:
    def __init__(self, contents=None):
        self.contents = list(contents or [])
        self.db = SimpleNamespace(brave_resonance="fantasy")


class PackViewTests(unittest.TestCase):
    def test_pack_view_uses_compact_items_and_dedicated_silver_strip(self):
        room = DummyRoom()
        character = DummyCharacter(location=room)
        room.contents = [character]

        view = build_pack_view(character)

        self.assertEqual("pack", view.get("variant"))
        self.assertEqual("", view.get("eyebrow"))
        self.assertEqual("Pack", view.get("title"))
        self.assertEqual("backpack", view.get("title_icon"))
        self.assertEqual([], view.get("chips"))
        self.assertEqual("Close", view.get("back_action", {}).get("label"))

        silver_section = view.get("sections", [])[0]
        self.assertEqual("pairs", silver_section.get("kind"))
        self.assertEqual("money", silver_section.get("variant"))
        self.assertTrue(silver_section.get("hide_label"))
        self.assertEqual("Silver", silver_section.get("items", [])[0].get("label"))
        self.assertEqual("29", silver_section.get("items", [])[0].get("value"))

        self.assertEqual(
            ["", "Consumables", "Ingredients", "Loot And Materials", "Spare Gear"],
            [section.get("label") for section in view.get("sections", [])],
        )
        spare_gear = _section(view, "Spare Gear")
        self.assertEqual("shield", spare_gear.get("icon"))
        self.assertEqual("items", spare_gear.get("variant"))
        self.assertEqual("list", spare_gear.get("kind"))
        self.assertEqual(
            ["Roadwarden Mail", "Trail Mix Satchel"],
            [item.get("text") for item in spare_gear.get("items", [])],
        )
        self.assertTrue(
            all(item.get("picker") for item in spare_gear.get("items", []))
        )
        self.assertEqual("Chest", spare_gear.get("items", [])[0].get("picker", {}).get("subtitle"))
        self.assertEqual("Snack", spare_gear.get("items", [])[1].get("picker", {}).get("subtitle"))
        self.assertIn("A patched shirt of mail", spare_gear.get("items", [])[0].get("tooltip", ""))
        self.assertTrue(
            any(
                "Trail Mix · 3-turn cooldown" == line
                for line in spare_gear.get("items", [])[1].get("picker", {}).get("body", [])
            )
        )
        self.assertFalse(
            any(
                line.startswith("Bonuses:")
                for item in spare_gear.get("items", [])
                for line in item.get("picker", {}).get("body", [])
            )
        )

        consumables = _section(view, "Consumables")
        self.assertEqual("list", consumables.get("kind"))
        self.assertEqual(["Field Bandage"], [item.get("text") for item in consumables.get("items", [])])
        self.assertEqual("2", consumables.get("items", [])[0].get("badge"))
        self.assertEqual("Consumable", consumables.get("items", [])[0].get("picker", {}).get("subtitle"))
        self.assertEqual(
            "Use",
            consumables.get("items", [])[0].get("actions", [])[0].get("label"),
        )
        self.assertEqual(
            "Use Field Bandage",
            consumables.get("items", [])[0].get("actions", [])[0].get("picker", {}).get("title"),
        )
        self.assertEqual(
            [{"label": "Dad", "command": "use Field Bandage", "meta": "You"}],
            [
                {
                    "label": option.get("label"),
                    "command": option.get("command"),
                    "meta": option.get("meta"),
                }
                for option in consumables.get("items", [])[0].get("actions", [])[0].get("picker", {}).get("options", [])
            ],
        )

    def test_pack_panel_uses_pack_labeling_and_summary_section(self):
        character = DummyCharacter()

        panel = build_pack_panel(character)

        self.assertEqual("", panel.get("eyebrow"))
        self.assertEqual("Pack", panel.get("title"))
        self.assertEqual("backpack", panel.get("title_icon"))
        self.assertEqual([], panel.get("chips"))

        on_hand = panel.get("sections", [])[0]
        self.assertEqual("On Hand", on_hand.get("label"))
        self.assertEqual(
            ["29 silver", "5 item types", "9 pieces"],
            [item.get("text") for item in on_hand.get("items", [])],
        )

        spare_gear = _section(panel, "Spare Gear")
        self.assertEqual("shield", spare_gear.get("icon"))
        self.assertEqual(
            ["Roadwarden Mail", "Trail Mix Satchel"],
            [item.get("text") for item in spare_gear.get("items", [])],
        )
        self.assertEqual(
            ["Chest", "Snack"],
            [item.get("meta") for item in spare_gear.get("items", [])],
        )

    def test_pack_view_uses_target_picker_for_nearby_allies_and_hides_combat_only_use(self):
        room = DummyRoom()
        character = DummyCharacter(
            char_id=7,
            location=room,
            party_id="party-7",
            inventory=[
                {"template": "field_bandage", "quantity": 2},
                {"template": "fireflask", "quantity": 1},
            ],
        )
        ally = DummyCharacter(
            char_id=8,
            key="Peep",
            location=room,
            party_id="party-7",
            inventory=[],
        )
        stranger = DummyRoomCharacter(char_id=9, key="Rook", location=room)
        room.contents = [stranger, character, ally]

        view = build_pack_view(character)
        consumables = _section(view, "Consumables")
        bandage = consumables.get("items", [])[0]
        fireflask = consumables.get("items", [])[1]

        self.assertEqual("Field Bandage", bandage.get("text"))
        self.assertEqual("Use", bandage.get("actions", [])[0].get("label"))
        self.assertEqual("Use Field Bandage", bandage.get("actions", [])[0].get("picker", {}).get("title"))
        self.assertEqual(
            [
                {"label": "Dad", "command": "use Field Bandage", "meta": "You"},
                {"label": "Peep", "command": "use Field Bandage = Peep", "meta": "Party"},
                {"label": "Rook", "command": "use Field Bandage = Rook", "meta": "Nearby"},
            ],
            [
                {
                    "label": option.get("label"),
                    "command": option.get("command"),
                    "meta": option.get("meta"),
                }
                for option in bandage.get("actions", [])[0].get("picker", {}).get("options", [])
            ],
        )

        self.assertEqual("Fire Flask", fireflask.get("text"))
        self.assertNotIn("actions", fireflask)


if __name__ == "__main__":
    unittest.main()
