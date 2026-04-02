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

from world.browser_views import build_combat_view


class DummyRoom:
    def __init__(self, key="Brush Line"):
        self.key = key
        self.db = SimpleNamespace(
            brave_world="Brave",
            brave_zone="Whispering Woods",
        )


class DummyCharacter:
    def __init__(self, char_id, key, room, class_key, resources, derived, abilities, inventory=None):
        self.id = char_id
        self.key = key
        self.location = room
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_resources=resources,
            brave_derived_stats=derived,
            brave_inventory=list(inventory or []),
        )
        self._abilities = list(abilities)

    def ensure_brave_character(self):
        return None

    def get_unlocked_abilities(self):
        return list(self._abilities)


class DummyEncounter:
    def __init__(self, room, participants, enemies, *, pending=None, states=None, title="Mire Teeth"):
        self.obj = room
        self.db = SimpleNamespace(round=2, encounter_title=title)
        self._participants = list(participants)
        self._enemies = list(enemies)
        self._pending = dict(pending or {})
        self._states = dict(states or {})

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return list(self._participants)

    def _describe_pending_action(self, character):
        return self._pending.get(character.id, "basic attack")

    def _get_participant_state(self, character):
        return self._states.get(
            character.id,
            {
                "guard": 0,
                "bleed_turns": 0,
                "poison_turns": 0,
                "curse_turns": 0,
                "snare_turns": 0,
                "feint_turns": 0,
            },
        )


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


def _entry(section, title):
    for entry in section.get("items", []):
        if entry.get("title") == title:
            return entry
    raise AssertionError(f"Missing entry {title}")


def _item(section, prefix):
    for item in section.get("items", []):
        if item.get("text", "").startswith(prefix):
            return item
    raise AssertionError(f"Missing item {prefix}")


