import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.brave_town import CmdBuy, CmdSell, CmdShift
from world.browser_service_views import build_shop_view
from world.commerce import (
    buy_shop_item,
    get_sale_price,
    get_buyable_entries,
    get_sellable_entries,
    is_outfitters_room,
    run_shop_shift,
    sell_inventory_item,
)


class DummyCharacter:
    def __init__(self):
        self.location = SimpleNamespace(db=SimpleNamespace(brave_room_id="brambleford_outfitters"))
        self.db = SimpleNamespace(
            brave_inventory=[],
            brave_quests={},
            brave_shop_bonus={},
            brave_silver=0,
        )

    def get_inventory_quantity(self, template_id):
        return sum(
            int(entry.get("quantity", 0))
            for entry in self.db.brave_inventory
            if entry.get("template") == template_id
        )

    def remove_item_from_inventory(self, template_id, quantity):
        remaining = quantity
        for entry in list(self.db.brave_inventory):
            if entry.get("template") != template_id:
                continue
            take = min(int(entry.get("quantity", 0)), remaining)
            entry["quantity"] = int(entry.get("quantity", 0)) - take
            remaining -= take
            if entry["quantity"] <= 0:
                self.db.brave_inventory.remove(entry)
            if remaining <= 0:
                return True
        return False

    def add_item_to_inventory(self, template_id, quantity=1, *, count_for_collection=True):
        for entry in self.db.brave_inventory:
            if entry.get("template") == template_id:
                entry["quantity"] += quantity
                return
        self.db.brave_inventory.append({"template": template_id, "quantity": quantity})

    def get_active_encounter(self):
        return None


