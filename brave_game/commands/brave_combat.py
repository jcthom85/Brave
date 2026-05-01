"""Combat commands extracted from Brave's main command module."""

from types import SimpleNamespace

from world.browser_views import build_combat_view
from world.browser_panels import build_combat_panel
from world.party import get_present_party_members
from world.content import get_content_registry
from world.tutorial import is_tutorial_solo_combat_room, record_command_event

from .brave import BraveCharacterCommand

CONTENT = get_content_registry()
ABILITY_LIBRARY = CONTENT.characters.ability_library
ITEM_TEMPLATES = CONTENT.items.item_templates


def _refresh_combat_scene(command, encounter, character):
    """Refresh combat for text sessions without double-pushing browser views."""

    snapshot = encounter.format_combat_snapshot()
    if command.get_web_session():
        command.send_other_sessions(snapshot)
        return
    command.msg(snapshot)


class _PreviewCharacter:
    """Lightweight combat-view participant used by the layout preview command."""

    def __init__(self, char_id, key, room, class_key, resources, derived, abilities, inventory=None):
        self.id = char_id
        self.key = key
        self.location = room
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_resources=dict(resources or {}),
            brave_derived_stats=dict(derived or {}),
            brave_inventory=list(inventory or []),
        )
        self._abilities = list(abilities or [])

    def ensure_brave_character(self):
        return self

    def get_unlocked_abilities(self):
        return list(self._abilities)


class _PreviewEncounter:
    """Synthetic encounter payload for fast browser combat-layout previews."""

    def __init__(self, room, participants, enemies, *, states=None, atb_states=None, title="Combat Layout Preview"):
        self.obj = room
        self.db = SimpleNamespace(round=2, encounter_title=title, pending_actions={})
        self._participants = list(participants)
        self._enemies = list(enemies)
        self._states = dict(states or {})
        self._atb_states = dict(atb_states or {})
        self.interval = 1

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return list(self._participants)

    def _get_participant_state(self, character):
        actor_id = character["id"] if isinstance(character, dict) else character.id
        return self._states.get(
            actor_id,
            {
                "guard": 0,
                "bleed_turns": 0,
                "poison_turns": 0,
                "curse_turns": 0,
                "snare_turns": 0,
                "feint_turns": 0,
            },
        )

    def _get_actor_atb_state(self, character=None, enemy=None, companion=None):
        if companion is not None:
            return self._atb_states.get(f"c:{companion['id']}", {"phase": "charging", "gauge": 55, "ready_gauge": 100})
        if character is not None:
            return self._atb_states.get(f"p:{character.id}", {"phase": "charging", "gauge": 42, "ready_gauge": 100})
        if enemy is not None:
            return self._atb_states.get(f"e:{enemy['id']}", {"phase": "charging", "gauge": 68, "ready_gauge": 100})
        return {"phase": "charging", "gauge": 0, "ready_gauge": 100}


def _preview_ability_names(class_key):
    """Return a small set of live ability display names for one class."""

    desired = {
        "warrior": ("Strike", "Defend"),
        "mage": ("Firebolt", "Frostbind"),
        "rogue": ("Feint", "Cheap Shot"),
        "paladin": ("Smite", "Guarding Aura"),
        "ranger": ("Quick Shot", "Mark Prey"),
        "cleric": ("Heal", "Cleanse"),
        "druid": ("Entangling Roots", "Living Current"),
    }.get(class_key, ("Strike",))
    names = []
    for name in desired:
        if any(str(ability.get("name") or "") == name for ability in ABILITY_LIBRARY.values()):
            names.append(name)
    return names or ["Strike"]


def _preview_inventory():
    """Return one lightweight combat-usable preview inventory."""

    options = ("field_bandage", "sunrise_tonic", "throwing_knife")
    inventory = []
    for template_id in options:
        if template_id in ITEM_TEMPLATES:
            inventory.append({"template": template_id, "quantity": 2})
    return inventory


