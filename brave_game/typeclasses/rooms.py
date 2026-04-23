"""
Room

Rooms are simple containers that has no location of their own.

"""

import textwrap

from evennia.objects.objects import DefaultRoom

from world.browser_views import build_room_view
from world.navigation import format_exit_summary, render_minimap, sort_exits
from world.questing import get_tracked_quest_payload
from world.resonance import get_resonance_label, get_world_label

from .objects import ObjectParent


TEXT_INDENT = "        "
TEXT_BODY_WIDTH = 60
DISPLAY_WIDTH = len(TEXT_INDENT) + TEXT_BODY_WIDTH
EXIT_LABEL = "EXITS: "


def _get_available_sessions(recipient):
    """Return all sessions attached to this recipient."""
    sessions = getattr(recipient, "sessions", None)
    if not sessions:
        return []

    if hasattr(sessions, "get"):
        return list(sessions.get())
    elif hasattr(sessions, "all"):
        return list(sessions.all())
    return []


def _get_web_sessions(recipient):
    """Return the webclient sessions attached to this recipient."""

    available = _get_available_sessions(recipient)
    return [
        session
        for session in available
        if (getattr(session, "protocol_key", "") or "").lower() in {"websocket", "ajax/comet", "webclient"}
    ]


def _only_web_sessions(recipient):
    """True if every attached session for this recipient is a web session."""

    available = _get_available_sessions(recipient)
    if not available:
        return False
    return len(_get_web_sessions(recipient)) == len(available)


def _send_webclient_event(recipient, **payload):
    """Send an OOB event only to webclient sessions for this recipient."""

    web_sessions = _get_web_sessions(recipient)
    if web_sessions and hasattr(recipient, "msg"):
        recipient.msg(session=web_sessions, **payload)


def _visible_room_contents(room, looker):
    visible_entities = [
        obj for obj in room.contents
        if obj != looker and not obj.destination and not obj.is_typeclass("typeclasses.characters.Character", exact=False)
    ]
    visible_chars = [
        obj for obj in room.contents
        if obj != looker
        and obj.is_typeclass("typeclasses.characters.Character", exact=False)
        and (
            getattr(obj, "is_connected", False)
            or bool(getattr(getattr(obj, "db", None), "brave_test_fixture", False))
        )
    ]
    return visible_entities, visible_chars


