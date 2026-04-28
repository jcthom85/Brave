import os
import random
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter
from world.combat_execution import execute_combat_ability


class DummyFighter:
    def __init__(self, char_id, key, *, race="human", class_key="warrior"):
        self.id = char_id
        self.key = key
        self.location = object()
        self.db = SimpleNamespace(
            brave_race=race,
            brave_class=class_key,
            brave_level=10,
            brave_resources={"hp": 30},
            brave_derived_stats={"max_hp": 30, "accuracy": 10, "dodge": 8, "armor": 6, "attack_power": 10, "spell_power": 10},
        )


class CombatReactionTests(unittest.TestCase):
    def _bind_telegraph_helpers(self, encounter):
        encounter._record_telegraph_outcome = lambda enemy, outcome, **kwargs: BraveEncounter._record_telegraph_outcome(encounter, enemy, outcome, **kwargs)

    def _bind_enemy_turn_helpers(self, encounter):
        self._bind_telegraph_helpers(encounter)
        encounter._get_participant_target = lambda target_id: BraveEncounter._get_participant_target(encounter, target_id)
        encounter._announce_combat_action = lambda enemy, label: BraveEncounter._announce_combat_action(encounter, enemy, label)

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
            _atb_tick_ms=lambda: 250,
            _save_actor_atb_state=lambda state, character=None, enemy=None: saved_state.update(state),
            _record_participant_contribution=lambda character, **kwargs: None,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        encounter._set_enemy_recovery_state = lambda current_enemy, ticks=1: BraveEncounter._set_enemy_recovery_state(encounter, current_enemy, ticks=ticks)
        self._bind_telegraph_helpers(encounter)

        interrupted = BraveEncounter._try_interrupt_enemy_action(encounter, attacker, enemy, "Shield Bash")

        self.assertTrue(interrupted)
        self.assertEqual("recovering", saved_state["phase"])
        self.assertEqual("interrupted", enemy.get("telegraph_outcome"))
        self.assertEqual("Shield Bash", enemy.get("telegraph_answer"))
        self.assertTrue(any("breaks Old Greymaw's Brush Pounce" in message for message in messages))

    def test_elf_interrupt_adds_extra_enemy_recovery(self):
        attacker = DummyFighter(1, "Leth", race="elf")
        enemy = {"id": "e1", "key": "Old Greymaw", "template_key": "old_greymaw", "hp": 40}
        saved_state = {}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _get_actor_atb_state=lambda character=None, enemy=None: {
                "fill_rate": 110,
                "phase": "winding",
                "current_action": {"label": "Brush Pounce"},
                "timing": {"telegraph": True, "interruptible": True},
            },
            _enemy_action_label=lambda current_enemy: "Brush Pounce",
            _default_atb_fill_rate=lambda **_kwargs: 100,
            _atb_tick_ms=lambda: 250,
            _save_actor_atb_state=lambda state, character=None, enemy=None: saved_state.update(state),
            _record_participant_contribution=lambda character, **kwargs: None,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        encounter._set_enemy_recovery_state = lambda current_enemy, ticks=1: BraveEncounter._set_enemy_recovery_state(encounter, current_enemy, ticks=ticks)
        self._bind_telegraph_helpers(encounter)

        interrupted = BraveEncounter._try_interrupt_enemy_action(encounter, attacker, enemy, "Shield Bash")

        self.assertTrue(interrupted)
        self.assertEqual("recovering", saved_state["phase"])
        self.assertEqual(2, saved_state["ticks_remaining"])

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
            _emit_combat_fx=lambda **kwargs: None,
            _save_enemy=lambda current_enemy: None,
            _damage_enemy=lambda attacker, current_enemy, damage, extra_text="", damage_type="physical": None,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        self._bind_enemy_turn_helpers(encounter)

        original_randint = random.randint
        random.randint = lambda a, b: 100
        try:
            BraveEncounter._execute_enemy_turn(encounter, enemy)
        finally:
            random.randint = original_randint

        self.assertEqual(23, interceptor.db.brave_resources["hp"])
        self.assertEqual(30, target.db.brave_resources["hp"])
        self.assertEqual("redirected", enemy.get("telegraph_outcome"))
        self.assertEqual("Intercept", enemy.get("telegraph_answer"))
        self.assertEqual("Tamsin", enemy.get("telegraph_target"))
        self.assertTrue(any("pulling it off Rook" in message for message in messages))
        self.assertTrue(any("hits Tamsin for 7 damage" in message for message in messages))

    def test_dwarf_takes_one_less_direct_damage(self):
        messages = []
        target = DummyFighter(1, "Brann", race="dwarf")
        room = object()
        target.location = room
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
                "reaction_label": None,
                "reaction_redirect_to": None,
            },
        }

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
            _get_character=lambda dbref: target if dbref == target.id else None,
            get_active_participants=lambda: [target],
            _get_effective_derived=lambda character: {"dodge": 0, "armor": 0},
            _roll_hit=lambda accuracy, dodge: True,
            _weapon_damage=lambda attack_power, armor, bonus=0: 12 + bonus,
            _spell_damage=lambda spell_power, armor, bonus=0: 12 + bonus,
            _get_participant_state=lambda character: states[str(character.id)],
            _record_participant_contribution=lambda character, **kwargs: None,
            _defeat_character=lambda character: None,
            _emit_combat_fx=lambda **kwargs: None,
            _save_enemy=lambda current_enemy: None,
            _damage_enemy=lambda attacker, current_enemy, damage, extra_text="", damage_type="physical": None,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        self._bind_enemy_turn_helpers(encounter)

        original_randint = random.randint
        random.randint = lambda a, b: 100
        try:
            BraveEncounter._execute_enemy_turn(encounter, enemy)
        finally:
            random.randint = original_randint

        self.assertEqual(19, target.db.brave_resources["hp"])
        self.assertEqual("unanswered", enemy.get("telegraph_outcome"))
        self.assertEqual("Brann", enemy.get("telegraph_target"))
        self.assertTrue(any("hits Brann for 11 damage" in message for message in messages))

    def test_telegraphed_attack_records_mitigated_outcome(self):
        messages = []
        target = DummyFighter(1, "Rook")
        enemy = {
            "id": "e1",
            "key": "Tower Archer",
            "template_key": "tower_archer",
            "hp": 20,
            "accuracy": 80,
            "attack_power": 12,
        }
        state = {
            "guard": 0,
            "reaction_guard": 5,
            "reaction_guard_source": target.id,
            "reaction_label": "Brace",
            "reaction_redirect_to": None,
        }
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
            _get_character=lambda dbref: target if dbref == target.id else None,
            get_active_participants=lambda: [target],
            _get_effective_derived=lambda character: {"dodge": 0, "armor": 0},
            _roll_hit=lambda accuracy, dodge: True,
            _weapon_damage=lambda attack_power, armor, bonus=0: 12 + bonus,
            _spell_damage=lambda spell_power, armor, bonus=0: 12 + bonus,
            _get_participant_state=lambda character: state,
            _record_participant_contribution=lambda character, **kwargs: None,
            _defeat_character=lambda character: None,
            _emit_combat_fx=lambda **kwargs: None,
            _save_enemy=lambda current_enemy: None,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        self._bind_enemy_turn_helpers(encounter)

        original_randint = random.randint
        random.randint = lambda a, b: 100
        try:
            BraveEncounter._execute_enemy_turn(encounter, enemy)
        finally:
            random.randint = original_randint

        self.assertEqual("mitigated", enemy.get("telegraph_outcome"))
        self.assertEqual("Brace", enemy.get("telegraph_answer"))
        self.assertEqual("Rook", enemy.get("telegraph_target"))
        self.assertTrue(any("takes the edge off" in message for message in messages))

    def _build_reaction_ability_encounter(self, messages, source, target, enemy):
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            db=SimpleNamespace(participant_states={}, enemies=[enemy]),
            _scaled_heal_amount=lambda derived, base, variance=0, divisor=1: base,
            _heal_character=lambda healer, healed, amount, heal_type="holy": None,
            _record_participant_contribution=lambda character, **kwargs: None,
            _add_threat=lambda character, amount: None,
            _get_actor_atb_state=lambda character=None, enemy=None: {
                "phase": "resolving",
                "current_action": {"label": "Aimed Shot"},
                "timing": {"telegraph": True, "interruptible": True},
            },
            _enemy_action_label=lambda current_enemy: "Aimed Shot",
            _handle_enemy_specials=lambda current_enemy: current_enemy,
            _choose_enemy_target=lambda current_enemy=None: target,
            get_active_enemies=lambda: [enemy],
            _get_character=lambda dbref: source if dbref == source.id else target if dbref == target.id else None,
            get_active_participants=lambda: [source, target] if source.id != target.id else [target],
            _get_effective_derived=lambda character: {"dodge": 0, "armor": 0, "spell_power": 10},
            _roll_hit=lambda accuracy, dodge: True,
            _weapon_damage=lambda attack_power, armor, bonus=0: 12 + bonus,
            _spell_damage=lambda spell_power, armor, bonus=0: 12 + bonus,
            _defeat_character=lambda character: None,
            _emit_combat_fx=lambda **kwargs: None,
            _save_enemy=lambda current_enemy: None,
            _damage_enemy=lambda attacker, current_enemy, damage, extra_text="", damage_type="physical": None,
        )
        encounter._get_participant_state = lambda character: BraveEncounter._get_participant_state(encounter, character)
        encounter._save_participant_state = lambda character, state: BraveEncounter._save_participant_state(encounter, character, state)
        encounter._apply_reaction_guard = lambda current_source, current_target, amount, label, redirect_to=None: BraveEncounter._apply_reaction_guard(
            encounter,
            current_source,
            current_target,
            amount=amount,
            label=label,
            redirect_to=redirect_to,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        self._bind_enemy_turn_helpers(encounter)
        return encounter

    def test_guarding_aura_registers_as_telegraph_mitigation(self):
        messages = []
        paladin = DummyFighter(1, "Ser Jorin", class_key="paladin")
        enemy = {
            "id": "e1",
            "key": "Tower Archer",
            "template_key": "tower_archer",
            "hp": 20,
            "accuracy": 80,
            "attack_power": 12,
        }
        encounter = self._build_reaction_ability_encounter(messages, paladin, paladin, enemy)

        execute_combat_ability(
            encounter,
            paladin,
            "guardingaura",
            "Guarding Aura",
            paladin,
            dict(paladin.db.brave_derived_stats),
            10,
            [paladin],
            [enemy],
        )
        original_randint = random.randint
        random.randint = lambda a, b: 100
        try:
            BraveEncounter._execute_enemy_turn(encounter, enemy)
        finally:
            random.randint = original_randint

        self.assertEqual("mitigated", enemy.get("telegraph_outcome"))
        self.assertEqual("Guarding Aura", enemy.get("telegraph_answer"))
        self.assertTrue(any("takes the edge off" in message for message in messages))

    def test_shield_of_dawn_registers_as_telegraph_mitigation(self):
        messages = []
        paladin = DummyFighter(1, "Ser Jorin", class_key="paladin")
        ally = DummyFighter(2, "Rook")
        room = object()
        paladin.location = room
        ally.location = room
        enemy = {
            "id": "e1",
            "key": "Tower Archer",
            "template_key": "tower_archer",
            "hp": 20,
            "accuracy": 80,
            "attack_power": 12,
        }
        encounter = self._build_reaction_ability_encounter(messages, paladin, ally, enemy)

        execute_combat_ability(
            encounter,
            paladin,
            "shieldofdawn",
            "Shield of Dawn",
            ally,
            dict(paladin.db.brave_derived_stats),
            10,
            [paladin, ally],
            [enemy],
        )
        original_randint = random.randint
        random.randint = lambda a, b: 100
        try:
            BraveEncounter._execute_enemy_turn(encounter, enemy)
        finally:
            random.randint = original_randint

        self.assertEqual("mitigated", enemy.get("telegraph_outcome"))
        self.assertEqual("Shield of Dawn", enemy.get("telegraph_answer"))
        self.assertEqual("Rook", enemy.get("telegraph_target"))

    def test_sacred_aegis_retaliates_when_protected_ally_is_hit(self):
        messages = []
        target = DummyFighter(1, "Rook")
        paladin = DummyFighter(2, "Ser Jorin", class_key="paladin")
        room = object()
        target.location = room
        paladin.location = room
        enemy = {
            "id": "e1",
            "key": "Tower Archer",
            "template_key": "tower_archer",
            "hp": 20,
            "accuracy": 80,
            "attack_power": 12,
            "judged_turns": 2,
        }
        states = {
            str(target.id): {
                "guard": 0,
                "reaction_guard": 0,
                "reaction_guard_source": None,
                "reaction_label": None,
                "reaction_redirect_to": None,
                "sacred_aegis_turns": 2,
                "sacred_aegis_source": paladin.id,
                "sacred_aegis_power": 4,
            },
        }

        def damage_enemy(attacker, current_enemy, damage, extra_text="", damage_type="physical"):
            current_enemy["hp"] -= damage
            messages.append(f"{attacker.key} retaliates for {damage}.{extra_text}")

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
            _get_character=lambda dbref: paladin if dbref == paladin.id else target if dbref == target.id else None,
            get_active_participants=lambda: [target, paladin],
            _get_effective_derived=lambda character: {"dodge": 0, "armor": 0, "spell_power": 9},
            _roll_hit=lambda accuracy, dodge: True,
            _weapon_damage=lambda attack_power, armor, bonus=0: 12 + bonus,
            _spell_damage=lambda spell_power, armor, bonus=0: 12 + bonus,
            _get_participant_state=lambda character: states.setdefault(str(character.id), {"guard": 0}),
            _record_participant_contribution=lambda character, **kwargs: None,
            _defeat_character=lambda character: None,
            _emit_combat_fx=lambda **kwargs: None,
            _save_enemy=lambda current_enemy: None,
            _damage_enemy=damage_enemy,
        )
        encounter._enemy_reaction_state = lambda current_enemy: BraveEncounter._enemy_reaction_state(encounter, current_enemy)
        self._bind_enemy_turn_helpers(encounter)

        original_randint = random.randint
        random.randint = lambda a, b: 100
        try:
            BraveEncounter._execute_enemy_turn(encounter, enemy)
        finally:
            random.randint = original_randint

        self.assertLess(enemy["hp"], 20)
        self.assertTrue(any("Ser Jorin retaliates" in message for message in messages))

    def test_living_current_cleanses_primary_target(self):
        messages = []
        source = DummyFighter(1, "Willow", class_key="druid")
        target = DummyFighter(2, "Rook")
        cleared = []
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _get_participant_state=lambda character: {},
            _scaled_heal_amount=lambda derived, base, variance=0, divisor=1: base,
            _heal_character=lambda healer, healed, amount, heal_type="nature": None,
            _clear_one_harmful_effect=lambda character: cleared.append(character.key) or "poison",
            _record_participant_contribution=lambda character, **kwargs: messages.append(("contribution", character.key, kwargs)),
        )

        handled = execute_combat_ability(
            encounter,
            source,
            "livingcurrent",
            "Living Current",
            target,
            {"spell_power": 10, "accuracy": 10},
            10,
            [source, target],
            [],
        )

        self.assertTrue(handled)
        self.assertEqual(["Rook"], cleared)
        self.assertTrue(any("washes the poison from Rook" in message for message in messages if isinstance(message, str)))
        self.assertTrue(any(entry[2].get("utility") == 1 for entry in messages if isinstance(entry, tuple)))

    def test_cleanse_renewing_light_and_blessing_clear_harmful_effects(self):
        cases = (
            ("cleanse", "Cleanse", "cleanses the poison", {"poison_turns": 2}),
            ("renewinglight", "Renewing Light", "strips the poison", {"poison_turns": 2}),
            ("blessing", "Blessing", "eases the poison", {"poison_turns": 2}),
        )
        for ability_key, ability_name, expected_text, initial_state in cases:
            with self.subTest(ability=ability_key):
                messages = []
                source = DummyFighter(1, "Sol", class_key="cleric")
                target = DummyFighter(2, "Rook")
                state = {
                    "guard": 0,
                    "bleed_turns": 0,
                    "poison_turns": 0,
                    "poison_damage": 4,
                    "poison_accuracy_penalty": 5,
                    "curse_turns": 0,
                    "snare_turns": 0,
                    **initial_state,
                }
                encounter = SimpleNamespace(
                    obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
                    _get_participant_state=lambda character: state,
                    _save_participant_state=lambda character, saved_state: state.update(saved_state),
                    _scaled_heal_amount=lambda derived, base, variance=0, divisor=1: base,
                    _heal_character=lambda healer, healed, amount, heal_type="holy": None,
                    _clear_one_harmful_effect=lambda character: BraveEncounter._clear_one_harmful_effect(encounter, character),
                    _record_participant_contribution=lambda character, **kwargs: messages.append(("contribution", kwargs)),
                )

                handled = execute_combat_ability(
                    encounter,
                    source,
                    ability_key,
                    ability_name,
                    target,
                    {"spell_power": 10, "healing_power": 10, "accuracy": 10},
                    10,
                    [source, target],
                    [],
                )

                self.assertTrue(handled)
                self.assertEqual(0, state.get("poison_turns"))
                self.assertTrue(any(expected_text in message for message in messages if isinstance(message, str)))


if __name__ == "__main__":
    unittest.main()