def _build_preview_encounter(character, ally_count, enemy_count, pet_count):
    """Build a synthetic encounter object for browser combat previews."""

    room = character.location
    ally_count = max(1, min(4, int(ally_count)))
    enemy_count = max(1, min(4, int(enemy_count)))
    pet_count = max(0, min(ally_count, int(pet_count)))

    ally_specs = [
        ("warrior", "Dad", {"hp": 24, "mana": 0, "stamina": 12}, {"max_hp": 28, "max_mana": 0, "max_stamina": 14}),
        ("mage", "Peep", {"hp": 17, "mana": 16, "stamina": 8}, {"max_hp": 20, "max_mana": 18, "max_stamina": 10}),
        ("rogue", "Mara", {"hp": 19, "mana": 4, "stamina": 11}, {"max_hp": 22, "max_mana": 6, "max_stamina": 12}),
        ("paladin", "Rook", {"hp": 23, "mana": 9, "stamina": 10}, {"max_hp": 28, "max_mana": 12, "max_stamina": 13}),
    ]

    participants = []
    atb_states = {}

    lead = _PreviewCharacter(
        character.id,
        character.key,
        room,
        getattr(character.db, "brave_class", "warrior"),
        character.db.brave_resources or {},
        character.db.brave_derived_stats or {},
        list(getattr(character, "get_unlocked_abilities", lambda: [])() or _preview_ability_names(getattr(character.db, "brave_class", "warrior"))),
        inventory=getattr(character.db, "brave_inventory", None) or _preview_inventory(),
    )
    participants.append(lead)
    atb_states[f"p:{lead.id}"] = {"phase": "ready", "gauge": 100, "ready_gauge": 100}

    next_id = 8000
    for class_key, key, resources, derived in ally_specs:
        if len(participants) >= ally_count:
            break
        while next_id == character.id:
            next_id += 1
        fake = _PreviewCharacter(
            next_id,
            key,
            room,
            class_key,
            resources,
            derived,
            _preview_ability_names(class_key),
            inventory=_preview_inventory(),
        )
        participants.append(fake)
        atb_states[f"p:{fake.id}"] = {"phase": "charging", "gauge": 28 + (len(participants) * 11), "ready_gauge": 100}
        next_id += 1

    for index in range(pet_count):
        owner = participants[index]
        companion_id = f"pc{index + 1}"
        companion_name = ("Marsh Hound", "Ash Hawk", "Briar Boar", "Marsh Hound")[index % 4]
        companion_key = ("marsh_hound", "ash_hawk", "briar_boar", "marsh_hound")[index % 4]
        participants.append(
            {
                "kind": "companion",
                "id": companion_id,
                "owner_id": owner.id,
                "key": companion_name,
                "icon": "pets",
                "companion_key": companion_key,
                "max_hp": 14 + index,
                "hp": 11 + index,
            }
        )
        atb_states[f"c:{companion_id}"] = {"phase": "charging", "gauge": 49 + (index * 8), "ready_gauge": 100}

    enemy_templates = [
        ("road_wolf", "Road Wolf", "wolf-head"),
        ("bog_creeper", "Bog Creeper", "poison-cloud"),
        ("tower_archer", "Tower Archer", "archer"),
        ("bandit_raider", "Bandit Raider", "crossed-swords"),
    ]
    enemies = []
    for index in range(enemy_count):
        template_key, key, icon = enemy_templates[index % len(enemy_templates)]
        enemy_id = f"e{index + 1}"
        name = key if enemy_count == 1 else f"{key} {index + 1}"
        enemies.append(
            {
                "id": enemy_id,
                "template_key": template_key,
                "key": name,
                "icon": icon,
                "hp": 12 + (index * 3),
                "max_hp": 18 + (index * 4),
            }
        )
        atb_states[f"e:{enemy_id}"] = {"phase": "charging", "gauge": 38 + (index * 13), "ready_gauge": 100}

    return _PreviewEncounter(
        room,
        participants,
        enemies,
        atb_states=atb_states,
        title=f"Combat Layout Preview · {ally_count}v{enemy_count}",
    )


class CmdCombatPreview(BraveCharacterCommand):
    """
    Preview combat layout states without a real fight.

    Usage:
      combatpreview
      combatpreview <allies>
      combatpreview <allies> <enemies>
      combatpreview <allies> <enemies> <pets>

    Opens a synthetic combat screen in the browser so you can inspect
    1-4 ally layouts and optional ranger-style pet sidecars.
    """

    key = "combatpreview"
    aliases = ["combattest", "combatlayout"]
    locks = "cmd:perm(Builder)"
    help_category = "Brave"

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not character.location:
            self.msg("You need to be in a room first.")
            return

        parts = [part for part in (self.args or "").split() if part]
        try:
            ally_count = int(parts[0]) if len(parts) >= 1 else 4
            enemy_count = int(parts[1]) if len(parts) >= 2 else ally_count
            pet_count = int(parts[2]) if len(parts) >= 3 else 0
        except ValueError:
            self.msg("Usage: combatpreview [allies 1-4] [enemies 1-4] [pets 0-4]")
            return

        encounter = _build_preview_encounter(character, ally_count, enemy_count, pet_count)
        view = build_combat_view(encounter, encounter.get_active_participants()[0])
        view["chips"] = list(view.get("chips", [])) + [{"label": "Preview", "icon": "visibility", "tone": "muted"}]
        self.scene_msg(
            "Combat layout preview.",
            panel=build_combat_panel(encounter),
            view=view,
        )


