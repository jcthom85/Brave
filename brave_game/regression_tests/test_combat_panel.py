import os
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.browser_panels import build_combat_panel


class DummyParticipant:
    def __init__(self, key):
        self.key = key


class DummyEncounter:
    def __init__(self, participants, enemies):
        self._participants = list(participants)
        self._enemies = list(enemies)

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return list(self._participants)


class CombatPanelTests(unittest.TestCase):
    def test_combat_panel_omits_round_chip_and_uses_ally_foe_counts(self):
        encounter = DummyEncounter(
            [DummyParticipant("Dad"), DummyParticipant("Peep")],
            [{"id": "e1", "key": "Bog Wolf", "hp": 11, "max_hp": 16}],
        )

        panel = build_combat_panel(encounter)
        chip_labels = [chip.get("label") for chip in panel.get("chips", [])]

        self.assertEqual(["2 allies", "1 foe"], chip_labels)
        self.assertFalse(any("round" in label.lower() for label in chip_labels))


if __name__ == "__main__":
    unittest.main()
