"""Brave-specific player commands for the first slice."""

import re

from evennia.commands.default.muxcommand import MuxCommand

from world.activities import (
    match_targetable_consumable_character,
    match_targetable_social_character,
    use_consumable_template,
)
from world.data.items import ITEM_TEMPLATES, get_item_category, get_item_use_profile, match_inventory_item
from world.content.registry import get_content_registry
from world.interactions import get_entity_emote_response
from world.party import get_present_party_members
from world.genders import get_brave_pronoun
from world.resonance import get_resource_label, get_stat_label
from world.screen_text import format_entry, wrap_text
from world.tutorial import TUTORIAL_STEPS, ensure_tutorial_state


def _normalize_token(value):
    """Normalize free-text tokens for fuzzy command matching."""

    return "".join(char for char in (value or "").lower() if char.isalnum())


_EVENNIA_MARKUP_RE = re.compile(r"\|[A-Za-z]")
_BODY_PART_EMOTE_RE = re.compile(r"^(?P<verb>[a-z]+)(?:\s+(?P<body>(?:my|their|his|her)\s+)?(?P<part>head|hands?|shoulders?|arms?|brow|brows|fists?))?$")


def _strip_evennia_markup(text):
    """Remove lightweight Evennia color markup for browser notices."""

    clean = str(text or "").replace("||", "|")
    return _EVENNIA_MARKUP_RE.sub("", clean)


def _third_person_verb(verb):
    """Return the simple third-person singular form of one verb."""

    verb = str(verb or "").strip().lower()
    if not verb:
        return ""
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    if verb.endswith(("s", "x", "z", "ch", "sh")):
        return verb + "es"
    return verb + "s"


def _base_form_verb(verb):
    """Return a best-effort base form for a simple third-person verb."""

    verb = str(verb or "").strip().lower()
    if not verb:
        return ""
    if verb.endswith("ies") and len(verb) > 3:
        return verb[:-3] + "y"
    if verb.endswith("es"):
        stem = verb[:-2]
        if stem.endswith(("s", "x", "z", "ch", "sh", "o")):
            return stem
    if verb.endswith("s") and len(verb) > 1:
        return verb[:-1]
    return verb


def _second_person_phrase(text):
    """Rewrite a room-style phrase so it reads naturally after `You`."""

    words = str(text or "").split()
    if not words:
        return ""
    words[0] = _base_form_verb(words[0])
    return " ".join(words)


def _format_social_emote(character, text):
    """Return self/room emote lines with gender-aware body-part phrasing."""

    raw = str(text or "").strip()
    if not raw:
        return None, None

    punctuation = raw[-1] if raw[-1] in ".!?" else "."
    base = raw.rstrip(".!?").strip()
    lowered = base.lower()
    pronoun = get_brave_pronoun(character, "possessive_adjective")

    gesture_map = {
        "nod": ("nods", "nod"),
        "smile": ("smiles", "smile"),
        "laugh": ("laughs", "laugh"),
        "wave": ("waves", "wave"),
        "shrug": (f"shrugs {pronoun} shoulders", "shrug"),
        "bow": ("bows", "bow"),
        "frown": ("frowns", "frown"),
        "grin": ("grins", "grin"),
        "kneel": ("kneels", "kneel"),
        "sigh": ("sighs", "sigh"),
        "shake head": (f"shakes {pronoun} head", "shake your head"),
        "shake my head": (f"shakes {pronoun} head", "shake your head"),
        "lower head": (f"lowers {pronoun} head", "lower your head"),
        "raise fist": (f"raises {pronoun} fist", "raise your fist"),
        "cross arms": (f"crosses {pronoun} arms", "cross your arms"),
        "fold arms": (f"folds {pronoun} arms", "fold your arms"),
        "rub hands": (f"rubs {pronoun} hands together", "rub your hands together"),
    }
    if lowered in gesture_map:
        room_text, self_text = gesture_map[lowered]
        return f"{character.key} {room_text}{punctuation}", f"You {self_text}{punctuation}"

    match = _BODY_PART_EMOTE_RE.match(lowered)
    if match and match.group("body") is None and match.group("part"):
        verb = match.group("verb")
        part = match.group("part")
        room_text = f"{_third_person_verb(verb)} {pronoun} {part}"
        self_text = f"{verb} your {part}"
        return f"{character.key} {room_text}{punctuation}", f"You {self_text}{punctuation}"

    words = base.split()
    if len(words) == 1:
        verb = words[0]
        room_text = _third_person_verb(verb)
        self_text = verb
    else:
        room_text = base
        self_text = _second_person_phrase(base)
    return f"{character.key} {room_text}{punctuation}", f"You {self_text}{punctuation}"