class CmdFight(BraveCharacterCommand):
    """
    Engage the threats in your current area.

    Usage:
      fight
      fight <threat>

    Starts or joins the current room encounter. If multiple hostile parties are
    present, specify which one to engage.
    """

    key = "fight"
    aliases = ["engage"]
    help_category = "Brave"

    def func(self):
        from typeclasses.scripts import BraveEncounter

        character = self.get_character()
        if not character:
            return
        if not character.location:
            self.msg("You have no location to fight in.")
            return
        if character.location.db.brave_safe:
            self.msg("This is a safe place. No immediate fight is pressing in here.")
            return

        threat_query = self.args.strip() or None
        if not BraveEncounter.get_for_room(character.location):
            preview = BraveEncounter.resolve_room_threat_preview(character.location, threat_query)
            if isinstance(preview, list):
                self.msg("Be more specific. That could mean: " + ", ".join(str(option.get("display_name") or option.get("party_name") or "threat") for option in preview))
                return
            if not preview:
                self.msg("Nothing stirs here right now.")
                return
            from world.boss_gates import find_gate_for_preview, start_gate_ready_check

            gate_key, gate = find_gate_for_preview(character.location, preview)
            if gate:
                ok, message = start_gate_ready_check(character, gate_key)
                if ok and self.get_web_session():
                    self.send_other_sessions(message)
                elif ok:
                    self.msg(message)
                else:
                    self.msg(message)
                return

        solo_tutorial = is_tutorial_solo_combat_room(character.location)
        encounter, created = BraveEncounter.start_for_room(
            character.location,
            expected_party_size=1 if solo_tutorial else self.get_present_party_size(character),
            threat_query=threat_query,
        )
        if not encounter:
            self.msg("Nothing stirs here right now.")
            return

        if created:
            encounter.add_participant(character)
            if character.db.brave_party_id and not solo_tutorial:
                for other in get_present_party_members(character):
                    if other != character and getattr(other, "is_connected", False):
                        encounter.add_participant(other)
            try:
                from world.browser_panels import send_audio_cue_once

                room_id = str(getattr(character.location.db, "brave_room_id", "") or "")
                if room_id == "brambleford_rat_and_kettle_cellar":
                    send_audio_cue_once(character, "sfx.story.cellar_threat", key="combat_cellar_threat", force=True)
                elif room_id.startswith("goblin_road_") and room_id != "goblin_road_fencebreaker_camp":
                    send_audio_cue_once(character, "sfx.story.road_danger", key="combat_goblin_road_danger", force=True)
            except Exception:
                pass
        else:
            ok, error = encounter.add_participant(character)
            if not ok:
                self.msg(error)
                return

        self.scene_msg(
            encounter.format_combat_snapshot(),
            panel=build_combat_panel(encounter),
            view=build_combat_view(encounter, character),
        )


class CmdBossGate(BraveCharacterCommand):
    """
    Stage or join a room-roster boss gate run.

    Usage:
      bossgate new <gate>
      bossgate join <run_id>
      bossgate leave <run_id>
      bossgate remove <run_id> <character_id>
      bossgate start <run_id>
      bossgate cancel <run_id>
    """

    key = "bossgate"
    aliases = ["boss"]
    help_category = "Brave"

    def func(self):
        from world.boss_gates import (
            cancel_gate,
            create_gate_run,
            join_gate_run,
            leave_gate_run,
            launch_gate_run,
            remove_gate_run_member,
            send_gate_choice_payload,
            send_gate_run_payload,
        )

        character = self.get_character()
        if not character or not character.location:
            return

        parts = [part for part in (self.args or "").split() if part]
        action = parts[0].lower() if parts else ""
        if action in {"choose", "runs"}:
            if len(parts) < 2:
                self.msg("No boss gate selected.")
                return
            send_gate_choice_payload(character, parts[1])
            return
        if action == "new":
            if len(parts) < 2:
                self.msg("No boss gate selected.")
                return
            ok, result = create_gate_run(character, parts[1])
            if not ok:
                self.msg(result)
            return
        if action in {"join", "ready", "assist"}:
            if len(parts) < 2:
                self.msg("No boss run selected.")
                return
            ok, message = join_gate_run(character, parts[1])
            if not ok:
                self.msg(message)
            return
        if action == "leave":
            if len(parts) < 2:
                self.msg("No boss run selected.")
                return
            ok, message = leave_gate_run(character, parts[1])
            if not ok:
                self.msg(message)
            return
        if action == "remove":
            if len(parts) < 3:
                self.msg("No boss run member selected.")
                return
            ok, message = remove_gate_run_member(character, parts[1], parts[2])
            if not ok:
                self.msg(message)
            return
        if action in {"start", "launch", "begin"}:
            run_id = parts[1] if len(parts) >= 2 else None
            ok, result = launch_gate_run(character, run_id)
            if not ok:
                self.msg(result)
                return
            encounter = result
            self.scene_msg(
                encounter.format_combat_snapshot(),
                panel=build_combat_panel(encounter),
                view=build_combat_view(encounter, character),
            )
            return
        if action in {"cancel", "stop"}:
            run_id = parts[1] if len(parts) >= 2 else None
            ok, message = cancel_gate(character, run_id)
            if not ok:
                self.msg(message)
            return
        if action == "show" and len(parts) >= 2:
            send_gate_run_payload(character, parts[1])
            return
        self.msg("No boss run selected.")


