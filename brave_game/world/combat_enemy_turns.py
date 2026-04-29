"""Enemy turn execution helpers for Brave combat encounters."""

import random

from world.combat_actor_utils import (
    _combat_entry_ref,
    _combat_target_name,
    _enemy_damage_type,
    _is_companion_actor,
    get_incoming_damage_reduction,
)


ENEMY_HEAL_ACTIONS = {
    "mossling": ("Mend Spores", (8, 12), ""),
    "barrow_wisp": ("Grave Light", (7, 11), "|m{source} feeds cold grave-light into {target}.|n"),
    "fen_wisp": ("Marsh Light", (8, 12), "|g{source} sheds sick marsh light over {target}.|n"),
    "hollow_wisp": ("Lamp Light", (9, 13), "|y{source} spills drowned lamp-light into {target}.|n"),
}


def execute_enemy_turn(encounter, enemy):
    """Resolve one enemy turn for an active combat encounter."""

    self = encounter
    reaction_state = self._enemy_reaction_state(enemy)
    telegraphed = reaction_state["telegraphed"]
    action_label = reaction_state["label"]
    enemy = self._handle_enemy_specials(enemy)
    if enemy.get("hidden_turns", 0) > 0:
        enemy["hidden_turns"] = max(0, enemy["hidden_turns"] - 1)
        self._save_enemy(enemy)
        if enemy["template_key"] == "miretooth":
            self.obj.msg_contents("|rMiretooth ghosts through the reeds somewhere just outside your sightline.|n")
        else:
            self.obj.msg_contents("|rOld Greymaw slips unseen through the brush.|n")
        return

    heal_action = ENEMY_HEAL_ACTIONS.get(enemy["template_key"])
    if heal_action:
        action_label, heal_range, message_template = heal_action
        ally = self._find_wounded_enemy(exclude_id=enemy["id"])
        if ally and ally["hp"] <= (ally["max_hp"] * 3) // 4:
            self._announce_combat_action(enemy, action_label)
            heal_amount = random.randint(*heal_range)
            if self._heal_enemy(enemy, ally, heal_amount):
                if message_template:
                    self.obj.msg_contents(message_template.format(source=enemy["key"], target=ally["key"]))
                return

    target = self._choose_enemy_target(enemy)
    if not target:
        return

    original_target = target
    original_target_state = self._get_participant_state(target)
    redirected_by = None
    if telegraphed:
        redirect_to = original_target_state.get("reaction_redirect_to")
        redirect_target = self._get_participant_target(redirect_to) if redirect_to else None
        if redirect_target and redirect_target in self.get_active_participants():
            redirected_by = redirect_target
            target = redirect_target

    derived = self._get_effective_derived(target)
    target_name = _combat_target_name(target, "Companion")
    target_hp = target.get("hp", 0) if _is_companion_actor(target) else (target.db.brave_resources or {}).get("hp", 0)
    target_max_hp = target.get("max_hp", 1) if _is_companion_actor(target) else target.db.brave_derived_stats["max_hp"]

    if enemy.get("bound_turns", 0) > 0:
        enemy["bound_turns"] = max(0, enemy["bound_turns"] - 1)
        self._save_enemy(enemy)
        self.obj.msg_contents(f"{enemy['key']} struggles against the frost and loses the moment.")
        return

    if telegraphed or action_label != "Attack":
        self._announce_combat_action(enemy, action_label)

    damage_bonus = 0
    hit_text = f"{enemy['key']} hits {target_name} for {{damage}} damage."
    if enemy["template_key"] == "forest_wolf" and target_hp <= target_max_hp // 2:
        damage_bonus += 3
        hit_text = f"{enemy['key']} lunges at {target_name} for {{damage}} damage."

    if enemy["template_key"] == "old_greymaw" and enemy.get("reposition_ready"):
        damage_bonus += 6
        hit_text = f"|rOld Greymaw bursts from the brush and tears into {target_name} for {{damage}} damage!|n"
        enemy["reposition_ready"] = False
        self._save_enemy(enemy)

    if enemy["template_key"] == "tower_archer":
        bandit_support = [
            other
            for other in self.get_active_enemies()
            if other["id"] != enemy["id"] and "bandit" in other.get("tags", [])
        ]
        if bandit_support:
            damage_bonus += 2
            hit_text = f"{enemy['key']} shoots through the melee and drills {target_name} for {{damage}} damage."

    if enemy["template_key"] == "captain_varn_blackreed" and target_hp <= target_max_hp // 2:
        damage_bonus += 5
        hit_text = f"|rBlackreed spots the weakness and drives into {target_name} for {{damage}} damage!|n"

    if enemy["template_key"] == "grubnak_the_pot_king" and enemy.get("enraged"):
        damage_bonus += 3
        hit_text = f"|rGrubnak slams through the steam and batters {target_name} for {{damage}} damage!|n"

    if enemy["template_key"] == "miretooth" and enemy.get("reposition_ready"):
        damage_bonus += 7
        hit_text = f"|rMiretooth erupts out of the black reeds and mauls {target_name} for {{damage}} damage!|n"
        enemy["reposition_ready"] = False
        self._save_enemy(enemy)

    if enemy["template_key"] == "hollow_lantern" and enemy.get("enraged"):
        damage_bonus += 4
        hit_text = f"|rThe Hollow Lantern floods the chamber with white-black fire and sears {target_name} for {{damage}} damage!|n"

    if not self._roll_hit(enemy["accuracy"], derived["dodge"]):
        if telegraphed:
            self._record_telegraph_outcome(enemy, "unanswered", label=action_label, target=target)
        self.obj.msg_contents(f"{enemy['key']} misses {target_name}.")
        self._emit_miss_fx(enemy, target)
        return

    if enemy.get("attack_kind") == "spell":
        damage = self._spell_damage(enemy.get("spell_power", enemy["attack_power"]), derived["armor"], bonus=damage_bonus)
    else:
        damage = self._weapon_damage(enemy["attack_power"], derived["armor"], bonus=damage_bonus)
    state = self._get_participant_state(target)
    reaction_prevented = 0
    reaction_source = None
    reaction_label = state.get("reaction_label") or "guard"
    if telegraphed and state.get("reaction_guard", 0):
        reaction_prevented = min(max(0, damage - 1), int(state.get("reaction_guard", 0) or 0))
        reaction_source = self._get_participant_target(state.get("reaction_guard_source")) if state.get("reaction_guard_source") else None
        damage = max(1, damage - reaction_prevented)
    if state.get("guard", 0):
        prevented = min(damage - 1, state["guard"])
        damage = max(1, damage - state["guard"])
        if prevented > 0:
            self._record_participant_contribution(target, mitigation=prevented)
    if telegraphed:
        if redirected_by:
            self._record_telegraph_outcome(enemy, "redirected", label=action_label, answer=reaction_label, target=target)
            self.obj.msg_contents(
                f"|y{_combat_target_name(redirected_by, 'Companion')} cuts in front of {enemy['key']}'s {action_label}, pulling it off {_combat_target_name(original_target, 'Companion')}.|n"
            )
        elif reaction_prevented > 0:
            self._record_telegraph_outcome(enemy, "mitigated", label=action_label, answer=reaction_label, target=target)
            source_name = _combat_target_name(reaction_source or target, "Companion")
            self.obj.msg_contents(
                f"|y{source_name}'s {reaction_label} takes the edge off {enemy['key']}'s {action_label}.|n"
            )
        else:
            self._record_telegraph_outcome(enemy, "unanswered", label=action_label, target=target)
            self.obj.msg_contents(f"|r{enemy['key']}'s {action_label} lands clean.|n")
    damage = max(1, damage - get_incoming_damage_reduction(target))
    if _is_companion_actor(target):
        resources = {"hp": max(0, int(target.get("hp", 0) or 0) - damage)}
        target["hp"] = resources["hp"]
        self._save_companion(target)
    else:
        resources = dict(target.db.brave_resources or {})
        resources["hp"] = max(0, resources["hp"] - damage)
        target.db.brave_resources = resources
    if telegraphed and reaction_prevented > 0:
        self._record_participant_contribution(reaction_source or target, mitigation=reaction_prevented, utility=1)
    self._record_participant_contribution(target, hits_taken=damage)
    self.obj.msg_contents(hit_text.format(damage=damage))
    self._emit_combat_fx(
        kind="damage",
        source=enemy["key"],
        source_ref=_combat_entry_ref(enemy),
        target=target_name,
        target_ref=_combat_entry_ref(target),
        amount=damage,
        text=str(damage),
        tone="damage",
        impact="damage",
        element=_enemy_damage_type(enemy),
        lunge=True,
    )
    sacred_turns = int(state.get("sacred_aegis_turns", 0) or 0)
    sacred_source = self._get_participant_target(state.get("sacred_aegis_source")) if state.get("sacred_aegis_source") else None
    if (
        damage > 0
        and sacred_turns > 0
        and sacred_source
        and sacred_source in self.get_active_participants()
        and enemy.get("hp", 0) > 0
    ):
        source_derived = self._get_effective_derived(sacred_source)
        retaliation = max(
            1,
            int(state.get("sacred_aegis_power", 0) or 0) + max(1, source_derived.get("spell_power", 0) // 4) - 1,
        )
        if enemy.get("judged_turns", 0) > 0:
            retaliation += 1
        self._damage_enemy(
            sacred_source,
            enemy,
            retaliation,
            extra_text=f" {_combat_target_name(sacred_source, 'Companion')}'s ward answers the blow.",
            damage_type="holy",
        )
        self._record_participant_contribution(sacred_source, meaningful=True, utility=1)

    if enemy["template_key"] == "ruk_fence_cutter" and resources["hp"] > 0 and random.randint(1, 100) <= 55:
        self._apply_bleed(target, turns=2, damage=4)
    elif enemy["template_key"] == "old_greymaw" and resources["hp"] > 0:
        self._apply_bleed(target, turns=2, damage=5 if damage_bonus else 4)
    elif enemy["template_key"] == "grave_crow" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
        self._apply_bleed(target, turns=2, damage=3)
    elif enemy["template_key"] == "carrion_hound" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
        self._apply_bleed(target, turns=2, damage=4)
    elif enemy["template_key"] == "cave_spider" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
        self._apply_snare(target, turns=2, accuracy_penalty=6, dodge_penalty=6)
    elif enemy["template_key"] == "briar_imp" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_curse(target, turns=2, armor_penalty=4, message=f"|m{target_name} is wrapped in a briar curse!|n")
    elif enemy["template_key"] == "goblin_hexer" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_curse(target, turns=2, armor_penalty=4, message=f"|m{target_name} is knotted up in goblin hex-thread!|n")
    elif enemy["template_key"] == "cave_bat_swarm" and resources["hp"] > 0 and random.randint(1, 100) <= 40:
        self._apply_bleed(target, turns=2, damage=3)
    elif enemy["template_key"] == "sludge_slime" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_snare(target, turns=2, accuracy_penalty=5, dodge_penalty=5)
    elif enemy["template_key"] in {"restless_shade", "barrow_wisp", "sir_edric_restless"} and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_curse(target, turns=2, armor_penalty=4, message=f"|m{target_name} shudders under a grave-cold curse!|n")
    elif enemy["template_key"] in {"mag_clamp_drone", "foreman_coilback"} and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_snare(target, turns=2, accuracy_penalty=5, dodge_penalty=5)
    elif enemy["template_key"] == "grubnak_the_pot_king" and resources["hp"] > 0 and random.randint(1, 100) <= 55:
        self._apply_snare(target, turns=2, accuracy_penalty=4, dodge_penalty=4)
    elif enemy["template_key"] == "bog_creeper" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_snare(target, turns=2, accuracy_penalty=6, dodge_penalty=6)
    elif enemy["template_key"] == "fen_wisp" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_curse(target, turns=2, armor_penalty=5, message=f"|m{target_name} shudders under a marsh-light curse!|n")
    elif enemy["template_key"] == "rot_crow" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
        self._apply_bleed(target, turns=2, damage=4)
    elif enemy["template_key"] == "mire_hound" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
        self._apply_poison(target, turns=2, damage=4, accuracy_penalty=5, message=f"|g{target_name} reels under a swamp-sick bite!|n")
    elif enemy["template_key"] == "miretooth" and resources["hp"] > 0 and random.randint(1, 100) <= 60:
        self._apply_poison(target, turns=3, damage=5, accuracy_penalty=6, message=f"|gMiretooth's bite leaves black fen venom burning through {target_name}!|n")
    elif enemy["template_key"] == "drowned_warder" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
        self._apply_snare(target, turns=2, accuracy_penalty=5, dodge_penalty=5)
    elif enemy["template_key"] == "silt_stalker" and resources["hp"] > 0 and random.randint(1, 100) <= 45:
        self._apply_bleed(target, turns=2, damage=4)
    elif enemy["template_key"] == "hollow_wisp" and resources["hp"] > 0 and random.randint(1, 100) <= 50:
        self._apply_curse(target, turns=2, armor_penalty=5, message=f"|m{target_name} shudders under a hollow-light curse!|n")
    elif enemy["template_key"] == "hollow_lantern" and resources["hp"] > 0 and random.randint(1, 100) <= 60:
        self._apply_curse(target, turns=3, armor_penalty=6, message=f"|mThe Hollow Lantern brands {target_name} in wrong light!|n")

    if resources["hp"] <= 0:
        if _is_companion_actor(target):
            self._defeat_companion(target)
        else:
            self._defeat_character(target)
