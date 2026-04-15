"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""

from twisted.internet.task import LoopingCall

_ROAMING_LOOP = None


def _run_roaming_loop():
    from world.roaming import advance_roaming_parties

    advance_roaming_parties()


def _ensure_roaming_loop(interval):
    global _ROAMING_LOOP

    if _ROAMING_LOOP and getattr(_ROAMING_LOOP, "running", False):
        return
    _ROAMING_LOOP = LoopingCall(_run_roaming_loop)
    _ROAMING_LOOP.start(interval, now=False)


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from evennia.server.models import ServerConfig
    from world.bootstrap import ensure_brave_world
    from world.roaming import ROAMING_TICK_INTERVAL, ensure_roaming_party_manager

    if ServerConfig.objects.conf("last_initial_setup_step") != "done":
        return

    ensure_brave_world()
    ensure_roaming_party_manager()
    _ensure_roaming_loop(ROAMING_TICK_INTERVAL)


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