def _find_emote_target(character, text):
    """Return a nearby social actor or enemy explicitly mentioned in an emote, if any."""

    if not character or not character.location:
        return None

    lowered = str(text or "").lower()
    room_target = match_targetable_social_character(character, text, include_self=False)
    if isinstance(room_target, list):
        room_target = room_target[0] if room_target else None
    if room_target and room_target != character:
        return "room", room_target

    get_encounter = getattr(character, "get_active_encounter", None)
    encounter = get_encounter() if callable(get_encounter) else None
    if encounter and not encounter.is_participant(character):
        encounter = None
    if encounter:
        enemies = list(encounter.get_active_enemies())
        enemies.sort(key=lambda enemy: len(enemy.get("key", "") or ""), reverse=True)
        for enemy in enemies:
            name = str(enemy.get("key") or "").strip()
            if not name:
                continue
            if re.search(r"\b" + re.escape(name.lower()) + r"\b", lowered):
                return "enemy", enemy

    return None


def _target_perspective_emote(room_line, target_name):
    """Rewrite a room emote line so the named target sees `you`."""

    line = str(room_line or "").strip()
    name = str(target_name or "").strip()
    if not line or not name:
        return line

    rewritten = re.sub(r"\b" + re.escape(name) + r"\b", "you", line, count=1)
    return rewritten


def _format_context_bonus_summary(bonuses, context):
    """Return a compact bonus string using the current resonance labels."""

    if not bonuses:
        return ""

    parts = []
    for key, value in bonuses.items():
        label = get_stat_label(key, context)
        sign = "+" if value >= 0 else ""
        parts.append(f"{label} {sign}{value}")
    return ", ".join(parts)


PACK_KIND_ORDER = ("consumable", "ingredient", "loot", "equipment")
PACK_KIND_LABELS = {
    "consumable": "Consumables",
    "ingredient": "Ingredients",
    "loot": "Loot And Materials",
    "equipment": "Spare Gear",
}


def _stack_blocks(blocks):
    """Join preformatted blocks with one blank line between them."""

    lines = []
    for block in blocks:
        if not block:
            continue
        if lines:
            lines.append("")
        lines.extend(block)
    return lines


def _quest_definitions():
    return get_content_registry().quests.quests


def _format_restore_summary(restore, character):
    """Return a readable meal-restore summary."""

    parts = []
    for resource_key in ("hp", "mana", "stamina"):
        amount = restore.get(resource_key, 0)
        if amount:
            parts.append(f"{get_resource_label(resource_key, character)} +{amount}")
    return ", ".join(parts)


def _format_item_value_text(item, quantity):
    """Return a compact item-value line when applicable."""

    value = item.get("value", 0)
    if value <= 0:
        return ""
    if quantity > 1:
        return f"Value: {value} silver each ({value * quantity} total)"
    return f"Value: {value} silver"


def _format_equipment_totals(character):
    """Return total gear bonuses from currently equipped items."""

    totals = {}
    equipment = character.db.brave_equipment or {}
    for template_id in equipment.values():
        item = ITEM_TEMPLATES.get(template_id)
        if not item:
            continue
        for key, value in (item.get("bonuses") or {}).items():
            totals[key] = totals.get(key, 0) + value
    return totals


