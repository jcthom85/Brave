"""Combat ability execution helpers shared by the encounter script."""

import random

from world.content import get_content_registry

CONTENT = get_content_registry()
ABILITY_LIBRARY = CONTENT.characters.ability_library


def _emit_combat_miss(encounter, source, target, message):
    """Broadcast a miss in both the battle feed and combat FX layer."""

    encounter.obj.msg_contents(message)
    emitter = getattr(encounter, "_emit_miss_fx", None)
    if callable(emitter):
        emitter(source, target)


def execute_combat_ability(encounter, character, ability_key, ability_name, target, derived, level, allies, enemies):
    """Execute one queued combat ability. Returns True when a handler ran."""

    ability_class = (ABILITY_LIBRARY.get(ability_key) or {}).get("class")
    handler = {
        "warrior": _execute_warrior_ability,
        "ranger": _execute_ranger_ability,
        "cleric": _execute_cleric_ability,
        "paladin": _execute_paladin_ability,
        "mage": _execute_mage_ability,
        "rogue": _execute_rogue_ability,
        "druid": _execute_druid_ability,
    }.get(ability_class)
    if not handler:
        return False
    handler(encounter, character, ability_key, ability_name, target, derived, level, allies, enemies)
    return True


def _execute_warrior_ability(encounter, character, ability_key, ability_name, target, derived, level, allies, _enemies):
    if ability_key == "strike":
        if not encounter._roll_hit(derived["accuracy"], target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} glances off {target['key']}.")
            encounter._add_threat(character, 4)
            return
        damage = encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=4)
        encounter._damage_enemy(character, target, damage, extra_text=" A heavy blow lands.", damage_type="physical")
        encounter._add_threat(character, 8)
        return

    if ability_key == "defend":
        state = encounter._get_participant_state(character)
        state["guard"] = 7 + level * 2
        encounter._save_participant_state(character, state)
        encounter._apply_reaction_guard(character, character, amount=6 + level, label="Defend")
        encounter.obj.msg_contents(f"{character.key} braces for the next exchange.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        encounter._add_threat(character, 5)
        return

    if ability_key == "shieldbash":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} slams wide of {target['key']}.")
            encounter._add_threat(character, 5)
            return
        damage = encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=2)
        encounter._damage_enemy(character, target, damage, extra_text=" The impact staggers the target.", damage_type="physical")
        if target["hp"] > 0:
            target["bound_turns"] = max(target.get("bound_turns", 0), 1)
            encounter._save_enemy(target)
            encounter.obj.msg_contents(f"{target['key']} is knocked off-balance.")
            encounter._try_interrupt_enemy_action(character, target, ability_name)
        encounter._add_threat(character, 9)
        return

    if ability_key == "battlecry":
        guard_value = 3 + level
        for ally in allies:
            state = encounter._get_participant_state(ally)
            state["guard"] = max(state.get("guard", 0), guard_value)
            encounter._save_participant_state(ally, state)
        encounter.obj.msg_contents(f"{character.key} bellows a battle cry that hardens the whole line.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=guard_value * max(1, len(allies)), utility=2)
        encounter._add_threat(character, 10)
        return

    if ability_key == "intercept":
        primary_guard = 8 + level * 2
        target_state = encounter._get_participant_state(target)
        target_state["guard"] = max(target_state.get("guard", 0), primary_guard)
        encounter._save_participant_state(target, target_state)
        if target.id != character.id:
            self_state = encounter._get_participant_state(character)
            self_state["guard"] = max(self_state.get("guard", 0), 4 + level)
            encounter._save_participant_state(character, self_state)
            encounter._apply_reaction_guard(character, character, amount=primary_guard, label="Intercept")
            encounter._apply_reaction_guard(character, target, amount=0, label="Intercept", redirect_to=character.id)
            encounter.obj.msg_contents(f"{character.key} steps in front of the next hit for {target.key}.")
        else:
            encounter._apply_reaction_guard(character, character, amount=8 + level * 2, label="Intercept")
            encounter.obj.msg_contents(f"{character.key} plants their feet and prepares to intercept the next hit.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=primary_guard, utility=2)
        encounter._add_threat(character, 10)
        return

    if ability_key == "tauntingblow":
        if not encounter._roll_hit(derived["accuracy"] + 1, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} misses {target['key']} but still draws attention.")
            encounter._add_threat(character, 8)
            return
        damage = encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=3)
        encounter._damage_enemy(character, target, damage, extra_text=" The taunt lands as hard as the steel.", damage_type="physical")
        if target["hp"] > 0:
            target["marked_turns"] = max(target.get("marked_turns", 0), 2)
            encounter._save_enemy(target)
        encounter._add_threat(character, 14)
        return

    if ability_key == "brace":
        state = encounter._get_participant_state(character)
        state["guard"] = max(state.get("guard", 0), 10 + level * 2)
        if state.get("snare_turns", 0) > 0:
            state["snare_turns"] = 0
            state["snare_accuracy_penalty"] = 0
            state["snare_dodge_penalty"] = 0
        encounter._save_participant_state(character, state)
        encounter._apply_reaction_guard(character, character, amount=8 + level * 2, label="Brace")
        encounter.obj.msg_contents(f"{character.key} locks into a braced stance and refuses to yield ground.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        encounter._add_threat(character, 8)
        return

    if ability_key == "laststand":
        max_hp = character.db.brave_derived_stats.get("max_hp", 1)
        amount = max(18, max_hp // 3)
        encounter._heal_character(character, character, amount, heal_type="valor")
        state = encounter._get_participant_state(character)
        state["guard"] = max(state.get("guard", 0), 8 + level)
        encounter._save_participant_state(character, state)
        encounter.obj.msg_contents(f"{character.key} digs in and refuses to fall.")
        encounter._add_threat(character, 12)


def _execute_ranger_ability(encounter, character, ability_key, ability_name, target, derived, level, _allies, enemies):
    if ability_key == "quickshot":
        if not encounter._roll_hit(derived["accuracy"] + 10, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} misses {target['key']}.")
            encounter._add_threat(character, 3)
            return
        damage = encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=3)
        encounter._damage_enemy(character, target, damage, damage_type="physical")
        return

    if ability_key == "markprey":
        target["marked_turns"] = 3
        encounter._save_enemy(target)
        encounter.obj.msg_contents(f"{character.key} uses {ability_name} on {target['key']}.")
        encounter._record_participant_contribution(character, meaningful=True, utility=1)
        encounter._add_threat(character, 3)
        return

    if ability_key == "aimedshot":
        if not encounter._roll_hit(derived["accuracy"] + 6, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key} takes the shot but {target['key']} slips the line.")
            encounter._add_threat(character, 4)
            return
        damage_bonus = 6 + (4 if target.get("marked_turns", 0) > 0 else 0)
        encounter._damage_enemy(
            character,
            target,
            encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=damage_bonus),
            damage_type="physical",
        )
        if target["hp"] > 0:
            encounter._try_interrupt_enemy_action(character, target, ability_name)
        return

    if ability_key == "snaretrap":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} snaps shut in the wrong place.")
            encounter._add_threat(character, 3)
            return
        encounter._damage_enemy(
            character,
            target,
            encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=2),
            extra_text=" The trap bites into the target's movement.",
            damage_type="physical",
        )
        if target["hp"] > 0:
            target["bound_turns"] = max(target.get("bound_turns", 0), 1)
            target["marked_turns"] = max(target.get("marked_turns", 0), 1)
            encounter._save_enemy(target)
        return

    if ability_key == "volley":
        fired = False
        for enemy in enemies:
            fired = True
            if not encounter._roll_hit(derived["accuracy"] - 2, enemy["dodge"]):
                _emit_combat_miss(encounter, character, enemy, f"{character.key}'s {ability_name} misses {enemy['key']}.")
                continue
            damage = encounter._weapon_damage(derived["attack_power"], enemy["armor"], bonus=1)
            encounter._damage_enemy(character, enemy, damage, damage_type="physical")
        if not fired:
            encounter.obj.msg_contents(f"{character.key}'s {ability_name} finds no targets.")
        return

    if ability_key == "evasiveroll":
        state = encounter._get_participant_state(character)
        state["guard"] = max(state.get("guard", 0), 3 + level)
        state["feint_turns"] = max(state.get("feint_turns", 0), 1)
        state["feint_accuracy_bonus"] = max(state.get("feint_accuracy_bonus", 0), 2)
        state["feint_dodge_bonus"] = max(state.get("feint_dodge_bonus", 0), 12)
        encounter._save_participant_state(character, state)
        encounter.obj.msg_contents(f"{character.key} rolls clear and resets the angle of the fight.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        return

    if ability_key == "barbedarrow":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} scrapes past {target['key']} without purchase.")
            encounter._add_threat(character, 3)
            return
        encounter._damage_enemy(character, target, encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=4), damage_type="physical")
        if target["hp"] > 0:
            encounter._apply_enemy_bleed(
                target,
                turns=2,
                damage=4,
                message=f"|rBarbs tear into {target['key']} and leave it bleeding!|n",
            )
        return

    if ability_key == "rainofarrows":
        fired = False
        for enemy in enemies:
            fired = True
            if not encounter._roll_hit(derived["accuracy"], enemy["dodge"]):
                _emit_combat_miss(encounter, character, enemy, f"{character.key}'s {ability_name} misses {enemy['key']}.")
                continue
            encounter._damage_enemy(character, enemy, encounter._weapon_damage(derived["attack_power"], enemy["armor"], bonus=4), damage_type="physical")
            if enemy["hp"] > 0:
                enemy["marked_turns"] = max(enemy.get("marked_turns", 0), 1)
                encounter._save_enemy(enemy)
        if not fired:
            encounter.obj.msg_contents(f"{character.key}'s {ability_name} finds no targets.")


