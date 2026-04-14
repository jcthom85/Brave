"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds

from .account import (
    CmdBraveCreate,
    CmdBraveDelete,
    CmdBraveLogout,
    CmdBraveOOCLook,
    CmdBravePlay,
    CmdBraveTheme,
    CmdBraveUnconnectedLook,
)
from .brave_arcade import CmdArcade, CmdArcadeSubmit
from .brave_combat import CmdAttack, CmdEnemies, CmdFight, CmdFlee, CmdThreatDebug, CmdUse
from .brave_creator import CmdContent
from .brave_explore import CmdCook, CmdEat, CmdFish, CmdItem, CmdMap, CmdMore, CmdReel, CmdRest, CmdTravel
from .brave_party import CmdParty
from .brave_profile import CmdBuild, CmdClass, CmdGear, CmdPack, CmdQuests, CmdRace, CmdSheet
from .brave_town import CmdForge, CmdPray, CmdRead, CmdSell, CmdShift, CmdShop, CmdTalk


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdBuild())
        self.add(CmdRace())
        self.add(CmdClass())
        self.add(CmdSheet())
        self.add(CmdGear())
        self.add(CmdPack())
        self.add(CmdShop())
        self.add(CmdSell())
        self.add(CmdShift())
        self.add(CmdForge())
        self.add(CmdMap())
        self.add(CmdMore())
        self.add(CmdFish())
        self.add(CmdReel())
        self.add(CmdCook())
        self.add(CmdEat())
        self.add(CmdForge())
        self.add(CmdPray())
        self.add(CmdQuests())
        self.add(CmdTravel())
        self.add(CmdFight())
        self.add(CmdEnemies())
        self.add(CmdThreatDebug())
        self.add(CmdAttack())
        self.add(CmdUse())
        self.add(CmdFlee())
        self.add(CmdRest())
        self.add(CmdParty())
        self.add(CmdArcade())
        self.add(CmdArcadeSubmit())
        self.add(CmdTalk())
        self.add(CmdRead())
        self.add(CmdContent())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdBraveOOCLook())
        self.add(CmdBravePlay())
        self.add(CmdBraveLogout())
        self.add(CmdBraveCreate())
        self.add(CmdBraveDelete())
        self.add(CmdBraveTheme())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.remove("look")
        self.add(CmdBraveUnconnectedLook())


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