def _format_inventory_entry(character, template_id, quantity):
    """Return a formatted pack-entry block."""

    item = ITEM_TEMPLATES[template_id]
    title = item["name"] + (f" x{quantity}" if quantity > 1 else "")
    details = []

    value_text = _format_item_value_text(item, quantity)
    if value_text:
        details.append(value_text)

    if item.get("kind") == "equipment":
        slot = item.get("slot")
        if slot:
            details.append("Slot: " + slot.replace("_", " ").title())
        bonus_text = _format_context_bonus_summary(item.get("bonuses", {}), character)
        if bonus_text:
            details.append(bonus_text)
        granted_ability = item.get("granted_ability")
        if granted_ability:
            ability_label = item.get("granted_ability_name", granted_ability)
            cooldown_turns = int(item.get("cooldown_turns", 0) or 0)
            if cooldown_turns > 0:
                details.append(f"{ability_label} · {cooldown_turns}-turn cooldown")
            else:
                details.append(ability_label)
    elif get_item_category(item) == "consumable":
        use = get_item_use_profile(item) or {}
        restore_text = _format_restore_summary(use.get("restore", {}), character)
        if restore_text:
            details.append("Restore: " + restore_text)
        buff_text = _format_context_bonus_summary(use.get("buffs", {}), character)
        if buff_text:
            details.append("Buff: " + buff_text)
        damage = dict(use.get("damage", {}))
        if damage.get("base"):
            low = int(damage.get("base", 0) or 0)
            high = low + max(0, int(damage.get("variance", 0) or 0))
            details.append(f"Damage: {low}-{high}" if high > low else f"Damage: {low}")
        contexts = [str(entry).title() for entry in (use.get("contexts") or [])]
        if contexts:
            details.append("Use: " + ", ".join(contexts))

    return format_entry(title, details=details, summary=item.get("summary"))


def _format_equipped_item_entry(character, slot, template_id):
    """Return a formatted equipment-slot block."""

    label = slot.replace("_", " ").title()
    if not template_id:
        return format_entry(f"{label}: Empty")

    item = ITEM_TEMPLATES.get(template_id)
    if not item:
        return format_entry(f"{label}: {template_id}")

    details = []
    bonus_text = _format_context_bonus_summary(item.get("bonuses", {}), character)
    if bonus_text:
        details.append(bonus_text)
    granted_ability = item.get("granted_ability")
    if granted_ability:
        ability_label = item.get("granted_ability_name", granted_ability)
        cooldown_turns = int(item.get("cooldown_turns", 0) or 0)
        if cooldown_turns > 0:
            details.append(f"{ability_label} · {cooldown_turns}-turn cooldown")
        else:
            details.append(ability_label)

    return format_entry(f"{label}: {item['name']}", details=details, summary=item.get("summary"))


def _format_quest_reward_text(definition):
    """Return a compact reward summary for a quest definition."""

    rewards = definition.get("rewards", {})
    parts = []
    if rewards.get("xp"):
        parts.append(f"{rewards['xp']} XP")
    if rewards.get("silver"):
        parts.append(f"{rewards['silver']} silver")
    for item_reward in rewards.get("items", []):
        template_id = item_reward.get("item")
        if not template_id:
            continue
        item_name = ITEM_TEMPLATES.get(template_id, {}).get("name", template_id)
        quantity = item_reward.get("quantity", 1)
        parts.append(item_name + (f" x{quantity}" if quantity > 1 else ""))
    return ", ".join(parts)