class CmdEnemies(BraveCharacterCommand):
    """
    View current enemies or likely local threats.

    Usage:
      enemies

    Shows the current combatants if a fight is active, or previews likely dangers in a hostile room.
    """

    key = "enemies"
    aliases = ["foes", "threats"]
    help_category = "Brave"

    def func(self):
        from typeclasses.scripts import BraveEncounter

        character = self.get_character()
        if not character:
            return
        encounter = self.get_encounter(character)
        if encounter and encounter.is_participant(character):
            self.scene_msg(
                encounter.format_combat_snapshot(),
                panel=build_combat_panel(encounter),
                view=build_combat_view(encounter, character),
            )
            return

        threats = BraveEncounter.get_visible_room_threats(character.location, character)
        if not threats:
            self.msg("No immediate enemies are pressing in here.")
            return

        lines = []
        for threat in threats:
            detail = threat.get("detail")
            summary = f"{threat['key']}: {threat['threat_label'].lower()} threat"
            if detail:
                summary += f" · {detail}"
            lines.append(summary)
        self.msg("Threats here:\n  " + "\n  ".join(lines) + "\nUse |wfight|n to start or join the current fight.")


class CmdTarget(BraveCharacterCommand):
    """
    Queue a basic attack target in combat.

    Usage:
      target
      target <enemy>

    Readies a basic attack against the nearest enemy or a chosen target. The
    legacy `attack` alias is accepted for old clients and typed commands, but
    `fight` is the only command that starts or joins an encounter.
    """

    key = "target"
    aliases = ["attack"]
    help_category = "Brave"

    def _refresh_combat_scene(self, encounter, character):
        _refresh_combat_scene(self, encounter, character)

    def func(self):
        character = self.get_character()
        if not character:
            return

        encounter = self.get_encounter(character, require=False)
        if not encounter or not encounter.is_participant(character):
            self.msg("Use |wfight|n to start or join the fight first.")
            return

        ok, message = encounter.queue_attack(character, self.args.strip() or None)
        if not ok:
            self.msg(message)
            return

        self._refresh_combat_scene(encounter, character)
        self.msg(message)


class CmdUse(BraveCharacterCommand):
    """
    Use a class ability or consumable.

    Usage:
      use <ability or consumable>
      use <ability or consumable> = <target>

    In combat, queues one of the currently implemented unlocked combat abilities or
    a carried combat consumable for the next round. Outside combat, uses a carried
    exploration consumable immediately.
    """

    key = "use"
    aliases = ["cast"]
    help_category = "Brave"

    def _refresh_combat_scene(self, encounter, character):
        _refresh_combat_scene(self, encounter, character)

    def func(self):
        character = self.get_character()
        if not character:
            return
        if not self.args:
            self.msg("Usage: use <ability> [= target]")
            return

        action_name = self.lhs if self.rhs is not None else self.args
        target_name = self.rhs.strip() if self.rhs else None
        action_name = action_name.strip()

        encounter = self.get_encounter(character, require=False)
        if not encounter or not encounter.is_participant(character):
            ok, message, result = self.use_explore_consumable(character, action_name, target_name)
            if self.deliver_consumable_notice(ok, message, result):
                return
            self.msg(message)
            return

        ok, message = encounter.queue_ability(character, action_name, target_name)
        ability_queued = ok
        if not ok:
            consumable_match = encounter.find_consumable(character, action_name, context="combat")
            if consumable_match:
                ok, message = encounter.queue_item(character, action_name, target_name)
        if not ok:
            self.msg(message)
            return

        if ability_queued:
            record_command_event(character, "class_ability")
        self._refresh_combat_scene(encounter, character)
        self.msg(message)


class CmdFlee(BraveCharacterCommand):
    """
    Queue a retreat from the current fight.

    Usage:
      flee

    Tries to fall back to the room you entered from on the next combat round.
    """

    key = "flee"
    aliases = ["retreat", "run"]
    help_category = "Brave"

    def _refresh_combat_scene(self, encounter, character):
        _refresh_combat_scene(self, encounter, character)

    def func(self):
        character = self.get_character()
        if not character:
            return

        encounter = self.get_encounter(character, require=True)
        if not encounter:
            return

        ok, message = encounter.queue_flee(character)
        if ok:
            self._refresh_combat_scene(encounter, character)
        self.msg(message)