class CombatViewTests(unittest.TestCase):
    def test_targeted_ally_ability_uses_picker_targets(self):
        room = DummyRoom()
        healer = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 20, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal", "Smite"],
        )
        ally = DummyCharacter(
            8,
            "Peep",
            room,
            "warrior",
            {"hp": 17, "mana": 0, "stamina": 9},
            {"max_hp": 26, "max_mana": 0, "max_stamina": 12},
            ["Strike"],
        )
        encounter = DummyEncounter(
            room,
            [healer, ally],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
            pending={7: "heal -> Peep"},
        )
        encounter.db.pending_actions = {"7": {"kind": "ability", "ability": "heal", "target": 8}}

        view = build_combat_view(encounter, healer)
        abilities = _section(view, "Abilities")

        heal_item = _item(abilities, "Heal")
        smite_item = _item(abilities, "Smite")

        self.assertEqual("A", heal_item.get("badge"))
        self.assertIsNone(heal_item.get("prefill"))
        self.assertIsNone(heal_item.get("command"))
        self.assertEqual("Heal Target", heal_item.get("picker", {}).get("title"))
        self.assertEqual(
            [
                {"label": "Dad", "command": "use Heal", "meta": "You"},
                {"label": "Peep", "command": "use Heal = Peep", "meta": "Ally"},
            ],
            [
                {
                    "label": option.get("label"),
                    "command": option.get("command"),
                    "meta": option.get("meta"),
                }
                for option in heal_item.get("picker", {}).get("options", [])
            ],
        )
        self.assertEqual("E", smite_item.get("badge"))
        self.assertEqual("use Smite = e1", smite_item.get("command"))
        self.assertEqual([], view.get("chips", []))
        self.assertEqual("2 Allies • 1 Foe", view.get("subtitle", ""))
        self.assertEqual("Flee", view.get("actions", [])[0].get("label"))
        self.assertIsNot(view.get("actions", [])[0].get("icon_only"), True)
        self.assertEqual("Heal · 10 MP", heal_item.get("text", ""))
        self.assertIn("8 MP", smite_item.get("text", ""))

        party = _section(view, "Party")
        dad_entry = _entry(party, "Dad")
        peep_entry = _entry(party, "Peep")
        self.assertEqual(
            [("HP", "20 / 24"), ("STA", "6 / 10"), ("MP", "18 / 20")],
            [(meter.get("label"), meter.get("value")) for meter in dad_entry.get("meters", [])],
        )
        self.assertEqual(
            [("HP", "17 / 26"), ("STA", "9 / 12")],
            [(meter.get("label"), meter.get("value")) for meter in peep_entry.get("meters", [])],
        )
        self.assertIn("Targeted", [chip.get("label") for chip in peep_entry.get("chips", [])])

    def test_combat_item_uses_shared_use_command(self):
        room = DummyRoom()
        cleric = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 14, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal", "Smite"],
            inventory=[{"template": "field_bandage", "quantity": 2}],
        )
        encounter = DummyEncounter(room, [cleric], [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}])

        view = build_combat_view(encounter, cleric)
        items = _section(view, "Items")
        bandage = _item(items, "Field Bandage")

        self.assertEqual("use Field Bandage", bandage.get("command"))
        self.assertEqual("2", bandage.get("badge"))

    def test_unaffordable_ability_is_not_clickable(self):
        room = DummyRoom()
        healer = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 20, "mana": 4, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal"],
        )
        encounter = DummyEncounter(
            room,
            [healer],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        view = build_combat_view(encounter, healer)
        abilities = _section(view, "Abilities")
        heal_item = _item(abilities, "Heal")

        self.assertIsNone(heal_item.get("command"))
        self.assertIsNone(heal_item.get("prefill"))
        self.assertIsNone(heal_item.get("picker"))
        self.assertIn("NEED 6", heal_item.get("text", ""))

    def test_combat_view_surfaces_restored_status_chips(self):
        room = DummyRoom()
        rogue = DummyCharacter(
            7,
            "Dad",
            room,
            "rogue",
            {"hp": 20, "mana": 0, "stamina": 12},
            {"max_hp": 24, "max_mana": 0, "max_stamina": 14},
            ["Backstab"],
        )
        encounter = DummyEncounter(
            room,
            [rogue],
            [{
                "id": "e1",
                "key": "Bog Wolf",
                "hp": 11,
                "max_hp": 16,
                "bleed_turns": 2,
                "poison_turns": 1,
            }],
            states={
                7: {
                    "guard": 0,
                    "bleed_turns": 0,
                    "poison_turns": 0,
                    "curse_turns": 0,
                    "snare_turns": 0,
                    "feint_turns": 0,
                    "stealth_turns": 1,
                }
            },
        )

        view = build_combat_view(encounter, rogue)
        party = _section(view, "Party")
        enemies = _section(view, "Enemies")
        rogue_entry = _entry(party, "Dad")
        enemy_entry = _entry(enemies, "Bog Wolf")

        self.assertIn("Hidden", [chip.get("label") for chip in rogue_entry.get("chips", [])])
        self.assertIn("Bleeding 2", [chip.get("label") for chip in enemy_entry.get("chips", [])])
        self.assertIn("Poisoned 1", [chip.get("label") for chip in enemy_entry.get("chips", [])])

    def test_selected_enemy_target_is_marked_in_enemy_cards(self):
        room = DummyRoom()
        warrior = DummyCharacter(
            7,
            "Dad",
            room,
            "warrior",
            {"hp": 20, "mana": 0, "stamina": 12},
            {"max_hp": 24, "max_mana": 0, "max_stamina": 14},
            ["Strike"],
        )
        encounter = DummyEncounter(
            room,
            [warrior],
            [
                {"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16},
                {"id": "e2", "key": "Mud Lurker", "hp": 13, "max_hp": 18},
            ],
        )
        encounter.db.pending_actions = {"7": {"kind": "attack", "target": "e2"}}
        view = build_combat_view(encounter, warrior)
        enemies = _section(view, "Enemies")
        wolf = _entry(enemies, "Bog Wolf")
        lurker = _entry(enemies, "Mud Lurker")
        self.assertNotIn("Targeted", [chip.get("label") for chip in wolf.get("chips", [])])
        self.assertIn("Targeted", [chip.get("label") for chip in lurker.get("chips", [])])

    def test_combat_view_lists_carried_meals_in_items_section(self):
        room = DummyRoom()
        cleric = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 20, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal"],
            inventory=[
                {"template": "crisped_perch_plate", "quantity": 2},
                {"template": "riverlight_chowder", "quantity": 1},
            ],
        )
        encounter = DummyEncounter(
            room,
            [cleric],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        view = build_combat_view(encounter, cleric)
        items = _section(view, "Items")
        plate = _item(items, "Crisped Perch Plate")
        chowder = _item(items, "Riverlight Chowder")

        self.assertEqual("2", plate.get("badge"))
        self.assertEqual("use Crisped Perch Plate", plate.get("command"))
        self.assertIn("HP+14", plate.get("text", ""))
        self.assertIn("STA+18", plate.get("text", ""))
        self.assertEqual("1", chowder.get("badge"))
        self.assertEqual("use Riverlight Chowder", chowder.get("command"))
        self.assertIn("MP+14", chowder.get("text", ""))

    def test_combat_view_lists_enemy_target_consumables(self):
        room = DummyRoom()
        rogue = DummyCharacter(
            7,
            "Dad",
            room,
            "rogue",
            {"hp": 20, "mana": 0, "stamina": 12},
            {"max_hp": 24, "max_mana": 0, "max_stamina": 14},
            ["Backstab"],
            inventory=[{"template": "fireflask", "quantity": 1}],
        )
        encounter = DummyEncounter(
            room,
            [rogue],
            [
                {"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16},
                {"id": "e2", "key": "Mud Lurker", "hp": 13, "max_hp": 18},
            ],
        )

        view = build_combat_view(encounter, rogue)
        items = _section(view, "Items")
        fireflask = _item(items, "Fire Flask")

        self.assertEqual("1", fireflask.get("badge"))
        self.assertIsNone(fireflask.get("command"))
        self.assertEqual("Fire Flask Target", fireflask.get("picker", {}).get("title"))
        self.assertIn("DMG 16-20", fireflask.get("text", ""))

    def test_combat_view_lists_cleanse_consumables_for_allies(self):
        room = DummyRoom()
        cleric = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 20, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal"],
            inventory=[{"template": "purity_salts", "quantity": 1}],
        )
        ally = DummyCharacter(
            8,
            "Peep",
            room,
            "warrior",
            {"hp": 17, "mana": 0, "stamina": 9},
            {"max_hp": 26, "max_mana": 0, "max_stamina": 12},
            ["Strike"],
        )
        encounter = DummyEncounter(
            room,
            [cleric, ally],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        view = build_combat_view(encounter, cleric)
        items = _section(view, "Items")
        salts = _item(items, "Purity Salts")

        self.assertEqual("use Purity Salts", salts.get("command"))
        self.assertIsNone(salts.get("picker"))
        self.assertEqual("Purity Salts Target", salts.get("actions", [])[0].get("picker", {}).get("title"))
        self.assertIn("CLEANSE", salts.get("text", ""))

    def test_combat_view_lists_guard_consumables_for_allies(self):
        room = DummyRoom()
        cleric = DummyCharacter(
            7,
            "Dad",
            room,
            "cleric",
            {"hp": 20, "mana": 18, "stamina": 6},
            {"max_hp": 24, "max_mana": 20, "max_stamina": 10},
            ["Heal"],
            inventory=[{"template": "ward_dust", "quantity": 1}],
        )
        ally = DummyCharacter(
            8,
            "Peep",
            room,
            "warrior",
            {"hp": 17, "mana": 0, "stamina": 9},
            {"max_hp": 26, "max_mana": 0, "max_stamina": 12},
            ["Strike"],
        )
        encounter = DummyEncounter(
            room,
            [cleric, ally],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        view = build_combat_view(encounter, cleric)
        items = _section(view, "Items")
        dust = _item(items, "Ward Dust")

        self.assertEqual("use Ward Dust", dust.get("command"))
        self.assertIsNone(dust.get("picker"))
        self.assertEqual("Ward Dust Target", dust.get("actions", [])[0].get("picker", {}).get("title"))
        self.assertIn("GUARD 12", dust.get("text", ""))


if __name__ == "__main__":
    unittest.main()
