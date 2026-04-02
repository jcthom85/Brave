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

from world.browser_views import build_sheet_view
from world.data.character_options import CLASSES, RACES
from world.resonance import get_resource_label


def _section(view, label):
    for section in view.get("sections", []):
        if section.get("label") == label:
            return section
    raise AssertionError(f"Missing section {label}")


class DummyCharacter:
    def __init__(self, *, meal_buff=None):
        self.key = "Dad"
        self.location = None
        self.db = SimpleNamespace(
            brave_race="human",
            brave_class="warrior",
            brave_level=6,
            brave_xp=120,
            brave_silver=34,
            brave_primary_stats={
                "strength": 7,
                "agility": 5,
                "intellect": 2,
                "spirit": 3,
                "vitality": 6,
            },
            brave_derived_stats={
                "max_hp": 48,
                "max_mana": 18,
                "max_stamina": 24,
                "attack_power": 12,
                "spell_power": 4,
                "armor": 9,
                "accuracy": 11,
                "dodge": 7,
            },
            brave_resources={
                "hp": 42,
                "mana": 10,
                "stamina": 20,
            },
            brave_meal_buff=meal_buff or {},
        )

    def get_active_meal_bonuses(self):
        return {"stamina": 5}


class SheetViewTests(unittest.TestCase):
    def test_sheet_view_uses_featured_status_card_and_minimal_header(self):
        character = DummyCharacter()

        with (
            patch("world.browser_views.split_unlocked_abilities", return_value=(["Shield Bash", "War Cry"], ["Iron Stance"], [])),
            patch("world.browser_views.format_ability_display", side_effect=lambda ability, _: ability),
            patch("world.browser_views.get_resonance_key", return_value="fantasy"),
            patch("world.browser_views.get_resonance_label", return_value="Fantasy Resonance"),
            patch("world.browser_views.get_active_blessing", return_value=None),
        ):
            view = build_sheet_view(character)

        self.assertEqual("sheet", view.get("variant"))
        self.assertEqual("", view.get("eyebrow"))
        self.assertEqual([], view.get("chips"))
        self.assertEqual("Close", view.get("back_action", {}).get("label"))
        self.assertEqual("Character Sheet", view.get("title"))
        self.assertEqual("", view.get("subtitle"))

        status = view.get("sections", [])[0]
        self.assertEqual("status", status.get("variant"))
        self.assertTrue(status.get("hide_label"))
        self.assertEqual("wide", status.get("span"))

        status_entry = status.get("items", [])[0]
        self.assertEqual(character.key, status_entry.get("title"))
        self.assertEqual(
            f"{RACES['human']['name']} {CLASSES['warrior']['name']} · Level 6",
            status_entry.get("meta"),
        )
        self.assertEqual(
            [
                get_resource_label("hp", character),
                get_resource_label("mana", character),
                get_resource_label("stamina", character),
            ],
            [meter.get("label") for meter in status_entry.get("meters", [])],
        )

        status_chips = [chip.get("label") for chip in status_entry.get("chips", [])]
        self.assertNotIn("34 silver", status_chips)
        self.assertNotIn("Resolve", status_chips)

        attributes = _section(view, "Attributes")
        stats = _section(view, "Stats")
        abilities = _section(view, "Abilities")
        passives = _section(view, "Passive Traits")
        self.assertEqual("stats", attributes.get("variant"))
        self.assertEqual("stats", stats.get("variant"))
        self.assertEqual(["Shield Bash", "War Cry"], [item.get("text") for item in abilities.get("items", [])])
        self.assertEqual(["Resolve", "Iron Stance"], [item.get("text") for item in passives.get("items", [])])
        self.assertTrue(abilities.get("items", [])[0].get("picker"))
        self.assertIn("Costs", abilities.get("items", [])[0].get("tooltip", ""))
        self.assertTrue(passives.get("items", [])[0].get("picker"))
        self.assertIn("Passive trait", passives.get("items", [])[0].get("tooltip", ""))

    def test_sheet_view_collects_effect_entries(self):
        character = DummyCharacter(meal_buff={"name": "Camp Stew", "cozy": True})

        with (
            patch("world.browser_views.split_unlocked_abilities", return_value=([], [], ["Mystery Edge"])),
            patch("world.browser_views.format_ability_display", side_effect=lambda ability, _: ability),
            patch("world.browser_views.get_resonance_key", return_value="clockwork"),
            patch("world.browser_views.get_resonance_label", return_value="Clockwork Resonance"),
            patch(
                "world.browser_views.get_active_blessing",
                return_value={
                    "name": "Dawn Ward",
                    "duration": "Until sunset.",
                    "bonuses": {"armor": 2},
                },
            ),
            patch(
                "world.browser_views._format_context_bonus_summary",
                side_effect=[
                    "Strength +1, Agility +1, Intellect +1, Spirit +1, Vitality +1",
                    "Stamina +5",
                    "Armor +2",
                ],
            ),
        ):
            view = build_sheet_view(character)

        effects = _section(view, "Effects")
        passives = _section(view, "Passive Traits")
        self.assertEqual("effects", effects.get("variant"))
        self.assertEqual("wide", effects.get("span"))
        self.assertEqual(["Resolve"], [item.get("text") for item in passives.get("items", [])])
        self.assertEqual(
            ["Camp Stew", "Dawn Ward", "Clockwork Resonance", "Progression Notes"],
            [item.get("title") for item in effects.get("items", [])],
        )
        self.assertEqual(
            ["Cozy"],
            [chip.get("label") for chip in effects.get("items", [])[0].get("chips", [])],
        )


if __name__ == "__main__":
    unittest.main()
