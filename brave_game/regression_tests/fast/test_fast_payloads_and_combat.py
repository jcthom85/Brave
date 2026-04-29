import unittest
from types import SimpleNamespace

from world.browser_context import CLASSES, ITEM_TEMPLATES
from world.browser_formatting import _format_context_bonus_summary, _format_item_value_text, _format_restore_summary
from world.browser_ui import _action, _entry, _hp_meter_tone, _item, _make_view, _meter, _picker, _section
from world.combat_actor_utils import (
    _ally_actor_id,
    _combat_entry_ref,
    _combat_target_id,
    _combat_target_name,
    _enemy_damage_type,
    _is_companion_actor,
)


class DummyCharacter:
    id = 42
    key = "Dad"

    def __init__(self):
        self.db = SimpleNamespace(brave_race="human")


class FastPayloadBuilderTests(unittest.TestCase):
    def test_browser_primitives_build_stable_payload_shapes(self):
        picker = _picker(
            "Choose",
            subtitle="Pick one",
            options=[{"label": "A", "command": "do a"}],
        )
        entry = _entry(
            "Title",
            meta="Meta",
            lines=["Line"],
            icon="star",
            picker=picker,
            meters=[_meter("HP", 7, 10, tone="good")],
        )
        view = _make_view(
            "Eyebrow",
            "Title",
            eyebrow_icon="flag",
            title_icon="star",
            sections=[_section("Section", "list", "entries", items=[entry])],
            actions=[_action("Go", "go", "play_arrow")],
            back=True,
        )

        self.assertEqual("Title", view["title"])
        self.assertEqual("Close", view["back_action"]["label"])
        self.assertEqual("70 / 100", _meter("ATB", 70, 100)["value"])
        self.assertEqual("danger", _hp_meter_tone(2, 10))
        self.assertEqual("Title", view["sections"][0]["items"][0]["title"])
        self.assertEqual({"text": "Thing", "icon": "category"}, _item("Thing", icon="category"))

    def test_browser_context_and_formatting_use_registry_data(self):
        character = DummyCharacter()

        self.assertIn("warrior", CLASSES)
        self.assertEqual("Militia Blade", ITEM_TEMPLATES["militia_blade"]["name"])
        self.assertEqual("HP +5, Stamina +2", _format_restore_summary({"hp": 5, "stamina": 2}, character))
        self.assertEqual("Attack +3", _format_context_bonus_summary({"attack_power": 3}, character))
        self.assertEqual("4 silver each · 12 total", _format_item_value_text({"value": 4}, 3))


class FastCombatActorHelperTests(unittest.TestCase):
    def test_combat_actor_refs_and_names_cover_players_enemies_and_companions(self):
        player = SimpleNamespace(id=7, key="Kest")
        enemy = {"id": "e1", "key": "Bog Wolf", "template_key": "forest_wolf"}
        companion = {"kind": "companion", "id": "c1", "key": "Marsh Hound"}

        self.assertEqual(7, _combat_target_id(player))
        self.assertEqual("Kest", _combat_target_name(player))
        self.assertEqual("Bog Wolf", _combat_target_name(enemy))
        self.assertEqual("p:7", _combat_entry_ref(player))
        self.assertEqual("e:e1", _combat_entry_ref(enemy))
        self.assertEqual("c:c1", _combat_entry_ref(companion))
        self.assertTrue(_is_companion_actor(companion))
        self.assertEqual("c1", _ally_actor_id(companion))

    def test_enemy_damage_type_mapping_is_available_without_combat_script_import(self):
        self.assertEqual("physical", _enemy_damage_type({"template_key": "tower_archer"}))
        self.assertEqual("shadow", _enemy_damage_type({"template_key": "hollow_wisp"}))
        self.assertEqual("nature", _enemy_damage_type({"template_key": "fen_wisp"}))
        self.assertEqual("lightning", _enemy_damage_type({"template_key": "relay_tick"}))
        self.assertEqual("physical", _enemy_damage_type({"template_key": "unknown"}))


if __name__ == "__main__":
    unittest.main()
