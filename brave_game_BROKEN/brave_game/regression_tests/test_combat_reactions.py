import os
import random
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter


class DummyFighter:
    def __init__(self, char_id, key):
        self.id = char_id
        self.key = key
        self.location = object()
        self.db = SimpleNamespace(
            brave_class="warrior",
            brave_level=10,
            brave_resources={"hp": 30},
            brave_derived_stats={"max_hp": 30},
        )


class CombatReactionTests(unittest.TestCase):
    def test_interrupt_tool_cancels_winding_enemy_action(self):
        messages = []
        attacker = DummyFighter(1, "Tamsin")
        enemy = {"id": "e1", "key": "Old Greymaw", "template_key": "old_greymaw", "hp": 40}
        saved_state = {}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _get_actor_atb_state=lambda character=None, enemy=None: {
                "fill_rate": 110,
                "phase": "winding",
                "current_action": {"label": "Brush Pounce"},
                "timing": {"telegraph": True, "interruptible": True},
            },
            _enemy_action_label=lambda current_enemy: "Brush Pounce",
            _default_atb_fill_rate=lambda **_kwargs: 100,
            _save_actor_atb_state=lambda state, character=None, enemy=None: saved_state.update(state),
            _record_participant_contribution=lambda character, **kwargs: None,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        encounter._set_enemy_recovery_state = lambda current_enemy, ticks=1: BraveEncounter._set_enemy_recovery_state(encounter, current_enemy, ticks=ticks)

        interrupted = BraveEncounter._try_interrupt_enemy_action(encounter, attacker, enemy, "Shield Bash")

        self.assertTrue(interrupted)
        self.assertEqual("recovering", saved_state["phase"])
        self.assertTrue(any("interrupts Old Greymaw's Brush Pounce" in message for message in messages))

    def test_telegraphed_attack_can_be_redirected_and_mitigated(self):
        messages = []
        target = DummyFighter(1, "Rook")
        interceptor = DummyFighter(2, "Tamsin")
        room = object()
        target.location = room
        interceptor.location = room
        enemy = {
            "id": "e1",
            "key": "Tower Archer",
            "template_key": "tower_archer",
            "hp": 20,
            "accuracy": 80,
            "attack_power": 12,
        }
        states = {
            str(target.id): {
                "guard": 0,
                "reaction_guard": 0,
                "reaction_guard_source": None,
                "reaction_label": "Intercept",
                "reaction_redirect_to": interceptor.id,
            },
            str(interceptor.id): {
                "guard": 0,
                "reaction_guard": 5,
                "reaction_guard_source": interceptor.id,
                "reaction_label": "Intercept",
                "reaction_redirect_to": None,
            },
        }
        contributions = []

        def get_state(character):
            return states[str(character.id)]

        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _get_actor_atb_state=lambda character=None, enemy=None: {
                "phase": "resolving",
                "current_action": {"label": "Aimed Shot"},
                "timing": {"telegraph": True, "interruptible": True},
            },
            _enemy_action_label=lambda current_enemy: "Aimed Shot",
            _handle_enemy_specials=lambda current_enemy: current_enemy,
            _choose_enemy_target=lambda current_enemy=None: target,
            get_active_enemies=lambda: [enemy],
            _get_character=lambda dbref: interceptor if dbref == interceptor.id else target if dbref == target.id else None,
            get_active_participants=lambda: [target, interceptor],
            _get_effective_derived=lambda character: {"dodge": 0, "armor": 0},
            _roll_hit=lambda accuracy, dodge: True,
            _weapon_damage=lambda attack_power, armor, bonus=0: 12 + bonus,
            _spell_damage=lambda spell_power, armor, bonus=0: 12 + bonus,
            _get_participant_state=get_state,
            _record_participant_contribution=lambda character, **kwargs: contributions.append((character.key, kwargs)),
            _defeat_character=lambda character: None,
            _save_enemy=lambda current_enemy: None,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)

        original_randint = random.randint
        random.randint = lambda a, b: 100
        try:
            BraveEncounter._execute_enemy_turn(encounter, enemy)
        finally:
            random.randint = original_randint

        self.assertEqual(23, interceptor.db.brave_resources["hp"])
        self.assertEqual(30, target.db.brave_resources["hp"])
        self.assertTrue(any("dragging it off Rook" in message for message in messages))
        self.assertTrue(any("blunts Tower Archer's Aimed Shot" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
