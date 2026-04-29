import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.scripts import BraveEncounter
from world.combat_execution import execute_combat_ability
from world.combat_enemy_turns import execute_enemy_turn
from world.ranger_companions import get_companion


class DummyFighter:
    def __init__(self, char_id, key, class_key):
        self.id = char_id
        self.key = key
        self.location = SimpleNamespace(db=SimpleNamespace(brave_resonance="fantasy"))
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
        self._mastery = {}

    def get_active_companion(self):
        return get_companion(self.db.brave_active_companion)

    def get_ability_mastery_rank(self, ability_key):
        return int(self._mastery.get(ability_key, 1) or 1)

    def award_companion_bond_xp(self, companion_key, amount):
        awards = list(getattr(self, "_bond_awards", []))
        awards.append((companion_key, amount))
        self._bond_awards = awards
        return [f"{companion_key} +{amount}"]


class ClassExecutionTests(unittest.TestCase):
    def _enemy_heal_fixture(self, template_key):
        messages = []
        healer = {"id": "healer", "template_key": template_key, "key": template_key.replace("_", " ").title()}
        ally = {"id": "ally", "template_key": "wounded_ally", "key": "Wounded Ally", "hp": 10, "max_hp": 40}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _enemy_reaction_state=lambda current: {"telegraphed": False, "label": "Attack"},
            _handle_enemy_specials=lambda current: current,
            _find_wounded_enemy=lambda exclude_id=None: ally,
            _announce_combat_action=lambda actor, label: BraveEncounter._announce_combat_action(encounter, actor, label),
            _heal_enemy=lambda source, target, amount: BraveEncounter._heal_enemy(encounter, source, target, amount),
            _save_enemy=lambda target: None,
            _choose_enemy_target=lambda current: (_ for _ in ()).throw(AssertionError("healer should not fall through to attack")),
        )
        return encounter, healer, ally, messages

    def test_mossling_heals_wounded_ally(self):
        encounter, healer, ally, messages = self._enemy_heal_fixture("mossling")

        with patch("world.combat_enemy_turns.random.randint", return_value=9):
            execute_enemy_turn(encounter, healer)

        self.assertEqual(19, ally["hp"])
        self.assertTrue(messages[0].startswith("|cMossling uses Mend Spores!|n"))
        self.assertIn("mends Wounded Ally for 9 HP", messages[1])

    def test_barrow_wisp_heals_wounded_ally(self):
        encounter, healer, ally, messages = self._enemy_heal_fixture("barrow_wisp")

        with patch("world.combat_enemy_turns.random.randint", return_value=8):
            execute_enemy_turn(encounter, healer)

        self.assertEqual(18, ally["hp"])
        self.assertTrue(messages[0].startswith("|cBarrow Wisp uses Grave Light!|n"))
        self.assertIn("mends Wounded Ally for 8 HP", messages[1])
        self.assertIn("feeds cold grave-light", messages[2])

    def test_fen_wisp_heals_wounded_ally(self):
        encounter, healer, ally, messages = self._enemy_heal_fixture("fen_wisp")

        with patch("world.combat_enemy_turns.random.randint", return_value=10):
            execute_enemy_turn(encounter, healer)

        self.assertEqual(20, ally["hp"])
        self.assertTrue(messages[0].startswith("|cFen Wisp uses Marsh Light!|n"))
        self.assertIn("mends Wounded Ally for 10 HP", messages[1])
        self.assertIn("sheds sick marsh light", messages[2])

    def test_hollow_wisp_heals_wounded_ally(self):
        encounter, healer, ally, messages = self._enemy_heal_fixture("hollow_wisp")

        with patch("world.combat_enemy_turns.random.randint", return_value=11):
            execute_enemy_turn(encounter, healer)

        self.assertEqual(21, ally["hp"])
        self.assertTrue(messages[0].startswith("|cHollow Wisp uses Lamp Light!|n"))
        self.assertIn("mends Wounded Ally for 11 HP", messages[1])
        self.assertIn("spills drowned lamp-light", messages[2])

    def test_player_ability_announces_name_before_resolution(self):
        messages = []
        cleric = DummyFighter(1, "Tamsin", "cleric")
        ally = DummyFighter(2, "Peep", "warrior")
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _announce_combat_action=lambda actor, label: BraveEncounter._announce_combat_action(encounter, actor, label),
            _get_participant_target=lambda target_id: ally if target_id == ally.id else None,
            _spend_resource=lambda character, resource, amount: None,
            _get_effective_derived=lambda character: dict(character.db.brave_derived_stats),
            get_active_participants=lambda: [cleric, ally],
            get_active_enemies=lambda: [],
        )

        with patch("typeclasses.scripts.execute_combat_ability") as execute_mock:
            BraveEncounter._execute_ability(encounter, cleric, {"ability": "heal", "target": ally.id})

        self.assertTrue(execute_mock.called)
        self.assertTrue(messages[0].startswith("|cTamsin uses Heal!|n"))

    def test_companion_turn_announces_named_move(self):
        messages = []
        companion = {"id": "c1", "key": "Marsh Hound", "companion_key": "marsh_hound"}
        enemy = {"id": "e1", "key": "Raider", "dodge": 0, "armor": 0, "hp": 20, "marked_turns": 0}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _announce_combat_action=lambda actor, label: BraveEncounter._announce_combat_action(encounter, actor, label),
            _choose_companion_target=lambda current: enemy,
            _get_effective_derived=lambda current: {"accuracy": 10, "attack_power": 10},
            _roll_hit=lambda accuracy, dodge: False,
            _emit_miss_fx=lambda source, target: None,
            _add_threat=lambda actor, amount: None,
        )

        BraveEncounter._execute_companion_turn(encounter, companion)

        self.assertTrue(messages[0].startswith("|cMarsh Hound uses Hamstring Bite!|n"))
        self.assertEqual("Marsh Hound misses Raider.", messages[1])

    def test_cleric_sanctuary_handles_companion_allies(self):
        cleric = DummyFighter(1, "Tamsin", "cleric")
        ally = DummyFighter(2, "Peep", "warrior")
        companion = {
            "kind": "companion",
            "id": "c1",
            "key": "Marsh Hound",
            "hp": 8,
            "max_hp": 20,
        }
        states = {}
        healed = []
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _get_participant_state=lambda actor: states.setdefault(str(actor.get("id") if isinstance(actor, dict) else actor.id), {"guard": 0}),
            _save_participant_state=lambda actor, state: states.__setitem__(str(actor.get("id") if isinstance(actor, dict) else actor.id), state),
            _heal_character=lambda source, target, amount, heal_type="healing": healed.append((target, amount, heal_type)),
        )

        execute_combat_ability(
            encounter,
            cleric,
            "sanctuary",
            "Sanctuary",
            cleric,
            cleric.db.brave_derived_stats,
            10,
            [cleric, ally, companion],
            [],
        )

        self.assertIn("c1", states)
        self.assertGreater(states["c1"]["guard"], 0)
        self.assertTrue(any(target is companion for target, _amount, _heal_type in healed))

    def test_enemy_special_announces_move_name(self):
        messages = []
        target = DummyFighter(2, "Peep", "warrior")
        enemy = {"id": "e1", "template_key": "tower_archer", "key": "Tower Archer", "accuracy": 10, "attack_power": 8}
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: messages.append(message)),
            _announce_combat_action=lambda actor, label: BraveEncounter._announce_combat_action(encounter, actor, label),
            _enemy_reaction_state=lambda current: {"telegraphed": True, "label": "Aimed Shot"},
            _handle_enemy_specials=lambda current: current,
            get_active_enemies=lambda: [enemy],
            _choose_enemy_target=lambda current=None: target,
            _get_participant_state=lambda actor: {"reaction_redirect_to": None, "reaction_label": None, "reaction_guard": 0, "guard": 0, "sacred_aegis_turns": 0},
            _get_participant_target=lambda target_id: None,
            _get_effective_derived=lambda actor: dict(actor.db.brave_derived_stats),
            _roll_hit=lambda accuracy, dodge: False,
            _emit_miss_fx=lambda source, target: None,
            _record_telegraph_outcome=lambda current_enemy, outcome, **kwargs: BraveEncounter._record_telegraph_outcome(encounter, current_enemy, outcome, **kwargs),
        )

        BraveEncounter._execute_enemy_turn(encounter, enemy)

        self.assertTrue(messages[0].startswith("|cTower Archer uses Aimed Shot!|n"))
        self.assertEqual("Tower Archer misses Peep.", messages[1])

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

    def test_mastered_firebolt_hits_harder_than_base_rank(self):
        mage = DummyFighter(1, "Nyra", "mage")
        enemy = {"id": "e1", "key": "Raider", "armor": 0, "dodge": 0, "hp": 30, "marked_turns": 0, "bound_turns": 0}
        hits = []
        encounter = SimpleNamespace(
            obj=SimpleNamespace(msg_contents=lambda message, **_kwargs: None),
            _roll_hit=lambda accuracy, dodge: True,
            _spell_damage=lambda spell_power, armor, bonus=0: spell_power + bonus,
            _damage_enemy=lambda attacker, target, damage, extra_text="", damage_type="fire": hits.append(damage),
            _add_threat=lambda character, amount: None,
        )

        execute_combat_ability(encounter, mage, "firebolt", "Firebolt", enemy, {"accuracy": 10, "spell_power": 12}, 10, [mage], [enemy])
        mage._mastery["firebolt"] = 3
        execute_combat_ability(encounter, mage, "firebolt", "Firebolt", enemy, {"accuracy": 10, "spell_power": 12}, 10, [mage], [enemy])

        self.assertGreater(hits[1], hits[0])

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

    def test_companion_bond_progress_is_awarded_from_meaningful_companion_fight(self):
        ranger = DummyFighter(1, "Kest", "ranger")
        encounter = SimpleNamespace(
            db=SimpleNamespace(
                participant_contributions={
                    "c1": {
                        "owner_id": 1,
                        "companion_key": "marsh_hound",
                        "companion_name": "Marsh Hound",
                        "meaningful_actions": 2,
                        "damage_done": 12,
                        "utility_points": 0,
                    }
                }
            ),
            _get_character=lambda dbref: ranger if dbref == 1 else None,
            _participant_reward_eligible=lambda character: True,
        )

        progress = BraveEncounter._award_companion_bond_progress(encounter)

        self.assertEqual([("marsh_hound", 3)], getattr(ranger, "_bond_awards", []))
        self.assertIn("Marsh Hound bond +3 XP.", progress[1][0])

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