def _format_tutorial_screen_block(character, completed_only=False):
    """Return structured tutorial journal lines for current or completed onboarding steps."""

    state = ensure_tutorial_state(character)
    status = state.get("status")
    if status == "inactive":
        return []

    flags = state.get("flags", {})
    current_step_key = state.get("step")
    current_order = TUTORIAL_STEPS[current_step_key]["order"] if current_step_key else 999
    
    if completed_only:
        blocks = []
        for step_key, step in TUTORIAL_STEPS.items():
            if status == "completed" or (step["order"] < current_order):
                blocks.append(format_entry(step["title"] + " [Tutorial Completed]", details=[step["summary"]]))
        return blocks

    if status == "completed":
        return [] # Entire tutorial is done, individual steps handled by completed_only=True path

    step_key = current_step_key or "first_steps"
    step = TUTORIAL_STEPS[step_key]

    checks = []
    if step_key == "first_steps":
        checks = [
            f"[{'x' if flags.get('talked_tamsin') else ' '}] Consult with Sergeant Tamsin Vale.",
            f"[{'x' if flags.get('visited_quartermaster_shed') else ' '}] Check the Quartermaster Shed east of the yard.",
            f"[{'x' if flags.get('returned_to_wayfarers_yard') else ' '}] Return before the yard moves on.",
        ]
    elif step_key == "pack_before_walk":
        checks = [
            f"[{'x' if flags.get('talked_nella') else ' '}] Let Quartermaster Nella check your kit.",
            f"[{'x' if flags.get('viewed_gear') else ' '}] Check your gear.",
            f"[{'x' if flags.get('viewed_pack') else ' '}] Open your pack.",
            f"[{'x' if flags.get('read_supply_board') else ' '}] Read the supply board.",
        ]
    elif step_key == "stand_your_ground":
        checks = [
            f"[{'x' if flags.get('talked_brask') else ' '}] Speak with Ringhand Brask in the Sparring Ring.",
        ]
    elif step_key == "clear_the_pens":
        checks = [
            f"[{'x' if flags.get('used_class_ability') else ' '}] Use your class skill in combat.",
            f"[{'x' if flags.get('won_vermin_fight') else ' '}] Win one fight in the Vermin Pens.",
        ]
    elif step_key == "catch_your_breath":
        checks = [
            f"[{'x' if flags.get('rested_after_fight') else ' '}] Rest in Wayfarer's Yard.",
        ]
    elif step_key == "through_the_gate":
        checks = [
            f"[{'x' if flags.get('talked_harl') else ' '}] Report to Captain Harl Rowan in the Training Yard.",
        ]

    optional_done = flags.get("read_family_post_sign") or flags.get("talked_peep") or flags.get("visited_family_post")
    checks.append(f"[{'x' if optional_done else ' '}] Optional: Visit Family Post for party basics.")

    details = [step["summary"]]
    details.extend(checks)
    return format_entry(step["title"] + " [Tutorial]", details=details)


def _format_quest_screen_block(character, quest_key, tracked_key=None):
    """Return structured journal lines for one active or completed quest."""

    definition = _quest_definitions()[quest_key]
    state = (character.db.brave_quests or {}).get(quest_key)
    if not state or state.get("status") == "locked":
        return []

    status = state.get("status", "active").replace("_", " ").title()
    details = [definition["summary"], f"Given by: {definition['giver']}"]

    for objective in state.get("objectives", []):
        progress_suffix = ""
        if objective.get("required", 1) > 1:
            progress_suffix = f" ({objective.get('progress', 0)}/{objective.get('required', 1)})"
        marker = "x" if objective.get("completed") else " "
        details.append(f"[{marker}] {objective.get('description', 'Objective')}{progress_suffix}")

    reward_text = _format_quest_reward_text(definition)
    if reward_text:
        details.append("Rewards: " + reward_text)

    title = f"{definition['title']} [{status}]"
    if quest_key == tracked_key:
        title += " [Tracked]"
    return format_entry(title, details=details)


def _wrap_paragraphs(text, indent="  "):
    """Wrap multiline room-facing text while preserving paragraph breaks."""

    lines = []
    for raw_line in str(text or "").splitlines():
        if not raw_line.strip():
            if lines and lines[-1] != "":
                lines.append("")
            continue
        lines.extend(wrap_text(raw_line.strip(), indent=indent))
    while lines and lines[-1] == "":
        lines.pop()
    return lines


