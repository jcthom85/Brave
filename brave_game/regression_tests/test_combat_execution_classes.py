import os
import unittest
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter
from world.combat_execution import execute_combat_ability
from world.ranger_companions import get_companion


class DummyFighter:
    def __init__(self, char_id, key, class_key):
        self.id = char_id
        self.key = key
        self.location = object()
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_level=10,
            brave_resources={"hp": 30, "mana": 30, "stamina": 30},
            brave_derived_stats={
                "max_hp": 30,
                "accuracy": 10,
                "dodge": 8,
                "armor": 6,
                "attack_power": 10,
                "spell_power": 12,
            },
            brave_active_companion="marsh_hound" if class_key == "ranger" else "",
        )

    def get_active_companion(self):
        return get_companion(self.db.brave_active_companion)


class ClassExecutionTests(unittest.TestCase):
    def test_warrior_strike_gains_control_bonus_on_marked_target(self):
        warrior = DummyFighter(1, "Rook", "warrior")
        enemy = {"id": "e1", "key": "Raider", "armor": 2, "dodge": 0, "hp": 40, "marked_turns": 2, "bound_turns": 0}
        recorded = {}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _roll_hit=lambda accuracy, dodge: True,
            _weapon_damage=lambda attack_power, armor, bonus=0: bonus,
            _damage_enemy=lambda attacker, target, damage, extra_text="", damage_type="physical": recorded.update({"damage": damage, "extra_text": extra_text}),
            _add_threat=lambda character, amount: None,
        )

        execute_combat_ability(encounter, warrior, "strike", "Strike", enemy, {"accuracy": 10, "attack_power": 10}, 10, [warrior], [enemy])

        self.assertEqual(6, recorded["damage"])
        self.assertIn("controlled target", recorded["extra_text"])

    def test_cleric_heal_scales_up_for_low_hp_target(self):
        cleric = DummyFighter(1, "Tamsin", "cleric")
        ally = DummyFighter(2, "Peep", "warrior")
        ally.db.brave_resources["hp"] = 10
        healed = {}
        encounter = SimpleNamespace(
            _scaled_heal_amount=lambda derived, base, variance=4, divisor=2: base,
            _heal_character=lambda source, target, amount, heal_type="holy": healed.update({"amount": amount}),
        )

        execute_combat_ability(encounter, cleric, "heal", "Heal", ally, {"spell_power": 12}, 10, [cleric, ally], [])

        self.assertEqual(16, healed["amount"])

    def test_mage_arcspark_chains_farther_on_marked_target(self):
        mage = DummyFighter(1, "Nyra", "mage")
        primary = {"id": "e1", "key": "Raider", "armor": 0, "dodge": 0, "hp": 30, "marked_turns": 2}
        secondary = {"id": "e2", "key": "Slinger", "armor": 0, "dodge": 0, "hp": 20}
        tertiary = {"id": "e3", "key": "Hexer", "armor": 0, "dodge": 0, "hp": 20}
        hits = []
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _roll_hit=lambda accuracy, dodge: True,
            _spell_damage=lambda spell_power, armor, bonus=0: 12,
            _damage_enemy=lambda attacker, target, damage, extra_text="", damage_type="lightning": hits.append((target["id"], damage, extra_text)),
            _add_threat=lambda character, amount: None,
        )

        execute_combat_ability(encounter, mage, "arcspark", "Arc Spark", primary, {"accuracy": 10, "spell_power": 12}, 10, [mage], [primary, secondary, tertiary])

        self.assertEqual(["e1", "e2", "e3"], [entry[0] for entry in hits])

    def test_ranger_hawk_extends_mark_duration(self):
        ranger = DummyFighter(1, "Kest", "ranger")
        ranger.db.brave_active_companion = "ash_hawk"
        enemy = {"id": "e1", "key": "Raider", "armor": 0, "dodge": 0, "hp": 30, "marked_turns": 0}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _save_enemy=lambda target: None,
            _record_participant_contribution=lambda character, **kwargs: None,
            _add_threat=lambda character, amount: None,
        )

        execute_combat_ability(encounter, ranger, "markprey", "Mark Prey", enemy, {"accuracy": 10, "attack_power": 10}, 10, [ranger], [enemy])

        self.assertEqual(4, enemy["marked_turns"])

    def test_ranger_boar_strengthens_snare_trap(self):
        ranger = DummyFighter(1, "Kest", "ranger")
        ranger.db.brave_active_companion = "briar_boar"
        enemy = {"id": "e1", "key": "Raider", "armor": 0, "dodge": 0, "hp": 30, "marked_turns": 0, "bound_turns": 0}
        recorded = {}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _roll_hit=lambda accuracy, dodge: True,
            _weapon_damage=lambda attack_power, armor, bonus=0: bonus,
            _damage_enemy=lambda attacker, target, damage, extra_text="", damage_type="physical": recorded.update({"damage": damage, "extra_text": extra_text}),
            _save_enemy=lambda target: None,
            _add_threat=lambda character, amount: None,
        )

        execute_combat_ability(encounter, ranger, "snaretrap", "Snare Trap", enemy, {"accuracy": 10, "attack_power": 10}, 10, [ranger], [enemy])

        self.assertEqual(2, enemy["bound_turns"])
        self.assertEqual(3, recorded["damage"])

    def test_rogue_backstab_gains_openings_from_bleed_and_poison(self):
        rogue = DummyFighter(1, "Vale", "rogue")
        enemy = {
            "id": "e1",
            "key": "Raider",
            "armor": 0,
            "dodge": 0,
            "hp": 30,
            "marked_turns": 0,
            "bound_turns": 0,
            "bleed_turns": 2,
            "poison_turns": 2,
        }
        recorded = {}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _roll_hit=lambda accuracy, dodge: True,
            _consume_stealth_bonus=lambda character: 0,
            _weapon_damage=lambda attack_power, armor, bonus=0: bonus,
            _damage_enemy=lambda attacker, target, damage, extra_text="", damage_type="physical": recorded.update({"damage": damage}),
            _add_threat=lambda character, amount: None,
        )

        execute_combat_ability(encounter, rogue, "backstab", "Backstab", enemy, {"accuracy": 10, "attack_power": 10}, 10, [rogue], [enemy])

        self.assertEqual(11, recorded["damage"])

    def test_druid_forms_modify_effective_stats(self):
        messages = []
        druid = DummyFighter(1, "Mira", "druid")
        encounter = SimpleNamespace(
            db=SimpleNamespace(participant_states={}),
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _get_participant_state=lambda character: BraveEncounter._get_participant_state(encounter, character),
            _save_participant_state=lambda character, state: BraveEncounter._save_participant_state(encounter, character, state),
            _record_participant_contribution=lambda character, **kwargs: None,
        )

        execute_combat_ability(encounter, druid, "wolfform", "Wolf Form", druid, dict(druid.db.brave_derived_stats), 10, [druid], [])
        wolf_stats = BraveEncounter._get_effective_derived(encounter, druid)

        execute_combat_ability(encounter, druid, "bearform", "Bear Form", druid, dict(druid.db.brave_derived_stats), 10, [druid], [])
        bear_stats = BraveEncounter._get_effective_derived(encounter, druid)

        self.assertGreater(wolf_stats["accuracy"], druid.db.brave_derived_stats["accuracy"])
        self.assertGreater(wolf_stats["dodge"], druid.db.brave_derived_stats["dodge"])
        self.assertGreater(bear_stats["armor"], druid.db.brave_derived_stats["armor"])
        self.assertGreater(bear_stats["attack_power"], druid.db.brave_derived_stats["attack_power"])
        self.assertTrue(any("wolf form" in message.lower() for message in messages))
        self.assertTrue(any("bear form" in message.lower() for message in messages))

    def test_druid_crow_and_serpent_forms_modify_effective_stats(self):
        messages = []
        druid = DummyFighter(1, "Mira", "druid")
        encounter = SimpleNamespace(
            db=SimpleNamespace(participant_states={}),
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _get_participant_state=lambda character: BraveEncounter._get_participant_state(encounter, character),
            _save_participant_state=lambda character, state: BraveEncounter._save_participant_state(encounter, character, state),
            _record_participant_contribution=lambda character, **kwargs: None,
        )

        execute_combat_ability(encounter, druid, "crowform", "Crow Form", druid, dict(druid.db.brave_derived_stats), 10, [druid], [])
        crow_stats = BraveEncounter._get_effective_derived(encounter, druid)

        execute_combat_ability(encounter, druid, "serpentform", "Serpent Form", druid, dict(druid.db.brave_derived_stats), 10, [druid], [])
        serpent_stats = BraveEncounter._get_effective_derived(encounter, druid)

        self.assertGreater(crow_stats["accuracy"], druid.db.brave_derived_stats["accuracy"])
        self.assertGreater(crow_stats["dodge"], druid.db.brave_derived_stats["dodge"])
        self.assertGreater(serpent_stats["spell_power"], druid.db.brave_derived_stats["spell_power"])
        self.assertGreater(serpent_stats["accuracy"], druid.db.brave_derived_stats["accuracy"])
        self.assertTrue(any("crow form" in message.lower() for message in messages))
        self.assertTrue(any("serpent form" in message.lower() for message in messages))

    def test_guarding_aura_sets_retaliatory_ward_state(self):
        messages = []
        paladin = DummyFighter(1, "Ser Jorin", "paladin")
        ally = DummyFighter(2, "Rook", "warrior")
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _get_participant_state=lambda character: BraveEncounter._get_participant_state(encounter, character),
            _save_participant_state=lambda character, state: BraveEncounter._save_participant_state(encounter, character, state),
            _apply_reaction_guard=lambda source, target, amount, label, redirect_to=None: None,
            _record_participant_contribution=lambda character, **kwargs: None,
            _add_threat=lambda character, amount: None,
            db=SimpleNamespace(participant_states={}),
        )

        execute_combat_ability(
            encounter,
            paladin,
            "guardingaura",
            "Guarding Aura",
            ally,
            dict(paladin.db.brave_derived_stats),
            10,
            [paladin, ally],
            [],
        )

        state = BraveEncounter._get_participant_state(encounter, ally)
        self.assertEqual(2, state["sacred_aegis_turns"])
        self.assertEqual(paladin.id, state["sacred_aegis_source"])
        self.assertGreater(state["sacred_aegis_power"], 0)


if __name__ == "__main__":
    unittest.main()
