"""Combat-focused browser view payload builders for Brave."""

import world.browser_views as browser_views
from world.ability_icons import get_ability_icon_name
from world.character_icons import get_class_icon
from world.combat_atb import render_atb_state
from world.resonance import get_resource_label
from world.browser_views import (
    CLASSES,
    ITEM_TEMPLATES,
    _action,
    _chip,
    _combat_card_size_class,
    _enemy_icon,
    _entry,
    _item,
    _make_view,
    _meter,
    _picker,
    _reactive_view,
    _section,
    get_item_use_profile,
)


def build_combat_view(encounter, character):
    """Return a browser-first sticky combat view with clickable actions."""

    from typeclasses.scripts import ABILITY_LIBRARY

    condition_telegraph_enemies = {
        "briar_imp",
        "cave_bat_swarm",
        "cave_spider",
        "carrion_hound",
        "drowned_warder",
        "fen_wisp",
        "goblin_hexer",
        "grave_crow",
        "grubnak_the_pot_king",
        "hollow_lantern",
        "hollow_wisp",
        "mire_hound",
        "miretooth",
        "restless_shade",
        "rot_crow",
        "ruk_fence_cutter",
        "sir_edric_restless",
        "sludge_slime",
    }

    timing_scale = max(1, int(round(1 / max(0.1, float(getattr(encounter, "interval", 1) or 1)))))

    def display_atb_ticks(raw_ticks):
        raw_ticks = int(raw_ticks or 0)
        if raw_ticks <= 0:
            return 0
        return max(1, (raw_ticks + timing_scale - 1) // timing_scale)

    render_now_ms = int(round(browser_views.time.time() * 1000))
    render_tick_ms = max(1, int(round(float(getattr(encounter, "interval", 1) or 1) * 1000)))

    def participant_id(participant):
        return participant.get("id") if isinstance(participant, dict) else participant.id

    def participant_name(participant):
        return str(participant.get("key") if isinstance(participant, dict) else participant.key)

    def participant_resources(participant):
        if isinstance(participant, dict):
            return {"hp": int(participant.get("hp", 0) or 0)}
        return participant.db.brave_resources or {}

    def participant_derived(participant):
        if isinstance(participant, dict):
            return {
                "max_hp": int(participant.get("max_hp", 1) or 1),
                "max_mana": 0,
                "max_stamina": 0,
            }
        return participant.db.brave_derived_stats or {}

    def participant_background_icon(participant):
        if isinstance(participant, dict):
            return participant.get("icon", "pets")
        return get_class_icon(participant.db.brave_class, CLASSES.get(participant.db.brave_class))

    def actor_atb_state(*, participant=None, enemy=None):
        getter = getattr(encounter, "_get_actor_atb_state", None)
        if not callable(getter):
            return {}
        try:
            if participant is not None:
                if isinstance(participant, dict):
                    return render_atb_state(getter(companion=participant) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
                return render_atb_state(getter(character=participant) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
            if enemy is not None:
                return render_atb_state(getter(enemy=enemy) or {}, tick_ms=render_tick_ms, now_ms=render_now_ms)
        except Exception:
            return {}
        return {}

    def combat_action_item(action):
        return _item(
            action.get("text", action.get("label", "")),
            badge=action.get("badge"),
            command=action.get("command"),
            prefill=action.get("prefill"),
            confirm=action.get("confirm"),
            actions=action.get("actions"),
            picker=action.get("picker"),
            tooltip=action.get("tooltip"),
        )

    def combat_option_icon(action):
        if action.get("kind") == "ability":
            return get_ability_icon_name(action.get("key"))
        if action.get("kind") == "social":
            return "sentiment_satisfied"
        return "lunch_dining"

    def party_has_harmful_condition():
        for participant in participants:
            state = encounter._get_participant_state(participant)
            if any(int(state.get(key, 0) or 0) > 0 for key in ("bleed_turns", "poison_turns", "curse_turns", "snare_turns")):
                return True
        return False

    def build_reaction_window():
        roles = set()
        threats = []
        harmful_condition_active = party_has_harmful_condition()
        for enemy in enemies:
            state = actor_atb_state(enemy=enemy)
            if (state or {}).get("phase") != "winding":
                continue
            timing = dict((state or {}).get("timing") or {})
            action = dict((state or {}).get("current_action") or {})
            threat_roles = {"guard"}
            if timing.get("interruptible"):
                threat_roles.add("interrupt")
            template_key = str(enemy.get("template_key") or "").strip().lower()
            if harmful_condition_active or template_key in condition_telegraph_enemies:
                threat_roles.add("cleanse")
            roles.update(threat_roles)
            threats.append(
                {
                    "enemy_id": enemy.get("id"),
                    "enemy": str(enemy.get("key") or "Enemy"),
                    "label": action.get("label") or enemy.get("telegraph_label") or "Attack",
                    "interruptible": bool(timing.get("interruptible")),
                    "roles": sorted(threat_roles),
                }
            )
        return {"active": bool(threats), "roles": sorted(roles), "threats": threats}

    def mark_reaction_actions(actions, reaction_roles):
        for action in actions:
            role = action.get("reaction_role")
            recommended = bool(role and role in reaction_roles)
            action["reaction_recommended"] = recommended
            if recommended:
                action["reaction_hint"] = f"Reaction window: {role}"
                if action.get("tooltip"):
                    action["tooltip"] = f"{action['tooltip']}\nReaction window: useful now."
                else:
                    action["tooltip"] = "Reaction window: useful now."
        return actions

    def combat_picker_options(action):
        options = []
        reaction_recommended = bool(action.get("reaction_recommended"))
        if action.get("enabled"):
            meta = action.get("text")
            if reaction_recommended:
                meta = f"{meta} · REACTION" if meta else "REACTION"
            primary = {
                "label": action.get("label") or action.get("text") or "",
                "icon": combat_option_icon(action),
                "meta": meta,
                "tone": "good" if reaction_recommended else ("accent" if action.get("kind") == "ability" else "good"),
                "tooltip": action.get("tooltip"),
            }
            if action.get("picker"):
                primary["picker"] = action.get("picker")
            elif action.get("command"):
                primary["command"] = action.get("command")
            if primary.get("command") or primary.get("picker"):
                options.append(primary)
        for inline_action in action.get("actions", []) or []:
            picker = inline_action.get("picker")
            command = inline_action.get("command")
            if not picker and not command:
                continue
            option = {
                "label": action.get("label") or action.get("text") or "",
                "icon": inline_action.get("icon") or combat_option_icon(action),
                "meta": inline_action.get("label"),
                "tone": "good" if reaction_recommended else (inline_action.get("tone") or "muted"),
                "tooltip": action.get("tooltip"),
            }
            if picker:
                option["picker"] = picker
            if command:
                option["command"] = command
            options.append(option)
        return options

    def build_combat_action_picker(title, icon_name, actions, empty_text):
        options = []
        for action in actions:
            options.extend(combat_picker_options(action))
        has_reaction = any(action.get("reaction_recommended") for action in actions)
        return _action(
            title,
            None,
            icon_name,
            tone="good" if has_reaction else ("accent" if options else "muted"),
            picker=_picker(
                title,
                subtitle="Reaction tools are highlighted." if has_reaction else "Choose an action.",
                picker_id=f"combat-{title.strip().lower()}",
                options=options,
                body=[] if options else [empty_text],
            ),
        )

    def atb_chip(state, *, label_ready="Ready", ready_tone="accent"):
        phase = (state or {}).get("phase")
        if phase == "ready":
            return _chip(label_ready, "bolt", ready_tone)
        if phase == "winding":
            ticks = display_atb_ticks((state or {}).get("ticks_remaining", 0))
            return _chip(f"Winding {ticks}", "hourglass_top", "danger")
        if phase == "recovering":
            ticks = display_atb_ticks((state or {}).get("ticks_remaining", 0))
            return _chip(f"Recovering {ticks}", "timer", "muted")
        if phase == "cooldown":
            ticks = display_atb_ticks((state or {}).get("ticks_remaining", 0))
            return _chip(f"Cooldown {ticks}", "timer", "muted")
        return None

    def atb_meter(state, *, enemy=False):
        state = dict(state or {})
        phase = state.get("phase")
        timing = dict(state.get("timing") or {})
        gauge = int(state.get("gauge", 0) or 0)
        ready_gauge = max(1, int(state.get("ready_gauge", 400) or 400))
        ticks_remaining = int(state.get("ticks_remaining", 0) or 0)
        phase_started_at_ms = int(state.get("phase_started_at_ms", 0) or 0)
        phase_duration_ms = int(state.get("phase_duration_ms", 0) or 0)
        elapsed_ms = max(0, render_now_ms - phase_started_at_ms) if phase_started_at_ms > 0 else 0
        phase_remaining_ms = max(0, phase_duration_ms - elapsed_ms) if phase_duration_ms > 0 else 0

        value = gauge
        tone = "atb"
        if phase in {"ready", "resolving", "winding"}:
            value = 100
            tone = "danger" if enemy else "good"
            if phase == "winding":
                tone = "danger" if enemy else "warn"
        elif phase in {"recovering", "cooldown"}:
            value = 0
            tone = "muted"
        else:
            value = max(0, min(100, int(round((gauge / ready_gauge) * 100))))
        meter_meta = {
            "kind": "atb",
            "hide_value": True,
            "phase": phase or "charging",
            "gauge": gauge,
            "phase_start_gauge": int(state.get("phase_start_gauge", gauge) or 0),
            "phase_started_at_ms": phase_started_at_ms,
            "phase_duration_ms": phase_duration_ms,
            "phase_remaining_ms": phase_remaining_ms,
            "ready_gauge": ready_gauge,
            "fill_rate": int(state.get("fill_rate", 100) or 100),
            "tick_ms": render_tick_ms,
            "ticks_remaining": ticks_remaining,
            "windup_ticks": int(timing.get("windup_ticks", 0) or 0),
            "recovery_ticks": int(timing.get("recovery_ticks", 0) or 0),
            "cooldown_ticks": int(timing.get("cooldown_ticks", 0) or 0),
        }
        return _meter("ATB", value, 100, tone=tone, meta=meter_meta)

    def build_participant_status_chips(state):
        chips = []
        if state.get("guard", 0) > 0:
            chips.append(_chip("Guarding", "shield", "good"))
        if state.get("reaction_redirect_to"):
            chips.append(_chip("Intercept", "swap_horiz", "good"))
        elif state.get("reaction_guard", 0) > 0:
            chips.append(_chip("Answer Ready", "shield", "accent"))
        if state.get("bleed_turns", 0) > 0:
            chips.append(_chip(f"Bleeding {state['bleed_turns']}", "water_drop", "danger"))
        if state.get("poison_turns", 0) > 0:
            chips.append(_chip(f"Poisoned {state['poison_turns']}", "warning", "danger"))
        if state.get("curse_turns", 0) > 0:
            chips.append(_chip(f"Cursed {state['curse_turns']}", "warning", "warn"))
        if state.get("snare_turns", 0) > 0:
            chips.append(_chip(f"Snared {state['snare_turns']}", "block", "warn"))
        if state.get("feint_turns", 0) > 0:
            chips.append(_chip("Feint Ready", "bolt", "accent"))
        if state.get("stealth_turns", 0) > 0:
            chips.append(_chip("Hidden", "visibility_off", "muted"))
        return chips

    def build_enemy_status_chips(enemy):
        chips = []
        telegraph_outcome = str(enemy.get("telegraph_outcome") or "").lower()
        telegraph_answer = str(enemy.get("telegraph_answer") or "")
        if telegraph_outcome == "interrupted":
            chips.append(_chip("Interrupted", "block", "good"))
        elif telegraph_outcome == "redirected":
            chips.append(_chip("Redirected", "swap_horiz", "good"))
        elif telegraph_outcome == "mitigated":
            chips.append(_chip("Mitigated", "shield", "good"))
        elif telegraph_outcome == "unanswered":
            chips.append(_chip("Landed Clean", "priority_high", "danger"))
        elif telegraph_outcome == "pending" and telegraph_answer:
            chips.append(_chip(f"Answer: {telegraph_answer}", "shield", "accent"))
        if enemy.get("marked_turns", 0) > 0:
            chips.append(_chip(f"Marked {enemy['marked_turns']}", "my_location", "accent"))
        if enemy.get("bound_turns", 0) > 0:
            chips.append(_chip(f"Bound {enemy['bound_turns']}", "block", "warn"))
        if enemy.get("hidden_turns", 0) > 0:
            chips.append(_chip(f"Hidden {enemy['hidden_turns']}", "visibility_off", "muted"))
        if enemy.get("shielded"):
            chips.append(_chip("Warded", "shield", "good"))
        if enemy.get("bleed_turns", 0) > 0:
            chips.append(_chip(f"Bleeding {enemy['bleed_turns']}", "water_drop", "danger"))
        if enemy.get("poison_turns", 0) > 0:
            chips.append(_chip(f"Poisoned {enemy['poison_turns']}", "warning", "warn"))
        return chips

    def hp_meter(current_hp, max_hp):
        ratio = (current_hp / max_hp) if max_hp else 0
        if ratio <= 0.25:
            tone = "danger"
        elif ratio <= 0.5:
            tone = "warn"
        else:
            tone = "good"
        return _meter("HP", current_hp, max_hp, tone=tone)

    def resource_meter(resource_key, current_value, max_value):
        short_label = {
            "mana": "MP",
            "stamina": "STA",
        }.get(resource_key, get_resource_label(resource_key, character)[:3].upper())
        tone = {
            "mana": "mana",
            "stamina": "stamina",
        }.get(resource_key, "accent")
        return _meter(short_label, current_value, max_value, tone=tone)

    enemies = encounter.get_active_enemies()
    participants = encounter.get_active_participants()
    encounter_title = (getattr(encounter.db, "encounter_title", "") or "").strip() or "Combat"

    ordered_participants = sorted(
        participants,
        key=lambda participant: (
            0 if not isinstance(participant, dict) and participant.id == character.id else 1,
            participant_name(participant).lower(),
        ),
    )
    player_participants = [participant for participant in ordered_participants if not isinstance(participant, dict)]
    companion_participants = [participant for participant in ordered_participants if isinstance(participant, dict)]
    ally_count = len(player_participants)
    companion_count = len(companion_participants)
    companion_by_owner = {}
    default_owner_id = player_participants[0].id if len(player_participants) == 1 else None
    for companion in companion_participants:
        owner_id = companion.get("owner_id")
        if owner_id is None:
            owner_id = default_owner_id
        companion_by_owner.setdefault(owner_id, []).append(companion)
    for owner_companions in companion_by_owner.values():
        owner_companions.sort(key=lambda companion: participant_name(companion).lower())

    foe_count = len(enemies)
    ally_label = "Ally" if ally_count == 1 else "Allies"
    companion_label = "Pet" if companion_count == 1 else "Pets"
    foe_label = "Foe" if foe_count == 1 else "Foes"
    pending_action = dict(getattr(encounter.db, "pending_actions", {}) or {}).get(str(character.id), {}) or {}
    selected_target_id = pending_action.get("target")
    selected_target_kind = None
    if pending_action.get("kind") == "attack":
        selected_target_kind = "enemy"
    elif pending_action.get("kind") == "ability":
        selected_ability = ABILITY_LIBRARY.get(pending_action.get("ability"))
        if selected_ability:
            selected_target_kind = selected_ability.get("target")
    elif pending_action.get("kind") == "item":
        selected_item = ITEM_TEMPLATES.get(pending_action.get("item"))
        selected_use = get_item_use_profile(selected_item, context="combat") or {}
        selected_target_kind = selected_use.get("target")

    reaction_window = build_reaction_window()
    combat_actions = browser_views.build_combat_action_payload(encounter, character)
    reaction_roles = set(reaction_window.get("roles") or [])
    mark_reaction_actions(combat_actions.get("abilities", []), reaction_roles)
    mark_reaction_actions(combat_actions.get("items", []), reaction_roles)

    def build_companion_sidecar(companion):
        resources = participant_resources(companion)
        derived = participant_derived(companion)
        state = encounter._get_participant_state(companion)
        status_chips = build_participant_status_chips(state)
        atb_state = actor_atb_state(participant=companion)
        atb_status = atb_chip(atb_state)
        if atb_status:
            status_chips = [atb_status] + list(status_chips)
        combat_state = []
        phase = (atb_state or {}).get("phase")
        if phase == "ready":
            combat_state.append("ready")
        if state.get("reaction_guard", 0) > 0 or state.get("reaction_redirect_to"):
            combat_state.append("guarding")
        if selected_target_kind == "ally" and selected_target_id == participant_id(companion):
            status_chips = list(status_chips) + [_chip("Targeted", "my_location", "good")]
            combat_state.append("selected")
        return _entry(
            participant_name(companion),
            meta="Companion",
            icon="pets",
            background_icon=participant_background_icon(companion),
            chips=status_chips[:2],
            meters=[
                atb_meter(atb_state),
                hp_meter(resources.get("hp", 0), derived.get("max_hp", 0)),
            ],
            selected=bool(selected_target_kind == "ally" and selected_target_id == participant_id(companion)),
            combat_state=combat_state,
            entry_ref=f"c:{participant_id(companion)}",
            size_class="compact",
        )

    party_entries = []
    party_count = len(player_participants)
    for participant in player_participants:
        if not isinstance(participant, dict):
            participant.ensure_brave_character()
        resources = participant_resources(participant)
        derived = participant_derived(participant)
        state = encounter._get_participant_state(participant)
        status_chips = build_participant_status_chips(state)
        atb_state = actor_atb_state(participant=participant)
        atb_status = atb_chip(atb_state)
        if atb_status:
            status_chips = [atb_status] + list(status_chips)
        combat_state = []
        phase = (atb_state or {}).get("phase")
        if phase == "ready":
            combat_state.append("ready")
        if state.get("reaction_guard", 0) > 0 or state.get("reaction_redirect_to"):
            combat_state.append("guarding")
        meters = [atb_meter(atb_state), hp_meter(resources.get("hp", 0), derived.get("max_hp", 0))]
        for resource_key in ("stamina", "mana"):
            max_value = derived.get(f"max_{resource_key}", 0)
            if max_value > 0:
                meters.append(resource_meter(resource_key, resources.get(resource_key, 0), max_value))
        if selected_target_kind == "ally" and selected_target_id == participant_id(participant):
            status_chips = list(status_chips) + [_chip("Targeted", "my_location", "good")]
            combat_state.append("selected")

        sidecars = [build_companion_sidecar(companion) for companion in companion_by_owner.get(participant.id, [])[:1]]

        party_entries.append(
            _entry(
                participant_name(participant),
                meta=None,
                icon="person",
                background_icon=participant_background_icon(participant),
                size_class=_combat_card_size_class(participant),
                chips=status_chips,
                meters=meters,
                selected=bool(selected_target_kind == "ally" and selected_target_id == participant_id(participant)),
                combat_state=combat_state,
                entry_ref=f"p:{participant.id}",
                sidecars=sidecars,
                cluster_ref=f"p:{participant.id}",
            )
        )

    enemy_name_totals = {}
    for enemy in enemies:
        group_key = str(enemy.get("template_key") or enemy.get("key") or enemy.get("id") or "").strip().lower()
        enemy_name_totals[group_key] = enemy_name_totals.get(group_key, 0) + 1

    enemy_name_seen = {}
    enemy_entries = []
    for enemy in enemies:
        status_chips = build_enemy_status_chips(enemy)
        atb_state = actor_atb_state(enemy=enemy)
        atb_status = atb_chip(atb_state, label_ready="Acting", ready_tone="danger")
        if atb_status:
            status_chips = [atb_status] + list(status_chips)
        lines = []
        active_action = dict((atb_state or {}).get("current_action") or {})
        if (atb_state or {}).get("phase") == "winding":
            lines.append(active_action.get("label", "Attack"))
        combat_state = []
        phase = (atb_state or {}).get("phase")
        if phase == "winding":
            combat_state.append("telegraph")
        elif phase in {"ready", "resolving"}:
            combat_state.append("ready")
        if selected_target_kind == "enemy" and selected_target_id == enemy.get("id"):
            status_chips = list(status_chips) + [_chip("Targeted", "my_location", "danger")]
            combat_state.append("selected")
        group_key = str(enemy.get("template_key") or enemy.get("key") or enemy.get("id") or "").strip().lower()
        enemy_name_seen[group_key] = enemy_name_seen.get(group_key, 0) + 1
        display_name = str(enemy.get("key") or "Enemy")
        if enemy_name_totals.get(group_key, 0) > 1:
            suffix = enemy_name_seen[group_key]
            last_token = display_name.rsplit(" ", 1)[-1]
            if not last_token.isdigit():
                display_name = f"{display_name} {suffix}"
        enemy_entries.append(
            _entry(
                display_name,
                lines=lines,
                icon=_enemy_icon(enemy),
                background_icon=_enemy_icon(enemy),
                size_class=_combat_card_size_class(enemy, enemy=True),
                command=f"target {enemy['id']}",
                chips=status_chips,
                meters=[atb_meter(atb_state, enemy=True), hp_meter(enemy["hp"], enemy["max_hp"])],
                selected=bool(selected_target_kind == "enemy" and selected_target_id == enemy.get("id")),
                combat_state=combat_state,
                entry_ref=f"e:{enemy['id']}",
            )
        )

    tutorial_guidance = []
    guidance_eyebrow = None
    guidance_title = None
    try:
        from world.tutorial import get_tutorial_combat_focus
    except Exception:
        tutorial_focus = []
    else:
        tutorial_focus = get_tutorial_combat_focus(character, encounter)
    if tutorial_focus:
        guidance_eyebrow = "Combat Tutorial"
        guidance_title = "Training Focus"
        tutorial_guidance = [
            (
                f"{str(item.get('title', 'Training') or 'Training').strip()}: {str(item.get('text', '') or '').strip()}"
                if str(item.get("text", "") or "").strip()
                else str(item.get("title", "Training") or "Training").strip(),
                item.get("icon") or "school",
            )
            for item in tutorial_focus
        ]

    return {
        **_make_view(
            "Combat",
            encounter_title,
            eyebrow_icon="swords",
            title_icon="warning",
            subtitle=" • ".join(
                bit
                for bit in (
                    f"{ally_count} {ally_label}",
                    f"{companion_count} {companion_label}" if companion_count else "",
                    f"{foe_count} {foe_label}",
                )
                if bit
            ),
            actions=[
                build_combat_action_picker("Abilities", "bolt", combat_actions.get("abilities", []), "No usable combat abilities."),
                build_combat_action_picker("Items", "lunch_dining", combat_actions.get("items", []), "No combat consumables packed."),
                _action("Flee", "flee", "logout", tone="danger"),
            ],
            sections=[
                _section("Heroes", "groups", "entries", items=party_entries or [_entry("No active heroes.", icon="person_off")], variant="party", span="compact" if party_count >= 3 else None),
                _section("Enemies", "warning", "entries", items=enemy_entries or [_entry("No enemies remain.", icon="task_alt")], variant="targets"),
            ],
            reactive=_reactive_view(encounter.obj, scene="combat", danger="combat"),
        ),
        "variant": "combat",
        "guidance": tutorial_guidance,
        "guidance_eyebrow": guidance_eyebrow,
        "guidance_title": guidance_title,
        "combat_actions": combat_actions,
        "reaction_window": reaction_window,
        "party_count": party_count,
        "enemy_count": foe_count,
        "sticky": True,
    }