class BraveCharacterCommand(MuxCommand):
    """Shared helpers for Brave commands."""

    WEB_PROTOCOLS = {"websocket", "ajax/comet", "webclient"}

    def get_web_session(self):
        """Return the current session if it is a web client session."""

        session = getattr(self, "session", None)
        protocol = (getattr(session, "protocol_key", "") or "").lower() if session else ""
        return session if session and protocol in self.WEB_PROTOCOLS else None

    def send_browser_panel(self, panel):
        """Send browser-only companion panel data for the current session."""

        session = self.get_web_session()
        if panel and session:
            self.msg(brave_panel=panel, session=session)

    def send_browser_view(self, view):
        """Send a browser-only main-pane view payload for the current session."""

        session = self.get_web_session()
        if view and session:
            self.msg(brave_view=view, session=session)

    def send_browser_notice(self, title, *, lines=None, tone="muted", icon=None, duration_ms=None, sticky=False):
        """Send a browser-only popup notice for the current session."""

        session = self.get_web_session()
        notice_lines = [str(line) for line in (lines or []) if str(line or "").strip()]
        if not session or (not title and not notice_lines):
            return False

        payload = {
            "title": title or "Notice",
            "tone": tone or "muted",
            "lines": notice_lines,
        }
        if icon:
            payload["icon"] = icon
        if duration_ms is not None:
            payload["duration_ms"] = max(0, int(duration_ms))
        if sticky:
            payload["sticky"] = True
        self.msg(brave_notice=payload, session=session)
        return True

    def send_other_sessions(self, text):
        """Send fallback text to any other connected sessions on the same puppet."""

        caller = getattr(self, "caller", None)
        current = getattr(self, "session", None)
        sessions = getattr(caller, "sessions", None)
        if not caller or not sessions or not current:
            return

        if hasattr(sessions, "get"):
            available = list(sessions.get())
        elif hasattr(sessions, "all"):
            available = list(sessions.all())
        else:
            available = []

        others = [session for session in available if session != current]
        if others:
            self.msg(text, session=others)

    def clear_scene(self):
        """Clear the webclient scene pane for full-screen Brave views."""

        session = self.get_web_session()
        if session:
            self.msg(brave_clear={}, session=session)

    def scene_msg(self, text, panel=None, view=None):
        """Replace the current scene with a new full-screen output block."""

        if view and self.get_web_session():
            self.send_browser_view(view)
            if panel and view.get("preserve_rail"):
                self.send_browser_panel(panel)
            self.send_other_sessions(text)
            return

        self.clear_scene()
        self.msg(text)

    def deliver_browser_notice(self, message, *, title=None, tone="muted", icon=None, duration_ms=None, sticky=False):
        """Show a browser popup on the active web session and text elsewhere."""

        plain_message = _strip_evennia_markup(message)
        if self.send_browser_notice(
            title or "Notice",
            lines=[plain_message],
            tone=tone,
            icon=icon,
            duration_ms=duration_ms,
            sticky=sticky,
        ):
            self.send_other_sessions(message)
            return True
        return False

    def deliver_consumable_notice(self, ok, message, result=None):
        """Show explore-time consumable feedback as a browser popup when possible."""

        item = result.get("item") if result else None
        title = item.get("name") if item else ("Can't Use Item" if not ok else "Item Used")
        tone = "good" if ok else "danger"
        icon = "check_circle" if ok else "error"
        duration_ms = 4200 if ok else 5600
        return self.deliver_browser_notice(
            message,
            title=title,
            tone=tone,
            icon=icon,
            duration_ms=duration_ms,
        )

    def send_room_emote(self, message):
        """Broadcast a short social emote in the current room."""

        character = self.get_character()
        if not character or not character.location:
            return False

        text = str(message or "").strip()
        if not text:
            self.msg("Usage: emote <message>")
            return False

        room_line, self_line = _format_social_emote(character, text)
        if not room_line or not self_line:
            self.msg("Usage: emote <message>")
            return False

        from world.browser_panels import broadcast_room_activity, send_room_activity_event

        target_info = _find_emote_target(character, text)
        excluded = [character]
        if target_info:
            target_kind, target = target_info
            if target_kind == "room":
                target_line = _target_perspective_emote(room_line, target.key)
                send_room_activity_event(target, target_line, cls="out", category="emote")
                excluded.append(target)
            elif target_kind == "enemy":
                encounter = None
                get_active_encounter = getattr(character, "get_active_encounter", None)
                if callable(get_active_encounter):
                    encounter = get_active_encounter()
                if not encounter:
                    from typeclasses.scripts import BraveEncounter

                    encounter = BraveEncounter.get_for_room(character.location)
                if encounter and encounter.is_participant(character):
                    reaction = encounter.react_to_emote(character, target, text)
                    if reaction:
                        broadcast_room_activity(character.location, reaction, exclude=excluded, cls="out")
        broadcast_room_activity(character.location, room_line, exclude=excluded, cls="out")
        if target_info and target_info[0] == "room":
            response = get_entity_emote_response(character, target_info[1], text)
            if response:
                broadcast_room_activity(character.location, response, exclude=[character], cls="out", category="emote")
        self.msg(self_line)
        return True

    def get_character(self):
        caller = self.caller
        if not hasattr(caller, "ensure_brave_character"):
            self.msg("That command is only available while controlling a Brave character.")
            return None
        caller.ensure_brave_character()
        return caller

    def get_encounter(self, character, require=False):
        from typeclasses.scripts import BraveEncounter

        encounter = BraveEncounter.get_for_room(character.location) if character.location else None
        if require and (not encounter or not encounter.is_participant(character)):
            self.msg("You are not currently in a fight.")
            return None
        return encounter

    def get_present_party_size(self, character):
        """Return the connected present party size for encounter scaling."""

        expected_party_size = 1
        if getattr(character.db, "brave_party_id", None):
            expected_party_size = max(
                1,
                sum(
                    1
                    for member in get_present_party_members(character)
                    if getattr(member, "is_connected", False)
                ),
            )
        return expected_party_size

    def get_local_entities(self, character, kind=None):
        """Return Brave world entities in the current room."""

        if not character.location:
            return []

        entities = [
            obj for obj in character.location.contents if getattr(obj.db, "brave_entity_id", None)
        ]
        if kind:
            entities = [
                obj
                for obj in entities
                if getattr(obj.db, "brave_entity_kind", None) == kind
            ]
        return entities

    def find_local_entity(self, character, query, kind=None):
        """Find a local Brave entity by name or alias."""

        entities = self.get_local_entities(character, kind=kind)
        if not query:
            return None, entities

        query_norm = _normalize_token(query)
        matches = []
        for entity in entities:
            names = [entity.key]
            names.extend(alias for alias in entity.aliases.all())
            tokens = [_normalize_token(name) for name in names]
            if any(query_norm == token for token in tokens):
                matches.append(entity)
        if matches:
            return matches[0] if len(matches) == 1 else matches, entities

        for entity in entities:
            names = [entity.key]
            names.extend(alias for alias in entity.aliases.all())
            tokens = [_normalize_token(name) for name in names]
            if any(query_norm in token for token in tokens):
                matches.append(entity)

        if not matches:
            return None, entities
        return matches[0] if len(matches) == 1 else matches, entities

    def get_local_characters(self, character, include_self=False):
        """Return local player characters in the current room."""

        if not character.location:
            return []

        characters = [
            obj
            for obj in character.location.contents
            if hasattr(obj, "ensure_brave_character")
            and (
                getattr(obj, "is_connected", False)
                or bool(getattr(getattr(obj, "db", None), "brave_test_fixture", False))
            )
        ]
        if not include_self:
            characters = [obj for obj in characters if obj != character]
        return characters

    def find_local_character(self, character, query, include_self=False):
        """Find a local player character by fuzzy name."""

        characters = self.get_local_characters(character, include_self=include_self)
        if not query:
            return None, characters

        query_norm = _normalize_token(query)
        matches = []
        for candidate in characters:
            if query_norm == _normalize_token(candidate.key):
                matches.append(candidate)
        if matches:
            return matches[0] if len(matches) == 1 else matches, characters

        for candidate in characters:
            if query_norm in _normalize_token(candidate.key):
                matches.append(candidate)

        if not matches:
            return None, characters
        return matches[0] if len(matches) == 1 else matches, characters

    def find_inventory_item(self, character, query, require_value=False):
        """Find an inventory template by fuzzy item name."""

        entries = []
        for entry in character.db.brave_inventory or []:
            template_id = entry.get("template")
            item = ITEM_TEMPLATES.get(template_id)
            if not item:
                continue
            if require_value and item.get("value", 0) <= 0:
                continue
            entries.append((template_id, item))

        if not query:
            return None, entries

        query_norm = _normalize_token(query)
        matches = []
        for template_id, item in entries:
            names = [item["name"], template_id.replace("_", " ")]
            if any(query_norm == _normalize_token(name) for name in names):
                matches.append((template_id, item))
        if matches:
            return matches[0] if len(matches) == 1 else matches, entries

        for template_id, item in entries:
            names = [item["name"], template_id.replace("_", " ")]
            if any(query_norm in _normalize_token(name) for name in names):
                matches.append((template_id, item))

        if not matches:
            return None, entries
        return matches[0] if len(matches) == 1 else matches, entries

    def use_explore_consumable(self, character, item_query, target_query=None, *, verb=None):
        """Use an exploration consumable, optionally targeting someone nearby."""

        match = match_inventory_item(character, item_query, category="consumable", verb=verb)
        if isinstance(match, list):
            names = ", ".join(ITEM_TEMPLATES[key]["name"] for key in match)
            return False, f"Be more specific. That could mean: {names}", None
        if not match:
            return False, "You do not have a usable consumable matching that.", None

        item = ITEM_TEMPLATES.get(match, {})
        use = get_item_use_profile(item, context="explore")
        if not use:
            any_use = get_item_use_profile(item) or {}
            contexts = tuple(any_use.get("contexts") or ())
            if "combat" in contexts and "explore" not in contexts:
                return False, f"{item.get('name', 'That item')} can only be used in combat.", None
            return False, "That item can't be used that way right now.", None

        target_type = use.get("target", "self")
        target = None
        if target_type == "enemy":
            return False, f"{item.get('name', 'That item')} can only be used in combat.", None
        if target_type == "ally":
            if target_query:
                target = match_targetable_consumable_character(character, target_query, include_self=True)
                if isinstance(target, list):
                    names = ", ".join(candidate.key for candidate in target)
                    return False, f"Be more specific. That could mean: {names}", None
                if not target:
                    return False, "No one here matches that target.", None
            else:
                target = character
        elif target_type == "self":
            if target_query:
                target = match_targetable_consumable_character(character, target_query, include_self=True)
                if isinstance(target, list):
                    names = ", ".join(candidate.key for candidate in target)
                    return False, f"Be more specific. That could mean: {names}", None
                if not target:
                    return False, "No one here matches that target.", None
                if target != character:
                    return False, f"{item.get('name', 'That item')} can only be used on yourself.", None
            else:
                target = character
        elif target_query:
            return False, "That item does not need a target.", None

        return use_consumable_template(
            character,
            match,
            context="explore",
            verb=verb,
            target=target,
        )


class CmdFinishPlaySilent(BraveCharacterCommand):
    """
    Silent placeholder for the 'finish play' command which is sent by the
    webclient during character creation.
    """

    key = "finish play"
    aliases = ["play now", "enter world"]
    locks = "cmd:all()"
    priority = -10

    def func(self):
        pass
