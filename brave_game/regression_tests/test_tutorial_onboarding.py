import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.resting import room_allows_rest
from world.browser_views import build_combat_view
from world.content import get_content_registry
from world.interactions import get_entity_response
from world.questing import advance_enemy_defeat, advance_room_visit, ensure_starter_quests, unlock_quest
from world.questing import get_tracked_quest_payload
from world.tutorial import (
    LANTERNFALL_WELCOME_PAGES,
    begin_tutorial,
    ensure_tutorial_state,
    get_lanternfall_intro_text,
    get_lanternfall_recap_text,
    get_tutorial_mechanical_guidance,
    get_tutorial_combat_focus,
    get_tutorial_exit_block,
    get_tutorial_entity_response,
    is_tutorial_solo_combat_room,
    record_command_event,
    record_encounter_victory,
    should_show_lanternfall_recap,
)


class DummyCharacter:
    def __init__(self):
        self.db = SimpleNamespace(
            brave_tutorial=None,
            brave_tutorial_current_step=None,
            brave_quests={},
            brave_tracked_quest=None,
            brave_track_suppressed=False,
            brave_harl_cellar_job_assigned=False,
            brave_inventory=[],
            brave_silver=0,
            brave_xp=0,
            brave_level=1,
            brave_class="warrior",
        )
        self.ndb = SimpleNamespace()
        self.account = SimpleNamespace(db=SimpleNamespace(brave_tutorial_completed=False))
        self.home = None
        self.location = None

    def grant_xp(self, amount):
        self.db.brave_xp += amount
        return []

    def add_item_to_inventory(self, template_id, quantity=1):
        self.db.brave_inventory.append({"template": template_id, "quantity": quantity})


def _room(room_id, *, safe=True, rest_allowed=False):
    return SimpleNamespace(db=SimpleNamespace(brave_room_id=room_id, brave_safe=safe, brave_rest_allowed=rest_allowed))


def _entity(entity_id):
    return SimpleNamespace(key=entity_id.title().replace("_", " "), db=SimpleNamespace(brave_entity_id=entity_id, brave_entity_kind="npc"))


