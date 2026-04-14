import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.content import get_content_registry
from world.questing import (
    _complete_quest,
    activate_quest,
    advance_enemy_defeat,
    advance_entity_talk,
    advance_item_collection,
    advance_room_visit,
    ensure_starter_quests,
    format_quest_block,
)


class DummyCharacter:
    def __init__(self):
        self.db = SimpleNamespace(
            brave_silver=0,
            brave_inventory=[],
            brave_quests={},
            brave_tracked_quest=None,
            brave_track_suppressed=False,
        )
        self.ndb = SimpleNamespace(brave_recent_quest_updates=[])
        self.key = "Tester"
        self.messages = []

    def grant_xp(self, amount):
        self.last_xp = amount
        return []

    def add_item_to_inventory(self, template_id, quantity):
        self.db.brave_inventory.append({"template": template_id, "quantity": quantity})

    def msg(self, message):
        self.messages.append(message)


def _room(room_id):
    return SimpleNamespace(db=SimpleNamespace(brave_room_id=room_id))


class QuestHandoffTests(unittest.TestCase):
    def test_full_authored_quest_chain_unlocks_and_completes_in_order(self):
        registry = get_content_registry()
        character = DummyCharacter()
        ensure_starter_quests(character)

        with patch("world.questing.unlock_trophy", return_value=True):
            for quest_key in registry.quests.starting_quests:
                state = character.db.brave_quests[quest_key]
                definition = registry.quests.quests[quest_key]
                if state["status"] == "locked" and definition.get("auto_start") is False:
                    self.assertTrue(activate_quest(character, quest_key))
                    state = character.db.brave_quests[quest_key]
                self.assertEqual("active", state["status"], f"{quest_key} should be active before completion")

                for objective in definition["objectives"]:
                    if objective["type"] == "visit_room":
                        advance_room_visit(character, _room(objective["room_id"]))
                    elif objective["type"] == "defeat_enemy":
                        for _index in range(objective.get("count", 1)):
                            advance_enemy_defeat(character, [objective["enemy_tag"]])
                    elif objective["type"] == "talk_entity":
                        advance_entity_talk(character, objective["entity_id"])
                    elif objective["type"] == "collect_item":
                        character.add_item_to_inventory(objective["item_id"], objective.get("count", 1))
                        advance_item_collection(character)
                    else:
                        self.fail(f"Unsupported objective type in smoke test: {objective['type']}")

                self.assertEqual("completed", character.db.brave_quests[quest_key]["status"], f"{quest_key} should complete")

        incomplete = {
            quest_key: state["status"]
            for quest_key, state in character.db.brave_quests.items()
            if state["status"] != "completed"
        }
        self.assertEqual({}, incomplete)
        self.assertTrue(any("Quest complete:" in message for message in character.messages))

    def test_completion_messages_include_authored_handoff_guidance(self):
        character = DummyCharacter()
        definition = {
            "title": "Ruk the Fence-Cutter",
            "rewards": {"xp": 120, "silver": 18, "trophies": ["ruk_fencecleaver_head"]},
            "chapter_complete": "First Hour Chapter",
            "chapter_reaction": "Mira, Sister Maybelle, Joss, and the Trophy Hall all have something new waiting back in Brambleford.",
            "next_step": "After Ruk falls, check in with Mira, Sister Maybelle, or Joss to choose the next branch.",
            "reward_tip": "Spend the silver and sort your pack before leaving the road behind. The next branch is longer and less forgiving.",
        }
        state = {"status": "active"}
        messages = []

        with patch("world.questing.unlock_trophy", return_value=True):
            changed = _complete_quest(character, definition, state, messages)

        self.assertTrue(changed)
        self.assertEqual("completed", state["status"])
        self.assertIn("|yChapter complete:|n First Hour Chapter", messages)
        self.assertIn(
            "|cTown reaction:|n Mira, Sister Maybelle, Joss, and the Trophy Hall all have something new waiting back in Brambleford.",
            messages,
        )
        self.assertIn(
            "|cNext:|n After Ruk falls, check in with Mira, Sister Maybelle, or Joss to choose the next branch.",
            messages,
        )
        self.assertIn(
            "|cTip:|n Spend the silver and sort your pack before leaving the road behind. The next branch is longer and less forgiving.",
            messages,
        )

    def test_practice_makes_heroes_reveals_intro_steps_before_completion(self):
        character = DummyCharacter()
        ensure_starter_quests(character)

        self.assertEqual("active", character.db.brave_quests["practice_makes_heroes"]["status"])
        advance_room_visit(character, _room("brambleford_training_yard"))

        practice_state = character.db.brave_quests["practice_makes_heroes"]
        self.assertEqual("active", practice_state["status"])
        self.assertFalse(practice_state["objectives"][0]["completed"])

        advance_entity_talk(character, "captain_harl_rowan")
        advance_room_visit(character, _room("brambleford_town_green"))
        advance_room_visit(character, _room("brambleford_lantern_rest_inn"))

        practice_state = character.db.brave_quests["practice_makes_heroes"]
        self.assertEqual("active", practice_state["status"])
        self.assertTrue(practice_state["objectives"][0]["completed"])
        self.assertTrue(practice_state["objectives"][1]["completed"])
        self.assertTrue(practice_state["objectives"][2]["completed"])
        self.assertFalse(practice_state["objectives"][3]["completed"])

        advance_entity_talk(character, "uncle_pib_underbough")
        advance_room_visit(character, _room("brambleford_rat_and_kettle_cellar"))
        for _index in range(3):
            advance_enemy_defeat(character, ["rat"])
        advance_room_visit(character, _room("brambleford_lantern_rest_inn"))

        practice_state = character.db.brave_quests["practice_makes_heroes"]
        self.assertEqual("active", practice_state["status"])
        self.assertTrue(practice_state["objectives"][6]["completed"])
        self.assertFalse(practice_state["objectives"][7]["completed"])

        advance_entity_talk(character, "uncle_pib_underbough")

        self.assertEqual("completed", character.db.brave_quests["practice_makes_heroes"]["status"])
        self.assertEqual("active", character.db.brave_quests["roadside_howls"]["status"])

    def test_rats_in_the_kettle_advances_in_order_and_returns_to_pib(self):
        character = DummyCharacter()
        ensure_starter_quests(character)
        character.db.brave_quests["practice_makes_heroes"]["status"] = "completed"
        ensure_starter_quests(character)
        self.assertEqual("locked", character.db.brave_quests["rats_in_the_kettle"]["status"])
        self.assertTrue(activate_quest(character, "rats_in_the_kettle"))

        advance_enemy_defeat(character, ["rat"])
        rats_state = character.db.brave_quests["rats_in_the_kettle"]
        self.assertEqual(0, rats_state["objectives"][1]["progress"])

        advance_room_visit(character, _room("brambleford_lantern_rest_inn"))
        rats_state = character.db.brave_quests["rats_in_the_kettle"]
        self.assertFalse(rats_state["objectives"][0]["completed"])

        advance_room_visit(character, _room("brambleford_rat_and_kettle_cellar"))
        for _index in range(3):
            advance_enemy_defeat(character, ["rat"])
        rats_state = character.db.brave_quests["rats_in_the_kettle"]
        self.assertEqual("active", rats_state["status"])
        self.assertTrue(rats_state["objectives"][1]["completed"])
        self.assertFalse(rats_state["objectives"][2]["completed"])

        advance_room_visit(character, _room("brambleford_lantern_rest_inn"))
        rats_state = character.db.brave_quests["rats_in_the_kettle"]
        self.assertEqual("completed", rats_state["status"])
        self.assertTrue(rats_state["objectives"][2]["completed"])

    def test_format_quest_block_surfaces_tips_and_completion_reaction(self):
        character = DummyCharacter()
        character.db.brave_quests = {
            "practice_makes_heroes": {
                "status": "active",
                "objectives": [
                    {
                        "description": "Speak with Captain Harl Rowan in the Training Yard.",
                        "completed": False,
                        "progress": 0,
                        "required": 1,
                    }
                ],
            },
            "roadside_howls": {
                "status": "completed",
                "objectives": [
                    {
                        "description": "Check in at the East Gate.",
                        "completed": True,
                        "progress": 1,
                        "required": 1,
                    }
                ],
            },
        }

        active_block = format_quest_block(character, "practice_makes_heroes")
        completed_block = format_quest_block(character, "roadside_howls")

        self.assertIn("Tip: Keep Uncle Pib's fish pie for the road", active_block)
        self.assertIn("Next: Go east to the East Gate and speak with Mira Fenleaf about the road.", active_block)
        self.assertIn("Reaction: You have seen enough of Goblin Road to feel the town walls fall behind you.", completed_block)


if __name__ == "__main__":
    unittest.main()
