import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
    def __init__(self, room, participants, enemies, *, pending=None, states=None, atb_states=None, title="Mire Teeth"):
        self.obj = room
        self.db = SimpleNamespace(round=2, encounter_title=title)
        self._participants = list(participants)
        self._enemies = list(enemies)
        self._pending = dict(pending or {})
        self._states = dict(states or {})
        self._atb_states = dict(atb_states or {})

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

    def _get_actor_atb_state(self, character=None, enemy=None):
        if character is not None:
            return self._atb_states.get(f"p:{character.id}", {"phase": "charging", "gauge": 0})
        if enemy is not None:
            return self._atb_states.get(f"e:{enemy['id']}", {"phase": "charging", "gauge": 0})
        return {"phase": "charging", "gauge": 0}


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


def _action(view, label):
    for action in view.get("actions", []):
        if action.get("label") == label:
            return action
    raise AssertionError(f"Missing action {label}")


def _picker_option(picker, label, *, meta=None):
    for option in picker.get("options", []):
        if option.get("label") != label:
            continue
        if meta is not None and option.get("meta") != meta:
            continue
        return option
    raise AssertionError(f"Missing picker option {label} / {meta}")


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
            atb_states={
                "p:7": {"phase": "ready", "gauge": 100, "ready_gauge": 100},
                "p:8": {"phase": "charging", "gauge": 45, "ready_gauge": 100},
                "e:e1": {"phase": "charging", "gauge": 70, "ready_gauge": 100},
            },
        )
        encounter.db.pending_actions = {"7": {"kind": "ability", "ability": "heal", "target": 8}}

        view = build_combat_view(encounter, healer)
        abilities_action = _action(view, "Abilities")
        heal_item = _picker_option(abilities_action.get("picker", {}), "Heal", meta="Heal · 10 MP")
        smite_item = _picker_option(abilities_action.get("picker", {}), "Smite", meta="Smite · 8 MP")

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
        self.assertEqual("use Smite = e1", smite_item.get("command"))
        self.assertEqual([], view.get("chips", []))
        self.assertEqual("2 Allies • 1 Foe", view.get("subtitle", ""))
        self.assertEqual(["Abilities", "Items", "Flee"], [action.get("label") for action in view.get("actions", [])])
        self.assertIsNot(_action(view, "Flee").get("icon_only"), True)

        party = _section(view, "Party")
        dad_entry = _entry(party, "Dad")
        peep_entry = _entry(party, "Peep")
        self.assertEqual(
            [("ATB", "100 / 100"), ("HP", "20 / 24"), ("STA", "6 / 10"), ("MP", "18 / 20")],
            [(meter.get("label"), meter.get("value")) for meter in dad_entry.get("meters", [])],
        )
        self.assertEqual(
            [("ATB", "45 / 100"), ("HP", "17 / 26"), ("STA", "9 / 12")],
            [(meter.get("label"), meter.get("value")) for meter in peep_entry.get("meters", [])],
        )
        self.assertIn("Ready", [chip.get("label") for chip in dad_entry.get("chips", [])])
        self.assertIn("Targeted", [chip.get("label") for chip in peep_entry.get("chips", [])])

        enemies_section = _section(view, "Enemies")
        wolf_entry = _entry(enemies_section, "Bog Wolf")
        self.assertEqual(
            [("ATB", "70 / 100"), ("HP", "11 / 16")],
            [(meter.get("label"), meter.get("value")) for meter in wolf_entry.get("meters", [])],
        )
        self.assertEqual([], wolf_entry.get("lines", []))

    def test_enemy_windup_surfaces_named_telegraph_in_view(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "p:7": {"phase": "charging", "gauge": 40},
                "e:e1": {
                    "phase": "winding",
                    "ticks_remaining": 1,
                    "current_action": {"kind": "enemy_attack", "label": "Brush Pounce"},
                },
            },
        )

        view = build_combat_view(encounter, warrior)
        enemies_section = _section(view, "Enemies")
        enemy_entry = _entry(enemies_section, "Old Greymaw")

        self.assertIn("Brush Pounce", enemy_entry.get("lines", []))
        self.assertIn("Winding 1", [chip.get("label") for chip in enemy_entry.get("chips", [])])
        self.assertEqual(
            [("ATB", "100 / 100"), ("HP", "28 / 32")],
            [(meter.get("label"), meter.get("value")) for meter in enemy_entry.get("meters", [])],
        )

    def test_atb_meter_stays_full_during_windup_and_resets_empty_for_recovery(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "p:7": {
                    "phase": "recovering",
                    "ticks_remaining": 1,
                    "timing": {"recovery_ticks": 2},
                },
                "e:e1": {
                    "phase": "winding",
                    "ticks_remaining": 1,
                    "timing": {"windup_ticks": 2},
                    "current_action": {"kind": "enemy_attack", "label": "Brush Pounce"},
                },
            },
        )

        view = build_combat_view(encounter, warrior)
        party_section = _section(view, "Party")
        enemies_section = _section(view, "Enemies")
        warrior_entry = _entry(party_section, "Dad")
        enemy_entry = _entry(enemies_section, "Old Greymaw")

        self.assertEqual(
            [("ATB", "0 / 100"), ("HP", "20 / 24"), ("STA", "12 / 14")],
            [(meter.get("label"), meter.get("value")) for meter in warrior_entry.get("meters", [])],
        )
        self.assertEqual(
            [("ATB", "100 / 100"), ("HP", "28 / 32")],
            [(meter.get("label"), meter.get("value")) for meter in enemy_entry.get("meters", [])],
        )
        self.assertIn("Recovering 1", [chip.get("label") for chip in warrior_entry.get("chips", [])])

    def test_atb_meter_projects_live_charge_progress_on_view_refresh(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "p:7": {
                    "phase": "charging",
                    "gauge": 0,
                    "ready_gauge": 400,
                    "phase_start_gauge": 0,
                    "phase_started_at_ms": 1_000,
                    "phase_duration_ms": 4_000,
                }
            },
        )

        with patch("world.browser_views.time.time", return_value=3.0):
            view = build_combat_view(encounter, warrior)

        party_section = _section(view, "Party")
        warrior_entry = _entry(party_section, "Dad")
        self.assertEqual(
            [("ATB", "50 / 100"), ("HP", "20 / 24"), ("STA", "12 / 14")],
            [(meter.get("label"), meter.get("value")) for meter in warrior_entry.get("meters", [])],
        )
        atb_meter = warrior_entry.get("meters", [])[0]
        self.assertEqual(
            {
                "phase": "charging",
                "gauge": 200,
                "phase_start_gauge": 0,
                "phase_duration_ms": 4000,
                "phase_remaining_ms": 2000,
                "ready_gauge": 400,
            },
            {
                "phase": atb_meter.get("meta", {}).get("phase"),
                "gauge": atb_meter.get("meta", {}).get("gauge"),
                "phase_start_gauge": atb_meter.get("meta", {}).get("phase_start_gauge"),
                "phase_duration_ms": atb_meter.get("meta", {}).get("phase_duration_ms"),
                "phase_remaining_ms": atb_meter.get("meta", {}).get("phase_remaining_ms"),
                "ready_gauge": atb_meter.get("meta", {}).get("ready_gauge"),
            },
        )
        self.assertAlmostEqual(50.0, atb_meter.get("percent"), places=2)

    def test_atb_meter_preserves_fractional_charge_percent(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "p:7": {
                    "phase": "charging",
                    "gauge": 167,
                    "ready_gauge": 400,
                    "phase_start_gauge": 167,
                    "phase_started_at_ms": 1_000,
                    "phase_duration_ms": 2_330,
                }
            },
        )

        with patch("world.browser_views.time.time", return_value=1.0):
            view = build_combat_view(encounter, warrior)

        atb_meter = _entry(_section(view, "Party"), "Dad").get("meters", [])[0]
        self.assertEqual("41 / 100", atb_meter.get("value"))
        self.assertAlmostEqual(41.75, atb_meter.get("percent"), places=2)

    def test_atb_meter_repairs_future_charge_start_when_field_is_not_locked(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "p:7": {
                    "phase": "charging",
                    "gauge": 100,
                    "ready_gauge": 400,
                    "fill_rate": 100,
                    "phase_start_gauge": 100,
                    "phase_started_at_ms": 5_000,
                    "phase_duration_ms": 3_000,
                }
            },
        )

        with patch("world.browser_views.time.time", return_value=4.0):
            view = build_combat_view(encounter, warrior)

        atb_meter = _entry(_section(view, "Party"), "Dad").get("meters", [])[0]
        self.assertAlmostEqual(25.0, atb_meter.get("percent"), places=2)
        self.assertEqual(4_000, atb_meter.get("meta", {}).get("phase_started_at_ms"))
        self.assertEqual(3_000, atb_meter.get("meta", {}).get("phase_duration_ms"))

    def test_atb_meter_freezes_charge_projection_while_action_is_in_progress(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "p:7": {
                    "phase": "charging",
                    "gauge": 0,
                    "ready_gauge": 400,
                    "phase_start_gauge": 0,
                    "phase_started_at_ms": 1_000,
                    "phase_duration_ms": 4_000,
                },
                "e:e1": {
                    "phase": "winding",
                    "ticks_remaining": 1,
                    "phase_started_at_ms": 2_500,
                    "phase_duration_ms": 1_000,
                    "timing": {"windup_ticks": 1},
                    "current_action": {"kind": "enemy_attack", "label": "Brush Pounce"},
                },
            },
        )

        with patch("world.browser_views.time.time", return_value=3.0):
            view = build_combat_view(encounter, warrior)

        party_section = _section(view, "Party")
        warrior_entry = _entry(party_section, "Dad")
        self.assertEqual(
            [("ATB", "0 / 100"), ("HP", "20 / 24"), ("STA", "12 / 14")],
            [(meter.get("label"), meter.get("value")) for meter in warrior_entry.get("meters", [])],
        )
        self.assertTrue(view.get("atb_locked"))
        self.assertEqual(3_500, view.get("atb_lock_until_ms"))
        self.assertEqual(
            {
                "phase_duration_ms": 4_000,
                "phase_remaining_ms": 4_000,
                "phase_started_at_ms": 1_000,
            },
            {
                "phase_duration_ms": warrior_entry.get("meters", [])[0].get("meta", {}).get("phase_duration_ms"),
                "phase_remaining_ms": warrior_entry.get("meters", [])[0].get("meta", {}).get("phase_remaining_ms"),
                "phase_started_at_ms": warrior_entry.get("meters", [])[0].get("meta", {}).get("phase_started_at_ms"),
            },
        )

    def test_atb_meter_freezes_charge_projection_while_turn_lock_is_active(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "p:7": {
                    "phase": "charging",
                    "gauge": 0,
                    "ready_gauge": 400,
                    "phase_start_gauge": 0,
                    "phase_started_at_ms": 1_000,
                    "phase_duration_ms": 4_000,
                }
            },
        )
        encounter.db.atb_turn_lock_until_ms = 4_000

        with patch("world.browser_views.time.time", return_value=3.0):
            view = build_combat_view(encounter, warrior)

        party_section = _section(view, "Party")
        warrior_entry = _entry(party_section, "Dad")
        self.assertEqual(
            [("ATB", "0 / 100"), ("HP", "20 / 24"), ("STA", "12 / 14")],
            [(meter.get("label"), meter.get("value")) for meter in warrior_entry.get("meters", [])],
        )
        self.assertTrue(view.get("atb_locked"))
        self.assertEqual(4_000, view.get("atb_lock_until_ms"))

    def test_atb_meter_stays_below_full_for_near_ready_charging_actor(self):
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
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32, "template_key": "old_greymaw"}],
            atb_states={
                "e:e1": {
                    "phase": "charging",
                    "gauge": 399,
                    "ready_gauge": 400,
                    "phase_start_gauge": 399,
                    "phase_started_at_ms": 1_000,
                    "phase_duration_ms": 250,
                }
            },
        )

        with patch("world.browser_views.time.time", return_value=2.0):
            view = build_combat_view(encounter, warrior)

        enemies_section = _section(view, "Enemies")
        enemy_entry = _entry(enemies_section, "Old Greymaw")
        self.assertEqual(
            [("ATB", "99 / 100"), ("HP", "28 / 32")],
            [(meter.get("label"), meter.get("value")) for meter in enemy_entry.get("meters", [])],
        )

    def test_duplicate_enemy_names_are_numbered_in_view(self):
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
                {"id": "e1", "key": "Grave Crow", "hp": 9, "max_hp": 12, "template_key": "grave_crow"},
                {"id": "e2", "key": "Grave Crow", "hp": 9, "max_hp": 12, "template_key": "grave_crow"},
            ],
        )

        view = build_combat_view(encounter, warrior)
        enemies_section = _section(view, "Enemies")

        crow_one = _entry(enemies_section, "Grave Crow 1")
        crow_two = _entry(enemies_section, "Grave Crow 2")

        self.assertEqual("attack e1", crow_one.get("command"))
        self.assertEqual("attack e2", crow_two.get("command"))
        self.assertEqual("e:e1", crow_one.get("entry_ref"))
        self.assertEqual("e:e2", crow_two.get("entry_ref"))
        self.assertIsNone(crow_one.get("meta"))
        self.assertIsNone(crow_one.get("badge"))

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
        items_action = _action(view, "Items")
        bandage = _picker_option(items_action.get("picker", {}), "Field Bandage", meta="Field Bandage · HP+18")

        self.assertEqual("use Field Bandage", bandage.get("command"))

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
        abilities_action = _action(view, "Abilities")
        self.assertEqual([], abilities_action.get("picker", {}).get("options", []))
        self.assertEqual(["No usable combat abilities."], abilities_action.get("picker", {}).get("body", []))

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
        self.assertIsNot(wolf.get("selected"), True)
        self.assertIs(lurker.get("selected"), True)

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
        items_action = _action(view, "Items")
        plate = _picker_option(items_action.get("picker", {}), "Crisped Perch Plate")
        chowder = _picker_option(items_action.get("picker", {}), "Riverlight Chowder")

        self.assertEqual("use Crisped Perch Plate", plate.get("command"))
        self.assertIn("HP+14", plate.get("meta", ""))
        self.assertIn("STA+18", plate.get("meta", ""))
        self.assertEqual("use Riverlight Chowder", chowder.get("command"))
        self.assertIn("MP+14", chowder.get("meta", ""))

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
        items_action = _action(view, "Items")
        fireflask = _picker_option(items_action.get("picker", {}), "Fire Flask", meta="Fire Flask · DMG 16-20")

        self.assertIsNone(fireflask.get("command"))
        self.assertEqual("Fire Flask Target", fireflask.get("picker", {}).get("title"))

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
        items_action = _action(view, "Items")
        salts = _picker_option(items_action.get("picker", {}), "Purity Salts")
        salts_target = _picker_option(items_action.get("picker", {}), "Purity Salts", meta="Target Ally")

        self.assertEqual("use Purity Salts", salts.get("command"))
        self.assertIsNone(salts.get("picker"))
        self.assertIn("CLEANSE", salts.get("meta", ""))
        self.assertEqual("Purity Salts Target", salts_target.get("picker", {}).get("title"))

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
        items_action = _action(view, "Items")
        dust = _picker_option(items_action.get("picker", {}), "Ward Dust", meta="Ward Dust · GUARD 12")
        dust_target = _picker_option(items_action.get("picker", {}), "Ward Dust", meta="Target Ally")

        self.assertEqual("use Ward Dust", dust.get("command"))
        self.assertIsNone(dust.get("picker"))
        self.assertEqual("Ward Dust Target", dust_target.get("picker", {}).get("title"))


if __name__ == "__main__":
    unittest.main()