def _execute_cleric_ability(encounter, character, ability_key, ability_name, target, derived, level, allies, enemies):
    if ability_key == "heal":
        amount = encounter._scaled_heal_amount(derived, 12, variance=4, divisor=2)
        encounter._heal_character(character, target, amount, heal_type="holy")
        return

    if ability_key == "smite":
        if not encounter._roll_hit(derived["accuracy"], target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} fails to connect with {target['key']}.")
            encounter._add_threat(character, 3)
            return
        damage = encounter._spell_damage(derived["spell_power"], target["armor"], bonus=2)
        encounter._damage_enemy(character, target, damage, damage_type="holy")
        return

    if ability_key == "blessing":
        encounter._heal_character(character, target, encounter._scaled_heal_amount(derived, 6, variance=2, divisor=4), heal_type="holy")
        state = encounter._get_participant_state(target)
        guard_value = 4 + level + derived.get("healing_power", 0)
        state["guard"] = max(state.get("guard", 0), guard_value)
        encounter._save_participant_state(target, state)
        encounter._apply_reaction_guard(character, target, amount=guard_value, label="Blessing")
        encounter.obj.msg_contents(f"{character.key} wraps {target.key} in a brief blessing of shelter.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        return

    if ability_key == "renewinglight":
        encounter._heal_character(character, target, encounter._scaled_heal_amount(derived, 18, variance=5, divisor=2), heal_type="holy")
        cleared = encounter._clear_one_harmful_effect(target)
        if cleared:
            encounter.obj.msg_contents(f"|gRenewing light strips the {cleared} from {target.key}.|n")
            encounter._record_participant_contribution(character, meaningful=True, utility=1)
        return

    if ability_key == "sanctuary":
        guard_value = 4 + level + max(1, derived.get("spell_power", 0) // 4)
        heal_amount = max(1, 4 + derived.get("healing_power", 0) // 2)
        for ally in allies:
            state = encounter._get_participant_state(ally)
            state["guard"] = max(state.get("guard", 0), guard_value)
            encounter._save_participant_state(ally, state)
            encounter._heal_character(character, ally, heal_amount, heal_type="holy")
        encounter.obj.msg_contents(f"{character.key} raises a sanctuary around the party.")
        return

    if ability_key == "cleanse":
        cleared = encounter._clear_one_harmful_effect(target)
        if cleared:
            encounter.obj.msg_contents(f"|g{character.key} cleanses the {cleared} from {target.key}.|n")
            encounter._record_participant_contribution(character, meaningful=True, utility=1)
        else:
            encounter.obj.msg_contents(f"{character.key} finds nothing fouled on {target.key} to cleanse.")
        encounter._heal_character(character, target, encounter._scaled_heal_amount(derived, 5, variance=2, divisor=4), heal_type="holy")
        return

    if ability_key == "radiantburst":
        fired = False
        for enemy in list(encounter.get_active_enemies()):
            fired = True
            if not encounter._roll_hit(derived["accuracy"] + 2, enemy["dodge"]):
                _emit_combat_miss(encounter, character, enemy, f"{character.key}'s {ability_name} fails to catch {enemy['key']} in the flare.")
                continue
            bonus = 3 + (4 if "undead" in enemy.get("tags", []) else 0)
            encounter._damage_enemy(character, enemy, encounter._spell_damage(derived["spell_power"], enemy["armor"], bonus=bonus), damage_type="holy")
        if not fired:
            encounter.obj.msg_contents(f"{character.key}'s {ability_name} finds no targets.")
        return

    if ability_key == "guardianlight":
        encounter._heal_character(character, target, encounter._scaled_heal_amount(derived, 22, variance=5, divisor=2), heal_type="holy")
        target_state = encounter._get_participant_state(target)
        target_state["guard"] = max(target_state.get("guard", 0), 6 + level + max(1, derived.get("healing_power", 0)))
        encounter._save_participant_state(target, target_state)
        encounter.obj.msg_contents(f"{character.key} leaves a guardian light hanging over {target.key}.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=target_state["guard"], utility=1)


def _execute_paladin_ability(encounter, character, ability_key, ability_name, target, derived, level, allies, enemies):
    if ability_key == "holystrike":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} skids off {target['key']} without purchase.")
            encounter._add_threat(character, 4)
            return
        holy_bonus = max(1, derived.get("spell_power", 0) // 4)
        extra_text = " Sacred force rides the impact."
        if "undead" in target.get("tags", []):
            holy_bonus += 4
            extra_text = " Holy force bites especially deep into the restless dead."
        damage = encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=3 + holy_bonus)
        encounter._damage_enemy(character, target, damage, extra_text=extra_text, damage_type="holy")
        encounter._add_threat(character, 7)
        return

    if ability_key == "guardingaura":
        guard_value = 6 + character.db.brave_level * 2 + max(1, derived.get("spell_power", 0) // 4)
        state = encounter._get_participant_state(target)
        state["guard"] = max(state.get("guard", 0), guard_value)
        encounter._save_participant_state(target, state)
        encounter._apply_reaction_guard(character, target, amount=guard_value, label="Guarding Aura")
        if target.id == character.id:
            encounter.obj.msg_contents(f"{character.key} gathers a guarding aura around themself.")
        else:
            encounter.obj.msg_contents(f"{character.key} throws a guarding aura over {target.key}.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=guard_value, utility=1)
        encounter._add_threat(character, 8)
        return

    if ability_key == "judgement":
        if not encounter._roll_hit(derived["accuracy"] + 3, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} fails to pin {target['key']} in place.")
            encounter._add_threat(character, 4)
            return
        bonus = 2 + max(1, derived.get("spell_power", 0) // 4)
        if target.get("marked_turns", 0) > 0 or target.get("bound_turns", 0) > 0:
            bonus += 2
        encounter._damage_enemy(
            character,
            target,
            encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=bonus),
            extra_text=" Judgement rides the blow.",
            damage_type="holy",
        )
        encounter._add_threat(character, 8)
        return

    if ability_key == "handofmercy":
        encounter._heal_character(character, target, encounter._scaled_heal_amount(derived, 15, variance=4, divisor=4), heal_type="holy")
        cleared = encounter._clear_one_harmful_effect(target)
        if cleared:
            encounter.obj.msg_contents(f"|gMercy steadies {target.key} and clears the {cleared}.|n")
            encounter._record_participant_contribution(character, meaningful=True, utility=1)
        return

    if ability_key == "consecrate":
        for enemy in enemies:
            encounter._damage_enemy(
                character,
                enemy,
                encounter._spell_damage(derived["spell_power"], enemy["armor"], bonus=2),
                extra_text=" Consecrated light scorches the ground beneath it.",
                damage_type="holy",
            )
        for ally in allies:
            state = encounter._get_participant_state(ally)
            state["guard"] = max(state.get("guard", 0), 2 + max(1, derived.get("spell_power", 0) // 5))
            encounter._save_participant_state(ally, state)
        encounter._add_threat(character, 9)
        return

    if ability_key == "shieldofdawn":
        state = encounter._get_participant_state(target)
        state["guard"] = max(state.get("guard", 0), 8 + level + max(1, derived.get("spell_power", 0) // 3))
        encounter._save_participant_state(target, state)
        encounter._apply_reaction_guard(character, target, amount=state["guard"], label="Shield of Dawn")
        encounter.obj.msg_contents(f"{character.key} turns a shield of dawn toward {target.key}.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        return

    if ability_key == "rebukeevil":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} leaves only ringing light in the air.")
            encounter._add_threat(character, 4)
            return
        bonus = 3 + (6 if "undead" in target.get("tags", []) else 0)
        encounter._damage_enemy(character, target, encounter._spell_damage(derived["spell_power"], target["armor"], bonus=bonus), damage_type="holy")
        if target["hp"] > 0 and "undead" in target.get("tags", []):
            target["bound_turns"] = max(target.get("bound_turns", 0), 1)
            encounter._save_enemy(target)
        encounter._add_threat(character, 7)
        return

    if ability_key == "avenginglight":
        for enemy in enemies:
            bonus = 5 + (3 if "undead" in enemy.get("tags", []) else 0)
            encounter._damage_enemy(character, enemy, encounter._spell_damage(derived["spell_power"], enemy["armor"], bonus=bonus), damage_type="holy")
        heal_amount = max(1, 6 + derived.get("healing_power", 0) // 2)
        for ally in allies:
            encounter._heal_character(character, ally, heal_amount, heal_type="holy")
        encounter._add_threat(character, 10)


def _execute_mage_ability(encounter, character, ability_key, ability_name, target, derived, _level, _allies, enemies):
    if ability_key == "firebolt":
        if not encounter._roll_hit(derived["accuracy"] + 4, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} flies wide of {target['key']}.")
            encounter._add_threat(character, 3)
            return
        damage = encounter._spell_damage(derived["spell_power"], target["armor"], bonus=4)
        extra_text = ""
        if target.get("bound_turns", 0) > 0:
            damage += 4
            extra_text = " The frozen target bursts in a wash of steam."
        encounter._damage_enemy(character, target, damage, extra_text=extra_text, damage_type="fire")
        return

    if ability_key == "frostbind":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} breaks apart before it can hold {target['key']}.")
            encounter._add_threat(character, 3)
            return
        damage = encounter._spell_damage(derived["spell_power"], target["armor"], bonus=1)
        encounter._damage_enemy(character, target, damage, extra_text=" Frost locks around its limbs.", damage_type="frost")
        if target["hp"] > 0:
            target["bound_turns"] = max(target.get("bound_turns", 0), 1)
            encounter._save_enemy(target)
            encounter.obj.msg_contents(f"{target['key']} is bound in frost.")
            encounter._try_interrupt_enemy_action(character, target, ability_name)
        return

    if ability_key == "arcspark":
        if not encounter._roll_hit(derived["accuracy"] + 5, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} crackles harmlessly past {target['key']}.")
            encounter._add_threat(character, 3)
            return
        primary_damage = encounter._spell_damage(derived["spell_power"], target["armor"], bonus=3)
        encounter._damage_enemy(character, target, primary_damage, damage_type="lightning")
        other_enemies = [enemy for enemy in enemies if enemy["id"] != target["id"]]
        if other_enemies:
            secondary = other_enemies[0]
            splash = max(1, primary_damage // 2)
            encounter._damage_enemy(character, secondary, splash, extra_text=" Arc spark leaps to a second target.", damage_type="lightning")
        return

    if ability_key == "flamewave":
        fired = False
        for enemy in enemies:
            fired = True
            bonus = 3 + (3 if enemy.get("bound_turns", 0) > 0 else 0)
            encounter._damage_enemy(character, enemy, encounter._spell_damage(derived["spell_power"], enemy["armor"], bonus=bonus), damage_type="fire")
        if not fired:
            encounter.obj.msg_contents(f"{character.key}'s {ability_name} washes across empty ground.")
        return

    if ability_key == "manashield":
        state = encounter._get_participant_state(character)
        state["guard"] = max(state.get("guard", 0), 6 + max(1, derived.get("spell_power", 0) // 2))
        encounter._save_participant_state(character, state)
        encounter.obj.msg_contents(f"{character.key} draws mana tight into a shimmering shield.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        return

    if ability_key == "staticfield":
        for enemy in enemies:
            encounter._damage_enemy(character, enemy, encounter._spell_damage(derived["spell_power"], enemy["armor"], bonus=1), damage_type="lightning")
            if enemy["hp"] > 0:
                enemy["marked_turns"] = max(enemy.get("marked_turns", 0), 2)
                encounter._save_enemy(enemy)
        return

    if ability_key == "icelance":
        if not encounter._roll_hit(derived["accuracy"] + 4, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} shatters wide of {target['key']}.")
            encounter._add_threat(character, 3)
            return
        bonus = 4 + (6 if target.get("bound_turns", 0) > 0 else 0)
        encounter._damage_enemy(
            character,
            target,
            encounter._spell_damage(derived["spell_power"], target["armor"], bonus=bonus),
            extra_text=" The lance spears through the cold already holding the target.",
            damage_type="frost",
        )
        return

    if ability_key == "meteorsigil":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} detonates just off the mark.")
            encounter._add_threat(character, 4)
            return
        encounter._damage_enemy(
            character,
            target,
            encounter._spell_damage(derived["spell_power"], target["armor"], bonus=10),
            extra_text=" The sigil lands with catastrophic force.",
            damage_type="fire",
        )
        for enemy in [enemy for enemy in enemies if enemy["id"] != target["id"]]:
            splash = max(3, derived.get("spell_power", 0) // 3 + random.randint(2, 4))
            encounter._damage_enemy(character, enemy, splash, extra_text=" Meteor fire splashes across the line.", damage_type="fire")


def _execute_rogue_ability(encounter, character, ability_key, ability_name, target, derived, level, _allies, _enemies):
    if ability_key == "stab":
        if not encounter._roll_hit(derived["accuracy"] + 8, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} slips past {target['key']} without finding anything vital.")
            encounter._add_threat(character, 3)
            return
        setup_bonus = encounter._consume_feint_bonus(character)
        damage = encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=3 + setup_bonus)
        openings = []
        if target.get("marked_turns", 0) > 0:
            damage += 4
            openings.append("mark")
        if target.get("bound_turns", 0) > 0:
            damage += 4
            openings.append("bind")

        extra_text = ""
        if setup_bonus and openings:
            extra_text = " The feint and the opening line up perfectly."
        elif setup_bonus:
            extra_text = " The feint leaves the strike perfectly placed."
        elif openings:
            extra_text = " You drive into the opening without mercy."

        encounter._damage_enemy(character, target, damage, extra_text=extra_text, damage_type="physical")
        return

    if ability_key == "feint":
        state = encounter._get_participant_state(character)
        guard_value = 4 + character.db.brave_level
        state["guard"] = max(state.get("guard", 0), guard_value)
        state["feint_turns"] = 2
        state["feint_accuracy_bonus"] = 6
        state["feint_dodge_bonus"] = 10
        encounter._save_participant_state(character, state)
        encounter._apply_reaction_guard(character, character, amount=guard_value, label="Feint")
        encounter.obj.msg_contents(f"{character.key} slips into a false opening, ready to punish the first bad reaction.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        return

    if ability_key == "backstab":
        if not encounter._roll_hit(derived["accuracy"] + 10, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} never finds the angle on {target['key']}.")
            encounter._add_threat(character, 4)
            return
        openings = 0
        if target.get("marked_turns", 0) > 0:
            openings += 4
        if target.get("bound_turns", 0) > 0:
            openings += 4
        stealth_bonus = encounter._consume_stealth_bonus(character)
        damage = encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=5 + openings + stealth_bonus)
        encounter._damage_enemy(character, target, damage, extra_text=" The blade lands exactly where the target is weakest.", damage_type="physical")
        return

    if ability_key == "poisonblade":
        if not encounter._roll_hit(derived["accuracy"] + 4, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} nicks only air.")
            encounter._add_threat(character, 3)
            return
        encounter._damage_enemy(character, target, encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=3), damage_type="poison")
        if target["hp"] > 0:
            encounter._apply_enemy_poison(
                target,
                turns=2,
                damage=4,
                message=f"|gVenom spreads through {target['key']} from the poisoned strike!|n",
            )
        return

    if ability_key == "vanish":
        state = encounter._get_participant_state(character)
        state["stealth_turns"] = max(state.get("stealth_turns", 0), 1)
        state["feint_turns"] = max(state.get("feint_turns", 0), 1)
        state["feint_dodge_bonus"] = max(state.get("feint_dodge_bonus", 0), 8)
        encounter._save_participant_state(character, state)
        encounter.obj.msg_contents(f"{character.key} drops from sight and waits for the line to break.")
        encounter._record_participant_contribution(character, meaningful=True, utility=1)
        return

    if ability_key == "cheapshot":
        if not encounter._roll_hit(derived["accuracy"] + 6, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} never finds soft ground beneath {target['key']}.")
            encounter._add_threat(character, 4)
            return
        encounter._damage_enemy(character, target, encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=4), damage_type="physical")
        if target["hp"] > 0:
            target["bound_turns"] = max(target.get("bound_turns", 0), 1)
            encounter._save_enemy(target)
            encounter._try_interrupt_enemy_action(character, target, ability_name)
        return

    if ability_key == "shadowstep":
        if not encounter._roll_hit(derived["accuracy"] + 12, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} leaves only a blur behind {target['key']}.")
            encounter._add_threat(character, 4)
            return
        bonus = 5 + encounter._consume_stealth_bonus(character)
        encounter._damage_enemy(character, target, encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=bonus), damage_type="physical")
        state = encounter._get_participant_state(character)
        state["guard"] = max(state.get("guard", 0), 3 + level)
        encounter._save_participant_state(character, state)
        return

    if ability_key == "eviscerate":
        if not encounter._roll_hit(derived["accuracy"] + 4, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} tears through nothing but momentum.")
            encounter._add_threat(character, 5)
            return
        bonus = 7
        if target.get("marked_turns", 0) > 0:
            bonus += 4
        if target.get("bound_turns", 0) > 0:
            bonus += 4
        if target.get("bleed_turns", 0) > 0:
            bonus += 4
        if target.get("poison_turns", 0) > 0:
            bonus += 4
        bonus += encounter._consume_stealth_bonus(character)
        encounter._damage_enemy(character, target, encounter._weapon_damage(derived["attack_power"], target["armor"], bonus=bonus), damage_type="physical")


def _execute_druid_ability(encounter, character, ability_key, ability_name, target, derived, level, allies, enemies):
    if ability_key == "thornlash":
        if not encounter._roll_hit(derived["accuracy"] + 3, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} whips through empty air around {target['key']}.")
            encounter._add_threat(character, 3)
            return
        lash_bonus = 2
        if target.get("marked_turns", 0) > 0 or target.get("bound_turns", 0) > 0:
            lash_bonus += 3
        damage = encounter._spell_damage(derived["spell_power"], target["armor"], bonus=lash_bonus)
        encounter._damage_enemy(character, target, damage, extra_text=" Thorned force drags across the target.", damage_type="nature")
        if target["hp"] > 0:
            target["marked_turns"] = max(target.get("marked_turns", 0), 2)
            encounter._save_enemy(target)
            encounter.obj.msg_contents(f"{target['key']} is left exposed by the thorn lash.")
        return

    if ability_key == "minormend":
        amount = 9 + derived["spell_power"] // 3 + random.randint(0, 3)
        encounter._heal_character(character, target, amount, heal_type="nature")
        cleared = encounter._clear_one_harmful_effect(target)
        if cleared:
            encounter.obj.msg_contents(f"|gNatural calm eases {target.key}'s {cleared}.|n")
            encounter._record_participant_contribution(character, meaningful=True, utility=1)
        return

    if ability_key == "entanglingroots":
        if not encounter._roll_hit(derived["accuracy"] + 2, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} clutches only empty ground.")
            encounter._add_threat(character, 3)
            return
        encounter._damage_enemy(character, target, encounter._spell_damage(derived["spell_power"], target["armor"], bonus=2), damage_type="nature")
        if target["hp"] > 0:
            target["bound_turns"] = max(target.get("bound_turns", 0), 1)
            encounter._save_enemy(target)
            encounter._try_interrupt_enemy_action(character, target, ability_name)
        return

    if ability_key == "moonfire":
        if not encounter._roll_hit(derived["accuracy"] + 3, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} gutters out before it reaches {target['key']}.")
            encounter._add_threat(character, 3)
            return
        bonus = 4 + (3 if target.get("marked_turns", 0) > 0 or target.get("bound_turns", 0) > 0 else 0)
        encounter._damage_enemy(character, target, encounter._spell_damage(derived["spell_power"], target["armor"], bonus=bonus), damage_type="nature")
        if target["hp"] > 0:
            target["marked_turns"] = max(target.get("marked_turns", 0), 1)
            encounter._save_enemy(target)
        return

    if ability_key == "barkskin":
        state = encounter._get_participant_state(target)
        state["guard"] = max(state.get("guard", 0), 7 + level + max(1, derived.get("spell_power", 0) // 3))
        encounter._save_participant_state(target, state)
        encounter.obj.msg_contents(f"{character.key} wraps {target.key} in a hard barkskin ward.")
        encounter._record_participant_contribution(character, meaningful=True, mitigation=state["guard"], utility=1)
        return

    if ability_key == "livingcurrent":
        encounter._heal_character(character, target, encounter._scaled_heal_amount(derived, 13, variance=4, divisor=3), heal_type="nature")
        secondary_targets = [
            ally
            for ally in allies
            if ally.id != target.id
            and (ally.db.brave_resources or {}).get("hp", 0) < ally.db.brave_derived_stats.get("max_hp", 0)
        ]
        if secondary_targets:
            encounter._heal_character(
                character,
                secondary_targets[0],
                max(1, encounter._scaled_heal_amount(derived, 6, variance=2, divisor=4) // 2),
                heal_type="nature",
            )
        return

    if ability_key == "swarm":
        for enemy in enemies:
            encounter._damage_enemy(
                character,
                enemy,
                encounter._spell_damage(derived["spell_power"], enemy["armor"], bonus=2),
                extra_text=" The swarm strips away safe footing.",
                damage_type="nature",
            )
            if enemy["hp"] > 0:
                enemy["marked_turns"] = max(enemy.get("marked_turns", 0), 1)
                encounter._save_enemy(enemy)
        return

    if ability_key == "rejuvenationgrove":
        for ally in allies:
            encounter._heal_character(character, ally, encounter._scaled_heal_amount(derived, 10, variance=3, divisor=4), heal_type="nature")
            cleared = encounter._clear_one_harmful_effect(ally)
            if cleared:
                encounter.obj.msg_contents(f"|gThe grove's calm strips the {cleared} from {ally.key}.|n")
                encounter._record_participant_contribution(character, meaningful=True, utility=1)
        return

    if ability_key == "wrathofthegrove":
        if not encounter._roll_hit(derived["accuracy"] + 3, target["dodge"]):
            _emit_combat_miss(encounter, character, target, f"{character.key}'s {ability_name} churns the ground but misses {target['key']}.")
            encounter._add_threat(character, 4)
            return
        bonus = 7 + (4 if target.get("marked_turns", 0) > 0 or target.get("bound_turns", 0) > 0 else 0)
        encounter._damage_enemy(
            character,
            target,
            encounter._spell_damage(derived["spell_power"], target["armor"], bonus=bonus),
            extra_text=" The whole grove seems to answer the strike.",
            damage_type="nature",
        )