class CommerceTests(unittest.TestCase):
    def _web_command(self, command_cls, character, args=""):
        command = object.__new__(command_cls)
        command.caller = character
        command.session = SimpleNamespace(protocol_key="websocket")
        command.args = args
        sent = []
        command.msg = lambda *args, **kwargs: sent.append({"args": args, "kwargs": kwargs})
        command.get_character = lambda: character
        return command, sent

    def test_outfitters_room_is_content_configured_shop_room(self):
        character = DummyCharacter()
        self.assertTrue(is_outfitters_room(character.location))
        self.assertFalse(is_outfitters_room(SimpleNamespace(db=SimpleNamespace(brave_room_id="brambleford_green"))))

    def test_sellable_entries_price_valued_inventory(self):
        character = DummyCharacter()
        character.db.brave_inventory = [{"template": "wolf_pelt", "quantity": 2}]

        entries = get_sellable_entries(character)

        self.assertEqual(["wolf_pelt"], [entry["template_id"] for entry in entries])
        self.assertEqual(8, entries[0]["unit_price"])
        self.assertEqual(16, entries[0]["total_price"])

    def test_active_collect_quest_items_are_reserved_from_sale(self):
        character = DummyCharacter()
        character.db.brave_inventory = [{"template": "moonleaf_sprig", "quantity": 4}]
        character.db.brave_quests = {
            "herbs_for_sister_maybelle": {
                "status": "active",
                "objectives": [{"progress": 1, "required": 3, "completed": False}],
            }
        }

        entries = get_sellable_entries(character)

        self.assertEqual(2, entries[0]["reserved"])
        self.assertEqual(2, entries[0]["sellable"])
        ok, result = sell_inventory_item(character, "moonleaf_sprig", 3)
        self.assertFalse(ok)
        self.assertIn("only sell 2", result)

    def test_shift_bonus_is_disabled_and_existing_bonus_is_cleared(self):
        character = DummyCharacter()
        character.db.brave_inventory = [{"template": "wolf_pelt", "quantity": 1}]
        character.db.brave_shop_bonus = {"name": "Old Bonus", "bonus_pct": 50, "sales_left": 3}

        ok, message = run_shop_shift(character)

        self.assertFalse(ok)
        self.assertIn("not taking counter help", message)
        ok, result = sell_inventory_item(character, "wolf_pelt", 1)

        self.assertTrue(ok)
        self.assertEqual(get_sale_price("wolf_pelt"), result["silver"])
        self.assertFalse(result["expired_bonus"])
        self.assertEqual({}, character.db.brave_shop_bonus)

    def test_buyable_entries_and_buy_shop_item_use_infinite_stock(self):
        character = DummyCharacter()
        character.db.brave_silver = 20

        entries = get_buyable_entries(character)

        self.assertIn("field_bandage", [entry["template_id"] for entry in entries])
        ok, result = buy_shop_item(character, "field_bandage", 1)
        self.assertTrue(ok)
        self.assertEqual(12, result["silver"])
        self.assertEqual(8, character.db.brave_silver)
        self.assertEqual(1, character.get_inventory_quantity("field_bandage"))

    def test_buy_shop_item_rejects_insufficient_silver(self):
        character = DummyCharacter()
        character.db.brave_silver = 1

        ok, result = buy_shop_item(character, "field_bandage", 1)

        self.assertFalse(ok)
        self.assertIn("need 12 silver", result)
        self.assertEqual(0, character.get_inventory_quantity("field_bandage"))

    def test_shop_view_surfaces_buy_sell_and_shift_actions(self):
        character = DummyCharacter()
        character.db.brave_silver = 84
        character.db.brave_inventory = [{"template": "wolf_pelt", "quantity": 2}]

        view = build_shop_view(character)

        self.assertEqual("Brambleford Outfitters", view["title"])
        self.assertEqual([], [action["label"] for action in view["actions"]])
        labels = [
            action["label"]
            for section in view["sections"]
            for item in section.get("items", [])
            for action in item.get("actions", [])
        ]
        self.assertIn("Buy", labels)
        self.assertIn("Sell", labels)

        buy_entry = next(
            item
            for section in view["sections"]
            if section["label"] == "Buy"
            for item in section["items"]
            if item["title"] == "Field Bandage"
        )
        sell_entry = next(
            item
            for section in view["sections"]
            if section["label"] == "Sell"
            for item in section["items"]
            if item["title"] == "Wolf Pelt x2"
        )
        self.assertNotIn("command", buy_entry)
        self.assertNotIn("command", sell_entry)
        self.assertIn("picker", buy_entry)
        self.assertIn("picker", sell_entry)
        self.assertEqual("Buy Field Bandage", buy_entry["picker"]["title"])
        self.assertEqual("Sell Wolf Pelt", sell_entry["picker"]["title"])
        self.assertNotIn("subtitle", buy_entry["picker"])
        self.assertNotIn("subtitle", sell_entry["picker"])
        self.assertEqual(1, len(buy_entry["picker"]["body"]))
        self.assertIn("wrap", buy_entry["picker"]["body"][0])
        self.assertNotIn("You have 84 silver.", buy_entry["picker"]["body"])
        self.assertEqual([{"label": "12 silver", "icon": "savings", "tone": "accent"}], buy_entry["picker"]["chips"])
        self.assertEqual("Buy", buy_entry["picker"]["title_prefix"])
        self.assertEqual("Field Bandage", buy_entry["picker"]["title_item"])
        self.assertEqual("title_item", buy_entry["picker"]["rarity_target"])
        self.assertEqual([{"label": "8 silver", "icon": "savings", "tone": "accent"}], sell_entry["picker"]["chips"])
        self.assertEqual("Sell", sell_entry["picker"]["title_prefix"])
        self.assertEqual("Wolf Pelt", sell_entry["picker"]["title_item"])
        self.assertEqual("title_item", sell_entry["picker"]["rarity_target"])
        self.assertEqual([], buy_entry["picker"]["options"])
        self.assertEqual([], sell_entry["picker"]["options"])
        self.assertEqual(
            {
                "label": "Quantity",
                "action_label": "Buy",
                "command_template": "buy Field Bandage = {quantity}",
                "min": 1,
                "max": 7,
                "initial": 1,
                "unit_price": 12,
                "total_label": "Total",
                "disabled": False,
            },
            buy_entry["picker"]["quantity_control"],
        )
        self.assertEqual(
            {
                "label": "Quantity",
                "action_label": "Sell",
                "command_template": "sell Wolf Pelt = {quantity}",
                "min": 1,
                "max": 2,
                "initial": 1,
                "unit_price": 8,
                "total_label": "Return",
                "disabled": False,
            },
            sell_entry["picker"]["quantity_control"],
        )

    def test_web_buy_uses_shop_view_and_popup_not_plain_text(self):
        character = DummyCharacter()
        character.db.brave_silver = 20
        command, sent = self._web_command(CmdBuy, character, "field bandage")

        command.func()

        self.assertFalse([event for event in sent if event["args"]])
        self.assertTrue(any("brave_view" in event["kwargs"] for event in sent))
        self.assertTrue(any("brave_notice" in event["kwargs"] for event in sent))
        notice = next(event["kwargs"]["brave_notice"] for event in sent if "brave_notice" in event["kwargs"])
        self.assertEqual("Purchase Complete", notice["title"])
        self.assertIn("Bought Field Bandage", " ".join(notice["lines"]))

    def test_web_sell_uses_shop_view_and_popup_not_plain_text(self):
        character = DummyCharacter()
        character.db.brave_inventory = [{"template": "wolf_pelt", "quantity": 1}]
        command, sent = self._web_command(CmdSell, character, "wolf pelt")

        command.func()

        self.assertFalse([event for event in sent if event["args"]])
        self.assertTrue(any("brave_view" in event["kwargs"] for event in sent))
        notice = next(event["kwargs"]["brave_notice"] for event in sent if "brave_notice" in event["kwargs"])
        self.assertEqual("Sale Complete", notice["title"])
        self.assertIn("Sold Wolf Pelt", " ".join(notice["lines"]))

    def test_web_shift_reports_unavailable_without_bonus_copy(self):
        character = DummyCharacter()
        command, sent = self._web_command(CmdShift, character)

        command.func()

        self.assertFalse([event for event in sent if event["args"]])
        notice = next(event["kwargs"]["brave_notice"] for event in sent if "brave_notice" in event["kwargs"])
        self.assertEqual("Shop Help Unavailable", notice["title"])
        self.assertIn("not taking counter help", " ".join(notice["lines"]))
        self.assertNotIn("Bonus", " ".join(notice["lines"]))


if __name__ == "__main__":
    unittest.main()