def _build_scene_payload(room, looker, visible_entities=None):
    tracked = get_tracked_quest_payload(looker) if looker and hasattr(looker, "ensure_brave_character") else None
    if not tracked:
        return {}
    return {"tracked_quest": tracked}


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    def return_appearance(self, looker, **kwargs):
        """
        Main method that Evennia calls to show the room. 
        We are overriding this to enforce the 'Page' layout.
        """
        if not looker:
            return ""
        if hasattr(getattr(looker, "ndb", None), "brave_showing_combat_result"):
            looker.ndb.brave_showing_combat_result = False
        _send_webclient_event(looker, brave_clear={})

        # 1. Header
        output = [self.get_display_header(looker, **kwargs)]

        # 2. Room Description (The Narrative)
        raw_desc = self.db.desc or "A place of mystery and potential."
        wrapped_desc = textwrap.fill(
            raw_desc,
            width=DISPLAY_WIDTH,
            initial_indent=TEXT_INDENT,
            subsequent_indent=TEXT_INDENT,
        )
        
        output.append(f"\n{wrapped_desc}\n")

        # 3. Entities (NPCs, Items, and Threats)
        visible_entities, visible_chars = _visible_room_contents(self, looker)
        from typeclasses.scripts import BraveEncounter

        visible_threats = BraveEncounter.get_visible_room_threats(self, looker)

        if visible_threats:
            output.append("\n        |rTHREATS HERE:|n")
            for threat in visible_threats:
                output.append(
                    f"          {threat['key']} |x[{threat['temperament_label'].lower()}, {threat['threat_label'].lower()} threat]|n"
                )
            output.append("")

        if visible_entities or visible_chars:
            output.append("\n        |wVISIBLE HERE:|n")
            for obj in visible_entities:
                output.append(f"          {obj.get_display_name(looker)}")
            for obj in visible_chars:
                output.append(f"          {obj.get_display_name(looker)}")
            output.append("")

        # 4. Footer (Interface)
        output.append(self.get_display_footer(looker, visible_entities=visible_entities, **kwargs))

        if looker:
            _send_webclient_event(
                looker,
                brave_view=build_room_view(
                    self,
                    looker,
                    visible_threats=visible_threats,
                    visible_entities=visible_entities,
                    visible_chars=visible_chars,
                ),
            )

        if _only_web_sessions(looker):
            return ""

        return "".join(output)

    def get_display_header(self, looker, **kwargs):
        zone = self.db.brave_zone
        world = getattr(self.db, "brave_world", "Brave")
        
        from world.resonance import get_resonance_profile
        profile = get_resonance_profile(self)
        cp = profile["color_primary"]
        cs = profile["color_secondary"]
        # Use subtle grey for the structural bars
        cb = "|x"

        mood_color = "|#d8b27a" if self.db.brave_safe else "|r"

        if world and world != "Brave":
            context = f"{zone} | {get_world_label(self)} | {get_resonance_label(self)}"
            context_color = cp
        else:
            context = zone or world or "Brave"
            context_color = mood_color

        title_lines = textwrap.wrap(self.key.upper(), width=TEXT_BODY_WIDTH) or [self.key.upper()]
        title_block = "\n".join(f"{TEXT_INDENT}{cs}{line}|n" for line in title_lines)
        banner_width = max(TEXT_BODY_WIDTH, max(len(line) for line in title_lines))
        context_text = str(context or "Brave").upper()
        filler = max(0, banner_width - len(context_text) - 2)
        left_rule = "-" * max(3, filler // 2)
        right_rule = "-" * max(3, filler - (filler // 2))

        header = [
            "\n",
            f"{TEXT_INDENT}{cb}{left_rule}|n {context_color}{context_text}|n {cb}{right_rule}|n",
            f"\n{title_block}\n",
        ]
        return "".join(header)

    def get_display_footer(self, looker, **kwargs):
        from world.resonance import get_resonance_profile
        profile = get_resonance_profile(self)
        cb = "|x"
        cs = profile["color_secondary"]
        
        footer_sections = []
        
        # 1. Activities & Hints
        activities = set(self.db.brave_activities or [])
        prompts = []
        if "fishing" in activities:
            prompts.append("        |cThe water looks fishable here.|n")
        if "cooking" in activities:
            prompts.append("        |yA warm hearth is ready here.|n")
        if self.db.brave_portal_hub:
            prompts.append("        |mThe Nexus ring is active here.|n")
        
        if prompts:
            footer_sections.append("\n" + "\n".join(prompts))

        # 2. Party Status
        if looker and hasattr(looker, "ensure_brave_character"):
            from world.party import get_present_party_members
            companions = [m.key for m in get_present_party_members(looker) if m.id != looker.id]
            if companions:
                footer_sections.append(f"\n{TEXT_INDENT}|wPARTY HERE:|n {', '.join(companions)}")

        # 3. Exits (The "Interface" block)
        # We send map data separately if it's a webclient-aware looker
        visible_entities = kwargs.get("visible_entities")

        if self.db.brave_map_region:
            map_data = render_minimap(self, radius=2, character=looker)
            if looker and map_data:
                _send_webclient_event(looker, mapdata=map_data)

        if looker:
            _send_webclient_event(looker, brave_scene=_build_scene_payload(self, looker, visible_entities=visible_entities))

        exits = sort_exits(list(self.exits))
        if exits:
            raw_exit_lines = textwrap.wrap(
                format_exit_summary(exits),
                width=DISPLAY_WIDTH,
                initial_indent=f"{TEXT_INDENT}{EXIT_LABEL}",
                subsequent_indent=f"{TEXT_INDENT}{' ' * len(EXIT_LABEL)}",
            )
            exit_rule_len = max(
                len(line) - len(TEXT_INDENT)
                for line in raw_exit_lines
            )
            rule = f"{TEXT_INDENT}{cb}" + "-" * exit_rule_len + "|n"
            styled_exit_lines = list(raw_exit_lines)
            styled_exit_lines[0] = styled_exit_lines[0].replace(
                f"{TEXT_INDENT}{EXIT_LABEL}",
                f"{TEXT_INDENT}{cs}EXITS:|n ",
                1,
            )
            interface_block = [f"\n{rule}", *styled_exit_lines, rule]
            footer_sections.append("\n".join(interface_block))

        return "\n".join(footer_sections) + "\n"
