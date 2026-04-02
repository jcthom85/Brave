"""Brave-specific player commands for the first slice."""

from evennia.commands.default.muxcommand import MuxCommand

from world.data.items import ITEM_TEMPLATES, get_item_category, get_item_use_profile
from world.party import get_present_party_members
from world.data.quests import QUESTS
from world.resonance import get_resource_label, get_stat_label
from world.screen_text import format_entry, wrap_text
from world.tutorial import TUTORIAL_STEPS, ensure_tutorial_state


def _normalize_token(value):
    """Normalize free-text tokens for fuzzy command matching."""

    return "".join(char for char in (value or "").lower() if char.isalnum())


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
        bonus_text = _format_context_bonus_summary(item.get("bonuses", {}), character)
        if bonus_text:
            details.append("Bonuses: " + bonus_text)
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
        details.append("Bonuses: " + bonus_text)

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


def _format_tutorial_screen_block(character):
    """Return structured tutorial journal lines for the current onboarding step."""

    state = ensure_tutorial_state(character)
    if state.get("status") != "active":
        return []

    step_key = state.get("step") or "first_steps"
    step = TUTORIAL_STEPS[step_key]
    flags = state["flags"]

    checks = []
    if step_key == "first_steps":
        checks = [
            f"[{'x' if flags.get('talked_tamsin') else ' '}] Speak with Sergeant Tamsin Vale.",
            f"[{'x' if flags.get('visited_quartermaster_shed') else ' '}] Head east to Quartermaster Shed.",
            f"[{'x' if flags.get('returned_to_wayfarers_yard') else ' '}] Return to Wayfarer's Yard.",
        ]
    elif step_key == "pack_before_walk":
        checks = [
            f"[{'x' if flags.get('talked_nella') else ' '}] Speak with Quartermaster Nella Cobb.",
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
            f"[{'x' if flags.get('won_vermin_fight') else ' '}] Win one fight in the Vermin Pens.",
        ]
    elif step_key == "through_the_gate":
        checks = [
            f"[{'x' if flags.get('talked_harl') else ' '}] Report to Captain Harl Rowan in the Training Yard.",
        ]

    optional_done = flags.get("read_family_post_sign") or flags.get("talked_peep")
    checks.append(f"[{'x' if optional_done else ' '}] Optional: Visit Family Post for party basics.")

    details = [step["summary"]]
    details.extend(checks)
    return format_entry(step["title"] + " [Tutorial]", details=details)


def _format_quest_screen_block(character, quest_key, tracked_key=None):
    """Return structured journal lines for one active or completed quest."""

    definition = QUESTS[quest_key]
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

        self.clear_scene()
        if view and self.get_web_session():
            self.send_browser_view(view)
            if panel and view.get("preserve_rail"):
                self.send_browser_panel(panel)
            self.send_other_sessions(text)
            return

        self.msg(text)

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
        """Return connected player characters in the current room."""

        if not character.location:
            return []

        characters = [
            obj
            for obj in character.location.contents
            if hasattr(obj, "ensure_brave_character") and getattr(obj, "is_connected", False)
        ]
        if not include_self:
            characters = [obj for obj in characters if obj != character]
        return characters

    def find_local_character(self, character, query, include_self=False):
        """Find a connected local player character by fuzzy name."""

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
