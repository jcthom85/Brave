"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects child classes like this.

    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """Block active tutorial characters from leaving before the yard is done."""

        from world.boss_gates import character_has_cleared_gate, find_gate_for_exit, start_gate_ready_check
        from world.navigation import get_exit_block_message, is_exit_available
        from world.tutorial import get_tutorial_exit_block

        if not is_exit_available(self, traversing_object):
            traversing_object.msg(get_exit_block_message(self))
            return

        gate_key, gate = find_gate_for_exit(self)
        if gate and not character_has_cleared_gate(traversing_object, gate_key):
            ok, message = start_gate_ready_check(traversing_object, gate_key)
            from world.browser_panels import send_text_to_non_web_sessions

            send_text_to_non_web_sessions(traversing_object, message if ok else message or "That route is held by a boss.")
            return

        block_message = get_tutorial_exit_block(traversing_object, target_location)
        if block_message:
            traversing_object.msg(block_message)
            return
        super().at_traverse(traversing_object, target_location, **kwargs)