class TutorialOnboardingTests(unittest.TestCase):
    def test_lanternfall_intro_sets_urgent_first_minute(self):
        self.assertEqual("A New Hero Arrives!", LANTERNFALL_WELCOME_PAGES[0]["title"])
        self.assertEqual(3, len(LANTERNFALL_WELCOME_PAGES))
        intro = get_lanternfall_intro_text()

        self.assertIn("bell hits before dawn", intro)
        self.assertIn("road lantern has gone black", intro)
        self.assertIn("talk tamsin", intro)

    def test_lanternfall_intro_does_not_frontload_system_lessons(self):
        combined = " ".join(page["text"].lower() for page in LANTERNFALL_WELCOME_PAGES)

        for forbidden in (
            "gear",
            "pack",
            "combat",
            "class",
            "status",
            "reward",
            "rest",
            "journal",
            "map",
            "sheet",
            "party",
            "captain harl",
            "harl",
        ):
            self.assertNotIn(forbidden, combined)

    def test_lanternfall_recap_guides_tutorial_skipped_characters_to_harl(self):
        character = DummyCharacter()
        character.db.brave_tutorial = {"status": "completed", "step": None, "flags": {}}
        ensure_starter_quests(character)
        character.location = _room("brambleford_training_yard")

        self.assertTrue(should_show_lanternfall_recap(character))
        self.assertIn("talk harl", get_lanternfall_recap_text())

    def test_harl_talk_unlocks_rat_job_instead_of_spawn_doing_it(self):
        character = DummyCharacter()
        character.db.brave_tutorial = {"status": "completed", "step": None, "flags": {}}
        ensure_starter_quests(character)
        character.location = _room("brambleford_training_yard")

        self.assertEqual("active", character.db.brave_quests["practice_makes_heroes"]["status"])
        self.assertNotIn("rats_in_the_kettle", character.db.brave_quests)
        self.assertEqual("practice_makes_heroes", character.db.brave_tracked_quest)

        response = get_entity_response(character, _entity("captain_harl_rowan"), "talk", is_action=True)

        self.assertIn("south lantern is out", response.lower())
        self.assertTrue(character.db.brave_harl_cellar_job_assigned)
        self.assertEqual("completed", character.db.brave_quests["practice_makes_heroes"]["status"])
        self.assertEqual("active", character.db.brave_quests["rats_in_the_kettle"]["status"])
        self.assertEqual("rats_in_the_kettle", character.db.brave_tracked_quest)

    def test_unlocking_quest_sends_new_quest_popup_payload(self):
        character = DummyCharacter()

        with patch("world.browser_panels.send_webclient_event") as send_webclient_event:
            self.assertTrue(unlock_quest(character, "roadside_howls"))

        popup_payloads = [
            call.kwargs["brave_quest_started"]
            for call in send_webclient_event.call_args_list
            if "brave_quest_started" in call.kwargs
        ]
        self.assertEqual(
            [
                {
                    "title": "Roadside Howls",
                    "next_step": "Follow the cut fences east and thin the goblin cutters still working along Goblin Road.",
                }
            ],
            popup_payloads,
        )

    def test_entering_training_yard_does_not_complete_practice_before_harl(self):
        character = DummyCharacter()
        character.db.brave_tutorial = {"status": "completed", "step": None, "flags": {}}
        ensure_starter_quests(character)

        advance_room_visit(character, _room("brambleford_training_yard"))

        self.assertEqual("active", character.db.brave_quests["practice_makes_heroes"]["status"])
        self.assertFalse(character.db.brave_quests["practice_makes_heroes"]["objectives"][0]["completed"])
        self.assertNotIn("rats_in_the_kettle", character.db.brave_quests)

    def test_missing_rat_job_does_not_initialize_active_without_harl_assignment(self):
        character = DummyCharacter()
        character.db.brave_tutorial = {"status": "completed", "step": None, "flags": {}}
        character.db.brave_quests = {
            "practice_makes_heroes": {
                "status": "completed",
                "objectives": [
                    {
                        "description": "Report to Captain Harl Rowan after Wayfarer's Yard.",
                        "completed": True,
                        "progress": 1,
                        "required": 1,
                    }
                ],
            }
        }

        ensure_starter_quests(character)

        self.assertNotIn("rats_in_the_kettle", character.db.brave_quests)

    def test_tamsin_opens_with_road_alarm_not_generic_tutorial(self):
        character = DummyCharacter()
        begin_tutorial(character)

        response = get_tutorial_entity_response(character, _entity("sergeant_tamsin_vale"), "talk", is_action=True)

        self.assertIn("South road lantern went black", response)
        self.assertIn("cut harness", response)
        self.assertIn("Head east to Nella", response)
        self.assertTrue(character.db.brave_tutorial["flags"]["talked_tamsin"])

    def test_damaged_cart_shows_road_evidence_without_advancing_required_flow(self):
        character = DummyCharacter()
        begin_tutorial(character)

        response = get_tutorial_entity_response(character, _entity("tutorial_damaged_cart"), "read")
        state = ensure_tutorial_state(character)

        self.assertIn("clawed mud", response)
        self.assertIn("harness leather cut", response)
        self.assertFalse(state["flags"]["talked_tamsin"])

    def test_combat_lesson_requires_class_ability_and_rest_before_harl(self):
        character = DummyCharacter()
        begin_tutorial(character)

        for event in ("talked_tamsin", "visited_quartermaster_shed", "talked_nella", "viewed_gear", "viewed_pack", "read_supply_board", "returned_to_wayfarers_yard", "talked_brask"):
            if event in {"viewed_gear", "viewed_pack"}:
                record_command_event(character, event.removeprefix("viewed_"))
            else:
                state = ensure_tutorial_state(character)
                state["flags"][event] = True
                character.db.brave_tutorial = state

        self.assertEqual("clear_the_pens", ensure_tutorial_state(character)["step"])

        record_encounter_victory(character, _room("tutorial_vermin_pens", safe=False))
        self.assertEqual("clear_the_pens", ensure_tutorial_state(character)["step"])

        record_command_event(character, "class_ability")
        self.assertEqual("fit_your_clasp", ensure_tutorial_state(character)["step"])
        self.assertEqual([{"template": "wayfarer_clasp", "quantity": 1}], character.db.brave_inventory)

        record_command_event(character, "equip_gear")
        self.assertEqual("catch_your_breath", ensure_tutorial_state(character)["step"])

        record_command_event(character, "rest")
        self.assertEqual("through_the_gate", ensure_tutorial_state(character)["step"])

    def test_kit_before_gate_completes_immediately_on_final_flag(self):
        character = DummyCharacter()
        begin_tutorial(character)
        state = ensure_tutorial_state(character)
        state["flags"].update(
            {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "returned_to_wayfarers_yard": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": False,
            }
        )
        state["step"] = "pack_before_walk"
        character.db.brave_tutorial = state

        get_tutorial_entity_response(character, _entity("tutorial_supply_board"), "read", is_action=True)

        self.assertEqual("stand_your_ground", character.db.brave_tutorial["step"])
        self.assertTrue(character.db.brave_tutorial["flags"]["read_supply_board"])

    def test_tutorial_combat_is_solo_and_adds_combat_focus(self):
        character = DummyCharacter()
        begin_tutorial(character)
        state = ensure_tutorial_state(character)
        state["flags"].update(
            {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "returned_to_wayfarers_yard": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": True,
                "talked_brask": True,
            }
        )
        character.db.brave_tutorial = state
        encounter = SimpleNamespace(obj=_room("tutorial_vermin_pens", safe=False))

        self.assertTrue(is_tutorial_solo_combat_room(encounter.obj))
        focus = get_tutorial_combat_focus(character, encounter)
        self.assertEqual("Use Strike", focus[0]["title"])
        self.assertTrue(any("HP" in entry["text"] for entry in focus))

    def test_tutorial_combat_focus_is_rendered_as_overlay_guidance(self):
        class CombatDummyCharacter:
            def __init__(self):
                self.id = 7
                self.key = "Dad"
                self.db = SimpleNamespace(
                    brave_class="warrior",
                    brave_resources={"hp": 18, "mana": 0, "stamina": 8},
                    brave_derived_stats={"max_hp": 20, "max_mana": 0, "max_stamina": 10},
                    brave_inventory=[],
                    brave_tutorial=None,
                )
                self.ndb = SimpleNamespace()

            def ensure_brave_character(self):
                return None

            def get_unlocked_abilities(self):
                return ["Strike"]

        class CombatDummyEncounter:
            def __init__(self, room):
                self.obj = room
                self.interval = 1
                self.db = SimpleNamespace(round=2, encounter_title="Vermin Pens")
                self._participants = [character]
                self._enemies = [{"id": "e1", "template_key": "vermin_rat", "key": "Training Rat", "hp": 9, "max_hp": 9}]

            def get_active_enemies(self):
                return list(self._enemies)

            def get_active_participants(self):
                return list(self._participants)

            def _get_participant_state(self, participant):
                return {
                    "guard": 0,
                    "bleed_turns": 0,
                    "poison_turns": 0,
                    "curse_turns": 0,
                    "snare_turns": 0,
                    "feint_turns": 0,
                }

            def _get_actor_atb_state(self, character=None, enemy=None, companion=None):
                if enemy is not None:
                    return {"phase": "charging", "gauge": 40}
                return {"phase": "ready", "gauge": 100}

        character = CombatDummyCharacter()
        begin_tutorial(character)
        state = ensure_tutorial_state(character)
        state["flags"].update(
            {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "returned_to_wayfarers_yard": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": True,
                "talked_brask": True,
            }
        )
        character.db.brave_tutorial = state
        view = build_combat_view(CombatDummyEncounter(_room("tutorial_vermin_pens", safe=False)), character)

        self.assertEqual("Training Focus", view.get("guidance_title"))
        self.assertEqual("Combat Tutorial", view.get("guidance_eyebrow"))
        self.assertTrue(view.get("guidance"))
        self.assertNotIn("Training Focus", [section.get("label") for section in view.get("sections", [])])

    def test_regular_tutorial_guidance_defers_during_vermin_pens_combat(self):
        character = DummyCharacter()
        begin_tutorial(character)
        state = ensure_tutorial_state(character)
        state["flags"].update(
            {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "returned_to_wayfarers_yard": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": True,
                "talked_brask": True,
            }
        )
        character.db.brave_tutorial = state
        character.location = _room("tutorial_vermin_pens", safe=False)
        encounter = SimpleNamespace(is_participant=lambda participant: participant is character)
        character.get_active_encounter = lambda: encounter

        self.assertIsNone(get_tutorial_mechanical_guidance(character))

    def test_rest_only_counts_after_tutorial_fight(self):
        character = DummyCharacter()
        begin_tutorial(character)

        record_command_event(character, "rest")

        state = ensure_tutorial_state(character)
        self.assertFalse(state["flags"]["rested_after_fight"])

    def test_rest_room_helper_requires_authored_rest_site(self):
        self.assertFalse(room_allows_rest(_room("brambleford_town_green")))
        self.assertTrue(room_allows_rest(_room("brambleford_lantern_rest_inn")))
        self.assertTrue(room_allows_rest(_room("tutorial_wayfarers_yard")))
        self.assertFalse(room_allows_rest(_room("tutorial_wayfarers_yard", safe=False)))

    def test_tutorial_exit_blocks_town_until_ready_for_harl(self):
        character = DummyCharacter()
        begin_tutorial(character)
        character.location = _room("tutorial_gate_walk")
        training_yard = _room("brambleford_training_yard")

        self.assertIn("Talk to Sergeant Tamsin", get_tutorial_exit_block(character, training_yard))

        state = ensure_tutorial_state(character)
        state["flags"].update(
            {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": True,
                "returned_to_wayfarers_yard": True,
                "talked_brask": True,
                "used_class_ability": True,
                "won_vermin_fight": True,
                "received_wayfarer_clasp": True,
                "equipped_wayfarer_clasp": True,
                "rested_after_fight": True,
            }
        )
        character.db.brave_tutorial = state

        self.assertIsNone(get_tutorial_exit_block(character, training_yard))

    def test_tutorial_gate_block_names_current_missing_lesson(self):
        character = DummyCharacter()
        begin_tutorial(character)
        character.location = _room("tutorial_gate_walk")
        training_yard = _room("brambleford_training_yard")

        state = ensure_tutorial_state(character)
        state["flags"].update(
            {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "talked_nella": True,
            }
        )
        character.db.brave_tutorial = state

        self.assertIn("Open your gear", get_tutorial_exit_block(character, training_yard))

        record_command_event(character, "gear")
        self.assertIn("Open your pack", get_tutorial_exit_block(character, training_yard))

        record_command_event(character, "pack")
        self.assertIn("Read the supply board", get_tutorial_exit_block(character, training_yard))

        state = ensure_tutorial_state(character)
        state["flags"]["read_supply_board"] = True
        character.db.brave_tutorial = state
        self.assertIn("Return west", get_tutorial_exit_block(character, training_yard))

    def test_optional_ui_and_family_lessons_do_not_block_graduation(self):
        character = DummyCharacter()
        begin_tutorial(character)
        state = ensure_tutorial_state(character)
        state["flags"].update(
            {
                "talked_tamsin": True,
                "visited_quartermaster_shed": True,
                "talked_nella": True,
                "viewed_gear": True,
                "viewed_pack": True,
                "read_supply_board": True,
                "returned_to_wayfarers_yard": True,
                "talked_brask": True,
                "used_class_ability": True,
                "won_vermin_fight": True,
                "received_wayfarer_clasp": True,
                "equipped_wayfarer_clasp": True,
                "rested_after_fight": True,
            }
        )
        character.db.brave_tutorial = state

        state = ensure_tutorial_state(character)

        self.assertEqual("through_the_gate", state["step"])
        self.assertFalse(state["flags"]["viewed_map"])
        self.assertFalse(state["flags"]["viewed_sheet"])
        self.assertFalse(state["flags"]["viewed_journal"])
        self.assertFalse(state["flags"]["talked_peep"])
        self.assertFalse(state["flags"]["read_family_post_sign"])

    def test_tutorial_pens_use_tuned_tutorial_enemy(self):
        encounters = get_content_registry().encounters

        pens = encounters.room_encounters["tutorial_vermin_pens"]
        enemy_ids = [enemy_id for encounter in pens for enemy_id in encounter["enemies"]]

        self.assertEqual(["tutorial_thorn_rat", "tutorial_thorn_rat"], enemy_ids)
        self.assertGreater(encounters.enemy_templates["tutorial_thorn_rat"]["max_hp"], encounters.enemy_templates["thorn_rat"]["max_hp"])
        self.assertLess(encounters.enemy_templates["tutorial_thorn_rat"]["attack_power"], encounters.enemy_templates["thorn_rat"]["attack_power"])

    def test_active_tutorial_uses_tracked_quest_payload(self):
        character = DummyCharacter()
        begin_tutorial(character)

        payload = get_tracked_quest_payload(character)

        self.assertEqual("tutorial", payload["kind"])
        self.assertEqual("Lanternfall", payload["title"])
        self.assertEqual("Wayfarer's Yard", payload["giver"])
        self.assertTrue(any("Tamsin" in objective["text"] for objective in payload["objectives"]))

    def test_first_hour_route_tracks_clear_handoffs_through_ruk(self):
        character = DummyCharacter()
        character.db.brave_tutorial = {"status": "completed", "step": None, "flags": {}}
        character.location = _room("brambleford_training_yard")
        ensure_starter_quests(character)

        get_entity_response(character, _entity("captain_harl_rowan"), "talk", is_action=True)
        self.assertEqual("rats_in_the_kettle", character.db.brave_tracked_quest)
        self.assertIn("stores matter", get_entity_response(character, _entity("uncle_pib_underbough"), "talk"))

        advance_room_visit(character, _room("brambleford_rat_and_kettle_cellar", safe=False))
        for _index in range(3):
            advance_enemy_defeat(character, {"rat"})
        self.assertEqual("completed", character.db.brave_quests["rats_in_the_kettle"]["status"])
        self.assertEqual("roadside_howls", character.db.brave_tracked_quest)
        self.assertIn("Mira", get_tracked_quest_payload(character)["objectives"][0]["text"])

        advance_room_visit(character, _room("brambleford_east_gate"))
        advance_room_visit(character, _room("goblin_road_old_fence_line", safe=False))
        advance_room_visit(character, _room("goblin_road_wolf_turn", safe=False))
        self.assertEqual("completed", character.db.brave_quests["roadside_howls"]["status"])
        self.assertEqual("fencebreakers", character.db.brave_tracked_quest)

        advance_enemy_defeat(character, {"goblin"})
        advance_enemy_defeat(character, {"goblin"})
        self.assertEqual("completed", character.db.brave_quests["fencebreakers"]["status"])
        self.assertEqual("ruk_the_fence_cutter", character.db.brave_tracked_quest)
        self.assertIn("Ruk's camp", get_entity_response(character, _entity("mira_fenleaf"), "talk"))

        advance_room_visit(character, _room("goblin_road_fencebreaker_camp", safe=False))
        advance_enemy_defeat(character, {"ruk", "boss"})

        self.assertEqual("completed", character.db.brave_quests["ruk_the_fence_cutter"]["status"])
        self.assertEqual("what_whispers_in_the_wood", character.db.brave_tracked_quest)
        self.assertEqual("active", character.db.brave_quests["what_whispers_in_the_wood"]["status"])
        self.assertEqual("active", character.db.brave_quests["bridgework_for_joss"]["status"])

        board = get_entity_response(
            character,
            SimpleNamespace(
                key="Town Notice Board",
                db=SimpleNamespace(brave_entity_id="town_notice_board", brave_entity_kind="readable"),
            ),
            "read",
        )
        self.assertIn("Ruk is dead", board)
        self.assertIn("road might breathe again", board)
        self.assertIn("woods have gone strange", get_entity_response(character, _entity("mira_fenleaf"), "talk"))


if __name__ == "__main__":
    unittest.main()
