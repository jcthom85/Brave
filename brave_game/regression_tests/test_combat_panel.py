import os
import unittest
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.browser_panels import build_combat_panel


class DummyParticipant:
    def __init__(self, key):
        self.key = key


class DummyEncounter:
    def __init__(self, participants, enemies, *, atb_states=None):
        self._participants = list(participants)
        self._enemies = list(enemies)
        self._atb_states = dict(atb_states or {})

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return list(self._participants)

    def _get_actor_atb_state(self, character=None, enemy=None):
        if character is not None:
            return self._atb_states.get(f"p:{character.key}", {"phase": "charging", "gauge": 0})
        if enemy is not None:
            return self._atb_states.get(f"e:{enemy['id']}", {"phase": "charging", "gauge": 0})
        return {"phase": "charging", "gauge": 0}


class CombatPanelTests(unittest.TestCase):
    def test_combat_panel_omits_round_chip_and_uses_ally_foe_counts(self):
        encounter = DummyEncounter(
            [DummyParticipant("Dad"), DummyParticipant("Peep")],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
            atb_states={"p:Dad": {"phase": "ready"}, "p:Peep": {"phase": "charging", "gauge": 45}, "e:e1": {"phase": "winding", "ticks_remaining": 1}},
        )

        panel = build_combat_panel(encounter)
        chip_labels = [chip.get("label") for chip in panel.get("chips", [])]
        party_items = panel.get("sections", [])[0].get("items", [])
        enemy_items = panel.get("sections", [])[1].get("items", [])

        self.assertEqual(["2 allies", "1 foe", "2 queued", "0 open"], chip_labels)
        self.assertFalse(any("round" in label.lower() for label in chip_labels))
        self.assertEqual(["READY", "ATB 11%"], [item.get("badge") for item in party_items])
        self.assertEqual("ready", party_items[0].get("meta"))
        self.assertEqual("W1", enemy_items[0].get("badge"))
        self.assertEqual(2, len(panel.get("sections", [])))

    def test_combat_panel_projects_live_charge_percent(self):
        encounter = DummyEncounter(
            [DummyParticipant("Dad")],
            [],
            atb_states={
                "p:Dad": {
                    "phase": "charging",
                    "gauge": 0,
                    "ready_gauge": 400,
                    "phase_start_gauge": 0,
                    "phase_started_at_ms": 1_000,
                    "phase_duration_ms": 4_000,
                }
            },
        )

        with patch("world.browser_panels.time.time", return_value=3.0):
            panel = build_combat_panel(encounter)

        party_items = panel.get("sections", [])[0].get("items", [])
        self.assertEqual(["ATB 50%"], [item.get("badge") for item in party_items])

    def test_combat_panel_keeps_charge_percent_live_while_turn_lock_is_active(self):
        encounter = DummyEncounter(
            [DummyParticipant("Dad")],
            [],
            atb_states={
                "p:Dad": {
                    "phase": "charging",
                    "gauge": 0,
                    "ready_gauge": 400,
                    "phase_start_gauge": 0,
                    "phase_started_at_ms": 1_000,
                    "phase_duration_ms": 4_000,
                }
            },
        )
        encounter.db = getattr(encounter, "db", None) or type("DB", (), {})()
        encounter.db.atb_turn_lock_until_ms = 4_000

        with patch("world.browser_panels.time.time", return_value=3.0):
            panel = build_combat_panel(encounter)

        party_items = panel.get("sections", [])[0].get("items", [])
        self.assertEqual(["ATB 50%"], [item.get("badge") for item in party_items])

    def test_combat_panel_keeps_near_ready_charge_below_full(self):
        encounter = DummyEncounter(
            [DummyParticipant("Dad")],
            [{"id": "e1", "key": "Old Greymaw", "hp": 28, "max_hp": 32}],
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

        with patch("world.browser_panels.time.time", return_value=2.0):
            panel = build_combat_panel(encounter)

        enemy_items = panel.get("sections", [])[1].get("items", [])
        self.assertEqual(["ATB 99%"], [item.get("badge") for item in enemy_items])


if __name__ == "__main__":
    unittest.main()
