"""
Ghost Mode command for Brave Creator Studio.
Allows developers to preview draft room content in-game.
"""

from __future__ import annotations
import json
from evennia import Command
from evennia.utils import create
from world.content import ContentEditor, get_content_registry

class CmdGhost(Command):
    """
    Ghost into a draft room.

    Usage:
      ghost <room_id>

    This will create a temporary 'ghost' version of the room 
    based on the current draft data and move you into it.
    """
    key = "ghost"
    locks = "cmd:perm(Developer)"
    help_category = "Developer"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: ghost <room_id>")
            return

        room_id = self.args.strip()
        editor = ContentEditor()
        
        # 1. Load draft data
        try:
            draft_rooms = editor.load_pack("world", stage="draft").get("rooms", [])
            room_data = next((r for r in draft_rooms if r.get("id") == room_id), None)
            
            if not room_data:
                # Fallback to live if not in draft
                registry = get_content_registry()
                room_data = registry.world.get_room(room_id)
                if not room_data:
                    caller.msg(f"Room '{room_id}' not found in draft or live.")
                    return
                caller.msg(f"|yRoom '{room_id}' not found in draft. Using live version.|n")
        except Exception as exc:
            caller.msg(f"Error loading draft data: {exc}")
            return

        # 2. Create/Find Ghost Room
        ghost_room_key = f"GHOST: {room_data.get('key', room_id)}"
        # Check if we already have a ghost room for this ID
        existing = caller.search(ghost_room_key, global_search=True, quiet=True)
        if existing:
            ghost_room = existing[0]
        else:
            ghost_room = create.create_object(
                "typeclasses.rooms.Room",
                key=ghost_room_key,
                locks="view:perm(Developer);move:perm(Developer)"
            )
            ghost_room.db.brave_ghost_source = room_id
            caller.msg(f"|gCreated ghost instance for {room_id}.|n")

        # 3. Update Ghost Room attributes from draft
        ghost_room.db.desc = room_data.get("desc", "No description.")
        ghost_room.db.brave_zone = room_data.get("zone", "Ghost Realm")
        ghost_room.db.brave_world = room_data.get("world", "Brave")
        ghost_room.db.brave_safe = room_data.get("safe", True)
        ghost_room.db.brave_activities = room_data.get("activities", [])
        
        # 4. Move caller to ghost room
        caller.move_to(ghost_room)
        caller.msg(f"|wYou ghost into {ghost_room.key}.|n")
        
        # 5. Tag for cleanup
        ghost_room.tags.add("ghost_room", category="temp")

class CmdGhostReturn(Command):
    """
    Return from Ghost Mode.

    Usage:
      unghost

    Returns you to your previous location and deletes the temporary ghost room.
    """
    key = "unghost"
    locks = "cmd:perm(Developer)"
    help_category = "Developer"

    def func(self):
        caller = self.caller
        location = caller.location
        
        if not location or not location.tags.get("ghost_room", category="temp"):
            caller.msg("You are not in a ghost room.")
            return
            
        # We don't necessarily know where they came from, so let's try to find their home
        home = caller.home or caller.search("brambleford_town_green", global_search=True)
        if isinstance(home, list): home = home[0]
        
        caller.move_to(home)
        caller.msg("|wReturning to reality.|n")
        
        # Cleanup if no one else is there
        if not any(obj.is_typeclass("typeclasses.characters.Character", exact=False) for obj in location.contents):
            location.delete()
            caller.msg("|xGhost instance collapsed.|n")
